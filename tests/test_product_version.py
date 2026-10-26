import json
from pathlib import Path
import unittest

from product_version import VERSION


class ProductVersionTests(unittest.TestCase):
    def test_product_and_manifests_share_candidate_version(self):
        root = Path(__file__).resolve().parent.parent
        identity = json.loads((root / "frontend/src/productVersion.json").read_text(encoding="utf-8"))
        self.assertEqual(identity["channel"], "candidate")
        self.assertRegex(VERSION, r"^1\.5\.0-rc\.[1-9][0-9]*$")
        for name in ("package.json", "package-lock.json"):
            manifest = json.loads((root / "frontend" / name).read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], VERSION)


if __name__ == "__main__":
    unittest.main()
