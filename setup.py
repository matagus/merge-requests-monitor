from setuptools import setup

APP = ["main.py"]

DATA_FILES = [("media", ["media/icon.png"]), ("", ["config.ini"])]

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

setup(app=APP, data_files=DATA_FILES, options={"py2app": OPTIONS}, setup_requires=REQ_LIST, name="MergeRequestsMonitor")
