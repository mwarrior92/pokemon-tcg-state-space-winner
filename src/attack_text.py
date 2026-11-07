"""
Attack-text compiler: one parser for what an attack does, shared by the engine bridge (exact values on the
real board) and the card compiler (typical values for deck scoring).

parse_attack(text, base_damage, cost, attack_name, card_name) -> spec dict:
  base           printed damage
  cost           Energy cost (engine EnergyType ints, or names from the card data)
  for_each       [(n, more, phrase)]       "N (more) damage for each <phrase>"
  counters       (n, phrase) | None        "place N damage counters on your opponent's Active for each <phrase>"
  fixed_counters n | None                  "put N damage counters on your opponent's Active Pokemon"
  coins          ("each", total) | ("more", bonus) | None   coin flips at expected value
  tails_nothing  bool                      "Flip a coin. If tails, this attack does nothing."
  moved          n                         bonus if this Pokemon moved from the Bench to the Active Spot this turn
  bonus          [(n, condition)]          "If <condition>, this attack does N more damage"
  needs_bench    name | None               "If you don't have <name> on your Bench, this attack does nothing"
  needs_stadium  bool                      "If there is no Stadium in play, this attack does nothing"
  copy           ("bench", filter) | ("opp_active", "") | None   copies another attack
  snipe          n                         "does N damage to 1 (or K) of your opponent's (Benched) Pokemon";
                                           K > 1 also sets spread ("damage", N, K - 1)
  counters_any   n                         "put N damage counters on your opponent's Pokemon in any way you like"
  ko_active      bool                      "both Active Pokemon are Knocked Out" (also a self-KO drawback)
  min_bench      n                         "If you have N-1 or fewer Benched Pokemon, this attack does nothing" -> needs N
  ignore_weakness / ignore_resistance      damage isn't affected by Weakness / Resistance
  typical        [expected, max] | None    patch-only: typical damage for deck-level scoring
  spread         (kind, amount, targets)   bench damage / counters besides the main target
  bypass         bool                      damage isn't affected by effects on the opponent's Active
  drawbacks      [str]                     discard Energy, can't attack next turn, self-damage, ...
  effects        [str]                     Special Conditions, healing, Energy acceleration, draw/search, ...
  unparsed       [str]                     damage-relevant sentences none of the rules understood
Per-attack patches from src/card_patches.json are merged on top (key "Card Name|Attack Name").
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PATCH_FILE = Path(__file__).resolve().parent / "card_patches.json"
_NUM = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
_PATCHES: dict[str, dict[str, Any]] | None = None


def norm(t: str | None) -> str:
    return (t or "").lower().replace("’", "'").replace("“", '"').replace("”", '"').replace("{ex}", "ex").replace("{v}", "v").strip()


def patch_key(card_name: str, attack_name: str) -> str:
    return f"{norm(card_name)}|{norm(attack_name)}"


def patches() -> dict[str, dict[str, Any]]:
    global _PATCHES
    if _PATCHES is None:
        _PATCHES = {}
        if PATCH_FILE.exists():
            raw = json.loads(PATCH_FILE.read_text(encoding="utf-8"))
            for k, v in raw.items():
                if k.startswith("_"):
                    continue
                card, _, atk = k.partition("|")
                _PATCHES[patch_key(card, atk)] = v
    return _PATCHES


# Clauses the compiler understands. Each: (name, regex, handler(spec, match)). Matched text is consumed,
# so whatever damage-relevant text is left over is reported as `unparsed`.
def _h_for_each(sp, m):
    if "heads" not in m.group(3):
        sp["for_each"].append((int(m.group(1)), bool(m.group(2)), m.group(3)))


def _h_counters(sp, m):
    sp["counters"] = (int(m.group(1)), m.group(2))


def _h_fixed_counters(sp, m):
    sp["fixed_counters"] = int(m.group(1))


def _h_coins_each(sp, m):
    k = _NUM.get(m.group(1), int(m.group(1)) if m.group(1).isdigit() else 1)
    sp["coins"] = ("each", 0.5 * k * int(m.group(2)))


def _h_coins_more_each(sp, m):
    k = _NUM.get(m.group(1), int(m.group(1)) if m.group(1).isdigit() else 1)
    sp["coins"] = ("more", 0.5 * k * int(m.group(2)))


def _h_coins_until(sp, m):
    sp["coins"] = ("more", float(m.group(1)))


def _h_coin_heads(sp, m):
    sp["coins"] = ("more", 0.5 * float(m.group(1)))


def _h_bonus(sp, m):
    sp["bonus"].append((int(m.group(2)), m.group(1).strip()))


def _h_drawback(name):
    def h(sp, m):
        sp["drawbacks"].append(name if isinstance(name, str) else name(m))
    return h


def _h_effect(name):
    def h(sp, m):
        sp["effects"].append(name if isinstance(name, str) else name(m))
    return h


CLAUSES: list[tuple[str, str, Any]] = [
    ("bypass", r"this attack's damage isn't affected by (?:weakness or resistance, or by )?any effects on (?:your opponent's active pokémon|those pokémon)",
     lambda sp, m: sp.__setitem__("bypass", True)),
    ("copy_bench", r"choose 1 of your benched (.+?)'s attacks and use it as this attack",
     lambda sp, m: sp.__setitem__("copy", ("bench", m.group(1).replace(" pokémon", "").strip()))),
    ("copy_opp", r"choose 1 of your opponent's active pokémon's attacks and use it as this attack",
     lambda sp, m: sp.__setitem__("copy", ("opp_active", ""))),
    ("coins_each", r"flip (\w+) coins?\. this attack does (\d+) damage for each heads", _h_coins_each),
    ("coins_more_each", r"flip (\w+) coins?\. this attack does (\d+) more damage for each heads", _h_coins_more_each),
    ("coins_until", r"flip a coin until you get tails\. this attack does (\d+) more damage for each heads", _h_coins_until),
    ("coin_heads", r"flip a coin\. if heads, this attack does (\d+) more damage", _h_coin_heads),
    ("tails_nothing", r"flip a coin\. if tails, this attack does nothing", lambda sp, m: sp.__setitem__("tails_nothing", True)),
    ("counters_each", r"(?:place|put) (\d+) damage counters? on your opponent's active pokémon for each ([^.]+)", _h_counters),
    ("spread_counters", r"put (\d+) damage counters on your opponent's benched pokémon in any way you like",
     lambda sp, m: sp.__setitem__("spread", ("counters", 10.0 * int(m.group(1)), 0))),
    ("spread_counters_one", r"place (\d+) damage counters on 1 of your opponent's benched pokémon",
     lambda sp, m: sp.__setitem__("spread", ("counters_one", 10.0 * int(m.group(1)), 1))),
    ("fixed_counters", r"(?:place|put) (\d+) damage counters? on your opponent's active pokémon", _h_fixed_counters),
    ("spread_damage", r"(?:this attack also )?does (\d+) damage to (\d+|each) of your opponent's benched pokémon",
     lambda sp, m: sp.__setitem__("spread", ("damage", float(m.group(1)), 99 if m.group(2) == "each" else int(m.group(2))))),
    ("snipe_multi", r"(?:this attack )?does (\d+) damage to (\d+|two|three) of your opponent's pokémon",
     lambda sp, m: (sp.__setitem__("snipe", float(m.group(1))),
                    sp.__setitem__("spread", ("damage", float(m.group(1)),
                                              _NUM.get(m.group(2), int(m.group(2)) if m.group(2).isdigit() else 2) - 1)))),
    ("snipe", r"(?:this attack )?does (\d+) damage to 1 of your opponent's (?:benched )?pokémon",
     lambda sp, m: sp.__setitem__("snipe", float(m.group(1)))),
    ("counters_any", r"(?:put|place) (\d+) damage counters? on your opponent's pokémon in any way you like",
     lambda sp, m: sp.__setitem__("counters_any", int(m.group(1)))),
    ("optional_bonus", r"you may ([^.]+?),? (?:and )?(?:if you do, )?(?:have )?this attack (?:do|does) (\d+) more damage",
     lambda sp, m: (sp["bonus"].append((int(m.group(2)), "optional: " + m.group(1).strip())),
                    sp["drawbacks"].append("optional cost: " + m.group(1).strip()))),
    ("ko_both", r"both active pokémon are knocked out",
     lambda sp, m: (sp.__setitem__("ko_active", True), sp["drawbacks"].append("knocks itself out"))),
    ("min_bench", r"if you have (\d+) or fewer benched pokémon, this attack does nothing",
     lambda sp, m: sp.__setitem__("min_bench", int(m.group(1)) + 1)),
    ("ignore_wr_both", r"this attack's damage isn't affected by weakness or resistance",
     lambda sp, m: (sp.__setitem__("ignore_weakness", True), sp.__setitem__("ignore_resistance", True))),
    ("ignore_weak", r"this attack's damage isn't affected by weakness",
     lambda sp, m: sp.__setitem__("ignore_weakness", True)),
    ("ignore_res", r"this attack's damage isn't affected by resistance",
     lambda sp, m: sp.__setitem__("ignore_resistance", True)),
    # defensive effects mention damage but don't deal any
    ("weaken_defender", r"during your opponent's next turn, attacks used by the defending pokémon do (\d+) less damage[^.]*",
     _h_effect("defender does less damage next turn")),
    ("next_turn_bonus", r"during your next turn, this pokémon's [^.]+? attack does (\d+) more damage[^.]*",
     _h_effect(lambda m: f"+{m.group(1)} on this attack next turn")),
    ("for_each", r"(\d+) (more )?damage for each ([^.]+)", _h_for_each),
    ("moved", r"if this pokémon moved from your bench to the active spot this turn, this attack does (\d+) more damage",
     lambda sp, m: sp.__setitem__("moved", float(m.group(1)))),
    ("needs_bench", r"if you don't have ([a-z' -]+?) on your bench, this attack does nothing",
     lambda sp, m: sp.__setitem__("needs_bench", m.group(1))),
    ("needs_stadium", r"if there is no stadium in play, this attack does nothing",
     lambda sp, m: sp.__setitem__("needs_stadium", True)),
    ("bonus", r"if ([^.]+?), this attack does (\d+) more damage", _h_bonus),
    ("ignore_wr", r"(?:don't apply|isn't affected by) weakness (?:and|or) resistance", lambda sp, m: None),
    # drawbacks for the attacker
    ("discard_energy", r"discard (all|an?|\d+|1) (?:basic )?(?:\{?\w\}? )?energy (?:cards? )?(?:from|attached to) this pokémon",
     _h_drawback(lambda m: f"discard {m.group(1)} energy")),
    ("cant_attack", r"during your next turn, this pokémon can't (?:use attacks|attack|use [^.]+)", _h_drawback("can't attack next turn")),
    ("self_damage", r"this pokémon (?:also )?does (\d+) damage to itself", _h_drawback(lambda m: f"self-damage {m.group(1)}")),
    # side effects
    ("status", r"(?:your opponent's active pokémon|the defending pokémon) is now (asleep|paralyzed|confused|burned|poisoned)(?: and (\w+))?",
     _h_effect(lambda m: "status: " + m.group(1) + (" + " + m.group(2) if m.group(2) else ""))),
    ("heal", r"heal (\d+|all) damage from (?:this pokémon|1 of your pokémon|each of your pokémon)", _h_effect(lambda m: f"heal {m.group(1)}")),
    ("attach", r"attach [^.]*energy[^.]*", _h_effect("energy acceleration")),
    ("search", r"search your deck[^.]*", _h_effect("search")),
    ("draw", r"draw (?:\d+|a) cards?[^.]*", _h_effect("draw")),
    ("prevent", r"during your opponent's next turn, prevent all (?:damage|effects)[^.]*", _h_effect("protects itself next turn")),
    ("less_damage", r"during your opponent's next turn, this pokémon takes (\d+) less damage[^.]*", _h_effect("takes less damage next turn")),
    ("cant_retreat", r"during your opponent's next turn, the defending pokémon can't retreat", _h_effect("defender can't retreat")),
    ("switch_self", r"switch this pokémon with 1 of your benched pokémon", _h_effect("switch self")),
    ("gust", r"switch (?:in )?1 of your opponent's benched pokémon (?:to|with)[^.]*", _h_effect("gust")),
    ("shuffle_self", r"shuffle this pokémon and all attached cards into your deck", _h_effect("shuffle self away")),
]
_COMPILED = [(n, re.compile(rx), h) for n, rx, h in CLAUSES]
DAMAGE_WORDS = ("damage", "knocked out", "does nothing", "damage counter")


def parse_attack(text: str | None, base_damage: float | int | str | None = 0, cost: list | None = None,
                 attack_name: str = "", card_name: str = "") -> dict[str, Any]:
    t = norm(text)
    try:
        base = float(re.sub(r"[^0-9.]", "", str(base_damage or 0)) or 0)
    except ValueError:
        base = 0.0
    sp: dict[str, Any] = {"base": base, "cost": list(cost or []), "name": norm(attack_name), "for_each": [],
                          "counters": None, "fixed_counters": None, "coins": None, "tails_nothing": False, "moved": 0.0,
                          "bonus": [], "needs_bench": None, "needs_stadium": False, "copy": None, "snipe": 0.0,
                          "spread": None, "bypass": False, "drawbacks": [], "effects": [], "unparsed": [], "patched": False,
                          "counters_any": 0, "ko_active": False, "min_bench": 0, "ignore_weakness": False,
                          "ignore_resistance": False, "typical": None}
    rest = t
    for _, rx, handler in _COMPILED:
        for m in list(rx.finditer(rest)):
            handler(sp, m)
        rest = rx.sub(" ", rest)
    # leftover sentences that still talk about damage are what the rules missed
    for sentence in re.split(r"(?<=[.)])\s+", rest):
        s = sentence.strip(" .")
        if len(s) > 3 and any(w in s for w in DAMAGE_WORDS) and "weakness and resistance for benched" not in s \
                and s not in ("this attack's damage", "this damage"):
            sp["unparsed"].append(s)
    pt = patches().get(patch_key(card_name, attack_name))
    if pt:
        for k, v in pt.items():
            if k in ("note",):
                continue
            sp[k] = [tuple(x) if isinstance(x, list) else x for x in v] if k in ("for_each", "bonus") else \
                (tuple(v) if isinstance(v, list) and k in ("copy", "coins", "counters", "spread") else v)
        sp["unparsed"] = pt.get("unparsed", [])
        sp["patched"] = True
    return sp


def typical_damage(sp: dict[str, Any]) -> tuple[float, float]:
    """(expected, max) damage on a TYPICAL board, for deck-level scoring without a real position."""
    typical = {"benched": 4.0, "hand": 7.0, "prize": 3.0, "energy": 3.0, "damage counter": 6.0, "discard": 6.0,
               "ex": 1.5, "heads": 1.0}

    def count(phrase: str) -> tuple[float, float]:
        for k, v in typical.items():
            if k in phrase:
                return v, v * 1.6
        return 2.0, 4.0

    if sp.get("typical"):
        return float(sp["typical"][0]), float(sp["typical"][1])
    exp = mx = sp["base"]
    if sp.get("ko_active"):
        return 300.0, 330.0
    for n, more, phrase in sp["for_each"]:
        c, cm = count(phrase)
        if more:
            exp, mx = exp + n * c, mx + n * cm
        elif sp["base"] == 0:
            exp, mx = n * c, n * cm
    if sp["counters"]:
        c, cm = count(sp["counters"][1])
        exp, mx = exp + 10 * sp["counters"][0] * c, mx + 10 * sp["counters"][0] * cm
    if sp["fixed_counters"]:
        exp, mx = exp + 10 * sp["fixed_counters"], mx + 10 * sp["fixed_counters"]
    if sp.get("counters_any"):
        exp, mx = exp + 10 * sp["counters_any"], mx + 10 * sp["counters_any"]
    if sp["coins"]:
        kind, x = sp["coins"]
        exp, mx = (x, 2 * x) if kind == "each" else (exp + x, mx + 2 * x)
    for n, _ in sp["bonus"]:
        exp, mx = exp + 0.5 * n, mx + n
    if sp["moved"]:
        exp, mx = exp + 0.85 * sp["moved"], mx + sp["moved"]
    if sp["tails_nothing"]:
        exp *= 0.5
    if sp["snipe"]:
        exp, mx = max(exp, sp["snipe"]), max(mx, sp["snipe"])
    return exp, mx
