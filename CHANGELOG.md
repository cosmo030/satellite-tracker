# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

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
