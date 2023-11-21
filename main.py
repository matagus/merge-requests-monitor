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

        config = configparser.ConfigParser()
        config.read("config.ini")
        
        self.feed_url = config["Gitlab"]["feed"]
    
        self.pending_count = 0
        self.last_updated = None

        self.timer = rumps.Timer(self.refresh, 60 * 5)
        self.timer.start()

        self.last_updated_menuitem = rumps.MenuItem("Last updated: Never", key="r")

        self.menu = [
            self.last_updated_menuitem,
            rumps.rumps.SeparatorMenuItem(),
            rumps.MenuItem("No pending MRs"),
            rumps.rumps.SeparatorMenuItem(),
            rumps.MenuItem("Quit", callback=self.quit_application, key="q"),
        ]

        self.entries = []

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


if __name__ == "__main__":
    GitlabNotifierApp().run()
