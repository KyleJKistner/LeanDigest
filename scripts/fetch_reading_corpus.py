"""Fetch the pinned retained-snapshot corpus used for reading-quality measurements.

Only `proofs/<id>/snapshot.json` members of the pinned offline catalog are
extracted. The archive digest is checked before anything is read. The snapshots
are unsigned retained observations; this script does not authenticate them.
"""
from __future__ import annotations
import argparse
import hashlib
import io
from pathlib import Path
import re
import sys
import urllib.request
import zipfile

CORPUS = {
    'release': 'leanglish-original-project-317dc31',
    'url': 'https://github.com/KyleJKistner/LeanDigest/releases/download/'
           'leanglish-original-project-317dc31/leanglish-all-findings.zip',
    'sha256': '57f9e481a83ff64b7ae01e9cdf0b4b47919adf1899d28313ab3b7e7cf5be0e2b',
    'snapshots': 492,
}
MEMBER = re.compile(r'Leanglish/proofs/([0-9a-f]{24})/snapshot\.json')


def extract(archive: bytes, output: Path) -> int:
    if hashlib.sha256(archive).hexdigest() != CORPUS['sha256']:
        raise ValueError('Corpus archive digest does not match the pinned release')
    count = 0
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for name in sorted(z.namelist()):
            m = MEMBER.fullmatch(name)
            if not m:
                continue
            dest = output/m[1]/'snapshot.json'
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(name))
            count += 1
    if count != CORPUS['snapshots']:
        raise ValueError(f'Expected {CORPUS["snapshots"]} snapshots, found {count}')
    return count


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('output', type=Path, help='New directory for <id>/snapshot.json files')
    p.add_argument('--archive', type=Path, help='Use an already downloaded archive instead of the release URL')
    a = p.parse_args(argv)
    if a.output.exists() and any(a.output.iterdir()):
        raise SystemExit('Use a new or empty output directory')
    data = a.archive.read_bytes() if a.archive else urllib.request.urlopen(CORPUS['url'], timeout=300).read()
    print(f'{extract(data, a.output)} snapshots from {CORPUS["release"]}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
