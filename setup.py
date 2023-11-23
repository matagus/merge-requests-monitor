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

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
