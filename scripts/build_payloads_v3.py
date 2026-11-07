#!/usr/bin/env python3
"""
build_payloads_v3.py
Builds payloads_v3.json (same schema as itsPLK payloads_v2.json) from the
LATEST GitHub releases of each payload, computes sha256 for every file, and
tags each entry with fw_11_60 status.

Usage:
    python build_payloads_v3.py                       # url = upstream direct link
    python build_payloads_v3.py --mirror-base https://github.com/YOU/ps5-payloads-mirror/releases/download/payloads-mirror
    set GITHUB_TOKEN=xxxx   (optional, avoids API rate limit)

Output:  out/payloads_v3.json   +  out/files/<filename>  (upload these to your own release if using --mirror-base)
"""
import argparse, hashlib, io, json, os, re, sys, urllib.request, zipfile

V2_URL = "https://itsplk.github.io/ps5-payloads-mirror/payloads_v2.json"
TOKEN = os.environ.get("GITHUB_TOKEN")

# fw_11_60: "yes" = stated by the project, "likely" = stated range/SDK suggests it,
#           "unverified" = project does not state firmware support (test before relying on it)
# name -> (owner/repo, category, fw_11_60, fw_note)
REPOS = {
 "etaHEN":                  ("etaHEN/etaHEN", "System & Jailbreak", "likely", "Release page states no range; scene guide: Relapse chain 7.00-13.60 runs etaHEN"),
 "kstuff-lite":             ("EchoStretch/kstuff-lite", "System & Jailbreak", "yes", "Stated 3.00-12.70"),
 "elfldr":                  ("ps5-payload-dev/elfldr", "Loaders", "unverified", "No firmware statement"),
 "onionHEN":                ("aydencharles/onionHEN", "System & Jailbreak", "yes", "Stated 4.03-12.70 (do not run with etaHEN/CheatRunner)"),
 "NeoEnabler":              ("gasb07/NeoEnabler", "Utilities & Tools", "yes", "Stated 4.00-13.60; 8GiB/GPU-clock features limited to 13.20/13.60"),
 "pldmgr":                  ("itsPLK/ps5-payload-manager", "Utilities & Tools", "likely", "Rebuilt with SDK for FW 13.60"),
 "ps5-exporter":            ("Marice/ps5-exporter", "Utilities & Tools", "unverified", "Tested on 13.60; others 'likely, not verified'"),
 "ps4mount":                ("gasb07/ps4mount", "Utilities & Tools", "yes", "Firmwares below 12.00 supported"),
 "ps5-web-file-manager":    ("owendswang/ps5-web-file-manager", "Networking & Servers", "yes", "Author benchmarks on FW 11.60"),
 "ps5upload":               ("phantomptr/ps5upload", "Networking & Servers", "unverified", "No firmware statement"),
 "ps5-dump-forge":          ("quer3q/ps5-dump-forge", "Utilities & Tools", "unverified", "No firmware statement"),
 "WebKit-Autoloader-Installer": ("itsPLK/ps5-webkit-autoloader", "Loaders", "unverified", "Changelog mentions 9.05 and 1.00-5.50 only; not for 11.60 browser entry"),
 "CheatRunner":             ("notmaj0r/CheatRunner", "Utilities & Tools", "unverified", "No firmware statement"),
 "ShadowMountPlus":         ("drakmor/ShadowMountPlus", "Utilities & Tools", "unverified", "No firmware statement"),
 "zftpd":                   ("seregonwar/zftpd", "Networking & Servers", "unverified", "No firmware statement"),
 "LiveShell":               ("ZiZc3/LiveShell", "Utilities & Tools", "unverified", "No firmware statement"),
 "WelcomeHubActivator":     ("ghost1372/WelcomeHubActivator", "Utilities & Tools", "unverified", "No firmware statement"),
 "PS5Save":                 ("heni0xyz/PS5Save", "Utilities & Tools", "unverified", "No firmware statement"),
 "ps-patch-system":         ("illusionyy/ps-patch-system", "Utilities & Tools", "unverified", "Only mentions 7.XX patterns"),
 "PKG-Manager":             ("itsPLK/ps5-pkg-manager", "Utilities & Tools", "unverified", "No firmware statement"),
 "ps5-app-dumper":          ("EchoStretch/ps5-app-dumper", "Utilities & Tools", "unverified", "No firmware statement"),
 "ps5debug-NG":             ("Pharaoh2k/ps5debug-NG", "System & Jailbreak", "unverified", "No firmware statement"),
 "ftpsrv-drakmor":          ("drakmor/ftpsrv", "Networking & Servers", "unverified", "No firmware statement"),
 "ps5-linux-loader":        ("ps5-linux/ps5-linux-loader", "Loaders", "unverified", "No firmware statement"),
 "ps5-date-time-sync":      ("kerrdec97/ps5-date-time-sync", "Utilities & Tools", "unverified", "No firmware statement"),
 "ftpsrv":                  ("ps5-payload-dev/ftpsrv", "Networking & Servers", "unverified", "No firmware statement"),
 "BFpilot":                 ("ItsBlurf/BFpilot", "Utilities & Tools", "unverified", "No firmware statement"),
 "nanoDNS":                 ("drakmor/nanoDNS", "Networking & Servers", "unverified", "No firmware statement"),
 "websrv":                  ("ps5-payload-dev/websrv", "Networking & Servers", "unverified", "No firmware statement"),
 "shsrv":                   ("ps5-payload-dev/shsrv", "Networking & Servers", "unverified", "No firmware statement"),
 "klogsrv":                 ("ps5-payload-dev/klogsrv", "Networking & Servers", "unverified", "No firmware statement"),
 "Lapy-JB-Daemon":          ("itsPLK/PS5-Lapy-JB-Daemon", "System & Jailbreak", "unverified", "No firmware statement"),
 "BackPork":                ("BestPig/BackPork", "System & Jailbreak", "unverified", "No firmware statement"),
 # --- NEW compared with v2 (verify it exists / has release assets before relying on it) ---
 "gdbsrv":                  ("ps5-payload-dev/gdbsrv", "Utilities & Tools", "unverified", "NEW - GDB server, no firmware statement"),
}
# not on GitHub (kept exactly as in v2): garlic-savemgr (git.etawen.dev)

# per-payload asset regex overrides (otherwise: first .elf, then .bin, then .zip)
ASSET_RE = {
 "zftpd": r"zhttp.*\.elf$",
 "ShadowMountPlus": r"\.zip$",
 "WebKit-Autoloader-Installer": r"installer.*\.elf$",
 "etaHEN": r"\.bin$",
 "ps5upload": r"\.elf$",
}
EXTRACT = {"ShadowMountPlus": "shadowmountplus.elf"}


def http(url, accept=None):
    req = urllib.request.Request(url, headers={"User-Agent": "payloads-v3-builder"})
    if accept: req.add_header("Accept", accept)
    if TOKEN and "api.github.com" in url: req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def latest_release(repo):
    rels = json.loads(http(f"https://api.github.com/repos/{repo}/releases?per_page=10"))
    rels = [r for r in rels if not r.get("draft")]
    return rels[0] if rels else None  # newest first, prereleases included (many tools only ship betas)


def pick_asset(name, assets):
    pats = [ASSET_RE[name]] if name in ASSET_RE else [r"\.elf$", r"\.bin$", r"\.zip$"]
    for p in pats:
        for a in assets:
            if re.search(p, a["name"], re.I): return a
    return None


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mirror-base", default="", help="base URL of YOUR release; url fields point here")
    ap.add_argument("--out", default="out")
    ap.add_argument("--previous", default="payloads_v3.json", help="last published catalog; unchanged payloads are not re-downloaded")
    ap.add_argument("--force", action="store_true", help="re-download everything")
    args = ap.parse_args()
    os.makedirs(os.path.join(args.out, "files"), exist_ok=True)

    v2 = json.loads(http(V2_URL))
    base = {p["name"]: p for p in v2["payloads"]}
    prev = {p["name"]: p for p in load_json(args.previous).get("payloads", [])}
    result, report = [], []

    for name, (repo, cat, fw, note) in REPOS.items():
        p = prev.get(name)
        old = p or base.get(name, {})
        try:
            rel = latest_release(repo)
            if not rel: raise RuntimeError("no release found")
            reuse = (p and not args.force and p.get("version") == rel["tag_name"] and p.get("checksum")
                     and (not args.mirror_base or p.get("url", "").startswith(args.mirror_base.rstrip("/") + "/")))
            if reuse:
                entry = dict(p); status = "unchanged"
            else:
                asset = pick_asset(name, rel["assets"])
                if not asset: raise RuntimeError("no matching asset")
                data = http(asset["browser_download_url"])
                ext = os.path.splitext(asset["name"])[1]
                if name in EXTRACT:  # zip containing the ELF: mirror the ELF itself (like v2)
                    data = zipfile.ZipFile(io.BytesIO(data)).read(EXTRACT[name]); ext = ".elf"
                sha = hashlib.sha256(data).hexdigest()
                fname = f"{name}_{rel['tag_name']}{ext}"
                with open(os.path.join(args.out, "files", fname), "wb") as f: f.write(data)
                entry = dict(old)  # keep icon_key, description, etc.
                entry.update({
                    "name": name, "filename": fname,
                    "url": (args.mirror_base.rstrip("/") + "/" + fname) if args.mirror_base else asset["browser_download_url"],
                    "source": f"https://github.com/{repo}/releases",
                    "source_direct": asset["browser_download_url"],
                    "version": rel["tag_name"], "last_update": rel["published_at"][:10],
                    "category": old.get("category", cat), "checksum": sha,
                    "prerelease": bool(rel.get("prerelease")),
                })
                entry.setdefault("description", (rel.get("body") or "").strip().split("\n")[0][:120] or name)
                if name in EXTRACT: entry["extract_file"] = EXTRACT[name]
                if name == "zftpd": entry["asset_pattern"] = "zhttp"
                status = "NEW" if not p else f"UPDATED {p.get('version')} -> {rel['tag_name']}"
        except Exception as e:
            if not old:
                report.append((name, f"SKIPPED (new, failed: {e})")); continue
            entry = dict(old); status = f"KEPT previous entry (fetch failed: {e})"
        entry["fw_11_60"], entry["fw_note"] = fw, note
        result.append(entry); report.append((name, status))

    g = prev.get("garlic-savemgr") or base.get("garlic-savemgr")
    if g:
        g = dict(g); g["fw_11_60"] = "unverified"; g["fw_note"] = "Hosted on git.etawen.dev; kept as-is"
        result.insert(1, g); report.append(("garlic-savemgr", "KEPT (non-GitHub source)"))

    try:  # icons.json is referenced relatively by the catalog; copy it next to the JSON
        with open(os.path.join(args.out, v2.get("icons_url", "icons.json")), "wb") as f:
            f.write(http(V2_URL.rsplit("/", 1)[0] + "/" + v2.get("icons_url", "icons.json")))
    except Exception as e:
        print("WARN: could not copy icons.json:", e)

    out = {"name": "PS5 Payloads v3", "icons_url": v2.get("icons_url", "icons.json"), "payloads": result}
    with open(os.path.join(args.out, "payloads_v3.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # change report (only when a previous catalog exists, to avoid a 35-line "everything is new" issue)
    changes = []
    if prev:
        cur = {e["name"]: e for e in result}
        for n, e in cur.items():
            tag = " (pre-release)" if e.get("prerelease") else ""
            if n not in prev:
                changes.append(f"- NEW **{n}** {e.get('version')}{tag} - 11.60: {e.get('fw_11_60')}")
            elif prev[n].get("version") != e.get("version"):
                changes.append(f"- **{n}**: {prev[n].get('version')} -> {e.get('version')}{tag} - 11.60: {e.get('fw_11_60')}")
        for n in prev:
            if n not in cur: changes.append(f"- REMOVED **{n}**")
    chg = os.path.join(args.out, "changes.md")
    if changes:
        with open(chg, "w", encoding="utf-8") as f: f.write("\n".join(changes) + "\n")
    elif os.path.exists(chg):
        os.remove(chg)

    for n, s in report: print(f"{n:30} {s}")
    print(f"\n{len(result)} payloads, {len(changes)} change(s) -> {args.out}/payloads_v3.json")


if __name__ == "__main__":
    main()
