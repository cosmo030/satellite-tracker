# Contributing

Thanks for helping! Bug reports, ideas and pull requests are welcome.

## Workflow

1. Fork the repository and create a branch named `<type>/<short-description>`, for example
   `feat/pass-predictions` or `fix/epoch-timezone`. Types: `feat`, `fix`, `refactor`,
   `docs`, `test`, `chore`, `build`, `ci`, `perf`.
2. Keep each pull request to one logical change. Refactoring, formatting and dependency
   updates go in their own pull requests.
3. Write commit messages in the [Conventional Commits](https://www.conventionalcommits.org/)
   style: `feat(catalog): add launch-year filter`. Use the imperative mood.
4. Run `make check` before you push. It is exactly what CI runs.
5. Open a pull request and fill in the template, including how you verified the change.
   `main` is protected: changes land through pull requests with passing checks.

## Expectations

- New behaviour comes with tests; bug fixes come with a test that fails without the fix.
- API changes: run `make openapi` and update [docs/api.md](docs/api.md).
- Configuration changes: update [.env.example](.env.example) and
  [docs/configuration.md](docs/configuration.md) in the same pull request.
- Significant design decisions get an ADR in [docs/adr/](docs/adr/).
- Never commit secrets, `.env` files or real personal data. Test data is synthetic.
- Respect the [CelesTrak usage policy](https://celestrak.org/usage-policy.php): only the
  ingest worker may call CelesTrak, and tests must not call it at all.

## Where Things Are

- Architecture: [docs/architecture.md](docs/architecture.md)
- Decisions: [docs/adr/](docs/adr/)
- Backend modules: `backend/src/sattrack/<module>/` with `domain.py` (rules), `repository.py`
  (SQL), `service.py` (use cases) and `api.py` (HTTP). Follow `catalog/` as the reference.
- Frontend: `frontend/src/orbit/` (pure orbit maths, tested), `globe/` (CesiumJS),
  `hooks/` (data loading), `components/` (UI).

## Glossary

| Term | Meaning |
|---|---|
| Element set / GP data | Mean orbital elements for SGP4, published by CelesTrak in OMM format |
| Epoch | The time an element set describes; accuracy drops as it ages |
| NORAD ID | Catalog number of a tracked object (6 digits since July 2026) |
| SATCAT | CelesTrak's catalog of object metadata (owner, launch date, type) |
| Ground track | The path of the point directly below the satellite |

Questions? Open an issue.
