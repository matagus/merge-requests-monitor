# Tests for Merge Requests Monitor

`test_main.py` holds the pytest suite for the app in `main.py`. What a test checks is stated by
its name and docstring, and the classes group the behaviours they cover -- so this file does not
re-list them. A hand-written index of test names, counts and percentages goes stale the moment a
test is added; ask pytest instead:

```bash
hatch run test:test --collect-only -q                    # the current list
hatch run test:test --cov=. --cov-report=term-missing    # the current coverage
```

## Running tests

```bash
hatch run test:test        # all tests
hatch run test:test -v     # all tests, verbose
hatch run test:cov         # terminal coverage report + htmlcov/index.html
```

The `test` environment runs on Python 3.11, 3.12, 3.13 and 3.14 through a hatch matrix; select
one with `hatch run test.py3.11:test`. CI runs every version of the matrix.

### Narrowing down

```bash
hatch run test:test tests/test_main.py                       # one file
hatch run test:test tests/test_main.py::TestFeedFailures     # one class
hatch run test:test -k cache                                 # tests matching a substring
```

## Conventions

Nothing in the suite touches the network, the real `Application Support` folder or the menu bar.
Every collaborator of `MergeRequestsMonitorApp` is replaced with a mock from `unittest.mock`:

| Patch target | Why |
|---|---|
| `main.feedparser.parse` | no HTTP request; the returned `Mock` stands for a feed document |
| `main.webbrowser.open_new_tab` | opening a merge request is asserted on, not performed |
| `main.rumps.alert`, `rumps.Window` | the dialogs a user would have to click |
| `main.rumps.quit_application` | so the run does not end mid-suite |
| `main.datetime` | to pin "last updated" timestamps |

```python
@patch("main.feedparser.parse")
def test_refresh(mock_parse):
    mock_parse.return_value = Mock(bozo=False, entries=[...])
    # ...
```

Config and cache files are per test: the autouse `app_support_folder` fixture repoints
`rumps.rumps.application_support` at `tmp_path / APP_NAME`, so `config.ini` and `feed_cache.json`
are read and written inside a temp directory that pytest discards. Where a test only cares about
what was written, `mock_open` stands in for the file.

## Adding tests

Mirror the class you are extending rather than adding an index here, and cover the failure path
next to the success path: the bugs this project has shipped were almost all failure paths -- an
unreadable feed, a half-written config, a link from a feed that is not a URL.
