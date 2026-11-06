# 03 — Carte du meta, et pourquoi la lecture naive est fausse

**2026-07-27.** 9 081 parties exploitables, extraites des archives « top episodes » des
**2026-07-20** et **2026-07-26**. Ces archives sont selectionnees par Kaggle sur la **note
moyenne des participants** (Bovard, fil 709160) : l'echantillon est donc **biaise vers le haut
du classement**, ce qui est exactement ce qu'on veut pour savoir contre quoi un deck devra tenir.

Qualite de l'echantillon : 10 nuls et **8 parties avec un agent en ERREUR sur 9 099** — soit
**0,1 %**. Le champ haut de ladder ne plante quasiment pas ; on ne gagnera rien en misant sur
les crashs adverses.

---

## 1. Le champ, en population

| archetype | joue | part | WR | IC95 | equipes |
|---|---:|---:|---:|---|---:|
| **Marnie's Grimmsnarl ex** + Morgrem | 7 229 | **39,8 %** | 51,3 % | [50,1 ; 52,4] | **96** |
| **Alakazam** + Kadabra | 4 648 | **25,6 %** | **46,8 %** | [45,4 ; 48,2] | 83 |
| Team Rocket's Spidops + Mewtwo | 1 813 | 10,0 % | 53,8 % | [51,5 ; 56,1] | 19 |
| Cynthia's Gabite + Garchomp ex | 1 263 | 7,0 % | 50,0 % | [47,2 ; 52,7] | 10 |
| Drakloak + Dragapult ex | 844 | 4,6 % | 55,2 % | [51,8 ; 58,5] | 4 |
| Crustle + Mega Kangaskhan ex | 821 | 4,5 % | 42,8 % | [39,4 ; 46,2] | 23 |
| Mega Kangaskhan ex + Meowth ex | 414 | 2,3 % | **61,4 %** | [56,6 ; 65,9] | **2** |

**Deux archetypes font 65 % du champ.** Et le second, Alakazam, **perd** (46,8 %) tout en etant
joue par 83 equipes.

## 2. La matrice de matchups — une structure pierre-feuille-ciseaux

Lignes battent colonnes, effectifs entre parentheses.

| | Marnie's | Alakazam | Team Rocket | Cynthia's | Drakloak | Crustle | Mega Kang |
|---|---|---|---|---|---|---|---|
| **Marnie's** | — | **57 %** (1742) | **56 %** (762) | 42 % (517) | 51 % (311) | 52 % (261) | **33 %** (237) |
| **Alakazam** | 43 % (1742) | — | **21 %** (476) | **67 %** (338) | 38 % (237) | **66 %** (271) | 58 % (78) |
| **Team Rocket** | 44 % (762) | **79 %** (476) | — | 43 % (162) | 30 % (100) | 59 % (70) | . |

Trois faits solides, tous sur de gros effectifs :

- **Team Rocket's Spidops ecrase Alakazam 79 % / 21 %** sur **476 parties**. C'est le contre le
  plus net du format, et Alakazam represente **un quart du champ**.
- **Marnie's bat Alakazam 57 %** sur **1 742 parties** — le matchup le plus joue du jeu.
- **Marnie's perd contre Mega Kangaskhan 33 %** sur 237 parties : le deck le plus joue a un
  contre identifie.

## 3. ⚠⚠ Le confondant — et pourquoi la lecture naive est FAUSSE

Lecture naive du tableau 1 : *« Mega Kangaskhan ex + Meowth ex est le meilleur deck, 61,4 % »*.

**C'est faux.** Regle ROGII, appliquee telle quelle : **une loi sur des POPULATIONS n'est pas une
loi sur des MODELES**. Le taux de victoire d'un archetype melange la force du DECK et celle du
PILOTE. `tools/meta_confound.py` separe les deux par trois controles.

### C1/C2 — concentration

| archetype | equipes | part de la 1ʳᵉ equipe | verdict |
|---|---:|---:|---|
| Marnie's Grimmsnarl ex | 96 | 9 % | **diversifie** |
| Alakazam | 83 | 16 % | **diversifie** |
| Crustle + Mega Kangaskhan | 23 | 33 % | diversifie |
| Team Rocket's Spidops | 19 | 48 % | fragile |
| Cynthia's Garchomp ex | 10 | **71 %** | **CONFONDU** |
| Drakloak + Dragapult ex | 4 | **64 %** | **CONFONDU** |
| **Mega Kangaskhan + Meowth ex** | **2** | **60 %** | **CONFONDU** |
| Kirlia + Mega Gardevoir ex | 1 | 100 % | **CONFONDU** |

Le 61,4 % de Mega Kangaskhan repose sur **2 equipes**, dont une fait 60 % des parties. Ce chiffre
mesure **un agent**, pas un deck. Idem pour Dragapult (55,2 %, 4 equipes).

### C3 — intra-pilote : le seul vrai test

On ne compare que des archetypes joues **par la meme equipe**. Le pilote est alors neutralise
par construction.

```
Oshbocker      Crustle 51% (269) | Alakazam 47% (137) | Drakloak 49% (81) | Marnie's 68% (31)
flg  (LB #1)   Drakloak 63% (131)                                        | Marnie's 62% (128)
Dominic Peel   Marnie's 55% (307)| Alakazam 46% (63)
Dries @ Tufa   Marnie's 58% (462)| Crustle  47% (75)
Rmy            Alakazam 42% (182)| Marnie's 45% (75)
```

Ecarts moyens **a pilote constant** :

| comparaison | ecart | equipes |
|---|---:|---:|
| Marnie's − Drakloak | **+8,4 pts** | 2 |
| Marnie's − Crustle | **+7,7 pts** | 4 |
| **Marnie's − Alakazam** | **+5,9 pts** | **6** |
| Marnie's − Team Rocket | **+5,6 pts** | 2 |

> 🔑 **Marnie's Grimmsnarl ex gagne TOUTES les comparaisons intra-pilote**, et la plus repliquee
> (contre Alakazam, **6 equipes independantes**) donne **+5,9 points**. C'est le seul archetype
> a la fois **diversifie** (96 equipes, 9 % max) et **gagnant a pilote constant**.
>
> ⚠ Effectifs d'equipes faibles (2 a 6). Ce qui rend le resultat credible n'est pas un test
> unique, c'est que **les quatre comparaisons pointent dans le meme sens**. A re-mesurer quand
> on aura plus de jours d'archives.

Preuve par l'exemple que le pilote domine : **`flg`, n°1 de la ladder (1200,6)**, obtient
**63 %** avec Drakloak et **62 %** avec Marnie's. Deux decks, meme resultat. Ce n'est pas le
deck qui fait son classement.

## 4. Ce que ca implique pour nous

1. **Le deck par defaut est Marnie's Grimmsnarl ex.** C'est le seul choix defendable *par la
   mesure* — et defendable **par ecrit**, ce qui vaut 20 % du bareme Strategy.
2. **Ne pas jouer Alakazam.** 25,6 % du champ, 46,8 % de victoires, et **79 % de defaites contre
   Team Rocket's Spidops**. Un quart du champ joue un deck perdant.
3. **Le contre a preparer est Mega Kangaskhan** (Marnie's y tombe a 33 %). C'est la faiblesse
   connue de notre deck par defaut, sur 237 parties.
4. **Ne jamais chercher a battre `flg` par le deck.** L'ecart du n°1 est dans l'agent.
5. ⚠ **Ne jamais citer les 61,4 % de Mega Kangaskhan comme « le meilleur deck »** dans le
   rapport. Un juge competent verrait le n=2, et ca couterait plus cher que ca ne rapporte.

## 5. Reste ouvert

- **Premier ou second joueur ?** Mon agent heuristique repond « premier » **par convention, sans
  mesure**. C'est mesurable sur les archives (`current.firstPlayer` croise avec `rewards`) mais
  mon extracteur ne l'a pas conserve — a rajouter au prochain passage (~11 min de re-parse).
- **Derive du meta** : je n'ai que 2 jours (20/07 et 26/07). Le champ bouge (temoignage forum :
  *« notre deck Archaludon tenait ~1000 ELO puis a chute quand le champ s'est deplace »*).
  A rejouer sur 5-6 jours avant de figer un choix de deck.
- L'archetypage par « 2 Pokemon evolues les plus joues » regroupe peut-etre des variantes
  distinctes (`Marnie's + Froslass` et `Marnie's + Dudunsparce` sortent separement).

## 6. Outillage

| outil | role |
|---|---|
| `tools/extract_meta.py` | lit les zips **en flux** — 21,5 Go/jour decompresses ne touchent jamais le disque ; ~7 ep/s, reprise sur curseur |
| `tools/analyze_meta.py` | archetypes, taux de jeu, WR + Wilson, matrice de matchups |
| `tools/meta_confound.py` | **C1/C2/C3** — separe la force du deck de celle du pilote |
| `tools/arena.py` | duels locaux, cotes alternees, IC95, anomalies comptees |

## 04/08 — TOP-150 NOMINATIF, decklists exactes extraites des replays (142/150 couverts)

Outil : `tools/top_field_decks.py` (archives quotidiennes 01-03/08, 13 824 episodes).
Sortie : **`data/meta/top150_decks.json`** — section `decks_uniques` (chaque liste distincte de
60 ids + rangs/parties/victoires de ses porteurs) = gauntlet pondere par le champ REEL, format
direct deckbuilding tool / `build_submission --deck`.

Distribution top-150 (deck le plus recent par equipe) : **Grimmsnarl+Froslass 55 (39 %)**,
Alakazam+Dudunsparce 23, Ogerpon 10, **Crustle+MegaKanga 10**, Cynthia 10, Lopunny 8.
Top-10 : #1 Majkel1337 (1297) joue Ogerpon ET Mega Lucario+Hariyama ; #4/#8 jouent Crustle.

🔑🔑 **Le Crustle du champ n'est PAS le canonique de juillet** : sur 18 listes (les 2 subs
actifs inclus), mediane **2 Mega Kangaskhan (pas 4), 3 Crustle**, et **11/18 sont des hybrides
Cornerstone Mask Ogerpon ex** (+ Rock Fighting Energy ×2, TR Factory, TR Petrel ×4, Ultra
Ball ×2), Switch 1 (pas 4), Xerosic 1 (pas 4), Crushing Hammer ×4 chez 7/18. `BEST_ev814`
optimise le squelette de juillet que le haut du champ a deja depasse.

⚠ special_hostage chiffre frais : **Enhanced Hammer 23/142 equipes (16 %, densite 0,63/deck,
dont le #6)**, Crushing 13/142. Profil energies du champ : 50 % des equipes a ZERO energie
speciale ; 12-14 speciales = 10 equipes seulement (la famille Crustle).
# 03 — Carte du méta (top-1000 Pokémon TCG Kaggle)

**Source unique :** `data/meta/top1000_decks.json` (généré 2026-08-04, couverture 1000/1000 équipes, 1275 decks, 430 entrées `decks_uniques`).
**Livrables associés :** `C:\Users\agent\Desktop\Pokemon\data\meta\gauntlet_champ.json` (40 listes) · `C:\Users\agent\Desktop\Pokemon\decks\champ\champ01..12_*.csv` (12 fichiers, 60 lignes exactes chacun).
**Synthèse de 4 analyses indépendantes du champ complet.** Écrit pour le track STRATEGY (70 % Model Score dont stabilité sur matchs répétés / non-dépendance aux états initiaux, 20 % Deck Score, 10 % rapport).

---

> ## CE QU'IL FAUT RETENIR
>
> 1. **Le champ est RÉSOLU en liste, pas en jeu.** 252 équipes sur 1000 (**25,2 %**) soumettent le **même multiset de 60 cartes** (Marnie's Grimmsnarl ex + Froslass), du rang **2 au rang 968** ; 86,6 % de l'archétype est bit-identique, 100 % tient à ≤5 cartes. **Aucune carte** n'y sépare le haut du bas (p = 0,34). L'écart de classement y vit dans le **pilotage**, hors de portée de ces données.
> 2. **Un seul signal de deck survit à tous les contrôles : le pôle CONTROLE de Crustle + Mega Kangaskhan ex.** WR **54,69 %** [52,20 ; 57,15] contre **44,91 %** [42,72 ; 47,12] pour le pôle STOCK — **+9,78 pts**, z = +5,75, intervalles de Wilson **disjoints**, sur 3 502 parties d'archive ; **+15,61 pts** en test apparié intra-équipe ; survit au leave-one-team-out (+9,17 pts au pire) et au contrôle de date (61 % vs 22 % en fenêtre août, p = 0,022).
> 3. **Notre candidat `BEST_crustle_kanga_ev814` a construit le pôle PERDANT** : à **2 cartes** de L3 (558 parties, 44,44 %) et L4 (334 parties, 37,43 %), mais à **14 cartes** de L1 (1 186 parties, 54,47 %) et **15** de L5 (266 parties, 56,77 %, rang 1). Il a le squelette consensuel à 100 % et a rempli les 15 cartes libres du mauvais côté de la coupe.
> 4. **Deux « effets » majeurs sont des artefacts de collecte, à ne surtout pas câbler.** (a) Le gradient de +20 pts d'Alakazam (Fezandipiti / Nighttime Mine / Shaymin) est un **gradient de DATE** : p = 0,002 dans le stratum stale, **p = 1,000** dans le stratum frais. (b) Le « les bons font tourner 2 decks » (72,0 % vs 2,83 %) est un **gradient d'EXPOSITION** : à 200+ parties observées, c'est **73,0 % / 70,8 % / 71,4 %**, plat.
> 5. **Le gauntlet dépend de la tranche visée, à un ordre de grandeur près.** **3** listes couvrent 50 % des *parties*, mais **10** pour 50 % des *équipes* et **124** pour 80 %. `Archaludon ex + Cinderace` pèse **19,2 %** des rangs 401-1000 et **0,00 %** du top-150 (rang min = 331 sur ses 120 slots).

---

## 1. La carte du méta par tranche de rang

### 1.1 Distribution (% de la tranche, archétype = `label_terrain` de `decks[0]`)

| Archétype | 1-50 (n=50) | 51-150 (n=100) | 151-400 (n=250) | 401-1000 (n=600) | Total |
|---|---|---|---|---|---|
| Marnie's Grimmsnarl ex + Froslass | **22,0 %** | **45,0 %** | **33,6 %** | 15,7 % | 234 |
| Alakazam + Dudunsparce | 14,0 % | 18,0 % | 24,4 % | **24,0 %** | 230 |
| **Archaludon ex + Cinderace** | **0,0 %** | **0,0 %** | 1,6 % | **19,2 %** | 119 |
| Crustle + Mega Kangaskhan ex | 10,0 % | 5,0 % | 10,4 % | 6,2 % | 73 |
| Mega Lucario ex + Hariyama | 0,0 % | 0,0 % | 2,8 % | 9,7 % | 65 |
| Cynthia's Garchomp ex + Roserade | 8,0 % | 7,0 % | 3,6 % | 3,3 % | 40 |
| Teal Mask Ogerpon ex | 8,0 % | 7,0 % | 2,8 % | 0,7 % | 22 |
| Dipplin + Thwackey | 10,0 % | 1,0 % | 2,8 % | 0,3 % | 15 |
| **Archétypes distincts** | **15** | **17** | **37** | **54** | 70 |

**Le milieu ne diffère pas du haut ; c'est le BAS qui est un autre jeu.**

### 1.2 Nombre effectif d'archétypes — profil en U

| Tranche | HHI | **N_eff = 1/HHI** | N_eff (non-stale seuls) | Part du n°1 |
|---|---|---|---|---|
| 1-50 | 0,1112 | **8,99** | 8,50 | 22,0 % |
| **51-150** | 0,2514 | **3,98** | **3,71** | **45,0 %** |
| 151-400 | 0,1891 | **5,29** | 4,74 | 33,6 % |
| 401-1000 | 0,1349 | **7,41** | 6,21 | 24,0 % |

**La tranche la plus mono-deck est 51-150, PAS le sommet** (8,99 → 3,98 → 5,29 → 7,41 ; le U tient et se creuse après contrôle de fraîcheur). Lecture : 51-150 = netdecking pur ; le top-50 diversifie parce qu'il **teste** (2,84 decks/équipe) ; le bas est diversifié par **bruit**.

### 1.3 Exclusivité haut/bas — asymétrie totale

- **Exclusifs au HAUT : 3 archétypes, 4 équipes.** Indiscernable du bruit. **Le sommet n'a aucune technologie propre.**
- **Exclusifs au BAS : 25 archétypes**, portés par deux entrées : Archaludon + Cinderace (19,17 pts d'écart), Mega Lucario + Hariyama (9,67 pts).
- **Contrôle le plus dur (rang min sur TOUS les slots, pas seulement `decks[0]`) :**
  - **Archaludon + Cinderace : rang min = 331** sur 120 slots. Exclusivité **réelle**, frais (70 vues le 2026-08-04), et survit au contrôle archive-seule (13,39 % vs 0,00 %).
  - **Mega Lucario + Hariyama : rang min = 1.** L'équipe classée 1ère le joue en deck secondaire. Son « exclusivité au bas » est un **artefact du choix `decks[0]`** + une vintage de juin. **Ne jamais le présenter comme un deck de bas de classement.**
- ⚠ Archaludon n'a **jamais été observé en volume** : 134 parties cumulées sur 120 instances (~1,1 chacune), 0 instance à n≥30. Deck faible ou vague trop récente : **les données ne peuvent pas trancher.**

### 1.4 La liste la plus copiée

⚠ **Correction de comptage :** `decks_uniques` est **sensible à l'ORDRE des 60 ids**. Les 430 entrées se réduisent à **398 listes canoniques** ; la liste n°1 passe de **239 à 252 équipes**.

| Tranche | A déjà joué la liste n°1 | En deck **courant** |
|---|---|---|
| 1-50 | **54,00 %** | 20,00 % |
| 51-150 | **61,00 %** | 39,00 % |
| 151-400 | 34,00 % | 28,40 % |
| 401-1000 | 13,17 % | 12,17 % |

22 004 parties cumulées, **WR 48,44 %** (48,82 % sur les 90 instances à n≥30). Origine commune établie (252 soumissions bit-identiques : convergence indépendante exclue) — **mais la nature de la source est inconnue** (notebook public ? deck du starter kit ? forum ?). Les 10 premières listes couvrent 47,4 % des slots, les 50 premières 67,8 % ; 352 listes sur 430 n'ont qu'une équipe.

### 1.5 Multi-decks : l'effet de rang est un ARTEFACT d'exposition

Brut : 72,00 % (1-50) → 40,00 % → 20,40 % → **2,83 %** (401-1000).
Médiane de `n_parties_vues` : **488** (1-50) → **1** (401-1000). **662 équipes n'ont qu'1 partie vue** → 0 % mécaniquement.

| n_parties_vues | 1-50 | 51-150 | 151-400 | 401-1000 |
|---|---|---|---|---|
| = 1 | (n=2) | 0,0 % | **0,0 %** (n=113) | **0,0 %** (n=541) |
| 10-49 | (n=3) | 23,3 % | 34,7 % | 33,3 % |
| **200+** | **73,0 %** (n=37) | **70,8 %** (n=24) | **71,4 %** (n=7) | (n=2) |

**≈71-73 % des équipes suffisamment observées font tourner ≥2 decks, à TOUS les rangs.** 117 des 144 équipes multi-decks (81,2 %) changent d'**archétype**, pas seulement de liste.

---

## 2. Crustle + Mega Kangaskhan ex — la carte complète des pôles

**Population :** 107 instances, **93 équipes**, **36 listes** distinctes, **3 611 parties d'archive** (+26 instances API à 1 partie, WR impossible). 4ᵉ archétype du champ (107/1275). Filtre **structurel** (ids 345 Crustle ET 756 Mega Kangaskhan ex), pas le `sig`.
⚠ Les compteurs diffèrent entre analyses selon l'unité : 107 instances / 93 équipes (Angle 2) vs 75 équipes en sous-`sig` dominante (Angle 3) vs 73 via `decks[0]` (Angle 1). **Ce ne sont pas des contradictions, ce sont trois dénominateurs.**

### 2.1 Quatre pôles structurels, dont deux morts

Distance = **cartes à échanger** (demi-différence symétrique des multisets). Les fusions intra-pôle coûtent **1 à 6,7 cartes** ; la fusion inter-moitiés coûte **17,07 cartes** — saut ×2,5. **Ce n'est PAS un continuum, la coupe est franche.**

| Pôle | listes | éq. | n_arch | **WR** | Wilson 95 % | rangs | dernière vue |
|---|---|---|---|---|---|---|---|
| **CONTROLE** (Petrel 4x + Cornerstone + Rock Fighting + Factory, Kanga à **2**) | 7 | 21 | **1 547** | **54,69 %** | **[52,20 ; 57,15]** | **1, 4, 8**, 17, 22, 23… | 2026-08-03 |
| **STOCK** (aucune pièce de contrôle ; 4x Xerosic/Switch/Hilda/Kanga) | 12 | 69 | **1 955** | **44,91 %** | **[42,72 ; 47,12]** | 8, 13, 19, 25, 28, 30… | 2026-08-03 |
| ROCHE-SANS-PETREL | 8 | **1** | 103 | 38,83 % | [29,99 ; 48,49] | 176 seulement | 2026-08-03 |
| PETREL-AGGRO (ancêtre abandonné) | 8 | 8 | **5** | (20 %) | [3,6 ; 62,5] | 304-955 | **2026-07-13** |

Baseline du fichier entier : **49,51 %** (27 685 / 55 917). CONTROLE = **+5,2 pts** au-dessus du champ ; STOCK = **−4,6 pts** en dessous.

| Comparaison | écart | z | IC |
|---|---|---|---|
| **CONTROLE vs STOCK** | **+9,78 pts** | **+5,75** | **DISJOINTS** |
| CONTROLE vs ROCHE-SANS-PETREL | +15,85 pts | +3,12 | DISJOINTS |
| ROCHE-SANS-PETREL vs STOCK | −6,08 pts | −1,21 | chevauchent |

### 2.2 Le confondant « les bons joueurs jouent CONTROLE » : testé, survécu (3 fois)

**(i) Stratification par rang** — CONTROLE tient **53-58 % dans les quatre tranches**, y compris chez les rangs 301-1000 (53,2 %) ; STOCK s'effondre à 31-38 % partout sauf en 26-100 (48,4 %, mais 1 361 des 1 482 parties viennent de deux équipes jouant les deux meilleures listes STOCK).

**(ii) Test apparié intra-équipe** (le test le plus propre : même joueur, même période, même ladder) — agrégat **84/157 = 53,50 %** [45,7 ; 61,1] contre **36/95 = 37,89 %** [28,8 ; 47,9], soit **+15,61 pts, z = +2,40**. Porté par LiamK (rang 8) : 53,7 % vs 38,7 %.

**(iii) Leave-one-team-out** — le pire retrait laisse **+9,17 pts**, y compris en retirant `flg` (rang 22, 858 des 1 547 parties CONTROLE).

WR par équipe **dans** CONTROLE (n≥20) : 66,2 / 57,1 / 53,7 / 55,1 / 54,5 / 54,0 / 50,0 / 48,1 %. **Le meilleur STOCK (48,5 %) est sous le pire CONTROLE.**

### 2.3 Les cartes qui séparent (21 instances CONTROLE vs 69 STOCK)

| Carte | CONTROLE | STOCK | méd. CTRL |
|---|---|---|---|
| **Ultra Ball** [1121] | **21/21** | **0/69** | 2 |
| **Cornerstone Mask Ogerpon ex** [117] | **21/21** | **0/69** | 1 |
| **Rock Fighting Energy** [20] | **21/21** | **0/69** | 2 |
| **Team Rocket's Factory** [1257] | **21/21** | **0/69** | 1 |
| **Team Rocket's Petrel** [1219] | **21/21** | 1/69 | 4 |
| Colress's Tenacity [1194] | 14/21 | **0/69** | 2 |
| Boss's Orders [1182] | 21/21 (méd. **4**) | 68/69 (méd. **2**) | 4 |
| Mega Kangaskhan ex [756] | méd. **2** | méd. **4** | 2 |
| Switch / Xerosic's Machinations | méd. **1** | méd. **4** | 1 |
| **Hand Trimmer** [1087] (inverse) | **0/21** | 55/69 | — |
| **Shaymin** [343] (inverse) | **0/21** | 30/69 | — |

**Squelette obligatoire (≥93 % des 93 équipes, 44-45 cartes) :** 4 Dwebble, 3-4 Crustle, 2-4 Mega Kangaskhan ex, 4 Pokégear 3.0, 4 Jumbo Ice Cream, 1 Hero's Cape, 4 Lillie's Determination, 4 Grow Grass, 4 Mist, 4 Spiky (+ Poffin/Hilda/Xerosic/Switch/Boss variables). **Les 15 cartes libres SONT l'axe qui sépare les deux pôles.**

⚠ **On ne peut attribuer le gain à AUCUNE carte individuelle** : Petrel (1 554 parties), Factory (1 551), Boss 4x (1 555), Kanga≤2 (1 548), Ultra Ball (1 598) sont quasi parfaitement colinéaires — dix fenêtres sur le même ensemble de decks, écarts tous entre +8,2 et +10,2 pts. **Seule carte non colinéaire : Crushing Hammer, et elle est PLATE (+0,13 pt** : 48,99 % avec / 48,86 % sans). Ce n'est **pas** le mécanisme.

### 2.4 L'axe stratégique (lecture des textes `cards.json` — mécanisme plausible, NON mesuré)

1. **Deux murs complémentaires.** Crustle (*Mysterious Rock Inn*) est immunisé aux **Pokémon ex** ; Cornerstone Mask Ogerpon ex (*Cornerstone Stance*) est immunisé aux **Pokémon à Talent**. Ensemble ils couvrent les deux moitiés du méta ; Rock Fighting Energy ferme la dernière porte (attaques à **effet**).
2. **Le deck arrête de courir** : Kanga 4→2, Switch 4→1, Xerosic 4→1. Il ne gagne plus la course de dégâts, il rend son actif **intouchable**.
3. **Boss's Orders 2→4 = l'arme offensive du plan** : derrière un mur imprenable, on va chercher la pièce qui casse le mur **sur le banc** avant qu'elle n'arrive.
4. **Petrel + Factory = tuteur autofinancé** (Petrel cherche n'importe quel Trainer, Factory rend 2 cartes) : c'est ce qui rend jouables les 1-of. Le deck joue **une bibliothèque de réponses**, pas une liste. Colress's Tenacity va chercher stade + énergie en une carte.
5. **Le mécanisme = invulnérabilité sélective + tuteur autofinancé + pince Boss's Orders.**

### 2.5 Notre candidat

| Distance (cartes) | Liste | Pôle | n_arch | WR |
|---|---|---|---|---|
| **2** | **L3** | **STOCK** | **558** | **44,44 %** |
| **2** | **L4** | **STOCK** | **334** | **37,43 %** |
| 3-5 | L2 | STOCK | 972 | 48,05 % |
| **14** | **L1** | **CONTROLE** | **1 186** | **54,47 %** |
| **15** | **L5** | **CONTROLE** | **266** | **56,77 %** (rang 1) |

Pour passer au pôle gagnant il faut échanger **un quart du deck** : **retirer** −2 Kanga (4→2), −3 Switch, −3 Xerosic, −2 Hilda, −1 Battle Cage, −1 Hand Trimmer, −1 Poffin ; **ajouter** +4 Team Rocket's Petrel, +2 Ultra Ball, +1 Cornerstone Mask Ogerpon ex, +2 Rock Fighting Energy, +1 Team Rocket's Factory, +2 Colress's Tenacity, +1 Tool Scrapper, +2 Boss's Orders (2→4), +1 Basic {G}.

---

## 3. Cartes discriminantes intra-archétype : un seul signal survit

**Unité = l'ÉQUIPE.** Test = Fisher exact haut (1-150) vs bas (>400).

### 3.1 Deux pièges de dénombrement, avant toute lecture de carte

**(a) 2 des 5 archétypes demandés sont INANALYSABLES en intra.** Archaludon ex + Cinderace : **0 équipe sur 120 dans le top-150**, 116/120 au-delà du rang 400. Mega Lucario ex + Hariyama : **1/66**. Il n'existe aucun « bon joueur » à qui comparer. **C'est le choix de l'archétype qui sépare, pas une carte dedans.**

**(b) `label_terrain` FUSIONNE des sous-archétypes.** Sous « Alakazam + Dudunsparce » vivent **3 `sig`** :

| sous-sig | n | 1-50 | 401-1000 |
|---|---|---|---|
| Alakazam + Kadabra | 206 | 18 | 98 |
| **Alakazam + Dudunsparce** (vraie ligne) | **46** | **0** | **41** |
| Kadabra + Alakazam | 13 | 0 | 7 |

Toute carte marquant la ligne Dudunsparce (`Neutralization Zone`, `Enriching Energy`) hérite mécaniquement de ce gradient — **3 des 9 « cartes discriminantes » initiales n'étaient que ses marqueurs. Il faut descendre au `sig`.**

### 3.2 Grimmsnarl + Froslass (291 équipes) — LISTE RÉSOLUE, zéro carte discriminante

**83,2 % jouent les 60 mêmes cartes** (19 listes distinctes, 17/29 cartes à ≥95 %). **Aucune carte n'atteint 15 pts d'écart, aucune n'est significative.** Écart moyen à la liste de référence : 0,30 slot/60 en top-50 vs 0,74 en bas (Mann-Whitney **p = 0,34**).

**Claim antérieur `Xerosic's Machinations` — VÉRIFIÉ ET REDIMENSIONNÉ :** le sens tient (**0/28** en top-50 vs **7/98** au-delà de 400) mais la fréquence en bas tombe de 19,4 % à **7,1 %** (le dénominateur de 36 sous-estimait le bas d'un facteur 2,7) et l'effet **n'est pas significatif** (Fisher **p = 0,347** ; 2 % vs 4 % en fenêtre août, p = 0,66). Seul appui restant : WR 43,6 % (601 parties, **3 decks**) vs 49,4 % (24 665 parties). **Ne pas construire dessus.**

### 3.3 Alakazam + Kadabra (206 équipes) — le gradient est une COURBE D'ADOPTION

Brut : Nighttime Mine +20,3 (p = 0,015), Fezandipiti ex +20,0 (p = 0,004), Shaymin +19,9 (p = 0,007), Battle Cage −16,4 (p = 0,032). Les trois premières forment **un paquet** (154 équipes ont les 3).

**Le contrôle qui tue le résultat :**

| carte | FRAIS haut/bas | p | STALE haut/bas | p |
|---|---|---|---|---|
| Fezandipiti ex | 17/18 vs 36/40 | **1,000** | 26/27 vs 38/58 | **0,002** |
| Nighttime Mine | 14/18 vs 31/40 | **1,000** | 25/27 vs 34/58 | **0,002** |
| Shaymin | 17/18 vs 34/40 | **0,417** | 25/27 vs 38/58 | **0,008** |
| Battle Cage | 4/18 vs 8/40 | **1,000** | 1/27 vs 19/58 | **0,002** |

**L'effet vit intégralement dans le stratum STALE et vaut exactement zéro dans le stratum FRAIS.** Cause visible : adoption méta de Fezandipiti ex — **juin 25 % → juillet 79 % → août 96 %** ; et les decks stale du bas sont plus vieux (date médiane 2026-07-16 vs 2026-07-28/08-02 en haut). **À fenêtre de date égale (≥2026-08-01, n=113) : +4,6 / +8,0 / +9,7 pts, tous ns.**

C'est **exactement la forme de fuite du « champ bimodal » réfuté le 27/07** : une variable de collecte corrélée à l'étiquette.

### 3.4 Crustle + Mega Kangaskhan — LE SEUL SIGNAL SURVIVANT

Ce ne sont pas 7 cartes, c'est **UNE variante** (patrons observés : `(0,0,0,0,0,0,0)` 52 équipes, `(1,1,1,1,1,0,0)` 12, `(1,1,1,1,1,1,1)` 6).

**Contrôle de date appliqué (decks vus ≥ 2026-08-01, n = 67) :**

| carte | haut (18) | bas (23) | grad | p |
|---|---|---|---|---|
| **Cornerstone Mask Ogerpon ex** | 61 % | 22 % | **+39,4** | **0,022 \*** |
| **Team Rocket's Factory** | 61 % | 26 % | **+35,0** | **0,031 \*** |
| **Basic {G} Energy** | 72 % | 100 % | **−27,8** | **0,011 \*** |
| **Battle Cage** | 61 % | 91 % | **−30,2** | **0,028 \*** |
| Hand Trimmer | 28 % | 48 % | −20,0 | 0,218 |
| Crushing Hammer | 39 % | 30 % | +8,5 | 0,742 |

**Appui indépendant (fenêtre août, decks à n≥50) :** variante **Cornerstone** = 20 équipes, rang médian **130**, **WR 54,3 % sur 1 362 parties** ; variante **Battle Cage** = 35 équipes, rang médian **259**, **WR 45,5 % sur 561 parties**.

### 3.5 Métrique de conformité (écart en slots/60 à la liste modale du top-150 du même sous-archétype)

| sous-archétype | 1-50 | 51-150 | 151-400 | 401-1000 | p (MW) |
|---|---|---|---|---|---|
| Grimmsnarl + Morgrem (283) | 0,30 | 0,64 | 0,48 | 0,74 | 0,34 |
| Alakazam + Kadabra (206) | 1,11 | 1,63 | 1,65 | **5,16** | 1,5e-4 |
| **Crustle + Mega Kangaskhan (75)** | **18,73** | **18,73** | **32,50** | **30,08** | **6,2e-3** |
| Cynthia's Gabite + Garchomp (41) | 0,57 | 0,50 | 2,60 | 4,12 | 0,58 |

**Crustle est le SEUL archétype sans consensus** (liste modale du top-150 = 6/22 seulement) — donc **le seul où un choix de liste peut encore payer**.

### 3.6 Deux réponses négatives, propres

- **Aucune carte, dans aucun des 6 archétypes, n'est jouée par 100 % du top-50 et 0 % du bas.** Le champ est trop standardisé pour qu'un tel séparateur existe.
- **Aucune preuve qu'un 3x contre un 4x sépare les rangs**, une fois la date contrôlée. Les 4 effets bruts d'Alakazam (Rare Candy 3x p=0,0012, Enhanced Hammer 4x p=0,0022, Dudunsparce 2x p=0,0031, Night Stretcher 1x p=0,0041) **meurent tous sur les decks frais** (p = 0,41 / 0,085 / 0,71 / 0,66). Ceux de Crustle sont **bimodaux (1x ou 4x)** = marqueurs de variante, pas réglage fin. Chez Grimmsnarl, le plus petit p sur 13 cartes est 0,167.
- **Cynthia's Garchomp ex : non concluant, pas « absent ».** À sous-sig constant (n=41), tous les écarts sont à p = 0,226 (15 équipes en top-150). `Premium Power Pro` (p=0,012 au label complet) redevient p = 0,226 après restriction.

---

## 4. Le gauntlet pondéré par le champ réel

### 4.1 Trois pondérations, trois champs différents

| Pondération | Ce qu'elle mesure | Quand l'utiliser |
|---|---|---|
| `poids_equipes` (1 équipe = 1 voix, fractionnée 1/k) | le champ **tel qu'il existe** | remonter le ladder ; **seule pondération qui voit les 342 équipes API** |
| `poids_parties` (base 55 917 parties d'archive) | le champ **tel qu'on le rencontre en haut** | défendre une position haute ; seule qui porte un WR exploitable |
| `poids_mixte` (moyenne, tri par défaut) | compromis | cible de rang encore indéterminée |

⚠ **Les 342 decks `source: api` valent 1 partie chacun = 0,608 % de la masse.** Une entrée API n'est pas « un deck peu joué », c'est **un deck NON MESURÉ**. Ils sont exclus du numérateur ET du dénominateur de `poids_parties`. **342 équipes sur 1000 sont 100 % API**, réparties 1 / 5 / 72 / **264** sur les tranches — **la pondération par parties efface essentiellement le bas du classement.**

Cas qui le prouve : la liste `Archaludon ex + Cinderace` (ordre 5) est jouée **à l'identique par 40 équipes** (rangs 439-904) avec **0 partie archivée** → poids-équipes 4,00 %, poids-parties 0,00 %. Netdeck bien réel, invisible au volume.

### 4.2 La pondération par RANG change tout

| Liste | global | 1-50 | 51-150 | 151-400 | 401-1000 |
|---|---|---|---|---|---|
| Marnie's Grimmsnarl ex + Froslass (r2) | 0,193 | 0,230 | **0,403** | 0,276 | 0,120 |
| Alakazam + Dudunsparce (r1) | 0,105 | 0,127 | 0,139 | 0,153 | 0,078 |
| **Archaludon ex + Cinderace (r439)** | 0,040 | **0,000** | **0,000** | 0,000 | **0,067** |
| **Mega Lucario ex + Hariyama (r388)** | 0,033 | **0,000** | **0,000** | 0,004 | **0,053** |
| Cynthia's Garchomp ex + Roserade (r13) | 0,026 | **0,058** | 0,044 | 0,025 | 0,021 |

**Deux des listes les plus lourdes du champ global n'existent pas au-dessus du rang 150.** Le gauntlet doit être **re-trié sur la tranche visée avant simulation**.

### 4.3 Combien d'adversaires simuler

| n listes | par équipes | par parties | par mixte |
|---|---|---|---|
| 5 | 40,5 % | 63,8 % | 50,1 % |
| 10 | 51,4 % | 73,0 % | 58,2 % |
| 20 | 62,2 % | 84,0 % | 68,4 % |
| **40 (livré)** | **70,1 %** | **93,0 %** | **78,3 %** |

Seuils divergents d'un ordre de grandeur : **3** listes pour 50 % des parties (16 pour 80 %, 49 pour 95 %) contre **10** listes pour 50 % des équipes (**124** pour 80 %, **274** pour 95 %). Le top-40 mixte effectivement livré couvre **68,0 % du champ-équipes et 88,5 % du champ-parties**.

**Par tranche (chaque tranche retriée en interne) :**

| tranche | listes distinctes | top5 | top10 | **top20** | top40 |
|---|---|---|---|---|---|
| 1-50 | 63 | 48,0 % | 61,3 % | **76,2 %** | 91,5 % |
| 51-150 | 55 | **64,9 %** | 73,9 % | **84,5 %** | **97,4 %** |
| 151-400 | 135 | 54,3 % | 62,8 % | **70,6 %** | 78,6 % |
| 401-1000 | 235 | 37,0 % | 48,3 % | **61,3 %** | 69,1 % |

**Le bas du ladder est presque trois fois plus diversifié que le haut.** Repli par archétype si la simulation carte-par-carte est trop chère : 5 archétypes = 72,9 % des équipes / 77,1 % des parties ; 10 = 82,8 % / 91,6 % ; 20 = 91,1 % / 98,3 % — **mais le repli n'efface pas le biais, il le concentre** (Archaludon : 11,95 % en équipes pour 0,11 % en parties).

### 4.4 Le champ est peuplé par ce qui se recopie, pas par ce qui gagne

| # | label | éq. | w_eq | w_part | WR | n arch | r_min |
|---|---|---|---|---|---|---|---|
| 1 | Marnie's Grimmsnarl ex + Froslass | 252 | 0,1931 | **0,3923** | 0,484 | 21 936 | 2 |
| 2 | Alakazam + Dudunsparce | 136 | 0,1054 | 0,0744 | 0,452 | 4 160 | 1 |
| 5 | **Archaludon ex + Cinderace** | 40 | **0,0400** | **0,0000** | n/a | **0** | 439 |
| 11 | **Crustle + Mega Kangaskhan ex (L1)** | 8 | 0,0047 | 0,0212 | **0,545** | 1 186 | 4 |
| 12 | **Dudunsparce + Mega Lopunny ex** | 10 | 0,0040 | 0,0184 | **0,597** | 1 030 | 1 |
| 17 | **Dragapult ex + Budew** | 9 | 0,0038 | 0,0152 | **0,588** | 849 | 11 |

Les deux archétypes les plus **présents** sont **sous 50 % de WR** ; `Mega Lopunny` (0,597, n=1030) et `Dragapult ex + Budew` (0,588, n=849) sont bien au-dessus et **quasi absents**. **C'est pourquoi il faut pondérer par PRÉSENCE et scorer par WR séparément.** Le tri mixte est ce qui garde à la fois `champ05/07/08` (lourds en équipes, nuls en volume) et `champ11/12` (l'inverse).

---

## CE QUE CES DONNÉES NE PEUVENT PAS DIRE

**Causalité — aucune, nulle part.**
- Rien n'est randomisé. Même pour Crustle/Cornerstone, l'alternative « les bons joueurs adoptent plus vite les listes récentes » n'est **pas exclue** : Cornerstone monte aussi dans le temps (juin 0/1, juillet 1/19, août 20/55). Le contrôle par fenêtre août réduit ce biais sans l'éliminer.
- La section 2.4 (mécanisme des murs) est une **lecture des textes de cartes**. Aucune partie n'a été simulée, aucune trace de replay lue. Que le mur Crustle/Cornerstone soit la **cause** du +9,78 est une hypothèse, pas un résultat.

**Attribution carte par carte — impossible dans Crustle.** Les composants du pôle CONTROLE sont quasi parfaitement colinéaires. **Seul le PAQUET ENTIER est mesuré, jamais ses pièces.** Le sous-gradient Crushing Hammer dans STOCK (48,2 % vs 41,7 %) est **confondu** (L2 contre L3/L4, équipes différentes) — ne pas le lire comme une valeur de carte.

**Robustesse statistique.**
- Le signal Crustle **ne survit pas à Bonferroni** : 32 cartes testables → seuil 0,0016, p obtenus 0,011-0,031. Il ne tient que parce que les 4 cartes bougent comme **un seul paquet** (un test effectif) et que WR + rang médian vont dans le même sens. **À re-tester sur échantillon indépendant avant d'en faire une règle.**
- Effectifs minuscules après conditionnement : Crustle fenêtre août = 18 haut / 23 bas ; Cynthia = 15 équipes en top-150. Un deck qui change bascule plusieurs points.
- Le test apparié repose **essentiellement sur UNE équipe** : 3 équipes sur 93 jouent les deux pôles, LiamK porte 134+93 des 157+95 parties. Un seul joueur n'établit pas une causalité de deck.
- Une équipe domine le pôle CONTROLE : `flg` (rang 22) porte **858 des 1 547 parties (55 %)** ; seules 8 équipes ont n≥20 dans CONTROLE.
- Q5 (71-73 % multi-decks) : la strate 200+ ne contient que **2 équipes** en 401-1000 ; l'égalité est établie sur n=37/24/7 et **extrapolée** au bas.

**Biais d'archive, assumé et non corrigé.**
- Tous les WR viennent des archives quotidiennes **biaisées vers le haut du classement**. Le WR 48,44 % de la liste n°1 décrit ce que ce deck fait **contre le haut**, pas contre le champ. 375 decks d'archive ont eux-mêmes n=1 : **« archive » ≠ « beaucoup de parties »**.
- **Aucun WR n'est une force intrinsèque** : une liste du top affronte un champ plus dur qu'une liste du rang 500. **Les WR ne sont pas comparables entre tranches.** L'écart +9,78 pts n'est **PAS** une espérance de gain en tête-à-tête.
- `mesure_en_parties: aucune` signifie **volume INCONNU, jamais volume nul**. 2 des 40 entrées livrées (dont `champ05`) ont 0 partie mesurée. Le fait que les entrées API ne pèsent que 0,6 % **n'est pas la preuve que le bas joue peu, c'est la preuve qu'on ne l'observe pas**.

**Fraîcheur.**
- **423 équipes sur 1000 sont stale partout**, et la fraîcheur chute avec le rang (39/50, 64/100, 167/250, 307/600). Les poids du bas décrivent un champ **de juin/juillet reconstitué**. Le champ réel au 16/08 peut avoir bougé.
- `stale` et « date du dernier jour vu » sont deux **proxys imparfaits** : un deck marqué frais peut avoir été soumis avant sa dernière partie observée. Les decks API sont frais **par construction** — `fresh` et `source=api` ne sont pas des contrôles indépendants (d'où le contrôle archive-seule mené séparément).

**Angles morts structurels.**
- **Rien ici ne mesure le JEU.** Deux équipes avec les 60 mêmes cartes et 200 rangs d'écart sont **indiscernables**. Chez Grimmsnarl (83 % sur la même liste), c'est **nécessairement là que vit l'écart** — et c'est précisément ce que ces données ne peuvent pas atteindre. Le WR d'une liste agrège des pilotes hétérogènes (L3 : 28 équipes, WR par équipe de 23,1 % à 49,3 %).
- L'absence de signal chez Grimmsnarl **ne prouve pas qu'aucune carte ne compte** : elle prouve que **personne ne dévie**, donc qu'aucune déviation n'est observable. Un slot flexible non exploré par le champ reste invisible.
- Archaludon et Mega Lucario ne sont **pas « mauvais » de façon établie** : ils sont absents du haut de l'échantillon de replays disponible.
- L'exclusivité haut/bas dépend de la définition des tranches **et du choix `decks[0]`** : toute liste d'exclusivité doit être relue avec le **rang minimum sur l'ensemble des slots**.
- Le fractionnement 1/k du vote multi-decks est une **convention, pas une mesure** : une équipe à 6 decks est traitée comme 6 × 1/6.
- Les cumuls par tranche **supposent qu'on affronte son voisinage Elo** — aucun appariement réel n'a été extrait des épisodes pour confirmer la largeur de la fenêtre.
- L'origine commune de la liste n°1 est établie ; **sa nature ne l'est pas** (notebook public / starter kit / forum). Rien dans le fichier ne porte cette information.

---

## ACTIONS

### A. Ce que l'outil de deckbuilding doit changer (par valeur attendue décroissante)

**A1 — Reconstruire l'EV Crustle depuis le squelette CONTROLE (L1), pas STOCK. [valeur : la plus haute, et de loin]**
C'est le **seul** levier de deck mesuré, contrôlé et survivant du dossier. Notre candidat est à 2 cartes du perdant, 14 du gagnant. Concrètement, dans le générateur :
- **Contraindre en dur** : `Cornerstone Mask Ogerpon ex` 1x, `Rock Fighting Energy` 2x, `Team Rocket's Factory` 1x, `Ultra Ball` 2x, `Team Rocket's Petrel` 4x, `Boss's Orders` **4x**, `Colress's Tenacity` 2x, `Tool Scrapper` 1x, `Mega Kangaskhan ex` **2x**, `Crustle` 3x.
- **Interdire / plafonner** : `Battle Cage` ≤1x (jamais 2x : 91 % du bas vs 61 % du haut), `Basic {G}` ≤2x (100 % du bas vs 72 % du haut), `Hand Trimmer` 0, `Shaymin` 0, `Xerosic's Machinations` 1x (pas 4x), `Switch` 1x (pas 4x).
- Liste de référence à battre : **L1** (1 186 parties, 54,47 %, rangs 4/17/22) ; variante haute **L5** = L1 +4 Crushing Hammer +1 Hilda +1 Cook, −2 Colress, −1 Tool Scrapper, −1 Battle Cage, −2 Basic {G} (266 parties, 56,77 %, rang 1).

**A2 — Retirer du scoring toute feature corrélée à la DATE ou à l'EXPOSITION. [valeur : haute, purement défensive]**
Deux fuites confirmées de la même famille que le « champ bimodal » réfuté le 27/07 :
- toute carte dont l'écart haut/bas meurt sur les decks frais (Fezandipiti, Nighttime Mine, Shaymin, Battle Cage chez Alakazam ; les 4 comptages de copies) ;
- toute feature dérivée de `n_decks_distincts` ou `n_parties_vues` — elles encodent la couverture d'archive, pas la stratégie.
**Règle à câbler : tout écart haut/bas doit être re-testé (a) à sous-`sig` constant, (b) en fenêtre de date fixe (≥2026-08-01), (c) stratifié frais/stale. Les trois, ou l'écart ne compte pas.**

**A3 — Descendre au `sig`, jamais au `label_terrain`. [valeur : haute, corrige 3 faux positifs déjà identifiés]**
`label_terrain` fusionne des decks distincts (Alakazam → 3 sig ; Crustle → 2 ; Cynthia → 2 ; Grimmsnarl → 2). Et **canoniser les listes par MULTISET des 60 cardId**, pas par ids ordonnés : 430 entrées → **398 listes**, la n°1 passe de 239 à 252 équipes.

**A4 — Paramétrer le gauntlet par TRANCHE VISÉE. [valeur : moyenne-haute, conditionne tout le temps de calcul]**
Fixer la cible **avant** de choisir les adversaires, puis retrier sur `poids_par_tranche_de_rang`. Simuler les **20 premières listes de la tranche** (≥70 % du champ local partout, 84,5 % en 51-150). Pondérer les matchups par `poids_equipes` si on remonte, par `poids_parties` si on défend. **Ne jamais lire un `wr_observe` sans `wr_fiable` / `wr_ic95` / `mesure_en_parties`.**

### B. Ce qu'il faut soumettre (Simulation, 16/08)

**B1 — Le deck : Crustle + Mega Kangaskhan ex, variante CONTROLE (base L1/L5).**
Pourquoi celui-là et pas Grimmsnarl :
- **C'est le seul archétype du champ SANS consensus** (liste modale du top-150 = 6/22 ; écart de conformité 18,7 vs 30-32 slots, p = 6,2e-3). C'est donc **le seul où un choix de liste peut encore payer** — ailleurs, la liste est résolue et 83 % du champ la joue.
- Appui empirique convergent : WR 54,69 % vs 44,91 % (Wilson disjoints), rang médian 130 vs 259, joué par les rangs **1, 4, 8, 17, 22, 23**.
- **Deck Score (20 %) : le concept se raconte en une phrase et s'aligne carte par carte** — *invulnérabilité sélective (Crustle immunise contre les ex, Cornerstone contre les Talents, Rock Fighting contre les effets) + tuteur autofinancé (Petrel/Factory, qui rend jouable une bibliothèque de 1-of) + pince offensive (Boss's Orders 4x pour aller chercher la clé sur le banc)*. Chaque inclusion se justifie par le plan, pas par le méta.
- **Model Score (70 %) : le plan de contrôle est structurellement moins dépendant de l'état initial** qu'un plan de course aux dégâts — c'est l'argument de « stabilité sur matchs répétés » et de « non-dépendance aux états initiaux » à défendre dans le rapport, **mais il doit être MESURÉ (voir C1), pas asserté.**

**B2 — Grimmsnarl + Froslass : ne rien changer, ne pas y investir.**
Si on le soumet, jouer la liste consensus telle quelle (17 cartes à ≥95 %). Les 4 slots flexibles (`Pokégear 3.0`, `Tool Scrapper`, `Handheld Fan`, `Judge`) sont **plats**. Tenir `Xerosic's Machinations` dehors reste raisonnable (0/28 en top-50) mais **ce n'est pas un résultat** (p = 0,347) : ne rien construire dessus. **Le gain n'est pas dans la liste, il est dans le jeu.**

**B3 — Alakazam + Kadabra : si soumis, jouer la liste d'août pour une raison de DATE, pas de rang.**
Inclure `Fezandipiti ex` + `Nighttime Mine` + `Shaymin` non parce qu'ils séparent les rangs (ils ne le font pas : +4,6/+8,0/+9,7 pt ns en août) mais parce que **96 % du champ d'août les joue** — ne pas les jouer, c'est jouer la liste de juillet. **Ne PAS basculer sur le `sig` `Alakazam + Dudunsparce`** (0/46 en top-50, 41/46 au-delà du rang 400) ; exclure `Battle Cage` et `Neutralization Zone`, marqueurs de cette ligne perdante.

**B4 — Ne pas soumettre Archaludon + Cinderace ni Mega Lucario + Hariyama.** 0/120 et 1/66 dans le top-150. Le levier est de **changer de deck**, pas de le régler. (Réserve : leur faiblesse n'est pas *établie*, seulement leur absence du haut de l'échantillon.)

### C. Ce qui reste à mesurer (par valeur décroissante)

**C1 — La stabilité, qui pèse 70 % et n'est mesurée NULLE PART dans ces 4 analyses.** Aucune ligne de ce document ne touche à la variance sur matchs répétés ni à la sensibilité aux états initiaux. Il faut : rejouer chaque liste candidate ×N contre le gauntlet de la tranche, à graines variées, et **rapporter la variance et la sensibilité au mulligan/pile de départ** — c'est le livrable qui rapporte le plus de points au barème et il n'existe pas encore.

**C2 — Le pôle CONTROLE sur un échantillon indépendant.** Le signal ne passe pas Bonferroni, tient sur 18 vs 23 équipes en fenêtre août, et son test apparié repose sur un joueur. **Re-mesurer sur un snapshot postérieur au 2026-08-04 avant d'en faire une règle.**

**C3 — Le tête-à-tête CONTROLE vs STOCK par simulation directe.** +9,78 pts est un WR contre des champs différents, pas une espérance de gain en duel. Une simulation L1 contre L3 le trancherait — et c'est du calcul, pas de la statistique observationnelle.

**C4 — La largeur de la fenêtre d'appariement Elo.** Toute la stratégie « re-trier le gauntlet par tranche » suppose qu'on affronte son voisinage. **Non vérifié** : aucun appariement réel n'a été extrait des épisodes.

**C5 — Le volume réel des 342 équipes API**, dont les 40 clones d'Archaludon (rangs 439-904, 0 partie archivée). Tant qu'il est inconnu, `poids_equipes` est un plancher et `poids_parties` un aveuglement — ni l'un ni l'autre n'est le champ.

**C6 — Cynthia's Garchomp ex : à re-mesurer quand l'archétype aura ≥40 équipes fraîches.** Tendances non significatives seulement (`Night Stretcher`, `Forest of Vitality`, `Hilda`, `Xerosic` à 100 % en top-150 vs 81 % en bas, p = 0,226).

## 04/08 — DECK ou PILOTE ? la decomposition, sur les 1000 equipes couvertes

| mesure | valeur |
|---|---|
| listes exactes de 60 cartes distinctes | 323 (deck courant) / 402 (toutes entrees) |
| couverture des **6 listes** les plus jouees | **42,4 %** des equipes |
| couverture des **6 ARCHETYPES** les plus joues | **75,3 %** des equipes |
| variance du rang expliquee par la LISTE EXACTE (eta^2) | **0,381** |
| variance du rang expliquee par l'ARCHETYPE (eta^2) | **0,246** |
| ecart de rang median entre 2 equipes a la MEME liste | **233 rangs** (26 195 paires) |
| ecart de rang median entre 2 equipes au hasard | 291 rangs |
| **reduction d'incertitude apportee par le deck** | **19,9 %** |

Etendue de rang A LISTE STRICTEMENT CONSTANTE (les 60 memes cartes) :

| liste | equipes | rang min | median | rang max | etendue |
|---|---|---|---|---|---|
| Marnie's Grimmsnarl ex + Froslass | 185 | **3** | 294 | **968** | 965 |
| Alakazam + Dudunsparce | 105 | **6** | 355 | **971** | 965 |
| Cynthia's Garchomp ex + Roserade | 26 | 13 | 393 | 982 | 969 |
| Crustle + Mega Kangaskhan ex | 21 | 30 | 463 | 882 | 852 |

🔑🔑 **Le deck fixe un PLAFOND, le pilote fixe la PLACE sous ce plafond.** Les 965 rangs
d'ecart a liste strictement identique ne peuvent venir que du pilotage et de la variance ;
symetriquement, `Archaludon ex + Cinderace` n'apparait JAMAIS avant le rang 331 quel que soit
son pilote (etendue 439-904). C'est la lecture qui reconcilie les deux : choisir un deck ne
place pas, il autorise ou interdit une zone.

⚠ eta^2 monte avec le nombre de groupes ; les 0,381 / 0,246 sont des BORNES HAUTES de la part
du deck. La mesure robuste est la reduction d'incertitude : **19,9 %**.
⚠ 546/1000 equipes seulement ont un deck frais ; la fraicheur chute avec le rang (39/50 en
tete, 304/600 en bas). Les rangs bas sont surtout reconstitues par archives anciennes ou par
un episode API isole.
