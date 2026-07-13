# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-07-13

### Fixed
- `pyyaml` was mislabeled as an optional dependency even though `recorder.py` imports it unconditionally, breaking install/test in any environment that only installed the `dev` extra. Moved it to required dependencies.

## [1.0.0] - 2026-07-13

### Added
- Initial stable release. A toolkit for simulating network partitions and failures in distributed systems.
- Test suite covering the package's core behavior.
- Packaging metadata for standalone distribution.
