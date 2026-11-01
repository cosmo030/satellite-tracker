import { useState, type Ref, type SubmitEvent } from 'react';

import {
  ORBIT_CLASSES,
  withSearchChanges,
  type SatellitePage,
  type SatelliteSearch,
  type SearchChanges,
} from '../api/client';
import { formatCount } from '../orbit/format';
import { OWNER_OPTIONS, ownerCodeFor, ownerName } from '../ui/catalog';
import { shortcutModifierLabel } from '../ui/keyboard';
import { SearchIcon } from './icons';
import { RollingNumber } from './RollingNumber';
import { Tile } from './Tile';

type FilterKind = 'orbit' | 'country' | 'year';

const FILTER_LABELS: Record<FilterKind, string> = {
  orbit: 'Orbit',
  country: 'Country',
  year: 'Launch year',
};
const FILTER_KINDS: readonly FilterKind[] = ['orbit', 'country', 'year'];
const FILTER_CLEARED: Record<FilterKind, SearchChanges> = {
  orbit: { orbitClass: undefined },
  country: { country: undefined },
  year: { launchYear: undefined },
};
const SHORTCUT_HINT = shortcutModifierLabel(navigator.userAgent);
const FIRST_LAUNCH_YEAR = 1957;
const LAST_LAUNCH_YEAR = 2100;
// SATCAT owner codes are short upper-case words such as "US", "PRC" or "EUME".
const OWNER_CODE_PATTERN = /^[A-Z0-9/]{1,10}$/;

interface SearchTileProps {
  search: SatelliteSearch;
  currentGroup: string | null;
  onChange: (search: SatelliteSearch) => void;
  page: SatellitePage | null;
  error: string | null;
  selectedId: number | null;
  onSelect: (noradId: number) => void;
  inputRef?: Ref<HTMLInputElement>;
}

/** Search field, filter chips and the list of matching satellites. */
export function SearchTile({
  search,
  currentGroup,
  onChange,
  page,
  error,
  selectedId,
  onSelect,
  inputRef,
}: SearchTileProps) {
  const [editing, setEditing] = useState<FilterKind | null>(null);
  const update = (changes: SearchChanges) => {
    onChange(withSearchChanges(search, changes));
  };

  return (
    <Tile
      id="search"
      title="Search"
      className="search-tile"
      meta={page ? <MatchCount total={page.total} /> : undefined}
    >
      <label className="field">
        <SearchIcon />
        <input
          ref={inputRef}
          type="search"
          placeholder="Name or NORAD ID"
          aria-label="Search by name or NORAD ID"
          maxLength={100}
          value={search.q ?? ''}
          onChange={(event) => {
            update({ q: event.target.value });
          }}
          onKeyDown={(event) => {
            if (event.key === 'Escape') update({ q: undefined });
          }}
        />
        <kbd className="kbd">{SHORTCUT_HINT}</kbd>
      </label>
      <FilterChips
        search={search}
        editing={editing}
        onEdit={(kind) => {
          setEditing((current) => (current === kind ? null : kind));
        }}
        onRemove={(kind) => {
          update(FILTER_CLEARED[kind]);
        }}
      />
      {editing && (
        <FilterEditor
          kind={editing}
          onApply={(changes) => {
            update(changes);
            setEditing(null);
          }}
          onCancel={() => {
            setEditing(null);
          }}
        />
      )}
      <ScopeSwitch
        checked={search.group !== undefined}
        disabled={!currentGroup}
        onToggle={(checked) => {
          update({ group: checked ? (currentGroup ?? undefined) : undefined });
        }}
      />
      {error && <p className="status error">Search failed. Is the API running?</p>}
      {page && <Results page={page} selectedId={selectedId} onSelect={onSelect} />}
    </Tile>
  );
}

/** The only count announced to screen readers when it changes (spec 6.1). */
function MatchCount({ total }: { total: number }) {
  return (
    <span aria-live="polite">
      <RollingNumber value={total} /> {total === 1 ? 'match' : 'matches'}
    </span>
  );
}

function activeFilterLabel(kind: FilterKind, search: SatelliteSearch): string | null {
  if (kind === 'orbit') return search.orbitClass ?? null;
  if (kind === 'country') return search.country ? ownerName(search.country) : null;
  return search.launchYear !== undefined ? String(search.launchYear) : null;
}

interface FilterChipsProps {
  search: SatelliteSearch;
  editing: FilterKind | null;
  onEdit: (kind: FilterKind) => void;
  onRemove: (kind: FilterKind) => void;
}

function FilterChips({ search, editing, onEdit, onRemove }: FilterChipsProps) {
  return (
    <div className="chips" role="group" aria-label="Filters">
      {FILTER_KINDS.map((kind) => {
        const active = activeFilterLabel(kind, search);
        if (active !== null) {
          return (
            <button
              key={kind}
              type="button"
              className="chip"
              aria-label={`Remove ${FILTER_LABELS[kind].toLowerCase()} filter ${active}`}
              onClick={() => {
                onRemove(kind);
              }}
            >
              {active}
              <span className="remove" aria-hidden="true">
                ×
              </span>
            </button>
          );
        }
        return (
          <button
            key={kind}
            type="button"
            className="chip chip-outline"
            aria-expanded={editing === kind}
            onClick={() => {
              onEdit(kind);
            }}
          >
            {FILTER_LABELS[kind]}
          </button>
        );
      })}
    </div>
  );
}

interface FilterEditorProps {
  kind: FilterKind;
  onApply: (changes: SearchChanges) => void;
  onCancel: () => void;
}

function FilterEditor({ kind, onApply, onCancel }: FilterEditorProps) {
  if (kind === 'orbit') {
    return (
      <div className="filter-editor" role="group" aria-label="Orbit class">
        {ORBIT_CLASSES.map((orbitClass) => (
          <button
            key={orbitClass}
            type="button"
            className="chip"
            onClick={() => {
              onApply({ orbitClass });
            }}
          >
            {orbitClass === 'OTHER' ? 'Other' : orbitClass}
          </button>
        ))}
      </div>
    );
  }
  return kind === 'country' ? (
    <CountryEditor onApply={onApply} onCancel={onCancel} />
  ) : (
    <YearEditor onApply={onApply} onCancel={onCancel} />
  );
}

type EditorProps = Omit<FilterEditorProps, 'kind'>;

function CountryEditor({ onApply, onCancel }: EditorProps) {
  const [text, setText] = useState('');
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    const raw = text.trim().toUpperCase();
    const code = ownerCodeFor(text) ?? (OWNER_CODE_PATTERN.test(raw) ? raw : null);
    if (code) onApply({ country: code });
  };
  return (
    <form className="filter-editor" onSubmit={submit}>
      <label className="field">
        <input
          autoFocus
          list="owner-options"
          placeholder="Country or code"
          aria-label="Country or owner code"
          maxLength={40}
          value={text}
          onChange={(event) => {
            setText(event.target.value);
          }}
          onKeyDown={(event) => {
            if (event.key === 'Escape') onCancel();
          }}
        />
      </label>
      <datalist id="owner-options">
        {OWNER_OPTIONS.map((option) => (
          <option key={option.code} value={option.name} />
        ))}
      </datalist>
      <button type="submit" className="chip">
        Apply
      </button>
    </form>
  );
}

function YearEditor({ onApply, onCancel }: EditorProps) {
  const [text, setText] = useState('');
  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    const year = Number.parseInt(text, 10);
    if (year >= FIRST_LAUNCH_YEAR && year <= LAST_LAUNCH_YEAR) onApply({ launchYear: year });
  };
  return (
    <form className="filter-editor" onSubmit={submit}>
      <label className="field">
        <input
          autoFocus
          type="number"
          inputMode="numeric"
          min={FIRST_LAUNCH_YEAR}
          max={LAST_LAUNCH_YEAR}
          placeholder="e.g. 2017"
          aria-label="Launch year"
          value={text}
          onChange={(event) => {
            setText(event.target.value);
          }}
          onKeyDown={(event) => {
            if (event.key === 'Escape') onCancel();
          }}
        />
      </label>
      <button type="submit" className="chip">
        Apply
      </button>
    </form>
  );
}

interface ScopeSwitchProps {
  checked: boolean;
  disabled: boolean;
  onToggle: (checked: boolean) => void;
}

function ScopeSwitch({ checked, disabled, onToggle }: ScopeSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      className="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => {
        onToggle(!checked);
      }}
    >
      <span className="switch-track" aria-hidden="true" />
      Only the selected group
    </button>
  );
}

interface ResultsProps {
  page: SatellitePage;
  selectedId: number | null;
  onSelect: (noradId: number) => void;
}

function Results({ page, selectedId, onSelect }: ResultsProps) {
  return (
    <div className="tile-scroll">
      <ul aria-label="Matching satellites">
        {page.items.map((satellite) => {
          const selected = satellite.norad_id === selectedId;
          return (
            <li key={satellite.norad_id}>
              <button
                type="button"
                className="list-row"
                aria-current={selected}
                onClick={() => {
                  onSelect(satellite.norad_id);
                }}
              >
                {selected && <span className="dot" aria-hidden="true" />}
                <span className="name">{satellite.name}</span>
                <span className="value ident">{satellite.norad_id}</span>
              </button>
            </li>
          );
        })}
      </ul>
      {page.total > page.items.length && (
        <p className="list-footer">
          Showing the first {page.items.length} of {formatCount(page.total)}
        </p>
      )}
    </div>
  );
}
