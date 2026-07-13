# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-13

### Added
- Initial stable release. Request tracing and observability for distributed systems.
- Test suite covering the package's core behavior.
- Packaging metadata for standalone distribution.

### Fixed
- Test suite failed to collect (`ModuleNotFoundError: tracing`) because nothing put `src` on `sys.path`; added `tests/conftest.py`.
