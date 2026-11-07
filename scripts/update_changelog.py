#!/usr/bin/env python3
"""Prepend out/changes.md to CHANGELOG.md. Usage: update_changelog.py CHANGES.md CHANGELOG.md"""
import datetime, os, sys
chg = open(sys.argv[1], encoding="utf-8").read().strip()
path = sys.argv[2]
old = open(path, encoding="utf-8").read() if os.path.exists(path) else "# Changelog\n"
head, _, rest = old.partition("\n")
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
open(path, "w", encoding="utf-8").write(f"{head}\n\n## {stamp}\n{chg}\n{rest}")
