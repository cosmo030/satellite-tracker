/** Messages exchanged between the UI thread and the propagation worker. */
import type { ElementSet } from '../api/client';

/** How often the worker recomputes every position (2 Hz). */
export const PROPAGATION_INTERVAL_MS = 500;

export type ToWorker = { type: 'load'; elements: ElementSet[] } | { type: 'clear' };

export type FromWorker =
  | { type: 'loaded'; noradIds: number[] }
  | {
      type: 'positions';
      timeMs: number;
      /** Packed [lon, lat, heightKm] per satellite, in the order of `noradIds`. */
      positions: Float64Array;
    };
