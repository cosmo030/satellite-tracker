import { Tile } from './Tile';

/** Pass predictions need an observer location and the phase 2 passes endpoint; until then, an empty state. */
export function PassesTile() {
  return (
    <Tile id="passes" title="Next passes" meta="max elev.">
      <p className="empty-state">Pass predictions for your location arrive in a later update.</p>
    </Tile>
  );
}
