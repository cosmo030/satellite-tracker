import type { ElementSet, Satellite, SatelliteDetail } from '../api/client';
import {
  epochAgeMs,
  formatAge,
  formatDegrees,
  formatKm,
  formatPeriod,
  formatSpeed,
  isEpochStale,
} from '../orbit/format';
import type { SatelliteState } from '../orbit/propagation';

type Fact = [label: string, value: string];

interface DetailsPanelProps {
  detail: SatelliteDetail | null;
  state: SatelliteState | null;
  now: Date;
  error: string | null;
  onClose: () => void;
}

const MISSING = '—';

function catalogFacts(satellite: Satellite): Fact[] {
  return [
    ['NORAD ID', String(satellite.norad_id)],
    ['Int. designator', satellite.intl_designator ?? MISSING],
    ['Type', satellite.object_type ?? MISSING],
    ['Country', satellite.country ?? MISSING],
    ['Launched', satellite.launch_date ?? MISSING],
    ['Orbit', satellite.orbit_class ?? MISSING],
  ];
}

function liveFacts(state: SatelliteState | null): Fact[] {
  if (!state) return [];
  return [
    ['Altitude', formatKm(state.heightKm)],
    ['Speed', formatSpeed(state.speedKmPerS)],
    ['Position', `${formatDegrees(state.latitudeDeg)}, ${formatDegrees(state.longitudeDeg)}`],
  ];
}

function elementFacts(elements: ElementSet | null, now: Date): Fact[] {
  if (!elements) return [];
  return [
    ['Inclination', formatDegrees(elements.inclination_deg)],
    ['Period', formatPeriod(elements.period_minutes)],
    ['Element epoch', formatAge(epochAgeMs(elements.epoch, now))],
  ];
}

/** Live position and catalog facts for the selected satellite. */
export function DetailsPanel({ detail, state, now, error, onClose }: DetailsPanelProps) {
  if (error || !detail) {
    return (
      <section className="panel">
        {error ? (
          <p className="error">Could not load this satellite.</p>
        ) : (
          <p className="muted">Loading…</p>
        )}
      </section>
    );
  }
  const { satellite, latest_elements: elements } = detail;
  const facts = [...catalogFacts(satellite), ...liveFacts(state), ...elementFacts(elements, now)];

  return (
    <section className="panel" aria-labelledby="details-heading">
      <div className="panel-header">
        <h2 id="details-heading">{satellite.name}</h2>
        <button type="button" className="link" onClick={onClose} aria-label="Close details">
          ✕
        </button>
      </div>
      {elements && isEpochStale(elements.epoch, now) && (
        <p className="warning">
          These orbital elements are more than 3 days old, so the position may be off.
        </p>
      )}
      {!elements && <p className="warning">No orbital elements available.</p>}
      <dl className="facts">
        {facts.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
