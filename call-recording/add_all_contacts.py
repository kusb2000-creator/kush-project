#!/usr/bin/env python3
"""
Add every phone contact to Google Phone's "Always record -> Selected numbers"
list in one go, by driving the phone over ADB (USB debugging).

Google Phone has no "record all contacts" switch and no API, so this script
does what you would do by hand: tap "Add", search the contact, tap it, repeat.

Usage (phone plugged in, USB debugging on):
    python add_all_contacts.py --limit 2     # try with 2 contacts first
    python add_all_contacts.py               # add everyone
    python add_all_contacts.py --inspect     # print what's on screen (for debugging)

Works on Windows, macOS and Linux with Python 3.8+ and Android platform-tools (adb).
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
DONE_FILE = os.path.join(HERE, "done_contacts.txt")

# Words Google Phone may use for the "add" button on the Selected numbers screen.
ADD_WORDS = re.compile(r"^(add|add number|add contact|add a number|\+)$", re.I)
SEARCH_WORDS = re.compile(r"search", re.I)


# ---------------------------------------------------------------- adb helpers

def find_adb():
    adb = os.environ.get("ADB") or shutil.which("adb")
    if not adb:
        for guess in (os.path.join(HERE, "platform-tools", "adb"),
                      os.path.join(HERE, "platform-tools", "adb.exe")):
            if os.path.exists(guess):
                return guess
        sys.exit("adb not found. Install Android platform-tools and put adb on PATH, "
                 "or unzip platform-tools next to this script.")
    return adb


ADB = None


def adb(*args, check=True):
    out = subprocess.run([ADB, *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if check and out.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def check_device():
    lines = [l for l in adb("devices").splitlines()[1:] if l.strip()]
    if not lines:
        sys.exit("No phone found. Plug it in with USB and turn on USB debugging.")
    if any("unauthorized" in l for l in lines):
        sys.exit("Phone says 'unauthorized'. Unlock it and tap 'Allow' on the USB debugging popup.")
    if len(lines) > 1:
        sys.exit("More than one device connected. Unplug the others.")


# ----------------------------------------------------------------- contacts

ROW_RE = re.compile(r"display_name=(.*?), data1=(.*)$")


def parse_contacts(text):
    """Parse `content query` output into a de-duplicated [(name, number)] list."""
    seen, result = set(), []
    for line in text.splitlines():
        m = ROW_RE.search(line)
        if not m:
            continue
        name, number = m.group(1).strip(), m.group(2).strip()
        if not name or name == "NULL" or name.lower() in seen:
            continue
        seen.add(name.lower())
        result.append((name, number))
    return sorted(result, key=lambda c: c[0].lower())


def read_contacts():
    out = adb("shell", "content", "query",
              "--uri", "content://com.android.contacts/data",
              "--projection", "display_name:data1",
              "--where", "\"mimetype='vnd.android.cursor.item/phone_v2'\"",
              check=False)
    contacts = parse_contacts(out)
    if not contacts:
        sys.exit("Could not read contacts from the phone.\n"
                 "Workaround: make a contacts.txt file with one name per line and run\n"
                 "    python add_all_contacts.py --contacts contacts.txt")
    return contacts


def load_contacts_file(path):
    with open(path, encoding="utf-8") as f:
        names = [l.strip() for l in f if l.strip()]
    return [(n, "") for n in dict.fromkeys(names)]


# --------------------------------------------------------------- screen I/O

class Node:
    def __init__(self, el):
        self.text = (el.get("text") or "").strip()
        self.desc = (el.get("content-desc") or "").strip()
        self.cls = el.get("class") or ""
        self.clickable = el.get("clickable") == "true"
        x1, y1, x2, y2 = map(int, re.findall(r"\d+", el.get("bounds") or "[0,0][0,0]"))
        self.bounds = (x1, y1, x2, y2)
        self.center = ((x1 + x2) // 2, (y1 + y2) // 2)

    def __repr__(self):
        return f"{self.cls.split('.')[-1]:<14} text={self.text!r:<30} desc={self.desc!r:<25} {self.bounds}"


def parse_screen(xml_text):
    start = xml_text.find("<?xml")
    if start == -1:
        start = xml_text.find("<hierarchy")
    root = ET.fromstring(xml_text[start:])
    return [Node(el) for el in root.iter("node")]


def screen(retries=4):
    for _ in range(retries):
        adb("shell", "uiautomator", "dump", "/sdcard/cr_dump.xml", check=False)
        xml_text = adb("exec-out", "cat", "/sdcard/cr_dump.xml", check=False)
        if "<hierarchy" in xml_text:
            return parse_screen(xml_text)
        time.sleep(0.7)
    raise RuntimeError("Could not read the phone screen (uiautomator dump failed).")


def tap(node):
    adb("shell", "input", "tap", str(node.center[0]), str(node.center[1]))


def type_text(s):
    adb("shell", "input", "text", s.replace(" ", "%s"))


def clear_field():
    adb("shell", "input", "keyevent", "KEYCODE_MOVE_END")
    adb("shell", "input", "keyevent", *(["KEYCODE_DEL"] * 40))


def back():
    adb("shell", "input", "keyevent", "KEYCODE_BACK")


def find_add_button(nodes):
    for n in nodes:
        if ADD_WORDS.match(n.text) or ADD_WORDS.match(n.desc):
            return n
    return None


def find_search_field(nodes):
    for n in nodes:
        if n.cls.endswith("EditText"):
            return n
    for n in nodes:
        if SEARCH_WORDS.search(n.desc) or SEARCH_WORDS.search(n.text):
            return n
    return None


def search_query(name, number):
    """Text to type into the picker search. adb can only type plain ASCII."""
    safe = re.sub(r"[^A-Za-z0-9 .\-]", "", name).strip()
    if safe and safe == name:
        return safe
    digits = re.sub(r"\D", "", number)
    return digits[-10:] if digits else safe


def find_result(nodes, name, search_box):
    sb_bottom = search_box.bounds[3] if search_box else 0
    for n in nodes:
        if n.cls.endswith("EditText"):
            continue
        if n.text.lower() == name.lower() and n.bounds[1] >= sb_bottom:
            return n
    return None


# ------------------------------------------------------------------ actions

def add_one(name, number, wait):
    nodes = screen()
    add_btn = find_add_button(nodes)
    if not add_btn:
        return "no 'Add' button on screen - are you on the Selected numbers page?"
    tap(add_btn)
    time.sleep(wait)

    nodes = screen()
    box = find_search_field(nodes)
    if not box:
        back()
        return "no search box in the contact picker"
    tap(box)
    time.sleep(0.4)
    nodes = screen()
    box = find_search_field(nodes) or box
    query = search_query(name, number)
    if not query:
        back()
        return "name has no typeable characters and no number"
    clear_field()
    type_text(query)
    time.sleep(wait)

    nodes = screen()
    hit = find_result(nodes, name, box)
    if not hit:
        back(); time.sleep(0.4)
        if not find_add_button(screen()):
            back()
        return f"contact not found in picker (searched '{query}')"
    tap(hit)
    time.sleep(wait)

    # Some contacts have several numbers: a second picker may appear.
    nodes = screen()
    if not find_add_button(nodes):
        digits = re.sub(r"\D", "", number)[-8:]
        pick = next((n for n in nodes if digits and digits in re.sub(r"\D", "", n.text)), None)
        if pick:
            tap(pick)
            time.sleep(wait)
            nodes = screen()
        if not find_add_button(nodes):
            back(); time.sleep(0.4)
            if not find_add_button(screen()):
                back()
            return "did not return to the list after picking - skipped"
    return None


def load_done():
    if not os.path.exists(DONE_FILE):
        return set()
    with open(DONE_FILE, encoding="utf-8") as f:
        return {l.strip().lower() for l in f if l.strip()}


def mark_done(name):
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(name + "\n")


def main():
    global ADB
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--limit", type=int, help="only add this many contacts (good for a test run)")
    p.add_argument("--contacts", help="text file with one contact name per line instead of reading the phone")
    p.add_argument("--wait", type=float, default=1.2, help="seconds to wait after each tap (raise if phone is slow)")
    p.add_argument("--inspect", action="store_true", help="print what's on the phone screen and exit")
    p.add_argument("--list", action="store_true", help="print the contacts that would be added and exit")
    p.add_argument("--redo", action="store_true", help="ignore done_contacts.txt and try everyone again")
    args = p.parse_args()

    ADB = find_adb()
    check_device()

    if args.inspect:
        for n in screen():
            if n.text or n.desc or n.clickable:
                print(n)
        return

    contacts = load_contacts_file(args.contacts) if args.contacts else read_contacts()
    done = set() if args.redo else load_done()
    todo = [c for c in contacts if c[0].lower() not in done]
    if args.limit:
        todo = todo[:args.limit]

    if args.list:
        for name, number in todo:
            print(f"{name}  {number}")
        print(f"\n{len(todo)} to add ({len(contacts)} contacts total, {len(done)} already done)")
        return

    print(f"{len(contacts)} contacts on phone, {len(done)} already done, {len(todo)} to add now.\n")
    print("On the phone open:  Phone app > Settings > Call recording > Selected numbers")
    print("(turn on 'Always record selected numbers'), keep the screen unlocked,")
    input("then press Enter here to start...")

    if not find_add_button(screen()):
        sys.exit("Can't see an 'Add' button. Open the Selected numbers page and try again,\n"
                 "or run with --inspect and send the output so the script can be adjusted.")

    failed = []
    for i, (name, number) in enumerate(todo, 1):
        err = add_one(name, number, args.wait)
        if err:
            failed.append((name, err))
            print(f"[{i}/{len(todo)}] FAIL  {name}: {err}")
        else:
            mark_done(name)
            print(f"[{i}/{len(todo)}] added {name}")

    print(f"\nDone. Added {len(todo) - len(failed)}, failed {len(failed)}.")
    if failed:
        print("Failed contacts (add these by hand, or run the script again):")
        for name, err in failed:
            print(f"  - {name}: {err}")


if __name__ == "__main__":
    main()
