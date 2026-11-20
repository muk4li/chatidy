"""META-001: segment completeness against the root export_manifest.json (synthetic only)."""
import io
import json
import unittest

from chatidy.importer import inspect_export, parse_export
from test_archives import archive
from test_segmented_exports import conversation


def manifest(names, shard_count=True, **extra):
    entry = {"files": names, "sharded": len(names) > 1}
    if shard_count:
        entry["shard_count"] = len(names)
    return json.dumps({"version": 1, "manifest_file": "export_manifest.json",
                       "export_files": [{"path": n, "size_bytes": 1} for n in names],
                       "logical_files": {"conversations.json": entry,
                                         "user.json": {"files": ["user.json"], "sharded": False}}, **extra})


def segments(count, total=None):
    names = [f"conversations-{i:03d}.json" for i in range(total or count)]
    files = [(n, json.dumps([conversation(i)])) for i, n in enumerate(names[:count])]
    return names, files


class ManifestTests(unittest.TestCase):
    def inventory(self, files):
        return inspect_export(io.BytesIO(archive(files)), "synthetic.zip")

    def test_complete_export_is_validated(self):
        names, files = segments(8)
        inventory = self.inventory(files + [("export_manifest.json", manifest(names))])
        self.assertTrue(inventory["manifests_validated"])
        self.assertNotIn("Ohne validiertes Manifest ist ein fehlendes letztes Segment nicht nachweisbar.", inventory["warnings"])
        self.assertIn("Konversationsdateien mit dem Export-Manifest abgeglichen: vollständig.", inventory["warnings"])
        self.assertEqual(len(parse_export(archive(files + [("export_manifest.json", manifest(names))]), "x.zip")), 8)

    def test_missing_last_segment_is_detected(self):
        names, files = segments(7, total=8)
        data = archive(files + [("export_manifest.json", manifest(names))])
        with self.assertRaisesRegex(ValueError, r"Manifest nennt 8 .* im Archiv sind 7 \(fehlend: conversations-007\.json\)"):
            inspect_export(io.BytesIO(data), "synthetic.zip")
        with self.assertRaisesRegex(ValueError, "Export unvollständig"):
            parse_export(data, "synthetic.zip")

    def test_unexpected_extra_segment_is_reported(self):
        names, files = segments(3)
        with self.assertRaisesRegex(ValueError, "nicht im Manifest: conversations-002.json"):
            self.inventory(files + [("export_manifest.json", manifest(names[:2]))])

    def test_classic_single_file_and_paths_in_manifest(self):
        files = [("data/conversations.json", json.dumps([conversation(0)])),
                 ("data/export_manifest.json", manifest(["data/conversations.json"], shard_count=False))]
        self.assertTrue(self.inventory(files)["manifests_validated"])

    def test_unrecognized_or_inconsistent_manifests_only_warn(self):
        names, files = segments(2)
        inconsistent = json.loads(manifest(names))
        inconsistent["logical_files"]["conversations.json"]["shard_count"] = 5
        two_candidates = json.loads(manifest(names))
        two_candidates["logical_files"]["other"] = {"files": ["conversations-000.json"]}
        for body in ("{not json", json.dumps([1]), json.dumps({"version": "1", "logical_files": {}}),
                     json.dumps({"version": True, "logical_files": {}}), json.dumps(inconsistent),
                     json.dumps(two_candidates), json.dumps({"version": 1, "logical_files": {"x": {"files": ["a.json"]}}})):
            with self.subTest(body=body[:40]):
                inventory = self.inventory(files + [("export_manifest.json", body)])
                self.assertFalse(inventory["manifests_validated"])
                self.assertIn("Ohne validiertes Manifest ist ein fehlendes letztes Segment nicht nachweisbar.", inventory["warnings"])

    def test_manifest_outside_root_folder_is_not_used(self):
        names, files = segments(1, total=2)
        inventory = self.inventory(files + [("sites/export_manifest.json", manifest(names))])
        self.assertFalse(inventory["manifests_validated"])


if __name__ == "__main__":
    unittest.main()
