# 0004. CesiumWidget with offline imagery

- **Status:** Proposed
- **Date:** 2026-10-31
- **Deciders:** cosmo030 (owner); drafted by an AI coding agent at the owner's request

## Context

CesiumJS's default `Viewer` loads imagery from Cesium ion, which needs an account token, and
its toolbar widgets use Knockout, which evaluates strings as code and so needs
`'unsafe-eval'` in the Content-Security-Policy. We want the project to run for any
contributor without accounts, and we want a strict CSP.

## Decision

We will use `CesiumWidget` (the globe without the Knockout toolbar) and the Natural Earth II
imagery bundled with CesiumJS. Satellites, the selected marker and orbit lines are drawn
with Cesium primitives, not entities. The production CSP allows `'wasm-unsafe-eval'` and
`blob:` workers but not `'unsafe-eval'`.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| `Viewer` with Cesium ion imagery | Higher-resolution imagery, built-in toolbar | Token required; `'unsafe-eval'` in CSP | Accounts and a weaker CSP for an MVP |
| OpenStreetMap tiles | Detailed map | OSM's tile policy discourages heavy app use | Not ours to rely on |

## Consequences

- **Positive:** Works offline and without tokens; strict CSP verified in a browser.
- **Negative:** Low-resolution imagery when zoomed in; no home or scene-mode buttons.
- **Follow-up:** Optional `VITE_CESIUM_ION_TOKEN` for better imagery if users ask for it.

## Security and Data Considerations

No third-party map requests from the browser, so visitors' IP addresses go only to our host.
