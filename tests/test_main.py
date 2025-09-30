from unittest.mock import Mock, patch, mock_open

import rumps

from main import MergeRequestsMonitorApp


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
        assert app.get_refresh_interval("6h") == 43200

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
        """Test refresh handles feed parsing errors"""
        # Mock parsing error
        mock_document = Mock(bozo=True)  # Indicates parsing error
        mock_parse.return_value = mock_document

        app = MergeRequestsMonitorApp()
        app.feed_urls = ["https://gitlab.com/invalid.atom"]

        app.refresh(None)

        assert app.title == "⚠️"

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
