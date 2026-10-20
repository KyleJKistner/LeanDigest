"""Copy pinned workflow inputs into fresh Actions artifacts and plan the repin.

Kept workflows download artifacts of earlier runs by run or artifact ID, and
Actions artifacts expire. `fetch` and `verify` run inside
.github/workflows/preserve-inputs.yml with the run token: they download one
pinned artifact, check every digest that the repository records for it, stage a
copy for upload, and compare the uploaded copy with the original. `merge` writes
the preservation record. `matrix`, `inventory` and `repin` use no network;
`repin` prints, and never applies, the edits that consumer files need.

Nothing here publishes a release, pushes, or edits a file. GH_TOKEN is consumed
by gh and never recorded. The module uses only the standard library and no
other module of this repository; the workflow's copy and record jobs run it
without installing the application, while its plan job installs the package to
run the tests (docs/INPUT_PRESERVATION.md).
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
from typing import NamedTuple
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'KyleJKistner/LeanDigest'
WORKFLOW = '.github/workflows/preserve-inputs.yml'
SCHEMA = 'leanglish.input-preservation/v1'
ITEM = 'leanglish.input-preservation-item/v1'
# The longest artifact retention a public repository allows; the record also
# reports the retention that GitHub actually applied.
RETENTION_DAYS = 90
MAX_ARCHIVE_BYTES = 2_000_000_000
MAX_ENTRIES = 25_000


class Origin(NamedTuple):
    """An artifact that consumers pin, as the Actions API listed it on 2026-10-20.

    `digest` is the SHA-256 of the artifact ZIP that GitHub reports. A 'files'
    input is copied as its extracted contents, so `gh run download -n/-p` keeps
    its layout; an 'archive' input is copied as the original ZIP bytes, so every
    digest recorded for that ZIP still applies to the restored file."""
    key: str
    name: str
    artifact_id: int
    run_id: int
    head_sha: str
    digest: str
    size: int
    expires_at: str
    layout: str
    group: str


_PROOF_RUN, _PROOF_HEAD, _PROOF_EXPIRY = 39065371645, '375219a70949f3d3e3e698bd53ad2788de132cab', '2027-01-15T20:07:21Z'
_PROOF_RETRIES = (
    (0, 12113217192, '02f764f326546dbf26f772d996f617d0847fca0850b13e7c5cf3df794ee39c20', 30930),
    (1, 12113501383, '831c8cf262480aa03c1de9ce4380b35ac235013b3a86345e326035b8e2edc7e0', 84248),
    (2, 12113845320, 'fd88cfdf0d8e53fd0898dd8e479f155bd0102b3d2ac2629b14cd918511dc76f2', 132676),
    (3, 12112224347, 'e781963498bdaca4f638a872bcdc568282a82610e29f8906dafa3e81b1510560', 3071),
    (4, 12112589633, '70a7e0dc90e3de337c6ba68bf4ce88db897f79beb7e18ea046072fb53ca18d44', 3071),
    (5, 12113915396, '149aa1f55f19e5888cb017420b15e41fbcd307a5ebe2d1334056107cf1378009', 152516),
    (6, 12112818139, 'e2f551bc3013108692c90d1a5eca8b0bf36b40843e3cb8c35d07ef71ca6c4781', 146730),
    (7, 12113237206, '97f28da21cb5eee3eb1704811649946260a8dbb72183f621608ad04f0ac56b78', 128556),
    (8, 12112334146, '54530263406de675ba6fc51e0a37a5e930bfb0e8d911680fd5863206ebcbd12d', 121321),
    (9, 12112349700, '4019ff785fbfce9a19e3c4a7ff1e31877bc73b5a730e7e2be5531ee9d0be5d5e', 76714),
    (10, 12112719847, '6fd0f6c78d8b75b5cf8ceb91d32c3e2a471cd12536206b9f433150725538ffce', 200314),
    (11, 12112189714, 'a5755f43c180561686e120fbac54f840bd7de28d87ae14419d87388cea5d96cc', 31403),
    (12, 12113520463, '3f3c055e03e6cbfaa5384eb3b5d95e3da042c9427036b24d6d5f977ca2f02228', 3070),
    (13, 12112669907, '13664fe6b3bd5a16bbf03c0a98ab803134769a7d3e06b7e142f65948e40c9717', 185219),
    (14, 12113540042, '2e20c28af3eed57a011b14fd34333a75360558917c410678a074a717009c3ca2', 3070),
    (15, 12113546144, '2e02b65f66aff9a88ccebc13f0421661bd61afa700b265d5f476f508d997c992', 77518),
)
ORIGINS = {o.key: o for o in (
    Origin('checkpoint', 'checkpoint-142c3d0f555a25666bb36dd1-1', 12217614568, 39315174445,
           '4f9c1e823dd65023cfa7d8b9afe5e08390b8d2ad',
           'f0cb3658f6edbffc2e62cd8f538ea9a7529a0e4cbe4e27286241030441003523',
           22385891, '2026-11-02T20:14:18Z', 'archive', 'checkpoint'),
    Origin('source', 'complete-openai-lean-source', 12012738377, 38822475057,
           'af04fe9b118d6d4a24c44dc03c6cbf4fe91af558',
           '4192507caa2d48023ec3d3cd8ff16d4d3b66ab8f62bc32ee358208961bdf1076',
           320755640, '2026-11-14T23:16:31Z', 'files', 'source'),
    Origin('statement-retry-CoarseAssembly', 'finding-statement-retry-CoarseAssembly', 12107274354,
           39050823104, '45a0e83670ac77031d8fb52a1f33525fb0ced448',
           '8454d0919da8807bbee04e8920abffe50650d9df16b401e00de6ebb17b293041',
           7013, '2026-11-16T16:52:30Z', 'files', 'statement-retries'),
    Origin('statement-retry-CharacterVarietiesAllSeamsSupport',
           'finding-statement-retry-CharacterVarietiesAllSeamsSupport', 12108605282,
           39050823104, '45a0e83670ac77031d8fb52a1f33525fb0ced448',
           'c0ee2f2029ab002b32aba213bd1b4024200c7353bd9c59bc66bf3d34c38d922a',
           8157, '2026-11-16T17:06:31Z', 'files', 'statement-retries'),
    Origin('observations', 'leanglish-all-finding-observations', 12107445952, 39049596449,
           'b3f691e33a5947dd4707fbd708475898b3f33e02',
           '6f0cecc148b6a002bda98ef9d015ce188214c042650a7e5b16b34211042a5a21',
           12872783, '2027-01-15T16:29:02Z', 'files', 'observations'),
    *(Origin(f'proof-retry-{shard}', f'finding-proof-retry-{shard}', ident, _PROOF_RUN, _PROOF_HEAD,
             digest, size, _PROOF_EXPIRY, 'files', 'proof-retries')
      for shard, ident, digest, size in _PROOF_RETRIES),
    Origin('breadth', 'leanglish-breadth-observations', 12116428595, 39076207515,
           '7e80297e5c25065db0373649522f5af9c615582d',
           '940e8611515acca1a7d7d2ee5552bb656175c7911dc5bf97752ca4ac2644a6c9',
           10422321, '2027-01-15T22:43:15Z', 'files', 'breadth'),
    Origin('nanoda-toolchain', 'original-nanoda-toolchain', 12152481984, 39170206904,
           '9d32ccc36c0095c81a04d68fd481a08e9f959a99',
           '869b77fe322f2394edc12aa3bf9780809424e512eccce5f45982ffde619c069a',
           98956485, '2027-01-16T21:58:59Z', 'archive', 'nanoda-toolchain'),
    Origin('completed-campaigns', 'completed-original-campaigns', 12195158110, 39270771889,
           '2744ca39a9267327453a2cfaecfeff2119c8809a',
           '4275b3fabc03eca1a4b7daa7a30121bf6b81ef1849f36f1a3392b755ad7cb5df',
           289240254, '2027-01-17T14:38:24Z', 'archive', 'completed-campaigns'),
    Origin('recovery-plan', 'validated-completion-plan', 12197582957, 39276345053,
           '58fceeaf09238c0b82aadd211f8301e8ce92f696',
           '8164869bdd4972b89c7481be210ab559493017cdf9c563e834f65362f36b4d6a',
           14615062, '2027-01-17T15:15:19Z', 'archive', 'recovery-plan'),
)}

# Digests that the repository records independently of the Actions API, with
# the files that record each. Member '' is the artifact ZIP itself; any other
# member is a file inside it. Inputs without an entry have no recorded digest:
# for them only the digest GitHub reports at copy time is checked.
W = '.github/workflows/'
RECORDED = {
    'checkpoint': (('', ORIGINS['checkpoint'].digest,
                    (W+'completion-resume.yml', 'proofreader/completion_results.py',
                     'scripts/check_original_checkpoint.py')),),
    'source': (('', ORIGINS['source'].digest, ('proofreader/dependency_cone.py',)),
               ('openai-lean-source.tar.gz', '7f596ba4fe17fe0d7d55655e6e82d99d4d87181e0a9032721c048d7385163f3c',
                ('scripts/assemble_finding_release.py',))),
    'nanoda-toolchain': (('', ORIGINS['nanoda-toolchain'].digest,
                          (W+'atomic-completion-worker.yml', W+'completion-resume.yml',
                           W+'completion-worker.yml')),),
    'completed-campaigns': (('', ORIGINS['completed-campaigns'].digest, (W+'completion-delivery.yml',)),),
    'recovery-plan': (('', ORIGINS['recovery-plan'].digest,
                       (W+'completion-delivery.yml', W+'completion-recovery.yml', W+'completion-resume.yml')),),
}

# Preserved copies that consumers download instead of the origin. `repin`
# prints the replacement for this block together with the consumer edits.
CURRENT: dict[str, dict] = {}

SETS = {
    'expiring-2026-11': ('checkpoint', 'source', 'statement-retries'),
    'checkpoint': ('checkpoint',),
    'source': ('source',),
    'statement-retries': ('statement-retries',),
    'expiring-2027-01': ('observations', 'proof-retries', 'breadth', 'nanoda-toolchain',
                         'completed-campaigns', 'recovery-plan'),
}


class Ref(NamedTuple):
    """Text in a consumer file that names a pinned artifact.

    `origin` is the text while the consumer downloads the original artifact and
    `copy`, when it differs, the text once it downloads a preserved copy. The
    pin placeholders are <RUN>, <ID>, <DIGEST>, <HEAD> and <NAME>; the origin
    placeholders are <ORIGIN_RUN>, <ORIGIN_ID>, <ORIGIN_HEAD> and
    <ORIGIN_DIGEST>. A line break continues at the indentation of the first line."""
    path: str
    origin: str
    copy: str | None = None


class Keep(NamedTuple):
    """A reference that stays unchanged after a repin, with the reason."""
    path: str
    text: str
    reason: str


PRODUCER = 'Records the run that produced the input; a copy does not change that.'
SAME_BYTES = 'Checks the original archive bytes, which the copy contains unchanged.'
ORIGINAL_IDENTITY = ('Checks the identity of the original checkpoint, which the acquisition '
                     'record keeps; the copied bytes are checked against its digest. The '
                     'record then does not name the copy that the bytes came from.')


def _gh_download(option: str) -> tuple[Ref, ...]:
    return (Ref(W+'all-findings-release.yml', f'gh run download <RUN> {option}'),
            Ref(W+'breadth-release.yml', f'gh run download <RUN> {option}'))


def _zip(path: str, destination: str) -> Ref:
    return Ref(path, f'gh api repos/$GITHUB_REPOSITORY/actions/artifacts/<ID>/zip > {destination}',
               f'gh run download <RUN> -R "$GITHUB_REPOSITORY" -n <NAME> -D /tmp/preserved/<ORIGIN_ID>\n'
               f'mv /tmp/preserved/<ORIGIN_ID>/original-<ORIGIN_ID>.zip {destination}')


def _sum(path: str, destination: str) -> Keep:
    return Keep(path, f"echo '<ORIGIN_DIGEST>  {destination}' | sha256sum -c -", SAME_BYTES)


_REMOTE = '-R "$GITHUB_REPOSITORY" '
GROUPS: dict[str, tuple[tuple[Ref, ...], tuple[Keep, ...]]] = {
    'checkpoint': ((
        Ref(W+'completion-resume.yml', "a=api(repo,'actions/artifacts/<ID>')"),
        Ref(W+'completion-resume.yml', "assert a['workflow_run']['id']==<RUN>"),
        Ref(W+'completion-resume.yml', "assert a['workflow_run']['head_sha']=='<HEAD>'"),
        Ref(W+'completion-resume.yml', "assert a['digest']=='sha256:<DIGEST>'"),
        Ref(W+'completion-resume.yml', "{'artifact_id':a['id'],'run_id':a['workflow_run']['id'],",
            "{'artifact_id':<ORIGIN_ID>,'run_id':<ORIGIN_RUN>,"),
        Ref(W+'completion-resume.yml',
            "'source_commit':a['workflow_run']['head_sha'],'archive_sha256':a['digest'].removeprefix('sha256:')})",
            "'source_commit':'<ORIGIN_HEAD>','archive_sha256':'<ORIGIN_DIGEST>'})"),
        _zip(W+'completion-resume.yml', '/tmp/acquired/checkpoint.zip'),
    ), (
        _sum(W+'completion-resume.yml', '/tmp/acquired/checkpoint.zip'),
        Keep('proofreader/completion_results.py', "acquisition != {'artifact_id':<ORIGIN_ID>, 'run_id':<ORIGIN_RUN>,",
             ORIGINAL_IDENTITY),
        Keep('scripts/check_original_checkpoint.py', "acquired.get('artifact_id') != <ORIGIN_ID> or", ORIGINAL_IDENTITY),
        Keep('tests/test_completion_resume.py', "'checkpoint_acquisition':{'artifact_id':<ORIGIN_ID>,'run_id':<ORIGIN_RUN>,",
             ORIGINAL_IDENTITY),
    )),
    'source': ((
        *_gh_download('-n complete-openai-lean-source'),
        *(Ref(W+name, 'gh run download <RUN> '+_REMOTE+'-n complete-openai-lean-source')
          for name in ('atomic-completion-worker.yml', 'completion-delivery.yml',
                       'completion-resume.yml', 'completion-worker.yml')),
        Ref(W+'dependency-cone.yml', "SOURCE_RUN: '<RUN>'"),
        Ref(W+'dependency-cone.yml', "SOURCE_ARTIFACT: '<ID>'"),
        Ref('proofreader/dependency_cone.py',
            "SOURCE_ARTIFACT = {'id': <ID>, 'name': 'complete-openai-lean-source', 'run_id': <RUN>,"),
        Ref('proofreader/dependency_cone.py', "'digest': 'sha256:<DIGEST>'}"),
        Ref('tests/test_dependency_cone.py', "meta = {'id': <ID>, 'name': 'complete-openai-lean-source', 'expired': False,"),
        Ref('tests/test_dependency_cone.py', "'workflow_run': {'id': <RUN>},"),
        Ref('tests/test_dependency_cone.py', "'digest': 'sha256:<DIGEST>'}"),
    ), (
        Keep('scripts/assemble_finding_release.py', "INPUT_RUNS={'source':<ORIGIN_RUN>,", PRODUCER),
        Keep('scripts/assemble_finding_release.py', "SOURCE_SHA256='"+RECORDED['source'][1][1]+"'",
             'Checks the source archive inside the artifact; a copy contains the same file.'),
    )),
    'statement-retries': ((
        *_gh_download("-p 'finding-statement-retry-*'"),
        Ref(W+'completion-delivery.yml', "gh run download <RUN> "+_REMOTE+"-p 'finding-statement-retry-*'"),
    ), (
        Keep('scripts/assemble_finding_release.py', "'statement_retries':<ORIGIN_RUN>,", PRODUCER),
    )),
    'observations': ((
        *_gh_download('-n leanglish-all-finding-observations'),
        Ref(W+'completion-delivery.yml', 'gh run download <RUN> '+_REMOTE+'-n leanglish-all-finding-observations'),
    ), (
        Keep('scripts/assemble_finding_release.py', "'observations':<ORIGIN_RUN>,", PRODUCER),
    )),
    'proof-retries': ((
        *_gh_download("-p 'finding-proof-retry-*'"),
    ), (
        Keep('scripts/assemble_finding_release.py', "'proof_retries':<ORIGIN_RUN>}", PRODUCER),
    )),
    'breadth': ((
        Ref(W+'breadth-release.yml', 'gh run download <RUN> -n leanglish-breadth-observations'),
    ), (
        Keep('scripts/assemble_finding_release.py', "'breadth_collection':<ORIGIN_RUN>,", PRODUCER),
    )),
    'nanoda-toolchain': ((
        _zip(W+'atomic-completion-worker.yml', '/tmp/tools.zip'),
        _zip(W+'completion-resume.yml', '/tmp/acquired/tools.zip'),
        _zip(W+'completion-worker.yml', '/tmp/tools.zip'),
    ), (
        _sum(W+'atomic-completion-worker.yml', '/tmp/tools.zip'),
        _sum(W+'completion-resume.yml', '/tmp/acquired/tools.zip'),
        _sum(W+'completion-worker.yml', '/tmp/tools.zip'),
    )),
    'completed-campaigns': ((
        _zip(W+'completion-delivery.yml', '/tmp/completed.zip'),
    ), (
        _sum(W+'completion-delivery.yml', '/tmp/completed.zip'),
    )),
    'recovery-plan': ((
        _zip(W+'completion-delivery.yml', '/tmp/plan.zip'),
        _zip(W+'completion-recovery.yml', '/tmp/recovery-plan.zip'),
        _zip(W+'completion-resume.yml', '/tmp/acquired/plan.zip'),
    ), (
        _sum(W+'completion-delivery.yml', '/tmp/plan.zip'),
        _sum(W+'completion-recovery.yml', '/tmp/recovery-plan.zip'),
        _sum(W+'completion-resume.yml', '/tmp/acquired/plan.zip'),
    )),
}
# Files that `repin` searches for leftover references to a replaced pin.
SCANNED = ('.github/workflows/*.yml', 'scripts/*.py', 'proofreader/**/*.py', 'leanglish/**/*.py', 'tests/**/*.py')
SELF = ('scripts/preserve_inputs.py', 'tests/test_preserve_inputs.py')
ARTIFACT_PLACEHOLDERS = ('<ID>', '<DIGEST>', '<NAME>', '<ORIGIN_ID>', '<ORIGIN_DIGEST>')


# Shared helpers ------------------------------------------------------------

def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def file_sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path: Path):
    return json.loads(path.read_text())


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)+'\n')


def members(group: str) -> list[Origin]:
    return [o for o in ORIGINS.values() if o.group == group]


def keys_of(name: str) -> list[str]:
    if name not in SETS:
        raise ValueError('Unknown artifact set: '+name)
    return [o.key for group in SETS[name] for o in members(group)]


def pin_of(key: str, current: dict | None = None) -> dict:
    """The artifact a consumer downloads now: the origin, or a preserved copy."""
    current = CURRENT if current is None else current
    if key in current:
        return {**current[key], 'copy': True}
    o = ORIGINS[key]
    return {'artifact_id': o.artifact_id, 'run_id': o.run_id, 'head_sha': o.head_sha,
            'digest': o.digest, 'copy': False}


def unpack(archive: Path, output: Path) -> None:
    """Reject traversal, links, duplicate paths and unexpectedly large archives."""
    if output.exists():
        raise ValueError('Extraction directories must be fresh')
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        if len(infos) > MAX_ENTRIES or sum(x.file_size for x in infos) > 3*MAX_ARCHIVE_BYTES:
            raise ValueError('Artifact expansion limit exceeded')
        seen = set()
        for item in infos:
            raw = item.filename.rstrip('/')
            p = PurePosixPath(raw)
            if (not raw or p.is_absolute() or '..' in p.parts or '\\' in raw or ':' in raw
                    or raw != p.as_posix() or raw in seen):
                raise ValueError('Unsafe or repeated artifact path: '+item.filename)
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError('Non-regular artifact entry: '+item.filename)
            seen.add(raw)
        output.mkdir(parents=True)
        for item in infos:
            target = output.joinpath(*PurePosixPath(item.filename).parts)
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(item) as src, target.open('xb') as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)


def manifest_of(root: Path) -> tuple[list[dict], list[str]]:
    """Every file with its size and digest, and the directories that hold no file."""
    files = [{'path': p.relative_to(root).as_posix(), 'bytes': p.stat().st_size, 'sha256': file_sha256(p)}
             for p in sorted(root.rglob('*')) if p.is_file()]
    empty = [p.relative_to(root).as_posix() for p in sorted(root.rglob('*'))
             if p.is_dir() and not any(q.is_file() for q in p.rglob('*'))]
    return files, empty


def content_of(files: list[dict], empty: list[str]) -> dict:
    return {'files': len(files), 'bytes': sum(f['bytes'] for f in files),
            'content_sha256': digest(files), 'empty_directories': empty}


def days_between(start: str, end: str) -> float:
    parse = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
    return round((parse(end)-parse(start)).total_seconds()/86400, 1)


# Copy: checks before upload and after upload ------------------------------

def check_metadata(meta: dict, origin: Origin, pin: dict) -> None:
    run = meta.get('workflow_run') or {}
    if meta.get('id') != pin['artifact_id'] or meta.get('name') != origin.name:
        raise ValueError('The Actions API returned a different artifact than the pin')
    if run.get('id') != pin['run_id'] or run.get('head_sha') != pin['head_sha']:
        raise ValueError('The pinned artifact belongs to another run or commit')
    if meta.get('digest') != 'sha256:'+pin['digest']:
        raise ValueError('The reported artifact digest differs from the pin')
    if meta.get('expired') is not False:
        raise ValueError('The pinned artifact has expired; it cannot be copied')
    size = meta.get('size_in_bytes')
    if type(size) is not int or not 0 < size <= MAX_ARCHIVE_BYTES or (not pin['copy'] and size != origin.size):
        raise ValueError('The artifact size is outside the recorded bound')


def stage(origin: Origin, pin: dict, meta: dict, archive: Path, work: Path) -> dict:
    """Check one downloaded artifact ZIP against its pins and stage the upload payload."""
    check_metadata(meta, origin, pin)
    if archive.stat().st_size != meta['size_in_bytes'] or file_sha256(archive) != pin['digest']:
        raise ValueError('The downloaded artifact differs from its reported digest')
    payload, checked = work/'payload', []
    if payload.exists():
        raise ValueError('Use a fresh work directory')
    inner = 'original-%d.zip' % origin.artifact_id
    if origin.layout == 'archive':
        source = archive
        if pin['copy']:
            unpack(archive, work/'content')
            found = sorted(p.relative_to(work/'content').as_posix() for p in (work/'content').rglob('*'))
            source = work/'content'/inner
            if found != [inner] or file_sha256(source) != origin.digest:
                raise ValueError('The preserved copy does not hold exactly the original archive')
        payload.mkdir(parents=True)
        shutil.move(str(source), str(payload/inner))
    else:
        unpack(archive, payload)
    for member, wanted, where in RECORDED.get(origin.key, ()):
        if member:
            path = payload.joinpath(*PurePosixPath(member).parts)
            if not path.is_file() or file_sha256(path) != wanted:
                raise ValueError('Recorded digest mismatch for '+member)
            how = 'file in the artifact'
        elif origin.layout == 'archive' or not pin['copy']:
            if wanted != origin.digest:
                raise ValueError('The recorded archive digest differs from the origin')
            how = 'original ZIP inside the copy' if pin['copy'] else 'downloaded artifact ZIP'
        else:
            how = 'not applicable to a copy; its contents are compared by content_sha256'
        checked.append({'member': member, 'sha256': wanted, 'recorded_in': list(where), 'checked_against': how})
    files, empty = manifest_of(payload)
    content = content_of(files, empty)
    if pin['copy'] and content['content_sha256'] != pin['content_sha256']:
        raise ValueError('The preserved copy differs from the contents first copied')
    write(work/'manifest.json', files)
    return {'schema': ITEM, 'status': 'fetched', 'key': origin.key, 'name': origin.name,
            'layout': origin.layout, 'group': origin.group, 'origin': origin_record(origin),
            'copied_from': {k: pin[k] for k in ('artifact_id', 'run_id', 'head_sha', 'digest')} | {
                'size_in_bytes': meta['size_in_bytes'], 'created_at': meta.get('created_at'),
                'expires_at': meta.get('expires_at'), 'is_preserved_copy': pin['copy']},
            'recorded_digests': checked, 'content': content}


def origin_record(o: Origin) -> dict:
    return {'artifact_id': o.artifact_id, 'run_id': o.run_id, 'head_sha': o.head_sha,
            'digest': o.digest, 'size_in_bytes': o.size, 'expires_at': o.expires_at}


def check_copy(fetched: dict, meta: dict, archive: Path, work: Path, *, run_id: int, head: str,
               artifact_id: int | None = None) -> dict:
    """Compare the uploaded copy, downloaded again, with the staged contents."""
    run = meta.get('workflow_run') or {}
    if (meta.get('name') != fetched['name'] or (artifact_id is not None and meta.get('id') != artifact_id) or
            run.get('id') != run_id or run.get('head_sha') != head or meta.get('expired') is not False):
        raise ValueError('The new artifact is not the upload of this run')
    reported = meta.get('digest') or ''
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', reported):
        raise ValueError('GitHub reported no digest for the new artifact')
    if archive.stat().st_size != meta.get('size_in_bytes') or 'sha256:'+file_sha256(archive) != reported:
        raise ValueError('The downloaded copy differs from its reported digest')
    unpack(archive, work/'copy')
    files, _ = manifest_of(work/'copy')
    if digest(files) != fetched['content']['content_sha256']:
        raise ValueError('The uploaded copy differs from the staged contents')
    created, expires = meta.get('created_at'), meta.get('expires_at')
    return {**fetched, 'status': 'preserved', 'round_trip_verified': True,
            'preserved': {'artifact_id': meta['id'], 'run_id': run_id, 'head_sha': head,
                          'digest': reported.removeprefix('sha256:'), 'size_in_bytes': meta['size_in_bytes'],
                          'created_at': created, 'expires_at': expires,
                          'retention_days_requested': RETENTION_DAYS,
                          'retention_days_observed': days_between(created, expires) if created and expires else None}}


def merge(name: str, records: Path, *, run_id: int, head: str) -> dict:
    keys = keys_of(name)
    found, failed = {}, []
    for path in sorted(records.glob('*.json')) if records.is_dir() else []:
        if path.name.endswith('.manifest.json'):
            continue
        item = read(path)
        key = item.get('key')
        if item.get('schema') != ITEM or key not in keys or key in found:
            raise ValueError('Unexpected or repeated item record: '+path.name)
        preserved = item.get('preserved') or {}
        if (item.get('status') == 'preserved' and item.get('round_trip_verified') is True and
                preserved.get('run_id') == run_id and preserved.get('head_sha') == head):
            found[key] = item
        else:
            failed.append({'key': key, 'stage': item.get('stage', item.get('status')), 'error': item.get('error')})
    reported = {f['key'] for f in failed}
    result = {'schema': SCHEMA, 'repository': REPOSITORY, 'workflow': WORKFLOW, 'set': name,
              'preservation_run_id': run_id, 'preservation_head_sha': head,
              'artifacts': [found[k] for k in keys if k in found], 'failed': failed,
              'missing': [k for k in keys if k not in found and k not in reported],
              'earliest_copy_expiry': min((found[k]['preserved']['expires_at'] for k in found
                                           if isinstance(found[k]['preserved'].get('expires_at'), str)), default=None),
              'release_published': False, 'consumers_repinned': False}
    result['record_sha256'] = digest(result)
    return result


# Repin: printed edits, never applied --------------------------------------

def fill(text: str, pin: dict, origin: Origin) -> str:
    values = {'<RUN>': pin['run_id'], '<ID>': pin['artifact_id'], '<DIGEST>': pin['digest'],
              '<HEAD>': pin['head_sha'], '<NAME>': origin.name, '<ORIGIN_RUN>': origin.run_id,
              '<ORIGIN_ID>': origin.artifact_id, '<ORIGIN_HEAD>': origin.head_sha,
              '<ORIGIN_DIGEST>': origin.digest}
    for placeholder, value in values.items():
        text = text.replace(placeholder, str(value))
    return text


def variant(ref: Ref, pin: dict) -> str:
    return ref.copy if pin['copy'] and ref.copy is not None else ref.origin


def locate(lines: list[str], text: str, *, whole: bool = False) -> tuple[int, int, str] | None:
    """First line index, line count and indent of the single occurrence of `text`.

    With `whole`, the first line must be an entire unindented line."""
    first, *rest = text.split('\n')
    hits = [i for i, line in enumerate(lines) if (line == first if whole else first in line)]
    if len(hits) != 1:
        return None
    i = hits[0]
    indent = lines[i][:len(lines[i])-len(lines[i].lstrip())]
    if lines[i+1:i+1+len(rest)] != [indent+r for r in rest]:
        return None
    return i, 1+len(rest), indent


def render_current(current: dict) -> str:
    if not current:
        return 'CURRENT: dict[str, dict] = {}'
    rows = ['    %r: {%s},' % (key, ', '.join('%r: %r' % (k, current[key][k]) for k in
            ('artifact_id', 'run_id', 'head_sha', 'digest', 'content_sha256'))) for key in sorted(current)]
    return 'CURRENT: dict[str, dict] = {\n'+'\n'.join(rows)+'\n}'


def _identifier(value) -> bool:
    return type(value) is int and value > 0


def _hex(value, length: int) -> bool:
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{%d}' % length, value) is not None


def _well_formed_copy(item) -> bool:
    preserved = item.get('preserved') if isinstance(item, dict) else None
    content = item.get('content') if isinstance(item, dict) else None
    return (isinstance(preserved, dict) and isinstance(content, dict) and
            _identifier(preserved.get('artifact_id')) and _hex(preserved.get('digest'), 64) and
            isinstance(preserved.get('expires_at'), str) and _hex(content.get('content_sha256'), 64) and
            isinstance(content.get('empty_directories'), list))


def check_record(record: dict, current: dict) -> None:
    if record.get('schema') != SCHEMA or record.get('record_sha256') != digest(
            {k: v for k, v in record.items() if k != 'record_sha256'}):
        raise ValueError('Not an unchanged preservation record')
    if record.get('repository') != REPOSITORY or record.get('workflow') != WORKFLOW:
        raise ValueError('The record comes from another repository or workflow')
    # Repin prints these values into workflow, Python and test text; anything
    # but plain identifiers and digests is refused rather than quoted.
    if not isinstance(record.get('set'), str) or record['set'] not in SETS:
        raise ValueError('The record names an unknown or malformed artifact set')
    if not (_identifier(record.get('preservation_run_id')) and _hex(record.get('preservation_head_sha'), 40)):
        raise ValueError('The record names a malformed preservation run or commit')
    if not all(_well_formed_copy(item) for item in record.get('artifacts') or []):
        raise ValueError('The record holds a malformed copy identity')
    if record.get('failed') or record.get('missing') or not record.get('artifacts'):
        raise ValueError('The preservation run did not copy every selected artifact')
    keys = [a['key'] for a in record['artifacts']]
    if len(keys) != len(set(keys)) or any(k not in ORIGINS for k in keys):
        raise ValueError('Unknown or repeated artifact in the record')
    for item in record['artifacts']:
        o, pin = ORIGINS[item['key']], pin_of(item['key'], current)
        if item.get('status') != 'preserved' or item.get('round_trip_verified') is not True:
            raise ValueError('An artifact copy was not verified: '+o.key)
        if item['origin'] != origin_record(o) or item['name'] != o.name or item['layout'] != o.layout:
            raise ValueError('The record describes a different origin: '+o.key)
        if {k: item['copied_from'][k] for k in ('artifact_id', 'run_id', 'head_sha', 'digest')} != \
                {k: pin[k] for k in ('artifact_id', 'run_id', 'head_sha', 'digest')}:
            raise ValueError('The record copied %s from another pin than consumers use now' % o.key)
        if (item['preserved']['run_id'] != record['preservation_run_id'] or
                item['preserved']['head_sha'] != record['preservation_head_sha']):
            raise ValueError('An artifact copy belongs to another run: '+o.key)


def plan_repin(record: dict, root: Path = ROOT, current: dict | None = None) -> dict:
    """The edits that point consumers at the copies in `record`, without applying them."""
    current = CURRENT if current is None else current
    check_record(record, current)
    copies = {a['key']: a for a in record['artifacts']}
    groups = sorted({ORIGINS[k].group for k in copies})
    texts: dict[str, list[str]] = {}
    def lines_of(path: str) -> list[str] | None:
        if path not in texts:
            p = root/path
            texts[path] = p.read_text().split('\n') if p.is_file() else None
        return texts[path]
    edits, unchanged, missing, notes, tokens = [], [], [], [], []
    covered: dict[str, set[int]] = {}
    new_current = dict(current)
    for group in groups:
        group_members = members(group)
        if any(o.key not in copies for o in group_members):
            raise ValueError('The record holds only part of the %s group' % group)
        olds = [pin_of(o.key, current) for o in group_members]
        news = [{'artifact_id': copies[o.key]['preserved']['artifact_id'], 'run_id': record['preservation_run_id'],
                 'head_sha': record['preservation_head_sha'], 'digest': copies[o.key]['preserved']['digest'],
                 'content_sha256': copies[o.key]['content']['content_sha256'], 'copy': True} for o in group_members]
        if len({(p['run_id'], p['head_sha']) for p in olds}) != 1:
            raise ValueError('Members of %s are pinned to different runs' % group)
        for o, new in zip(group_members, news):
            new_current[o.key] = {k: new[k] for k in ('artifact_id', 'run_id', 'head_sha', 'digest', 'content_sha256')}
            tokens.append((str(pin_of(o.key, current)['artifact_id']), group))
            if copies[o.key]['content']['empty_directories']:
                notes.append('%s: empty directories are not preserved: %s' % (
                    o.key, ', '.join(copies[o.key]['content']['empty_directories'])))
        if group_members[0].layout == 'files':
            tokens.append((str(olds[0]['run_id']), group))
        refs, keeps = GROUPS[group]
        origin, old, new = group_members[0], olds[0], news[0]
        for ref in refs:
            before, after = fill(variant(ref, old), old, origin), fill(variant(ref, new), new, origin)
            lines = lines_of(ref.path)
            spot = locate(lines, before) if lines is not None else None
            if spot is None:
                missing.append({'path': ref.path, 'text': before})
                continue
            i, count, indent = spot
            first, *rest = after.split('\n')
            changed = [lines[i].replace(before.split('\n')[0], first)]+[indent+r for r in rest]
            span = set(range(i, i+count))
            if span & covered.get(ref.path, set()):
                raise ValueError('Two references edit the same line of '+ref.path)
            covered.setdefault(ref.path, set()).update(span)
            if changed != lines[i:i+count]:
                edits.append({'path': ref.path, 'line': i+1, 'old': lines[i:i+count], 'new': changed, 'group': group})
        for keep in keeps:
            text = fill(keep.text, old, origin)
            lines = lines_of(keep.path)
            spot = locate(lines, text) if lines is not None else None
            if spot is None:
                notes.append('%s: the unchanged reference was not found: %s' % (keep.path, text))
                continue
            covered.setdefault(keep.path, set()).add(spot[0])
            unchanged.append({'path': keep.path, 'line': spot[0]+1, 'text': lines[spot[0]].strip(),
                              'reason': keep.reason, 'group': group})
    # References of inputs outside this record stay as they are; knowing them
    # keeps a run ID that several inputs share from reading as unhandled.
    for group in sorted(set(GROUPS)-set(groups)):
        origin = members(group)[0]
        pin = pin_of(origin.key, current)
        for path, text in ([(r.path, variant(r, pin)) for r in GROUPS[group][0]] +
                           [(k.path, k.text) for k in GROUPS[group][1]]):
            lines = lines_of(path)
            spot = locate(lines, fill(text, pin, origin)) if lines is not None else None
            if spot is not None:
                covered.setdefault(path, set()).update(range(spot[0], spot[0]+spot[1]))
    block = 'scripts/preserve_inputs.py'
    lines = lines_of(block)
    before, after = render_current(current), render_current(new_current)
    spot = locate(lines, before, whole=True) if lines is not None else None
    if spot is None:
        missing.append({'path': block, 'text': before})
    else:
        edits.append({'path': block, 'line': spot[0]+1, 'old': lines[spot[0]:spot[0]+spot[1]],
                      'new': after.split('\n'), 'group': 'CURRENT'})
    unclassified = []
    for pattern in SCANNED:
        for path in sorted(root.glob(pattern)):
            rel = path.relative_to(root).as_posix()
            if rel in SELF or not path.is_file():
                continue
            for n, line in enumerate(lines_of(rel) or []):
                for token, group in tokens:
                    if re.search(r'(?<![0-9])%s(?![0-9])' % token, line) and n not in covered.get(rel, set()):
                        unclassified.append({'path': rel, 'line': n+1, 'text': line.strip(), 'token': token,
                                             'group': group})
    edits.sort(key=lambda e: (e['path'], e['line']))
    return {'preservation_run_id': record['preservation_run_id'], 'set': record['set'], 'groups': groups,
            'edits': edits, 'unchanged': sorted(unchanged, key=lambda u: (u['path'], u['line'])),
            'missing': missing, 'unclassified': unclassified, 'notes': notes, 'current': new_current,
            'earliest_copy_expiry': record['earliest_copy_expiry']}


def format_plan(plan: dict) -> str:
    out = ['Repin plan for preservation run %d (set %s). Nothing has been changed.' % (
        plan['preservation_run_id'], plan['set']), '']
    if plan['missing'] or plan['unclassified']:
        out.append('This plan is incomplete. Resolve every item below before editing any file.')
        out += ['  not found in %s: %s' % (m['path'], m['text']) for m in plan['missing']]
        out += ['  unhandled reference %s:%d (%s): %s' % (u['path'], u['line'], u['token'], u['text'])
                for u in plan['unclassified']]
        out.append('')
    path = None
    for edit in plan['edits']:
        if edit['path'] != path:
            path = edit['path']
            out.append(path)
        out.append('  line %d' % edit['line'])
        out += ['  - '+line for line in edit['old']]+['  + '+line for line in edit['new']]
    if plan['unchanged']:
        out += ['', 'Unchanged references:']
        out += ['  %s:%d  %s\n    %s' % (u['path'], u['line'], u['text'], u['reason']) for u in plan['unchanged']]
    if plan['notes']:
        out += ['', 'Notes:']+['  '+n for n in plan['notes']]
    out += ['', 'Apply these edits in one reviewed commit on every branch that triggers a consumer, and copy',
            'the preservation record to artifacts/input-preservation/%d.json in the same commit.' % plan['preservation_run_id'],
            'The copies expire from %s; dispatch preserve-inputs.yml again before then.' % plan['earliest_copy_expiry']]
    return '\n'.join(out)


def inventory() -> str:
    """The Markdown table of pinned inputs in docs/INPUT_PRESERVATION.md."""
    rows = ['| Artifact (ID) | Run | Bytes | Expires (UTC) | Digest recorded in | Downloaded by | Set |',
            '| --- | --- | ---: | --- | --- | --- | --- |']
    for group in dict.fromkeys(o.group for o in sorted(ORIGINS.values(), key=lambda o: (o.expires_at, o.key))):
        found = members(group)
        refs = GROUPS[group][0]
        users = ', '.join('`%s`' % p.rsplit('/', 1)[-1] for p in sorted({r.path for r in refs if r.path.startswith(W)}))
        sets = ', '.join('`%s`' % s for s in SETS if group in SETS[s])
        recorded = ', '.join(sorted({'`%s`' % path.rsplit('/', 1)[-1] for o in found
                                     for _, _, where in RECORDED.get(o.key, ()) for path in where})) or 'None'
        if len(found) == 1:
            label = '`%s` (%d)' % (found[0].name, found[0].artifact_id)
        else:
            stem = found[0].name.rsplit('-', 1)[0]
            label = '`%s-*` (%d artifacts)' % (stem, len(found))
        expiry = min(o.expires_at for o in found)
        rows.append('| %s | %d | %s | %s | %s | %s | %s |' % (
            label, found[0].run_id, format(sum(o.size for o in found), ','), expiry[:16].replace('T', ' '),
            recorded, users, sets))
    return '\n'.join(rows)


# Command line ---------------------------------------------------------------

def api(path: str):
    run = subprocess.run(['gh', 'api', f'repos/{REPOSITORY}/{path}'], capture_output=True, text=True,
                         timeout=180, check=True)
    return json.loads(run.stdout)


def download(artifact_id: int, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as out:
        subprocess.run(['gh', 'api', f'repos/{REPOSITORY}/actions/artifacts/{artifact_id}/zip'],
                       stdout=out, stderr=subprocess.PIPE, timeout=1800, check=True)


def fail(work: Path, key: str, step: str, exc: Exception) -> int:
    write(work/'record'/(key+'.json'), {'schema': ITEM, 'key': key, 'status': 'failed', 'stage': step,
                                        'error': str(exc)})
    print('PRESERVATION_FAILED', key, step, exc, file=sys.stderr, flush=True)
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('mode', choices=['matrix', 'fetch', 'verify', 'merge', 'repin', 'inventory'])
    p.add_argument('--set', dest='name', help='matrix, merge: an artifact set from SETS')
    p.add_argument('--key', help='fetch, verify: one artifact key from ORIGINS')
    p.add_argument('--work', type=Path, help='fetch, verify: the work directory of one artifact')
    p.add_argument('--artifact-id', type=lambda v: int(v) if v else None,
                   help='verify: the ID that upload-artifact reported')
    p.add_argument('--run-id', type=int, help='verify, merge: this preservation run')
    p.add_argument('--head', help='verify, merge: the commit of this preservation run')
    p.add_argument('--records', type=Path, help='merge: the downloaded item records')
    p.add_argument('--output', type=Path, help='merge: the preservation record to write')
    p.add_argument('--record', type=Path, help='repin: a preservation record')
    p.add_argument('--root', type=Path, default=ROOT, help='repin: the checkout whose files are read')
    p.add_argument('--json', action='store_true', help='repin: print the plan as JSON')
    p.add_argument('--github-output', type=Path, help='matrix: append the matrix to this file')
    p.add_argument('--allow-download', action='store_true', help='fetch, verify: permit artifact downloads')
    a = p.parse_args(argv)
    if a.mode == 'inventory':
        print(inventory())
        return 0
    if a.mode == 'matrix':
        # A ZIP is stored without recompression; extracted contents use the default level.
        matrix = {'include': [{'key': k, 'name': ORIGINS[k].name, 'level': 0 if ORIGINS[k].layout == 'archive' else 6}
                              for k in keys_of(a.name or '')]}
        text = json.dumps(matrix, separators=(',', ':'))
        if a.github_output:
            with a.github_output.open('a') as out:
                out.write('matrix='+text+'\n'+'count=%d\n' % len(matrix['include']))
        print(text)
        return 0
    if a.mode == 'repin':
        if a.record is None:
            p.error('repin requires --record')
        try:
            plan = plan_repin(read(a.record), a.root)
        except ValueError as exc:
            print('REPIN_REFUSED', exc, file=sys.stderr)
            return 1
        print(json.dumps(plan, indent=2, sort_keys=True) if a.json else format_plan(plan))
        return 1 if plan['missing'] or plan['unclassified'] else 0
    if a.mode == 'merge':
        if not (a.name and a.records and a.output and a.run_id and a.head):
            p.error('merge requires --set, --records, --output, --run-id and --head')
        result = merge(a.name, a.records, run_id=a.run_id, head=a.head)
        write(a.output, result)
        for path in sorted(a.records.glob('*.manifest.json')) if a.records.is_dir() else []:
            target = a.output.parent/'manifests'/path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        print('PRESERVATION_RECORD', json.dumps({k: result[k] for k in ('set', 'missing', 'failed',
              'earliest_copy_expiry')}), flush=True)
        return 1 if result['failed'] or result['missing'] else 0
    if not a.allow_download:
        p.error(a.mode+' requires --allow-download')
    if a.key not in ORIGINS or a.work is None:
        p.error(a.mode+' requires a known --key and --work')
    origin = ORIGINS[a.key]
    if a.mode == 'fetch':
        try:
            if a.work.exists():
                raise ValueError('Use a fresh work directory')
            pin = pin_of(a.key)
            meta = api(f'actions/artifacts/{pin["artifact_id"]}')
            check_metadata(meta, origin, pin)
            download(pin['artifact_id'], a.work/'download.zip')
            fetched = stage(origin, pin, meta, a.work/'download.zip', a.work)
            (a.work/'download.zip').unlink(missing_ok=True)
            write(a.work/'fetched.json', fetched)
        except Exception as exc:
            return fail(a.work, a.key, 'fetch', exc)
        print('PRESERVATION_FETCHED', json.dumps(fetched['content']), flush=True)
        return 0
    try:
        if not (a.run_id and a.head and re.fullmatch(r'[0-9a-f]{40}', a.head)):
            raise ValueError('verify requires --run-id and a full --head commit')
        fetched = read(a.work/'fetched.json')
        listed = api(f'actions/runs/{a.run_id}/artifacts?name={origin.name}&per_page=100')['artifacts']
        if len(listed) != 1:
            raise ValueError('Expected exactly one new artifact named '+origin.name)
        download(listed[0]['id'], a.work/'copy.zip')
        item = check_copy(fetched, listed[0], a.work/'copy.zip', a.work, run_id=a.run_id, head=a.head,
                          artifact_id=a.artifact_id)
        write(a.work/'record'/(a.key+'.json'), item)
        shutil.copyfile(a.work/'manifest.json', a.work/'record'/(a.key+'.manifest.json'))
    except Exception as exc:
        return fail(a.work, a.key, 'verify', exc)
    print('PRESERVATION_VERIFIED', json.dumps(item['preserved']), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
