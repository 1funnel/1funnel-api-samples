# SPDX-License-Identifier: Apache-2.0
"""Optional repository convenience; individual sample tests run without this tool."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess

spec = importlib.util.spec_from_file_location('ci_plan', Path(__file__).with_name('ci-plan.py'))
plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan)
parser = argparse.ArgumentParser()
parser.add_argument('--language', required=True, choices=['nodejs', 'python', 'java', 'curl'])
args = parser.parse_args()
selected = json.loads(os.environ['SAMPLE_IDS']) if 'SAMPLE_IDS' in os.environ else None
for sample in plan.catalog():
    if sample['language'] == args.language and (selected is None or sample['id'] in selected):
        print('Testing', sample['id'], flush=True)
        subprocess.run(sample['test'], cwd=plan.ROOT / sample['path'], check=True)
