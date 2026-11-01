import type { Ref } from 'react';

import type { Group } from '../api/client';
import type { GroupSatellites } from '../hooks/useGroupSatellites';
import { RollingNumber } from './RollingNumber';
import { Tile } from './Tile';

interface GroupsTileProps {
  groups: Group[] | null;
  groupsFailed: boolean;
  group: string | null;
  satellites: GroupSatellites;
  onSelectGroup: (slug: string) => void;
  /** Receives the active group's row so the dock can move focus to it. */
  activeRowRef?: Ref<HTMLButtonElement>;
}

/** The CelesTrak groups; the active one is drawn on the globe. */
export function GroupsTile({
  groups,
  groupsFailed,
  group,
  satellites,
  onSelectGroup,
  activeRowRef,
}: GroupsTileProps) {
  return (
    <Tile
      id="groups"
      title="Groups"
      meta={groups ? <RollingNumber value={groups.length} /> : undefined}
    >
      {groupsFailed && <p className="status error">Could not reach the API.</p>}
      {!groupsFailed && groups === null && <p className="status">Loading groups…</p>}
      {groups?.length === 0 && (
        <p className="empty-state">No data yet. Run the ingest worker or `make seed`.</p>
      )}
      {groups && groups.length > 0 && (
        <ul className="tile-scroll" aria-label="Satellite groups">
          {groups.map((g) => {
            const active = g.slug === group;
            return (
              <li key={g.slug}>
                <button
                  type="button"
                  className="list-row"
                  aria-pressed={active}
                  ref={active ? activeRowRef : undefined}
                  onClick={() => {
                    onSelectGroup(g.slug);
                  }}
                >
                  <span className="name">{g.name}</span>
                  <RollingNumber className="value" value={g.satellite_count} />
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {satellites.error && <p className="status error">{satellites.error}</p>}
    </Tile>
  );
}
