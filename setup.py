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


# Runtime requirements are declared once, in requirements.txt (the file the release
# workflow installs). py2app itself is a build tool, so it must not end up in the bundle.
def _runtime_requirements():
    with open("requirements.txt") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#") and not line.lower().startswith("py2app")
        ]


REQ_LIST = _runtime_requirements()

setup(
    app=APP,
    include=["__about__"],
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    install_requires=REQ_LIST,
    # Do not add pinned requirements here; edit requirements.txt instead.
    name="MergeRequestsMonitor",
    version=__version__,
)
