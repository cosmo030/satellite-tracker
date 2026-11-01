import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';

import { ApiClient, type Group, type SatelliteSearch } from './api/client';
import { Dock } from './components/Dock';
import { GroupsTile } from './components/GroupsTile';
import { PassesTile } from './components/PassesTile';
import { SearchTile } from './components/SearchTile';
import { SelectedTile } from './components/SelectedTile';
import { SettingsPopover } from './components/SettingsPopover';
import { TimelineTile } from './components/TimelineTile';
import { ViewportTile } from './components/ViewportTile';
import {
  Workspace,
  type RevealTarget,
  type WorkspaceHandle,
  type WorkspaceTiles,
} from './components/Workspace';
import { Globe, type GlobeHandle } from './globe/Globe';
import type { GlobeLayers } from './globe/GlobeScene';
import { useGroups } from './hooks/useGroups';
import { useGroupSatellites } from './hooks/useGroupSatellites';
import { useLayoutMode, type LayoutMode } from './hooks/useMediaQuery';
import { useNow } from './hooks/useNow';
import { useSatelliteSearch } from './hooks/useSatelliteSearch';
import { useSelectedSatellite } from './hooks/useSelectedSatellite';
import { useSkin } from './hooks/useSkin';
import { isSearchShortcut } from './ui/keyboard';
import { defaultLayout, LAYOUT_STORAGE_KEY, parseStoredLayout } from './ui/layout';
import { readStorage, removeStorage } from './ui/storage';

const DEFAULT_GROUP = 'stations';
const DETAILS_REFRESH_MS = 1000;
const api = new ApiClient();

/** The group shown on the globe: the user's choice, else Space stations, else the first group. */
function activeGroup(groups: Group[] | null, chosen: string | null): Group | null {
  if (!groups) return null;
  const wanted = chosen ?? DEFAULT_GROUP;
  return groups.find((g) => g.slug === wanted) ?? groups[0] ?? null;
}

/** Focus targets for the dock buttons, filled in by the tiles. */
interface FocusTargets {
  search: HTMLInputElement | null;
  groups: HTMLButtonElement | null;
  timeline: HTMLButtonElement | null;
}

export function App() {
  const { groups, failed: groupsFailed } = useGroups(api);
  const [chosenGroup, setChosenGroup] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [search, setSearch] = useState<SatelliteSearch>({ limit: 25 });
  const now = useNow(DETAILS_REFRESH_MS);

  const current = activeGroup(groups, chosenGroup);
  const group = current?.slug ?? null;
  const satellites = useGroupSatellites(api, group);
  const results = useSatelliteSearch(api, search);
  const selected = useSelectedSatellite(api, selectedId, now);

  const skin = useSkin();
  const mode = useLayoutMode();
  const [layout, setLayout] = useState(() => ({
    version: 0,
    initial: parseStoredLayout(readStorage(LAYOUT_STORAGE_KEY)),
  }));
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sheet, setSheet] = useState<RevealTarget | null>(null);
  const [lighting, setLighting] = useState(true);
  const [layers, setLayers] = useState<GlobeLayers>({ orbitPath: true, groundTrack: true });
  const [viewportTile, setViewportTile] = useState<HTMLElement | null>(null);

  const workspaceRef = useRef<WorkspaceHandle>(null);
  const globeRef = useRef<GlobeHandle>(null);
  const settingsButtonRef = useRef<HTMLButtonElement>(null);
  const focusTargets = useRef<FocusTargets>({ search: null, groups: null, timeline: null });

  const reveal = useCallback(
    (target: RevealTarget) => {
      if (mode === 'narrow') setSheet(target);
      else workspaceRef.current?.reveal(target);
      focusSoon(focusTargets.current, target);
    },
    [mode],
  );
  useSearchShortcut(reveal);
  // Dock buttons toggle a bottom sheet on small screens; elsewhere they reveal the tile.
  const dockAction = (target: RevealTarget) => () => {
    if (mode === 'narrow' && sheet === target) setSheet(null);
    else reveal(target);
  };

  const selectSatellite = (noradId: number | null) => {
    setSelectedId(noradId);
    if (mode === 'narrow') setSheet(noradId === null ? null : 'selected');
  };

  const tiles: WorkspaceTiles = {
    groups: (
      <GroupsTile
        groups={groups}
        groupsFailed={groupsFailed}
        group={group}
        satellites={satellites}
        activeRowRef={(element) => {
          focusTargets.current.groups = element;
        }}
        onSelectGroup={(slug) => {
          setChosenGroup(slug);
          setSearch((previous) =>
            previous.group === undefined ? previous : { ...previous, group: slug },
          );
        }}
      />
    ),
    search: (
      <SearchTile
        search={search}
        currentGroup={group}
        onChange={setSearch}
        page={results.page}
        error={results.error}
        selectedId={selectedId}
        onSelect={selectSatellite}
        inputRef={(element) => {
          focusTargets.current.search = element;
        }}
      />
    ),
    viewport: (
      <ViewportTile
        tileRef={setViewportTile}
        groupName={current?.name ?? null}
        satelliteCount={satellites.isLoading ? null : satellites.noradIds.length}
        lighting={lighting}
        onToggleLighting={() => {
          setLighting((on) => !on);
        }}
        layers={layers}
        onChangeLayers={setLayers}
      />
    ),
    timeline: (
      <TimelineTile
        now={now}
        liveRef={(element) => {
          focusTargets.current.timeline = element;
        }}
      />
    ),
    selected: (
      <SelectedTile
        selectedId={selectedId}
        detail={selected.detail}
        state={selected.state}
        now={now}
        error={selected.error}
        onClose={() => {
          selectSatellite(null);
        }}
      />
    ),
    passes: <PassesTile />,
  };

  const dock = (
    <Dock
      onHome={() => {
        globeRef.current?.flyHome();
        setSheet(null);
      }}
      onSearch={dockAction('search')}
      onGroups={dockAction('groups')}
      onTimeline={dockAction('timeline')}
      onSettings={() => {
        setSettingsOpen((open) => !open);
      }}
      settingsOpen={settingsOpen}
      openSheet={mode === 'narrow' ? sheet : null}
      settingsButtonRef={settingsButtonRef}
    />
  );

  return (
    <>
      <Globe
        ref={globeRef}
        noradIds={satellites.noradIds}
        positions={satellites.positions}
        selectedId={selectedId}
        selectedPosition={selected.state}
        selectedTrack={selected.track}
        onPick={selectSatellite}
        viewportTile={viewportTile}
        skin={skin.skin}
        lighting={lighting}
        layers={layers}
        now={now}
      />
      <div className={mode === 'narrow' ? 'app narrow' : 'app'}>
        {dock}
        <Layout
          mode={mode}
          tiles={tiles}
          sheet={sheet}
          selectedOpen={selectedId !== null}
          workspace={
            <Workspace
              key={layout.version}
              ref={workspaceRef}
              tiles={tiles}
              initialLayout={layout.initial}
              withRightColumn={mode === 'wide'}
              onLayoutChange={() => {
                globeRef.current?.updatePlacement();
              }}
            />
          }
        />
        {settingsOpen && (
          <SettingsPopover
            skin={skin.preference}
            glassNote={skin.glassNote}
            onSkinChange={skin.choose}
            onResetLayout={() => {
              removeStorage(LAYOUT_STORAGE_KEY);
              setLayout((current) => ({ version: current.version + 1, initial: defaultLayout() }));
            }}
            onClose={() => {
              setSettingsOpen(false);
            }}
            anchorRef={settingsButtonRef}
            modal={mode === 'narrow'}
          />
        )}
      </div>
    </>
  );
}

interface LayoutProps {
  mode: LayoutMode;
  tiles: WorkspaceTiles;
  workspace: ReactNode;
  sheet: RevealTarget | null;
  selectedOpen: boolean;
}

/** Wide: the full workspace. Medium: workspace plus a sliding right sheet. Narrow: bottom sheets. */
function Layout({ mode, tiles, workspace, sheet, selectedOpen }: LayoutProps) {
  if (mode === 'narrow') {
    return (
      <>
        {tiles.viewport}
        {sheet && <div className="sheet bottom-sheet">{tiles[sheet]}</div>}
      </>
    );
  }
  return (
    <>
      {workspace}
      {mode === 'medium' && (
        <aside
          className="sheet side-sheet"
          data-open={selectedOpen}
          inert={!selectedOpen}
          aria-label="Selected satellite"
        >
          {tiles.selected}
          {tiles.passes}
        </aside>
      )}
    </>
  );
}

/** Move focus to a tile's main control once it has been revealed (after React and the panels update). */
function focusSoon(targets: FocusTargets, target: RevealTarget): void {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (target === 'search') targets.search?.select();
      if (target === 'search' || target === 'groups' || target === 'timeline')
        targets[target]?.focus();
    });
  });
}

/** ⌘K / Ctrl K reveals and focuses the search field from anywhere. */
function useSearchShortcut(reveal: (target: RevealTarget) => void): void {
  const revealRef = useRef(reveal);
  useEffect(() => {
    revealRef.current = reveal;
  }, [reveal]);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!isSearchShortcut(event)) return;
      event.preventDefault();
      revealRef.current('search');
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
    };
  }, []);
}
