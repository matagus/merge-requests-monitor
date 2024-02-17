import configparser
import html
import webbrowser

from datetime import datetime

import feedparser
import rumps

from __about__ import __version__

APP_NAME = "Merge Requests Monitor"
VERSION = __version__
DESCRIPTION = "A System Tray app that monitors your merge requests and let you access them quickly."
ICON_PATH = "media/icon.png"
DEFAULT_REFRESH_INTERVAL = "5m"
DEFAULT_FEED_URL = "https://gitlab.com/<username>/<repo>/-/merge_requests.atom?feed_token=<token>&state=opened"


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
        self.merge_requests = []

        config = self.get_or_create_config()
        self.refresh_interval_label = config["refresh_interval"]
        self.feed_url = config["feed"]

        # make this app do what it must do!
        self.build_menu()
        self.update_title()
        self.start_timer()

    def update_title(self):
        self.title = f"{len(self.merge_requests)}"

    def build_menu(self):
        self.menu.clear()

        self.menu.add(rumps.MenuItem(f"Last updated: {self.last_updated}"))

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
            for merge_request in self.merge_requests:
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
                "feed": self.feed_url,
                "refresh_interval": self.refresh_interval_label,
            }
            config.write(f)

    def get_or_create_config(self):
        def _get_config():
            with self.open("config.ini") as f:
                config.read_file(f)
                return config["Gitlab"]

        config = configparser.ConfigParser()

        try:
            return _get_config()

        except FileNotFoundError:
            with self.open("config.ini", "w") as f:
                config["Gitlab"] = {
                    "feed": DEFAULT_FEED_URL,
                    "refresh_interval": DEFAULT_REFRESH_INTERVAL,
                }
                config.write(f)

            return _get_config()

    def get_refresh_interval(self, label):
        return {
            "60s": 60,
            "5m": 60 * 5,
            "10m": 60 * 10,
            "30m": 60 * 30,
            "1h": 60 * 60,
            "12h": 60 * 60 * 12,
        }[label]

    def refresh(self, sender):
        # retrieve the feed entries
        try:
            document = feedparser.parse(self.feed_url)
        except Exception:
            return

        self.merge_requests = document.entries
        self.last_updated = datetime.now().strftime("%H:%M")

        # rebuild the menu
        self.build_menu()
        self.update_title()

    @rumps.clicked("Preferences")
    def set_preferences(self, sender):
        response = rumps.Window(
            title="Set Preferences",
            message="Enter your Gitlab's merge requests feed URL:",
            default_text=self.feed_url,
            ok="Save",
            cancel="Cancel",
        ).run()

        if response.clicked:
            self.feed_url = response.text
            self.save_config()

    @rumps.clicked("Quit")
    def quit_application(self, sender=None):
        self.timer.stop()
        rumps.quit_application(sender)

    def open_url(self, sender):
        for merge_req in self.merge_requests:
            if merge_req.title == html.escape(sender.title):
                webbrowser.open_new_tab(merge_req.link)

    def set_refresh_interval(self, sender):
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
