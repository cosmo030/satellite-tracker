# API Reference

Base path: `/api/v1`. All endpoints are public, read-only `GET` requests returning JSON.
Timestamps are ISO 8601 in UTC. The machine-readable spec is [openapi.json](openapi.json)
(a test fails if it drifts from the code; regenerate with `make openapi`). A running API
also serves interactive docs at `/api/docs`.

Errors use FastAPI's format: `{"detail": "..."}` for 404, a list of field errors for 422
(invalid parameters), and `{"detail": "Internal server error", "correlation_id": "..."}` for
500, where the ID matches the server log entry.

## `GET /groups`

Groups that have been ingested, with member counts.

```json
[{ "slug": "stations", "name": "Space stations", "satellite_count": 12 }]
```

## `GET /elements?group={slug}`

Latest element set for every satellite in a group, for SGP4 propagation in the client.

| Parameter | Type | Rules |
|---|---|---|
| `group` | string | Required; `^[a-z0-9-]{1,50}$` |
| `limit` | integer | 1–20000, default 5000 |
| `offset` | integer | ≥ 0, default 0 |

Responses carry `ETag` and `Cache-Control: public, max-age=300`. Send the ETag back in
`If-None-Match` to get `304 Not Modified` when nothing changed. Unknown group: `404`.

```json
[{
  "norad_id": 25544, "object_name": "ISS (ZARYA)", "object_id": "1998-067A",
  "epoch": "2026-10-30T12:00:00Z", "mean_motion": 15.50103472, "eccentricity": 0.0006703,
  "inclination_deg": 51.6416, "raan_deg": 247.4627, "arg_of_pericenter_deg": 130.536,
  "mean_anomaly_deg": 325.0288, "bstar": 0.00034, "mean_motion_dot": 0.0002,
  "mean_motion_ddot": 0.0, "element_set_no": 999, "rev_at_epoch": 48000,
  "classification_type": "U", "ephemeris_type": 0, "period_minutes": 92.897,
  "orbit_class": "LEO"
}]
```

## `GET /satellites`

Search and filter satellites, sorted by name.

| Parameter | Type | Rules |
|---|---|---|
| `q` | string | 1–100 characters; matches the name (case-insensitive) or an exact NORAD ID |
| `group` | string | Group slug |
| `orbit_class` | string | `LEO`, `MEO`, `GEO`, `HEO` or `OTHER` |
| `country` | string | CelesTrak owner code, `^[A-Z0-9/]{1,10}$` (for example `US`, `PRC`, `ESA`) |
| `launch_year` | integer | 1957–2100 |
| `limit` | integer | 1–200, default 50 |
| `offset` | integer | 0–100000, default 0 |

```json
{
  "items": [{
    "norad_id": 25544, "name": "ISS (ZARYA)", "intl_designator": "1998-067A",
    "object_type": "PAY", "country": "ISS", "launch_date": "1998-11-20", "orbit_class": "LEO"
  }],
  "total": 1, "limit": 50, "offset": 0
}
```

## `GET /satellites/{norad_id}`

One satellite with its latest element set (`latest_elements` may be `null`). Unknown ID: `404`.

## `GET /health`

`200` with the freshness of the ingested data, or `503` when the database is unreachable.
`data_state` is `ok`, `stale` (no successful download for more than 6 hours) or `no_data`.

```json
{
  "status": "ok", "data_state": "ok",
  "last_successful_fetch_at": "2026-10-31T10:00:04Z", "data_age_seconds": 1520
}
```

## Orbit classes

Computed from mean motion *n* (revolutions/day) and eccentricity *e*, following the
thresholds Space-Track uses: HEO if *e* ≥ 0.25; LEO if *n* > 11.25; GEO if
0.99 ≤ *n* ≤ 1.01 and *e* < 0.01; MEO if *n* > 1.01; otherwise OTHER.
