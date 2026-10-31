import { useEffect, useState } from 'react';

import { ApiClient, type Group, type SatelliteSearch } from './api/client';
import { DetailsPanel } from './components/DetailsPanel';
import { GroupPanel } from './components/GroupPanel';
import { SearchPanel } from './components/SearchPanel';
import { Globe } from './globe/Globe';
import { useGroupSatellites } from './hooks/useGroupSatellites';
import { useNow } from './hooks/useNow';
import { useSatelliteSearch } from './hooks/useSatelliteSearch';
import { useSelectedSatellite } from './hooks/useSelectedSatellite';

const DEFAULT_GROUP = 'stations';
const DETAILS_REFRESH_MS = 1000;
const api = new ApiClient();

function preferredGroup(groups: Group[]): string | null {
  return groups.find((g) => g.slug === DEFAULT_GROUP)?.slug ?? groups[0]?.slug ?? null;
}

export function App() {
  const [groups, setGroups] = useState<Group[] | null>(null);
  const [groupsError, setGroupsError] = useState(false);
  const [chosenGroup, setChosenGroup] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [search, setSearch] = useState<SatelliteSearch>({ limit: 25 });
  const now = useNow(DETAILS_REFRESH_MS);

  useEffect(() => {
    const controller = new AbortController();
    api
      .listGroups(controller.signal)
      .then(setGroups)
      .catch(() => {
        if (!controller.signal.aborted) setGroupsError(true);
      });
    return () => {
      controller.abort();
    };
  }, []);

  const group = chosenGroup ?? (groups ? preferredGroup(groups) : null);
  const satellites = useGroupSatellites(api, group);
  const results = useSatelliteSearch(api, search);
  const selected = useSelectedSatellite(api, selectedId, now);

  return (
    <div className="app">
      <aside className="sidebar">
        <header>
          <h1>Satellite Tracker</h1>
          <p className="muted">Live positions from open orbital data</p>
        </header>
        <GroupPanel
          groups={groups}
          groupsFailed={groupsError}
          group={group}
          satellites={satellites}
          onSelectGroup={(slug) => {
            setChosenGroup(slug);
            setSearch((previous) =>
              previous.group === undefined ? previous : { ...previous, group: slug },
            );
          }}
        />
        {selectedId !== null && (
          <DetailsPanel
            detail={selected.detail}
            state={selected.state}
            now={now}
            error={selected.error}
            onClose={() => {
              setSelectedId(null);
            }}
          />
        )}
        <SearchPanel
          search={search}
          currentGroup={group}
          onChange={setSearch}
          page={results.page}
          error={results.error}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
        <footer className="muted small">
          Orbital data: <a href="https://celestrak.org">CelesTrak</a>. Globe:{' '}
          <a href="https://cesium.com/platform/cesiumjs/">CesiumJS</a>.
        </footer>
      </aside>
      <main className="globe-container">
        <Globe
          noradIds={satellites.noradIds}
          positions={satellites.positions}
          selectedId={selectedId}
          selectedPosition={selected.state}
          selectedTrack={selected.track}
          onPick={setSelectedId}
        />
      </main>
    </div>
  );
}
