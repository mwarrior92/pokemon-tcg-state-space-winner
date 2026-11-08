# Third-party notices

This repository includes or depends on the following third-party software.

## Included in this repository

### Twinleaf game engine (fork) - `engine/twinleaf/`
- Source: https://github.com/twinleafgg/twinleafgg (folder `ptcg-server/`), based on
  RyuuPlay (https://github.com/keeshii/ryuu-play)
- License: MIT - full text and copyright notices in [engine/twinleaf/LICENSE](engine/twinleaf/LICENSE)
- Copyright (c) 2020 keeshii; Copyright (c) twinleaf.gg contributors
- Modified: yes - local changes are listed in [engine/twinleaf/UPSTREAM.md](engine/twinleaf/UPSTREAM.md)
  and marked in the source with `[winner patch NNN]`.

## npm packages used by `sim/` (installed, not committed)

| Package | License | Use |
|---|---|---|
| esbuild | MIT | bundling (dev) |
| typescript | Apache-2.0 | type checking (dev) |
| @types/node | MIT | type definitions (dev) |
| @progress/pako-esm | MIT | imported by the engine's replay module |

## Game content

Pokémon card names, card text and related content are trademarks and copyright of Nintendo,
Creatures Inc., GAME FREAK inc. and The Pokémon Company. This project is not affiliated with,
endorsed by, or sponsored by them.
