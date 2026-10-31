# 0003. One ingest service owns all CelesTrak traffic

- **Status:** Proposed
- **Date:** 2026-10-31
- **Deciders:** cosmo030 (owner); drafted by an AI coding agent at the owner's request

## Context

CelesTrak is a free, donation-funded service. Its [usage policy](https://celestrak.org/usage-policy.php)
says GP data updates every 2 hours, asks clients to download each data set only once per
update, and requires them to stop querying on any non-200 response; ignoring errors can get
an IP address firewalled. Since 2026-07-11 new objects have 6-digit catalog numbers that the
legacy TLE format cannot represent, and the default response format changed to CSV on
2026-05-09.

## Decision

We will make the ingest worker the only component that contacts CelesTrak. It:

- requests `FORMAT=JSON` (OMM) explicitly and stores catalog numbers as `BIGINT`;
- fetches each group at most once per 2 hours, and SATCAT metadata once per day, based on
  the last successful request recorded in `fetch_log`;
- stops the whole run on any non-200 response or network error and backs off
  (2 h, 4 h, 8 h, ... up to 24 h);
- identifies itself with a `User-Agent` that links to this repository.

Browsers and the API only ever read from our database.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Browser fetches from CelesTrak directly | No backend | Every visitor hits CelesTrak; violates the policy at any scale | Not acceptable |
| API fetches on demand with a cache | No worker | Request bursts after cache expiry; harder to guarantee "once per update" | A scheduled worker is simpler to reason about |
| TLE format | Widely supported | Cannot represent catalog numbers ≥ 100000 | Obsolete for new objects |

## Consequences

- **Positive:** Upstream traffic is constant and small, and auditable in `fetch_log`.
- **Negative:** Data can be up to 2 hours older than CelesTrak's latest.
- **Follow-up:** Add SatNOGS through the same worker if radio data is added later.

## Security and Data Considerations

Outbound HTTPS to celestrak.org only, with a timeout. Responses are validated before storage.
