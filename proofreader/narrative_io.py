"""Source-bound extraction/re-extraction and offline, reproducible reading bundles.

Remote execution sends the complete submitted source to AXLE only after explicit
consent. Native elaboration can execute arbitrary metaprograms: it is NOT a
sandbox. Imported receipts are observations, never authentication credentials.
"""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import re
from typing import Any

from .core import lean_string
from .kernel import InvalidExport, require
from .kernel_io import axle_request, strict_json, _write_json
from .lean import MODULE_RE, driver_file, run_bounded
from .model import digest, report
from .narrative import Snapshot, Narrative, reading_binding, prose, check_reading
from .polynomial import verify as verify_polynomial
from .render import write_html

PREFIX = 'PR_NARRATIVE:'
MAX_BYTES = 16_000_000
VERSION = re.compile(r'4\.\d+\.\d+')


def exporter_source() -> str:
    return (Path(__file__).parent / 'data' / 'Narrative.lean').read_text(encoding='utf-8')


def extraction_source(theorem: str, *, version: str, context: str | None = None,
                      module: str | None = None, driver: str | None = None) -> str:
    require(sum(x is not None for x in (context,module,driver)) == 1, 'Supply one source context, imported module or exact driver')
    require(isinstance(theorem,str) and 0 < len(theorem) <= 2000 and '\x00' not in theorem,
            'Invalid theorem name')
    require(isinstance(version,str) and VERSION.fullmatch(version) is not None, 'An exact Lean version is required')
    exporter = exporter_source()
    marker = 'open Lean Meta Elab Command'
    require(marker in exporter, 'Missing exporter boundary')
    if driver is not None:
        require(isinstance(driver,str) and bool(driver.strip()) and len(driver.encode('utf-8')) <= MAX_BYTES, 'Invalid exact driver')
        prefix = driver
    elif module is not None:
        require(bool(MODULE_RE.fullmatch(module)), 'Unsafe module name')
        prefix = exporter.replace(marker, 'import '+module+'\n'+marker, 1)
    else:
        require(isinstance(context,str) and bool(context.strip()), 'Empty source context')
        require(len(context.encode('utf-8')) <= MAX_BYTES, 'Source context exceeds the budget')
        # Required tool imports precede, rather than substitute, the caller's
        # complete import header. No source line or existing import is dropped.
        prefix = 'import Lean\nimport Lean.Util.CollectAxioms\n'+context.rstrip()+'\n'+exporter[exporter.index(marker):]
    gate = '\nrun_elab do\n  unless Lean.versionString == '+lean_string(version)+' do\n    throwError "ProofReader exact Lean version mismatch"\n'
    return prefix+gate+('' if driver is not None else '\n#narrative '+lean_string(theorem)+'\n')


def parse_stream(stdout: str, *, theorem: str, version: str) -> Snapshot:
    require(isinstance(stdout,str) and len(stdout.encode('utf-8')) <= MAX_BYTES, 'Exporter output budget')
    records = []
    for line in stdout.splitlines():
        m = re.fullmatch(r'(?:[^\n]*?\binfo: )?'+PREFIX+r'(.*)', line)
        if m:
            records.append(Snapshot(strict_json(m[1])))
    require(len(records) == 1, 'Expected exactly one complete narrative record')
    s = records[0]
    require(s.record['theorem'] == theorem, 'Unexpected exported theorem')
    require(s.record['lean_version'] == version, 'Exact Lean version mismatch')
    return s


def response_stdout(response: dict, source: str, version: str) -> str:
    require(isinstance(response,dict) and response.get('okay') is True,
            'Lean execution did not succeed: '+str(response.get('user_error', response.get('detail','missing success')))[:500])
    require(response.get('failed_declarations') == [], 'Incomplete or disallowed declarations were reported')
    require(isinstance(response.get('content'),str) and response['content'].rstrip('\n') == source.rstrip('\n'),
            'Service changed the submitted source')
    require(response.get('info',{}).get('environment') == 'lean-'+version, 'Service used another environment')
    for field in ('lean_messages','tool_messages'):
        messages=response.get(field)
        require(isinstance(messages,dict) and messages.get('errors') == [], 'Missing or unsuccessful '+field)
    infos=response['lean_messages'].get('infos')
    require(isinstance(infos,list) and all(isinstance(x,str) for x in infos), 'Malformed Lean messages')
    return '\n'.join(infos)


def extract_narrative(theorem: str, output: Path, *, context: str | None = None,
                      module: str | None = None, version: str = '4.34.1', backend: str = 'native',
                      project: Path | None = None, trust_project: bool = False,
                      allow_remote: bool = False, timeout: float = 180,
                      expected: dict | None = None, driver: str | None = None) -> dict:
    """Expected snapshot, when given, must match fresh extraction exactly."""
    require(backend in {'native','axle'}, 'Unknown execution backend')
    if backend == 'native' and not trust_project:
        raise PermissionError('Lean elaboration runs code. Pass --trust-project only for trusted or isolated source.')
    if backend == 'axle' and not allow_remote:
        raise PermissionError('This sends the full Lean source to AXLE. Pass --allow-remote to consent.')
    require(0 < timeout <= 900, 'Invalid execution timeout')
    if backend == 'native':
        require(project is not None and project.is_dir(), 'Native extraction needs an existing --project')
    else:
        require(module is None and (context is not None or driver is not None), 'Remote extraction requires self-contained source context or exact driver')
    expected_snapshot = Snapshot(expected) if expected is not None else None
    if expected_snapshot is not None:
        require(expected_snapshot.record['theorem'] == theorem and expected_snapshot.record['lean_version'] == version,
                'Expected snapshot theorem/version mismatch')
    source = extraction_source(theorem,version=version,context=context,module=module,driver=driver)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/'Extract.lean').write_text(source,encoding='utf-8')
    if driver is not None:
        (output/'OriginalDriver.lean').write_text(driver,encoding='utf-8')
    if context is not None:
        (output/'Context.lean').write_text(context,encoding='utf-8')
    # Never leave last run's successful record at the canonical output path.
    for name in ('snapshot.json','actual-snapshot.json','receipt.json','reading.json','reader.html','coverage.json','proof.txt','polynomial-certificates.json'):
        path=output/name
        if path.is_file():path.unlink()
    receipt={'schema':'proofreader.narrative-receipt/v1','status':'failed',
             'theorem':theorem,'lean_version':version,'backend':backend,
             'source_sha256':digest(source),'context_sha256':digest(context) if context is not None else None,
             'driver_sha256':digest(driver) if driver is not None else None, 'module':module,'receipt_authenticated':False,'english_formally_verified':False,
             'exact_openai_project_replayed':False,'errors':[], 'expected_snapshot_sha256':expected_snapshot.sha256 if expected_snapshot else None}
    try:
        if backend=='axle':
            response=axle_request(source,version,allow_remote=True,timeout=timeout)
            _write_json(output/'response.json',response)
            stdout=response_stdout(response,source,version)
            receipt['service_info']=response['info']
        else:
            assert project is not None
            with driver_file(project,source) as driver_path:
                run=run_bounded(['lake','env','lean',str(driver_path)],project.resolve(),timeout=timeout)
            _write_json(output/'run.json',asdict(run))
            (output/'stderr.txt').write_text(run.stderr,encoding='utf-8')
            require(run.status=='passed' and run.exit_code==0,run.reason or 'Native Lean did not succeed')
            stdout=run.stdout
        (output/'stdout.txt').write_text(stdout,encoding='utf-8')
        snapshot=parse_stream(stdout,theorem=theorem,version=version)
        # Preserve diagnostic actual snapshot separately on a comparison failure.
        _write_json(output/'actual-snapshot.json',snapshot.record)
        if expected_snapshot is not None:
            require(snapshot.record == expected_snapshot.record,'Re-extracted snapshot differs from the supplied record')
        receipt.update(status='passed',snapshot_sha256=snapshot.sha256,
                       selected_judgements=snapshot.record['judgements_checked'],
                       snapshot_reextraction_matched=expected_snapshot is not None,
                       all_selected_judgements_kernel_checked=True,
                       path_linkage_checked_in_lean=True,
                       trust_boundary='Trusted source, imports, Lean compiler, traversal, pretty-printer, renderer, and recorded transport. No formal English guarantee.')
        write_bundle(snapshot.record,output,source=context or driver or ('import '+str(module)+'\n'),file='Context.lean',receipt=receipt)
    except (ValueError,OSError,RuntimeError,RecursionError) as exc:
        receipt['status']='failed'
        receipt['all_selected_judgements_kernel_checked']=False
        receipt['path_linkage_checked_in_lean']=False
        receipt['errors']=[str(exc)[:4000]]
        for name in ('snapshot.json','reading.json','reader.html','coverage.json','proof.txt','polynomial-certificates.json'):
            stale=output/name
            if stale.is_file():stale.unlink()
    _write_json(output/'receipt.json',receipt)
    return receipt


def write_bundle(record: dict, output: Path, *, source: str = '', file: str = 'Original.lean',
                 receipt: dict | None = None, title: str | None = None,
                 provenance_note: str | None = None) -> dict:
    n=Narrative(record)
    d=n.document(source=source,file=file,receipt=receipt,title=title,provenance_note=provenance_note)
    check_reading(record,d)
    for i,c in n.certificates.items():verify_polynomial(n.frames[i],c)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    _write_json(output/'snapshot.json',record)
    _write_json(output/'polynomial-certificates.json',list(n.certificates.values()))
    (output/'reading.json').write_text(d.to_json(),encoding='utf-8')
    (output/'proof.txt').write_text(prose(d),encoding='utf-8')
    write_html(d,output/'reader.html')
    if receipt is not None:_write_json(output/'receipt.json',receipt)
    result={**n.snapshot.coverage(),**report(d),'snapshot_sha256':n.snapshot.sha256,
            'reading_binding':reading_binding(d),'polynomial_certificates_replayed':len(n.certificates),
            'exported_frames_accounted_for':len(n.owners),'whole_corpus_coverage':False,
            'formula_backend':record['formula_backend'],'model_calls':0}
    _write_json(output/'coverage.json',result)
    return result


def verify_certificates(record: dict, certificates: list[dict]) -> None:
    s=Snapshot(record)
    require(isinstance(certificates,list) and len(certificates)<=1000,'Certificate budget')
    seen=set()
    for c in certificates:
        require(isinstance(c,dict) and type(c.get('frame_id')) is int,'Invalid certificate')
        i=c['frame_id'];require(0<=i<len(s.frames) and i not in seen,'Invalid/repeated certificate frame')
        verify_polynomial(s.frames[i],c);seen.add(i)
