import html
import webbrowser
import configparser

from datetime import datetime

import feedparser
import rumps


icon_path = "media/icon.png"


class GitlabNotifierApp(rumps.App):
    def __init__(self):
        super(GitlabNotifierApp, self).__init__(
            name="gitlab_notifier", quit_button=None, icon=icon_path, template=True
        )

        # initialize variables
        self.feed_url = self.get_feed_url() 
        self.refresh_interval_label = "5m"
        self.pending_count = 0
        self.last_updated = None
        self.entries = []
        self.build_menu()
        self.start_timer()

    def build_menu(self):
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
            rumps.MenuItem("About", callback=self.about),
            rumps.MenuItem("Quit", callback=self.quit_application, key="q"),
        ]

    def start_timer(self):
        self.timer = rumps.Timer(
            self.refresh, self.get_refresh_interval(self.refresh_interval_label)
        )
        self.timer.start()

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

    def is_merge_request(self, title):
        if title in ["No pending MRs", "Quit", "About"]:
            return False

        if title.startswith("Refresh Interval")  or title.startswith("Last updated"):
            return False

        return True

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
            
            if self.is_merge_request(key):
                self.menu.pop(key)

        last_separator_key = self.menu.keys()[-2]

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

    @rumps.clicked("About")
    def about(self, _):
        rumps.alert(
            "Gitlab Notifier",
            "A System Tray app that monitors your merge requests and let you access them quickly.\n\n"
            "Version 0.1\n\n"
            "Author: Matias Agustin Mendez <matagus@gmail.com>\n\n"
            "https://github.com/matagus/gitlab-notifier",
            icon_path=icon_path
        )


if __name__ == "__main__":
    GitlabNotifierApp().run()
