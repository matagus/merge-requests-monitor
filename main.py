import html
import webbrowser
import configparser

from datetime import datetime

import feedparser
import rumps


class GitlabNotifierApp(rumps.App):
    def __init__(self):
        super(GitlabNotifierApp, self).__init__(
            name="gitlab_notifier", quit_button=None, icon="media/icon.png", template=True
        )

        self.feed_url = self.get_feed_url()
    
        self.refresh_interval_label = "5m"
        self.pending_count = 0
        self.last_updated = None

        self.timer = rumps.Timer(
            self.refresh, self.get_refresh_interval(self.refresh_interval_label)
        )
        self.timer.start()

        self.last_updated_menuitem = rumps.MenuItem("Last updated: Never", key="r")

        self.menu = [
            self.last_updated_menuitem,
            (rumps.MenuItem(
                f"Refresh Interval: {self.refresh_interval_label}",
                callback=self.set_refresh_interval), 
                [
                    rumps.MenuItem("60s", callback=self.set_refresh_interval),
                    rumps.MenuItem("5m", callback=self.set_refresh_interval),
                    rumps.MenuItem("10m", callback=self.set_refresh_interval),
                    rumps.MenuItem("30m", callback=self.set_refresh_interval),
                    rumps.MenuItem("1h", callback=self.set_refresh_interval),
                    rumps.MenuItem("12h", callback=self.set_refresh_interval),
                ]
            ),
            rumps.rumps.SeparatorMenuItem(),
            rumps.MenuItem("No pending MRs"),
            rumps.rumps.SeparatorMenuItem(),
            rumps.MenuItem("Quit", callback=self.quit_application, key="q"),
        ]

        self.entries = []

    def get_feed_url(self):
        config = configparser.ConfigParser()
        config.read("config.ini") 
        return config["Gitlab"]["feed"]

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
        try:
            document = feedparser.parse(self.feed_url)
        except Exception as e:
            print(e)
            return

        self.entries = document.entries
        self.pending_count = len(document.entries)
        self.last_updated = datetime.now().strftime("%H:%M")

        # Remove menu items for MRs
        menu_item_list = self.menu.values().copy()

        for menuitem in menu_item_list:
            try:
                key = menuitem.title
            except AttributeError:
                continue

            if key.startswith("No pending MRs") or key.startswith("Last updated") or key.startswith("Quit"):
                continue

            if key.startswith("Refresh Interval"):
                continue

            self.menu.pop(key)

        last_separator_key = self.menu.keys()[-1]

        for entry in self.entries:
            title = html.unescape(entry.title)
            self.menu.insert_before(
                last_separator_key,
                rumps.MenuItem(title, callback=self.open_url),
            )

        if self.pending_count == 0:
            self.title = "0"
            self.menu["No pending MRs"].hidden = False
        else:
            self.menu.insert_before(
                last_separator_key,
                rumps.rumps.SeparatorMenuItem(),
            )
            self.title = f"{self.pending_count}"
            self.menu["No pending MRs"].hidden = True

        self.last_updated_menuitem.title = f"Last updated: {self.last_updated}"
            
    @rumps.clicked("Quit")
    def quit_application(self, sender=None):
        self.timer.stop()
        rumps.quit_application(sender)

    def open_url(self, sender):
        for entry in self.entries:
            if entry.title == html.escape(sender.title):
                webbrowser.open_new_tab(entry.link)

    def set_refresh_interval(self, sender):
        refresh_interval_menu = self.menu["Refresh Interval: 5m"]

        self.refresh_interval = self.get_refresh_interval(sender.title)
        self.timer.stop()
        self.timer.interval = self.refresh_interval
        self.timer.start()

        self.refresh_interval_label = sender.title
        refresh_interval_menu.title = f"Refresh Interval: {self.refresh_interval_label}"


if __name__ == "__main__":
    GitlabNotifierApp().run()
