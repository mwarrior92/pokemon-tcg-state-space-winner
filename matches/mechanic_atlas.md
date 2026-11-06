# Atlas des capacites — schema v25

**87 scalaires d'option** (ce que l'IA lit de CHAQUE choix possible) et **133 scalaires d'etat** (ce qu'elle lit du PLATEAU), soit **220 canaux de perception**.

> Genere par introspection du code (`tools/capability_atlas.py`). Les densites sont MESUREES sur un echantillon etale du corpus reel, jamais estimees.

## 1. LIRE L'OPTION

*Ce que la carte proposee EST, avant tout jugement.*

| canal | horizon | non nul | poids mesure | ce qu'il mesure |
|---|---|---|---|---|
| `rank_abs` | · instant | 26.5 % | (2.9 % v20) | Position de l'option dans le menu du moteur, qui les ordonne du meilleur au pire. Le NULL du projet est `[0]`, pas l'aleatoire. |
| `rank_rel` | · instant | 26.5 % | (12.9 % v20) | Meme position, relative au nombre d'options. |
| `is_first` | · instant | 4.4 % | (1.7 % v20) | L'option est-elle la premiere proposee. |
| `has_card` | · instant | 24.2 % | (3.4 % v20) | L'option porte-t-elle une carte identifiable. |
| `has_attack` | · instant | 1.4 % | (2.3 % v20) | L'option est une ATTAQUE. Rare : 1,5 % des lignes. |
| `is_pokemon` | · instant | 8.3 % | (2.8 % v20) | La carte est un Pokemon. |
| `is_energy` | · instant | 7.6 % | (4.6 % v20) | La carte est une Energie. |
| `is_trainer` | · instant | 8.3 % | (2.4 % v20) | La carte est un Dresseur. |
| `opt_retreat` | · instant | 8.1 % | (1.0 % v20) | Cout de retraite de la carte : la mobilite, donc la capacite a sortir un attaquant piege. |
| `opt_cant_attack` | · instant | 0.1 % | — | La carte porte une CONDITION d'attaque (`Power Saver` interdit d'attaquer sans 4 Pokemon Rocket en jeu). |
| `opt_energy_units` | · instant | 0.3 % | — | Unites d'energie fournies. `Team Rocket's Energy` en vaut DEUX : l'attacher vaut deux fois un basique. |
| `opt_ends_turn` | 🔁 tour courant | 3.8 % | (1.2 % v20) | Cette option TERMINE le tour (ATTACK ou END). C'est la brique du jeu par sequence : un joueur fort epuise tout ce qui ne coupe pas le tour avant de couper. Regle du jeu, pas frequence. 12,9 % des options. |
| `opt_is_supporter` | · instant | 3.6 % | (2.6 % v20) | L'option est un SUPPORTER : un seul par tour, donc la jouer consomme une ressource unique du tour. |
| `opt_search_to_bench` | · instant | 1.9 % | (1.5 % v20) | L'option cherche un Pokemon et le pose AU BANC : c'est du developpement, pas de la pioche. |
| `opt_search_energy` | · instant | 1.4 % | (1.4 % v20) | L'option cherche une ENERGIE dans le deck. |
| `slot_valid` | · instant | 11.4 % | — | ⚖ v22 — LE DRAPEAU QUI REND LES CINQ SUIVANTES LISIBLES : le slot vise par cette option a-t-il ete IDENTIFIE ? Sans lui, zero signifierait a la fois « slot inconnu » et « slot connu, valeur nulle » — ce depot a paye cette confusion (un ZERO qui remplace un INCONNU ne s'annonce pas comme une absence de mesure, il CONCOURT comme une mesure). La recuperation S'ABSTIENT plutot que de deviner. |
| `slot_energy` | · instant | 3.5 % | — | ⚖ v22 — energies POSEES sur le candidat vise. ⛔ LE TROU LE PLUS COUTEUX FERME PAR CE SCHEMA : deux exemplaires de la MEME carte dans deux slots differents rendaient des lignes d'option RIGOUREUSEMENT IDENTIQUES hors rang, donc le choix se decidait par la POSITION dans le menu — indecidable par construction, qu'aucun volume de corpus ne pouvait corriger. Mesure : 108 205 groupes d'options a ligne identique mais etat de slot DIFFERENT, soit 42,8 par PARTIE. |
| `slot_dmg_frac` | · instant | 2.1 % | — | ⚖ v22 — part de PV deja perdue par le candidat. Promouvoir un Pokemon a 10 PV le fait mourir au checkup et offre deux prix : cas MESURE sur replay reel. |
| `slot_maxhp` | · instant | 11.4 % | — | ⚖ v22 — PV maximum du candidat : un mur et une carte fragile ne se promeuvent pas pour la meme raison. |
| `slot_atk_ready` | · instant | 1.7 % | — | 🔑 v22 — LA COLONNE QUI PORTE LA DECISION DE PROMOTION : ce candidat a-t-il son attaque EN LIGNE (energies posees >= cout minimum d'une de ses attaques) ? C'est la question meme que le reseau ne pouvait pas poser, et la cause mesuree d'une promotion a 0 energie devant un attaquant charge a 3 avec un KO immediat. ⚠ Compare des UNITES et non des types (les energies de BANC ne portent que des comptes) : c'est une BORNE, pas une certitude. |
| `slot_is_op` | · instant | 1.0 % | — | ⚖ v22 — de quel COTE est le slot vise. Un gust designe LEUR banc, une promotion le NOTRE : deux intentions opposees sous des lignes jusqu'ici identiques. Le champ `ar` du record portait la zone et n'etait lu par AUCUNE ligne d'`encode` — il l'est enfin, par la voie qui resout aussi l'index. |
| `slot_debloque` | · instant | 2.5 % | — | 🔑 v23 — CETTE ATTACHE COMPLETE-T-ELLE UN COUT ? `slot_atk_ready` decrit l'AVANT ; celle-ci decrit l'APRES, c'est-a-dire le seul effet qui compte quand on route une energie. Mesure : 62 attachements sur 294 (21,1 %) mettent EFFECTIVEMENT une attaque en ligne, et les 6 erreurs de routage relevees l'exigent TOUTES (6/6). ⚠ Vivante a 1,34 % seulement — c'est peu, et c'est attendu : la question ne se pose que sur les menus d'attache. |
| `slot_survie` | · instant | 10.2 % | — | ⚖ v23 — le slot vise SURVIT-il au tour adverse previsible. Ajoutee dans le meme geste que `slot_debloque`, sur le meme constat : router une energie vers un porteur qui meurt avant d'attaquer est la sous-classe d'erreur a l'association la plus franche du corpus (53 attachements sur 294, p = 0,0001 au denominateur PARTIE). ⛔ Lire ce p AVEC la correction de Holm (docs/29) : 13 classes testees ensemble, aucune ne survit. La colonne se justifie par sa CONSTRUCTIBILITE, pas par ce lien. |
| `slot_fresh` | · instant | 2.1 % | — | 🔑 v25 — le candidat vise a ete POSE CE TOUR, donc il **ne peut pas evoluer**. Sur un menu EVOLVE c'est la moitie de la question, et le reseau devait la deviner depuis rien. |
| `slot_tools` | · instant | 0.4 % | — | ⚖ v25 — le candidat porte-t-il DEJA un outil. Un outil attache en interdit un second, et `Hero's Cape` (+100 PV) deplace le letal : attacher sur un porteur occupe est un coup perdu, indistinguable avant. |
| `slot_atk_ready_type` | · instant | 1.7 % | — | 🔑 v25 — LA VERSION EXACTE DE `slot_atk_ready`. Celle-ci compare des UNITES : trois energies incolores s'y annoncent pretes pour un cout {R}{R}{C}. Ici on verifie PAR TYPE via `_cout_payable`, qui n'admet aucun arbitrage. ⚖ On AJOUTE au lieu de corriger en place, pour que l'ablation puisse dire ce que le type apporte — corriger effacerait la comparaison. ⚠ Sur un enregistrement d'avant le 05/08 les identites manquent : la colonne retombe sur la lecture par unites plutot que d'ecrire un faux zero. Mesure : leve sur 6,50 % des lignes contre 1,94 % pour la version par unites. |
| `opts_nonterm_frac` | 🔁 tour courant | 99.5 % | (2.3 % v20) | Part des options legales qui ne coupent PAS le tour. A 0, attaquer ne coute rien ; a 0,8, attaquer jette sept actions. Pendant d'etat de `opt_ends_turn`. |

## 2. CALCULER LES DEGATS

*Combien cette attaque enleve reellement. Le pole le plus rentable du projet : sa correction a paye +130,7 points.*

| canal | horizon | non nul | poids mesure | ce qu'il mesure |
|---|---|---|---|---|
| `atk_dmg` | · instant | 1.3 % | (1.1 % v20) | Degats de l'attaque, TOUTES corrections incluses : base + multiplicateur + pile ou face + conditionnel + cible libre + bonus d'outil, puis faiblesse x2 / resistance -30. |
| `atk_dmg_frac` | · instant | 1.3 % | (4.6 % v20) | Ces degats rapportes aux PV de la cible. |
| `atk_lethal` | · instant | 0.6 % | (3.9 % v20) | L'attaque TUE l'actif adverse. Verifie contre le moteur : 154 annonces, 154 KO reels, ZERO faux positif. |
| `atk_random` | · instant | 0.0 % | (8.8 % v20) | Le degat est une ESPERANCE (pile ou face), pas une certitude. Distinguer les deux evite d'apprendre une garantie fausse. |
| `atk_bench_dmg` | · instant | 0.4 % | (0.0 % v20) | Degats de BANC (spread). `Phantom Dive` +60, `Shadow Bullet` +30 : ce qui gagne la course, deux KO au lieu d'un. |
| `atk_self_dmg` | · instant | 0.0 % | — | Recul : l'attaque nous blesse aussi. |
| `atk_bench_split` | · instant | 0.0 % | — | Le degat de banc est-il un BUDGET a repartir (`Phantom Dive`, 60 au TOTAL) ou un montant sur UNE cible (`Shadow Bullet`, 30) ? Les confondre annonce trois prix la ou il y en a un. 3 attaques du pool, dont le moteur de Dragapult. |
| `atk_ignores_wr` | · instant | 0.0 % | — | L'attaque ignore la Faiblesse et/ou la Resistance. ⛔ La clause RESISTANCE n'etait traitee nulle part : nous retirions 30 degats a tort sur `Rock Hurl` et `Cosmic Beam`, et le x2 fantome contaminait AUSSI huit colonnes d'etat via `_max_dmg_vs`. |
| `atk_self_lock` | · instant | 0.0 % | — | L'attaque se VERROUILLE elle-meme : elle ne peut pas etre rejouee au tour suivant (`Mega Brave` 270). Un degat affiche sans son cout de rechargement est un degat surestime. |
| `atk_needs_partner` | · instant | 0.0 % | — | L'attaque exige un PARTENAIRE en jeu et ne fait RIEN sans lui : `Cosmic Beam` affiche 70 et vaut zero sans Lunatone. Trouve par l'auditeur a vocabulaire ouvert. |
| `atk_pierces` | · instant | 0.1 % | (5.3 % v20) | Les degats IGNORENT les effets de protection de la cible (bouclier, prevention). |
| `eff_hp_buff` | · instant | 0.4 % | (3.3 % v20) | Outil qui ajoute des PV (`Hero's Cape` +100). Deplace le letal des DEUX cotes. |
| `eff_dmg_buff` | · instant | 0.3 % | (0.0 % v20) | Outil qui ajoute des degats (`Brave Bangle` +30). Integre au calcul de letal de notre attaquant. |
| `eff_dmg_shield` | · instant | 0.0 % | — | La carte REDUIT les degats subis en jeu. `Full Metal Lab` (stade) blinde les DEUX camps de 30 : notre calcul de KO est faux sans lui. |
| `eff_hp_debuff` | · instant | 0.0 % ⛔ | — | La carte RETIRE des PV en jeu. `Gravity Mountain` : -30 PV a chaque Stade 2, des deux cotes. Le motif de `eff_hp_buff` exigeait un `+` — le signe qui RAPPROCHE le letal n'etait lu par rien. |
| `eff_attack_twice` | 🔁 tour courant | 0.0 % | — | Permet d'attaquer DEUX fois dans le tour. ⚠ Le texte porteur est sur une CAPACITE, pas sur l'attaque : cette colonne a d'abord ete placee dans le bloc ATTAQUE, donc lue a l'envers. |
| `abil_selfko_dmg` | · instant | 0.0 % | — | Degats infliges par une CAPACITE qui se sacrifie. `Cursed Blast` (Dusknoir) pose 130 degats n'importe ou. |
| `atk_lethal_bench` | · instant | 0.1 % | — | L'attaque tue au moins un Pokemon du BANC adverse. Ferme les 17,2 % de KO reels que `atk_lethal` (actif seul) n'annoncait jamais. 2,3 % des options d'attaque. |
| `op_immune_to_me` | · instant | 2.2 % | (5.7 % v20) | L'adversaire est IMMUNISE a notre attaquant (classe Crustle : annule les {ex}). Nos degats valaient litteralement ZERO et nous annoncions des letaux. |
| `bench_dmg_off` | · instant | 18.4 % | (1.3 % v20) | Les degats de BANC sont ETEINTS (`Battle Cage`, Shaymin) : cela desarme le plan entier de 44 % du champ. |

## 3. LIRE LES CAPACITES

*Ce que la carte FAIT au-dela de ses degats.*

| canal | horizon | non nul | poids mesure | ce qu'il mesure |
|---|---|---|---|---|
| `abil_present` | · instant | 16.5 % | (2.9 % v20) | La carte a une capacite. 20,8 % des options. |
| `abil_energy` | · instant | 0.9 % | (4.3 % v20) | Acceleration d'energie (`Punk Up` : 5 gratuites a l'evolution, le moteur du deck le plus joue du format). |
| `abil_draw` | · instant | 3.5 % | (1.4 % v20) | Pioche N cartes. |
| `abil_heal` | · instant | 1.0 % | (0.5 % v20) | Soigne / retire des marqueurs de degats. |
| `eff_search` | · instant | 6.4 % | (2.2 % v20) | Cherche dans le deck, y compris « regarde les N premieres cartes » (Pokegear, Bug Catching Set, Recon Directive). |
| `eff_gust` | · instant | 0.7 % | (1.7 % v20) | Rappelle un Pokemon du banc adverse (`Boss's Orders`) : la carte qui decide QUELLE cible on attaque. |
| `eff_prevent` | · instant | 1.0 % | (2.8 % v20) | Empeche les degats ou les EFFETS d'attaque. |
| `eff_disrupt` | · instant | 0.5 % | (1.5 % v20) | Defausse des ressources adverses (energie, outils, main). |
| `eff_switch` | · instant | 0.4 % | (1.6 % v20) | Change l'actif ou modifie la retraite. |
| `atk_status` | · instant | 0.0 % | — | L'attaque inflige un etat special. |
| `atk_effect` | · instant | 0.2 % | (6.9 % v20) | L'attaque porte un effet non dommageable. Drapeau GROSSIER assume : signale qu'il se passe autre chose. |
| `atk_deny` | · instant | 0.0 % | — | L'attaque PRIVE l'adversaire au tour suivant (retraite, Objets). `Itchy Pollen` : « la principale facon de perdre ». |
| `eff_handsize` | · instant | 1.1 % | (1.6 % v20) | Disruption de MAIN (`Unfair Stamp` ramene l'adversaire a 2 cartes). |
| `eff_abilock` | · instant | 0.0 % | — | Verrou de capacites (`Watchtower`), des 2 cotes. |
| `abil_transfer` | · instant | 0.9 % | (0.0 % v20) | DEPLACE des marqueurs vers l'ADVERSAIRE (`Adrena-Brain`). Offensif — c'etait confondu avec un soin. |
| `eff_recover` | · instant | 0.7 % | (2.2 % v20) | Recupere depuis la DEFAUSSE (`Night Stretcher`, `Sacred Ash`, `Lana's Aid`). Present dans les 4 listes du champ. |
| `eff_evo_skip` | · instant | 0.2 % | (2.8 % v20) | `Rare Candy` : saute le Stade 1, un TOUR gagne. |
| `eff_random` | · instant | 0.0 % | — | L'effet d'un DRESSEUR depend d'une piece (`Crushing Hammer`). Jouer 50 % comme une certitude est une faute. |
| `eff_cost_up` | · instant | 0.3 % | (0.0 % v20) | Rencherit le cout des attaques (`Nighttime Mine`). |
| `eff_use_condition` | · instant | 0.5 % | (1.8 % v20) | L'effet est CONDITIONNEL (« seulement si... ») : son esperance n'est pas sa valeur affichee. |
| `eff_heal_amount` | · instant | 0.1 % | (3.4 % v20) | MONTANT de soin. Le soin etait invisible sur 21 cartes sur 21, dont `Jumbo Ice Cream` (x4 chez Crustle) classe a tort en acceleration d'energie — l'effet exactement inverse. |
| `eff_status` | · instant | 0.0 % | (2.6 % v20) | Une condition speciale infligee par un DRESSEUR ou une CAPACITE. `atk_status` ne lit que les ATTAQUES : `Lisia's Appeal` rappelle un Pokemon du banc adverse ET le rend Confus, et nous ne voyions que le rappel. |
| `op_effect_immune` | 🪞 miroir | 13.1 % | (12.4 % v20) | L'adversaire est immunise aux EFFETS d'attaque (`Mist Energy`) : statuts et deplacements ne prennent pas. |

## 4. LA COURSE AUX PRIX

*La seule ressource qui termine la partie.*

| canal | horizon | non nul | poids mesure | ce qu'il mesure |
|---|---|---|---|---|
| `atk_prizes` | · instant | 0.6 % | (2.6 % v20) | Nombre de PRIX que cette attaque rapporte, actif ET banc, avec le decompte exact de `Legacy Energy`. Une attaque qui prend deux prix n'est pas une attaque qui en prend un. 53 % des attaques. |
| `opt_gust_prizes` | · instant | 0.3 % | (2.2 % v20) | Prix que rapporterait la cible qu'on peut ARRACHER du banc (`Boss's Orders`). Un gust sur un {ex} vaut deux prix, pas un. |
| `my_prize` | 🏁 terminal | 98.8 % | (4.3 % v20) | Prix qu'il NOUS reste a prendre. |
| `op_prize` | 🏁 terminal | 98.9 % | (3.8 % v20) | Prix qu'il LEUR reste a prendre. |
| `prize_diff` | 🏁 terminal | 55.7 % | (3.3 % v20) | L'ecart brut. |
| `my_active_prizes` | · instant | 100.0 % | (1.9 % v20) | Valeur en PRIX de notre actif (1, 2 ou 3). ⚠ MESURE : plus elle est HAUTE, plus on gagne (49,9 / 59,9 / 58,2 % a 1 / 2 / 3 prix). Ce n'est pas un passif. |
| `op_active_prizes` | · instant | 100.0 % | (1.1 % v20) | Valeur en PRIX de LEUR actif. ⚠ MESURE : plus elle est haute, plus ILS gagnent (AUC 0,4877 pour nous, donc sous 0,5). Ce n'est pas une proie. |
| `active_prize_gap` | · instant | 41.1 % | (2.3 % v20) | Ecart de valeur en prix entre les deux actifs (leur - le notre). ⚠ MESURE : ANTI-correle a notre victoire (AUC 0,4796 ; 59,8 % a -2 contre 44,9 % a +2, monotone). Le nom ne porte AUCUNE direction : lire la mesure, pas l'intuition. |
| `op_multiprize_frac` | · instant | 59.2 % | (0.3 % v20) | Part de leur plateau qui vaut 2 ou 3 prix. |
| `my_ko_to_win` | 🏁 terminal | 98.8 % | (2.8 % v20) | Combien de KO pour FERMER la partie. Deux prix restants contre des basiques = 2 KO ; contre un ex = 1. |
| `op_ko_to_win` | 🏁 terminal | 98.9 % | (2.2 % v20) | Idem pour eux. |
| `race_margin` | 🏁 terminal | 100.0 % | (0.9 % v20) | Qui gagne la course, en KO et non en prix. |
| `my_hp_per_prize` | · instant | 94.9 % | (1.3 % v20) | PV par prix concede : l'efficacite d'un mur. 200 PV pour 1 prix est un mur, pour 2 prix un cadeau. |
| `op_hp_per_prize` | · instant | 93.6 % | (1.2 % v20) | Idem pour leur actif. |
| `my_best_wall` | · instant | 94.3 % | (1.6 % v20) | Le meilleur mur disponible sur notre banc. |
| `tool_math` | · instant | 13.9 % | (0.4 % v20) | Somme des bonus d'outils en jeu (PV + degats). |
| `deckout_lead` | 🏁 terminal | 93.1 % | (1.7 % v20) | Avance au DECK-OUT : qui epuise sa pioche en premier perd, et cela decide ~14 % des parties. |
| `gust_exposure` | 🪞 miroir | 43.4 % | (1.8 % v20) | Notre EXPOSITION a un gust adverse : combien il gagnerait a arracher notre banc plutot qu'a frapper l'actif. |

## 5. MENACE ET TRAJECTOIRE

*Ce qui va arriver, pas ce qui est.*

| canal | horizon | non nul | poids mesure | ce qu'il mesure |
|---|---|---|---|---|
| `atk_selfguard` | · instant | 0.0 % | — | L'attaque nous PROTEGE au tour adverse suivant (`Metal Defender` : plus de Faiblesse ; `Frost Barrier` : -30 degats ; `Dig` : tout prevenu). ⚠ A ne pas confondre avec `atk_deny`, qui prive l'adversaire d'une ACTION : celle-ci change ce que son attaque lui RAPPORTE. |
| `eff_counter_dmg` | · instant | 0.3 % | (6.4 % v20) | Degats RENVOYES a l'attaquant. Change le calcul de qui gagne un echange. |
| `my_active_hp` | · instant | 94.9 % | (3.1 % v20) | PV de notre actif. |
| `op_active_hp` | · instant | 93.6 % | (2.5 % v20) | PV de leur actif. |
| `ko_now` | · instant | 21.8 % | (9.3 % v20) | On tue MAINTENANT. |
| `ko_margin` | · instant | 92.7 % | (4.5 % v20) | De combien on depasse (ou manque) le letal. |
| `threat_now` | 🪞 miroir | 29.7 % | (2.0 % v20) | ILS tuent maintenant. |
| `threat_margin` | 🪞 miroir | 94.0 % | (2.2 % v20) | Marge de leur menace. |
| `my_status` | · instant | 0.2 % | (6.1 % v20) | Etat special sur notre actif. |
| `op_status` | · instant | 0.2 % | (7.7 % v20) | Etat special sur le leur. |
| `my_dmg_ratio` | · instant | 30.1 % | (3.4 % v20) | Part de PV deja perdue par notre actif. |
| `op_dmg_ratio` | · instant | 32.2 % | (1.4 % v20) | Idem pour le leur. |
| `op_bench_threat` | 🪞 miroir | 91.0 % | (1.0 % v20) | Menace LATENTE de leur banc : 26,9 % des etats la voient depasser leur actif, de 70 degats en median. |
| `my_bench_ko` | · instant | 92.5 % | (1.7 % v20) | Notre win condition en preparation. |
| `ko_next_turn` | 🔮 ANTICIPE t+1 | 27.3 % | (6.7 % v20) | On tuera au PROCHAIN tour, une energie de plus. Sans cela aucune planification a deux coups n'est representable. |
| `op_bench_dmg_max` | · instant | 35.6 % | (1.3 % v20) | Le Pokemon de leur banc le plus mur : le DECLENCHEUR d'une conversion. 35,5 % des etats en portent. |
| `op_bench_dmg_sum` | · instant | 35.6 % | (0.4 % v20) | La pression globale accumulee : le PLAN. |
| `my_bench_dmg_max` | · instant | 32.0 % | (1.8 % v20) | Notre banc le plus expose : la DEFENSE. |
| `op_threat_next` | 🔮 ANTICIPE t+1 | 35.0 % | (3.4 % v20) | Ce que l'adversaire pourra faire au tour SUIVANT, pas maintenant : la temporisation se decide la-dessus. |
| `ko_next_margin` | 🔮 ANTICIPE t+1 | 92.3 % | — | DE COMBIEN on depasse (ou manque) le letal au tour prochain. ⚖ v22 : le degat exact etait DEJA calcule par `ko_next_turn` puis ECRASE en booleen — rater de 10 (une energie, un outil suffisent) et rater de 200 (le mur tient deux tours) etaient le meme nombre. Porte de redondance PASSEE avant encodage : R2 = 0,927 sur 8 canaux existants, soit 7,26 % de variance NEUVE ; dementi sur 17,29 % des decisions, et a portee actionnable (<= 30 degats) sur 43,80 % des PARTIES. ⚠ 7,26 % est un PLAFOND (mesure contre 8 scalaires sur 110) : seule l'ablation apres entrainement tranchera. |
| `threat_next_margin` | 🔮 ANTICIPE t+1 | 90.6 % | — | Le symetrique adverse : de combien LEUR letal du tour prochain nous depasse ou nous manque. Variance neuve 4,84 %, dementi 14,88 % des decisions. C'est la colonne sur laquelle une TEMPORISATION peut se decider — murer n'a de sens que si l'adversaire rate de peu. |
| `op_bench_dmg_frac` | · instant | 35.6 % | — | 🔑 v25 — LES DEGATS DEJA POSES SUR SON BANC (1 - PV restants / PV max, sur les slots lisibles). C'est la condition de victoire de tout un pan du format — `Shadow Bullet`, `Phantom Dive` — qui accumule sur le banc puis convertit en double KO. Le banc adverse n'etait lu que par son compte de PV, jamais par sa MOISSON. |

## 6. TEMPO ET DEVELOPPEMENT

*L'avance d'un tour, irrattrapable une fois perdue.*

| canal | horizon | non nul | poids mesure | ce qu'il mesure |
|---|---|---|---|---|
| `atk_energy_cost` | · instant | 0.0 % | — | L'attaque DEFAUSSE nos energies. `Draconic Buster` fait 260 degats et vide l'attaquant : il ne peut pas recommencer au tour suivant. Le reseau voyait 260 gratuits. |
| `atk_accel` | · instant | 0.0 % | — | L'attaque ATTACHE de l'energie a nos Pokemon. **64 exemplaires du champ** — le plus gros trou de la passe v13. `Aura Jab` et `Turbo Flare` arment le tour SUIVANT : elles valent bien plus que leurs degats affiches. |
| `atk_switch` | · instant | 0.1 % | (6.8 % v20) | L'attaque nous fait changer d'actif : une retraite GRATUITE, qui sort un attaquant piege sans payer le cout. 26 exemplaires. |
| `atk_evolve` | · instant | 0.0 % | — | L'attaque cherche SON evolution et la pose (`Ascension`). Un tour entier gagne — ce que `Rare Candy` fait payer une carte. |
| `retreat_saves` | 🪞 miroir | 0.5 % | (0.6 % v20) | Cette RETRAITE sort notre actif d'une portee letale. Une retraite sur trois le fait, et rien ne le disait. ⚠ Remplace `retreat_dest_safe`, structurellement morte : une option de RETRAITE ne porte aucune carte (mesure 400/400). |
| `turn` | · instant | 98.4 % | (9.8 % v20) | Numero du tour. |
| `my_bench_n` | · instant | 94.3 % | (5.0 % v20) | Taille de notre banc. |
| `op_bench_n` | · instant | 93.4 % | (2.3 % v20) | Taille du leur. |
| `my_act_en` | · instant | 61.2 % | (3.1 % v20) | Energies (UNITES) sur notre actif. |
| `op_act_en` | · instant | 66.2 % | (1.4 % v20) | Idem pour le leur. |
| `energy_attached` | 🔁 tour courant | 35.3 % | (8.2 % v20) | A-t-on deja attache ce tour-ci. |
| `supporter_played` | 🔁 tour courant | 42.4 % | (5.3 % v20) | Supporter deja joue ce tour. |
| `stadium_played` | 🔁 tour courant | 8.7 % | (3.8 % v20) | Stade deja joue ce tour. |
| `retreated` | 🔁 tour courant | 6.4 % | (0.0 % v20) | Retraite deja utilisee ce tour. |
| `turn_actions` | 🔁 tour courant | 100.0 % | (4.2 % v20) | Actions deja faites dans ce tour. |
| `i_am_first` | · instant | 49.6 % | (1.7 % v20) | Sommes-nous le joueur qui commence. |
| `has_stadium` | · instant | 68.8 % | (1.6 % v20) | Un stade est en jeu. |
| `my_fresh` | · instant | 22.4 % | (2.5 % v20) | Notre actif vient d'arriver (ne peut pas evoluer). |
| `my_bench_en_sum` | · instant | 56.8 % | (3.6 % v20) | Energie posee sur notre banc. |
| `op_bench_en_sum` | · instant | 59.6 % | (2.1 % v20) | Idem pour le leur. |
| `my_bench_en_max` | · instant | 56.8 % | (6.2 % v20) | Notre attaquant de banc le plus charge. |
| `evo_in_hand` | · instant | 10.8 % | (4.3 % v20) | L'evolution de notre actif est EN MAIN : decide le plan des trois prochains tours. |
| `energy_tempo_diff` | · instant | 99.0 % | (2.4 % v20) | Le DIFFERENTIEL d'energie en jeu. Rater un attachement est irrattrapable : une par tour, sans exception. Seul le differentiel compte, jamais le compte absolu. |
| `op_dev_deficit` | · instant | 89.2 % | (1.8 % v20) | Retard de developpement ADVERSE (banc + energies) rapporte a la NORME DU TOUR, mesuree sur 376 493 decisions. C'est le seul tell de niveau qui survive au controle par archetype (rho intra -0,143). |
| `my_dev_deficit` | · instant | 92.0 % | (2.6 % v20) | Le NOTRE, meme norme. Verifie symetrique. |
| `bench_refuge` | · instant | 65.1 % | (1.9 % v20) | Existe-t-il au banc un Pokemon vers qui retraiter en SECURITE ? La mobilite ne vaut que si la destination tient. |
| `evo_ready_frac` | · instant | 41.0 % | (3.4 % v20) | Part de notre plateau prete a EVOLUER. Une evolution differee est du tempo deja paye et non encaisse. |
| `evo_skip_live` | · instant | 2.8 % | (3.1 % v20) | Un saut d'evolution est disponible (`Rare Candy`) : la chaine Base -> Stade 2 tient en un tour. |
| `bench_libre` | · instant | 71.2 % | — | 🔑 v25 — LA PLACE RESTANTE AU BANC, en fraction de `bench_max`. Elle EST la capacite a se developper : un banc plein change la valeur de toute carte qui pose, et le reseau devait le deduire d'une longueur de liste qu'il ne voit pas. |
| `my_bench_fresh_frac` | · instant | 51.7 % | — | ⚖ v25 — part de NOTRE banc posee ce tour, donc incapable d'evoluer. Pendant d'etat de `slot_fresh`. |
| `op_bench_fresh_frac` | · instant | 4.0 % | — | ⚖ v25 — la meme chose cote ADVERSE, ou elle dit ce qu'il POURRA faire evoluer au tour suivant. docs/15 §3 releve nommement que les asymetries de ce genre — une colonne presente d'un seul cote — elargissent le point aveugle. |
| `my_bench_tools_frac` | · instant | 6.5 % | — | ⚖ v25 — part de notre banc portant deja un outil, donc fermee a un second. |
| `op_bench_tools_frac` | · instant | 8.2 % | — | ⚖ v25 — idem cote adverse : combien de ses bancs sont deja equipes. |

## 7. ECONOMIE ET RESSOURCES

*Main, deck, defausse : ce dont on dispose encore.*

| canal | horizon | non nul | poids mesure | ce qu'il mesure |
|---|---|---|---|---|
| `atk_search` | · instant | 0.0 % | — | L'attaque TUTORE le deck. Distinct de `atk_evolve` : chercher une ressource et chercher son evolution ne preparent pas le meme tour. 18 exemplaires. |
| `atk_draw` | · instant | 0.1 % | — | L'attaque PIOCHE. `Filch` (0 degat, x4 dans le deck n°1 du champ) est un tour de developpement deguise en attaque nulle. ⚠ Cette colonne a valu ZERO pendant une heure : un BACKSPACE (0x08) ecrit a la place de `` par un heredoc. Le source semblait juste. |
| `eff_hand_cost` | · instant | 0.2 % | (0.0 % v20) | La carte se paie en CARTES DE LA MAIN (defausser pour jouer). Un effet gratuit et un effet a deux cartes ne se comparent pas. |
| `opt_is_acespec` | · instant | 0.6 % | (3.3 % v20) | Carte ACE SPEC : une seule par deck. La jouer est irreversible pour la partie entiere. |
| `my_deck` | · instant | 99.8 % | (4.1 % v20) | Cartes restantes dans notre deck. |
| `op_deck` | · instant | 99.7 % | (3.6 % v20) | Dans le leur. |
| `my_hand_n` | · instant | 99.0 % | (4.1 % v20) | Taille de notre main. Une GRANDE main est un risque face a la disruption, pas un confort. |
| `op_hand_n` | · instant | 98.9 % | (2.9 % v20) | Taille de la leur. |
| `hand_energy` | · instant | 58.0 % | (1.0 % v20) | Energies en main. |
| `hand_trainer` | · instant | 95.5 % | (3.7 % v20) | Dresseurs en main. |
| `hand_pokemon` | · instant | 77.9 % | (2.2 % v20) | Pokemon en main. |
| `my_tools` | · instant | 9.4 % | (1.4 % v20) | Outils sur notre actif. |
| `op_tools` | · instant | 12.2 % | (0.8 % v20) | Sur le leur. |
| `my_discard_n` | · instant | 93.9 % | (2.5 % v20) | Taille de notre defausse. |
| `op_discard_n` | · instant | 92.2 % | (3.4 % v20) | De la leur. |
| `my_discard_energy` | · instant | 56.7 % | (1.3 % v20) | Energies a notre defausse. |
| `hand_search_avail` | · instant | 79.3 % | (1.6 % v20) | Une RECHERCHE est disponible en main. Le sequencage professionnel : chercher AVANT de piocher, pour concentrer le deck avant que l'aleatoire ne s'execute. |
| `hand_draw_avail` | · instant | 62.5 % | (2.3 % v20) | Une PIOCHE est disponible en main. |
| `hand_supporter_live` | · instant | 45.0 % | (1.9 % v20) | Avons-nous un SUPPORTER jouable en main ? Un tour sans supporter n'est pas un tour normal. |
| `my_acespec_left` | · instant | 77.2 % | (1.4 % v20) | Notre ACE SPEC est-elle encore disponible ? Une seule par deck et par partie. |
| `dead_frac` | 🔁 tour courant | 49.5 % | (3.7 % v20) | Part de notre main que RIEN ne permet de jouer maintenant. `my_hand_n` compte les cartes, `hand_trainer` les classe : aucune ne disait lesquelles sont MORTES. Moyenne 0,430 ; non nulle sur 89,1 % des decisions en contexte Main. |
| `dead_valid` | 🔁 tour courant | 56.8 % | (3.7 % v20) | Drapeau de validite de `dead_frac`. Sans lui, zero signifierait a la fois « main entierement jouable » et « on est dans un sous-menu, la question n'a pas de sens ». |
| `retreat_live` | · instant | 87.9 % | (1.4 % v20) | Cout de retraite EN JEU, pas celui IMPRIME (deja porte par une colonne d'option). Differe sur 1,006 % des decisions. ATTENTION Le signe dominant est POSITIF : `Gravity Gemstone` rencherit (2 074 cas) bien plus souvent qu'`Air Balloon` n'allege (317). |
| `special_hostage` | · instant | 14.7 % | (1.2 % v20) | Notre attaque tient a UNE energie speciale et la perdre la tue : 68,6 % des actifs porteurs. Non mesurable avant `_cout_payable` — il faut le cout par TYPE pour le savoir. |

## 8. VARIANCE ET INFORMATION

*Lisser le hasard au lieu de le subir.*

| canal | horizon | non nul | poids mesure | ce qu'il mesure |
|---|---|---|---|---|
| `atk_dmg_sd` | · instant | 0.0 % | (1.9 % v20) | ECART-TYPE de la loi de degats. « 4 pieces x 30 » et « 60 degats » affichent la meme moyenne : seul l'ecart-type les separe. 7,5 % des attaques. |
| `atk_p_lethal` | · instant | 0.6 % | (3.8 % v20) | P(degats >= PV adverses), calculee sur la loi EXACTE (binomiale ou geometrique), pas simulee. Le seul nombre qui repond a « est-ce que ce coup gagne ? ». |
| `atk_dmg_floor` | · instant | 1.3 % | (1.1 % v20) | PLANCHER garanti : les degats obtenus si tout le hasard tombe mal. Le pendant du risque. 94,6 % des attaques. |
| `unseen_frac` | · instant | 100.0 % | (3.0 % v20) | Volume de ce qui peut encore sortir (deck + prix). La COMPRESSION : un deck mince n'est pas un deck vide. |
| `p_draw_energy` | · instant | 99.4 % | (1.1 % v20) | P(la prochaine carte piochee est une energie). EXACT : les 6 prix etant tires uniformement du deck, ils ne biaisent pas la proportion du non-vu, ils en font partie. |
| `p_draw_pokemon` | · instant | 99.6 % | (1.8 % v20) | Idem pour un Pokemon. |
| `p_draw_trainer` | · instant | 99.9 % | (3.3 % v20) | Idem pour un Dresseur. |
| `unseen_trunc` | · instant | 0.9 % | (7.6 % v20) | DRAPEAU D'HONNETETE : la defausse depasse les 40 identifiants stockes, donc les comptes ci-dessus surestiment. Une mesure fausse qui se SAIT vaut mieux qu'une qui se tait. |

## 9. MOTEURS EN JEU

*Ce qui tourne en permanence sur le plateau.*

| canal | horizon | non nul | poids mesure | ce qu'il mesure |
|---|---|---|---|---|
| `eff_passive_dmg` | · instant | 0.1 % | — | Capacite qui pose des degats CHAQUE TOUR sur tous les porteurs de capacite (`Freezing Shroud`), des deux cotes. |
| `abil_once_cap` | 🔁 tour courant | 0.5 % | (2.1 % v20) | Capacite plafonnee a UN usage par tour. Distingue un moteur repetable d'un effet unique. |
| `abil_on_entry` | · instant | 1.7 % | (1.5 % v20) | Capacite declenchee A L'ENTREE en jeu : elle se paie une fois et ne se rejoue pas. |
| `passive_dmg_in_play` | · instant | 22.8 % | (3.2 % v20) | Un moteur de degats passifs TOURNE (Froslass). Un drapeau d'option ne voit que l'instant ou l'on POSE la carte ; celui-ci voit tous les tours ou elle travaille — 400x plus souvent. |
| `my_abil_bearers` | · instant | 88.8 % | (2.0 % v20) | Part de NOTRE plateau portant une capacite — donc vulnerable aux degats passifs et au verrou. |
| `op_abil_bearers` | · instant | 87.0 % | (1.0 % v20) | Part du LEUR. Rend le SIGNE de Froslass calculable : elle frappe les deux cotes, sa valeur est une DIFFERENCE. |
| `abilock_in_play` | · instant | 1.0 % | — | Un verrou de capacites est actif sur le plateau. |
| `abil_armed_diff` | · instant | 39.2 % | (4.3 % v20) | DIFFERENCE de capacites armees entre les deux plateaux. Un moteur de plus est un avantage qui se paie chaque tour. |

## 10. ROLE ET META

*Qui attaque, qui controle, et contre quel archetype.*

| canal | horizon | non nul | poids mesure | ce qu'il mesure |
|---|---|---|---|---|
| `arch_marnie_morgrem` | · instant | 31.5 % | (3.5 % v20) | Archetype adverse reconnu : Marnie's Grimmsnarl. |
| `arch_alakazam` | · instant | 25.4 % | (7.1 % v20) | Archetype adverse : Alakazam. |
| `arch_rocket` | · instant | 8.4 % | (2.7 % v20) | Archetype adverse : Team Rocket's Spidops. |
| `arch_cynthia` | · instant | 5.2 % | (8.6 % v20) | Archetype adverse : Cynthia's Garchomp. |
| `arch_dragapult` | · instant | 3.4 % | (5.5 % v20) | Archetype adverse : Drakloak + Dragapult. |
| `arch_crustle_kang` | · instant | 12.9 % | (2.9 % v20) | Archetype adverse : Crustle + Kangaskhan. |
| `arch_kang_meowth` | · instant | 2.4 % | — | Archetype adverse : Kangaskhan + Meowth. |
| `arch_marnie_froslass` | · instant | 0.4 % | — | Archetype adverse : Marnie's + Froslass. |
| `arch_dipplin` | · instant | 1.7 % | — | Archetype adverse : Dipplin. |
| `arch_mfroslass_starmie` | · instant | 1.3 % | — | Archetype adverse : Mega Froslass ex + Mega Starmie ex. ✅ CORRIGE (689e0bc) : cette colonne a sur-declenche pendant tout le schema 16 — `_deck_posterior` prenait le PREMIER archetype partageant un nom, si bien que Starmie+Dusclops atterrissait ici et que 65 % de ses tirs etaient des faux positifs. Le routage prend desormais le MEILLEUR recouvrement (docs/06 C45). |
| `arch_starmie_dusclops` | · instant | 0.5 % | (4.8 % v20) | Archetype adverse : Mega Starmie ex + Dusclops. ✅ CORRIGE (689e0bc) : n'a JAMAIS ete allumee sous le schema 16 — pas une fois sur 8 956 957 decisions — alors que cet archetype est le 10e plus frequent du champ (1,872 %) ; son creneau etait structurellement inatteignable. Verifie apres correctif : un plateau [Mega Starmie ex, Dusclops] l'allume bien a 1,0, et plus AUCUN creneau d'archetype n'est orphelin. |
| `arch_cinderace_starmie` | · instant | 0.3 % | (3.2 % v20) | Archetype adverse : Cinderace + Mega Starmie ex. |
| `arch_lucario_hariyama` | · instant | 0.6 % | (3.2 % v20) | Archetype adverse : Lucario + Hariyama. |
| `arch_brambleghast` | · instant | 0.3 % | (18.9 % v20) | Archetype adverse : Brambleghast. |
| `arch_archaludon` | · instant | 0.4 % | (5.7 % v20) | Archetype adverse : Archaludon ex. |
| `arch_dudunsparce` | · instant | 2.9 % | — | Archetype adverse : Dudunsparce. |
| `arch_unknown` | · instant | 2.4 % | (5.3 % v20) | Archetype adverse NON reconnu. |
| `arch_conf` | · instant | 98.3 % | (1.6 % v20) | CONFIANCE de l'identification d'archetype. ⚖ C'est elle qui distingue « je sais » de « je devine » : sans elle, un argmax dur presente une supposition comme une certitude. |

## 11. LIRE L'ADVERSAIRE

*🔑 POLE OUVERT PAR LE SCHEMA 25. Tout ce que l'on DEDUIT de ce qu'on ne voit pas : sa main par son inaction, nos prix par elimination, ses ressources par ce qu'il a deja brule. Les dix premiers poles lisent le VISIBLE ; celui-ci lit le reste, et chacune de ses colonnes porte donc un drapeau de validite — un zero qui remplace un inconnu est un mensonge chiffre.*

| canal | horizon | non nul | poids mesure | ce qu'il mesure |
|---|---|---|---|---|
| `opt_prized_certain` | · instant | 0.9 % | — | 🔑 v25 — la carte visee par cette option est SUREMENT dans nos prix. Chercher une carte prizee est une action vide : le menu la propose, le moteur la refuse. Le pendant d'etat est `pk_valid`, qui porte seul la distinction « pas de deduction » / « deduction faite, carte absente » — la repeter par option couterait 82 colonnes pour une information de DECISION. |
| `opt_prized_possible` | · instant | 6.2 % | — | ⚖ v25 — la carte visee est PEUT-ETRE prizee (elle appartient a l'ensemble des candidats non elimines). Une recherche dessus est un pari, pas une erreur : les deux colonnes separent le certain du possible au lieu de les confondre. |
| `op_seg_valid` | · instant | 94.6 % | — | ⛔ v25 — LE DRAPEAU SANS LEQUEL LES TROIS SUIVANTES MENTENT : a-t-on observe un tour adverse COMPLET ? `op_seg_seen == 0` veut dire « jamais observe ». Sans ce drapeau, cet INCONNU s'ecrirait 0 et concourrait comme la mesure « il n'a pas joue de Supporter », qui est son contraire exact (regle 4 du depot). |
| `op_no_supporter_last_turn` | · instant | 30.1 % | — | 🔑 v25 — L'INFERENCE DE MAIN ADVERSE LA MIEUX ETABLIE DU DEPOT : un adversaire qui ne joue AUCUN Supporter d'un tour complet n'en tient probablement aucun. C'est une inference par CHOIX RESTREINT. 📏 AUC 0,83235 -> 0,84960, soit **+0,0173**, IC95 bootstrap PAR PARTIE [+0,0069 ; +0,0260], disjoint de zero. Vaut 0 quand le drapeau vaut 0. |
| `op_seg_stale` | · instant | 8.2 % | — | ⚖ v25 — anciennete de l'observation, en tours, bornee a 5 puis divisee par 5. Une inference de main VIEILLIT : « il n'avait pas de Supporter » date de trois tours ne vaut pas celle du tour dernier — il a pioche depuis. |
| `op_sup_rate` | · instant | 83.4 % | — | ⚖ v25 — Supporters adverses vus par tour ecoule, borne a 1. Un adversaire qui en joue un par tour depuis dix tours n'a pas la meme main que celui qui n'en a joue aucun. |
| `pk_valid` | · instant | 94.4 % | — | ⛔ v25 — meme role que `slot_valid` : sans lui, « aucune deduction disponible » et « deduction faite, rien de certain » s'ecrivent tous deux 0. C'est le drapeau qui rend les cinq colonnes de prize-check lisibles, y compris les deux colonnes d'OPTION. |
| `pk_stale` | · instant | 44.5 % | — | ⚖ v25 — age de la deduction en tours, borne a 10 puis divise par 10. La vue qui l'a permise date, et le deck a ete pioche depuis. |
| `pk_certain_frac` | · instant | 51.0 % | — | ⚖ v25 — part des candidats CERTAINEMENT prizes parmi les possibles (`len(certain) / len(possible)`). A 1 la deduction est close, a 0,1 elle n'est qu'un soupcon : deux etats que le reseau lisait pareil. |
| `pk_pris_depuis` | · instant | 22.3 % | — | 🔑 v25 — LA PEREMPTION QUI COMPTE VRAIMENT, et ce n'est pas le temps. Chaque prix PRIS depuis la vue retire une carte de la zone et invalide une part de la deduction. `pk_prize_at` moins `my_prize` donne exactement ce nombre, borne a 6 puis divise par 6. |
| `pk_ampleur` | · instant | 94.4 % | — | ⚖ v25 — TAILLE de la deduction (`pk_n`), qui n'est PAS `len(pk_ids)` des que la liste est capee. Bornee a 12 puis divisee par 12. |
| `pk_trunc_flag` | · instant | 0.0 % ⛔ | — | ⛔ v25 — la liste de candidats a ete TRONQUEE par le cap. Au-dela, les comptes sont des BORNES BASSES : une deduction tronquee reste vraie mais cesse d'etre exacte, et le reseau doit pouvoir le savoir plutot que de lire un compte amoindri comme un compte juste. |
| `op_disc_valid` | · instant | 92.2 % | — | ⛔ v25 — sa defausse a-t-elle ete lue. Zone PUBLIQUE, donc aucune inference n'est requise — mais l'absence de lecture reste un inconnu, pas un « il n'a rien brule ». |
| `op_gust_brules` | · instant | 28.6 % | — | 🔑 v25 — COMBIEN DE SES `Boss's Orders` SONT DEJA DANS SA DEFAUSSE. ⛔ Corrige un biais DIRECTIONNEL : `gust_exposure` suppose qu'il peut toujours arracher un Pokemon de notre banc — vrai au tour 1, beaucoup moins quand ses quatre gusts sont brules. La colonne surestimait donc le danger, TOUJOURS dans le meme sens. Un biais constant est apprenable ; un biais qui decroit au fil de la partie ne l'est pas sans ce compteur. `op_discard_n` (un simple compte) ne pouvait pas le porter : c'est l'IDENTITE qui compte. |
| `op_hammer_brules` | · instant | 28.5 % | — | ⚖ v25 — ses marteaux deja brules (`Enhanced Hammer` x25, `Crushing Hammer` x5 sur 294 attachements). 30 attachements sur 294 (10,2 %) finissent retires par l'adversaire, dans 13 parties sur 49 : savoir combien il en a brules dit s'il faut encore craindre pour l'energie qu'on pose. ⚠ Le lien de cette classe avec la DEFAITE n'est PAS etabli (p = 0,8962) : la colonne se justifie par la representabilite d'un mecanisme reel, pas par une cause. Ne pas lui en preter une. |
| `op_disc_trunc` | · instant | 0.8 % | — | ⛔ v25 — la defausse est capee a 40 identifiants et DEBORDE sur 0,70 % des decisions, concentrees sur **9,77 % des PARTIES** — une partie longue sur dix. Au-dela du cap les deux compteurs ci-dessus sont des bornes basses. |
| `op_play_rate` | · instant | 83.4 % | — | ⚖ v25 — cartes jouees par tour adverse observe, normalisees par 5 et bornees a 1. Complete `op_sup_rate` : le rythme, pas seulement la ressource unique. |

## 🔭 SUR COMBIEN DE TOURS L'IA VOIT-ELLE ?

⛔ **LE CRITERE, ET IL EST UNIQUE : le code EVALUE-T-IL UN ETAT AUTRE QUE LE PRESENT ?**
Pas si le NOM parle du futur. Pas si le TEXTE de la carte parle du futur. Pas si la
CONSEQUENCE est future. L'audit adverse du 03/08 a corrige **11 classements** sur ce
seul motif, et **tous dans le meme sens** — du futur vers le present.

| horizon | canaux | ce que cela signifie |
|---|---|---|
| 🔮 ANTICIPE t+1 | **4** | **le code MODIFIE l'etat puis recalcule.** La seule anticipation reelle. |
| 🪞 miroir | **6** | evalue le camp ADVERSE, mais sur l'etat PRESENT. Ce n'est pas voir devant. |
| 🔁 tour courant | **11** | propriete de la SEQUENCE d'actions de ce tour-ci. |
| 🏁 terminal | **9** | condition de fin de partie, lue sur l'etat present. |
| · instant | **190** | propriete de l'etat present. Le regime par defaut. |

> 🔑🔑 **4 canaux sur 220 anticipent.** Et ils font la MEME chose :
> - `ko_next_margin` — meme calcul, rendu en MARGE et non en booleen (v22). Zero appel supplementaire : le degat est hisse avec sa garde de court-circuit, verifie a 44 572 appels contre 44 572.
> - `ko_next_turn` — net_policy.py:3294 — une energie de plus a NOUS, puis on recalcule : notre letal au tour prochain.
> - `op_threat_next` — net_policy.py:2832 — une energie de plus a l'ADVERSAIRE, puis on recalcule ses degats : son letal au tour prochain.
> - `threat_next_margin` — idem pour l'ADVERSAIRE : de combien son letal du tour prochain nous depasse.
>
> ⟹ **Toute la vision du futur de cet agent tient dans « et s'il avait une energie de
> plus ? », posee deux fois, et la reponse est BINAIRE (letal ou non).** Il n'existe
> aucun canal qui projette a deux tours, aucun qui compte les ressources futures,
> aucun qui evalue une position apres un echange.

### ⛔ LES TROUS QUE CETTE CARTE REND VISIBLES

| trou | ce qui manque | ce qui existe deja et pourrait le porter |
|---|---|---|
| **Profondeur** | Aucun canal a t+2. La tete auxiliaire a ete ENTRAINEE a predire t+2 mais elle n'est **jamais appelee en jeu** — cout d'inference nul, valeur nulle. | `net_v20aux.pt` existe ; son duel est la dette R46. |
| **Granularite de l'anticipation** | Les deux canaux t+1 rendent un BOOLEEN (letal / pas letal). Rien ne dit *de combien* on rate, ni *ce qui change* si l'echange a lieu. | `ko_margin` et `threat_margin` font deja cela pour t0 — la forme existe. |
| **Le tour, comme objet** | 11 canaux decrivent la sequence du tour, mais **aucun etage ne la DECIDE** : le planificateur est refute (R51) et desarme. | `agent/turn_planner.py` + le moteur EST un arbre (C47). |
| **Ressources futures** | Rien ne projette la main, le deck ou l'energie au tour suivant. `p_draw_*` donne une probabilite de pioche mais ne la CONSOMME jamais. | les 4 colonnes hypergeometriques. |

### Ou agit chaque canal

| chaine | canaux | etat |
|---|---|---|
| **Evaluation de situation** (encode, servi au reseau) | 220 | tous, par construction |
| **Decision de ligne** (etage AU-DESSUS du reseau) | 0 en service | les 4 etages sont DESARMES, chacun par une mesure : planificateur R51 (4,50 %), regle du banc R52 (-5,2 pts), lecture d'adversaire refutee, `certain_move` neutre |

> ⚠ **C'est le desequilibre central de cet agent, et il est mesure, pas suppose :** il PERCOIT sur 185 canaux et il DECIDE avec un seul argmax. Entre les deux, rien.

## ⛔ CE QUE L'IA NE SAIT **PAS** FAIRE

| nature | sujet | pourquoi |
|---|---|---|
| ✅ FERME v13 | Les 17 aveugles du CHAMP | Audit retourne contre les 27 listes ADVERSES reelles + nos 4 canoniques : 17 occurrences aveugles (43 exemplaires) -> **0**, et 138 partiels -> 23. Neuf colonnes neuves, quatre multiplicateurs rendus exacts. |
| ✅ FERME v13 | ⛔ Une ERREUR ACTIVE, a deux endroits | La clause « isn't affected by RESISTANCE » n'etait traitee nulle part : -30 degats retires a tort. Et `_max_dmg_vs` n'interrogeait meme pas l'exemption, donc le x2 fantome contaminait ko_now, ko_margin, threat_now, threat_margin, ko_next_turn et les deux _bench_best — huit colonnes d'etat. Deux copies d'une meme regle avaient diverge ; il n'y en a plus qu'une. |
| ✅ FERME v12 | Letalite de BANC, `Dark Frost`, variance comme LOI, `bench_max` | Voir C37. `atk_lethal_bench` ferme les 17,2 % de KO reels jamais annonces. |
| ⚠ MESURE | La VARIANCE est un chantier a PETIT N | Mesure CONTRE les colonnes qu'elles pretendent depasser (C37bis) : `atk_p_lethal` vs `atk_lethal` r = +0,997, `atk_dmg_floor` vs `atk_dmg` r = +0,996. Sur 14 887 options d'attaque, **la loi ne dement la moyenne que dans 0,51 % des cas** — 11 fois moins que la letalite de banc. La densite dit qu'une colonne n'est pas morte, pas qu'elle est NEUVE. |
| ⛔ NON CALCULABLE | Le « Baiting » | Poser une fausse menace pour attirer un `Boss's Orders` est une INTENTION, pas un etat. Rien dans l'observation ne la distingue. |
| ⚠ A MESURER | L'horizon MULTI-TOURS | La tete auxiliaire t+2 a ete ENTRAINEE deux fois (v3 : +0,19 pt de top-1 ; v9 : -0,85 pt) et JAMAIS DUELLEE — verifie, il n'existe aucun `duel_trace_net_v9aux_vs_net_v9.jsonl`. Or top-1 et victoire divergent (C29). Le manque n'est pas l'entrainement, c'est la mesure en jeu. Le bras est cable dans le pipeline v13. |
| ⚠ CABLE, NON JUGE | Le SEQUENCAGE : l'ordre COMPTE, par la LEGALITE | ⛔⛔ CETTE ENTREE A MENTI. Elle affirmait « RIEN N'EST CABLE : aucun fichier de l'agent n'appelle la primitive » — FAUX depuis le commit `0e09569` : `agent/turn_planner.py` (18,5 Ko) appelle `search_begin` / `search_step` / `search_release` / `search_end` et est cable dans `net_agent`, `net_duel`, `build_submission` et `planner_gate`. Un atlas qui ment sur ce qui EXISTE fait chercher au mauvais endroit — c'est exactement ce qu'il est cense empecher, et c'est la faute R47 sous une autre forme. ⚠ CE QUI MANQUE VRAIMENT est une MESURE VALIDE : le seul chiffre connu, 15/395 = 3,80 pct, date du 03/08 01:48:48 alors que le planificateur a ete corrige a 02:02 — l'arene PRECEDE le correctif de 14 minutes, et elle mesurait une version qui ne pouvait JAMAIS attaquer. ⚠ Faiblesse ouverte et nommee : l'objectif compare le meilleur LOGIT du menu terminal A a celui de B, or un logit n'est comparable qu'A L'INTERIEUR d'un menu. Detail ci-dessous.  |
| (suite) MESURE D'ORIGINE | Le SEQUENCAGE — ce qui l'a etabli | ⛔ Le blocage etait une ERREUR DE MODELE, pas une limite : `tools/probe_search_api.py` etablit que deux `search_step` depuis le MEME `searchId` divergent et que les parents restent valides — le moteur est un ARBRE, le retour arriere est GRATUIT. (`turn_branching.py` croyait devoir REJOUER un chemin ; il reste faux et ne doit pas etre relance.) MESURE : 33 % des paires d'actions consecutives sont des DEVERROUILLAGES, 47 % des tours en portent un, et contre un null APPARIE (meme multiset, meme sequence) permuter les memes actions change le menu de fin de tour 1,65-13,91 % du temps contre 0,00 % — 5 runs sur 5, IC disjoints, deux decks. 🔑 L'effet passe par le MENU et non par la preference : 1 flip sur 470 a menu identique. ⟹ ce n'est PAS la recherche refutee 3 fois (celles-ci estimaient une VALEUR ; ici perdre une action est un fait de LEGALITE). Reste a etablir le gain en VICTOIRES sur un reseau du schema COURANT. |
| ⚠ EXPOSITION | `atk_lethal` sur les attaques geometriques | « Flip until tails » n'est plus code ZERO. 8 attaques changent, ~17 options sur 6 869 annoncent un letal qu'elles n'annoncaient pas : le record de 154/154 sans faux positif est EXPOSE. ⚠ TOUJOURS OUVERT au 2026-08-03 : `tools/lethal_truth.py` n'a jamais ete rejoue depuis — verifie, il n'existe aucun resultat sur disque, et le schema est passe de v13 a v17 entre-temps. A rejouer sur `net_v17.pt`. |
| ⛔ REFUTE | Lire le NIVEAU de l'adversaire (opponent_read) | Le detecteur annoncait AUC 0,955 au tour 6 sur adversaires inedits et un champ BIMODAL sur la retraite (0,108 sous 1000 Elo contre 0,782 au-dessus). ⛔⛔ LES TROIS NOMBRES MESURAIENT UNE FUITE : le corpus porte LES DEUX joueurs sous le MEME `gid`, un regroupement par `gid` seul fait ALTERNER le point de vue et fabrique une fausse retraite par tour — et l'alternance n'existe que si l'Elo depasse 1000 (corpus extrait a `--min-rating 1000`). Corrige : retraite PLATE a 0,099-0,137, AUC 0,529 sur adversaires inedits = le hasard. L'etage `opponent_adapt` reste embarque mais DESARME (`POKE_ADAPT` non definie). docs/06 C46. |
| ⚠ PARTIELS | 23 occurrences restent « effet non identifie » | Une capacite de MISE EN PLACE (Cinderace), une clause de restriction d'energie, et quatre cartes exotiques a 4 exemplaires. Aucune n'est une mecanique de jeu non portee — verifie carte par carte. |
| ⛔ TROU DE DONNEES | Les menus MULTI-SELECTION : le reseau n'en a JAMAIS vu un seul | `net_agent.act` ne passe pas ces menus au modele (il sait classer UNE option, pas composer un sous-ensemble) et retombe sur `_legal` = les k PREMIERES options dans l'ordre du moteur, c'est-a-dire la baseline mesuree a 0,3345 de top-1. Part reelle : **6,57 pct des decisions** (79,95 pct au reseau, 13,48 pct de coups FORCES qui n'en sont pas un trou). ⛔ Et ce n'est pas un trou de MODELE mais de DONNEES : `extract_rated_data.py:203` jette ces decisions, `pick` est un entier 200 000 fois sur 200 000. On ne peut pas l'apprendre de ce corpus. ⚖ Parade MESUREE sur 6 000 episodes (sur le BANC les pilotes >= 1000 prennent 92,9 pct du permis, nous 50 pct ; sur `AttachTo` l'ecart est INVERSE) : `net_policy.choisir_multi`, DESARMEE (`POKE_MULTISEL=1`) tant qu'une arene ne l'a pas jugee. |
| 🔬 VALIDE, NON CABLE | Prize-check : savoir lesquelles de NOS cartes sont prizees | `sel.deck` est livre sur 8,20 pct des decisions, 79,43 pct surviennent apres la 1re vue, et la vue est COMPLETE dans **100,0 pct** des cas (`len(deck) == deckCount`) — donc pas de filtre, la soustraction est saine. ⛔ MAIS la formule « 60 - main - jeu - defausse - deck » SURCOMPTE de +1 dans 996 cas sur 1 029 : la carte EN TRANSIT, jouee depuis la main et dont l'effet resout, n'appartient a aucune zone (les 33 exceptions sont les effets de CAPACITE, ou rien ne transite). ⚖ Regle conservatrice : une carte dont le compte deduit vaut >= 2 est CERTAINEMENT prizee. ⏸ Cabler exige un etat PERSISTANT cote `net_agent` ET un champ nouveau a l'extraction — un changement de FORMAT du corpus, pas un ajout de colonne. |
| ⚠ BORNE DE MESURE | Tout duel replie sur 6,57 pct des decisions | `net_duel` ne sait pas jouer un menu multi-selection au reseau : il y replie sur la meme heuristique pour LES DEUX camps. C'est symetrique, donc cela ne truque pas le vainqueur — mais l'ecart y est nul par construction, donc tout taux de victoire est DILUE vers 50 pct sur cette part. ⛔ Le chiffre affiche etait longtemps 26,39 pct : DOUBLE (le compteur sommait ses causes ET leur total) et gonfle par les coups FORCES. |

## Couches de decision

| couche | etat | mesure |
|---|---|---|
| Reseau (transformer, identite de carte + attention) | **EN PRODUCTION** | v19 = 970,8 sur la ladder, +130,7 points sur v17 a deck constant |
| `certain_move` — couche de regles DEMONTRABLES | **NON embarquee** | 48,6 % sur 3 978 parties : ne paie pas (R44) |
| Recherche a la decision | refutee 3x | 20,0 % par-dessus la politique experte |


---

# 🧭 INSTRUMENT DE PROGRES — ce qui manque, classe par ce qu'on en sait

> ⚖ Les sections ci-dessus disent ce que le modele **LIT**. Celles-ci disent ce qu'il
> en **FAIT**, **OU il perd**, et **ce qui a deja ete juge**. Chaque nombre porte sa
> source et sa date ; **une mesure absente s'affiche « — », jamais « 0 »**.

## 1. Ce qui PESE reellement dans la decision

| source | fichier | date | etat |
|---|---|---|---|
| poids | `data/card_weight_audit.json` | 2026-08-04 18:48 | ⛔ **PERIMEE** — PERIMEE : mesuree sur le schema v21, le code est en v25 |
| poids_repli | `data/ablation_poids.json` | 2026-08-03 14:42 | ⛔ **PERIMEE** — PERIMEE : mesuree sur le schema v20, le code est en v25 |
| chemin | `data/decision_path_audit.json` | 2026-08-04 17:28 | ⛔ **PERIMEE** — PERIMEE : mesuree sur le schema v22, le code est en v25 |
| carte | `data/card_effect_audit.json` | 2026-08-05 12:23 | a jour |

⚠ **Une source PERIMEE n'est pas une source absente** : elle porte de vrais
nombres, mesures sur un AUTRE schema. Les afficher sans le dire serait la panne
muette que ce depot a payee quatre fois.

### Les dettes, comptees par classe

| classe de dette | canaux | ce que cela veut dire |
|---|---:|---|
| `POIDS_PERIME` | 182 | le poids connu vient d'un schema anterieur : a re-mesurer |
| `SANS_MESURE_DE_POIDS` | 36 | aucune source ne connait ce canal — souvent parce qu'il vient d'etre AJOUTE |
| `CARTE_PARTIELLE` | 29 | une partie du texte est portee, l'autre non |
| `CARTE_AVEUGLE` | 18 | des effets de cartes n'atteignent aucun canal |
| `SUPPORT_TROP_FAIBLE` | 8 | trop peu de decisions l'exercent pour conclure : dette de CORPUS, pas de modele |
| `CARTE_FAUSSE` | 6 | ⛔ des cartes allument ce canal avec une valeur INCORRECTE |
| `JAMAIS_REMPLIE` | 3 | le corpus ne l'allume jamais : le generateur ne l'exerce pas |
| `CORPUS_SANS_SUPPORT` | 2 | l'ablation ne la voit pas alors que la chaine la voit non nulle |
| `IGNOREE_PAR_LE_RESEAU` | 2 | remplie, exercee, et le reseau n'en fait RIEN : dette de MODELE |
| `NON_DISCRIMINANTE` | 1 | elle bouge, mais ne change aucune decision |

🔑 **`CARTE_FAUSSE` d'abord, toujours.** Un canal aveugle prive le reseau d'une
information ; un canal FAUX lui en donne une qui ment, et il l'apprend.

⚠ **36 canaux sans AUCUNE mesure de poids** : `slot_valid`, `slot_energy`, `slot_dmg_frac`, `slot_maxhp`, `slot_atk_ready`, `slot_is_op`, `slot_debloque`, `slot_survie`, `slot_fresh`, `slot_tools`, `slot_atk_ready_type`, `opt_prized_certain` …
Ce n'est pas « ils ne servent a rien » — c'est « on ne sait pas », et la
difference est tout l'objet de ce document.

### ⛔ Canaux RECLAMES par l'audit des cartes, et qui n'existent pas

| canal reclame | cartes | part du champ cumulee |
|---|---:|---:|
| `atk_gust[INEXISTANTE]` | 11 | 0.9 % |
| `_dmg_positif` | 17 | 0.9 % |
| `atk_lethal_direct` | 12 | 0.5 % |
| `atk_win` | 1 | 0.0 % |
| `atk_bounce[INEXISTANTE]` | 3 | 6.2 % |

C'est de la **matiere a construire** : des effets de cartes reels qu'aucune
colonne ne porte, trouves en confrontant la prose de l'audit au schema reel.

## 1bis. Ou l'information se PERD entre la carte et le coup joue

> Ces pertes ne se rattachent a AUCUN canal : elles frappent la chaine elle-meme
> (troncatures, menus qui ne passent pas par le reseau). Un canal parfaitement rempli
> ne sert a rien si l'etage qui le lirait est court-circuite.

| perte | % des decisions | % des PARTIES |
|---|---:|---:|
| deux options du menu restent identiques pour le reseau | 53.75 % | **100.00 %** |
| la decision passe par le reseau | 86.06 % | **100.00 %** |
| une seule option : le reseau n'est pas consulte | 8.54 % | **100.00 %** |
| menu multi-selection : `act` retourne AVANT `encode`, hors du reseau | 5.41 % | **99.00 %** |
| la main depasse MAX_HAND | 22.92 % | **86.50 %** |
| la coupe de main retire une carte absente du menu | 17.10 % | **81.00 %** |
| le menu depasse MAX_OPTS : des options sont coupees | 2.18 % | **50.50 %** |
| la troncature a coupe LE coup reellement joue | 0.34 % | **15.00 %** |
| mon banc depasse MAX_BENCH | 0.13 % | **0.50 %** |
| le banc adverse depasse MAX_BENCH | 0.17 % | **0.50 %** |

🔑 **Lire la colonne PARTIES, pas la colonne decisions.** C'est la faute que ce
depot a payee six fois : une perte a 0,34 % des decisions touche **15 % des
parties**, et une partie perdue est une partie perdue. Le denominateur par
decision fait disparaitre exactement ce qui compte.

## 2. OU l'on perd — et a qui c'est imputable

### `dissect_v25.json`

- **n** : 49
- **wins** : 32
- **losses** : 17
- **taux** : 0.6530612244897959
- **ic95** : (0.5131093521943978, 0.7707579039068556)
- **n_validation** : 1
- **par_archetype_brut** : {'Crustle': [1, 1], 'Alakazam + Dudunsparce': [3, 3], 'Teal Mask Ogerpon ex': [1, 1], "Marnie's Grimmsnarl ex + Marnie's Morgrem": [12, 7], 'Alakazam + Kadabra': [9, 3], 'Drakloak + Dragapult ex': [3, 2], 'Mega Starmie ex + Mega Froslass ex': [1, 0], 'Archaludon ex + Cinderace': [4, 2], 'Mega Lucario ex + Hariyama': [4, 4], "Team Rocket's Spidops + Team Rocket's Mewtwo ex": [1, 1], "Cynthia's Gabite + Cynthia's Garchomp ex": [2, 2], 'Mega Lucario ex + Dudunsparce': [1, 1], 'Crustle + Mega Kangaskhan ex': [3, 1], 'N’s Zoroark ex': [1, 1], 'Mega Lucario ex': [1, 1], 'Mega Kangaskhan ex + Crustle': [1, 1], 'Kadabra + Alakazam': [1, 1]}
- **par_archetype_canonique** : {'Crustle': [1, 1], 'Alakazam + Dudunsparce': [3, 3], 'Teal Mask Ogerpon ex': [1, 1], "Marnie's Grimmsnarl ex + Marnie's Morgrem": [12, 7], 'Alakazam + Kadabra': [10, 4], 'Dragapult ex + Drakloak': [3, 2], 'Mega Froslass ex + Mega Starmie ex': [1, 0], 'Archaludon ex + Cinderace': [4, 2], 'Hariyama + Mega Lucario ex': [4, 4], "Team Rocket's Mewtwo ex + Team Rocket's Spidops": [1, 1], "Cynthia's Gabite + Cynthia's Garchomp ex": [2, 2], 'Dudunsparce + Mega Lucario ex': [1, 1], 'Crustle + Mega Kangaskhan ex': [4, 2], 'N’s Zoroark ex': [1, 1], 'Mega Lucario ex': [1, 1]}
- **premier** : {'n': 33, 'w': 27, 'ic': (0.6561143295070478, 0.9138934877430174)}
- **second** : {'n': 16, 'w': 5, 'ic': (0.14164435051961052, 0.5559606813326594)}
- **modes_fin** : {3: 17, 1: 24, 2: 8}
- **modes_fin_defaites** : {3: 10, 1: 6, 2: 1}
- **prix_concedes** : 125
- **prix_pris** : 167

| classe d'erreur | parties touchees | occurrences | p (lien avec la defaite) | statut |
|---|---:|---:|---:|---|
| E2d energie posee sur un emplacement qui n'attaquera jamais | 37 / 49 | 84 | 0.0497 ⚠ | MESUREE |
| E2c energie qui debloquait ailleurs, posee ou elle ne debloque rien | 4 / 49 | 5 | 0.2653 | MESUREE |
| E3c idem mais l'alternative chargee tape <100 (mineur) | 1 / 49 | 4 | 0.3400 | MESUREE |
| nos attaques offensives a 0 degat parce que la cible est immunisee | 1 / 49 | 13 | 0.3430 | MESUREE (champ nos_attaques_annulees) |
| Pokemon de banc OFFERTS et non poses (le fait ; cf. le test de lien) | 34 / 49 | 51 | 0.7263 | MESUREE (champ bench_non_poses) |
| E3 promotion non chargee devant un charge a >=100 degats | 8 / 49 | 18 | 0.7623 | MESUREE |
| E6 capacite offerte et non utilisee du tour | 16 / 49 | 56 | 0.8271 | MESUREE |
| E1 menu multi-selection sous-consomme (choisir_multi desarmee) | 34 / 49 | 50 | 0.8539 | MESUREE |
| E4 tour muet : attaque OFFENSIVE offerte, aucune declaree | 1 / 49 | 30 | 1.0000 | MESUREE |
| E2a energie du tour defaussee (<=1 tour) | 0 / 49 | — | 1.0000 | ZERO NON QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E3b promotion du plus faible de deux charges | 0 / 49 | — | 1.0000 | ZERO NON QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E5a KO immediat dispo, aucune attaque declaree | 0 / 49 | 0 | 1.0000 | ZERO QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E5b KO immediat dispo, attaque plus faible choisie | 0 / 49 | 0 | 1.0000 | ZERO QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| un mur IMMUNISE attend au banc (crustle_au_banc) pendant qu'un {ex} tue notre Pokemon | 13 / 49 | 19 | 1.0000 | MESUREE (derivee de ko_subis_detail) |

⚠ **`p` est un test de PERMUTATION sur la difference de frequence entre
parties gagnees et perdues.** Un `p` eleve ne veut pas dire que la classe
n'existe pas — il veut dire qu'on n'a PAS montre de lien avec la defaite.
Confondre les deux fabrique des chantiers imaginaires.

⚠ **Une classe a « 0 occurrence » peut etre DEFINITIONNELLE** : l'outil ne
pouvait pas la voir. Et une correlation n'est pas une cause — la dissection
v25 a vu une de ses conclusions refutee par ses propres donnees.

### `dissect_v26.json`

- **n** : 47
- **wins** : 27
- **losses** : 20
- **taux** : 0.574468085106383
- **ic95** : (0.43281668771211546, 0.7048658399817417)
- **n_validation** : 1
- **par_archetype_brut** : {'Ceruledge ex + Fezandipiti ex': [1, 1], 'Archaludon ex + Cinderace': [2, 1], 'Mega Lucario ex + Hariyama': [4, 2], 'Drakloak + Dragapult ex': [2, 1], "Marnie's Grimmsnarl ex + Marnie's Morgrem": [14, 9], 'Alakazam + Kadabra': [9, 6], "Cynthia's Gabite + Cynthia's Garchomp ex": [2, 2], "Marnie's Grimmsnarl ex + Froslass": [1, 0], 'Teal Mask Ogerpon ex + Arboliva ex': [1, 0], 'Teal Mask Ogerpon ex': [1, 1], 'Crustle': [1, 1], 'Dipplin + Thwackey': [1, 0], 'Crustle + Mega Kangaskhan ex': [4, 1], "Ethan's Quilava + Ethan's Typhlosion": [1, 0], 'Conkeldurr + Crabominable': [1, 1], "Crustle + Ethan's Quilava": [1, 0], 'Mega Kangaskhan ex + Crustle': [1, 1]}
- **par_archetype_canonique** : {'Ceruledge ex + Fezandipiti ex': [1, 1], 'Archaludon ex + Cinderace': [2, 1], 'Hariyama + Mega Lucario ex': [4, 2], 'Dragapult ex + Drakloak': [2, 1], "Marnie's Grimmsnarl ex + Marnie's Morgrem": [14, 9], 'Alakazam + Kadabra': [9, 6], "Cynthia's Gabite + Cynthia's Garchomp ex": [2, 2], "Froslass + Marnie's Grimmsnarl ex": [1, 0], 'Arboliva ex + Teal Mask Ogerpon ex': [1, 0], 'Teal Mask Ogerpon ex': [1, 1], 'Crustle': [1, 1], 'Dipplin + Thwackey': [1, 0], 'Crustle + Mega Kangaskhan ex': [5, 2], "Ethan's Quilava + Ethan's Typhlosion": [1, 0], 'Conkeldurr + Crabominable': [1, 1], "Crustle + Ethan's Quilava": [1, 0]}
- **premier** : {'n': 26, 'w': 14, 'ic': (0.35457636204430115, 0.712444173047651)}
- **second** : {'n': 21, 'w': 13, 'ic': (0.40878295815501514, 0.7924923220201749)}
- **modes_fin** : {2: 11, 3: 11, 1: 25}
- **modes_fin_defaites** : {3: 7, 1: 11, 2: 2}
- **prix_concedes** : 137
- **prix_pris** : 162

| classe d'erreur | parties touchees | occurrences | p (lien avec la defaite) | statut |
|---|---:|---:|---:|---|
| Pokemon de banc OFFERTS et non poses (le fait ; cf. le test de lien) | 36 / 47 | 51 | 0.0444 ⚠ | MESUREE (champ bench_non_poses) |
| un mur IMMUNISE attend au banc (crustle_au_banc) pendant qu'un {ex} tue notre Pokemon | 11 / 47 | 17 | 0.0637 | MESUREE (derivee de ko_subis_detail) |
| E1 menu multi-selection sous-consomme (choisir_multi desarmee) | 36 / 47 | 50 | 0.0666 | MESUREE |
| E6 capacite offerte et non utilisee du tour | 17 / 47 | 52 | 0.2128 | MESUREE |
| E2c energie qui debloquait ailleurs, posee ou elle ne debloque rien | 10 / 47 | 24 | 0.2259 | MESUREE |
| nos attaques offensives a 0 degat parce que la cible est immunisee | 1 / 47 | 2 | 0.4284 | MESUREE (champ nos_attaques_annulees) |
| E3 promotion non chargee devant un charge a >=100 degats | 3 / 47 | 5 | 0.7105 | MESUREE |
| E2d energie posee sur un emplacement qui n'attaquera jamais | 34 / 47 | 105 | 0.9458 | MESUREE |
| E3c idem mais l'alternative chargee tape <100 (mineur) | 1 / 47 | 6 | 1.0000 | MESUREE |
| E4 tour muet : attaque OFFENSIVE offerte, aucune declaree | 1 / 47 | 1 | 1.0000 | MESUREE |
| E2a energie du tour defaussee (<=1 tour) | 0 / 47 | — | 1.0000 | ZERO NON QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E3b promotion du plus faible de deux charges | 0 / 47 | — | 1.0000 | ZERO NON QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E5a KO immediat dispo, aucune attaque declaree | 0 / 47 | 0 | 1.0000 | ZERO QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E5b KO immediat dispo, attaque plus faible choisie | 0 / 47 | 0 | 1.0000 | ZERO QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |

⚠ **`p` est un test de PERMUTATION sur la difference de frequence entre
parties gagnees et perdues.** Un `p` eleve ne veut pas dire que la classe
n'existe pas — il veut dire qu'on n'a PAS montre de lien avec la defaite.
Confondre les deux fabrique des chantiers imaginaires.

⚠ **Une classe a « 0 occurrence » peut etre DEFINITIONNELLE** : l'outil ne
pouvait pas la voir. Et une correlation n'est pas une cause — la dissection
v25 a vu une de ses conclusions refutee par ses propres donnees.

### `dissect_v27.json`

- **n** : 43
- **wins** : 28
- **losses** : 15
- **taux** : 0.6511627906976745
- **ic95** : (0.501715070970981, 0.775816012510369)
- **n_validation** : 1
- **par_archetype_brut** : {'Mega Lucario ex + Hariyama': [10, 6], 'Crustle + Drednaw': [1, 0], 'Mega Abomasnow ex': [4, 4], "Marnie's Grimmsnarl ex + Dudunsparce": [1, 1], 'Alakazam + Kadabra': [6, 6], "Ethan's Quilava + Ethan's Typhlosion": [1, 0], "Team Rocket's Spidops + Team Rocket's Mewtwo ex": [2, 1], 'Mega Starmie ex + Dusclops': [1, 0], 'Dudunsparce + Kadabra': [1, 1], 'Conkeldurr + Crabominable': [1, 1], 'Drakloak + Dragapult ex': [4, 4], 'Mega Froslass ex + Mega Starmie ex': [1, 0], "Marnie's Grimmsnarl ex + Marnie's Morgrem": [4, 2], "Hop's Trevenant": [1, 1], 'Iono’s Bellibolt ex + Iono’s Kilowattrel': [1, 0], 'Dipplin + Thwackey': [1, 0], 'Crustle': [1, 0], 'Teal Mask Ogerpon ex': [1, 1], 'Dudunsparce + Mega Lopunny ex': [1, 0]}
- **par_archetype_canonique** : {'Hariyama + Mega Lucario ex': [10, 6], 'Crustle + Drednaw': [1, 0], 'Mega Abomasnow ex': [4, 4], "Dudunsparce + Marnie's Grimmsnarl ex": [1, 1], 'Alakazam + Kadabra': [6, 6], "Ethan's Quilava + Ethan's Typhlosion": [1, 0], "Team Rocket's Mewtwo ex + Team Rocket's Spidops": [2, 1], 'Dusclops + Mega Starmie ex': [1, 0], 'Dudunsparce + Kadabra': [1, 1], 'Conkeldurr + Crabominable': [1, 1], 'Dragapult ex + Drakloak': [4, 4], 'Mega Froslass ex + Mega Starmie ex': [1, 0], "Marnie's Grimmsnarl ex + Marnie's Morgrem": [4, 2], "Hop's Trevenant": [1, 1], 'Iono’s Bellibolt ex + Iono’s Kilowattrel': [1, 0], 'Dipplin + Thwackey': [1, 0], 'Crustle': [1, 0], 'Teal Mask Ogerpon ex': [1, 1], 'Dudunsparce + Mega Lopunny ex': [1, 0]}
- **premier** : {'n': 27, 'w': 18, 'ic': (0.47824419872105484, 0.8135694555640666)}
- **second** : {'n': 16, 'w': 10, 'ic': (0.38640647097934805, 0.8151901744524719)}
- **modes_fin** : {1: 18, 2: 13, 3: 12}
- **modes_fin_defaites** : {1: 8, 2: 2, 3: 5}
- **prix_concedes** : 114
- **prix_pris** : 119

| classe d'erreur | parties touchees | occurrences | p (lien avec la defaite) | statut |
|---|---:|---:|---:|---|
| un mur IMMUNISE attend au banc (crustle_au_banc) pendant qu'un {ex} tue notre Pokemon | 14 / 43 | 24 | 0.0298 ⚠ | MESUREE (derivee de ko_subis_detail) |
| E2d energie posee sur un emplacement qui n'attaquera jamais | 28 / 43 | 73 | 0.0507 | MESUREE |
| nos attaques offensives a 0 degat parce que la cible est immunisee | 2 / 43 | 20 | 0.1175 | MESUREE (champ nos_attaques_annulees) |
| E3 promotion non chargee devant un charge a >=100 degats | 5 / 43 | 17 | 0.3104 | MESUREE |
| E2c energie qui debloquait ailleurs, posee ou elle ne debloque rien | 10 / 43 | 22 | 0.4743 | MESUREE |
| E6 capacite offerte et non utilisee du tour | 7 / 43 | 21 | 0.4956 | MESUREE |
| E1 menu multi-selection sous-consomme (choisir_multi desarmee) | 0 / 43 | 0 | 1.0000 | ZERO QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E2a energie du tour defaussee (<=1 tour) | 0 / 43 | — | 1.0000 | ZERO NON QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E3b promotion du plus faible de deux charges | 0 / 43 | — | 1.0000 | ZERO NON QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E3c idem mais l'alternative chargee tape <100 (mineur) | 0 / 43 | — | 1.0000 | ZERO NON QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E4 tour muet : attaque OFFENSIVE offerte, aucune declaree | 0 / 43 | 0 | 1.0000 | ZERO QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E5a KO immediat dispo, aucune attaque declaree | 0 / 43 | 0 | 1.0000 | ZERO QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| E5b KO immediat dispo, attaque plus faible choisie | 0 / 43 | 0 | 1.0000 | ZERO QUALIFIE (absente du fichier : le generateur ne l'a pas emise) |
| Pokemon de banc OFFERTS et non poses (le fait ; cf. le test de lien) | 0 / 43 | 0 | 1.0000 | MESUREE (champ bench_non_poses) |

⚠ **`p` est un test de PERMUTATION sur la difference de frequence entre
parties gagnees et perdues.** Un `p` eleve ne veut pas dire que la classe
n'existe pas — il veut dire qu'on n'a PAS montre de lien avec la defaite.
Confondre les deux fabrique des chantiers imaginaires.

⚠ **Une classe a « 0 occurrence » peut etre DEFINITIONNELLE** : l'outil ne
pouvait pas la voir. Et une correlation n'est pas une cause — la dissection
v25 a vu une de ses conclusions refutee par ses propres donnees.

## 3. Ce qui a DEJA ete juge — ne pas reproposer

**120 verdicts** lus depuis le registre (genere le 2026-08-05 23:54).

- ⚠ **identifiants EN DOUBLE** : `C44`, `C49`, `C52`, `R49`
- ⚠ **cites dans le CODE, absents du registre** : `C39`, `R13`, `R14`

⛔ **Avant de proposer un mecanisme, demander au registre s'il est deja mort.**
Le 04/08, une entree de file demandait une arene DEJA jouee et perdue — et sa
commande etait de surcroit INERTE (variable globale armant les deux camps :
ecart nul par construction). Une tache peut etre perimee ET impossible.

## 4. Ce qui est CONSTRUCTIBLE, et a quel cout

| classe | ce que c'est | entrees |
|---|---|---:|
| **A** | CONSTRUCTIBLE MAINTENANT (re-encodage ~1,2 h, zero re-extraction) | 10 |
| **B** | EXIGE LA RE-EXTRACTION (3,66 h + 1,2 h de re-encodage) | 12 |
| **C** | EXIGE UN ENTRAINEMENT D'UN AUTRE TYPE | 5 |
| **D** | FERME PAR UNE MESURE (ne pas repayer sous un autre nom) | 9 |
| **E** | STRUCTURELLEMENT IMPOSSIBLE DEPUIS L'OBSERVATION | 5 |

Source : `docs\16_inventaire_trous.md` (genere le 2026-08-05 18:50).

⛔ **Les classes D et E ne sont pas des chantiers.** D = ferme par une MESURE (le
repayer sous un autre nom est la faute que ce depot a commise cinq fois sur la
famille des etages de decision). E = structurellement impossible depuis
l'observation — le *baiting*, par exemple, est une INTENTION, pas un etat : rien
dans ce que le moteur livre ne la distingue d'un placement ordinaire.

---

> ⚖ **CE QUE CET INSTRUMENT NE FAIT PAS, DELIBEREMENT : un SCORE unique.** Fondre un
> poids, une troncature et une carte fausse en un seul nombre demanderait des
> coefficients ecrits a la main — exactement le « nombre en dur qui mentira dans trois
> jours ». Il rend des **dettes etiquetees avec leur grandeur mesuree et leur source** ;
> le tri reste a l'humain, donc visible et discutable.
