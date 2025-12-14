# Changelog

All notable changes to the rtlamr Multi-Scan Suite are documented in this file.

This project follows a readable changelog style intended to communicate **what changed**, **why it matters**, and **whether behavior changed**, 
without requiring readers to inspect commit history.

---

## [Unreleased]

### Added

* Canonical separation between **frequency selection** and **observation** across all documentation.
* Explicit terminology for **enumerated (ISM-derived)** and **declared (operator-driven)** entry modes.
* Clear scoping language in operator and methodology guides to prevent false workflow necessity.

### Changed

* README.md rewritten for clarity, intent alignment, and accurate mental modeling.
* ARCHITECTURE.md clarified to reflect true system structure and logging behavior.
* QUICKSTART.md reframed as an ISM-derived *example workflow*, not a requirement.
* USAGE.md reorganized to group commands by entry mode instead of implied order.
* OPERATOR_GUIDE.md scoped to describe effective workflows without restricting usage.
* MASTER_OPERATOR_GUIDE.md reframed as a **methodology guide**, not a system definition.
* GLOSSARY.md tightened to reflect current terminology and axis separation.
* DEVS.md refined for precise internal terminology and implementation accuracy.

### Fixed

* Removed lingering documentation assumptions that ISM sweeps are mandatory.
* Corrected outdated implications about core scans being analyzer-only artifacts.
* Eliminated legacy directory and terminology references across docs.

### Removed

* Implicit architectural authority from non-architectural documents.

---

## [0.1.0] — Initial Public Release

### Added

* rtlamr Multi-Scan sweep engine
* Analyzer for core frequency and radio extraction
* Multi-frequency core scan support
* Structured logging under `logs/ism_sweeps/` and `logs/core_scans/`
* Operator-facing documentation set

---

## Notes

Version numbers may be tagged in GitHub Releases. Until then, the **Unreleased** section reflects the current working state of the repository.
