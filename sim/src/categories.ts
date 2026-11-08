// State categories: a few interpretable axes that summarise a position from one player's side.
//
// A category is a short key such as "race:behind ready:1-0 ko:yes threat:yes". Its axes are
// computed from the cheap feature groups (no engine probes), so categorising is about a millisecond
// and means the same thing the value models see. The axes:
//   race    prize cards left: ahead (fewer left than the opponent) / even / behind
//   ready   attackers ready now, mine-theirs, each 0 / 1 / 2+ (a Pokémon in play with an attack
//           whose Energy cost its attached Energy meets)
//   ko      can I Knock Out something this turn (rules-based reach: attacker, Energy within one
//           attachment, a way into the Active Spot, gust for benched targets)
//   threat  can the opponent Knock Out my Active on their next turn (same reach, their side,
//           public information only)
// The full feature vector is recorded next to the category in playouts, so finer categories can be
// derived later (clustering, more axes) without replaying games.
import { features } from './features';
import { Sim } from './sim';

export interface Category {
  key: string;
  axes: { race: 'ahead' | 'even' | 'behind'; readyMe: number; readyOp: number; ko: boolean; threat: boolean };
}

const bin = (n: number) => (n >= 2 ? 2 : n);

export function categorize(sim: Sim, me: number): Category {
  const fv = features(sim, me, ['board', 'attacks', 'resources', 'reach']);
  const v = (name: string) => {
    const i = fv.names.indexOf(name);
    return i < 0 ? 0 : fv.values[i];
  };
  const prizesMe = v('me.prizes'), prizesOp = v('op.prizes');
  const race = prizesMe < prizesOp ? 'ahead' : prizesMe > prizesOp ? 'behind' : 'even';
  const ready = (tag: string) => {
    let n = 0;
    for (let a = 0; a < 6; a++) {
      if (!v(`${tag}.s${a}.present`)) {
        continue;
      }
      if ([0, 1].some(j => v(`${tag}.s${a}.a${j}.present`) && v(`${tag}.s${a}.a${j}.gap`) === 0)) {
        n++;
      }
    }
    return bin(n);
  };
  const readyMe = ready('me'), readyOp = ready('op');
  const ko = v('me.reach.maxPrize') > 0;
  const threat = v('op.reach.ko0') > 0;
  const key = `race:${race} ready:${readyMe}-${readyOp} ko:${ko ? 'yes' : 'no'} threat:${threat ? 'yes' : 'no'}`;
  return { key, axes: { race, readyMe, readyOp, ko, threat } };
}
