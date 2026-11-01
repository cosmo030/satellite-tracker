# 0006. Use Wikimedia for satellite descriptions and images

- **Status:** Proposed
- **Date:** 2026-11-01
- **Deciders:** cosmo030 (owner); drafted by an AI coding agent at the owner's request

## Context

The Selected tile shows orbital facts but nothing about what an object is or what it is for. The
owner's spec ("Satellite descriptions and images") asks for a short description, one or two
purpose categories, operator and manufacturer, and a freely licensed image, with correct
attribution, and with no hand-written content. Objects nobody has written about (most debris,
rocket bodies and individual constellation members) must keep today's layout exactly.

## Decision

We will take all of this content from Wikimedia, fetched by the backend and served from our API:

- **Sources.** Wikidata (CC0) matches catalog objects by NORAD ID (P377), then COSPAR ID (P247),
  and gives purpose classes (P31 walked up P279), operator (P137), manufacturer (P176),
  constellation membership (P361), an image file (P18) and the English article title. English
  Wikipedia (CC BY-SA 4.0) gives a two-to-three-sentence intro extract. Wikimedia Commons gives
  the image and its author and license. When an object has no article but belongs to a
  constellation that does, the constellation's text is shown under "About the {name}
  constellation", never as if it described the object, and without an image.
- **Server-side fetching and hosting.** A new `enrich` job (`backend/src/sattrack/enrich/`) runs in
  the worker process: once a day for new and refresh-due objects, a full refresh every 7 days
  (`SATTRACK_ENRICH_INTERVAL_HOURS`). It stores text in `satellite_about` and two JPEG/PNG
  thumbnails (480 and 960 px) in `satellite_image`. The API serves both (`/satellites/{id}/about`,
  `/satellites/{id}/image`); the browser never contacts a Wikimedia domain.
- **Etiquette.** Every request carries a User-Agent with the project URL and an operator contact
  (`SATTRACK_ENRICH_CONTACT`, required). Requests run one at a time, at least 250 ms apart per
  host; 429 honours `Retry-After` (capped at 120 s, three retries); any 5xx, network error or
  unexpected body stops the run. Work is saved in chunks of 200 objects, each in one transaction,
  so a failed run never overwrites good data. Ingest and enrich share a PostgreSQL advisory lock
  and never write at the same time.
- **Licenses.** Only Commons files whose license is public domain, CC0, CC BY or CC BY-SA (any
  version) and not flagged non-free are stored. Every image shows "{author}, {license}" linking to
  the file page; every description shows "From Wikipedia, CC BY-SA 4.0" (or "From Wikidata").
  No Wikipedia text or Commons file is committed to the repository; tests use synthetic fixtures.
- **Fallback.** `has_about` on the detail response tells the browser whether to ask at all. Without
  data, the tile renders exactly as before; a failed `/about` request behaves the same way.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| NASA Image and Video Library | Public-domain images, simple API | NASA missions only; no descriptions, operators or categories; matching by free-text search | Covers a small part of the catalog and cannot be matched reliably |
| UCS Satellite Database | Curated purpose, operator and contractor fields | Spreadsheet updated irregularly; active satellites only; no text or images; reuse terms unclear | Would still need a second source for text and images |
| Load Wikimedia content in the browser | No storage, no job | Every visitor's IP and selections reach Wikimedia; depends on their uptime and rate limits; needs CSP exceptions | Privacy and stability; the spec forbids it |
| Hand-written descriptions | Exactly the wording we want | Thousands of objects to write and maintain | Out of scope (non-goal) |

## Consequences

- **Positive:** Well-known objects (ISS, Hubble, Tianhe, navigation and weather satellites) gain
  text, purpose chips and a photo. Everything is served from our origin with long-lived ETag
  caching, so the strict Content-Security-Policy is unchanged.
- **Negative:** The database grows by the stored images: about 260 KB per object with an image
  (the first live run stored 109 images, 28 MB, for the six default groups plus Starlink). Coverage
  is only as good as Wikidata: of about 11,000 Starlink satellites, only six direct-to-cell
  satellites have Wikidata items; the rest show no About block.
- **Trade-offs found while building it:** Commons now returns thumbnails from
  `thumb.wikimedia.org` with tracking parameters; downloads are allowed from it and
  `upload.wikimedia.org` only, with the query string removed. The class-to-category lookup runs
  per chunk (cached for the run) rather than once per run, to keep each chunk self-contained.
  A matched object that yields no usable text, category, operator or image is stored as
  `no_match`, so the API's `has_about` stays meaningful.
- **Follow-up:** A name-based constellation fallback (for example `STARLINK-*` to the Starlink
  article) would need its own matching rules and is a separate decision.

## Security and Data Considerations

Threat model: the job sends only public catalog identifiers to Wikimedia, never visitor data.
Content from Wikimedia is untrusted. Text is stored as plain text (HTML in author and description
fields is stripped with a parser) and rendered by React as text, never as HTML. Image downloads
are restricted to HTTPS on the two Wikimedia image hosts, must start with JPEG or PNG magic bytes,
and are limited to 5 MB; SVG and other formats are rejected. The contact setting is validated as
an email address or HTTPS URL, which prevents header injection. `SATTRACK_ENRICH_ENABLED=false`
turns off all Wikimedia traffic.
