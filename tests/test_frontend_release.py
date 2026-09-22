import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from deploy.frontend_release import promote, rollback


class FrontendReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for folder, content in [('dist', 'old'), ('dist-next', 'new')]:
            (self.root / folder).mkdir()
            (self.root / folder / 'index.html').write_text(content)

    def test_promote_and_rollback_preserve_both_versions(self):
        saved = promote(self.root)
        self.assertEqual('new', (self.root / 'dist/index.html').read_text())
        self.assertEqual('old', (saved / 'index.html').read_text())
        displaced = rollback(self.root, saved.name)
        self.assertEqual('old', (self.root / 'dist/index.html').read_text())
        self.assertEqual('new', (displaced / 'index.html').read_text())

    def test_invalid_build_does_not_change_current(self):
        (self.root / 'dist-next/index.html').unlink()
        with self.assertRaises(ValueError):
            promote(self.root)
        self.assertEqual('old', (self.root / 'dist/index.html').read_text())

    def test_failed_promotion_restores_current(self):
        rename = Path.rename
        def fail_candidate(path, target):
            if path.name == 'dist-next':
                raise OSError('simulated promotion failure')
            return rename(path, target)
        with patch.object(Path, 'rename', fail_candidate), self.assertRaises(OSError):
            promote(self.root)
        self.assertEqual('old', (self.root / 'dist/index.html').read_text())

    def test_backup_path_cannot_escape_frontend(self):
        for name in ['../dist-backup-other', '/tmp/dist-backup-other', 'dist-next']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                rollback(self.root, name)

    def test_failed_rollback_restores_current(self):
        saved = promote(self.root)
        rename = Path.rename
        def fail_backup(path, target):
            if path == saved:
                raise OSError('simulated rollback failure')
            return rename(path, target)
        with patch.object(Path, 'rename', fail_backup), self.assertRaises(OSError):
            rollback(self.root, saved.name)
        self.assertEqual('new', (self.root / 'dist/index.html').read_text())
        self.assertEqual('old', (saved / 'index.html').read_text())
