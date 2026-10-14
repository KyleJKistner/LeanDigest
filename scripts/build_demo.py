#!/usr/bin/env python3
"""Regenerate the hash-pinned source demo and wheel assets. Never runs Lean."""
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from proofreader.corpus import benchmark_sources

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    result = benchmark_sources(ROOT / 'examples/openai', ROOT / 'artifacts/openai-sample')
    if result['failed_or_missing_files'] or result['source_files_indexed'] != 6:
        raise SystemExit('Pinned sample inventory did not reconcile; refusing to package a partial demo')
    data = ROOT / 'proofreader/data'
    data.mkdir(exist_ok=True)
    for src, dst in [
        ('artifacts/openai-sample/document.json', 'demo.json'),
        ('lean/ProofReader.lean', 'ProofReader.lean'),
        ('examples/openai/LICENSE', 'OPENAI_SOURCE_LICENSE.txt'),
        ('THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_NOTICES.md'),
    ]:
        shutil.copyfile(ROOT / src, data / dst)
    print(f"Packaged {result['source_files_indexed']} source files, {result['declaration_candidates']} declarations; no Lean build or English certification")

if __name__ == '__main__':
    main()
