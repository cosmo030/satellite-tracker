# 0002. Propagate orbits in the browser

- **Status:** Proposed
- **Date:** 2026-10-31
- **Deciders:** cosmo030 (owner); drafted by an AI coding agent at the owner's request

## Context

A satellite's position changes every second, but its orbital elements stay valid for days.
The globe must update smoothly for hundreds or thousands of satellites, and the server should
stay cheap no matter how many people watch.

## Decision

We will ship element sets (a few hundred bytes each) from the API and compute positions in
the browser with satellite.js (SGP4) inside a Web Worker, at 2 Hz. The API never streams
positions. Element responses carry ETags so browsers and caches reuse them between the
2-hourly updates.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Server computes positions, pushed over WebSocket | Thin client | Server CPU and bandwidth grow with every viewer and every second | Does not scale on one small server |
| Server computes, client polls | Simple | Same cost, plus latency | Same reason |
| Propagate on the main thread | Simpler code | Blocks rendering for large groups | The worker costs little and keeps the UI smooth |

## Consequences

- **Positive:** Server load depends on data updates, not viewers; works for large groups.
- **Negative:** Client and server use different SGP4 implementations; results agree to
  well within display precision, but they are two code paths.
- **Follow-up:** For the full catalog (10k+ objects) consider sgp4 in WebAssembly and
  interpolation between ticks (phase 3).

## Security and Data Considerations

None.
