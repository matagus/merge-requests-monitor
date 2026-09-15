import os
import sys

from setuptools import setup

from py2app.build_app import py2app as _py2app

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
    # py2app#546: the python.org framework builds ship Tcl/Tk 9.x frameworks that
    # contain the static stub archives lib{tcl,tk}stub.a. py2app copies them into the
    # bundle and then ad-hoc signs it, and codesign rejects a bundle holding an
    # unsigned nested Mach-O ("code object is not signed at all"), which surfaces as
    # RuntimeError: Cannot sign bundle. Neither rumps nor feedparser imports tkinter,
    # so keep it out of the module graph and refuse to bundle the frameworks. The
    # paths are derived from sys.prefix so this is a no-op on a Python without Tk.
    "excludes": ["tkinter"],
    "dylib_excludes": [
        os.path.join(sys.prefix, "Frameworks", "Tcl.framework"),
        os.path.join(sys.prefix, "Frameworks", "Tk.framework"),
    ],
}


# py2app >= 0.28.9 dropped support for the `install_requires` option and raises
# "install_requires is no longer supported" when the distribution has a non-empty one.
# Setuptools copies PEP 621 `[project] dependencies` from pyproject.toml into
# `distribution.install_requires`, so the check fires even though this file never passes
# install_requires. The runtime requirements must already be installed when
# `python setup.py py2app` runs; the release workflow does that from requirements.txt.
# `rumps` is force-included through OPTIONS["packages"] and feedparser is picked up by
# modulegraph from main.py's imports.
class py2app(_py2app):
    def finalize_options(self):
        self.distribution.install_requires = []
        super().finalize_options()


setup(
    app=APP,
    include=["__about__"],
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    cmdclass={"py2app": py2app},
    name="MergeRequestsMonitor",
    version=__version__,
)
