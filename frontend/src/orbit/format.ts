/**
 * Display helpers for orbital data. Negative numbers use a true minus sign (U+2212), dates read
 * "14 Jul 2017" and clock times are 24-hour UTC.
 */

const MINUS = '−';
const MS_PER_MINUTE = 60_000;
const MS_PER_HOUR = 3_600_000;
const MS_PER_DAY = 86_400_000;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** Element sets older than this lose accuracy noticeably; the UI warns about them. */
export const STALE_EPOCH_AFTER_MS = 3 * MS_PER_DAY;
/** Element sets younger than this are shown as fresh. */
export const FRESH_EPOCH_UNDER_MS = MS_PER_DAY;

export type Freshness = 'fresh' | 'aging' | 'stale';

export function epochAgeMs(epoch: string, now: Date): number {
  return now.getTime() - new Date(epoch).getTime();
}

export function isEpochStale(epoch: string, now: Date): boolean {
  return epochAgeMs(epoch, now) > STALE_EPOCH_AFTER_MS;
}

export function epochFreshness(ageMs: number): Freshness {
  if (ageMs > STALE_EPOCH_AFTER_MS) return 'stale';
  if (ageMs >= FRESH_EPOCH_UNDER_MS) return 'aging';
  return 'fresh';
}

/** Age of an element set: "35 min old", "7 h old", "4 d old" (or "in 2 h" for future epochs). */
export function formatElementAge(ageMs: number): string {
  const amount = ageAmount(Math.abs(ageMs));
  return ageMs < 0 ? `in ${amount}` : `${amount} old`;
}

function ageAmount(ms: number): string {
  if (ms < MS_PER_HOUR) return `${Math.floor(ms / MS_PER_MINUTE)} min`;
  if (ms < 2 * MS_PER_DAY) return `${Math.floor(ms / MS_PER_HOUR)} h`;
  return `${Math.floor(ms / MS_PER_DAY)} d`;
}

/** A number with fixed decimals and a true minus sign. */
export function formatFixed(value: number, decimals: number): string {
  const text = Math.abs(value).toFixed(decimals);
  return value < 0 && Number(text) !== 0 ? `${MINUS}${text}` : text;
}

/** Degrees with two decimals: "97.50°", "−15.19°". */
export function formatDegrees(degrees: number): string {
  return `${formatFixed(degrees, 2)}°`;
}

export function formatPeriod(minutes: number): string {
  if (minutes < 120) return `${minutes.toFixed(1)} min`;
  return `${(minutes / 60).toFixed(2)} h`;
}

/**
 * Whole numbers with the user's thousands separators ("11,156" in English, "11.156" in German).
 * Digits stay Latin so rolling digits (0–9 strips) always match what is shown.
 */
export function formatCount(value: number, locale?: string): string {
  return value.toLocaleString(locale, { numberingSystem: 'latn', maximumFractionDigits: 0 });
}

/** A calendar date from the catalog ("2017-07-14") as "14 Jul 2017"; null if unreadable. */
export function formatCalendarDate(isoDate: string): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(isoDate);
  if (!match) return null;
  const [, year, month, day] = match;
  const monthName = MONTHS[Number(month) - 1];
  if (monthName === undefined) return null;
  return `${Number(day)} ${monthName} ${year ?? ''}`;
}

/** UTC clock time: "14:51:32". */
export function formatUtcClock(date: Date): string {
  return date.toISOString().slice(11, 19);
}

/** A full UTC timestamp: "1 Nov 2026, 07:12:04 UTC". */
export function formatUtcTimestamp(date: Date): string {
  const day = `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()] ?? ''} ${date.getUTCFullYear()}`;
  return `${day}, ${formatUtcClock(date)} UTC`;
}
