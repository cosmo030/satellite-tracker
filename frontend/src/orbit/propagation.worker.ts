/// <reference lib="webworker" />
/**
 * Propagates every loaded satellite off the UI thread, so the globe stays responsive.
 */
import type { SatRec } from 'satellite.js';

import { createSatrec, propagateAll } from './propagation';
import { PROPAGATION_INTERVAL_MS, type FromWorker, type ToWorker } from './workerProtocol';

declare const self: DedicatedWorkerGlobalScope;

let satrecs: SatRec[] = [];
let timer: ReturnType<typeof setInterval> | undefined;

function post(message: FromWorker, transfer: Transferable[] = []): void {
  self.postMessage(message, transfer);
}

function tick(): void {
  const now = Date.now();
  const positions = propagateAll(satrecs, new Date(now));
  post({ type: 'positions', timeMs: now, positions }, [positions.buffer]);
}

self.onmessage = (event: MessageEvent<ToWorker>) => {
  clearInterval(timer);
  if (event.data.type === 'clear') {
    satrecs = [];
    return;
  }
  const { elements } = event.data;
  satrecs = elements.map(createSatrec);
  post({ type: 'loaded', noradIds: elements.map((e) => e.norad_id) });
  tick();
  timer = setInterval(tick, PROPAGATION_INTERVAL_MS);
};
