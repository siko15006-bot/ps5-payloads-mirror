#!/usr/bin/env python3
"""Refuse to publish a broken catalog. Usage: validate_catalog.py NEW.json [PREVIOUS.json]"""
import json, re, sys

new = json.load(open(sys.argv[1], encoding="utf-8"))["payloads"]
errs, names = [], set()
for p in new:
    n = p.get("name", "?")
    if n in names: errs.append(f"duplicate name {n}")
    names.add(n)
    for k in ("name", "filename", "url", "version", "checksum"):
        if not p.get(k): errs.append(f"{n}: missing {k}")
    if p.get("checksum") and not re.fullmatch(r"[0-9a-f]{64}", p["checksum"]): errs.append(f"{n}: bad checksum")
    if p.get("url") and not p["url"].startswith("https://"): errs.append(f"{n}: url not https")
if len(sys.argv) > 2:
    try:
        old = json.load(open(sys.argv[2], encoding="utf-8"))["payloads"]
        if len(new) < 0.8 * len(old): errs.append(f"payload count dropped {len(old)} -> {len(new)}")
    except Exception:
        pass
if len(new) < 20: errs.append(f"only {len(new)} payloads")
if errs:
    print("VALIDATION FAILED:\n- " + "\n- ".join(errs)); sys.exit(1)
print(f"catalog OK: {len(new)} payloads")
