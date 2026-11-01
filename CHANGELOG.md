# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Redesigned the web UI as a tiled instrument panel around the globe (UI redesign, part 1):
  Groups, Search, globe viewport, Timeline, Selected and Next passes tiles with resizable,
  collapsible splitters whose layout is remembered; Instrument and Frosted glass skins in a new
  Settings popover; self-hosted Tektur and Instrument Sans fonts with tabular figures; layouts for
  medium and phone-sized screens. See ADR 0005.
- The globe now shows day/night lighting; only the selected satellite uses the accent colour.
- Selected satellites show the country name instead of the SATCAT owner code.
- Counts use the browser's locale for thousands separators (for example "11.156" in German).

### Added

- Rolling digits: when a count changes (group sizes, the number of groups, search matches, the
  object count on the globe), the UTC clock ticks, or the selected satellite's displayed altitude
  or speed changes, the changed digits roll like an odometer, ones first, up for increases and
  down for decreases. Coordinates and the other details do not roll; reduced-motion settings,
  hidden tabs and collapsed tiles switch instantly.
- `Ctrl K` / `⌘K` focuses search from anywhere.
- Toggles for the orbit path, ground track and day/night lighting on the globe.
- Timeline tile with the UTC clock and the current UTC day (time controls follow in phase 2).

- 3D globe (CesiumJS) with live positions for a satellite group, computed with SGP4 in a
  Web Worker at 2 Hz.
- Search by name or NORAD ID, with filters for orbit class, country, launch year and group.
- Details panel with altitude, speed, position, inclination, period and element age, plus a
  warning for elements older than 3 days.
- Orbit path and ground track for the selected satellite.
- REST API: `/api/v1/groups`, `/elements` (with ETags), `/satellites`, `/satellites/{id}`,
  `/health`.
- Ingest worker for CelesTrak GP (OMM JSON) and SATCAT data that follows the CelesTrak usage
  policy, with a fetch log and back-off on errors.
- Database schema migration `0001` (satellites, element history, groups, fetch log).
- Synthetic demo data loader (`make seed`).
- Docker Compose deployment with Caddy, CI with secret scanning and dependency audits.
