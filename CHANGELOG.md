# Changelog

## [0.2.0] - 2025-06-18

### Added
- Support for scraping multiple Substack URLs in a single run
- `--urls-file` option to load URLs from a file
- Support for piping URLs via stdin
- `--interval` option for continuous monitoring with periodic re-runs
- Example `substacks.txt.example` file
- Comprehensive error handling for individual URL failures in batch mode

### Changed
- Command line argument from single `url` to multiple `urls`
- Enhanced continuous mode to work with multiple URLs
- Improved progress reporting with emoji indicators
- Better structured output for batch operations

### Fixed
- Type annotations updated for better Python version compatibility
- Fixed undefined `self.writer_url` attribute
- Corrected Pydoll API usage with CSS selectors

## [0.1.2] - Previous Release

### Added
- Continuous/incremental fetching mode with `--continuous` flag
- Automatic post numbering based on publication date
- State persistence between runs

### Changed
- Switched from sequential numbering to date-based prefixes (YYYYMMDD)
- Improved async processing architecture

### Fixed
- HTML downloading and MD conversion stuck in "Waiting for page to fully load..." loop
- Various performance improvements
