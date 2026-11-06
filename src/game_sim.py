"""
Turn-by-turn abstract Pokemon TCG simulator.

The game is modeled as STATE TRANSITIONS: every card effect is an explicit change to
the board (Dusknoir's Cursed Blast = Dusknoir is Knocked Out, the opponent takes a
Prize, 13 damage counters land on a chosen Pokemon). Games are sampled with real
shuffled decks, so likely states (e.g. how many Pokemon the player going first has in
play when the second player starts) appear at their natural frequency, and a state's
value is simply how often games through it are won.

Rules modeled: setup + mulligans, 6 Prizes, draw/deck-out, 1 energy attach, 1 Supporter
(none on the first player's first turn), no attack on the first player's first turn,
evolution timing, Rare Candy, retreat, Weakness x2 / Resistance -30, Tera bench
protection, attack damage vs damage counters, bench limits, item lock, retreat lock,
"can't attack next turn", Knock Outs, Prizes (ex = 2, Mega ex = 3).
Not modeled: Special Conditions (except as no-ops), most coin-flip side effects,
hidden-information play (the policy is a greedy heuristic, identical for every deck).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from card_compiler import CompiledCard, card_matches_filter
from sim_effects import AttackScript, CardScript, can_pay, compile_script, energy_units, missing_units

MAX_PLIES = 50


def S(card: CompiledCard) -> CardScript:
    return compile_script(card)


@dataclass
class Mon:
    stack: list[CompiledCard]
    entered_turn: int
    damage: int = 0
    energy: list[CompiledCard] = field(default_factory=list)
    tool: CompiledCard | None = None
    moved_in_turn: int = -1
    cant_attack_until: int = -1
    cant_retreat_turn: int = -1
    ability_used_turn: int = -1
    evolved_turn: int = -1

    @property
    def card(self) -> CompiledCard:
        return self.stack[-1]


@dataclass
class Player:
    idx: int
    decklist: list[CompiledCard]
    deck: list[CompiledCard] = field(default_factory=list)
    hand: list[CompiledCard] = field(default_factory=list)
    discard: list[CompiledCard] = field(default_factory=list)
    prizes: list[CompiledCard] = field(default_factory=list)
    active: Mon | None = None
    bench: list[Mon] = field(default_factory=list)
    turns_taken: int = 0
    supporter_used: bool = False
    energy_attached: bool = False
    retreated: bool = False
    stadium_played: bool = False
    item_locked_turn: int = -1
    ko_on_turn: int = -10          # last ply on which one of my Pokemon was Knocked Out
    buffs: list[dict[str, Any]] = field(default_factory=list)
    legacy_used: bool = False
    once_names: set[str] = field(default_factory=set)

    def in_play(self) -> list[Mon]:
        return ([self.active] if self.active else []) + list(self.bench)

    @property
    def prizes_left(self) -> int:
        return len(self.prizes)


class Game:
    def __init__(self, deck_a: list[CompiledCard], deck_b: list[CompiledCard], seed: int, first: int = 0,
                 agents: tuple[Any, Any] | None = None):
        self.rng = random.Random(seed)
        self.players = [Player(0, list(deck_a)), Player(1, list(deck_b))]
        self.first = first
        self.turn = 0                 # global ply counter (1 = first player's first turn)
        self.current = first
        self.stadium: CompiledCard | None = None
        self.stadium_owner = -1
        self.winner: int | None = None
        self.end_reason = ""
        self.trace: list[dict[str, Any]] = []
        self.events: list[tuple[int, int, str]] = []   # (ply, player, event)
        self.agents = agents or (GreedyAgent(), GreedyAgent())
        self.verbose = False
        self.log_lines: list[str] = []

    def note(self, pl: "Player", msg: str) -> None:
        if self.verbose:
            self.log_lines.append(f"[ply {self.turn} P{pl.idx}] {msg}")

    # ------------------------------------------------------------------ helpers
    def opp(self, p: int) -> Player:
        return self.players[1 - p]

    def stadium_flags(self) -> set[str]:
        return S(self.stadium).stadium if self.stadium else set()

    def shuffle(self, pl: Player) -> None:
        self.rng.shuffle(pl.deck)

    def draw(self, pl: Player, n: int) -> int:
        k = 0
        for _ in range(n):
            if not pl.deck:
                break
            pl.hand.append(pl.deck.pop())
            k += 1
        return k

    def abilities_on(self, mon: Mon, owner: Player) -> bool:
        if "watchtower" in self.stadium_flags() and "Colorless" in mon.card.types:
            return False
        return True

    def passives(self, pl: Player) -> set[str]:
        out: set[str] = set()
        for m in pl.in_play():
            if self.abilities_on(m, pl):
                out |= S(m.card).passives
        return out

    def damp_in_play(self) -> bool:
        return any("DAMP" in self.passives(p) for p in self.players)

    def max_hp(self, mon: Mon) -> int:
        hp = mon.card.hp
        if mon.tool and "jamming_tower" not in self.stadium_flags():
            t = S(mon.tool).tool
            if "hp" in t and (not t.get("hp_type") or t["hp_type"].capitalize() in mon.card.types or mon.card.name.lower().startswith(t["hp_type"])):
                hp += t["hp"]
        for e in mon.energy:
            t = S(e).tool
            if "hp" in t and "Grass" in mon.card.types:
                hp += t["hp"]
        if "gravity_mountain" in self.stadium_flags() and mon.card.stage == 2:
            hp -= 30
        return hp

    def units(self, mon: Mon, pl: Player) -> list[str]:
        wild = "WILD_GROWTH" in self.passives(pl)
        out: list[str] = []
        for e in mon.energy:
            u = energy_units(e, mon.card)
            if wild and "BASIC_ENERGY" in e.tags and e.primary_energy_type == "Grass":
                u = ["Grass", "Grass"]
            out += u
        return out

    def retreat_cost(self, mon: Mon, pl: Player) -> int:
        rc = mon.card.retreat_cost
        if mon.tool and "jamming_tower" not in self.stadium_flags():
            rc -= S(mon.tool).tool.get("retreat_minus", 0)
        if mon.card.stage == 0 and "SKYLINER" in self.passives(pl):
            rc = 0
        if "n_castle" in self.stadium_flags() and mon.card.name.startswith("N's "):
            rc = 0
        return max(0, rc)

    def bench_limit(self, pl: Player) -> int:
        if "area_zero" in self.stadium_flags() and any("Tera" in m.card.subtypes for m in pl.in_play()):
            return 8
        return 5

    def attack_cost(self, mon: Mon, atk: AttackScript, pl: Player) -> list[str]:
        cost = list(atk.cost)
        if "SEASONED_SKILL" in S(mon.card).passives and self.abilities_on(mon, pl):
            taken = 6 - self.opp(pl.idx).prizes_left
            for _ in range(taken):
                if "Colorless" in cost:
                    cost.remove("Colorless")
        if "nighttime_mine" in self.stadium_flags() and "Tera" in mon.card.subtypes:
            cost.append("Colorless")
        return cost

    def can_use_attack(self, mon: Mon, atk: AttackScript, pl: Player) -> bool:
        if mon.cant_attack_until > self.turn:
            return False
        return can_pay(self.attack_cost(mon, atk, pl), self.units(mon, pl))

    # ------------------------------------------------------------------ play moves
    def put_on_bench(self, pl: Player, card: CompiledCard, from_hand: bool = True) -> Mon | None:
        if len(pl.bench) >= self.bench_limit(pl):
            return None
        if from_hand:
            pl.hand.remove(card)
        self.note(pl, f"bench {card.name}")
        mon = Mon([card], entered_turn=self.turn)
        pl.bench.append(mon)
        if "risky_ruins" in self.stadium_flags() and card.stage == 0 and "Darkness" not in card.types:
            self.place_counters(pl, mon, 2, from_attack=False, owner_is_target=True, by_effect=False)
        sc = S(card)
        if from_hand and sc.ability and sc.ability.get("trigger") == "bench" and self.abilities_on(mon, pl):
            self.agents[pl.idx].on_bench_trigger(self, pl, mon, sc.ability)
        return mon

    def evolve(self, pl: Player, mon: Mon, card: CompiledCard, from_hand: bool = True) -> None:
        if from_hand:
            pl.hand.remove(card)
        self.note(pl, f"evolve {mon.card.name} -> {card.name}")
        mon.stack.append(card)
        mon.evolved_turn = self.turn
        sc = S(card)
        if from_hand and sc.ability and sc.ability.get("trigger") == "evolve" and self.abilities_on(mon, pl):
            if sc.ability["kind"] == "draw":
                self.draw(pl, sc.ability["n"])

    def can_evolve(self, pl: Player, mon: Mon, card: CompiledCard) -> bool:
        if card.evolves_from != mon.card.name or pl.turns_taken == 0:
            return False
        if mon.evolved_turn == self.turn:
            return False
        if mon.entered_turn < self.turn:
            return True
        return "forest_of_vitality" in self.stadium_flags() and "Grass" in mon.card.types and "Grass" in card.types

    def attach_energy(self, pl: Player, mon: Mon, card: CompiledCard, from_hand: bool = True) -> None:
        if from_hand:
            pl.hand.remove(card)
        self.note(pl, f"attach {card.name} -> {mon.card.name}")
        mon.energy.append(card)
        t = S(card).tool
        rt = card.rules_text.lower()
        if from_hand and "when you attach this card from your hand to a psychic" in rt and "Psychic" in mon.card.types:
            self.search_to_bench(pl, {"kind": "pokemon", "filter": {"stage": 0, "ptype": "Psychic"}, "n": 2})
        if from_hand and t.get("on_attach_draw"):
            self.draw(pl, t["on_attach_draw"])

    def search_to_bench(self, pl: Player, spec: dict[str, Any]) -> int:
        k = 0
        for _ in range(spec.get("n", 1)):
            if len(pl.bench) >= self.bench_limit(pl):
                break
            c = self.agents[pl.idx].choose_from(self, pl, [x for x in pl.deck if matches_spec(x, spec)], purpose="bench")
            if not c:
                break
            pl.deck.remove(c)
            self.put_on_bench(pl, c, from_hand=False)
            k += 1
        self.shuffle(pl)
        return k

    def switch_active(self, pl: Player, new: Mon) -> None:
        if pl.active is None:
            pl.bench.remove(new)
            pl.active = new
        else:
            pl.bench.remove(new)
            pl.bench.append(pl.active)
            pl.active = new
        new.moved_in_turn = self.turn

    # ------------------------------------------------------------------ damage
    def place_counters(self, owner: Player, mon: Mon, n: int, from_attack: bool, owner_is_target: bool = True,
                       by_effect: bool = True) -> int:
        """Damage counters (NOT attack damage): ignore Weakness/Resistance and damage modifiers."""
        is_bench = mon is not owner.active
        if by_effect:
            if is_bench and "battle_cage" in self.stadium_flags():
                return 0
            if is_bench and from_attack and "SPHERICAL_SHIELD" in self.passives(owner):
                return 0
            if "HIDE_N_SNEAK" in S(mon.card).passives:
                return 0
            if from_attack and any("prevent all effects of attacks" in e.rules_text.lower() for e in mon.energy):
                return 0
        mon.damage += 10 * n
        return 10 * n

    def attack_damage_to(self, att_pl: Player, attacker: Mon, def_pl: Player, target: Mon, amount: float,
                         atk: AttackScript | None) -> int:
        """Apply ATTACK DAMAGE (with Weakness/Resistance and protection effects)."""
        if amount <= 0:
            return 0
        is_bench = target is not def_pl.active
        d_pass = self.passives(def_pl)
        if is_bench:
            if "BENCH_SAFE" in S(target.card).passives:
                return 0
            if "FLOWER_CURTAIN" in d_pass and not target.card.is_rule_box:
                return 0
            if "SPHERICAL_SHIELD" in d_pass:
                return 0
            dmg = int(amount)
        else:
            dmg = int(amount)
            ignores_wr = atk.ignores_wr if atk else False
            weak = target.card.weakness
            if "FAIRY_ZONE" in self.passives(att_pl) and "Dragon" in target.card.types:
                weak = "Psychic"
            if not ignores_wr and weak and weak in attacker.card.types:
                dmg *= 2
            if not ignores_wr and target.card.resistance and target.card.resistance in attacker.card.types:
                dmg -= 30
            ignores_eff = atk.ignores_effects if atk else False
            if "EX_IMMUNE" in S(target.card).passives and attacker.card.is_rule_box and not ignores_eff \
                    and self.abilities_on(target, def_pl):
                return 0
        dmg = max(0, dmg)
        target.damage += dmg
        return dmg

    def check_knockouts(self, attacker_side: int | None = None) -> None:
        """Resolve all Knock Outs; the opposing player takes Prizes."""
        for pl in self.players:
            for mon in list(pl.in_play()):
                if mon.damage < self.max_hp(mon):
                    continue
                if "DURABLE_BODY" in S(mon.card).passives and mon.damage < self.max_hp(mon) + 999 and self.rng.random() < 0.5 \
                        and attacker_side is not None and attacker_side != pl.idx:
                    mon.damage = self.max_hp(mon) - 10
                    continue
                self.knock_out(pl, mon)
        for pl in self.players:
            if self.winner is not None:
                return
            if pl.active is None:
                if not pl.bench:
                    self.end(1 - pl.idx, "no Pokemon in play")
                    return
                self.agents[pl.idx].promote(self, pl)

    def knock_out(self, pl: Player, mon: Mon) -> None:
        taker = self.opp(pl.idx)
        prizes = mon.card.prize_liability
        if any(S(e).tool.get("prize_minus") for e in mon.energy) and not pl.legacy_used:
            prizes -= 1
            pl.legacy_used = True
        if mon.tool and S(mon.tool).tool.get("prize_minus") and mon.card.name.startswith("Lillie's"):
            prizes -= 1
        if getattr(self, "_extra_prize", False):
            prizes += 1
        if mon is pl.active:
            pl.active = None
        else:
            pl.bench.remove(mon)
        pl.discard += mon.stack + mon.energy + ([mon.tool] if mon.tool else [])
        pl.ko_on_turn = self.turn
        self.events.append((self.turn, pl.idx, f"KO:{mon.card.name}:{prizes}"))
        for _ in range(max(0, prizes)):
            if taker.prizes:
                taker.hand.append(taker.prizes.pop())
        if not taker.prizes:
            self.end(taker.idx, "took all Prizes")

    def end(self, winner: int, reason: str) -> None:
        if self.winner is None:
            self.winner = winner
            self.end_reason = reason

    # ------------------------------------------------------------------ flow
    def setup(self) -> None:
        mulligans = [0, 0]
        for pl in self.players:
            pl.deck = list(pl.decklist)
            while True:
                self.shuffle(pl)
                pl.hand = [pl.deck.pop() for _ in range(7)]
                if any(c.supertype == "Pokémon" and c.stage == 0 for c in pl.hand) or \
                        any("FOSSIL_BASIC" in c.tags for c in pl.hand):
                    break
                pl.deck += pl.hand
                pl.hand = []
                mulligans[pl.idx] += 1
                if mulligans[pl.idx] > 20:
                    raise ValueError("deck has no Basic Pokemon")
        for pl in self.players:
            self.agents[pl.idx].setup(self, pl)
            pl.prizes = [pl.deck.pop() for _ in range(6)]
        for pl in self.players:
            extra = mulligans[1 - pl.idx]
            if extra:
                self.draw(pl, extra)
        self.snapshot("setup")

    def play(self) -> int | None:
        self.setup()
        while self.winner is None and self.turn < MAX_PLIES:
            self.turn += 1
            pl = self.players[self.current]
            pl.supporter_used = pl.energy_attached = pl.retreated = pl.stadium_played = False
            pl.buffs = []
            pl.once_names = set()
            if not pl.deck:
                self.end(1 - pl.idx, "deck out")
                break
            self.draw(pl, 1)
            if self.verbose:
                self.note(pl, "HAND " + ", ".join(sorted(c.name for c in pl.hand)) + " | BOARD " +
                          "; ".join(f"{m.card.name}({m.damage}dmg,{len(m.energy)}E)" for m in pl.in_play()))
            if self.turn == 2:
                self.snapshot("start_second_turn1")
            self.agents[pl.idx].take_turn(self, pl)
            if self.winner is not None:
                break
            for m in pl.in_play():
                for e in list(m.energy):
                    if S(e).tool.get("discard_end_of_turn"):
                        m.energy.remove(e)
                        pl.discard.append(e)
            pl.turns_taken += 1
            self.snapshot("end_turn")
            self.current = 1 - self.current
        if self.winner is None:
            a, b = self.players
            if a.prizes_left != b.prizes_left:
                self.winner = 0 if a.prizes_left < b.prizes_left else 1
                self.end_reason = "ply cap (fewer prizes left)"
            else:
                self.end_reason = "draw"
        return self.winner

    def snapshot(self, tag: str) -> None:
        a, b = self.players
        self.trace.append({
            "tag": tag, "ply": self.turn, "mover": self.current,
            "prizes": (a.prizes_left, b.prizes_left),
            "in_play": (len(a.in_play()), len(b.in_play())),
            "hand": (len(a.hand), len(b.hand)),
            "deck": (len(a.deck), len(b.deck)),
            "ready": (sum(1 for m in a.in_play() if any(self.can_use_attack(m, at, a) and at.base + 1 > 0 for at in S(m.card).attacks)),
                      sum(1 for m in b.in_play() if any(self.can_use_attack(m, at, b) and at.base + 1 > 0 for at in S(m.card).attacks))),
        })


# ---------------------------------------------------------------------------
# Card-spec matching
# ---------------------------------------------------------------------------

def matches_spec(c: CompiledCard, spec: dict[str, Any]) -> bool:
    k = spec.get("kind")
    if k == "any":
        return True
    if k == "pokemon":
        return c.supertype == "Pokémon" and card_matches_filter(c, spec.get("filter") or {})
    if k in ("energy", "basic_energy"):
        if c.supertype != "Energy":
            return False
        if k == "basic_energy" and "BASIC_ENERGY" not in c.tags:
            return False
        return not spec.get("etype") or c.primary_energy_type == spec["etype"]
    if c.supertype != "Trainer":
        return False
    if k == "trainer":
        return True
    sub = {"item": "Item", "tool": "Pokémon Tool", "supporter": "Supporter", "stadium": "Stadium"}[k]
    if sub not in c.subtypes:
        return False
    if spec.get("team_rocket") and "Team Rocket" not in c.name:
        return False
    return True


# ---------------------------------------------------------------------------
# Greedy policy (identical for every deck)
# ---------------------------------------------------------------------------

class GreedyAgent:
    """
    Plays each turn by repeatedly taking the best available transition:
    develop (abilities, search, bench, evolve, draw/search Supporter), attach, then pick
    the attack line with the best state delta (Prizes taken - Prizes given + damage
    progress), including gusting, switching, and popping self-KO bombers.
    """

    # ---- deck understanding ----
    def _profile(self, g: Game, pl: Player) -> dict[str, Any]:
        key = "_prof"
        if hasattr(pl, key):
            return getattr(pl, key)
        names = {c.name for c in pl.decklist}
        evo_from = {c.name: c.evolves_from for c in pl.decklist if c.supertype == "Pokémon"}
        value: dict[str, float] = {}
        for c in pl.decklist:
            if c.supertype != "Pokémon":
                continue
            best = 0.0
            for a in c.attacks:
                best = max(best, a.expected_damage + 0.5 * a.bench_spread_damage)
            value[c.name] = best
        # attacker lines: Pokemon whose best attack is a real threat
        attackers = sorted((n for n, v in value.items() if v >= 110), key=lambda n: -value[n])
        line_names: set[str] = set()
        for n in attackers + [c.name for c in pl.decklist if c.supertype == "Pokémon" and S(c).ability]:
            cur = n
            while cur:
                line_names.add(cur)
                cur = evo_from.get(cur)
        prof = {"names": names, "evo_from": evo_from, "value": value, "attackers": attackers, "line": line_names,
                "hns_attack": any("if_hns" in [m["mod"] for a in S(c).attacks for m in a.mods] for c in pl.decklist)}
        setattr(pl, key, prof)
        return prof

    def card_value(self, g: Game, pl: Player, c: CompiledCard) -> float:
        """How much we'd like to have `c` in hand right now (for search/discard decisions)."""
        prof = self._profile(g, pl)
        in_play = [m.card.name for m in pl.in_play()]
        hand_names = [x.name for x in pl.hand]
        if c.supertype == "Pokémon":
            v = 1.0 + prof["value"].get(c.name, 0) / 100.0
            if c.name in prof["line"]:
                v += 1.0
            if c.stage >= 1:
                # an evolution is great when its pre-evolution is in play
                if any(m.card.name == c.evolves_from for m in pl.in_play()):
                    v += 2.5
                else:
                    v -= 1.0
            elif c.name in prof["line"] and in_play.count(c.name) == 0:
                v += 1.5
            if S(c).ability:
                v += 0.8
            if c.is_rule_box and prof["value"].get(c.name, 0) < 110:
                v -= 0.5
            v -= 0.6 * hand_names.count(c.name)
            if "HIDE_N_SNEAK" in S(c).passives and prof["hns_attack"]:
                v -= 1.5   # these want to be discarded
            return v
        if c.supertype == "Energy":
            need = self._energy_need(g, pl)
            return 0.6 + (1.5 if need else 0.0) - 0.3 * sum(1 for x in pl.hand if x.supertype == "Energy")
        sc = S(c)
        kind = sc.trainer["kind"] if sc.trainer else "ITEM"
        v = 1.0
        if kind == "SUPPORTER":
            v += 1.0 - 0.5 * sum(1 for x in pl.hand if "Supporter" in x.subtypes)
        if c.name == "Rare Candy":
            v += 1.0 if any(x.stage == 2 for x in pl.hand) else 0.0
        return v

    def _energy_need(self, g: Game, pl: Player) -> bool:
        for m in pl.in_play():
            for a in S(m.card).attacks:
                if missing_units(g.attack_cost(m, a, pl), g.units(m, pl)) > 0 and (a.base > 0 or a.mods or a.snipe):
                    return True
        return False

    def choose_from(self, g: Game, pl: Player, options: list[CompiledCard], purpose: str = "hand") -> CompiledCard | None:
        if not options:
            return None
        if purpose == "bench":
            options = [o for o in options if o.supertype == "Pokémon" and o.stage == 0]
            if not options:
                return None
        return max(options, key=lambda c: self.card_value(g, pl, c) + g.rng.random() * 1e-3)

    def choose_discards(self, g: Game, pl: Player, n: int, exclude: CompiledCard | None = None) -> list[CompiledCard]:
        pool = [c for c in pl.hand if c is not exclude]
        pool.sort(key=lambda c: self.card_value(g, pl, c))
        return pool[:n]

    # ---- setup ----
    def setup(self, g: Game, pl: Player) -> None:
        basics = [c for c in pl.hand if (c.supertype == "Pokémon" and c.stage == 0) or "FOSSIL_BASIC" in c.tags]
        poke_basics = [c for c in basics if c.supertype == "Pokémon"] or basics

        def start_score(c: CompiledCard) -> float:
            sc = 0.0
            sc -= 0.8 * c.retreat_cost
            sc -= 1.5 * (c.prize_liability - 1) if c.supertype == "Pokémon" else 0
            if any(len(a.cost) <= 1 and (a.printed_damage > 0 or a.is_item_lock) for a in c.attacks):
                sc += 1.0
            if S(c).ability and S(c).ability.get("trigger") == "bench":
                sc -= 3.0
            return sc
        act = max(poke_basics, key=start_score)
        pl.hand.remove(act)
        pl.active = Mon([fossil_as_pokemon(act)] if act.supertype != "Pokémon" else [act], entered_turn=0)
        for c in sorted([b for b in pl.hand if b.supertype == "Pokémon" and b.stage == 0], key=lambda c: -self.card_value(g, pl, c)):
            if len(pl.bench) >= 5:
                break
            sc = S(c)
            if sc.ability and sc.ability.get("trigger") == "bench":
                continue
            if c.is_rule_box and self._profile(g, pl)["value"].get(c.name, 0) < 110 and sc.ability and sc.ability.get("after_ko"):
                continue
            pl.hand.remove(c)
            pl.bench.append(Mon([c], entered_turn=0))

    def promote(self, g: Game, pl: Player) -> None:
        best = max(pl.bench, key=lambda m: self._readiness(g, pl, m))
        pl.bench.remove(best)
        pl.active = best

    def _readiness(self, g: Game, pl: Player, m: Mon) -> float:
        best = 0.0
        for a in S(m.card).attacks:
            miss = missing_units(g.attack_cost(m, a, pl), g.units(m, pl))
            dmg = self.expected_damage(g, pl, m, a, None)
            best = max(best, dmg / 100.0 - 0.8 * miss)
        return best - 0.4 * (m.card.prize_liability - 1) - 0.2 * g.retreat_cost(m, pl) + (m.card.hp - m.damage) / 400.0

    def on_bench_trigger(self, g: Game, pl: Player, mon: Mon, ab: dict[str, Any]) -> None:
        if ab["kind"] == "search":
            self.do_search(g, pl, ab["search"])
        elif ab["kind"] == "stadium_discard" and g.stadium and g.stadium_owner != pl.idx:
            g.players[g.stadium_owner].discard.append(g.stadium)
            g.stadium = None
        elif ab["kind"] == "switch_in" and pl.active and self._readiness(g, pl, mon) > self._readiness(g, pl, pl.active):
            if ab.get("move_energy"):
                for m in pl.in_play():
                    if m is not mon:
                        mon.energy += m.energy
                        m.energy = []
            g.switch_active(pl, mon)

    # ---- generic operations ----
    def do_search(self, g: Game, pl: Player, sr: dict[str, Any], from_cards: list[CompiledCard] | None = None) -> list[CompiledCard]:
        src = pl.deck if from_cards is None else from_cards
        found: list[CompiledCard] = []
        specs = sr["specs"]
        if sr.get("mode") == "or":
            best_spec, best_v = None, -1e9
            for sp in specs:
                cands = [c for c in src if matches_spec(c, sp)]
                if cands:
                    v = max(self.card_value(g, pl, c) for c in cands)
                    if v > best_v:
                        best_spec, best_v = sp, v
            specs = [best_spec] if best_spec else []
        if sr.get("mode") == "combo":
            n = specs[0]["n"] if specs else 0
            for _ in range(n):
                cands = [c for c in src if any(matches_spec(c, sp) for sp in specs) and c not in found]
                c = self.choose_from(g, pl, cands, purpose=sr.get("dest", "hand"))
                if c:
                    found.append(c)
        else:
            for sp in specs:
                for _ in range(sp.get("n", 1)):
                    cands = [c for c in src if matches_spec(c, sp) and c not in found]
                    c = self.choose_from(g, pl, cands, purpose=sr.get("dest", "hand"))
                    if c:
                        found.append(c)
        dest = sr.get("dest", "hand")
        if dest == "top" and any(any(e["eff"] == "copy_topdeck" for e in x.effects) for m in pl.in_play() for x in S(m.card).attacks):
            opp = g.opp(pl.idx)
            src_now = [c for c in src if c not in found] + found
            pokes = sorted([c for c in src_now if c.supertype == "Pokémon" and not c.is_rule_box],
                           key=lambda c: -max((x.base + (x.snipe or {}).get("amount", 0) for x in S(c).attacks), default=0))
            found = pokes[:len(found)] or found
        for c in found:
            src.remove(c)
            if dest == "bench":
                if len(pl.bench) < g.bench_limit(pl):
                    g.put_on_bench(pl, c, from_hand=False)
                else:
                    pl.hand.append(c)
            elif dest == "top":
                pl.deck.append(c)
            else:
                pl.hand.append(c)
        if from_cards is None and dest != "top":
            g.shuffle(pl)
        elif dest == "top":
            tops = found
            for c in tops:
                pl.deck.remove(c)
            g.shuffle(pl)
            pl.deck += tops
            if tops:
                pl.known_top = tops[-1]
        return found

    def look_top(self, g: Game, pl: Player, n: int, take: int, specs: list[dict[str, Any]], rest: str) -> None:
        n = min(n, len(pl.deck))
        top = pl.deck[len(pl.deck) - n:]
        del pl.deck[len(pl.deck) - n:]
        chosen: list[CompiledCard] = []
        for _ in range(take):
            cands = [c for c in top if c not in chosen and any(matches_spec(c, sp) for sp in specs)]
            c = self.choose_from(g, pl, cands)
            if c:
                chosen.append(c)
        for c in chosen:
            top.remove(c)
            pl.hand.append(c)
        if rest == "discard":
            pl.discard += top
        elif rest == "bottom":
            pl.deck[:0] = top
        else:
            pl.deck += top
            g.shuffle(pl)

    # ---- turn ----
    def take_turn(self, g: Game, pl: Player) -> None:
        for _ in range(6):
            changed = False
            changed |= self._use_abilities(g, pl)
            changed |= self._bench_basics(g, pl)
            changed |= self._evolve(g, pl)
            changed |= self._play_items(g, pl)
            changed |= self._play_stadium(g, pl)
            if not pl.supporter_used:
                changed |= self._maybe_development_supporter(g, pl)
            if g.winner is not None:
                return
            if not changed:
                break
        self._attach_tools(g, pl)
        self._attack_phase(g, pl)

    def _items_ok(self, g: Game, pl: Player) -> bool:
        return pl.item_locked_turn != g.turn

    def _use_abilities(self, g: Game, pl: Player) -> bool:
        changed = False
        for m in list(pl.in_play()):
            sc = S(m.card)
            ab = sc.ability
            if not ab or ab.get("trigger") != "once" or m.ability_used_turn == g.turn or not g.abilities_on(m, pl):
                continue
            if ab["name"] in pl.once_names:
                continue
            if ab.get("active_only") and m is not pl.active:
                continue
            if ab.get("after_ko") and pl.ko_on_turn != g.turn - 1:
                continue
            if ab.get("needs_festival_active") and not (pl.active and "FESTIVAL_LEAD" in S(pl.active.card).passives):
                continue
            k = ab["kind"]
            used = False
            if k == "draw":
                if ab.get("shuffle_self") and len(pl.hand) >= 5:
                    continue
                if ab.get("discard_cost"):
                    if not pl.hand:
                        continue
                    d = self.choose_discards(g, pl, 1)
                    for c in d:
                        pl.hand.remove(c)
                        pl.discard.append(c)
                g.draw(pl, ab["n"])
                used = True
                if ab.get("shuffle_self"):
                    self._shuffle_mon_into_deck(g, pl, m)
            elif k == "look_top":
                if pl.deck:
                    self.look_top(g, pl, ab["n"], ab["take"], ab["specs"], "bottom")
                    used = True
            elif k == "search":
                if pl.deck:
                    self.do_search(g, pl, ab["search"])
                    used = True
            elif k == "attach_hand":
                cands = [c for c in pl.hand if "BASIC_ENERGY" in c.tags and (not ab.get("etype") or c.primary_energy_type == ab["etype"])]
                if cands:
                    tgt = m if ab.get("self_only") else self._best_energy_target(g, pl, cands[0])
                    if tgt:
                        g.attach_energy(pl, tgt, cands[0])
                        tgt.damage = max(0, tgt.damage - ab.get("heal", 0))
                        g.draw(pl, ab.get("draw", 0))
                        used = True
            elif k == "attach_discard":
                cands = [c for c in pl.discard if "BASIC_ENERGY" in c.tags]
                if cands:
                    tgt = self._best_energy_target(g, pl, cands[0])
                    if tgt:
                        pl.discard.remove(cands[0])
                        tgt.energy.append(cands[0])
                        used = True
            elif k == "metal_maker":
                top = pl.deck[-ab["n"]:]
                del pl.deck[-ab["n"]:]
                for c in [c for c in top if "BASIC_ENERGY" in c.tags and c.primary_energy_type == ab["etype"]]:
                    top.remove(c)
                    tgt = self._best_energy_target(g, pl, c)
                    (tgt.energy if tgt else pl.discard).append(c)
                pl.deck[:0] = top
                used = True
            if used:
                g.note(pl, f"ability {ab['name']} ({m.card.name})")
                m.ability_used_turn = g.turn
                pl.once_names.add(ab["name"])
                changed = True
        return changed

    def _shuffle_mon_into_deck(self, g: Game, pl: Player, m: Mon) -> None:
        cards = m.stack + m.energy + ([m.tool] if m.tool else [])
        if m is pl.active:
            if not pl.bench:
                return
            pl.active = None
            self.promote(g, pl)
        else:
            pl.bench.remove(m)
        pl.deck += cards
        g.shuffle(pl)

    def _bench_basics(self, g: Game, pl: Player) -> bool:
        changed = False
        prof = self._profile(g, pl)
        if self._items_ok(g, pl):
            for c in [c for c in pl.hand if "FOSSIL_BASIC" in c.tags]:
                if len(pl.bench) >= g.bench_limit(pl) or not any(x.evolves_from == c.name for x in pl.decklist):
                    break
                pl.hand.remove(c)
                pl.bench.append(Mon([fossil_as_pokemon(c)], entered_turn=g.turn))
                changed = True
        for c in sorted([c for c in pl.hand if c.supertype == "Pokémon" and c.stage == 0], key=lambda c: -self.card_value(g, pl, c)):
            if len(pl.bench) >= g.bench_limit(pl):
                break
            if c not in pl.hand:
                continue
            sc = S(c)
            # keep extra copies of non-line Pokemon in hand when the bench is filling up
            useful = c.name in prof["line"] or prof["value"].get(c.name, 0) >= 110 or sc.ability is not None
            if not useful and len(pl.bench) >= 3:
                continue
            if sc.ability and sc.ability.get("after_ko") and c.is_rule_box and pl.ko_on_turn != g.turn - 1:
                continue
            if "HIDE_N_SNEAK" in sc.passives and prof["hns_attack"]:
                continue
            g.put_on_bench(pl, c)
            changed = True
        return changed

    def _evolve(self, g: Game, pl: Player) -> bool:
        changed = False
        for c in sorted([c for c in pl.hand if c.supertype == "Pokémon" and c.stage >= 1], key=lambda c: -c.stage):
            if c not in pl.hand:
                continue
            targets = [m for m in pl.in_play() if g.can_evolve(pl, m, c)]
            if targets:
                tgt = max(targets, key=lambda m: (m is pl.active, -m.damage))
                g.evolve(pl, tgt, c)
                changed = True
        # Rare Candy
        if self._items_ok(g, pl) and pl.turns_taken >= 1:
            for rc in [c for c in pl.hand if S(c).trainer and any(o["op"] == "rare_candy" for o in S(c).trainer["ops"])]:
                for st2 in [c for c in pl.hand if c.stage == 2]:
                    s1 = st2.evolves_from
                    root = self._profile(g, pl)["evo_from"].get(s1) or g_root(pl, s1)
                    tg = [m for m in pl.in_play() if m.card.stage == 0 and m.card.name == root and m.entered_turn < g.turn]
                    if tg and rc in pl.hand and st2 in pl.hand:
                        pl.hand.remove(rc)
                        pl.discard.append(rc)
                        g.evolve(pl, tg[0], st2)
                        changed = True
                        break
        return changed

    def _play_stadium(self, g: Game, pl: Player) -> bool:
        if pl.stadium_played:
            return False
        for c in pl.hand:
            if "Stadium" not in c.subtypes:
                continue
            if g.stadium is not None and g.stadium.name == c.name:
                continue
            flags = S(c).stadium
            if not flags or flags & {"watchtower", "jamming_tower", "gravity_mountain", "nighttime_mine", "risky_ruins"}:
                # hate stadiums: only play over an opponent's stadium or onto an empty field late
                if g.stadium is not None and g.stadium_owner == pl.idx:
                    continue
            if g.stadium is not None:
                g.players[g.stadium_owner].discard.append(g.stadium)
            pl.hand.remove(c)
            g.stadium, g.stadium_owner = c, pl.idx
            pl.stadium_played = True
            if "lumiose" in flags and len(pl.bench) < g.bench_limit(pl) and pl.turns_taken == 0:
                pass
            return True
        return False

    def _play_items(self, g: Game, pl: Player) -> bool:
        if not self._items_ok(g, pl):
            return False
        changed = False
        for c in list(pl.hand):
            if c not in pl.hand or "Item" not in c.subtypes:
                continue
            sc = S(c)
            if not sc.trainer or not sc.trainer["ops"]:
                continue
            ops = sc.trainer["ops"]
            kinds = {o["op"] for o in ops}
            if kinds & {"gust", "switch", "dmg_buff", "rare_candy", "modal_switch"}:
                continue  # handled in the attack phase / evolution
            if not self._conditions_ok(g, pl, c):
                continue
            if not self._worth_playing(g, pl, c, ops):
                continue
            if self._play_trainer(g, pl, c):
                changed = True
        return changed

    def _conditions_ok(self, g: Game, pl: Player, c: CompiledCard) -> bool:
        conds = set()
        for v in c.action_conditions.values():
            conds |= set(v)
        opp = g.opp(pl.idx)
        for cond in conds:
            if cond == "BEHIND_ON_PRIZES" and not pl.prizes_left > opp.prizes_left:
                return False
            if cond == "AFTER_OWN_KO" and pl.ko_on_turn != g.turn - 1:
                return False
            if cond == "OPP_PRIZES_LE_3" and opp.prizes_left > 3:
                return False
            if cond == "OPP_PRIZES_LE_2" and opp.prizes_left > 2:
                return False
            if cond == "OPP_PRIZES_EQ_2" and opp.prizes_left != 2:
                return False
            if cond == "LAST_CARD_IN_HAND" and len(pl.hand) != 1:
                return False
            if cond == "NOT_FIRST_TURN" and pl.turns_taken == 0:
                return False
        for r in c.requirements:
            if r["filter"].get("tera") and not any("Tera" in m.card.subtypes for m in pl.in_play()):
                return False
        return True

    def _worth_playing(self, g: Game, pl: Player, c: CompiledCard, ops: list[dict[str, Any]]) -> bool:
        opp = g.opp(pl.idx)
        cost = S(c).trainer["discard_cost"]
        if cost and len(pl.hand) - 1 < cost:
            return False
        for o in ops:
            op = o["op"]
            if op == "search":
                if not pl.deck:
                    return False
                if o["dest"] == "bench" and len(pl.bench) >= g.bench_limit(pl):
                    return False
                cands = [x for x in pl.deck if any(matches_spec(x, sp) for sp in o["specs"])]
                if not cands:
                    return False
                best = max(self.card_value(g, pl, x) for x in cands)
                worst_discard = sum(self.card_value(g, pl, x) for x in self.choose_discards(g, pl, cost, exclude=c)) if cost else 0
                return best >= 2.0 + 0.6 * worst_discard
            if op == "look_top":
                return len(pl.deck) > 0 and not (any(sp["kind"] == "supporter" for sp in o["specs"]) and any("Supporter" in x.subtypes for x in pl.hand))
            if op == "recover":
                return any(x.supertype == "Pokémon" or "BASIC_ENERGY" in x.tags for x in pl.discard) and \
                    max((self.card_value(g, pl, x) for x in pl.discard if x.supertype == "Pokémon"), default=0) >= 2.0
            if op == "reset_both":
                # symmetric reset: good when our hand is small or theirs is big
                return len(pl.hand) - 1 <= o["me"] or len(opp.hand) >= o["opp"] + 4
            if op == "opp_bottom_draw":
                return len(opp.hand) >= 4
            if op == "hammer":
                return any(m.energy for m in opp.in_play())
            if op == "heal":
                a = pl.active
                return a is not None and a.damage >= 50 and len(a.energy) >= o.get("min_energy", 0)
            if op == "attach_discard":
                return any("BASIC_ENERGY" in x.tags for x in pl.discard) and self._attach_targets(g, pl, o)
            if op == "energy_switch":
                return False
            if op in ("draw", "draw_to", "discard_hand_draw"):
                return len(pl.hand) <= 4
            if op == "tool_scrap":
                return any(m.tool for m in opp.in_play())
        return True

    def _attach_targets(self, g: Game, pl: Player, o: dict[str, Any]) -> list[Mon]:
        out = []
        for m in pl.in_play():
            if o.get("bench_only") and m is pl.active:
                continue
            if o.get("filter") and not card_matches_filter(m.card, o["filter"]):
                continue
            out.append(m)
        return out

    def _play_trainer(self, g: Game, pl: Player, c: CompiledCard) -> bool:
        sc = S(c)
        tr = sc.trainer
        if tr["discard_cost"]:
            if len(pl.hand) - 1 < tr["discard_cost"]:
                return False
            for d in self.choose_discards(g, pl, tr["discard_cost"], exclude=c):
                pl.hand.remove(d)
                pl.discard.append(d)
        pl.hand.remove(c)
        g.note(pl, f"play {c.name}")
        if tr["kind"] == "SUPPORTER":
            pl.supporter_used = True
        opp = g.opp(pl.idx)
        for o in tr["ops"]:
            op = o["op"]
            if op == "shuffle_draw":
                pl.deck += pl.hand
                pl.hand = []
                g.shuffle(pl)
                n = o["alt"][1] if o.get("alt") and pl.prizes_left == o["alt"][0] else o["n"]
                g.draw(pl, n)
            elif op == "reset_both":
                for who, n in ((pl, o["me"]), (opp, o["opp"])):
                    who.deck += who.hand
                    who.hand = []
                    g.shuffle(who)
                    g.draw(who, n)
            elif op == "opp_bottom_draw":
                if opp.hand:
                    opp.deck[:0] = opp.hand
                    opp.hand = []
                    g.draw(opp, o["n"])
            elif op == "opp_discard_to":
                while len(opp.hand) > o["n"]:
                    d = min(opp.hand, key=lambda x: g.agents[opp.idx].card_value(g, opp, x))
                    opp.hand.remove(d)
                    opp.discard.append(d)
            elif op == "both_discard_to":
                for who in (opp, pl):
                    while len(who.hand) > o["n"]:
                        d = min(who.hand, key=lambda x: g.agents[who.idx].card_value(g, who, x))
                        who.hand.remove(d)
                        who.discard.append(d)
            elif op == "eri":
                items = sorted([x for x in opp.hand if "Item" in x.subtypes], key=lambda x: -g.agents[opp.idx].card_value(g, opp, x))[:o["n"]]
                for x in items:
                    opp.hand.remove(x)
                    opp.discard.append(x)
            elif op == "discard_hand_draw":
                pl.discard += pl.hand
                pl.hand = []
                g.draw(pl, o["n"])
            elif op == "gwynn":
                ds = [x for x in pl.hand if x.supertype == "Pokémon" and not x.is_rule_box]
                ds.sort(key=lambda x: self.card_value(g, pl, x))
                ds = ds[:2]
                for x in ds:
                    pl.hand.remove(x)
                    pl.discard.append(x)
                g.draw(pl, 3 * len(ds))
            elif op == "draw_to":
                g.draw(pl, max(0, o["n"] - len(pl.hand)))
            elif op == "draw":
                g.draw(pl, o["n"])
            elif op == "look_top":
                self.look_top(g, pl, o["n"], o["take"], o["specs"], o["rest"])
            elif op == "search":
                self.do_search(g, pl, o)
            elif op == "crispin":
                types_seen = []
                for x in sorted([x for x in pl.deck if "BASIC_ENERGY" in x.tags], key=lambda x: -self._energy_fit(g, pl, x)):
                    if x.primary_energy_type not in [t.primary_energy_type for t in types_seen]:
                        types_seen.append(x)
                    if len(types_seen) == 2:
                        break
                if types_seen:
                    first = types_seen[0]
                    pl.deck.remove(first)
                    tgt = self._best_energy_target(g, pl, first)
                    (tgt.energy if tgt else pl.hand).append(first)
                if len(types_seen) > 1:
                    pl.deck.remove(types_seen[1])
                    pl.hand.append(types_seen[1])
                g.shuffle(pl)
            elif op == "janine":
                for m in [m for m in pl.in_play() if "Darkness" in m.card.types][:2]:
                    e = next((x for x in pl.deck if "BASIC_ENERGY" in x.tags and x.primary_energy_type == "Darkness"), None)
                    if e:
                        pl.deck.remove(e)
                        m.energy.append(e)
                g.shuffle(pl)
            elif op == "attach_discard":
                tgts = self._attach_targets(g, pl, o)
                pool = [x for x in pl.discard if "BASIC_ENERGY" in x.tags and (not o.get("etype") or x.primary_energy_type == o["etype"])]
                if o.get("each"):
                    for m in tgts[:o["n"]]:
                        if pool:
                            e = pool.pop()
                            pl.discard.remove(e)
                            m.energy.append(e)
                elif tgts and pool:
                    tgt = max(tgts, key=lambda m: self._energy_gain(g, pl, m))
                    for e in sorted(pool, key=lambda e: -self._energy_fit_mon(g, pl, tgt, e))[:o["n"]]:
                        pl.discard.remove(e)
                        tgt.energy.append(e)
            elif op == "recover":
                for _ in range(o["n"]):
                    cands = [x for x in pl.discard if (("pokemon" in o["kinds"] and x.supertype == "Pokémon" and not (o.get("non_rule_box") and x.is_rule_box))
                                                         or ("basic_energy" in o["kinds"] and "BASIC_ENERGY" in x.tags))]
                    x = self.choose_from(g, pl, cands)
                    if not x:
                        break
                    pl.discard.remove(x)
                    (pl.deck if o["dest"] == "deck" else pl.hand).append(x)
                if o["dest"] == "deck":
                    g.shuffle(pl)
            elif op == "heal":
                tgt = pl.active if o["target"] == "active" else max(pl.in_play(), key=lambda m: m.damage)
                if tgt and len(tgt.energy) >= o.get("min_energy", 0):
                    tgt.damage = max(0, tgt.damage - o["n"])
            elif op == "hammer":
                if not o["coin"] or g.rng.random() < 0.5:
                    tg = [m for m in opp.in_play() if m.energy and (not o["special_only"] or any("SPECIAL_ENERGY" in e.tags for e in m.energy))]
                    if tg:
                        m = opp.active if opp.active in tg else tg[0]
                        e = next((e for e in m.energy if "SPECIAL_ENERGY" in e.tags), m.energy[0]) if o["special_only"] or True else m.energy[0]
                        m.energy.remove(e)
                        opp.discard.append(e)
            elif op == "tool_scrap":
                for m in [m for m in opp.in_play() if m.tool][:2]:
                    opp.discard.append(m.tool)
                    m.tool = None
            elif op == "dmg_buff":
                pl.buffs.append(o)
            elif op == "move_bench_to_active" and pl.active:
                moved = 0
                for m in pl.bench:
                    while m.energy and moved < o["n"]:
                        pl.active.energy.append(m.energy.pop())
                        moved += 1
            elif op in ("gust", "switch", "modal_switch"):
                pass  # executed by the attack planner
        pl.discard.append(c)
        return True

    def _energy_fit(self, g: Game, pl: Player, e: CompiledCard) -> float:
        return max((self._energy_fit_mon(g, pl, m, e) for m in pl.in_play()), default=0.0)

    def _energy_fit_mon(self, g: Game, pl: Player, m: Mon, e: CompiledCard) -> float:
        best = 0.0
        units = g.units(m, pl)
        ab = S(m.card).ability
        if ab and ab.get("needs_energy") and ab["needs_energy"] in energy_units(e, m.card)                 and not any(ab["needs_energy"] in energy_units(x, m.card) for x in m.energy):
            best = 1.6   # switches on an Ability (Munkidori Adrena-Brain needs Darkness Energy)
        for a in S(m.card).attacks:
            cost = g.attack_cost(m, a, pl)
            before = missing_units(cost, units)
            after = missing_units(cost, units + energy_units(e, m.card))
            if after < before:
                best = max(best, (before - after) + self.expected_damage(g, pl, m, a, None) / 150.0)
        return best

    def _energy_gain(self, g: Game, pl: Player, m: Mon) -> float:
        best = 0.0
        for a in S(m.card).attacks:
            miss = missing_units(g.attack_cost(m, a, pl), g.units(m, pl))
            if miss:
                best = max(best, self.expected_damage(g, pl, m, a, None) / 100.0 / miss)
        return best

    def _can_reach_active(self, g: Game, pl: Player) -> float:
        """How reliably a benched Pokemon can be brought Active (retreat now, switch cards, free retreat)."""
        a = pl.active
        if a is None:
            return 1.0
        if g.retreat_cost(a, pl) <= len(a.energy) and a.cant_retreat_turn != g.turn:
            return 1.0
        if any(S(c).trainer and any(o["op"] in ("switch", "modal_switch") for o in S(c).trainer["ops"]) for c in pl.hand):
            return 0.9
        return 0.35   # only if the Active gets Knocked Out first

    def _best_energy_target(self, g: Game, pl: Player, e: CompiledCard) -> Mon | None:
        reach = self._can_reach_active(g, pl)
        cands = []
        for i, m in enumerate(pl.in_play()):
            fit = self._energy_fit_mon(g, pl, m, e)
            if m is pl.active:
                fit += 0.3
                # energy that pays for a retreat out of a non-attacking Active also has value
                if g.retreat_cost(m, pl) > len(m.energy) and not any(self.expected_damage(g, pl, m, a, None) > 0
                                                                      and missing_units(g.attack_cost(m, a, pl), g.units(m, pl)) <= 1
                                                                      for a in S(m.card).attacks):
                    fit = max(fit, 0.8)
            else:
                fit *= reach
            cands.append((fit, -i, m))
        cands = [c for c in cands if c[0] > 0]
        if not cands:
            return None
        return max(cands, key=lambda c: (c[0], c[1]))[2]

    def _maybe_development_supporter(self, g: Game, pl: Player) -> bool:
        if pl.turns_taken == 0 and g.first == pl.idx:
            if not any(S(c).trainer and S(c).trainer.get("first_turn_ok") for c in pl.hand):
                return False
        supps = [c for c in pl.hand if "Supporter" in c.subtypes and S(c).trainer]
        if not supps:
            return False
        # Reserve the Supporter if an attack plan needs one (Boss's Orders KO, Black Belt, Rosa)
        plan_with = self.best_plan(g, pl, allow_supporter=True)
        plan_without = self.best_plan(g, pl, allow_supporter=False)
        if plan_with and plan_with["uses_supporter"] and plan_with["value"] > (plan_without["value"] if plan_without else 0) + 0.5:
            return False
        best, best_v = None, 0.6
        for c in supps:
            if not self._conditions_ok(g, pl, c):
                continue
            v = self._supporter_value(g, pl, c)
            if v > best_v:
                best, best_v = c, v
        if best:
            return self._play_trainer(g, pl, best)
        return False

    def _supporter_value(self, g: Game, pl: Player, c: CompiledCard) -> float:
        opp = g.opp(pl.idx)
        v = 0.0
        hand = len(pl.hand) - 1
        for o in S(c).trainer["ops"]:
            op = o["op"]
            if op == "shuffle_draw":
                n = o["alt"][1] if o.get("alt") and pl.prizes_left == o["alt"][0] else o["n"]
                v += (n - hand) * 0.5
            elif op == "reset_both":
                v += (o["me"] - hand) * 0.45 + (len(opp.hand) - o["opp"]) * 0.35
            elif op == "draw":
                v += o["n"] * 0.45
            elif op == "draw_to":
                v += (o["n"] - hand) * 0.45
            elif op == "discard_hand_draw":
                v += (o["n"] - hand) * 0.5
            elif op == "gwynn":
                v += 1.3 * min(2, sum(1 for x in pl.hand if x.supertype == "Pokémon" and not x.is_rule_box))
            elif op == "search":
                cands = [x for x in pl.deck if any(matches_spec(x, sp) for sp in o["specs"])]
                if cands:
                    tops = sorted((self.card_value(g, pl, x) for x in cands), reverse=True)[:sum(sp.get("n", 1) for sp in o["specs"])]
                    v += sum(max(0.0, t - 1.5) for t in tops) * 0.6
            elif op == "look_top":
                v += 0.8
            elif op in ("crispin", "janine"):
                v += 1.2 if self._energy_need(g, pl) else 0.2
            elif op == "attach_discard":
                tg = self._attach_targets(g, pl, o)
                if tg and any("BASIC_ENERGY" in x.tags for x in pl.discard):
                    v += 1.0 + max(self._energy_gain(g, pl, m) for m in tg)
            elif op == "opp_discard_to":
                v += max(0, len(opp.hand) - o["n"]) * 0.45
            elif op == "eri":
                v += 0.4 * sum(1 for x in opp.hand if "Item" in x.subtypes)
            elif op == "recover":
                v += 0.8 if any(x.supertype == "Pokémon" for x in pl.discard) else 0.0
            elif op == "heal":
                v += (pl.active.damage / 100.0) if pl.active else 0.0
        return v

    def _attach_tools(self, g: Game, pl: Player) -> None:
        if not self._items_ok(g, pl):
            return
        for c in [c for c in pl.hand if "Pokémon Tool" in c.subtypes]:
            t = S(c).tool
            cands = [m for m in pl.in_play() if m.tool is None]
            if not cands:
                return
            if "dmg" in t:
                cands = [m for m in cands if card_matches_filter(m.card, t["dmg"]["filter"])]
                tgt = max(cands, key=lambda m: (m is pl.active, self._profile(g, pl)["value"].get(m.card.name, 0)), default=None)
            elif "hp" in t:
                tgt = max(cands, key=lambda m: (self._profile(g, pl)["value"].get(m.card.name, 0) + 50 * (m is pl.active)), default=None)
            elif "retreat_minus" in t:
                tgt = max(cands, key=lambda m: (m is pl.active, m.card.retreat_cost), default=None)
                if tgt and tgt.card.retreat_cost == 0:
                    tgt = None
            else:
                tgt = None
            if tgt:
                pl.hand.remove(c)
                tgt.tool = c

    # ---- attack planning: transitions with explicit state deltas ----
    def expected_damage(self, g: Game, pl: Player, m: Mon, a: AttackScript, target: Mon | None,
                        extra_buffs: list[dict[str, Any]] | None = None, rng: random.Random | None = None) -> float:
        opp = g.opp(pl.idx)
        dmg = float(a.base)
        if a.snipe:
            dmg = float(a.snipe["amount"])
        if a.fallback_damage is not None and not a.mods:
            dmg = a.fallback_damage
        for md in a.mods:
            k = md["mod"]
            per = md.get("per", 0)
            if k == "per_hand":
                dmg += per * max(0, len(pl.hand))
            elif k == "per_bench_both":
                dmg += per * (len(pl.bench) + len(opp.bench))
            elif k == "per_my_bench":
                dmg += per * len(pl.bench)
            elif k == "per_energy_both_active":
                dmg += per * (len(m.energy) + (len(opp.active.energy) if opp.active else 0))
            elif k == "per_energy_opp_active":
                dmg += per * (len(opp.active.energy) if opp.active else 0)
            elif k == "per_my_grass_energy":
                dmg += per * sum(u == "Grass" for x in pl.in_play() for u in g.units(x, pl))
            elif k == "per_energy_self":
                dmg += per * len(m.energy)
            elif k == "per_opp_prizes_taken":
                dmg += per * (6 - opp.prizes_left)   # Prizes the OPPONENT has taken (comeback scaling)
            elif k == "per_self_counter":
                dmg += per * (m.damage // 10)
            elif k == "per_opp_ex":
                dmg += per * sum(1 for x in opp.in_play() if "ex" in x.card.subtypes)
            elif k == "per_my_basic":
                dmg += per * sum(1 for x in pl.in_play() if x.card.stage == 0)
            elif k == "coin_until_tails":
                if rng:
                    while rng.random() < 0.5:
                        dmg += per
                else:
                    dmg += per
            elif k == "coins":
                n = md.get("n", 1)
                if rng:
                    dmg += per * sum(1 for _ in range(n) if rng.random() < 0.5)
                else:
                    dmg += per * n * 0.5
            elif k == "tails_nothing":
                if rng and rng.random() < 0.5:
                    return 0.0
                if not rng:
                    dmg *= 0.5
            elif k == "if_moved_in":
                if m.moved_in_turn == g.turn or getattr(m, "_planned_move_in", False):
                    dmg += per
            elif k == "if_opp_ex":
                t = target or opp.active
                if t and "ex" in t.card.subtypes:
                    dmg += per
            elif k == "if_stadium":
                if g.stadium:
                    dmg += per
            elif k == "if_ko_last":
                if pl.ko_on_turn == g.turn - 1:
                    dmg += per
            elif k == "if_hns":
                if sum(1 for x in pl.discard if "HIDE_N_SNEAK" in S(x).passives) >= md.get("need", 4):
                    dmg += per
            elif k == "if_extra_energy":
                if len(g.units(m, pl)) - len(a.cost) >= 2:
                    dmg += per
            elif k == "if_same_type":
                if {t for x in pl.in_play() for t in x.card.types} & {t for x in opp.in_play() for t in x.card.types}:
                    dmg += per
            elif k == "if_opp_type":
                t = target or opp.active
                if t and md.get("ptype") in t.card.types:
                    dmg += per
            elif k == "optional_discard_boost":
                if len(m.energy) >= len(a.cost) + 0:
                    dmg += per
            elif k == "discard_any_energy":
                dmg += per * sum(1 for x in pl.in_play() for e in x.energy if "BASIC_ENERGY" in e.tags)
            elif k == "needs_partner":
                if not any(x.card.name == md["name"] for x in pl.bench):
                    return 0.0
        for e in a.effects:
            if e["eff"] == "copy_topdeck":
                # Seek Inspiration copies the TOP card of the deck: known if we stacked it
                # (Academy at Night / Ciphermaniac), otherwise the deck-composition average.
                if not pl.deck:
                    return 0.0
                def _copy_val(c: CompiledCard) -> float:
                    if c.supertype != "Pokémon" or c.is_rule_box:
                        return 0.0
                    return max((self.expected_damage(g, pl, m, x, target, extra_buffs, None) for x in S(c).attacks
                                if not any(ef["eff"] == "copy_topdeck" for ef in x.effects)), default=0.0)
                if getattr(pl, "known_top", None) is pl.deck[-1]:
                    dmg = _copy_val(pl.deck[-1])
                else:
                    vals = [_copy_val(c) for c in pl.deck]
                    dmg = sum(vals) / len(vals)
            elif e["eff"] == "copy_bench":
                best = 0.0
                for x in pl.bench:
                    if e.get("owner") and not x.card.name.lower().startswith(e["owner"]):
                        continue
                    for a2 in S(x.card).attacks:
                        if any(ef["eff"] == "copy_bench" for ef in a2.effects):
                            continue
                        best = max(best, self.expected_damage(g, pl, m, a2, target, extra_buffs, rng))
                dmg = best
        if a.kind == "counters":
            return dmg
        if dmg > 0:
            dmg += self._bonus(g, pl, m, a, target or opp.active, extra_buffs)
        return dmg

    def _bonus(self, g: Game, pl: Player, m: Mon, a: AttackScript, target: Mon | None, extra: list[dict[str, Any]] | None) -> float:
        bonus = 0.0
        is_ex_target = bool(target and "ex" in target.card.subtypes)
        sources = list(pl.buffs) + list(extra or [])
        if m.tool and "dmg" in S(m.tool).tool and "jamming_tower" not in g.stadium_flags():
            sources.append(S(m.tool).tool["dmg"])
        for b in sources:
            if b.get("vs_ex") and not is_ex_target:
                continue
            f = dict(b.get("filter") or {})
            f.pop("direct_attacker", None)
            if f and not card_matches_filter(m.card, f):
                continue
            bonus += b["amount"]
        aura = S(m.card)
        for x in pl.in_play():
            sx = S(x.card)
            if "ATTACK_AURA" in sx.passives and x is not m and g.abilities_on(x, pl):
                word = sx.tool["aura"]["word"]
                if word.capitalize() in m.card.subtypes or m.card.name.lower().startswith(word) or word.capitalize() in m.card.types:
                    bonus += sx.tool["aura"]["amount"]
        return bonus

    def _gust_sources(self, g: Game, pl: Player, allow_supporter: bool) -> list[tuple[str, CompiledCard]]:
        out = []
        can_supp = allow_supporter and not pl.supporter_used and not (pl.turns_taken == 0 and g.first == pl.idx)
        for c in pl.hand:
            tr = S(c).trainer
            if not tr:
                continue
            ops = {o["op"] for o in tr["ops"]}
            if "gust" in ops:
                if tr["kind"] == "SUPPORTER" and can_supp:
                    out.append(("supporter", c))
                elif tr["kind"] == "ITEM" and self._items_ok(g, pl):
                    out.append(("item", c))
        return out

    def _switch_sources(self, g: Game, pl: Player, allow_supporter: bool) -> list[tuple[str, CompiledCard | None]]:
        out: list[tuple[str, CompiledCard | None]] = []
        if pl.active and not pl.retreated and pl.active.cant_retreat_turn != g.turn:
            if g.retreat_cost(pl.active, pl) <= len(pl.active.energy):
                out.append(("retreat", None))
        can_supp = allow_supporter and not pl.supporter_used and not (pl.turns_taken == 0 and g.first == pl.idx)
        for c in pl.hand:
            tr = S(c).trainer
            if not tr:
                continue
            ops = {o["op"] for o in tr["ops"]}
            if ("switch" in ops or "modal_switch" in ops) and "gust" not in ops:   # Prime Catcher is a gust source
                if tr["kind"] == "ITEM" and self._items_ok(g, pl):
                    out.append(("item", c))
                elif tr["kind"] == "SUPPORTER" and can_supp:
                    out.append(("supporter", c))
        return out

    def best_plan(self, g: Game, pl: Player, allow_supporter: bool = True) -> dict[str, Any] | None:
        """
        Enumerate attack transitions: (attacker [after switching]) x (target [after gusting])
        x (energy attachment) x (self-KO bombers popped) x (damage buffs). Each is scored by its
        state delta: Prizes taken - Prizes given up + partial damage progress - resources spent.
        """
        opp = g.opp(pl.idx)
        if pl.active is None or opp.active is None:
            return None
        if pl.turns_taken == 0 and g.first == pl.idx:
            return None
        energy_cards = [c for c in pl.hand if c.supertype == "Energy"] if not pl.energy_attached else []
        gusts = [(None, None)] + self._gust_sources(g, pl, allow_supporter)
        switches = [(None, None)] + self._switch_sources(g, pl, allow_supporter)
        bombers = [m for m in pl.in_play() if S(m.card).ability and S(m.card).ability["kind"] == "bomber"
                   and m.ability_used_turn != g.turn and g.abilities_on(m, pl)] if not g.damp_in_play() else []
        buff_supps = [c for c in pl.hand if S(c).trainer and S(c).trainer["kind"] == "SUPPORTER"
                      and any(o["op"] == "dmg_buff" for o in S(c).trainer["ops"]) and self._conditions_ok(g, pl, c)]
        buff_items = [c for c in pl.hand if S(c).trainer and S(c).trainer["kind"] == "ITEM"
                      and any(o["op"] == "dmg_buff" for o in S(c).trainer["ops"])] if self._items_ok(g, pl) else []
        can_supp = allow_supporter and not pl.supporter_used
        plans: list[dict[str, Any]] = []
        for sw_kind, sw_card in switches:
            attackers = [pl.active] if sw_kind is None else list(pl.bench)
            for att in attackers:
                if sw_kind == "retreat" and att is pl.active:
                    continue
                for gk, gcard in gusts:
                    if gk == "supporter" and sw_kind == "supporter":
                        continue
                    targets = [opp.active] if gk is None else list(opp.bench)
                    for tgt in targets:
                        for e_card in [None] + energy_cards[:3]:
                            units = g.units(att, pl) + (energy_units(e_card, att.card) if e_card else [])
                            if sw_kind == "retreat":
                                pass
                            for a in S(att.card).attacks:
                                if att.cant_attack_until > g.turn:
                                    continue
                                if not can_pay(g.attack_cost(att, a, pl), units):
                                    continue
                                buffs: list[dict[str, Any]] = []
                                used_supp = gk == "supporter" or sw_kind == "supporter"
                                for bi in buff_items:
                                    buffs += [o for o in S(bi).trainer["ops"] if o["op"] == "dmg_buff"]
                                if buff_supps and can_supp and not used_supp:
                                    bs = buff_supps[0]
                                    buffs_s = buffs + [o for o in S(bs).trainer["ops"] if o["op"] == "dmg_buff"]
                                else:
                                    bs, buffs_s = None, buffs
                                for use_supp_buff in ([False, True] if bs else [False]):
                                    bb = buffs_s if use_supp_buff else buffs
                                    att._planned_move_in = sw_kind is not None
                                    dmg = self.expected_damage(g, pl, att, a, tgt, extra_buffs=bb)
                                    att._planned_move_in = False
                                    for n_bomb in range(0, min(2, len(bombers)) + 1):
                                        p = self._score_plan(g, pl, opp, att, a, tgt, dmg, bombers[:n_bomb], gk is not None)
                                        cost = 0.0
                                        cost += 0.15 if gk == "supporter" else (0.35 if gk == "item" else 0.0)
                                        cost += {None: 0.0, "retreat": 0.12 * g.retreat_cost(pl.active, pl), "item": 0.08, "supporter": 0.2}[sw_kind]
                                        cost += 0.1 if use_supp_buff else 0.0
                                        plans.append({
                                            "value": p["value"] - cost, "attacker": att, "attack": a, "target": tgt,
                                            "switch": (sw_kind, sw_card), "gust": (gk, gcard), "energy": e_card,
                                            "bombers": bombers[:n_bomb], "supp_buff": bs if use_supp_buff else None,
                                            "uses_supporter": gk == "supporter" or sw_kind == "supporter" or use_supp_buff,
                                            "ko": p["ko"],
                                        })
        if not plans:
            return None
        return max(plans, key=lambda x: x["value"])

    def _score_plan(self, g: Game, pl: Player, opp: Player, att: Mon, a: AttackScript, tgt: Mon,
                    dmg: float, bombers: list[Mon], gusted: bool) -> dict[str, Any]:
        hp_left = g.max_hp(tgt) - tgt.damage
        eff = dmg
        if a.kind != "counters" and tgt is opp.active:
            weak = tgt.card.weakness
            if "FAIRY_ZONE" in g.passives(pl) and "Dragon" in tgt.card.types:
                weak = "Psychic"
            if not a.ignores_wr and weak and weak in att.card.types:
                eff *= 2
            if not a.ignores_wr and tgt.card.resistance and tgt.card.resistance in att.card.types:
                eff -= 30
            if "EX_IMMUNE" in S(tgt.card).passives and att.card.is_rule_box and not a.ignores_effects:
                eff = 0
        if a.snipe and tgt is not opp.active and "BENCH_SAFE" in S(tgt.card).passives:
            eff = 0
        if "FESTIVAL_LEAD" in S(att.card).passives and "festival" in g.stadium_flags() and g.abilities_on(att, pl):
            eff = eff * 2 if eff < hp_left else eff   # attacks twice (second hit on the next Active after a KO)
        bomb = sum(10 * S(b.card).ability["counters"] for b in bombers)
        if "HIDE_N_SNEAK" in S(tgt.card).passives:
            bomb = 0
        given = sum(b.card.prize_liability for b in bombers)
        if bombers and len(pl.in_play()) - len(bombers) < 1:
            return {"value": -99, "ko": False}
        ko = eff + bomb >= hp_left
        prizes = tgt.card.prize_liability if ko else 0
        if ko and bombers and eff >= hp_left:
            # bombers wasted if the attack already KOs
            return {"value": -5, "ko": True}
        value = prizes - 1.05 * given
        if ko and prizes >= opp.prizes_left:
            value += 10.0    # game-winning transition
        if given and given >= pl.prizes_left:
            value -= 20.0
        if not ko:
            # damage progress toward a 2-hit KO is real (if partial) value
            value += 0.45 * tgt.card.prize_liability * min(1.0, (eff + bomb) / max(1.0, hp_left))
        # spread side-effects resolve as real transitions: bench Knock Outs are Prizes
        value += self._spread_prizes(g, pl, opp, a, exclude=tgt)
        # keep threatening attackers safe: penalize attackers with a self lock
        if any(e["eff"] == "self_lock" for e in a.effects):
            value -= 0.1
        return {"value": value, "ko": ko}

    def _spread_prizes(self, g: Game, pl: Player, opp: Player, a: AttackScript, exclude: Mon | None) -> float:
        """Expected Prize value of an attack's bench damage / bench counters (greedy allocation)."""
        cage = "battle_cage" in g.stadium_flags()
        shield = "SPHERICAL_SHIELD" in g.passives(opp)
        curtain = "FLOWER_CURTAIN" in g.passives(opp)
        value = 0.0
        for e in a.effects:
            if e["eff"] == "bench_counters":
                if cage or shield:
                    continue
                budget = e["n"]
                bench = [m for m in opp.bench if m is not exclude and "BENCH_SAFE" not in S(m.card).passives
                         and "HIDE_N_SNEAK" not in S(m.card).passives]
                bench.sort(key=lambda m: (g.max_hp(m) - m.damage) / max(1, m.card.prize_liability))
                for m in bench:
                    need = (g.max_hp(m) - m.damage + 9) // 10
                    if need <= budget and (e["split"] or need <= e["n"]):
                        value += m.card.prize_liability
                        budget -= need
                        if not e["split"]:
                            break
                if bench:
                    value += 0.02 * budget
            elif e["eff"] == "bench_damage":
                bench = [m for m in opp.bench if m is not exclude and "BENCH_SAFE" not in S(m.card).passives
                         and not shield and not (curtain and not m.card.is_rule_box)]
                bench.sort(key=lambda m: g.max_hp(m) - m.damage)
                for m in bench[:e["targets"]]:
                    if g.max_hp(m) - m.damage <= e["amount"]:
                        value += m.card.prize_liability
                    else:
                        value += 0.1
        return value

    def _attack_phase(self, g: Game, pl: Player) -> None:
        opp = g.opp(pl.idx)
        plan = self.best_plan(g, pl, allow_supporter=True)
        if plan is None or plan["value"] <= 0.0 and not self._any_attack_value(plan):
            self._generic_attach(g, pl)
            self._setup_retreat(g, pl)
            # a weak attack still beats passing
            plan = self.best_plan(g, pl, allow_supporter=False)
            if plan is None:
                return
        # execute the transition sequence
        gk, gcard = plan["gust"]
        if gk and gcard in pl.hand:
            self._play_gust(g, pl, gcard, plan["target"])
        sk, scard = plan["switch"]
        if sk == "retreat" and plan["attacker"] in pl.bench:
            self._retreat_to(g, pl, plan["attacker"])
        elif sk in ("item", "supporter") and scard in pl.hand and plan["attacker"] in pl.bench:
            pl.hand.remove(scard)
            pl.discard.append(scard)
            if sk == "supporter":
                pl.supporter_used = True
            g.switch_active(pl, plan["attacker"])
            if S(scard).trainer and any(o["op"] == "draw_to" for o in S(scard).trainer["ops"]):
                g.draw(pl, max(0, 5 - len(pl.hand)))
        if plan["energy"] is not None and plan["energy"] in pl.hand and not pl.energy_attached:
            g.attach_energy(pl, plan["attacker"], plan["energy"])
            pl.energy_attached = True
        if not pl.energy_attached:
            self._generic_attach(g, pl)
        if plan["supp_buff"] is not None and plan["supp_buff"] in pl.hand and not pl.supporter_used:
            self._play_trainer(g, pl, plan["supp_buff"])
        if self._items_ok(g, pl):
            for c in [c for c in pl.hand if S(c).trainer and S(c).trainer["kind"] == "ITEM" and any(o["op"] == "dmg_buff" for o in S(c).trainer["ops"])]:
                if plan["attack"].kind != "counters":
                    self._play_trainer(g, pl, c)
        # Munkidori-style counter movers (free value)
        self._adrena(g, pl)
        if g.winner is not None or opp.active is None:
            return
        for b in plan["bombers"]:
            if b in pl.in_play() and plan["target"] in opp.in_play():
                g.place_counters(opp, plan["target"], S(b.card).ability["counters"], from_attack=False)
                b.ability_used_turn = g.turn
                g.events.append((g.turn, pl.idx, f"BOMB:{b.card.name}"))
                b.damage = g.max_hp(b)
                g.check_knockouts()
                if g.winner is not None:
                    return
        if pl.active is None or opp.active is None:
            return
        att = pl.active
        a = plan["attack"] if plan["attacker"] is att else None
        if a is None or not g.can_use_attack(att, a, pl):
            cands = [x for x in S(att.card).attacks if g.can_use_attack(att, x, pl)]
            if not cands:
                return
            a = max(cands, key=lambda x: self.expected_damage(g, pl, att, x, opp.active))
        self.execute_attack(g, pl, att, a)

    def _any_attack_value(self, plan: dict[str, Any] | None) -> bool:
        return bool(plan and plan["value"] > -1)

    def _play_gust(self, g: Game, pl: Player, c: CompiledCard, target: Mon) -> None:
        opp = g.opp(pl.idx)
        tr = S(c).trainer
        pl.hand.remove(c)
        pl.discard.append(c)
        if tr["kind"] == "SUPPORTER":
            pl.supporter_used = True
        if target in opp.bench:
            opp.bench.remove(target)
            if opp.active:
                opp.bench.append(opp.active)
            opp.active = target
        if any(o["op"] == "switch" for o in tr["ops"]) and pl.bench:
            best = max(pl.bench, key=lambda m: self._readiness(g, pl, m))
            if self._readiness(g, pl, best) > self._readiness(g, pl, pl.active):
                g.switch_active(pl, best)

    def _retreat_to(self, g: Game, pl: Player, new: Mon) -> None:
        a = pl.active
        cost = g.retreat_cost(a, pl)
        for _ in range(cost):
            if not a.energy:
                break
            e = min(a.energy, key=lambda e: 0 if e.primary_energy_type in (None, "Colorless") else 1)
            a.energy.remove(e)
            pl.discard.append(e)
        pl.retreated = True
        g.switch_active(pl, new)

    def _setup_retreat(self, g: Game, pl: Player) -> None:
        """Nothing to attack with: retreat into a better-developed Pokemon if it's cheap."""
        if not pl.active or not pl.bench or pl.retreated or pl.active.cant_retreat_turn == g.turn:
            return
        best = max(pl.bench, key=lambda m: self._readiness(g, pl, m))
        if self._readiness(g, pl, best) > self._readiness(g, pl, pl.active) + 0.5 and g.retreat_cost(pl.active, pl) <= min(1, len(pl.active.energy)):
            self._retreat_to(g, pl, best)

    def _generic_attach(self, g: Game, pl: Player) -> None:
        if pl.energy_attached:
            return
        es = [c for c in pl.hand if c.supertype == "Energy"]
        best = None
        for e in es:
            if "can only be attached to" in e.rules_text.lower() and not any(m.card.name.startswith("Team Rocket's") for m in pl.in_play()):
                continue
            tgt = self._best_energy_target(g, pl, e)
            if tgt:
                sc = self._energy_fit_mon(g, pl, tgt, e) + (0.3 if tgt is pl.active else 0)
                if best is None or sc > best[0]:
                    best = (sc, e, tgt)
        if best:
            g.attach_energy(pl, best[2], best[1])
            pl.energy_attached = True

    def _adrena(self, g: Game, pl: Player) -> None:
        opp = g.opp(pl.idx)
        if "WATCHFUL_EYE" in g.passives(pl) | g.passives(opp):
            return
        for m in pl.in_play():
            ab = S(m.card).ability
            if not ab or ab["kind"] != "adrena" or m.ability_used_turn == g.turn or not g.abilities_on(m, pl):
                continue
            if ab.get("needs_energy") and not any(ab["needs_energy"] in energy_units(e, m.card) for e in m.energy):
                continue
            src = max(pl.in_play(), key=lambda x: x.damage)
            if src.damage <= 0 or opp.active is None:
                continue
            n = min(ab["counters"], src.damage // 10)
            tgt = self._best_counter_target(g, opp, n)
            placed = g.place_counters(opp, tgt, n, from_attack=False)
            if placed:
                src.damage -= placed
                m.ability_used_turn = g.turn
        g.check_knockouts()

    def _best_counter_target(self, g: Game, opp: Player, n: int) -> Mon:
        cands = opp.in_play()
        kos = [m for m in cands if g.max_hp(m) - m.damage <= 10 * n]
        if kos:
            return max(kos, key=lambda m: m.card.prize_liability)
        return opp.active

    def execute_attack(self, g: Game, pl: Player, att: Mon, a: AttackScript, second: bool = False) -> None:
        opp = g.opp(pl.idx)
        if not second:
            self._stack_top_for_copy(g, pl, att, a)
        tgt = opp.active
        g.events.append((g.turn, pl.idx, f"ATK:{att.card.name}:{a.name}"))
        g.note(pl, f"ATTACK {att.card.name} {a.name} -> {tgt.card.name}")
        dmg = self.expected_damage(g, pl, att, a, tgt, rng=g.rng)
        # discard-for-damage choices
        for md in a.mods:
            if md["mod"] == "discard_any_energy":
                need = max(0, g.max_hp(tgt) - tgt.damage)
                n = 0
                for x in pl.in_play():
                    for e in list(x.energy):
                        if "BASIC_ENERGY" in e.tags and n * md["per"] < need:
                            x.energy.remove(e)
                            pl.discard.append(e)
                            n += 1
                dmg = n * md["per"] + self._bonus(g, pl, att, a, tgt, None)
            if md["mod"] == "optional_discard_boost":
                if g.max_hp(tgt) - tgt.damage > dmg - md["per"]:
                    for _ in range(md["n"]):
                        if att.energy:
                            pl.discard.append(att.energy.pop())
                else:
                    dmg -= md["per"]
        if any(e["eff"] == "copy_topdeck" for e in a.effects) and pl.deck:
            top = pl.deck.pop()
            pl.discard.append(top)
            dmg = 0.0
            if top.supertype == "Pokémon" and not top.is_rule_box:
                cands = [x for x in S(top).attacks if not any(ef["eff"] == "copy_topdeck" for ef in x.effects)]
                if cands:
                    a = max(cands, key=lambda x: self.expected_damage(g, pl, att, x, tgt))
                    dmg = self.expected_damage(g, pl, att, a, tgt, rng=g.rng)
            g.events.append((g.turn, pl.idx, f"COPY:{top.name}:{a.name}"))
        if any(e["eff"] == "extra_prize" for e in a.effects):
            g._extra_prize = True
        if a.snipe:
            n_t = a.snipe["n_targets"]
            pool = [m for m in opp.in_play() if not (a.snipe["bench_only"] and m is opp.active)
                    and not (a.snipe["ex_only"] and "ex" not in m.card.subtypes)]
            pool.sort(key=lambda m: (g.max_hp(m) - m.damage <= a.snipe["amount"], m.card.prize_liability, m is opp.active), reverse=True)
            for m in pool[:n_t]:
                g.attack_damage_to(pl, att, opp, m, a.snipe["amount"] + (self._bonus(g, pl, att, a, m, None) if m is opp.active else 0), a)
        elif a.kind == "counters":
            if dmg > 0:
                g.place_counters(opp, tgt, int(dmg // 10), from_attack=True)
        else:
            g.attack_damage_to(pl, att, opp, tgt, dmg, a)
        for e in a.effects:
            k = e["eff"]
            if k == "bench_counters":
                self._spread_counters(g, opp, e["n"], e["split"])
            elif k == "bench_damage":
                if e.get("cost_shuffle_energy"):
                    if len(att.energy) < e["cost_shuffle_energy"]:
                        continue
                    for _ in range(e["cost_shuffle_energy"]):
                        pl.deck.append(att.energy.pop())
                    g.shuffle(pl)
                for m in sorted(opp.bench, key=lambda m: g.max_hp(m) - m.damage)[:e["targets"]]:
                    g.attack_damage_to(pl, att, opp, m, e["amount"], a)
            elif k == "counters_all":
                if sum(1 for x in pl.discard if "HIDE_N_SNEAK" in S(x).passives) >= e.get("need_hns", 0):
                    for m in opp.in_play():
                        g.place_counters(opp, m, e["n"] // 10, from_attack=True)
            elif k == "item_lock":
                opp.item_locked_turn = g.turn + 1
            elif k == "no_retreat":
                tgt.cant_retreat_turn = g.turn + 1
            elif k == "self_lock":
                att.cant_attack_until = g.turn + 3
            elif k == "discard_self_energy":
                pl.discard += att.energy
                att.energy = []
            elif k == "return_energy" and att.energy:
                pl.hand.append(att.energy.pop())
            elif k == "recoil":
                att.damage += e.get("n") or 0
            elif k == "draw":
                g.draw(pl, e.get("n") or 1)
            elif k == "discard_hand_draw":
                pl.discard += pl.hand
                pl.hand = []
                g.draw(pl, e.get("n") or 6)
            elif k == "search":
                self.do_search(g, pl, e["search"])
            elif k == "mill":
                for _ in range(e.get("n") or 1):
                    if opp.deck:
                        opp.discard.append(opp.deck.pop())
            elif k == "push_out" and opp.bench and opp.active is tgt:
                g.agents[opp.idx].promote_swap(g, opp)
            elif k == "double_ko":
                att.damage = g.max_hp(att)
                tgt.damage = g.max_hp(tgt)
            elif k == "attach_from":
                src = pl.discard if e["src"] == "discard" else pl.deck
                for _ in range(e.get("n") or 1):
                    en = next((x for x in src if "BASIC_ENERGY" in x.tags and (not e.get("etype") or x.primary_energy_type == e["etype"])), None)
                    if not en:
                        break
                    src.remove(en)
                    tm = self._best_energy_target(g, pl, en) or att
                    tm.energy.append(en)
            elif k == "revive_to_bench":
                for _ in range(e.get("n") or 1):
                    x = next((x for x in pl.discard if x.supertype == "Pokémon" and x.stage == 0 and x.name.lower().startswith((e.get("name") or "")[:5])), None)
                    if not x or len(pl.bench) >= g.bench_limit(pl):
                        break
                    pl.discard.remove(x)
                    g.put_on_bench(pl, x, from_hand=False)
            elif k == "recover_poke":
                x = self.choose_from(g, pl, [x for x in pl.discard if x.supertype == "Pokémon"])
                if x:
                    pl.discard.remove(x)
                    pl.hand.append(x)
            elif k == "ascension":
                evo = next((x for x in pl.deck if x.evolves_from == att.card.name), None)
                if evo:
                    pl.deck.remove(evo)
                    g.evolve(pl, att, evo, from_hand=False)
                    g.shuffle(pl)
            elif k == "self_switch" and pl.bench:
                best = max(pl.bench, key=lambda m: self._readiness(g, pl, m))
                g.switch_active(pl, best)
            elif k == "tuck_self":
                pass
        g.check_knockouts(attacker_side=pl.idx)
        g._extra_prize = False
        if (not second and g.winner is None and pl.active is att and opp.active is not None
                and "FESTIVAL_LEAD" in S(att.card).passives and "festival" in g.stadium_flags()
                and g.abilities_on(att, pl) and g.can_use_attack(att, a, pl)):
            g.note(pl, "Festival Lead: attack again")
            self.execute_attack(g, pl, att, a, second=True)

    def _stack_top_for_copy(self, g: Game, pl: Player, att: Mon, a: AttackScript) -> None:
        """Academy at Night: put the best copy target from hand on top before Seek Inspiration."""
        if not any(e["eff"] == "copy_topdeck" for e in a.effects):
            return
        if "academy" not in g.stadium_flags() or getattr(pl, "academy_turn", -1) == g.turn:
            return
        cands = [c for c in pl.hand if c.supertype == "Pokémon" and not c.is_rule_box]
        if not cands:
            return
        opp = g.opp(pl.idx)
        best = max(cands, key=lambda c: max((self.expected_damage(g, pl, att, x, opp.active) for x in S(c).attacks
                                             if not any(ef["eff"] == "copy_topdeck" for ef in x.effects)), default=0.0))
        pl.hand.remove(best)
        pl.deck.append(best)
        pl.known_top = best
        pl.academy_turn = g.turn
        g.note(pl, f"Academy at Night: {best.name} on top")

    def _spread_counters(self, g: Game, opp: Player, n: int, split: bool) -> None:
        bench = [m for m in opp.bench if "BENCH_SAFE" not in S(m.card).passives]
        if not bench:
            return
        if not split:
            tgt = min(bench, key=lambda m: (g.max_hp(m) - m.damage > 10 * n, -m.card.prize_liability))
            g.place_counters(opp, tgt, n, from_attack=True)
            return
        left = n
        for m in sorted(bench, key=lambda m: (g.max_hp(m) - m.damage, -m.card.prize_liability)):
            need = (g.max_hp(m) - m.damage + 9) // 10
            if need <= left:
                g.place_counters(opp, m, need, from_attack=True)
                left -= need
        if left > 0:
            g.place_counters(opp, bench[0] if bench[0] in opp.bench else opp.bench[0], left, from_attack=True)

    def promote_swap(self, g: Game, pl: Player) -> None:
        old = pl.active
        pl.active = None
        self.promote(g, pl)
        if old:
            pl.bench.append(old)


def fossil_as_pokemon(card: CompiledCard) -> CompiledCard:
    """Restored-Pokemon fossil Items are played as 60-HP Basic Colorless Pokemon."""
    import copy as _copy
    c = _copy.copy(card)
    c.supertype = "Pokémon"
    c.stage = 0
    c.hp = 60
    c.types = ["Colorless"]
    c.prize_liability = 1
    c.attacks = []
    c.uid = card.uid + "#fossil"
    return c


def g_root(pl: Player, s1_name: str) -> str | None:
    for c in pl.decklist:
        if c.name == s1_name:
            return c.evolves_from
    return None
