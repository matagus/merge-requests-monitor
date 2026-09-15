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


# py2app >= 0.28.9 dropped support for the `install_requires` option, so the runtime
# requirements must already be installed when `python setup.py py2app` runs; the release
# workflow does that from requirements.txt. `rumps` is force-included through
# OPTIONS["packages"] and feedparser is picked up by modulegraph from main.py's imports.
setup(
    app=APP,
    include=["__about__"],
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    name="MergeRequestsMonitor",
    version=__version__,
)
