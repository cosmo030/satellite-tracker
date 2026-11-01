# Security Policy

## Reporting a Vulnerability

Please do not open a public issue for security problems. Use GitHub's
[private vulnerability reporting](https://github.com/cosmo030/satellite-tracker/security/advisories/new)
instead. Include steps to reproduce and the affected version or commit. You should get a
first response within 7 days.

## Scope

The application stores only public orbital data and has no user accounts. Relevant reports
include injection, cross-site scripting, ways to make the server send excessive traffic to
CelesTrak, denial of service against the API, and exposure of configuration or credentials.

## Supported Versions

Only the latest release on `main` receives fixes.
