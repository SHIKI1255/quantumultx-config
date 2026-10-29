import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import check_update as probe
from shared_data import digest, json_bytes


class VersionProbeTests(unittest.TestCase):
    def scenario(self, change=False, source_change=False, incident=False, force=False):
        basis={"schema_version":1,"bundle_sha256":"d"*64}
        m={**basis,"shared_version":digest(json_bytes(basis))}
        old={"schema_version":2,"shared_version":"e"*64 if change else m["shared_version"],
             "source_files_sha256":{} if source_change else {"code":"h"}}
        seen=[]
        def fetch(url):
            seen.append(url)
            return json_bytes(m if url.endswith("/shared/manifest.json") else old)
        with patch.object(probe,"release_sha",side_effect=["a"*40,"b"*40]), patch.object(probe,"fetch",side_effect=fetch), patch.object(probe,"source_hashes",return_value={"code":"h"}), patch.object(probe,"incidents",return_value=[{}] if incident else []):
            result=probe.check(force)
        return result,seen

    def test_unchanged_skips_and_changed_is_pinned(self):
        result,seen=self.scenario()
        self.assertFalse(result["changed"])
        self.assertEqual(result["shared_release"],"a"*40)
        self.assertTrue(all("/"+"a"*40+"/" in u or "/"+"b"*40+"/" in u for u in seen))
        result,_=self.scenario(change=True)
        self.assertTrue(result["changed"]);self.assertEqual(result["reason"],"shared_update")

    def test_builder_recovery_and_manual_run_force_full_checks(self):
        for kwargs,reason in [({"source_change":True},"builder_update"),({"incident":True},"recovery_verification"),({"force":True},"full_validation")]:
            result,_=self.scenario(**kwargs)
            self.assertTrue(result["changed"]);self.assertEqual(result["reason"],reason)

    def test_failed_or_unknown_manifest_is_not_no_change(self):
        for value in [b"not JSON",json_bytes({"schema_version":99}),json_bytes({"schema_version":1,"shared_version":"wrong"})]:
            with patch.object(probe,"release_sha",return_value="a"*40),patch.object(probe,"fetch",return_value=value),self.assertRaises((ValueError,KeyError)):
                probe.check()
        with patch.object(probe,"release_sha",side_effect=OSError()),self.assertRaises(OSError):
            probe.check()

    def test_twice_daily_trigger_and_full_validation_dependency(self):
        text=(probe.ROOT/".github/workflows/update.yml").read_text()
        minute="17" if probe.REPOSITORY.endswith("clash-config") else "47"
        hours="11,23" if probe.REPOSITORY.endswith("clash-config") else "10,22"
        self.assertIn("cron: '"+minute+" "+hours+" * * *'",text)
        self.assertIn("needs: probe\n    if: needs.probe.outputs.changed == 'true'",text)
        self.assertIn("'--shared-release', $env:SHARED_RELEASE",text)
        self.assertIn("needs: [probe, validate, publish, monitor]",text)

if __name__ == "__main__":unittest.main()
