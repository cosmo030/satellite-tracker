/** Geometry of the timeline track: one UTC day, with the playhead at the current time. */

const MS_PER_DAY = 86_400_000;
export const HOURS_PER_DAY = 24;
/** Every sixth hour gets a taller tick and a label. */
export const MAJOR_TICK_EVERY_HOURS = 6;

/** Fraction (0..1) of the current UTC day that has passed at ``now``. */
export function utcDayFraction(now: Date): number {
  const msIntoDay = ((now.getTime() % MS_PER_DAY) + MS_PER_DAY) % MS_PER_DAY;
  return msIntoDay / MS_PER_DAY;
}

export interface TrackTick {
  hour: number;
  /** Position along the track, 0..1. */
  position: number;
  major: boolean;
}

export function hourTicks(): TrackTick[] {
  return Array.from({ length: HOURS_PER_DAY + 1 }, (_, hour) => ({
    hour,
    position: hour / HOURS_PER_DAY,
    major: hour % MAJOR_TICK_EVERY_HOURS === 0,
  }));
}
