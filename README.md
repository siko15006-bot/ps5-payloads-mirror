# ps5-payloads-mirror

[![build](https://github.com/siko15006-bot/ps5-payloads-mirror/actions/workflows/build.yml/badge.svg)](https://github.com/siko15006-bot/ps5-payloads-mirror/actions/workflows/build.yml)

Auto-updated PS5 payload catalog (same schema as itsPLK `payloads_v2.json`), rebuilt **every hour** by GitHub Actions.

**Catalog URL** (paste in the payload manager -> *Add a New Source*):

    https://raw.githubusercontent.com/siko15006-bot/ps5-payloads-mirror/main/payloads_v3.json

## How it works
1. Reads the latest release of every upstream repo listed in `scripts/build_payloads_v3.py` (`REPOS`).
2. Downloads **only payloads whose version changed**, computes sha256, uploads to the `payloads-mirror` release.
3. Validates the catalog (`scripts/validate_catalog.py`) and refuses to publish a broken one.
4. Commits `payloads_v3.json`, prepends `CHANGELOG.md`, and opens an **Issue assigned to the owner** listing what changed (push notification in the GitHub app).
5. Deletes release files no longer referenced.

## Extra fields
- `fw_11_60`: `yes` (project states support) / `likely` / `unverified` - test before relying on `unverified`.
- `fw_note`: where that status came from.
- `prerelease`: the newest upstream release is a pre-release/beta.

## Maintenance
- Add a payload: add a line to `REPOS` (and an `ASSET_RE` entry if the default `.elf/.bin/.zip` pick is wrong).
- Force a full rebuild: Actions -> build-payloads-v3 -> Run workflow -> *force*.
- GitHub pauses scheduled workflows after 60 days without repo activity; re-enable from the Actions tab if that happens.
