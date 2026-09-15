import json
from types import SimpleNamespace
from unittest.mock import Mock, patch, mock_open

import pytest
import rumps

from main import APP_NAME, DEFAULT_FEED_URL, FEED_CACHE_FILE, MergeRequestsMonitorApp


@pytest.fixture(autouse=True)
def app_support_folder(tmp_path, monkeypatch):
    """Keep the app's files inside a temp folder instead of the real Application Support one."""
    folder = tmp_path / APP_NAME
    folder.mkdir()
    monkeypatch.setattr(rumps.rumps, "application_support", lambda name: str(folder))
    return folder


class TestMergeRequestsMonitorApp:
    """Test suite for MergeRequestsMonitorApp"""

    def test_init(self):
        """Test app initialization with default config"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()

        assert app.name == "Merge Requests Monitor"
        assert app.title == "0"
        assert app.last_updated == "Never"
        assert app.merge_requests == []
        assert isinstance(app.timer, rumps.Timer)

    def test_init_with_existing_config(self):
        """Test app initialization with existing config file"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()

        # Config should be loaded with defaults or existing values
        assert app.refresh_interval_label in ["60s", "5m", "10m", "30m", "1h", "3h", "6h"]
        assert isinstance(app.feed_urls, list)
        assert len(app.feed_urls) > 0

    def test_get_refresh_interval(self):
        """Test refresh interval conversion from labels to seconds"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()

        assert app.get_refresh_interval("60s") == 60
        assert app.get_refresh_interval("5m") == 300
        assert app.get_refresh_interval("10m") == 600
        assert app.get_refresh_interval("30m") == 1800
        assert app.get_refresh_interval("1h") == 3600
        assert app.get_refresh_interval("3h") == 10800
        assert app.get_refresh_interval("6h") == 21600

    def test_update_title_no_merge_requests(self):
        """Test title shows 0 when no merge requests"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()
        app.merge_requests = []

        app.update_title()

        assert app.title == "0"

    def test_update_title_with_merge_requests(self):
        """Test title shows count of merge requests"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()
        app.merge_requests = [Mock(), Mock(), Mock()]

        app.update_title()

        assert app.title == "3"

    @patch("main.feedparser.parse")
    def test_refresh_successful(self, mock_parse):
        """Test successful feed refresh"""
        # Mock feed entries
        entry1 = Mock(title="Fix bug #123", link="https://gitlab.com/mr/1")
        entry2 = Mock(title="Draft: New feature", link="https://gitlab.com/mr/2")
        mock_document = Mock(bozo=False, entries=[entry1, entry2])
        mock_parse.return_value = mock_document

        app = MergeRequestsMonitorApp()
        app.feed_urls = ["https://gitlab.com/feed1.atom"]

        # Trigger refresh
        app.refresh(None)

        assert len(app.merge_requests) == 2
        assert app.title == "2"
        assert app.last_updated != "Never"

    @patch("main.feedparser.parse")
    def test_refresh_with_multiple_feeds(self, mock_parse):
        """Test refresh with multiple feed URLs"""
        # Mock entries from different feeds
        entry1 = Mock(title="MR from feed 1", link="https://gitlab.com/mr/1")
        entry2 = Mock(title="MR from feed 2", link="https://gitlab.com/mr/2")
        entry3 = Mock(title="MR from feed 2 again", link="https://gitlab.com/mr/3")

        mock_doc1 = Mock(bozo=False, entries=[entry1])
        mock_doc2 = Mock(bozo=False, entries=[entry2, entry3])
        mock_parse.side_effect = [mock_doc1, mock_doc2]

        app = MergeRequestsMonitorApp()
        app.feed_urls = ["https://gitlab.com/feed1.atom", "https://gitlab.com/feed2.atom"]

        app.refresh(None)

        assert len(app.merge_requests) == 3
        assert mock_parse.call_count == 2

    @patch("main.feedparser.parse")
    def test_refresh_with_parsing_error(self, mock_parse):
        """A broken feed warns in the badge but still leaves the menu and timestamp usable"""
        # Mock parsing error
        mock_document = Mock(bozo=True)  # Indicates parsing error
        mock_parse.return_value = mock_document

        app = MergeRequestsMonitorApp()
        app.feed_urls = ["https://gitlab.com/invalid.atom"]

        app.refresh(None)

        assert app.title == "⚠️"
        assert app.failed_feeds == ["https://gitlab.com/invalid.atom"]
        assert app.last_updated != "Never"
        menu_titles = [item.title for item in app.menu.values() if hasattr(item, "title")]
        assert "No pending MRs" in menu_titles
        assert any("⚠️ feed 1 failed" in title for title in menu_titles)

    @patch("main.feedparser.parse")
    def test_refresh_updates_timestamp(self, mock_parse):
        """Test refresh updates last_updated timestamp"""
        mock_document = Mock(bozo=False, entries=[])
        mock_parse.return_value = mock_document

        app = MergeRequestsMonitorApp()

        # Mock datetime to control timestamp
        with patch("main.datetime") as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.return_value = "14:30"
            mock_datetime.now.return_value = mock_now

            app.refresh(None)

            assert app.last_updated == "14:30"
            mock_now.strftime.assert_called_once_with("%H:%M")

    def test_build_menu_no_merge_requests(self):
        """Test menu building with no merge requests"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()
        app.merge_requests = []

        app.build_menu()

        menu_titles = [item.title for item in app.menu.values() if hasattr(item, "title")]
        assert "No pending MRs" in menu_titles
        assert "Quit" in menu_titles

    def test_build_menu_with_merge_requests(self):
        """Test menu building with merge requests"""
        entry1 = Mock(title="Fix authentication bug", link="https://gitlab.com/mr/1")
        entry2 = Mock(title="Add new API endpoint", link="https://gitlab.com/mr/2")
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()
        app.merge_requests = [entry1, entry2]

        app.build_menu()

        menu_titles = [item.title for item in app.menu.values() if hasattr(item, "title")]
        assert "Fix authentication bug" in menu_titles
        assert "Add new API endpoint" in menu_titles

    def test_build_menu_separates_draft_merge_requests(self):
        """Test menu separates draft MRs from regular MRs"""
        entry1 = Mock(title="Fix bug", link="https://gitlab.com/mr/1")
        entry2 = Mock(title="Draft: New feature", link="https://gitlab.com/mr/2")
        entry3 = Mock(title="Draft: Experimental change", link="https://gitlab.com/mr/3")
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()
        app.merge_requests = [entry1, entry2, entry3]

        app.build_menu()

        menu_titles = [item.title for item in app.menu.values() if hasattr(item, "title")]
        assert "Merge Requests" in menu_titles
        assert "Draft Merge Requests" in menu_titles
        assert "Fix bug" in menu_titles
        assert "Draft: New feature" in menu_titles

    def test_build_menu_with_html_entities(self):
        """Test menu correctly unescapes HTML entities in MR titles"""
        entry = Mock(title="Fix &quot;bug&quot; &amp; improve", link="https://gitlab.com/mr/1")
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()
        app.merge_requests = [entry]

        app.build_menu()

        menu_titles = [item.title for item in app.menu.values() if hasattr(item, "title")]
        assert 'Fix "bug" & improve' in menu_titles

    def test_build_menu_includes_refresh_interval_options(self):
        """Test menu includes all refresh interval options"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()

        app.build_menu()

        # Find the refresh interval menu item
        refresh_menu = None
        for item in app.menu.values():
            if hasattr(item, "title") and "Refresh Interval" in item.title:
                refresh_menu = item
                break

        assert refresh_menu is not None
        submenu_titles = [item.title for item in refresh_menu.values() if hasattr(item, "title")]
        expected_intervals = ["60s", "5m", "10m", "30m", "1h", "3h", "6h"]
        for interval in expected_intervals:
            assert interval in submenu_titles

    def test_save_config(self):
        """Test saving configuration to file"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()
        app.feed_urls = ["https://gitlab.com/feed1.atom", "https://gitlab.com/feed2.atom"]
        app.refresh_interval_label = "10m"

        # Mock the file operations
        m = mock_open()
        with patch.object(app, "open", m):
            app.save_config()

        # Verify file was opened for writing
        m.assert_called_once_with("config.ini", "w")

        # Verify ConfigParser.write was called
        handle = m()
        assert handle.write.called

    def test_get_or_create_config_existing_file(self):
        """Test loading existing config file"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()

        # Config should be loaded successfully
        assert isinstance(app.feed_urls, list)
        assert isinstance(app.refresh_interval_label, str)

    def test_get_or_create_config_creates_default(self):
        """Test creating default config when file doesn't exist"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()

        # Config should be loaded (either default or existing)
        assert app.refresh_interval_label in ["60s", "5m", "10m", "30m", "1h", "3h", "6h"]
        assert len(app.feed_urls) > 0

    @patch("main.webbrowser.open_new_tab")
    def test_open_url(self, mock_browser):
        """Test opening MR URL in browser"""
        entry1 = Mock(title="Fix bug", link="https://gitlab.com/mr/1")
        entry2 = Mock(title="Add feature", link="https://gitlab.com/mr/2")
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()
        app.merge_requests = [entry1, entry2]

        # Create a mock menu item
        sender = Mock()
        sender.title = "Fix bug"

        app.open_url(sender)

        mock_browser.assert_called_once_with("https://gitlab.com/mr/1")

    @patch("main.webbrowser.open_new_tab")
    def test_open_url_with_html_entities(self, mock_browser):
        """Test opening MR URL with HTML entities in title"""
        entry = Mock(title="Fix &quot;bug&quot;", link="https://gitlab.com/mr/1")
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()
        app.merge_requests = [entry]

        sender = Mock()
        sender.title = 'Fix "bug"'  # Unescaped version

        app.open_url(sender)

        mock_browser.assert_called_once_with("https://gitlab.com/mr/1")

    def test_set_refresh_interval(self):
        """Test changing refresh interval"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()
        initial_interval = app.refresh_interval_label

        # Mock sender (menu item)
        sender = Mock()
        sender.title = "10m"
        sender.state = 0

        # Mock menu structure - need to replace the method itself
        refresh_menu_item = Mock()
        refresh_menu_item.title = f"Refresh Interval: {initial_interval}"
        app.menu.values = Mock(return_value=[refresh_menu_item])

        app.set_refresh_interval(sender)

        assert sender.state == 1  # Checkbox state
        assert app.refresh_interval_label == "10m"
        assert app.refresh_interval == 600  # 10 minutes in seconds

    def test_set_preferences(self):
        """Test setting preferences via dialog"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()

        # Mock the preferences dialog
        with patch("rumps.Window") as mock_window:
            mock_response = Mock()
            mock_response.clicked = True
            mock_response.text = "https://gitlab.com/feed1.atom, https://gitlab.com/feed2.atom"
            mock_window.return_value.run.return_value = mock_response

            app.set_preferences(None)

            assert app.feed_urls == ["https://gitlab.com/feed1.atom", "https://gitlab.com/feed2.atom"]

    def test_set_preferences_cancel(self):
        """Test canceling preferences dialog"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()
        original_feeds = app.feed_urls.copy()

        # Mock the preferences dialog with cancel
        with patch("rumps.Window") as mock_window:
            mock_response = Mock()
            mock_response.clicked = False
            mock_window.return_value.run.return_value = mock_response

            with patch.object(app, "save_config") as mock_save:
                app.set_preferences(None)

            # Config should not be saved
            mock_save.assert_not_called()
            assert app.feed_urls == original_feeds

    @patch("main.rumps.quit_application")
    def test_quit_application(self, mock_quit):
        """Test quitting the application"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()

        app.quit_application(None)

        mock_quit.assert_called_once_with(None)

    @patch("main.rumps.alert")
    def test_about_dialog(self, mock_alert):
        """Test about dialog"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()

        app.about(None)

        mock_alert.assert_called_once()
        call_args = mock_alert.call_args[0]
        assert "Merge Requests Monitor" in call_args[0]
        assert "Version" in call_args[1]

    def test_timer_starts_automatically(self):
        """Test timer starts automatically on initialization"""
        with patch("main.feedparser.parse", return_value=Mock(bozo=False, entries=[])):
            app = MergeRequestsMonitorApp()

        assert hasattr(app, "timer")
        assert isinstance(app.timer, rumps.Timer)
        # Timer interval should match the configured refresh interval
        expected_interval = app.get_refresh_interval(app.refresh_interval_label)
        assert app.timer.interval == expected_interval

    @patch("main.feedparser.parse")
    def test_refresh_clears_previous_merge_requests(self, mock_parse):
        """Test refresh clears previous MRs before fetching new ones"""
        # First call returns 2 entries
        entry1 = Mock(title="MR 1", link="https://gitlab.com/mr/1")
        entry2 = Mock(title="MR 2", link="https://gitlab.com/mr/2")
        mock_doc1 = Mock(bozo=False, entries=[entry1, entry2])
        # Second call returns only 1 entry
        entry3 = Mock(title="MR 3", link="https://gitlab.com/mr/3")
        mock_doc2 = Mock(bozo=False, entries=[entry3])

        mock_parse.side_effect = [mock_doc1, mock_doc2]

        app = MergeRequestsMonitorApp()
        app.feed_urls = ["https://gitlab.com/feed.atom"]

        # First refresh
        app.refresh(None)
        assert len(app.merge_requests) == 2

        # Second refresh should clear and reload
        app.refresh(None)
        assert len(app.merge_requests) == 1
        assert app.merge_requests[0].title == "MR 3"


class TestFeedCachePersistence:
    """The conditional GET cache has to survive restarts and crashes."""

    FEED_URL = "https://gitlab.com/feed1.atom"

    def _cached(self, etag='"etag-v1"', modified=None):
        """In memory form: entries are objects the menu can read attributes off."""
        return {
            "etag": etag,
            "modified": modified,
            "entries": [SimpleNamespace(title="MR 1", link="https://gitlab.com/mr/1")],
        }

    def _stored(self, etag='"etag-v1"', modified=None):
        """On disk form: entries are plain JSON objects."""
        return {
            "etag": etag,
            "modified": modified,
            "entries": [{"title": "MR 1", "link": "https://gitlab.com/mr/1"}],
        }

    def _document(self, status=200, etag=None, entries=()):
        document = Mock(bozo=False, entries=list(entries))
        headers = {"status": status}
        if etag is not None:
            headers["etag"] = etag
        document.get.side_effect = lambda key, default=None: headers.get(key, default)
        return document

    def test_refresh_writes_the_cache_to_disk(self, app_support_folder):
        app = MergeRequestsMonitorApp()
        app.feed_urls = [self.FEED_URL]

        entries = [Mock(title="MR 1", link="https://gitlab.com/mr/1")]
        with patch("main.feedparser.parse", return_value=self._document(etag='"etag-v1"', entries=entries)):
            app.refresh(None)

        stored = json.loads((app_support_folder / FEED_CACHE_FILE).read_text())
        assert stored["version"] == 1
        assert stored["feeds"][self.FEED_URL]["etag"] == '"etag-v1"'
        assert stored["feeds"][self.FEED_URL]["entries"] == [{"title": "MR 1", "link": "https://gitlab.com/mr/1"}]

    def test_validators_and_entries_are_reused_after_a_restart(self, app_support_folder):
        (app_support_folder / FEED_CACHE_FILE).write_text(
            json.dumps({"version": 1, "feeds": {self.FEED_URL: self._stored(modified="Mon, 01 Jan 2024 00:00:00 GMT")}})
        )

        app = MergeRequestsMonitorApp()
        app.feed_urls = [self.FEED_URL]
        assert app.feed_cache[self.FEED_URL]["etag"] == '"etag-v1"'

        document = self._document(status=304, etag='"etag-v2"')
        with patch("main.feedparser.parse", return_value=document) as mock_parse:
            app.refresh(None)

        # the persisted validators went out as conditional GET headers...
        mock_parse.assert_called_once_with(self.FEED_URL, etag='"etag-v1"', modified="Mon, 01 Jan 2024 00:00:00 GMT")
        # ...and the 304 kept the cached merge requests instead of emptying the menu
        assert [mr.title for mr in app.merge_requests] == ["MR 1"]
        assert app.title == "1"
        # a rotated ETag is persisted as well
        assert (
            json.loads((app_support_folder / FEED_CACHE_FILE).read_text())["feeds"][self.FEED_URL]["etag"]
            == '"etag-v2"'
        )

    def test_removed_feeds_are_pruned_from_the_cache(self, app_support_folder):
        app = MergeRequestsMonitorApp()
        app.feed_urls = ["https://gitlab.com/kept.atom"]
        app.feed_cache = {
            "https://gitlab.com/kept.atom": self._cached(),
            "https://gitlab.com/gone.atom": self._cached(),
        }

        app.save_feed_cache()

        assert set(json.loads((app_support_folder / FEED_CACHE_FILE).read_text())["feeds"]) == {
            "https://gitlab.com/kept.atom"
        }

    def test_truncated_cache_file_is_ignored(self, app_support_folder):
        (app_support_folder / FEED_CACHE_FILE).write_text('{"version": 1, "feeds": {"https://gitlab.com')

        assert MergeRequestsMonitorApp().feed_cache == {}

    def test_cache_written_by_a_newer_version_is_ignored(self, app_support_folder):
        (app_support_folder / FEED_CACHE_FILE).write_text(
            json.dumps({"version": 999, "feeds": {self.FEED_URL: self._stored()}})
        )

        assert MergeRequestsMonitorApp().feed_cache == {}

    def test_unchanged_cache_is_not_written_again(self, app_support_folder):
        app = MergeRequestsMonitorApp()
        app.feed_urls = [self.FEED_URL]
        app.feed_cache = {self.FEED_URL: self._cached()}
        app.save_feed_cache()

        # nothing changed, so the next save must leave the file alone
        (app_support_folder / FEED_CACHE_FILE).write_text("sentinel")
        app.save_feed_cache()

        assert (app_support_folder / FEED_CACHE_FILE).read_text() == "sentinel"


class TestFeedFailures:
    """One unreadable feed must not blank out the good ones or leave the UI stale (issue #197)."""

    BROKEN = "https://gitlab.com/broken.atom?feed_token=secret"
    WORKING = "https://gitlab.com/working.atom?feed_token=secret"

    def _entries(self, *titles):
        return [SimpleNamespace(title=title, link=f"https://gitlab.com/mr/{title}") for title in titles]

    def _cached(self, *titles):
        return {"etag": None, "modified": None, "entries": self._entries(*titles)}

    def _document(self, *titles, bozo=False, status=200):
        document = Mock(bozo=bozo, entries=self._entries(*titles))
        headers = {"status": status}
        document.get.side_effect = lambda key, default=None: headers.get(key, default)
        return document

    def _parse(self, documents):
        """Answer each configured feed url with the document that was set up for it."""
        return Mock(side_effect=lambda url, **_: documents[url])

    def test_a_broken_feed_does_not_hide_the_other_feeds(self):
        app = MergeRequestsMonitorApp()
        app.feed_urls = [self.WORKING, self.BROKEN]
        app.feed_cache = {self.BROKEN: self._cached("Old MR")}
        documents = {
            self.WORKING: self._document("New MR"),
            self.BROKEN: self._document(bozo=True),
        }

        with patch("main.feedparser.parse", self._parse(documents)):
            app.refresh(None)

        # the working feed renders, the broken one falls back to what it last fetched
        assert [mr.title for mr in app.merge_requests] == ["New MR", "Old MR"]
        assert app.title == "⚠️"
        assert app.failed_feeds == [self.BROKEN]

    def test_feeds_after_a_broken_one_are_still_fetched(self):
        app = MergeRequestsMonitorApp()
        app.feed_urls = [self.BROKEN, self.WORKING]
        documents = {
            self.BROKEN: self._document(bozo=True),
            self.WORKING: self._document("New MR"),
        }

        with patch("main.feedparser.parse", self._parse(documents)) as mock_parse:
            app.refresh(None)

        assert mock_parse.call_count == 2
        assert [mr.title for mr in app.merge_requests] == ["New MR"]

    def test_the_broken_feed_is_named_in_the_menu_without_leaking_its_token(self):
        app = MergeRequestsMonitorApp()
        app.feed_urls = [self.WORKING, self.BROKEN]
        documents = {
            self.WORKING: self._document("New MR"),
            self.BROKEN: self._document(bozo=True),
        }

        with patch("main.feedparser.parse", self._parse(documents)):
            app.refresh(None)
            app.build_menu()

        last_updated = app.menu.values()[0].title
        # position, not url: a feed url carries the user's private feed token
        assert "⚠️ feed 2 failed" in last_updated
        assert "secret" not in last_updated

    def test_the_good_feeds_are_still_saved_to_the_cache(self, app_support_folder):
        app = MergeRequestsMonitorApp()
        app.feed_urls = [self.WORKING, self.BROKEN]
        app.feed_cache = {self.BROKEN: self._cached("Old MR")}
        documents = {
            self.WORKING: self._document("New MR"),
            self.BROKEN: self._document(bozo=True),
        }

        with patch("main.feedparser.parse", self._parse(documents)):
            app.refresh(None)

        stored = json.loads((app_support_folder / FEED_CACHE_FILE).read_text())
        assert stored["feeds"][self.WORKING]["entries"] == [{"title": "New MR", "link": "https://gitlab.com/mr/New MR"}]
        # the broken feed keeps what it had before, the unparsable body is never stored
        assert stored["feeds"][self.BROKEN]["entries"] == [{"title": "Old MR", "link": "https://gitlab.com/mr/Old MR"}]

    def test_the_warning_clears_when_the_feed_recovers(self):
        app = MergeRequestsMonitorApp()
        app.feed_urls = [self.BROKEN]
        broken = self._document(bozo=True)
        documents = {self.BROKEN: broken}

        with patch("main.feedparser.parse", self._parse(documents)):
            app.refresh(None)

        assert app.failed_feeds == [self.BROKEN]

        documents[self.BROKEN] = self._document("New MR")
        with patch("main.feedparser.parse", self._parse(documents)):
            app.refresh(None)

        assert app.failed_feeds == []
        assert app.title == "1"

    def test_the_broken_feed_keeps_showing_its_last_good_fetch(self):
        app = MergeRequestsMonitorApp()
        app.feed_urls = [self.BROKEN]
        app.feed_cache = {self.BROKEN: self._cached("Old MR")}
        documents = {self.BROKEN: self._document(bozo=True)}

        with patch("main.feedparser.parse", self._parse(documents)):
            app.refresh(None)

        assert [mr.title for mr in app.merge_requests] == ["Old MR"]
        assert app.failed_feeds == [self.BROKEN]

    def test_a_not_modified_feed_is_not_reported_as_broken(self):
        """A 304 sends no body, so its cache has to stand in without the feed looking broken"""
        app = MergeRequestsMonitorApp()
        app.feed_urls = [self.WORKING]
        app.feed_cache = {self.WORKING: self._cached("Cached MR")}
        documents = {self.WORKING: self._document(bozo=True, status=304)}

        with patch("main.feedparser.parse", self._parse(documents)):
            app.refresh(None)

        assert app.failed_feeds == []
        assert app.title == "1"
        assert [mr.title for mr in app.merge_requests] == ["Cached MR"]


class TestConfigFeedUrls:
    """A config.ini we cannot fully read is no reason to refuse to start (issue #198)."""

    FEED_A = "https://gitlab.com/a.atom"
    FEED_B = "https://gitlab.com/b.atom"

    def _start(self, app_support_folder, feed_keys):
        """Start the app against a config.ini whose [Gitlab] section holds `feed_keys`."""
        (app_support_folder / "config.ini").write_text(f"[Gitlab]\nrefresh_interval = 5m\n{feed_keys}")
        return MergeRequestsMonitorApp()

    def test_the_configured_feeds_are_read(self, app_support_folder):
        app = self._start(app_support_folder, f"feeds = {self.FEED_A},{self.FEED_B}\n")

        assert app.feed_urls == [self.FEED_A, self.FEED_B]

    def test_the_legacy_single_feed_is_still_read(self, app_support_folder):
        """The versions before multi-feed wrote one url under the singular key."""
        app = self._start(app_support_folder, f"feed = {self.FEED_A}\n")

        assert app.feed_urls == [self.FEED_A]

    def test_a_config_without_either_feed_key_starts_on_the_default(self, app_support_folder):
        """The crash this guards against: neither key raised an uncaught KeyError."""
        app = self._start(app_support_folder, "")

        assert app.feed_urls == [DEFAULT_FEED_URL]

    def test_blank_feed_entries_fall_back_to_the_default(self, app_support_folder):
        """A feeds key holding nothing usable stands in for the key being absent."""
        app = self._start(app_support_folder, "feeds = , ,\n")

        assert app.feed_urls == [DEFAULT_FEED_URL]

    def test_feed_entries_are_trimmed_and_empties_dropped(self, app_support_folder):
        app = self._start(app_support_folder, f"feeds = {self.FEED_A} , ,{self.FEED_B} ,\n")

        assert app.feed_urls == [self.FEED_A, self.FEED_B]
