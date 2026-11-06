"""
Delta Reign (ME06, PTCGL code DLR, regulation J) card data, transcribed from the official
card images in PokeBeach's set guide (2026-11-06 release):
https://www.pokebeach.com/2026/10/delta-reign-set-guide-full-card-list-cut-cards-product-lineup-store-promos-and-more

Run `python build_me6.py` to (re)generate cards/me6.json in the pokemon-tcg-data schema
used by the rest of this folder. Only gameplay-distinct cards are listed: numbers 001-103 plus
129 Pokemon Catcher. The secret rares (104+) are alternate-art reprints of these, and
132-134 (Bubbly Water / Growing Grass / Nitro Fire Energy) are reprints of cards already present.
"""
from __future__ import annotations

import json
from pathlib import Path

SET_ID, SET_CODE = "me6", "DLR"
TYPE = {"G": "Grass", "R": "Fire", "W": "Water", "L": "Lightning", "P": "Psychic", "F": "Fighting",
        "D": "Darkness", "M": "Metal", "N": "Dragon", "C": "Colorless"}
EX_RULE = "Pokémon ex rule: When your Pokémon ex is Knocked Out, your opponent takes 2 Prize cards."
MEGA_RULE = "Mega Evolution ex Rule: When your Mega Evolution Pokémon ex is Knocked Out, your opponent takes 3 Prize cards."
TOOL_RULE = ("You may attach any number of Pokémon Tools to your Pokémon during your turn. "
             "You may attach only 1 Pokémon Tool to each Pokémon, and it stays attached.")
ITEM_RULE = "You may play any number of Item cards during your turn."
SUPP_RULE = "You may play only 1 Supporter card during your turn."
STAD_RULE = "You may play only 1 Stadium card during your turn. Put it next to the Active Spot, and discard it if another Stadium comes into play. A Stadium with the same name can't be played."

CARDS: list[dict] = []


def P(num, name, stage, hp, ptype, attacks=(), abilities=(), weak=None, res=None, retreat=0,
      evolves=None, ex=False, mega=False, tera=False, rules=()):
    """Pokemon. attacks: (cost letters, name, damage string, text). weak/res: type letter."""
    subtypes = [stage] + (["MEGA"] if mega else []) + (["ex"] if ex else []) + (["Tera"] if tera else [])
    card = {
        "id": f"{SET_ID}-{num}", "name": name, "supertype": "Pokémon", "subtypes": subtypes,
        "hp": str(hp), "types": [TYPE[ptype]], "number": str(num), "regulationMark": "J",
        "attacks": [{"name": n, "cost": [TYPE[c] for c in cost], "convertedEnergyCost": len(cost),
                     "damage": dmg, "text": text} for cost, n, dmg, text in attacks],
        "retreatCost": ["Colorless"] * retreat, "convertedRetreatCost": retreat,
    }
    if evolves:
        card["evolvesFrom"] = evolves
    if abilities:
        card["abilities"] = [{"name": n, "text": t, "type": "Ability"} for n, t in abilities]
    if weak:
        card["weaknesses"] = [{"type": TYPE[weak], "value": "×2"}]
    if res:
        card["resistances"] = [{"type": TYPE[res], "value": "-30"}]
    r = list(rules) + ([MEGA_RULE] if mega else ([EX_RULE] if ex else []))
    if r:
        card["rules"] = r
    CARDS.append(card)


def T(num, name, kind, text, ace=False):
    """Trainer: kind in Item / Supporter / Stadium / Pokémon Tool."""
    extra = {"Item": ITEM_RULE, "Supporter": SUPP_RULE, "Stadium": STAD_RULE, "Pokémon Tool": TOOL_RULE}[kind]
    rules = [text, extra] + (["ACE SPEC: You can't have more than 1 ACE SPEC card in your deck."] if ace else [])
    CARDS.append({"id": f"{SET_ID}-{num}", "name": name, "supertype": "Trainer",
                  "subtypes": [kind] + (["ACE SPEC"] if ace else []), "number": str(num),
                  "regulationMark": "J", "rules": rules})


# ---------------------------------------------------------------- Grass
P(1, "Heracross", "Basic", 130, "G", [
    ("G", "Spike Draw", "20", "Draw 2 cards."),
    ("GGC", "High Horsepower", "130", "This Pokémon also does 30 damage to itself."),
], weak="R", retreat=3)
P(2, "Surskit", "Basic", 50, "G", [
    ("C", "Multiply", "", "Search your deck for up to 2 Surskit and put them onto your Bench. Then, shuffle your deck."),
    ("G", "Bug Bite", "10", ""),
], weak="R", retreat=1)
P(3, "Masquerain", "Stage 1", 110, "G", [
    ("C", "Frightening Pattern", "30", "During your opponent's next turn, the Defending Pokémon can't use attacks."),
    ("G", "Bug Out", "50×", "Reveal the bottom 7 cards of your deck, and this attack does 50 damage for each Pokémon you find there that has the Bug Out attack. Then, shuffle any revealed Pokémon back into your deck. Discard the other cards."),
], weak="R", retreat=1, evolves="Surskit")
P(4, "Cacnea", "Basic", 70, "G", [
    ("C", "Knock Away", "10+", "Flip a coin. If heads, this attack does 10 more damage."),
], weak="R", retreat=2)
P(5, "Cacturne", "Stage 1", 130, "G", [
    ("C", "Linear Attack", "", "This attack does 30 damage to 1 of your opponent's Pokémon. (Don't apply Weakness and Resistance for Benched Pokémon.)"),
    ("G", "Punishing Needles", "10+", "This attack does 50 more damage for each of your opponent's Pokémon in play that has an Ability."),
], weak="R", retreat=2, evolves="Cacnea")
P(6, "Combee", "Basic", 50, "G", [
    ("G", "Fade Out", "10", "Put this Pokémon and all attached cards into your hand."),
    ("CCC", "Bug Out", "50×", "Reveal the bottom 7 cards of your deck, and this attack does 50 damage for each Pokémon you find there that has the Bug Out attack. Then, shuffle any revealed Pokémon back into your deck. Discard the other cards."),
], weak="R", retreat=1)
P(7, "Vespiquen", "Stage 1", 120, "G", [
    ("G", "Pierce", "40", ""),
    ("CCC", "Clean Hit", "80+", "If your opponent's Active Pokémon is an Evolution Pokémon, this attack does 80 more damage."),
], weak="R", retreat=1, evolves="Combee")
P(8, "Shaymin", "Basic", 80, "G", [
    ("G", "Overrun", "20", "This attack also does 20 damage to 1 of your opponent's Benched Pokémon. (Don't apply Weakness and Resistance for Benched Pokémon.)"),
], weak="R", retreat=1)
P(9, "Virizion", "Basic", 120, "G", [
    ("C", "Double Draw", "", "Draw 2 cards."),
    ("GGC", "Solar Beam", "110", ""),
], weak="R", retreat=1)

P(10, "Wimpod", "Basic", 70, "G", [
    ("G", "Ram", "10", ""),
], abilities=[("Punk Out", "If your opponent has any Pokémon ex in play, this Pokémon has no Retreat Cost.")], weak="R", retreat=3)
P(11, "Mega Golisopod ex", "Stage 1", 340, "G", [
    ("G", "Finishing Blow", "60+", "If your opponent's Active Pokémon already has any damage counters on it, this attack does 160 more damage."),
    ("CCC", "Quadruple Hold", "160", "During your opponent's next turn, the Defending Pokémon can't retreat."),
], weak="R", retreat=3, evolves="Wimpod", ex=True, mega=True)
P(12, "Sprigatito", "Basic", 70, "G", [
    ("G", "Play Rough", "10+", "Flip a coin. If heads, this attack does 20 more damage."),
], weak="R", retreat=1)
P(13, "Floragato", "Stage 1", 90, "G", [
    ("GG", "Slash", "60", ""),
], weak="R", retreat=1, evolves="Sprigatito")
P(14, "Meowscarada ex", "Stage 2", 320, "G", [
    ("GG", "Magical Bullet", "120", "This attack also does 120 damage to 1 of your opponent's Benched Pokémon that has any damage counters on it. (Don't apply Weakness and Resistance for Benched Pokémon.)"),
], weak="R", retreat=2, evolves="Floragato", ex=True)
P(15, "Smoliv", "Basic", 60, "G", [
    ("G", "Spray Fluid", "20", ""),
], weak="R", retreat=1)
P(16, "Dolliv", "Stage 1", 90, "G", [
    ("G", "Leaf Step", "40", ""),
], weak="R", retreat=1, evolves="Smoliv")
P(17, "Arboliva", "Stage 2", 150, "G", [
    ("GC", "Mega Drain", "100", "Heal 30 damage from this Pokémon."),
], abilities=[("Slippery Oil", "Once during your turn, you may use this Ability. Switch out your opponent's Active Pokémon to the Bench. (Your opponent chooses the new Active Pokémon.)")],
  weak="R", retreat=2, evolves="Dolliv")

# ---------------------------------------------------------------- Fire
P(18, "Growlithe", "Basic", 80, "R", [
    ("C", "Roar", "", "Switch out your opponent's Active Pokémon to the Bench. (Your opponent chooses the new Active Pokémon.)"),
    ("RCC", "Rear Kick", "50", ""),
], weak="W", retreat=2)
P(19, "Arcanine", "Stage 1", 150, "R", [
    ("RCC", "Fervent Fang", "90+", "If your opponent has 4 or fewer Prize cards remaining, this attack does 90 more damage."),
    ("RRCC", "Heat Tackle", "200", "This Pokémon also does 50 damage to itself."),
], weak="W", retreat=4, evolves="Growlithe")
P(20, "Magmar", "Basic", 90, "R", [
    ("C", "Gather Strength", "", "Search your deck for up to 2 Basic Energy cards, reveal them, and put them into your hand. Then, shuffle your deck."),
    ("RC", "Combustion", "30", ""),
], weak="W", retreat=2)
P(21, "Magmortar", "Stage 1", 140, "R", [
    ("RRC", "Heat Crash", "80", ""),
], abilities=[("Buddy Boost", "Once during your turn, you may use this Ability. Attach a Basic Fire Energy card, a Basic Lightning Energy card, or 1 of each from your hand to your Electivire and Magmortar in any way you like.")],
  weak="W", retreat=3, evolves="Magmar")
P(22, "Torkoal", "Basic", 130, "R", [
    ("RC", "Searing Flame", "30", "Your opponent's Active Pokémon is now Burned."),
    ("RRC", "Combustion Blast", "120", "During your next turn, this Pokémon can't use Combustion Blast."),
], weak="W", retreat=3)
P(23, "Heat Rotom ex", "Basic", 190, "R", [
    ("CC", "Rewarm", "30×", "This attack does 30 damage for each Basic Fire Energy card in your discard pile. Then, shuffle those cards into your deck."),
    ("RRC", "Strong Flare", "170", "Discard 2 Energy from this Pokémon."),
], weak="W", retreat=1, ex=True)
P(24, "Heatmor", "Basic", 110, "R", [
    ("R", "Destructive Flame", "30", "Flip a coin. If heads, discard an Energy from your opponent's Active Pokémon."),
], weak="W", retreat=1)

# ---------------------------------------------------------------- Water
P(25, "Mantine", "Basic", 110, "W", [
    ("C", "Make Waves", "", "Each player shuffles their hand into their deck and draws 4 cards."),
    ("WC", "Bubble Drain", "30", "Heal 30 damage from this Pokémon."),
], weak="L", retreat=1)

P(26, "Kyogre", "Basic", 150, "W", [
    ("WC", "Waterfall", "40", ""),
    ("WWC", "Brutal Whirlpool", "100", "If a Stadium that has \"Legendary\" in its name is in play, this attack also does 50 damage to each of your opponent's Benched Pokémon. (Don't apply Weakness and Resistance for Benched Pokémon.)"),
], weak="L", retreat=3)
P(27, "Frillish", "Basic", 80, "W", [
    ("C", "Hook", "10", ""),
], weak="L", retreat=2)
P(28, "Jellicent", "Stage 1", 120, "W", [
    ("WCC", "Gentle Slap", "100", ""),
], abilities=[("Deep Sea Draw", "Once during your turn, you may use this Ability. Draw a card. If you do, you may put a card from your hand on the bottom of your deck.")],
  weak="L", retreat=2, evolves="Frillish")
P(29, "Wishiwashi ex", "Basic", 260, "W", [
    ("WWWC", "Hydro Splash", "220", ""),
], abilities=[("Oceanic Gain", "Once during your turn, if this Pokémon is in the Active Spot, you may use this Ability. Heal 50 damage from this Pokémon.")],
  weak="L", retreat=3, ex=True)

# ---------------------------------------------------------------- Lightning
P(30, "Electabuzz", "Basic", 90, "L", [
    ("C", "Call for Family", "", "Search your deck for up to 2 Basic Pokémon and put them onto your Bench. Then, shuffle your deck."),
    ("LLC", "Headbutt", "60", ""),
], weak="F", retreat=2)
P(31, "Electivire", "Stage 1", 140, "L", [
    ("CC", "Body Slam", "30", "Flip a coin. If heads, your opponent's Active Pokémon is now Paralyzed."),
    ("LLCC", "Voltaic Hammer", "60×", "Discard any amount of Basic Energy from this Pokémon, and this attack does 60 damage for each card you discarded in this way."),
], weak="F", retreat=3, evolves="Electabuzz")
P(32, "Jolteon", "Stage 1", 110, "L", [
    ("L", "Tackle", "30", ""),
    ("LLL", "Thunderbolt", "220", "Discard all Energy from this Pokémon."),
], weak="F", retreat=0, evolves="Eevee")
P(33, "Raikou ex", "Basic", 200, "L", [
    ("L", "Thunder-Clad", "", "If you go first, you can use this attack during your first turn. Search your deck for an Energy card and attach it to this Pokémon. Then, shuffle your deck."),
    ("LLC", "Power Rush", "200", "Flip a coin. If tails, during your next turn, this Pokémon can't use attacks."),
], weak="F", retreat=0, ex=True)

P(34, "Rotom", "Basic", 80, "L", [
    ("LC", "Thunder Shock", "50", "Flip a coin. If heads, your opponent's Active Pokémon is now Paralyzed."),
], weak="F", retreat=1)
P(35, "Thundurus", "Basic", 120, "L", [
    ("LCC", "Thunderous Edge", "90", "This attack's damage isn't affected by any effects on your opponent's Active Pokémon."),
], abilities=[("Incarnate Solidarity", "If you have Tornadus, Thundurus, Landorus, and Enamorus in play, ignore all Colorless Energy in the costs of attacks used by this Pokémon.")],
  weak="F", retreat=1)
P(36, "Pincurchin", "Basic", 80, "L", [
    ("CC", "Energy Crush", "20×", "This attack does 20 damage for each Energy attached to all of your opponent's Pokémon."),
], weak="F", retreat=1)
P(37, "Pawmi", "Basic", 60, "L", [
    ("L", "Quick Attack", "10+", "Flip a coin. If heads, this attack does 20 more damage."),
], weak="F", retreat=1)
P(38, "Pawmo", "Stage 1", 90, "L", [
    ("L", "Electro Ball", "40", ""),
], weak="F", retreat=1, evolves="Pawmi")
P(39, "Pawmot", "Stage 2", 150, "L", [
    ("LC", "Electric Punch", "100", ""),
], abilities=[("Generator's Touch", "Once during your turn, you may use this Ability. Attach a Basic Lightning Energy card from your discard pile to 1 of your Pokémon.")],
  weak="F", retreat=1, evolves="Pawmo")
P(40, "Wattrel", "Basic", 60, "L", [
    ("L", "Agility", "10", "Flip a coin. If heads, during your opponent's next turn, prevent all damage from and effects of attacks done to this Pokémon."),
], weak="L", res="F", retreat=1)
P(41, "Kilowattrel", "Stage 1", 120, "L", [
    ("L", "Raid", "30+", "If this Pokémon evolved from Wattrel during this turn, this attack does 90 more damage."),
    ("LC", "Speed Dive", "70", ""),
], weak="L", res="F", retreat=1, evolves="Wattrel")

P(42, "Miraidon", "Basic", 120, "L", [
    ("LC", "Claw Slash", "50", ""),
    ("LLC", "Flashing Bolt", "120", "During your next turn, this Pokémon can't use Flashing Bolt."),
], weak="F", retreat=1)

# ---------------------------------------------------------------- Psychic
P(43, "Drowzee", "Basic", 80, "P", [
    ("P", "Pound", "20", ""),
], weak="D", res="F", retreat=2)
P(44, "Hypno", "Stage 1", 120, "P", [
    ("P", "Mind Ruler", "20×", "This attack does 20 damage for each card in your opponent's hand."),
    ("PC", "Hypnoblast", "50", "Your opponent's Active Pokémon is now Asleep."),
], weak="D", res="F", retreat=2, evolves="Drowzee")
P(45, "Giratina", "Basic", 130, "P", [
    ("PPC", "Chaos Crawler", "120", "During your opponent's next turn, prevent all damage from attacks done to this Pokémon. If 1 of your Pokémon used Chaos Crawler during your last turn, this attack can't be used."),
], weak="D", res="F", retreat=3)
P(46, "Golett", "Basic", 90, "P", [
    ("PP", "Light Punch", "50", ""),
], weak="D", res="F", retreat=3)
P(47, "Mega Golurk ex", "Stage 1", 350, "P", [
    ("PP", "Goliath's Punch", "300", "This Pokémon also does 30 damage to itself."),
], abilities=[("Restricted Activation", "This Pokémon can't use attacks unless you have 10 or more cards in your hand.")],
  weak="D", res="F", retreat=3, evolves="Golett", ex=True, mega=True)
P(48, "Enamorus", "Basic", 120, "P", [
    ("PPCC", "Rising Heart", "100+", "If your opponent's Active Pokémon is a Pokémon ex, this attack does 100 more damage."),
], abilities=[("Incarnate Solidarity", "If you have Tornadus, Thundurus, Landorus, and Enamorus in play, ignore all Colorless Energy in the costs of attacks used by this Pokémon.")],
  weak="M", retreat=1)

# ---------------------------------------------------------------- Fighting
P(49, "Sandshrew", "Basic", 60, "F", [
    ("F", "Ascension", "", "Search your deck for a card that evolves from this Pokémon and put it onto this Pokémon to evolve it. Then, shuffle your deck."),
], weak="G", retreat=1)

P(50, "Sandslash", "Stage 1", 110, "F", [
    ("F", "Digging Claw", "60", "Discard the top card of your opponent's deck."),
], abilities=[("Counterattack Quills", "If this Pokémon is in the Active Spot and is damaged by an attack from your opponent's Pokémon (even if this Pokémon is Knocked Out), place 3 damage counters on the Attacking Pokémon.")],
  weak="G", retreat=1, evolves="Sandshrew")
P(51, "Onix", "Basic", 120, "F", [
    ("CCC", "Guard Press", "80", "During your opponent's next turn, this Pokémon takes 30 less damage from attacks (after applying Weakness and Resistance)."),
], weak="G", retreat=4)
P(52, "Steelix", "Stage 1", 190, "F", [
    ("FFCC", "Tough Swing", "150", "This attack's damage isn't affected by Resistance."),
], abilities=[("High Density Armor", "If this Pokémon has full HP, it takes 60 less damage from attacks from your opponent's Pokémon (after applying Weakness and Resistance).")],
  weak="G", retreat=4, evolves="Onix")
P(53, "Groudon", "Basic", 150, "F", [
    ("FC", "Strength", "40", ""),
    ("FFC", "Brutal Lands", "100+", "If a Stadium that has \"Legendary\" in its name is in play, this attack does 170 more damage."),
], weak="G", retreat=4)
P(54, "Landorus", "Basic", 130, "F", [
    ("FCC", "Gaia Crush", "110", "Discard a Stadium in play."),
], abilities=[("Incarnate Solidarity", "If you have Tornadus, Thundurus, Landorus, and Enamorus in play, ignore all Colorless Energy in the costs of attacks used by this Pokémon.")],
  weak="G", retreat=2)

# ---------------------------------------------------------------- Darkness
P(55, "Nidoran ♀", "Basic", 60, "D", [
    ("C", "Find a Friend", "", "Search your deck for a Pokémon, reveal it, and put it into your hand. Then, shuffle your deck."),
    ("D", "Gnaw", "10", ""),
], weak="F", retreat=1)
P(56, "Nidorina", "Stage 1", 90, "D", [
    ("DC", "Tackle", "60", ""),
], weak="F", retreat=2, evolves="Nidoran ♀")
P(57, "Nidoqueen", "Stage 2", 170, "D", [
    ("DCC", "Giga Impact", "150", "During your next turn, this Pokémon can't use attacks."),
], abilities=[("Maternal Call", "Once during your turn, you may use this Ability. Flip a coin. If heads, switch in 1 of your opponent's Benched Pokémon to the Active Spot.")],
  weak="F", retreat=3, evolves="Nidorina")

P(58, "Spinarak", "Basic", 60, "D", [
    ("D", "Poison Sting", "", "Your opponent's Active Pokémon is now Poisoned."),
    ("CCC", "Bug Out", "50×", "Reveal the bottom 7 cards of your deck, and this attack does 50 damage for each Pokémon you find there that has the Bug Out attack. Then, shuffle any revealed Pokémon back into your deck. Discard the other cards."),
], weak="F", retreat=1)
P(59, "Ariados", "Stage 1", 100, "D", [
    ("D", "Tormenting Poison", "", "Your opponent's Active Pokémon is now Poisoned. During Pokémon Checkup, place 4 damage counters on that Pokémon instead of 1."),
    ("CCC", "Stealthy Sting", "80", "During your opponent's next turn, prevent all damage done to this Pokémon by attacks from Basic Pokémon."),
], weak="F", retreat=1, evolves="Spinarak")
P(60, "Sableye", "Basic", 80, "D", [
    ("D", "Lure Out", "", "Reveal the top 5 cards of your opponent's deck. You may choose any number of Basic Pokémon you find there and put those Pokémon onto their Bench. Your opponent shuffles the other cards back into their deck."),
    ("DC", "Ominous Eyes", "", "Place 5 damage counters on 1 of your opponent's Pokémon."),
], weak="G", retreat=1)
P(61, "Carvanha", "Basic", 70, "D", [
    ("DC", "Ambush", "20+", "Flip a coin. If heads, this attack does 20 more damage."),
], weak="G", retreat=1)
P(62, "Sharpedo", "Stage 1", 120, "D", [
    ("DC", "Crunch", "60", "Flip a coin. If heads, discard an Energy from your opponent's Active Pokémon."),
], weak="G", retreat=1, evolves="Carvanha")
P(63, "Darkrai", "Basic", 120, "D", [
    ("D", "Shadow-Clad", "", "Search your deck for up to 2 Basic Darkness Energy cards and attach them to this Pokémon. Then, shuffle your deck."),
    ("DDC", "Dark Cutter", "110", ""),
], weak="G", retreat=2)
P(64, "Purrloin", "Basic", 60, "D", [
    ("D", "Dig Claws", "20", ""),
], weak="G", retreat=1)

P(65, "Liepard", "Stage 1", 110, "D", [
    ("D", "Follow-Up Claw", "20×", "This attack does 20 damage for each damage counter on your opponent's Active Pokémon."),
    ("DCC", "Slash", "90", ""),
], weak="G", retreat=1, evolves="Purrloin")
P(66, "Zorua", "Basic", 70, "D", [
    ("D", "Stampede", "10", ""),
    ("DC", "Scratch", "30", ""),
], weak="G", retreat=1)
P(67, "Zoroark ex", "Stage 1", 270, "D", [
    ("D", "Riotous Beating", "20×", "This attack does 20 damage for each of your Pokémon in play."),
    ("DCC", "Slashing Strike", "210", "During your next turn, this Pokémon can't use Slashing Strike."),
], weak="G", retreat=2, evolves="Zorua", ex=True)
P(68, "Inkay", "Basic", 60, "D", [
    ("D", "Knock Off", "10", "Discard a random card from your opponent's hand."),
], weak="G", retreat=1)
P(69, "Mega Malamar ex", "Stage 1", 320, "D", [
    ("DD", "Psychic Marionette", "70×", "This attack does 70 damage for each of your opponent's Benched Pokémon."),
    ("DDD", "Eerie Wave", "200", "Your opponent's Active Pokémon is now Confused."),
], weak="G", retreat=2, evolves="Inkay", ex=True, mega=True)
P(70, "Morpeko", "Basic", 80, "D", [
    ("C", "Call for Family", "", "Search your deck for up to 2 Basic Pokémon and put them onto your Bench. Then, shuffle your deck."),
    ("D", "Slap", "30", ""),
], weak="G", retreat=1)
P(71, "Zarude", "Basic", 130, "D", [
    ("D", "Corkscrew Punch", "20", ""),
    ("DC", "Deadly Whip", "50+", "Flip 2 coins. If both of them are heads, this attack does 150 more damage."),
], weak="G", retreat=2)

# ---------------------------------------------------------------- Dragon
P(72, "Druddigon", "Basic", 120, "N", [
    ("RW", "Drag Off", "", "Switch in 1 of your opponent's Benched Pokémon to the Active Spot. This attack does 40 damage to the new Active Pokémon."),
    ("CCC", "Claw Slash", "80", ""),
], retreat=2)

P(73, "Jangmo-o", "Basic", 70, "N", [
    ("LF", "Hard Head", "30", "During your opponent's next turn, this Pokémon takes 30 less damage from attacks (after applying Weakness and Resistance)."),
], retreat=1)
P(74, "Hakamo-o", "Stage 1", 100, "N", [
    ("LF", "Double Smash", "70×", "Flip 2 coins. This attack does 70 damage for each heads."),
], retreat=2, evolves="Jangmo-o")
P(75, "Kommo-o", "Stage 2", 160, "N", [
    ("LFC", "Hammer In", "170", ""),
], abilities=[("Beat Scales", "Once during your turn, you may use this Ability. Look at the top 6 cards of your deck and attach any number of Basic Energy cards you find there to your Dragon Pokémon in any way you like. Shuffle the other cards back into your deck.")],
  retreat=2, evolves="Hakamo-o")
P(76, "Cyclizar", "Basic", 120, "N", [
    ("CC", "Bite", "30", ""),
    ("GWC", "Break Through", "110", "This attack also does 30 damage to 1 of your opponent's Benched Pokémon. (Don't apply Weakness and Resistance for Benched Pokémon.)"),
], retreat=1)

# ---------------------------------------------------------------- Colorless
P(77, "Tauros", "Basic", 130, "C", [
    ("CC", "Raging Horns", "50+", "This attack does 10 more damage for each damage counter on this Pokémon."),
], weak="F", retreat=2)
P(78, "Eevee", "Basic", 70, "C", [
    ("C", "Nap", "", "Heal 20 damage from this Pokémon."),
    ("C", "Headbutt", "10", ""),
], weak="F", retreat=1)
P(79, "Delibird", "Basic", 90, "C", [
    ("C", "Beat", "10", ""),
], abilities=[("Energizing Present", "Once during your turn, if this Pokémon is in the Active Spot, you may use this Ability. Look at the top 6 cards of your deck, reveal an Energy card you find there, and put it into your hand. Shuffle the other cards and put them on the bottom of your deck.")],
  weak="L", res="F", retreat=1)
P(80, "Azurill", "Basic", 30, "C", [
    ("", "Bouncy-Bounce Charge", "", "Search your deck for an Energy card and attach it to 1 of your Benched Pokémon. Then, shuffle your deck."),
], weak="F", retreat=0)

P(81, "Swablu", "Basic", 50, "C", [
    ("C", "Run Around", "", "Switch this Pokémon with 1 of your Benched Pokémon."),
    ("CC", "Peck", "20", ""),
], weak="L", res="F", retreat=1)
P(82, "Altaria", "Stage 1", 110, "C", [
    ("CCC", "Flap", "80", ""),
], abilities=[("Cottony Carrier", "Your Basic Pokémon in play have no Retreat Cost.")],
  weak="L", res="F", retreat=1, evolves="Swablu")
P(83, "Kecleon", "Basic", 90, "C", [
    ("CC", "Colorful Whip", "30×", "Reveal any number of Pokémon from your hand, and this attack does 30 damage for each different type of Pokémon you revealed in this way."),
], weak="F", retreat=2)
P(84, "Mega Rayquaza ex", "Basic", 280, "C", [
    ("RLC", "Storm Emerald", "50×", "This attack does 50 damage for each Fire Energy and each Lightning Energy attached to all of your Pokémon."),
], abilities=[("Ruler's Roar", "Once during your turn, when you play this Pokémon from your hand onto your Bench, you may use this Ability. Look at the top 4 cards of your deck and attach a Basic Energy card you find there to this Pokémon. Shuffle the other cards and put them on the bottom of your deck.")],
  weak="L", res="F", retreat=2, ex=True, mega=True)
P(85, "Tornadus", "Basic", 110, "C", [
    ("CCC", "Corkscrew Dive", "70", "You may draw cards until you have 6 cards in your hand."),
], abilities=[("Incarnate Solidarity", "If you have Tornadus, Thundurus, Landorus, and Enamorus in play, ignore all Colorless Energy in the costs of attacks used by this Pokémon.")],
  weak="L", res="F", retreat=1)
P(86, "Fletchling", "Basic", 60, "C", [
    ("C", "Surprise Attack", "30", "Flip a coin. If tails, this attack does nothing."),
], weak="L", res="F", retreat=1)
P(87, "Fletchinder", "Stage 1", 80, "C", [
    ("CC", "Clutch", "40", "During your opponent's next turn, the Defending Pokémon can't retreat."),
], weak="L", res="F", retreat=0, evolves="Fletchling")
P(88, "Talonflame ex", "Stage 2", 280, "C", [
    ("CC", "Talon Hunt", "150", "You may search your deck for up to 2 cards and put them into your hand. Then, shuffle your deck."),
], abilities=[("Excited Dive", "Once during your turn, if this Pokémon is in your hand, and if you have any Colorless Mega Evolution Pokémon ex in play, you may use this Ability. Put this Pokémon onto your Bench.")],
  weak="L", res="F", retreat=0, evolves="Fletchinder", ex=True)

# ---------------------------------------------------------------- Trainers
T(89, "Aarune", "Supporter", "Search your deck for up to 3 in any combination of Supporter and Stadium cards, reveal them, and put them into your hand. Then, shuffle your deck.")
T(90, "Adventure Lantern", "Item", "Search your deck for a Basic Fire Energy card and a Basic Lightning Energy card, reveal them, and put them into your hand. Then, shuffle your deck.")
T(91, "Custom Vest", "Pokémon Tool", "If the Pokémon this card is attached to isn't a Mega Evolution Pokémon ex, it takes 60 less damage from attacks from your opponent's Mega Evolution Pokémon ex (after applying Weakness and Resistance).")
T(92, "Emcee's Hype", "Supporter", "Draw 2 cards. If your opponent has 3 or fewer Prize cards remaining, draw 2 more cards.")
T(93, "Grisham", "Supporter", "Heal 50 damage from each Pokémon (both yours and your opponent's).")
# Legendary Stadiums are split cards: 2 different halves (e.g. 094 + 095) are played together as 1 Stadium.
LEGEND_RULE = "You cannot play this card by itself. You must combine 2 different {n} from your hand to play as 1 Stadium card."
for num, nm, txt in [
    (94, "Legendary Pyroduct", "Evolution Pokémon in play (both yours and your opponent's) have no Abilities."),
    (95, "Legendary Pyroduct", "Evolution Pokémon in play (both yours and your opponent's) have no Abilities."),
    (96, "Legendary Summit", "Whenever a Colorless Pokémon (yours or your opponent's) is Knocked Out by damage from an attack from the opponent's Pokémon, that player takes 1 fewer Prize card."),
    (97, "Legendary Summit", "Whenever a Colorless Pokémon (yours or your opponent's) is Knocked Out by damage from an attack from the opponent's Pokémon, that player takes 1 fewer Prize card."),
    (98, "Legendary Trench", "Whenever a Pokémon (yours or your opponent's) is healed, double the amount of damage healed."),
    (99, "Legendary Trench", "Whenever a Pokémon (yours or your opponent's) is healed, double the amount of damage healed."),
]:
    T(num, nm, "Stadium", f"{LEGEND_RULE.format(n=nm)} {txt}")
T(100, "Mega Rayquaza Cap", "Pokémon Tool",
  "The Pokémon this card is attached to can use the attack on this card. (You still need the necessary Energy to use this attack.) "
  "[Colorless] Delta Gift: For each of your Pokémon that has a Mega Rayquaza Cap attached, search your deck for a Basic Energy card and attach it to that Pokémon. Then, shuffle your deck.")
T(101, "Tasty Rice Ball", "Item", "Heal 30 damage from your Active Pokémon. For each Tasty Rice Ball card (not including this card) in your discard pile, heal 30 more damage.")
T(102, "Tate & Liza's Training", "Supporter", "Draw 2 cards. If you drew any cards in this way, and if a Stadium that has \"Legendary\" in its name is in play, put this Tate & Liza's Training into your hand instead of the discard pile.")
T(103, "Zinnia's Trust", "Supporter", "Switch your Active Pokémon with 1 of your Benched Pokémon. If you do, move an Energy from the Pokémon you moved to your Bench to the new Active Pokémon.")
T(129, "Pokémon Catcher", "Item", "Flip a coin. If heads, switch in 1 of your opponent's Benched Pokémon to the Active Spot.")


def build() -> None:
    out = Path(__file__).parent / "cards" / f"{SET_ID}.json"
    out.write_text(json.dumps(CARDS, ensure_ascii=False, indent=2), encoding="utf-8")
    sets = json.loads((Path(__file__).parent / "sets.json").read_text(encoding="utf-8"))
    if not any(s["id"] == SET_ID for s in sets):
        print(f"NOTE: add a '{SET_ID}' entry (ptcgoCode {SET_CODE}) to sets.json so the loader picks this file up")
    print(f"wrote {len(CARDS)} cards to {out}")


if __name__ == "__main__":
    build()
