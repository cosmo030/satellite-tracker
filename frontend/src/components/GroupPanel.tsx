import type { Group } from '../api/client';
import type { GroupSatellites } from '../hooks/useGroupSatellites';

interface GroupPanelProps {
  groups: Group[] | null;
  groupsFailed: boolean;
  group: string | null;
  satellites: GroupSatellites;
  onSelectGroup: (slug: string) => void;
}

/** Picks which group of satellites is shown on the globe. */
export function GroupPanel({
  groups,
  groupsFailed,
  group,
  satellites,
  onSelectGroup,
}: GroupPanelProps) {
  const hasGroups = groups !== null && groups.length > 0;
  return (
    <section className="panel">
      <label>
        Group
        <select
          value={group ?? ''}
          disabled={!hasGroups}
          onChange={(event) => {
            onSelectGroup(event.target.value);
          }}
        >
          {groups?.map((g) => (
            <option key={g.slug} value={g.slug}>
              {g.name} ({g.satellite_count})
            </option>
          ))}
        </select>
      </label>
      {groupsFailed && <p className="error">Could not reach the API.</p>}
      {groups?.length === 0 && (
        <p className="warning">No data yet. Run the ingest worker or `make seed`.</p>
      )}
      <GroupStatus group={group} satellites={satellites} />
    </section>
  );
}

function GroupStatus({ group, satellites }: Pick<GroupPanelProps, 'group' | 'satellites'>) {
  if (!group) return null;
  if (satellites.isLoading) return <p className="muted">Loading satellites…</p>;
  if (satellites.error) return <p className="error">{satellites.error}</p>;
  return <p className="muted">{satellites.noradIds.length} satellites on the globe</p>;
}
