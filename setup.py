from setuptools import setup

from __about__ import __version__

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
    "feedparser==6.0.12",
    "py2app>=0.28.6",
    "rumps>=0.4.0",
]

setup(
    app=APP,
    include=["__about__"],
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=REQ_LIST,
    name="MergeRequestsMonitor",
    version=__version__,
)
