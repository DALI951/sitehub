#!/usr/bin/env python3
"""SiteHub deploy — uploads the web app + api.php to modali.powerpme.com/public_html/sitehub/,
plus site.json description overrides into existing site folders.

Creds: env SITEHUB_SFTP_PASS (fallbacks: DEKKAN_SFTP_PASS -> DUOSCORE_SFTP_PASS, same host/user).
Usage: python scripts/deploy.py [--dry-run]
"""
import os, sys, io, stat, re, json, posixpath
import paramiko

HOST = "modali.powerpme.com"
USER = "modali"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WWW = os.path.join(ROOT, "www")
REMOTE = "/public_html/sitehub"

# site.json overrides for existing folders (nice names + brief explanations)
OVERRIDES = {
    "sitehub": {"name": "SiteHub", "description": "This hub — every deployed site auto-detected in one list.",
                "order": 0},
    "score": {"name": "DuoScore", "description": "Two-player phone scorekeeper — rounds, totals, win target, confetti when someone wins."},
    "dekkan": {"name": "Dekkan", "description": "Arabic small-shop kit — till, stock, debts, day reports, facture printing."},
    "ranimlife": {"name": "RanimLife", "description": "Ranim's person-OS — Quran hifdh, school timetable, focus timer, prayer times, money."},
    "dalideck": {"name": "DaliDeck", "description": "The personal OS dashboard — tasks, notes, money; synced via dalideck-sync."},
    "synchro-diag": {"name": "Synchro Diag", "description": "Adaptive questionnaire for Dad's rental-car company — decides what to build him next."},
    "rabie": {"name": "Rabie Box", "description": "Rabie's no-pressure request box — chips + a message, nothing else."},
    "mc-status": {"name": "MC Status", "description": "Live Minecraft server status — who's online plus join history."},
    "company": {"name": "Company Site", "description": "Trilingual company-site template, dark cinema, FR/EN/AR."},
    "litematic-studio": {"name": "Litematic Studio", "description": "Drop a .litematic file, import the build, place it block by block."},
    "streamhub": {"name": "StreamHub", "description": "Search-and-play streaming hub for topcinema series."},
    "tasktracker": {"name": "Task Tracker (PHP)", "description": "PHP account pages behind the Flutter staff task tracker."},
}

def creds():
    for env in ("SITEHUB_SFTP_PASS", "DEKKAN_SFTP_PASS", "DUOSCORE_SFTP_PASS"):
        p = os.environ.get(env)
        if p:
            return p, env
    return None, None

def walk_files(base):
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".github")]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, base).replace(os.sep, "/")
            out.append((rel, full))
    return out

def main():
    dry = "--dry-run" in sys.argv
    pw, src = creds()
    if not pw:
        print("no credentials: set SITEHUB_SFTP_PASS (or DEKKAN/DUOSCORE_SFTP_PASS) first")
        return 1

    t = paramiko.Transport((HOST, 22))
    t.connect(username=USER, password=pw)
    sftp = paramiko.SFTPClient.from_transport(t)
    print("connected")

    def mkdirs(path):
        parts = path.strip("/").split("/")
        cur = ""
        for p in parts:
            cur += "/" + p
            try:
                sftp.stat(cur)
            except IOError:
                sftp.mkdir(cur)

    def put(base, rel, data=None):
        remote = posixpath.join(REMOTE if base == WWW else '/', rel) if base == WWW else posixpath.join(REMOTE, rel)
        if base != WWW:
            remote = posixpath.join(REMOTE, rel)
        sftp.put(localpath=os.path.join(base, rel), remotepath=remote)
        print("  put", rel)

    mkdirs(REMOTE)
    if not dry:
        # wipe old web assets so stale files never stick
        for item in sftp.listdir(REMOTE):
            sftp.remove(posixpath.join(REMOTE, item))
    files = walk_files(WWW)
    for rel, full in files:
        if dry:
            print("DRY put", rel)
            continue
        parent = posixpath.dirname(posixpath.join(REMOTE, rel))
        mkdirs(parent)
        sftp.put(full, posixpath.join(REMOTE, rel))
        print("  put", rel)

    # api.php
    api_remote = posixpath.join(REMOTE, "api.php")
    if dry:
        print("DRY put api.php")
    else:
        sftp.put(os.path.join(ROOT, "api", "api.php"), api_remote)
        print("  put api.php")

    # site.json overrides into existing folders
    for d, meta in OVERRIDES.items():
        remote = "/public_html/%s/site.json" % d
        data = json.dumps(meta, ensure_ascii=False).encode("utf-8")
        try:
            sftp.stat("/public_html/" + d)
        except IOError:
            print("  skip %s (no folder)" % d)
            continue
        if dry:
            print("DRY site.json", d)
            continue
        with sftp.open(remote, "wb") as f:
            f.write(data)
        print("  site.json", d)

    sftp.close()
    t.close()
    print("done" if not dry else "dry-run (no changes)")
    return 0

if __name__ == "__main__":
    sys.exit(main())