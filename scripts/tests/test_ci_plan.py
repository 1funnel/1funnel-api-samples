# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('ci_plan', Path(__file__).resolve().parents[1] / 'ci-plan.py')
plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan)


class PlannerTest(unittest.TestCase):
    def setUp(self):
        self.entries = plan.catalog()

    def test_sample_change_selects_only_that_sample(self):
        sample = self.entries[0]
        self.assertEqual(plan.select(self.entries, [sample['path'] + '/src/app.mjs']), [sample])

    def test_shared_or_unknown_changes_test_everything(self):
        for name in ['fixtures/wallet/balance.json', '.github/workflows/samples.yml', 'samples/catalog.json', 'samples/deleted/task/python/src/app.py', 'README.md']:
            with self.subTest(name=name):
                self.assertEqual(plan.select(self.entries, [name]), self.entries)
        self.assertEqual(plan.select(self.entries, None), self.entries)

    def test_multiple_samples_and_no_changes(self):
        chosen = self.entries[:2]
        self.assertEqual(plan.select(self.entries, [s['path'] + '/README.md' for s in chosen]), chosen)
        self.assertEqual(plan.select(self.entries, []), [])


if __name__ == '__main__':
    unittest.main()
