# 0005. Tiled, resizable workspace with switchable skins

- **Status:** Proposed
- **Date:** 2026-11-01
- **Deciders:** cosmo030 (owner); drafted by an AI coding agent at the owner's request

## Context

The MVP frontend is a fixed sidebar next to the globe. It reads like a generic dashboard, the
sidebar stacks every control in one scroll column, and users cannot give more room to what they
care about (the globe, the details of a satellite, the search results). The owner's UI spec
(phase 1.1) asks for a tiled instrument panel around the globe, user-resizable and persisted, in
two surface materials: a solid "Instrument" skin and a "Frosted glass" skin.

## Decision

We will lay the frontend out as a full-viewport workspace of tiles (Groups, Search, globe viewport,
Timeline, Selected, Next passes) around an icon dock:

- Tiles are resized with splitters built on **react-resizable-panels** (v4), using pixel-based
  limits; the library also provides pointer, touch and keyboard resizing and collapsible panels.
  We override its keyboard steps (8 px, Shift 32 px) and its double-click (collapse instead of
  reset) to match the spec.
- Sizes and collapsed state are saved in `localStorage` (`sattrack.ui.layout.v1`), validated on
  load, and can be reset from Settings.
- Skins are CSS custom properties keyed on `<html data-skin>`. Components never branch on the
  skin, except the globe placement: in Instrument the Cesium canvas covers the viewport tile; in
  Frosted glass it fills the window behind translucent, blurred tiles, centred on the viewport
  tile by making the canvas just large enough around the tile's centre (no projection changes).
  Frosted glass falls back to Instrument surfaces under `prefers-reduced-transparency` or without
  `backdrop-filter`.
- Text uses self-hosted Tektur and Instrument Sans (OFL), from the Fontsource packages, with
  tabular figures for every live number.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Hand-written CSS grid splitters | No dependency | Pointer capture, touch, keyboard and ARIA to build and test ourselves | The owner chose the library; it covers these cases |
| `dockview` (full docking) | Tabs, drag tiles between columns | Much larger API and bundle | Rearranging tiles is out of scope for this iteration |
| Off-centre Cesium frustum for Frosted | Canvas stays window-sized | Per-frustum near-plane offsets interact with Cesium's multi-frustum rendering | The oversized canvas gives the same result with no projection changes |
| A UI component library | Ready-made controls | Generic look, which this redesign is meant to remove | Not needed for six tiles |

## Consequences

- **Positive:** The globe is the centre of the app; users shape the workspace; a second skin is a
  token set, not a second UI.
- **Negative:** One more runtime dependency; Frosted glass costs GPU time (backdrop blur over a live
  WebGL canvas) and a canvas slightly larger than the window; two font files (about 76 KB) load on
  first visit.
- **Trade-offs found while building it:** Collapse and expand are instant, because animating panel
  sizes with CSS makes the library pin a half-animated pixel size. Frosted glass darkens what shows
  through it (`brightness(0.22)` in the backdrop filter), because the spec's white wash alone gives
  white text about 1:1 contrast over polar ice; with it, muted text stays at 4.7:1 or more.
- **Follow-up:** Tile rearranging (docking) and part 2 of the redesign (globe imagery and world
  design) are separate decisions.

## Security and Data Considerations

Fonts are served from our own origin, so the strict Content-Security-Policy is unchanged and no
third-party requests are made. Layout and skin preferences stay in the browser; no personal data.
