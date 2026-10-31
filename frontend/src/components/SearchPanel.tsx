import {
  ORBIT_CLASSES,
  withSearchChanges,
  type OrbitClass,
  type SatellitePage,
  type SatelliteSearch,
  type SearchChanges,
} from '../api/client';

interface SearchPanelProps {
  search: SatelliteSearch;
  currentGroup: string | null;
  onChange: (search: SatelliteSearch) => void;
  page: SatellitePage | null;
  error: string | null;
  selectedId: number | null;
  onSelect: (noradId: number) => void;
}

/** Search box, filters and the list of matching satellites. */
export function SearchPanel({
  search,
  currentGroup,
  onChange,
  page,
  error,
  selectedId,
  onSelect,
}: SearchPanelProps) {
  const update = (changes: SearchChanges) => {
    onChange(withSearchChanges(search, changes));
  };

  return (
    <section className="panel" aria-labelledby="search-heading">
      <h2 id="search-heading">Search</h2>
      <input
        type="search"
        placeholder="Name or NORAD ID"
        aria-label="Search by name or NORAD ID"
        maxLength={100}
        value={search.q ?? ''}
        onChange={(event) => {
          update({ q: event.target.value });
        }}
      />
      <div className="filters">
        <label className="checkbox">
          <input
            type="checkbox"
            disabled={!currentGroup}
            checked={search.group !== undefined}
            onChange={(event) => {
              update({ group: event.target.checked ? (currentGroup ?? undefined) : undefined });
            }}
          />
          Only the selected group
        </label>
        <label>
          Orbit
          <select
            value={search.orbitClass ?? ''}
            onChange={(event) => {
              update({ orbitClass: (event.target.value || undefined) as OrbitClass | undefined });
            }}
          >
            <option value="">Any</option>
            {ORBIT_CLASSES.map((orbitClass) => (
              <option key={orbitClass} value={orbitClass}>
                {orbitClass}
              </option>
            ))}
          </select>
        </label>
        <label>
          Country
          <input
            type="text"
            placeholder="e.g. US"
            maxLength={10}
            value={search.country ?? ''}
            onChange={(event) => {
              update({ country: event.target.value });
            }}
          />
        </label>
        <label>
          Launch year
          <input
            type="number"
            min={1957}
            max={2100}
            value={search.launchYear ?? ''}
            onChange={(event) => {
              const year = Number.parseInt(event.target.value, 10);
              update({ launchYear: Number.isNaN(year) ? undefined : year });
            }}
          />
        </label>
      </div>
      {error && <p className="error">Search failed. Is the API running?</p>}
      {page && (
        <>
          <p className="muted">
            {page.total.toLocaleString('en-US')} match{page.total === 1 ? '' : 'es'}
            {page.total > page.items.length ? `, showing ${page.items.length}` : ''}
          </p>
          <ul className="results">
            {page.items.map((satellite) => (
              <li key={satellite.norad_id}>
                <button
                  type="button"
                  className={satellite.norad_id === selectedId ? 'selected' : undefined}
                  onClick={() => {
                    onSelect(satellite.norad_id);
                  }}
                >
                  <span>{satellite.name}</span>
                  <span className="muted">
                    {satellite.norad_id}
                    {satellite.orbit_class ? ` · ${satellite.orbit_class}` : ''}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
