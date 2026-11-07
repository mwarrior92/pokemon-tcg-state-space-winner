"""
Game-tree search over actions (Monte Carlo tree search), n turns deep.

  * Nodes are game states; edges are single actions by EITHER player (a card played, an attachment,
    a target / card choice, an attack, ending the turn). A path continues until `n_turns` turn
    boundaries have been crossed (default 3: the rest of our turn, the opponent's turn, our next turn),
    or the game ends.
  * Each iteration plays one path through the engine's forward model:
      1. sample the hidden cards (our deck order and Prizes, the opponent's hand / deck / Prizes)
         consistent with what is visible;
      2. walk the tree: at each decision the player to move picks the edge with the best value FOR THEM
         plus an exploration bonus (UCT), so the opponent defends rather than cooperates;
      3. add one new edge, then finish the path to the depth limit with a quick rollout policy;
      4. score the end: +1 / -1 for a win / loss, otherwise the board evaluation squashed to (-1, 1);
      5. back the score up the path.
  * Because every iteration re-runs the actions through the engine with fresh draws, coin flips and
    hidden-card guesses, chance and hidden information are averaged over ("open loop" search):
    edges are keyed by WHAT the action does (card ids, targets, attack), not by option index, so the
    same edge is recognised whatever the shuffle produced.
  * The move played is the most-visited edge at the root.
  * The tree is KEPT between decisions (rolling horizon): after our move, the root moves to that edge's
    child; when our next turn comes, the opponent's actual turn is classified into one of the plan
    categories and the root moves through that plan edge. What was already explored for this turn is
    reused and new iterations extend the horizon n turns past the present. If the opponent did
    something we never explored (a surprise), the tree is discarded. Reused statistics were gathered
    against an older, shallower horizon, so they are decayed when the root crosses a turn.
  * `observe(obs)` lets the game loop pass every observation (both players' steps), so the opponent's
    actual turn can be classified from the engine's event log; without it, the change in our board is used.

  * Optional shrinking horizon (`horizon_start`, `horizon_floor`): e.g. 9 turns on our first turn, one
    less on each of our later turns, never below 3 - early decisions look furthest ahead; late in the
    game the future is less uncertain and many paths end in a win or loss before the horizon anyway.
    "Turns" count both players' turns.

  agent = MCTSAgent(engine, my_deck, opp_deck, rng, iterations=150, n_turns=3)
  agent = MCTSAgent(engine, my_deck, opp_deck, rng, horizon_start=9, horizon_floor=3)
  action = agent(obs)
"""
from __future__ import annotations

import math
import random
from typing import Any

from cabt_bridge import (AREA_ACTIVE, AREA_BENCH, AREA_DECK, AREA_DISCARD, AREA_HAND, OT_ATTACH, OT_ATTACK, OT_END,
                         OT_EVOLVE, OT_PLAY, OT_RETREAT, OT_ABILITY, ST_MAIN, Engine, SearchAgent, evaluate_state)

EVAL_SCALE = 30.0          # fitted scores: tanh(value / 30) = 2 P(win) - 1 (calibrated, no centering)
HAND_SCALE = 10.0          # hand-set scores: leaves are scored RELATIVE to the root position, on this scale,
                           # so typical +-30..100 midgame values don't saturate tanh and erase differences


def _card_at(ob: dict[str, Any], o: dict[str, Any]) -> int | None:
    """Card id an option refers to (by area + index), if it refers to one."""
    area, idx = o.get("area"), o.get("index")
    if area is None and idx is not None and o.get("type") in (OT_PLAY, OT_ATTACH, OT_EVOLVE):
        area = AREA_HAND                 # play / attach / evolve options give a hand index without an area
    if area is None or idx is None:
        return None
    cur = ob["current"]
    pl = cur["players"][o.get("playerIndex", cur["yourIndex"])]
    try:
        if area == AREA_DECK:
            return (ob["select"].get("deck") or [])[idx]["id"]
        if area == AREA_HAND:
            return pl["hand"][idx]["id"]
        if area == AREA_DISCARD:
            c = pl["discard"][idx]
            return c if isinstance(c, int) else c["id"]
        if area == AREA_ACTIVE:
            return pl["active"][0]["id"]
        if area == AREA_BENCH:
            return pl["bench"][idx]["id"]
    except (IndexError, KeyError, TypeError):
        return None
    return None


def option_key(ob: dict[str, Any], i: int) -> tuple:
    """What option i does, independent of list position."""
    o = ob["select"]["option"][i]
    target = None
    if o.get("inPlayArea") is not None:
        target = _card_at(ob, {"area": o["inPlayArea"], "index": o.get("inPlayIndex"),
                               "playerIndex": o.get("playerIndex", ob["current"]["yourIndex"])})
    return (o.get("type"), _card_at(ob, o), o.get("area"), o.get("playerIndex"), target,
            o.get("attackId"), o.get("number"))


def choice_key(ob: dict[str, Any], choice: list[int]) -> tuple:
    return (ob["select"].get("context"), tuple(sorted(option_key(ob, i) for i in choice)))


class _Edge:
    __slots__ = ("n", "w", "child")

    def __init__(self) -> None:
        self.n = 0
        self.w = 0.0                 # summed value from the ROOT player's perspective
        self.child: _Node | None = None


class _Node:
    __slots__ = ("n", "edges", "prior")

    def __init__(self) -> None:
        self.n = 0
        self.edges: dict[tuple, _Edge] = {}
        self.prior: dict[tuple, float] | None = None    # one-step greedy scores, for expansion order


# rollout priorities for main-phase options (quick, sensible default play)
_PRIORITY = {OT_EVOLVE: 9.0, OT_ATTACH: 8.0, OT_PLAY: 7.0, OT_ABILITY: 6.0, OT_ATTACK: 5.0, OT_RETREAT: 1.0, OT_END: 0.0}

# ---------------------------------------------------------------------------
# Opponent turns are HIGH-LEVEL edges: one plan category per turn, played out by its own policy.
# ---------------------------------------------------------------------------
OPP_PLANS = ("setup", "attack", "gust_ko", "abilities_attack")
_GUST_TEXT = ("switch in 1 of your opponent's benched pokémon to the active spot",
              "your opponent switches their active pokémon with 1 of their benched")


def _is_gust(engine: Engine, card_id: int | None) -> bool:
    c = engine.cards.get(card_id or -1, {})
    t = " ".join((s.get("text") or "").lower().replace("’", "'") for s in c.get("skills") or [])
    return any(g in t for g in _GUST_TEXT)


def _places_damage(engine: Engine, card_id: int | None) -> bool:
    c = engine.cards.get(card_id or -1, {})
    t = " ".join((s.get("text") or "").lower() for s in c.get("skills") or [])
    return "damage counters on" in t and "opponent" in t


class MCTSAgent:
    def __init__(self, engine: Engine, my_deck: list[int], opp_deck: list[int], rng: random.Random,
                 iterations: int = 150, n_turns: int = 3, c_explore: float = 0.1, max_steps: int = 400,
                 sub_cap: int = 6, reuse: bool = True, decay: float = 0.5,
                 horizon_start: int | None = None, horizon_floor: int = 3, greedy_turn: bool = True,
                 n_guesses: int = 10, default_margin: float = 0.02, greedy_opp: bool = False) -> None:
        self.engine = engine
        self.rng = rng
        self.iterations = iterations
        self.n_turns = n_turns
        self.greedy_turn = greedy_turn
        self.default_margin = default_margin
        self.greedy_opp = greedy_opp
        self.n_guesses = n_guesses                 # shared hidden-card guesses per decision (paired comparisons)
        self._guess_pool: list[tuple] = []
        self.horizon_start = horizon_start
        self.horizon_floor = horizon_floor
        self._horizon_now = n_turns
        self._root_value = 0.0
        self.c = c_explore
        self.max_steps = max_steps
        self.sub_cap = sub_cap
        # the one-turn agent supplies hidden-card sampling, the static sub-choice policy and candidate choices
        self.helper = SearchAgent(engine, my_deck, opp_deck, rng, sub_search=False)
        self.last_stats: dict[str, Any] = {}
        self.reuse = reuse
        self.decay = decay
        self.tree: _Node | None = None             # subtree for the decision we expect next
        self.me: int | None = None
        self.last_turn: int | None = None
        self.followed: set[int] = set()            # opponent turns already stepped through in the tree
        self.events = {"attack": False, "gust": False, "counters": False, "seen": False}
        self.snapshot: dict[str, Any] | None = None
        self.counts = {"reused": 0, "surprises": 0, "fresh": 0}

    # ---- action sets ----
    def _choices(self, ob: dict[str, Any]) -> list[list[int]]:
        sel = ob["select"]
        if sel["type"] == ST_MAIN:
            return [[i] for i in range(len(sel["option"]))]
        if sel["maxCount"] == 0:
            return [[]]
        return self.helper._candidate_selections(ob, cap=self.sub_cap)

    def _rollout_choice(self, ob: dict[str, Any], actions_this_turn: int) -> list[int]:
        sel = ob["select"]
        if sel["type"] != ST_MAIN:
            return self.helper.static_choice(ob)
        opts = sel["option"]
        if actions_this_turn >= 12:                      # don't loop forever inside one turn
            for i, o in enumerate(opts):
                if o["type"] in (OT_ATTACK, OT_END):
                    return [i]
        best, best_v = 0, -1.0
        for i, o in enumerate(opts):
            v = _PRIORITY.get(o["type"], 3.0) + self.rng.random() * 2.5
            if v > best_v:
                best, best_v = i, v
        return [best]

    # ---- opponent plans ----
    def _gust_target(self, ob: dict[str, Any], who: int) -> int | None:
        """For a pick-one choice among the other side's Benched Pokemon: the one worth the most Prizes
        that our Active could Knock Out (else simply the most Prizes)."""
        from cabt_bridge import _prize_value, attack_plan
        sel = ob["select"]
        if sel["maxCount"] != 1:
            return None
        cur = ob["current"]
        att = (cur["players"][who].get("active") or [None])[0]
        best, best_v = None, -1.0
        for i, o in enumerate(sel["option"]):
            if o.get("area") != AREA_BENCH or o.get("playerIndex") == who:
                continue
            try:
                mon = cur["players"][o["playerIndex"]]["bench"][o["index"]]
            except (IndexError, KeyError, TypeError):
                continue
            pv = _prize_value(self.engine, mon["id"])
            ko = bool(att) and attack_plan(self.engine, cur, who, att, mon)[0] >= mon.get("hp", 999)
            v = pv * (2.0 if ko else 1.0)
            if v > best_v:
                best, best_v = i, v
        return best

    def _plan_choice(self, ob: dict[str, Any], plan: str, actions_this_turn: int,
                     state: dict[str, Any] | None = None) -> list[int]:
        """The opponent's play under one high-level plan (details inside the plan are lumped together).
        With `state` (and greedy_opp), each main-phase action is the opponent's one-step greedy best FROM THEIR
        SIDE among the actions the plan allows, the way the one-turn agent plays; otherwise quick priorities."""
        sel = ob["select"]
        cur = ob["current"]
        who = cur["yourIndex"]
        if sel["type"] != ST_MAIN:
            if plan == "gust_ko":
                t = self._gust_target(ob, who)
                if t is not None:
                    return [t]
            return self.helper.static_choice(ob)
        if state is not None and self.greedy_opp and actions_this_turn < 12:
            best, best_v = None, -1e18
            for i, o in enumerate(sel["option"]):
                t = o["type"]
                cid = _card_at(ob, o) if t in (OT_PLAY, OT_ABILITY) else None
                if plan == "setup" and t == OT_ATTACK:
                    continue
                gust = t == OT_PLAY and _is_gust(self.engine, cid)
                if gust and plan != "gust_ko":
                    continue
                bonus = 0.0
                if plan == "gust_ko" and gust:
                    bonus = 1e6                                  # the plan: gust first
                if plan == "abilities_attack" and t == OT_ABILITY and _places_damage(self.engine, cid):
                    bonus = 1e6                                  # the plan: place counters first
                ch = self.engine.search_step(state["searchId"], [i])
                if ch is None:
                    continue
                v = evaluate_state(self.engine, ch["observation"]["current"], who, mid_turn=cur["turn"]) + bonus \
                    - (0.5 if t == OT_END else 0.0)
                if v > best_v:
                    best, best_v = [i], v
            if best is not None:
                return best
        from cabt_bridge import attack_estimate
        opts = sel["option"]
        if actions_this_turn >= 12:
            for i, o in enumerate(opts):
                if o["type"] == (OT_END if plan == "setup" else OT_ATTACK):
                    return [i]
        att = (cur["players"][who].get("active") or [None])[0]
        dfn = (cur["players"][1 - who].get("active") or [None])[0]
        best, best_v = 0, -1e9
        for i, o in enumerate(opts):
            t = o["type"]
            cid = _card_at(ob, o) if t in (OT_PLAY, OT_ABILITY) else None
            if t == OT_ATTACK:
                if plan == "setup":
                    v = -5.0
                else:
                    dmg = attack_estimate(self.engine, cur, who, att, dfn, o.get("attackId"))[0] if att else 0.0
                    v = 5.0 + dmg / 100.0
            elif t == OT_END:
                v = 0.5 if plan == "setup" else 0.0
            elif t == OT_PLAY and _is_gust(self.engine, cid):
                v = 10.0 if plan == "gust_ko" else -1.0
            elif t == OT_ABILITY and _places_damage(self.engine, cid):
                v = 10.0 if plan == "abilities_attack" else (4.0 if plan == "setup" else 6.0)
            elif t == OT_RETREAT:
                v = 1.0 if plan == "setup" else -1.0
            else:
                v = _PRIORITY.get(t, 3.0)
            v += self.rng.random()
            if v > best_v:
                best, best_v = i, v
        return [best]

    def _prior(self, state: dict[str, Any], keys: list[tuple], choices: list[list[int]], me: int) -> dict[tuple, float]:
        """One-step greedy score of each option at a node (as the one-turn agent ranks them)."""
        ob = state["observation"]
        turn = ob["current"]["turn"]
        out: dict[tuple, float] = {}
        for key, ch in zip(keys, choices):
            if key in out:
                continue
            nxt = self.engine.search_step(state["searchId"], ch)
            if nxt is None:
                out[key] = -1e18
                continue
            o = ob["select"]["option"][ch[0]] if ch else {}
            out[key] = evaluate_state(self.engine, nxt["observation"]["current"], me, mid_turn=turn)                 - (0.5 if o.get("type") == OT_END else 0.0)
        return out

    def _greedy_choice(self, state: dict[str, Any], me: int) -> list[int] | None:
        """One-step greedy main-phase choice for us (as the one-turn agent completes its turn): try each
        option in the forward model and keep the one whose result scores best (ending the turn slightly
        penalised so useful actions come first)."""
        ob = state["observation"]
        best, best_v = None, -1e18
        for i, o in enumerate(ob["select"]["option"]):
            ch = self.engine.search_step(state["searchId"], [i])
            if ch is None:
                continue
            v = evaluate_state(self.engine, ch["observation"]["current"], me,
                               mid_turn=ob["current"]["turn"]) - (0.5 if o["type"] == OT_END else 0.0)
            if v > best_v:
                best, best_v = [i], v
        return best

    # ---- search ----
    def _leaf_value(self, cur: dict[str, Any], me: int) -> float:
        if cur.get("result", -1) >= 0:
            return 1.0 if cur["result"] == me else (-1.0 if cur["result"] == 1 - me else 0.0)
        from cabt_bridge import _EVAL
        v = evaluate_state(self.engine, cur, me)
        if _EVAL.get("fitted"):
            return math.tanh(v / EVAL_SCALE)
        return math.tanh((v - self._root_value) / HAND_SCALE)

    def _iterate(self, obs: dict[str, Any], root: _Node, me: int) -> bool:
        eng = self.engine
        guess = self._guess_pool[self._iter_no % len(self._guess_pool)] if self._guess_pool else self.helper._guesses(obs)
        self._iter_no += 1
        state = eng.search_begin(obs, *guess)
        if state is None:
            return False
        path: list[tuple[_Node, int, tuple]] = []
        node: _Node | None = root
        last_turn = obs["current"]["turn"]
        boundaries = 0
        actions_this_turn = 0
        value = None
        opp_plan: str | None = None
        plan_turn: int | None = None
        try:
            for _ in range(self.max_steps):
                ob = state["observation"]
                cur = ob["current"]
                if cur.get("result", -1) >= 0 or ob.get("select") is None:
                    value = self._leaf_value(cur, me)
                    break
                if cur["turn"] != last_turn:
                    boundaries += 1
                    last_turn = cur["turn"]
                    actions_this_turn = 0
                if boundaries >= self._horizon_now:
                    value = self._leaf_value(cur, me)
                    break
                who = cur["yourIndex"]
                if who != me:
                    # Opponent: one high-level plan edge per turn, then the plan's policy plays the turn.
                    if ob["select"]["type"] == ST_MAIN and plan_turn != cur["turn"]:
                        plan_turn = cur["turn"]
                        if node is None:
                            opp_plan = "attack"
                        else:
                            keys = [("plan", p) for p in OPP_PLANS]
                            fresh = [k for k in keys if k not in node.edges]
                            if fresh:
                                key = self.rng.choice(fresh)
                                node.edges[key] = _Edge()
                                path.append((node, who, key))
                                node = None
                            else:
                                log_n = math.log(max(1, node.n))
                                key = max(keys, key=lambda k: -node.edges[k].w / node.edges[k].n
                                          + self.c * math.sqrt(log_n / node.edges[k].n))
                                e = node.edges[key]
                                path.append((node, who, key))
                                if e.child is None:
                                    e.child = _Node()
                                node = e.child
                            opp_plan = key[1]
                    if plan_turn == cur["turn"] and opp_plan:
                        choice = self._plan_choice(ob, opp_plan, actions_this_turn, state)
                    else:
                        choice = self.helper.static_choice(ob)   # opponent choices outside their main phase
                    nxt = eng.search_step(state["searchId"], choice)
                    if nxt is None:
                        break
                    if ob["select"]["type"] == ST_MAIN:
                        actions_this_turn += 1
                    state = nxt
                    continue
                choices = self._choices(ob)
                if len(choices) == 1:
                    choice = choices[0]
                elif node is None:
                    choice = None
                    if (self.greedy_turn and cur["turn"] == obs["current"]["turn"] and ob["select"]["type"] == ST_MAIN
                            and actions_this_turn < 12):
                        choice = self._greedy_choice(state, me)       # the turn we're actually playing
                    if choice is None:
                        choice = self._rollout_choice(ob, actions_this_turn)
                else:
                    keys = [choice_key(ob, c) for c in choices]
                    fresh = [k for k, key in enumerate(keys) if key not in node.edges]
                    if fresh:
                        # expand the most promising untried edge first: for our main-phase decisions by a
                        # one-step greedy look (computed once per node), for card / target choices in the
                        # static policy's ranked order (candidates come ranked)
                        if ob["select"]["type"] == ST_MAIN and len(fresh) > 1:
                            if node.prior is None:
                                node.prior = self._prior(state, keys, choices, me)
                            pick = max(fresh, key=lambda k: node.prior.get(keys[k], -1e18))
                        else:
                            pick = fresh[0]
                        node.edges[keys[pick]] = _Edge()
                        path.append((node, who, keys[pick]))
                        choice, node = choices[pick], None
                    else:
                        sign = 1.0 if who == me else -1.0
                        log_n = math.log(max(1, node.n))
                        best_k, best_u = 0, -1e18
                        for k, key in enumerate(keys):
                            e = node.edges[key]
                            u = sign * e.w / e.n + self.c * math.sqrt(log_n / e.n)
                            if u > best_u:
                                best_k, best_u = k, u
                        e = node.edges[keys[best_k]]
                        path.append((node, who, keys[best_k]))
                        if e.child is None:
                            e.child = _Node()
                        choice, node = choices[best_k], e.child
                nxt = eng.search_step(state["searchId"], choice)
                if nxt is None:
                    break
                if ob["select"]["type"] == ST_MAIN:
                    actions_this_turn += 1
                state = nxt
            if value is None:
                value = self._leaf_value(state["observation"]["current"], me)
        finally:
            eng.search_end()
        for nd, _, key in path:
            e = nd.edges[key]
            e.n += 1
            e.w += value
            nd.n += 1
        return True

    # ---- following the real game through the kept tree ----
    def observe(self, obs: dict[str, Any]) -> None:
        """Record what the opponent did, from the engine's event log of every step."""
        if self.me is None:
            return
        opp = 1 - self.me
        for lg in obs.get("logs") or []:
            if lg.get("playerIndex") != opp:
                continue
            t = lg.get("type")
            if t == 15:                                                # attack
                self.events["attack"] = self.events["seen"] = True
            elif t == 10 and _is_gust(self.engine, lg.get("cardId")):  # Trainer played: a gust card
                self.events["gust"] = self.events["seen"] = True
            elif t == 16 and lg.get("putDamageCounter") and not self.events["attack"]:
                self.events["counters"] = self.events["seen"] = True
            elif t in (6, 10, 11, 12):
                self.events["seen"] = True

    def _snap(self, cur: dict[str, Any], me: int) -> dict[str, Any]:
        p = cur["players"][me]
        mons = [m for m in (p.get("active") or []) if m] + list(p.get("bench") or [])
        act = (p.get("active") or [None])[0]
        return {"damage": sum(m.get("maxHp", 0) - m.get("hp", 0) for m in mons), "n": len(mons),
                "opp_prizes": len(cur["players"][1 - me].get("prize") or []), "active": act and act.get("serial"),
                "serials": {m.get("serial") for m in mons}}

    def _classify_opp_turn(self, cur: dict[str, Any], me: int) -> str:
        """Which plan category the opponent's actual turn fell into."""
        ev = self.events
        if not ev["seen"] and self.snapshot is not None:              # no event log: infer from our board
            now = self._snap(cur, me)
            hit = now["damage"] > self.snapshot["damage"] or now["opp_prizes"] < self.snapshot["opp_prizes"]
            swapped = (self.snapshot["active"] is not None and now["active"] != self.snapshot["active"]
                       and self.snapshot["active"] in now["serials"])
            return "setup" if not hit else ("gust_ko" if swapped else "attack")
        if not ev["attack"]:
            return "setup"
        if ev["gust"]:
            return "gust_ko"
        return "abilities_attack" if ev["counters"] else "attack"

    def _decay(self, node: _Node) -> None:
        stack = [node]
        while stack:
            nd = stack.pop()
            nd.n *= self.decay
            for e in nd.edges.values():
                e.n *= self.decay
                e.w *= self.decay
                if e.child is not None:
                    stack.append(e.child)

    def _follow_opponent(self, cur: dict[str, Any], me: int) -> None:
        """Move the kept root through the plan edge(s) for opponent turns played since our last decision."""
        if self.tree is None or self.last_turn is None or cur["turn"] == self.last_turn:
            return
        first = cur.get("firstPlayer", 0)
        for t in range(self.last_turn + 1, cur["turn"] + 1):
            owner = first if t % 2 == 1 else 1 - first
            if owner == me or t in self.followed:
                continue
            if t == cur["turn"] and not self.events["seen"]:
                return                                                   # their turn hasn't really started
            key = ("plan", self._classify_opp_turn(cur, me))
            e = self.tree.edges.get(key)
            self.followed.add(t)
            self.events = {"attack": False, "gust": False, "counters": False, "seen": False}
            if e is None or e.child is None:
                self.tree = None                                         # a surprise: start fresh
                self.counts["surprises"] += 1
                return
            self.tree = e.child
            self._decay(self.tree)

    def horizon(self, cur: dict[str, Any], me: int) -> int:
        """Turns to look ahead from this decision: fixed `n_turns`, or `horizon_start` on our first turn,
        one less on each later turn of ours, never below `horizon_floor`."""
        if self.horizon_start is None:
            return self.n_turns
        first_turn = 1 if cur.get("firstPlayer", 0) == me else 2
        ours_so_far = max(0, (cur.get("turn", 1) - first_turn) // 2)
        return max(self.horizon_floor, self.horizon_start - ours_so_far)

    def __call__(self, obs: dict[str, Any]) -> list[int]:
        sel = obs.get("select")
        if not sel:
            return []
        choices = self._choices(obs)
        if len(choices) <= 1 or not obs.get("search_begin_input"):
            return choices[0] if choices else self.helper.static_choice(obs)
        me = obs["current"]["yourIndex"]
        self.me = me
        cur = obs["current"]
        self._horizon_now = self.horizon(cur, me)
        self._root_value = evaluate_state(self.engine, cur, me)
        self.max_steps = max(self.max_steps, 60 * self._horizon_now)
        if self.reuse:
            self._follow_opponent(cur, me)
        root = self.tree if (self.reuse and self.tree is not None) else _Node()
        # the same few hidden-card guesses, cycled, so every option is judged against the same hands
        self._guess_pool = [self.helper._guesses(obs) for _ in range(max(1, self.n_guesses))]
        self._iter_no = 0
        self.counts["reused" if root is self.tree else "fresh"] += 1
        done = 0
        for _ in range(self.iterations):
            try:
                done += self._iterate(obs, root, me)
            except OSError:                              # rare engine fault: skip this iteration
                continue
        keys = [choice_key(obs, c) for c in choices]
        scored = [(root.edges[k].n, root.edges[k].w / max(1, root.edges[k].n), i) for i, k in enumerate(keys) if k in root.edges]
        self.last_stats = {"iterations": done, "edges": len(scored), **self.counts}
        self._last_root, self._last_keys, self._last_choices = root, keys, choices   # for diagnostics
        if not scored:
            return self.helper.static_choice(obs) if sel["type"] != ST_MAIN else choices[0]
        # pick by value among options with a reasonable share of the visits (robust at small budgets)
        top = max(n for n, _, _ in scored)
        q_best, _, i = max((q, n, i) for n, q, i in scored if n >= 0.2 * top)
        if sel["type"] != ST_MAIN:
            # card / target choices: the board score can't tell most of them apart (it counts the hand,
            # not which cards are in it), so keep the static policy's ranked pick unless another option
            # is clearly better
            default = self.helper.static_choice(obs)
            dkey = choice_key(obs, default) if default is not None else None
            for n, q, j in scored:
                if keys[j] == dkey and q >= q_best - self.default_margin:
                    i = j
                    break
        if self.reuse:
            e = root.edges.get(keys[i])
            self.tree = e.child if e is not None else None
            self.last_turn = cur["turn"]
            self.snapshot = self._snap(cur, me)
        return choices[i]
