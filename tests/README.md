# Tests for Merge Requests Monitor

This directory contains tests for the Merge Requests Monitor application.

## Running Tests

### Run all tests
```bash
hatch run test:test
```

### Run tests with verbose output
```bash
hatch run test:test -v
```

### Run tests with coverage report
```bash
hatch run test:cov
```

This will generate:
- Terminal coverage report showing percentage and missing lines
- HTML coverage report in `htmlcov/` directory (open `htmlcov/index.html` in a browser)

### Run specific test file or test
```bash
# Run a specific test file
hatch run test:test tests/test_main.py

# Run a specific test method
hatch run test:test tests/test_main.py::TestMergeRequestsMonitorApp::test_init
```

## Test Structure

The tests use `pytest` with `unittest.mock` for mocking dependencies. Key testing patterns:

### Mocking feedparser
To test feed parsing without making real HTTP requests:
```python
@patch("main.feedparser.parse")
def test_refresh(mock_parse):
    mock_document = Mock(bozo=False, entries=[...])
    mock_parse.return_value = mock_document
    # ... test code
```

## Current Test Coverage

The test suite provides comprehensive coverage of the `MergeRequestsMonitorApp` class:

### Initialization & Configuration
- ✅ **App initialization** (`test_init`) - Verifies default state setup
- ✅ **Config loading** (`test_init_with_existing_config`) - Tests existing config file handling
- ✅ **Config creation** (`test_get_or_create_config_creates_default`) - Tests default config creation
- ✅ **Config persistence** (`test_save_config`) - Verifies config writing to disk

### Refresh Functionality
- ✅ **Successful refresh** (`test_refresh_successful`) - Tests normal feed fetching
- ✅ **Multiple feeds** (`test_refresh_with_multiple_feeds`) - Tests aggregating multiple GitLab feeds
- ✅ **Parsing errors** (`test_refresh_with_parsing_error`) - Tests error handling with ⚠️ indicator
- ✅ **Timestamp updates** (`test_refresh_updates_timestamp`) - Tests last_updated tracking
- ✅ **MR list clearing** (`test_refresh_clears_previous_merge_requests`) - Tests proper state reset

### Title & Display
- ✅ **Empty state** (`test_update_title_no_merge_requests`) - Tests "0" display
- ✅ **With MRs** (`test_update_title_with_merge_requests`) - Tests count display
- ✅ **Refresh intervals** (`test_get_refresh_interval`) - Tests all time conversions (60s, 5m, 10m, 30m, 1h, 3h, 6h)

### Menu Building
- ✅ **Empty menu** (`test_build_menu_no_merge_requests`) - Tests "No pending MRs" state
- ✅ **With MRs** (`test_build_menu_with_merge_requests`) - Tests MR listing
- ✅ **Draft separation** (`test_build_menu_separates_draft_merge_requests`) - Tests draft/regular MR sections
- ✅ **HTML entities** (`test_build_menu_with_html_entities`) - Tests proper title unescaping
- ✅ **Interval options** (`test_build_menu_includes_refresh_interval_options`) - Tests all refresh options present

### User Interactions
- ✅ **URL opening** (`test_open_url`) - Tests browser opening for MRs
- ✅ **URL with entities** (`test_open_url_with_html_entities`) - Tests URL matching with unescaped titles
- ✅ **Preferences dialog** (`test_set_preferences`) - Tests feed URL configuration
- ✅ **Preferences cancel** (`test_set_preferences_cancel`) - Tests dialog cancellation
- ✅ **Interval changes** (`test_set_refresh_interval`) - Tests changing refresh frequency
- ✅ **About dialog** (`test_about_dialog`) - Tests about screen
- ✅ **Quit action** (`test_quit_application`) - Tests app termination

### Feed Cache & Conditional Requests
The feed cache (`feed_cache.json`, stored next to `config.ini`) keeps GitLab's `ETag`/`Last-Modified` validators and the
last seen entries on disk so unchanged feeds are not re-parsed. Covered by `TestFeedCachePersistence`:

- ✅ **Cache written** (`test_refresh_writes_the_cache_to_disk`) - Tests validators and entries land on disk after a refresh
- ✅ **Restart reuse** (`test_validators_and_entries_are_reused_after_a_restart`) - Tests a fresh app instance reads the cache back
- ✅ **Feed pruning** (`test_removed_feeds_are_pruned_from_the_cache`) - Tests dropped feeds disappear from the cache
- ✅ **Corrupt cache** (`test_truncated_cache_file_is_ignored`) - Tests a truncated JSON file is treated as empty
- ✅ **Newer cache format** (`test_cache_written_by_a_newer_version_is_ignored`) - Tests forward-compatible cache versioning
- ✅ **No rewrite when unchanged** (`test_unchanged_cache_is_not_written_again`) - Tests the disk is left alone when nothing moved

### Feed Failures
A feed that cannot be read is kept separate from the healthy ones, and the menu says so. Covered by
`TestFeedFailures`:

- ✅ **Other feeds survive** (`test_a_broken_feed_does_not_hide_the_other_feeds`) - Tests the good feeds still render next to the ⚠️ badge
- ✅ **Loop continues** (`test_feeds_after_a_broken_one_are_still_fetched`) - Tests a failure does not abort the remaining feeds
- ✅ **Fallback content** (`test_the_broken_feed_keeps_showing_its_last_good_fetch`) - Tests the cached entries stand in for the failed feed
- ✅ **Menu warning** (`test_the_broken_feed_is_named_in_the_menu_without_leaking_its_token`) - Tests "Last updated" points at the failing feed by position, never by its tokenized url
- ✅ **Partial save** (`test_the_good_feeds_are_still_saved_to_the_cache`) - Tests an unreadable body is never written over the last good cache
- ✅ **Warning clears** (`test_the_warning_clears_when_the_feed_recovers`) - Tests a later good refresh resets the state
- ✅ **304 is not a failure** (`test_a_not_modified_feed_is_not_reported_as_broken`) - Tests an unchanged feed reuses its cache instead of being emptied or flagged

### Timer Management
- ✅ **Auto-start** (`test_timer_starts_automatically`) - Tests timer initialization

### Test Statistics
- **Total tests**: 39 (26 for `MergeRequestsMonitorApp`, 6 for feed cache persistence, 7 for feed failures)
- **Methods tested**: 18 of 18 (the uncovered lines are the legacy single-feed `config.ini` fallback, the `OSError`
  best-effort cache-write fallback and the `__main__` entrypoint)
- **Line coverage**: 97% on `main.py`
- **Edge cases covered**: HTML entities, draft MRs, multiple feeds, parsing errors, corrupt and future-dated cache files

## Testing Best Practices

All tests follow these patterns:
- Mock `feedparser.parse` to avoid real HTTP requests
- Use `unittest.mock` for rumps UI components (dialogs, alerts)
- Mock file I/O operations for config testing
- Test both success and error paths
- Verify state changes and side effects
