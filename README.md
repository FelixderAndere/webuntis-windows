# webuntis-windows

`webuntis-windows` is a Windows application for viewing WebUntis timetables. It provides a shared API layer, a command-line interface, and a graphical interface so you can access the same timetable data in different ways.

## What the project does

The project can:

- log in to a WebUntis account
- load timetables for students, classes, rooms, teachers, or the current user
- cache and sort timetable data for faster display
- show timetable data in either a CLI or a GUI
- package the GUI as a Windows executable

## Content

- [WebuntisAPI.py](WebuntisAPI.py) contains the shared WebUntis logic. It handles login, timetable loading, caching, filtering duplicate lessons, and basic output helpers.
- [WebuntisCLI.py](WebuntisCLI.py) is the terminal-based interface. It asks for credentials, lets you choose a category and identifier, and prints the timetable to the console.
- [WebuntisGUI.py](WebuntisGUI.py) is the graphical interface. It provides a Tkinter window for loading credentials, selecting timetable owners, navigating weeks, and displaying lessons on a visual weekly grid.
- [Example.py](Example.py) is a sample or helper script for trying the API outside of the main interfaces.
- [requirements.txt](requirements.txt) lists the Python dependency needed by the project.

## Requirements

- Python 3
- The dependency from [requirements.txt](requirements.txt) ([python-webuntis](https://github.com/python-webuntis/python-webuntis))

Install the dependency with:

```bash
pip install -r requirements.txt
```

## Usage

It is recommended to create a file called `credentials.json` with your credentials.
You can create it by using `WebuntisGUI.py` and the login dialog or write it like so:
```
{
    "server": "https://XXXXX.webuntis.com",
    "school": "XXXXX",
    "username": "USERNAME",
    "password": "PASSWORD"
}
```
If you save `credentials.json` next to `WebuntisCLI.py`, your credentials stay on your own machine and are only used for logging in to WebUntis.

### CLI

Run the terminal version with:

```bash
python WebuntisCLI.py
```

### GUI

Run the graphical version with:

```bash
python WebuntisGUI.py
```

### Exe

The Windows executable can be downloaded from the newest release in the GitHub Releases section. That release contains the current packaged `.exe` build for the GUI, which is automatically created via GitHub Actions / Workflows.

## Special thanks

This project uses [python-webuntis](https://github.com/python-webuntis/python-webuntis). Thanks to the maintainers for providing the library that makes the WebUntis connection possible.

## ⚠️ Disclaimer
This is an unofficial, independent project and is not affiliated with, endorsed by, or approved by Untis. “Untis” is a trademark of its respective owner and is used here strictly for identification purposes. 

This project has no bad intent of disturbing or harming anyone and does not guarantee for any claims caused by it (see MIT License). Users are responsible for compliance with applicable terms and laws.
The Data it displays is already visible to the logged-in user. It only retrieves timetable information that is in WebUntis and then sorts, groups, and displays that existing data in a more convenient way.
It is a pure hobby / free-time project built mainly for fun and for use in a school context.


