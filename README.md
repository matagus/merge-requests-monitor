# Merge Requests Monitor

A System Tray app for Mac OSX that monitors your open merge requests and let you access them quickly. So far it only supports Gitlab's pull requests.

![Screenshot of the app in the system tray displaying your open merge requests](https://raw.githubusercontent.com/matagus/merge-requests-monitor/main/screenshots/1.png)


## Installation

Download the latest DMG installer file from [Releases section](https://github.com/matagus/merge-requests-monitor/releases) and install it.

**IMPORTANT**: Before running the app, please go to `System Preferences` --> `Privacy & Security` and allow
`"MergeRequestsMonitor"` app to be executed. This is a necessary step since by default MacOS won't allow you to run any
app you download from places other than the App Store.

## Configuration

(TO-DO)

## Build & run

Alternatively, you can locally build the app bundle:

```bash
  pip install -r requirements.txt
  python setup.py py2app
```

And the just run the app:

```bash
  ./dist/main.app/Contents/MacOS/main
```

**TIP**: Move the above `.app` bundle to `/Applications` folder if you want to run it as any other install app.

## Roadmap

- Add support for Github Pull Requests
- Have a new separate menu sections for draft merge request
- Notifications
- Publish it @ the App Store

See [Milestones](https://github.com/matagus/merge-requests-monitor/milestones) for more details about the roadmap.

## Authors.

- [@matagus](https://www.github.com/matagus)


## License

[GPL v3](https://choosealicense.com/licenses/gpl-3.0/)


Acknowledgements
================

 - [Two steps to turn a Python file to a macOS installer](https://gist.github.com/Kvnbbg/84871ae4d642c2dd896e0423471b1b52) helped me quickly understand how to build a DMG using `create-dmg`.
 - [create-dmg](https://github.com/create-dmg/create-dmg): A shell script to build fancy DMGs (macOs app installer)
 - [rumps](https://github.com/jaredks/rumps): Ridiculously uncomplicated macOS Python statusbar apps
 - [py2app](https://github.com/ronaldoussoren/py2app): a Python setuptools command which will allow you to make standalone Mac OS X application bundles.
 - README.md file was generated using [readme.so](https://readme.so/editor)
 - Icon by [Remix Design](https://github.com/Remix-Design/RemixIcon)
