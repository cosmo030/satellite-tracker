/** Display helpers for orbital data. */

/** Element sets older than this lose accuracy noticeably; the UI warns about them. */
export const STALE_EPOCH_AFTER_MS = 3 * 24 * 60 * 60 * 1000;

export function epochAgeMs(epoch: string, now: Date): number {
  return now.getTime() - new Date(epoch).getTime();
}

export function isEpochStale(epoch: string, now: Date): boolean {
  return epochAgeMs(epoch, now) > STALE_EPOCH_AFTER_MS;
}

export function formatAge(ageMs: number): string {
  const minutes = Math.floor(Math.abs(ageMs) / 60_000);
  const suffix = ageMs < 0 ? 'from now' : 'ago';
  if (minutes < 60) return `${minutes} min ${suffix}`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours} h ${suffix}`;
  return `${Math.floor(hours / 24)} days ${suffix}`;
}

export function formatKm(km: number): string {
  return `${Math.round(km).toLocaleString('en-US')} km`;
}

export function formatSpeed(kmPerS: number): string {
  return `${kmPerS.toFixed(2)} km/s`;
}

export function formatDegrees(degrees: number): string {
  return `${degrees.toFixed(2)}°`;
}

export function formatPeriod(minutes: number): string {
  if (minutes < 120) return `${minutes.toFixed(1)} min`;
  return `${(minutes / 60).toFixed(2)} h`;
}
