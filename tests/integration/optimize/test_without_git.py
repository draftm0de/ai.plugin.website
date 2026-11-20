"""Git-free audit/apply and file guard acceptance."""
import shutil
from unittest.mock import patch
from tests.support import optimize_helpers as h
import audit


class WithoutGit(h.AuditCase):
    def setUp(self):
        super().setUp()
        shutil.rmtree(self.root / '.git')

    def test_audit_decide_apply_recheck_without_git_queries(self):
        original = audit.subprocess.run
        def no_git(argv, *args, **kwargs):
            self.assertNotEqual(argv[0], 'git')
            return original(argv, *args, **kwargs)
        with patch.object(audit.subprocess, 'run', side_effect=no_git):
            result = self.audit(proposals={'seo.description-too-short|/a.html|': self.proposal_for(h.GOOD_A)})
            self.assertEqual(result['status'], 'clean-with-warnings')
            self.decide(['SEO-001'], 'approved')
            result = self.apply(['SEO-001'], minutes=1)
            self.assertEqual(result['exit_code'], 0, result)
            self.assertIn(h.GOOD_A, (self.site / 'src/content.json').read_text())
        self.assertFalse((self.root / '.git').exists())

    def test_added_modified_and_deleted_files_are_detected(self):
        for operation in ('add', 'modify', 'delete'):
            with self.subTest(operation=operation):
                target = self.site / ('new.txt' if operation == 'add' else 'src/touched.txt')
                if operation != 'add': target.write_text('original')
                def mutate():
                    if operation == 'delete': target.unlink()
                    else: target.write_text('changed')
                result = self.audit(minutes={'add': 1, 'modify': 2, 'delete': 3}[operation], hooks={'after_checks': mutate})
                self.assertEqual(result['status'], 'readonly-violated', result)
                self.assertIn(target.relative_to(self.root).as_posix(), result['readonly_violations'])
