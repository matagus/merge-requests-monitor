import configparser
import html
import json
import os
import webbrowser

from datetime import datetime
from types import SimpleNamespace

import feedparser
import rumps

from __about__ import __version__

APP_NAME = "Merge Requests Monitor"
VERSION = __version__
DESCRIPTION = "A System Tray app that monitors your merge requests and let you access them quickly."
ICON_PATH = "media/icon.png"
DEFAULT_REFRESH_INTERVAL = "5m"
DEFAULT_FEED_URL = "https://gitlab.com/<username>/<repo>/-/merge_requests.atom?feed_token=<token>&state=opened"
FEED_CACHE_FILE = "feed_cache.json"
FEED_CACHE_VERSION = 1


class MergeRequestsMonitorApp(rumps.App):
    def __init__(self):
        super().__init__(
            name=APP_NAME,
            title="0",
            quit_button=None,
            icon=ICON_PATH,
            template=True,
        )

        # initialize default variables & loan config values
        self.last_updated = "Never"
        # feed urls that could not be read during the last refresh
        self.failed_feeds = []
        self.merge_requests = []
        # conditional GET validators (ETag / Last-Modified) plus the entries they were fetched
        # with, per feed url. Kept on disk so a restart or a crash does not turn into a full
        # re-download of every feed.
        self.feed_cache = self.load_feed_cache()
        self.saved_feed_cache = None

        config = self.get_or_create_config()
        self.refresh_interval_label = self.read_refresh_interval(config)
        self.feed_urls = self.read_feed_urls(config)

        # make this app do what it must do!
        self.build_menu()
        self.update_title()
        self.start_timer()

    def update_title(self):
        if self.failed_feeds:
            # the badge warns that what the menu shows is not the whole story; the count of the
            # feeds we could read is in the menu itself
            self.title = "⚠️"
            return
        self.title = f"{len(self.merge_requests)}"

    def last_updated_label(self):
        """The "Last updated" entry, warning about the feeds that could not be read.

        A failed feed keeps showing the merge requests of its last good fetch, which is worth
        saying out loud. Failed feeds are named by their position in the configuration and not
        by their url, which carries a secret feed token.
        """
        label = f"Last updated: {self.last_updated}"
        numbers = [
            str(number) for number, feed_url in enumerate(self.feed_urls, start=1) if feed_url in self.failed_feeds
        ]
        if not numbers:
            return label
        word = "feeds" if len(numbers) > 1 else "feed"
        return f"{label} · ⚠️ {word} {', '.join(numbers)} failed (showing last known MRs)"

    def build_menu(self):
        self.menu.clear()

        self.menu.add(rumps.MenuItem(self.last_updated_label()))

        refresh_menu = rumps.MenuItem(
            f"Refresh Interval: {self.refresh_interval_label}",
            callback=self.set_refresh_interval,
        )
        for freq in ["60s", "5m", "10m", "30m", "1h", "3h", "6h"]:
            refresh_menu.add(rumps.MenuItem(freq, callback=self.set_refresh_interval))

        self.menu.add(refresh_menu)
        self.menu.add(rumps.rumps.SeparatorMenuItem())

        if len(self.merge_requests) == 0:
            self.menu.add(rumps.MenuItem("No pending MRs"))
        else:
            draft_merge_requests = [mr for mr in self.merge_requests if "Draft: " in mr.title]
            merge_requests = [mr for mr in self.merge_requests if "Draft: " not in mr.title]

            if len(merge_requests) > 0:
                # This acts as section title
                self.menu.add(rumps.MenuItem("Merge Requests"))

                for merge_request in merge_requests:
                    title = html.unescape(merge_request.title)
                    self.menu.add(rumps.MenuItem(title, callback=self.open_url))

            if len(merge_requests) > 0 and len(draft_merge_requests) > 0:
                self.menu.add(rumps.rumps.SeparatorMenuItem())

            if len(draft_merge_requests) > 0:
                # This acts as section title
                self.menu.add(rumps.MenuItem("Draft Merge Requests"))

                for merge_request in draft_merge_requests:
                    title = html.unescape(merge_request.title)
                    self.menu.add(rumps.MenuItem(title, callback=self.open_url))

        self.menu.add(rumps.rumps.SeparatorMenuItem())
        self.menu.add(rumps.MenuItem("Preferences", callback=self.set_preferences))
        self.menu.add(rumps.MenuItem("About", callback=self.about))
        self.menu.add(rumps.MenuItem("Quit", key="q", callback=self.quit_application))

    def start_timer(self):
        freq_interval = self.get_refresh_interval(self.refresh_interval_label)

        self.timer = rumps.Timer(self.refresh, freq_interval)
        self.timer.start()

    def save_config(self):
        with self.open("config.ini", "w") as f:
            config = configparser.ConfigParser()
            config["Gitlab"] = {
                "feeds": ",".join(self.feed_urls),
                "refresh_interval": self.refresh_interval_label,
            }
            config.write(f)

    def default_config(self):
        """The section a config file is rewritten from when it cannot be used as it stands."""
        return {
            "feeds": f"{DEFAULT_FEED_URL}\n",
            "refresh_interval": DEFAULT_REFRESH_INTERVAL,
        }

    def get_or_create_config(self):
        """The `[Gitlab]` section, writing the defaults over a config file that cannot be used.

        A file that is absent and a file that is there but unusable are the same problem for
        the person using the app: neither has a `[Gitlab]` section to start on. Only the first
        one raised FileNotFoundError, so the second (an empty file, or one holding a different
        section) let `config["Gitlab"]` raise a KeyError the except clause never caught, and
        the app died before the menu existed. With no menu there is no Preferences dialog to
        correct the file in, and the file itself sits under ~/Library/Application Support/.

        An unusable file is replaced by the defaults rather than worked around, which is what
        makes the "or create" in the name true for both cases: whatever comes back can be read,
        and the Preferences dialog is there to put the real feed urls into it.
        """

        def _get_config():
            with self.open("config.ini") as f:
                config.read_file(f)
                return config["Gitlab"]

        config = configparser.ConfigParser()

        try:
            return _get_config()

        except (FileNotFoundError, KeyError):
            with self.open("config.ini", "w") as f:
                config["Gitlab"] = self.default_config()
                config.write(f)

            return _get_config()

    def read_feed_urls(self, config):
        """The feed urls the app should poll, whatever shape the config file is in.

        A comma separated list under "feeds" is what the current versions write, a single url
        under "feed" is what the single-feed versions wrote. A hand edited file, or one left
        half written by a crash, can hold neither key, and that is no reason to refuse to
        start: fall back to the default feed rather than letting the KeyError escape.

        Blank entries are dropped, so a "feeds" with nothing in it counts as the missing key
        it is and gets the same fallback instead of a url that can never be fetched.
        """
        configured = config.get("feeds", fallback="") or config.get("feed", fallback="")
        urls = [url.strip() for url in configured.split(",") if url.strip()]
        return urls or [DEFAULT_FEED_URL]

    def read_refresh_interval(self, config):
        """The refresh interval the app starts on, whatever shape the config file is in.

        Same shape as #198, one line above the feeds: indexing the section directly meant a
        `[Gitlab]` without a `refresh_interval` key, written by an older version or edited by
        hand, raised an uncaught KeyError out of __init__, which is the crash that leaves no
        menu behind. A missing key is no reason to refuse to start, so fall back to the
        default; a blank value counts as the missing key it stands for, as it does in
        read_feed_urls().

        Only the presence of the key is handled here. A value that is not one of the menu
        labels is a bad value rather than a missing key, and stays the separate issue it is.
        """
        label = config.get("refresh_interval", fallback="").strip()
        return label or DEFAULT_REFRESH_INTERVAL

    def get_refresh_interval(self, label):
        return {
            "60s": 60,
            "5m": 60 * 5,
            "10m": 60 * 10,
            "30m": 60 * 30,
            "1h": 60 * 60,
            "3h": 60 * 60 * 3,
            "6h": 60 * 60 * 6,
        }[label]

    def feed_cache_path(self, filename=FEED_CACHE_FILE):
        """Absolute path of a file inside this app's Application Support folder."""
        return os.path.join(self._application_support, filename)

    def feed_cache_payload(self):
        """JSON serializable view of the cache, pruned to the feeds currently configured."""
        return {
            "version": FEED_CACHE_VERSION,
            "feeds": {
                feed_url: {
                    "etag": cached["etag"],
                    "modified": cached["modified"],
                    "entries": [{"title": entry.title, "link": entry.link} for entry in cached["entries"]],
                }
                for feed_url, cached in self.feed_cache.items()
                if feed_url in self.feed_urls
            },
        }

    def save_feed_cache(self):
        """Write the cache through a temporary file so a crash can never half-overwrite it."""
        try:
            payload = json.dumps(self.feed_cache_payload(), sort_keys=True)
            if payload == self.saved_feed_cache:
                return  # nothing changed since the last write, leave the disk alone
            temp_path = self.feed_cache_path(f"{FEED_CACHE_FILE}.tmp")
            with open(temp_path, "w") as f:
                f.write(payload)
            os.replace(temp_path, self.feed_cache_path())
        except OSError:
            return  # caching is best effort, the next refresh just downloads the feeds again
        self.saved_feed_cache = payload

    def load_feed_cache(self):
        """Read the cache back, ignoring anything we cannot make sense of."""
        try:
            with open(self.feed_cache_path()) as f:
                stored = json.load(f)
            if stored.get("version") != FEED_CACHE_VERSION:
                return {}
            return {
                feed_url: {
                    "etag": cached.get("etag"),
                    "modified": cached.get("modified"),
                    "entries": [
                        SimpleNamespace(title=entry.get("title") or "", link=entry.get("link") or "")
                        for entry in cached.get("entries") or []
                    ],
                }
                for feed_url, cached in (stored.get("feeds") or {}).items()
            }
        except (OSError, ValueError, AttributeError):
            return {}

    def refresh(self, sender):
        self.merge_requests = []
        self.failed_feeds = []
        for feed_url in self.feed_urls:
            cached = self.feed_cache.setdefault(feed_url, {"etag": None, "modified": None, "entries": []})
            document = feedparser.parse(feed_url, etag=cached["etag"], modified=cached["modified"])

            # gitlab rotates the validators, so take the fresh ones even on a 304. Only accept
            # strings: feedparser gives us the raw header value, anything else is unusable here.
            for header in ("etag", "modified"):
                value = document.get(header)
                if isinstance(value, str):
                    cached[header] = value

            # The server honoured If-None-Match / If-Modified-Since. A 304 carries no body, so
            # `entries` comes back empty and this branch has to run before the entries are
            # refreshed below, or an unchanged feed would overwrite its own cache with nothing.
            # (Checked against feedparser 6.0.14: a 304 leaves `bozo` false, so its position
            # relative to the failure handling underneath does not matter.)
            if document.get("status") == 304:
                self.merge_requests.extend(cached["entries"])
                continue

            if document.bozo:
                # A broken feed must not take the rest of the app down with it: keep the entries
                # of the last good fetch, flag this feed in the menu and carry on with the feeds
                # after it.
                self.failed_feeds.append(feed_url)
                self.merge_requests.extend(cached["entries"])
                continue

            # keep only the fields the menu needs, so the cache stays plain serializable data
            cached["entries"] = [
                SimpleNamespace(
                    title=str(getattr(entry, "title", "") or ""), link=str(getattr(entry, "link", "") or "")
                )
                for entry in document.entries
            ]
            self.merge_requests.extend(cached["entries"])

        self.last_updated = datetime.now().strftime("%H:%M")
        self.build_menu()
        self.update_title()
        self.save_feed_cache()

    @rumps.clicked("Preferences")
    def set_preferences(self, sender):
        response = rumps.Window(
            title="Set Preferences",
            message="Enter your Gitlab's merge requests feed URLs (comma-separated):",
            default_text=",".join(self.feed_urls),
            ok="Save",
            cancel="Cancel",
        ).run()

        if response.clicked:
            self.feed_urls = [url.strip() for url in response.text.split(",")]
            self.save_config()
            self.refresh(None)

    @rumps.clicked("Quit")
    def quit_application(self, sender=None):
        self.timer.stop()
        rumps.quit_application(sender)

    def open_url(self, sender):
        for merge_req in self.merge_requests:
            if html.unescape(merge_req.title) == sender.title:
                webbrowser.open_new_tab(merge_req.link)

    def set_refresh_interval(self, sender):
        sender.state = 1  # set the selected item as checked
        refresh_interval_menu = self.menu.values()[0]

        self.refresh_interval = self.get_refresh_interval(sender.title)
        self.timer.stop()
        self.timer.interval = self.refresh_interval
        self.timer.start()

        self.refresh_interval_label = sender.title
        refresh_interval_menu.title = f"Refresh Interval: {self.refresh_interval_label}"
        self.save_config()

    @rumps.clicked("About")
    def about(self, _):
        rumps.alert(
            f"{APP_NAME}\n",
            f"{DESCRIPTION}\n\n"
            f"Version {VERSION}\n\n"
            "Author: Matias Agustin Mendez <matagus@gmail.com>\n\n"
            "https://github.com/matagus/merge-requests-monitor",
            icon_path=ICON_PATH,
        )


if __name__ == "__main__":
    MergeRequestsMonitorApp().run()
