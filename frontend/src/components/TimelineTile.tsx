import type { Ref } from 'react';

import { formatUtcClock } from '../orbit/format';
import { hourTicks, utcDayFraction } from '../ui/timeline';
import { PlayIcon } from './icons';
import { RollingNumber } from './RollingNumber';
import { Tile } from './Tile';

const TICKS = hourTicks();
// Time controls (play, speed, scrubbing) arrive with phase 2; until then the tile shows live time.
const NOT_YET = 'Time controls arrive in a later update';
const MS_PER_SECOND = 1000;

/**
 * The clock rolls its changed digits each second (owner decision, beyond UI spec 6.1, which
 * keeps the clock still). It counts whole seconds since the epoch, so it always rolls up.
 */
function clockText(epochSeconds: number): string {
  return formatUtcClock(new Date(epochSeconds * MS_PER_SECOND));
}

interface TimelineTileProps {
  now: Date;
  /** Receives the Live chip so the dock can move focus to the timeline. */
  liveRef?: Ref<HTMLButtonElement>;
}

/** UTC clock, live state and a track of the current UTC day with the playhead at now. */
export function TimelineTile({ now, liveRef }: TimelineTileProps) {
  const playhead = utcDayFraction(now);
  return (
    <Tile id="timeline" title="Timeline" hideHeader className="timeline-tile">
      <div className="timeline-controls">
        <button type="button" className="icon-button" disabled aria-label="Play" title={NOT_YET}>
          <PlayIcon />
        </button>
        <button
          ref={liveRef}
          type="button"
          className="chip live-chip"
          aria-pressed="true"
          title="Showing the current time"
        >
          <span className="dot" aria-hidden="true" />
          Live
        </button>
        <time className="clock" dateTime={now.toISOString()}>
          <RollingNumber value={Math.floor(now.getTime() / MS_PER_SECOND)} format={clockText} />
          <span className="unit">UTC</span>
        </time>
        <button
          type="button"
          className="chip speed"
          disabled
          title={NOT_YET}
          aria-label="Playback speed 1×"
        >
          1×
        </button>
      </div>
      <div className="track" aria-hidden="true">
        {TICKS.map((tick) => (
          <span
            key={tick.hour}
            className={tick.major ? 'tick major' : 'tick'}
            style={{ left: `${tick.position * 100}%` }}
          />
        ))}
        {TICKS.filter((tick) => tick.major && tick.hour < 24).map((tick) => (
          <span
            key={`label-${tick.hour}`}
            className="tick-label"
            style={{ left: `${tick.position * 100}%` }}
          >
            {String(tick.hour).padStart(2, '0')}
          </span>
        ))}
        <span className="playhead" style={{ left: `${playhead * 100}%` }} />
      </div>
    </Tile>
  );
}
