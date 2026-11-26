# Auto-add all contacts to Google Phone call recording (CMF Phone 1)

Google Phone only lets you add contacts to **Always record > Selected numbers**
one at a time. This script does the tapping for you over USB, for every contact.

## One-time setup

1. **On the phone - turn on USB debugging**
   - Settings > About phone > (Software info) > tap **Build number** 7 times.
   - Settings > System > Developer options > turn on **USB debugging**.
2. **On the computer**
   - Install Python 3: https://www.python.org/downloads/ (on Windows tick "Add python.exe to PATH").
   - Download Android **platform-tools**: https://developer.android.com/tools/releases/platform-tools
     and unzip it **into this folder** (so you have `call-recording/platform-tools/adb`).
3. Plug the phone in by USB, unlock it, and tap **Allow** on the "Allow USB debugging?" popup.

## Run it

1. On the phone open **Phone app > Settings > Call recording > Selected numbers**
   and turn on **Always record selected numbers**. Keep the screen on.
2. On the computer:
   - Windows: double-click `run_windows.bat`
   - Mac/Linux: `python3 add_all_contacts.py`
3. Press Enter. Don't touch the phone until it says **Done**.

Try a small test first: `python add_all_contacts.py --limit 2`

Also turn on **Always record > Numbers not in your contacts** so unknown callers are recorded too.

## Good to know

- Re-run any time you add new contacts. Already-added names are remembered in
  `done_contacts.txt` and skipped (`--redo` ignores that file).
- Names in Hindi or with symbols are searched by phone number, since adb can only type English letters.
- Phone slow / taps missed? Add `--wait 2`.
- If it stops with "no 'Add' button" or "no search box", run `python add_all_contacts.py --inspect`
  on that screen and share the output so the script can be matched to your phone's exact screen.
- `--list` shows which contacts it will add without touching anything.
