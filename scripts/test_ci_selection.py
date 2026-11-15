"""CI selection/gate and offline docs validation; standard library only."""
from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from ci_select import SUITES, changed_paths, plan, select, verify_gate
from ci_docs import CORE, validate

FULL = dict.fromkeys(SUITES, True)


class SelectionTests(unittest.TestCase):
    def test_documentation_only(self):
        self.assertEqual(select(['docs/PROJECT-HANDOFF.md', 'README.md', 'AGENTS.md']), dict.fromkeys(SUITES, False))

    def test_components_and_union(self):
        self.assertEqual(select(['frontend/src/App.tsx']), dict(unit=False, postgres=False, ui=True))
        self.assertEqual(select(['backend/tests/integration/test_revisions.py']), dict(unit=True, postgres=True, ui=False))
        self.assertEqual(select(['worker/tests/test_real_upstox.py']), dict(unit=True, postgres=True, ui=False))
        self.assertEqual(select(['backend/tests/test_main.py', 'frontend/tests/workbench.spec.ts']), FULL)
        for path in ('backend/app/main.py', 'worker/worker/candidates.py', 'shared/stock_discovery_analysis/strategy.py'):
            with self.subTest(path=path): self.assertEqual(select([path]), FULL)

    def test_sensitive_dependencies_fixtures_and_unknown_are_full(self):
        paths = ['.github/workflows/ci.yml', 'scripts/ci_select.py', 'scripts/ci_docs.py',
                 'backend/requirements.txt', 'frontend/package-lock.json', '.python-version',
                 'backend/migrations/versions/0017.py', 'deploy/bookmyhost/compose.yaml',
                 'compose.yaml', 'worker/Dockerfile', '.env.example', 'docs/contracts/v2/schema.json',
                 'docs/contracts/evidence/README.md', 'docs/policies/policy.json',
                 'frontend/src/auth.ts', 'frontend/src/Session.tsx', 'frontend/public/Dockerfile', 'frontend/public/schema.sql', 'frontend/src/access.ts',
                 'docs/security.md', 'backend/tests/integration/test_chartink_delivery.py',
                 'unknown.new', '../README.md', '/README.md']
        for path in paths:
            with self.subTest(path=path): self.assertEqual(select([path]), FULL)
        self.assertEqual(select([]), FULL)

    def test_large_diff_and_odd_filenames_are_not_truncated_or_executed(self):
        self.assertEqual(select([f'docs/{i}.md' for i in range(1001)] + ['shared/changed.py']), FULL)
        self.assertEqual(select(['docs/a space\nand $(false).md']), dict.fromkeys(SUITES, False))

    def test_gate_exhaustive_results_and_selection(self):
        for mask in itertools.product(('true','false'), repeat=3):
            for results in itertools.product(('success','failure','cancelled','skipped'), repeat=3):
                needs = {'changes': {'result':'success','outputs':dict(zip(SUITES,mask))}}
                needs.update({name:{'result':r} for name,r in zip(SUITES,results)})
                good = all(r == ('success' if m=='true' else 'skipped') for m,r in zip(mask,results))
                if good: verify_gate(needs)
                else:
                    with self.assertRaises(ValueError): verify_gate(needs)

    def test_gate_rejects_failed_selector_missing_invalid_outputs_and_jobs(self):
        good={'changes':{'result':'success','outputs':dict.fromkeys(SUITES,'false')}}
        good.update({name:{'result':'skipped'} for name in SUITES})
        for result in ('failure','cancelled','skipped'):
            bad=deepcopy(good);bad['changes']['result']=result
            with self.assertRaises(ValueError):verify_gate(bad)
        for value in ('',None,True,'TRUE','maybe'):
            bad=deepcopy(good);bad['changes']['outputs']['unit']=value
            with self.assertRaises(ValueError):verify_gate(bad)
        for missing in ('unit','changes'):
            bad=deepcopy(good);del bad[missing]
            with self.assertRaises(ValueError):verify_gate(bad)

    def test_git_diff_covers_multiple_commits_renames_deletions_and_merge_base_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def git(*args):
                return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.PIPE).decode().strip()
            def write(name,body):
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
            def commit():
                git('add','.');git('commit','-m','synthetic selection fixture');return git('rev-parse','HEAD')
            git('init','-b','main');git('config','user.name','CI fixture');git('config','user.email','ci@example.invalid')
            write('backend/old.py','original\n');write('docs/old.md','# old\n');base=commit()
            git('checkout','-b','topic');git('mv','backend/old.py','docs/renamed.md');first=commit()
            write('frontend/src/view.ts','changed');head=commit()
            event={'before':base,'after':head}
            paths=changed_paths(event,'push',head,root)
            self.assertEqual(set(paths),{'backend/old.py','docs/renamed.md','frontend/src/view.ts'})
            self.assertEqual(plan(event,'push',head,root)['required'],FULL)
            git('checkout','main');write('docs/base.md','# current base');newbase=commit()
            git('merge','topic','--no-edit');merge=git('rev-parse','HEAD')
            event={'pull_request':{'base':{'sha':newbase},'head':{'sha':head}}}
            self.assertEqual(set(changed_paths(event,'pull_request',merge,root)),set(paths))
            self.assertEqual(plan(event,'pull_request',merge,root)['required'],FULL)
            git('rm','docs/old.md');after=commit()
            self.assertIn('docs/old.md',changed_paths({'before':merge,'after':after},'push',after,root))
            for bad in ({'before':'0'*40,'after':after},{'before':'f'*40,'after':after},{}):
                self.assertEqual(plan(bad,'push',after,root)['required'],FULL)
            self.assertEqual(plan(event,'pull_request',first,root)['required'],FULL)
            self.assertEqual(plan({},'unknown',after,root)['required'],FULL)


class DocumentationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in CORE:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# Summary\n')

    def check(self,paths):
        with redirect_stdout(StringIO()):validate(self.root,paths)

    def test_links_code_fences_and_core_summaries(self):
        (self.root/'docs/new.md').write_text('# Doc\n[board](SIMPLE-BOARD.md)\n```python\n[x](not-real)\n```\n')
        self.check(['docs/new.md'])
        (self.root/'docs/PROJECT-HANDOFF.md').write_text('[missing](absent.md)')
        with self.assertRaisesRegex(ValueError,'broken_local_link'):self.check([])

    def test_conflicts_fences_and_reference_links_fail(self):
        for text,error in [('<<<<<<< HEAD\n','merge_conflict'),('```python\nx\n','unclosed'),('[ref]: missing.md\n','broken_local')]:
            (self.root/'docs/new.md').write_text(text)
            with self.assertRaisesRegex(ValueError,error):self.check(['docs/new.md'])

    def test_deleted_target_breaks_unchanged_referrer(self):
        subprocess.run(['git','init'],cwd=self.root,check=True,capture_output=True)
        (self.root/'docs/old.md').write_text('[link](removed.md)')
        subprocess.run(['git','add','.'],cwd=self.root,check=True,capture_output=True)
        with self.assertRaisesRegex(ValueError,'deleted_link_target'):self.check(['docs/removed.md'])
