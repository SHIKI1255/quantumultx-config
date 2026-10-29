"""Scheduled data-only check; an immutable producer revision is passed to the build."""
import json
import os
from pathlib import Path
import sys
from build import ROOT, REPOSITORY
from shared_data import COMMON_REPOSITORY, RAW, fetch, digest, json_bytes, release_sha, require
from release_health import incidents


def source_hashes(root):
    paths = [p for folder in ("scripts", "config", "tests") for p in sorted((root/folder).rglob("*"))
             if p.is_file() and "__pycache__" not in p.parts]
    paths += [root/"docs/third_party.md"]
    if REPOSITORY.endswith("clash-config"):
        paths += [root/"docs/install.md"]
    return {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in paths}


def check(force=False):
    common = release_sha(COMMON_REPOSITORY)
    m = json.loads(fetch(RAW + COMMON_REPOSITORY + "/" + common + "/shared/manifest.json"))
    require(m.get("schema_version") == 1, "Unknown shared schema")
    require(m["shared_version"] == digest(json_bytes({k:v for k,v in m.items() if k!="shared_version"})),
            "Shared manifest version mismatch")
    if force:
        return {"changed": True, "reason": "full_validation", "shared_release": common,
                "shared_version": m["shared_version"]}
    own = release_sha(REPOSITORY)
    old = json.loads(fetch(RAW + REPOSITORY + "/" + own + "/manifest.json"))
    require(old.get("schema_version") == 2, "Unknown client manifest schema")
    changed = old["shared_version"] != m["shared_version"]
    reason = "shared_update" if changed else "no_change"
    if old["source_files_sha256"] != source_hashes(ROOT):
        changed, reason = True, "builder_update"
    if not changed and incidents():
        changed, reason = True, "recovery_verification"
    return {"changed": changed, "reason": reason, "shared_release": common,
            "shared_version": m["shared_version"], "client_release": own}


def main():
    try:
        event = os.environ.get("GITHUB_EVENT_NAME")
        require(event in {"push","pull_request","schedule","workflow_dispatch"}, "Unexpected event")
        scheduled = event == "schedule" or (event == "workflow_dispatch" and
                    os.environ.get("PROBE_ONLY") == "true")
        result = check(force=not scheduled)
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("changed=" + str(result["changed"]).lower() + "\n")
            f.write("shared_release=" + result["shared_release"] + "\n")
        print(json.dumps(result))
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        print("PROBE STOPPED: public version check failed", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
