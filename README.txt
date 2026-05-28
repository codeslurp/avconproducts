Valve Code Selector
===================

A local web app that replaces the Excel "Valve Code Selector Dashboard". Pick
attributes from cascading dropdowns and get back the Bare Valve Code,
Catalogue Code, BTO, FOS, and the full 50-attribute data sheet for that SKU.

How to use
----------
1. Double-click run.bat
2. Your default browser opens automatically to http://127.0.0.1:5037
3. Pick a Series, then Body Material, Ball Material, etc. Each dropdown only
   shows options that lead to a real SKU -- you can't build an invalid combo.
4. The Bare Valve Code, Catalogue Code, BTO, and FOS appear at the top of the
   Result panel. Expand "All attributes" for the full data sheet.
5. To stop the app: close the black command-prompt window.

How to update the catalog
-------------------------
1. Replace the .xlsm file in the data\ folder with the newer version.
   (The app picks the most recently modified .xlsm in that folder, so you can
   leave the old one in place if you want to roll back.)
2. If the app is running, close its command window, then double-click run.bat
   again. The new data is loaded at startup.

Requirements
------------
- Windows 10 or 11
- If a python\ folder is included in this bundle, you don't need anything
  installed. If not, install Python 3.10+ from https://www.python.org/downloads
  (check "Add to PATH" during install) and then run "py -m pip install flask
  openpyxl" from a command prompt before launching.

Troubleshooting
---------------
- "Address already in use": another copy of the app is running. Close that
  command window and try again, or change PORT in app\server.py.
- Browser opens to a "site can't be reached" page: wait ~2 seconds and refresh.
  The server needs a moment to load the ~3,900 row catalog.
- "No .xlsm catalog file found": make sure exactly one Ball Valve Data Sheet
  Structure .xlsm is in the data\ folder.

What's NOT included
-------------------
- Actuator sizing: the actuator columns in the catalog are pre-populated;
  there's no automatic torque-vs-FOS sizing. Users get whatever the catalog row
  contains.
- Print / PDF export: not in this version. Use the browser's "Print" feature
  (Ctrl+P) for a paper data sheet.
