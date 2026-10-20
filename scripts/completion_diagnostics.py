"""Summarize already-retained recovery logs; this is not a proof-validation gate."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from proofreader.original_project import child, read, write


def diagnose(collections: list[Path], output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    status_path = output/'site/original-verification.json'
    remaining = None
    if status_path.is_file():
        status = read(status_path)
        remaining = {
            'theorems': [{'module': r['module'], 'name': r['name']}
                         for r in status['theorems'] if not r['reading_available']],
            'tasks': [{'id': r['id'], 'status': r['status'], 'diagnosis': r['diagnosis']}
                      for r in status['tasks'] if r['status'] != 'passed'],
        }
        write(output/'remaining-obligations.json', remaining)
    workers = []
    for folder in collections:
        for directory in sorted(folder.glob('completion-result-*')):
            # The frozen archive and its extracted directory intentionally share
            # a stem. Only the directory contains individual observations.
            if directory.is_symlink():
                raise ValueError('Linked recovery diagnostics directory')
            if not directory.is_dir():
                continue
            worker = {'identity': read(directory/'identity.json'), 'rounds': [],
                      'final': read(directory/'final-status.json')
                      if (directory/'final-status.json').is_file() else None,
                      'proof_outcomes': [], 'unsuccessful_checks': []}
            for file in sorted(directory.glob('round-*/execution.json')):
                record = read(file)
                worker['rounds'].append({'round': file.parent.name,
                    'status': record.get('status'), 'reason': record.get('reason'),
                    'exit_code': record.get('exit_code'),
                    'stdout_tail': record.get('stdout', '')[-2400:],
                    'stderr_tail': record.get('stderr', '')[-1200:]})
            for file in sorted(directory.rglob('original-proof-worker.json')):
                record = read(file)
                worker['proof_outcomes'].append({key: record.get(key) for key in
                    ('module', 'status', 'validated_readings', 'error')})
                ledger = file.parent/'reading/proofs.json'
                if ledger.is_file():
                    for row in read(ledger)['targets']:
                        if row['status'] != 'reading-generated':
                            worker['proof_outcomes'].append({key: row.get(key) for key in
                                ('module', 'name', 'status', 'reason', 'errors')})
            for file in sorted(directory.rglob('worker.json')):
                for row in read(file).get('targets', []):
                    if row['status'] != 'passed' and row.get('log'):
                        record = read(child(file.parent, row['log']))
                        worker['unsuccessful_checks'].append({'id': row['id'], 'status': row['status'],
                            'stdout_tail': record.get('stdout', '')[-3500:],
                            'stderr_tail': record.get('stderr', '')[-1800:]})
            workers.append(worker)
    result = {'schema': 'leanglish.completion-diagnostics/v1', 'workers': workers,
              'remaining': remaining, 'proof_acceptance_established': False}
    write(output/'execution-diagnostics.json', result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collections', nargs='+', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.collections, args.output)
    print('REMAINING_OBLIGATIONS', json.dumps(result['remaining'], sort_keys=True), flush=True)
    for worker in result['workers']:
        if worker['unsuccessful_checks'] or any(r.get('status') not in ('complete','reading-generated')
                                                for r in worker['proof_outcomes']):
            print('RETAINED_EXECUTION_REVIEW', json.dumps(worker, sort_keys=True), flush=True)
    print('DIAGNOSTIC_WORKERS', len(result['workers']), flush=True)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
