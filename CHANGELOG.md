# Changelog

## Types of Changes and How to Note Them

* Added - For any new features that have been added since the last version was released
* Changed - To note any changes to the software's existing functionality
* Deprecated - To note any features that were once stable but are no longer and have thus been removed
* Fixed - Any bugs or errors that have been fixed should be so noted
* Removed - This notes any features that have been deleted and removed from the software
* Security - This acts as an invitation to users who want to upgrade and avoid any software vulnerabilities

## \#6 2026-03-10

### Added
* Per-platform release builds: `release.sh` produces separate zips for each platform
  via `VITE_PLATFORM` environment variable (#80)
* Interactive received-file validation script (`validate_received.py`) for post-session
  QA (#80)
* Data extraction for all 7 platforms: LinkedIn (#87), X (#88), Instagram (#85),
  Chrome (#84), Facebook (#83), YouTube (#89), TikTok (#86)
* Eyra logging sync: Python log forwarding to browser console via `LogForwarder`,
  `WindowLogSource`, `CommandSystemLog`; `logLevel` prop on host component (#98)
* Async donations support for Eyra Next platform (`VITE_ASYNC_DONATIONS=true`):
  workflow awaits `DonateSuccess`/`DonateError` reply over MessageChannel;
  Firefox channel-mismatch fix (32fbb3b)
* Git pre-commit protection against accidentally committing DDP/participant data (#90)

### Changed
* Column headers in consent UI are now Dutch throughout, visible to participants
  (#95, #97)
* Script architecture: multi-platform with per-platform filtering via `VITE_PLATFORM`
  (#80)

### Fixed
* Four `return`-in-`finally` block bugs in `extraction_helpers`, `x`, and `whatsapp`
  (#96)
* Zod v4 compatibility for visualization types (#98)

## \#5 2025-09-10

* Switched to pnpm for package management
* Switched to Vite for the frontend build system
* Added Spanish language
* Changed: split script.py into a default basic version in script.py and an advanced version script_custom_ui.py
* Added renovate

## \#4 2025-05-02

* Fixed - Explicit loaded event is sent to ensure proper initialization (channel setup)
* Changed: Feldspar is now split into React component and app
* Changed: Allow multiple block-types to interleave on a submission page
* Added: end to end tests using Playwright

## \#3 2025-04-08

* Changed: layout to support mobile screens (enables mobile friendly data donation) 
* Added: support for mobile variant of a table using cards (used for data donation consent screen)

## \#2 2024-06-13

* Added: Support for progress prompt
* Added: German translations
* Added: Support for assets available in Python

## \#1 2024-03-15

Initial version
