from setuptools import setup

APP = ["main.py"]

DATA_FILES = [("media", ["media/icon.png"])]

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "LSUIElement": True,
    },
    "iconfile": "media/icon.png",
    "packages": ["rumps"],
}

REQ_LIST = [
    "feedparser>=6.0.0",
    "py2app>=0.28.0",
    "rumps>=0.4.0",
]

APP_NAME = "Merge Requests Monitor"

VERSION = "0.2.0"

DESCRIPTION = "A System Tray app that monitors your merge requests and let you access them quickly."

ICON_PATH = "media/icon.png"


if __name__ == "__main__":
    setup(
        app=APP,
        data_files=DATA_FILES,
        options={"py2app": OPTIONS},
        setup_requires=REQ_LIST,
        name=APP_NAME,
        version=VERSION,
        description=DESCRIPTION,
    )
