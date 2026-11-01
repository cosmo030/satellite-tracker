import type { ReactNode } from 'react';

import type { ElementSet, OrbitClass, SatelliteDetail } from '../api/client';
import {
  epochAgeMs,
  epochFreshness,
  formatCalendarDate,
  formatDegrees,
  formatElementAge,
  formatFixed,
  formatPeriod,
  formatUtcTimestamp,
} from '../orbit/format';
import type { SatelliteState } from '../orbit/propagation';
import { objectTypeLabel, ownerName } from '../ui/catalog';
import { CloseIcon } from './icons';
import { Tile } from './Tile';

const MISSING = '—';

interface SelectedTileProps {
  selectedId: number | null;
  detail: SatelliteDetail | null;
  state: SatelliteState | null;
  now: Date;
  error: string | null;
  onClose: () => void;
}

/** Live position and catalog facts for the selected satellite. */
export function SelectedTile({
  selectedId,
  detail,
  state,
  now,
  error,
  onClose,
}: SelectedTileProps) {
  const orbitClass = detail?.satellite.orbit_class ?? detail?.latest_elements?.orbit_class ?? null;
  const meta =
    selectedId === null ? undefined : <SelectedMeta orbitClass={orbitClass} onClose={onClose} />;
  return (
    <Tile id="selected" title="Selected" meta={meta}>
      <div className="tile-scroll">
        <SelectedBody
          selectedId={selectedId}
          detail={detail}
          state={state}
          now={now}
          error={error}
        />
      </div>
    </Tile>
  );
}

function SelectedMeta({
  orbitClass,
  onClose,
}: {
  orbitClass: OrbitClass | null;
  onClose: () => void;
}) {
  return (
    <>
      {orbitClass && <span>{orbitClass === 'OTHER' ? 'Other orbit' : orbitClass}</span>}
      <button
        type="button"
        className="icon-button"
        aria-label="Close selected satellite"
        onClick={onClose}
      >
        <CloseIcon />
      </button>
    </>
  );
}

function SelectedBody({
  selectedId,
  detail,
  state,
  now,
  error,
}: Omit<SelectedTileProps, 'onClose'>) {
  if (selectedId === null) {
    return (
      <p className="empty-state">
        Select a satellite on the globe or in search to see its orbit and live position.
      </p>
    );
  }
  if (error) return <p className="status error">Could not load this satellite.</p>;
  if (!detail) return <p className="status">Loading…</p>;
  return <SatelliteSummary detail={detail} state={state} now={now} />;
}

function SatelliteSummary({
  detail,
  state,
  now,
}: {
  detail: SatelliteDetail;
  state: SatelliteState | null;
  now: Date;
}) {
  const { satellite, latest_elements: elements } = detail;
  return (
    <>
      <h3 className="selected-name">{satellite.name}</h3>
      <p className="selected-sub">{subtitle(detail)}</p>
      <div className="hero">
        <HeroValue
          value={state ? formatFixed(state.heightKm, 1) : MISSING}
          label="altitude, km"
          accent
        />
        <HeroValue
          value={state ? formatFixed(state.speedKmPerS, 3) : MISSING}
          label="speed, km/s"
        />
      </div>
      <dl className="facts">
        <Fact label="Latitude" ident>
          {state ? formatDegrees(state.latitudeDeg) : MISSING}
        </Fact>
        <Fact label="Longitude" ident>
          {state ? formatDegrees(state.longitudeDeg) : MISSING}
        </Fact>
        <Fact label="Inclination">
          {elements ? formatDegrees(elements.inclination_deg) : MISSING}
        </Fact>
        <Fact label="Period">{elements ? formatPeriod(elements.period_minutes) : MISSING}</Fact>
        <Fact label="Launched">
          {satellite.launch_date ? (formatCalendarDate(satellite.launch_date) ?? MISSING) : MISSING}
        </Fact>
        <Fact label="Elements">
          {elements ? <Freshness elements={elements} now={now} /> : 'None available'}
        </Fact>
      </dl>
      <MoreDetails detail={detail} />
    </>
  );
}

function subtitle({ satellite }: SatelliteDetail): ReactNode {
  const extras = [
    satellite.country ? ownerName(satellite.country) : null,
    satellite.object_type ? objectTypeLabel(satellite.object_type) : null,
  ].filter((part): part is string => part !== null);
  return (
    <>
      NORAD <span className="ident">{satellite.norad_id}</span>
      {extras.map((part) => `, ${part}`).join('')}
    </>
  );
}

function sentenceStart(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function HeroValue({
  value,
  label,
  accent = false,
}: {
  value: string;
  label: string;
  accent?: boolean;
}) {
  return (
    <div>
      <div className={accent ? 'hero-value accent' : 'hero-value'}>{value}</div>
      <div className="hero-label">{label}</div>
    </div>
  );
}

function Fact({
  label,
  ident = false,
  children,
}: {
  label: string;
  ident?: boolean;
  children: ReactNode;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className={ident ? 'ident' : undefined}>{children}</dd>
    </div>
  );
}

/** Element age as text plus a coloured dot; the text alone carries the meaning. */
function Freshness({ elements, now }: { elements: ElementSet; now: Date }) {
  const ageMs = epochAgeMs(elements.epoch, now);
  const level = epochFreshness(ageMs);
  const age = formatElementAge(ageMs);
  return (
    <span className="freshness" data-level={level}>
      <span className="dot" aria-hidden="true" />
      {level === 'stale' ? `${age}, position may be off` : age}
    </span>
  );
}

function MoreDetails({ detail }: { detail: SatelliteDetail }) {
  const { satellite, latest_elements: elements } = detail;
  const orbitClass = satellite.orbit_class ?? elements?.orbit_class ?? null;
  return (
    <details className="more">
      <summary>More details</summary>
      <dl className="facts">
        <Fact label="International designator" ident>
          {satellite.intl_designator ?? MISSING}
        </Fact>
        <Fact label="Object type">
          {satellite.object_type ? sentenceStart(objectTypeLabel(satellite.object_type)) : MISSING}
        </Fact>
        <Fact label="Orbit class">{orbitClass ?? MISSING}</Fact>
        <Fact label="Element epoch">
          {elements ? formatUtcTimestamp(new Date(elements.epoch)) : MISSING}
        </Fact>
      </dl>
    </details>
  );
}
