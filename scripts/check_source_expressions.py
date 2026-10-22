#!/usr/bin/env python3
"""Export source expressions and replay them in a fresh pinned Lean process.

This gate executes trusted Lean project code. It records failures and requires
--trust-project. The core suite is a structural regression sample, not the fixed
OpenAI corpus cohort. Optional Bezout checking uses the disclosed import adapter.
No output from this gate certifies English or authenticates a hostile runtime.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from proofreader.source_expressions import Expressions
from proofreader.model import canonical_json, digest as content_digest

MODULES = ('KernelExport.lean', 'JsonReplay.lean', 'Narrative.lean',
           'SourceExpressions.lean', 'SourceExpressionsFixtures.lean')
FIXTURES = ('dependent', 'witness', 'localFact', 'shadow', 'twoProofs',
            'localApplication', 'implicitInstance', 'localDefinitions', 'branches',
            'quantified', 'proofDefinition', 'hiddenDependency', 'siblingNames', 'sharedBinderNodes')
LIBRARY = ('Nat.add_assoc', 'Nat.add_comm', 'Nat.mul_assoc', 'Nat.mul_comm',
           'Nat.add_left_cancel', 'Nat.mul_zero', 'Nat.zero_mul', 'List.append_assoc',
           'List.length_append', 'List.map_append', 'List.map_map', 'List.reverse_reverse',
           'And.comm', 'and_assoc', 'Or.comm', 'or_assoc', 'Iff.symm', 'Iff.trans',
           'Classical.not_not', 'Classical.em')
TARGETS = tuple('SourceExpressionsFixtures.' + n for n in FIXTURES) + LIBRARY
COMMON = '''import SourceExpressions
import SourceExpressionsFixtures
import Narrative
{extra}
open Lean Meta Elab Command ProofReader.SourceExpressions
set_option maxHeartbeats 10000000
set_option maxRecDepth 10000
'''


def named(text: str) -> dict:
    result: dict = {'tag': 'anonymous'}
    for part in text.split('.'):
        if not part or not (part.replace('_', '').isalnum() and not part[0].isdigit()):
            raise ValueError('Expected a simple dotted declaration name')
        result = {'tag': 'str', 'prefix': result, 'value': part}
    return result


def file_digest(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def export_driver(extra: str, directory: str) -> str:
    return COMMON.format(extra=extra) + '''run_elab do
  let input ← Replay.liftJ <| Json.parse (← IO.FS.readFile "targets.json")
  let targets ← Replay.arr input
  let output := DIRECTORY
  IO.FS.createDirAll output
  for k in [:targets.size] do
    let target ← Replay.liftJ <| ProofReaderJsonReplay.name targets[k]!
    let snap ← ProofReaderNarrative.exportOne target
    let paths ← (← Replay.arr (← Replay.field snap "frames")).mapM
      (fun row => do return ← Replay.nums (← Replay.field row "path"))
    let record ← exportOne target paths
    IO.FS.writeFile (output ++ "/" ++ toString k ++ ".json") record.compress
    IO.FS.writeFile (output ++ "/" ++ toString k ++ ".snapshot.json") snap.compress
  logInfo "SOURCE_EXPRESSION_EXPORT_COMPLETE"
'''.replace('DIRECTORY', json.dumps(directory))


def replay_driver(extra: str, requests: str) -> str:
    return COMMON.format(extra=extra) + '''run_elab do
  let input ← Replay.liftJ <| Json.parse (← IO.FS.readFile REQUESTS)
  let requests ← Replay.arr input
  let mut results : Array Json := #[]
  for req in requests do
    let target ← Replay.liftJ <| ProofReaderJsonReplay.name (← Replay.field req "name")
    let paths ← (← Replay.arr (← Replay.field req "paths")).mapM
      (fun j => do return ← Replay.nums j)
    let filename ← Replay.str (← Replay.field req "file")
    let record ← Replay.liftJ <| Json.parse (← IO.FS.readFile filename)
    let snapshotFile ← Replay.str (← Replay.field req "snapshot_file")
    let snapshot ← Replay.liftJ <| Json.parse (← IO.FS.readFile snapshotFile)
    let freshSnapshot ← ProofReaderNarrative.exportOne target
    Replay.equalJson snapshot freshSnapshot "Snapshot source replay mismatch"
    let count ← Replay.verify record target paths
    results := results.push <| Json.mkObj [("name", ProofReaderKernel.nameJson target),
      ("frames", toJson paths.size), ("kernel_judgements", toJson count)]
  IO.FS.writeFile "replayed.json" (Json.arr results).compress
  logInfo "SOURCE_EXPRESSION_REPLAY_COMPLETE"
'''.replace('REQUESTS', json.dumps(requests))


def extraction_driver(extra: str) -> str:
    return COMMON.format(extra=extra) + r'''run_elab do
  let input ← Replay.liftJ <| Json.parse (← IO.FS.readFile "requests.json")
  let requests ← Replay.arr input
  let mut results : Array Json := #[]
  for req in requests do
    let target ← Replay.liftJ <| ProofReaderJsonReplay.name (← Replay.field req "name")
    let paths ← (← Replay.arr (← Replay.field req "paths")).mapM
      (fun j => do return ← Replay.nums j)
    let filename ← Replay.str (← Replay.field req "file")
    let record ← Replay.liftJ <| Json.parse (← IO.FS.readFile filename)
    let es ← Replay.decode record
    let frames ← Replay.arr (← Replay.field record "frames")
    for k in [:paths.size] do
      let expected ← Replay.getExpr es (← Replay.field frames[k]! "lifted_type")
      let destination := Name.str `ExtractedSource ("lemma_" ++ toString results.size)
      let result ← extractAt target paths[k]! destination expected
      results := results.push result
  IO.FS.writeFile "extracted.json" (Json.arr results).compress
  logInfo "SOURCE_EXPRESSION_EXTRACTION_COMPLETE"
'''


def negative_driver(extra: str) -> str:
    return COMMON.format(extra=extra) + r'''run_elab do
  let input ← Replay.liftJ <| Json.parse (← IO.FS.readFile "negative-cases.json")
  let cases ← Replay.arr input
  let mut results : Array Json := #[]
  for c in cases do
    let label ← Replay.str (← Replay.field c "label")
    let expected ← Replay.str (← Replay.field c "expected_error")
    let req ← Replay.field c "request"
    let target ← Replay.liftJ <| ProofReaderJsonReplay.name (← Replay.field req "name")
    let paths ← (← Replay.arr (← Replay.field req "paths")).mapM
      (fun j => do return ← Replay.nums j)
    let filename ← Replay.str (← Replay.field req "file")
    let record ← Replay.liftJ <| Json.parse (← IO.FS.readFile filename)
    let outcome ← try
        let _ ← Replay.verify record target paths
        pure (none : Option String)
      catch error => pure (some (← error.toMessageData.toString))
    let some message := outcome | throwError "Mutation accepted: {label}"
    unless (message.splitOn expected).length > 1 do
      throwError "Wrong rejection for {label}: {message}"
    results := results.push <| Json.mkObj [("label",toJson label),("diagnostic",toJson message)]
  let bypass ← try
      withOptions (fun o => o.setBool `debug.skipKernelTC true) do
        Replay.kernelCheck [] #[] (mkConst `True.intro) (mkConst `False)
      pure (none : Option String)
    catch error => pure (some (← error.toMessageData.toString))
  let some message := bypass | throwError "Kernel bypass accepted"
  unless (message.splitOn "(kernel) declaration type mismatch").length > 1 do
    throwError "Wrong kernel bypass rejection: {message}"
  results := results.push <| Json.mkObj [("label",toJson "kernel-bypass"),("diagnostic",toJson message)]
  let badType ← try
      let _ ← extractAt `SourceExpressionsFixtures.twoProofs #[] `RejectedSourceLemma (mkConst `False)
      pure (none : Option String)
    catch error => pure (some (← error.toMessageData.toString))
  let some badTypeMessage := badType | throwError "Invalid extraction type accepted"
  unless (badTypeMessage.splitOn "Extracted lemma type mismatch").length > 1 do
    throwError "Wrong extraction rejection: {badTypeMessage}"
  if (← getEnv).contains `RejectedSourceLemma then throwError "Failed extraction changed the environment"
  results := results.push <| Json.mkObj [("label",toJson "extraction-type"),("diagnostic",toJson badTypeMessage)]
  let overwrite ← try
      let _ ← extractAt `SourceExpressionsFixtures.twoProofs #[] `SourceExpressionsFixtures.twoProofs (mkConst `False)
      pure (none : Option String)
    catch error => pure (some (← error.toMessageData.toString))
  let some overwriteMessage := overwrite | throwError "Existing declaration overwritten"
  unless (overwriteMessage.splitOn "Extraction name already exists").length > 1 do
    throwError "Wrong overwrite rejection: {overwriteMessage}"
  results := results.push <| Json.mkObj [("label",toJson "extraction-overwrite"),("diagnostic",toJson overwriteMessage)]
  IO.FS.writeFile "rejected.json" (Json.arr results).compress
  logInfo "SOURCE_EXPRESSION_REJECTIONS_COMPLETE"
'''


def mutations(records: dict[str, dict]) -> list[tuple[str, str, dict, str]]:
    """Mutate actual exported records; replay still expects the original request."""
    tests: list[tuple[str, str, dict, str]] = []
    name = 'SourceExpressionsFixtures.'
    def edit(label, target, change, error):
        r = deepcopy(records[name + target])
        change(r)
        tests.append((label, name + target, r, error))
    def last(r): return r['frames'][-1]
    def app(r): return next(f['application'] for f in r['frames'] if f['application'])
    def first_context(r): return next(f['context'] for f in r['frames'] if f['context'])
    edit('wrong-target', 'twoProofs', lambda r: r.update(name=named('SourceExpressionsFixtures.shadow')), 'Source declaration mismatch')
    edit('wrong-version', 'twoProofs', lambda r: r.update(lean_version='0.0.0'), 'Toolchain mismatch')
    edit('extra-top-field', 'twoProofs', lambda r: r.update(english_certified=True), 'Unexpected or missing expression-record fields')
    edit('lost-universe', 'witness', lambda r: r.update(levels=[]), 'Universe inventory mismatch')
    edit('invented-axiom', 'twoProofs', lambda r: r.update(axioms=['sorryAx']), 'Axiom inventory mismatch')
    edit('missing-frame', 'twoProofs', lambda r: r['frames'].pop(), 'Requested frame inventory mismatch')
    edit('swapped-frames', 'twoProofs', lambda r: r['frames'].reverse(), 'Requested source path mismatch')
    edit('wrong-path', 'twoProofs', lambda r: last(r).update(path=[]), 'Requested source path mismatch')
    edit('scope-escape', 'twoProofs', lambda r: last(r)['context'].pop(), 'Source context length mismatch')
    edit('binder-origin', 'twoProofs', lambda r: last(r)['context'][-1].update(path=[]), 'Source binder identity mismatch')
    edit('binder-name', 'twoProofs', lambda r: first_context(r)[0].update(name=named('wrong')), 'Source binder label mismatch')
    edit('binder-annotation', 'twoProofs', lambda r: first_context(r)[0].update(binder='instance'), 'Source binder annotation mismatch')
    edit('same-type-wrong-reference', 'twoProofs', lambda r: last(r).update(reference=1), 'Local reference identity mismatch')
    edit('lost-proof-dependency', 'hiddenDependency', lambda r: last(r).update(proof_support=[]), 'Source proof dependencies mismatch')
    edit('lost-claim-dependency', 'dependent', lambda r: last(r).update(claim_support=[]), 'Source claim dependencies mismatch')
    edit('lost-type-dependency', 'dependent', lambda r: last(r).update(required_context=last(r)['required_context'][1:]), 'Dependency closure mismatch')
    edit('lost-definition-dependencies', 'hiddenDependency', lambda r: last(r).update(required_context=[1,4]), 'Dependency closure mismatch')
    def drop_value(r):
        c = next(c for f in r['frames'] for c in f['context'] if c['value'] is not None)
        c['value'] = None
    edit('definition-as-hypothesis', 'hiddenDependency', drop_value, 'Invalid expression record')
    def nondep(r):
        c = next(c for f in r['frames'] for c in f['context'] if c['value'] is not None)
        c['nondep'] = not c['nondep']
    edit('definition-flag', 'hiddenDependency', nondep, 'Let dependency flag mismatch')
    edit('claim-display', 'twoProofs', lambda r: last(r)['display'].update(claim='False'), 'Claim display mismatch')
    edit('lifted-display', 'twoProofs', lambda r: last(r)['display'].update(lifted='False'), 'Lifted display mismatch')
    edit('term-kind', 'twoProofs', lambda r: last(r).update(term_kind='app'), 'Source term kind mismatch')
    edit('omit-proof-argument', 'localApplication', lambda r: app(r)['arguments'].pop(), 'Application argument inventory mismatch')
    edit('application-head', 'localApplication', lambda r: app(r).update(local=0), 'Application local identity mismatch')
    edit('argument-path', 'localApplication', lambda r: app(r)['arguments'][0].update(path=[]), 'Application argument path mismatch')
    edit('argument-order', 'witness', lambda r: app(r)['arguments'][0].update(index=1), 'Application argument order mismatch')
    edit('proof-as-data', 'localApplication', lambda r: app(r)['arguments'][0].update(is_proof=False), 'Argument proof/data classification mismatch')
    def false_claim(r):
        r['exprs'].append({'tag':'const','name':named('False'),'levels':[]})
        last(r)['type'] = len(r['exprs'])-1
    edit('false-claim', 'twoProofs', false_claim, 'Source expression identity mismatch')
    def unrelated_true_claim(r):
        r['exprs'].append({'tag':'const','name':named('True'),'levels':[]})
        last(r)['type']=len(r['exprs'])-1
    edit('unrelated-true-claim', 'twoProofs', unrelated_true_claim, 'Source expression identity mismatch')
    def wrong_witness(r):
        assert app(r)['constant']==named('Exists.intro')
        app(r)['arguments'][2]['value'] = r['statement']
    edit('wrong-witness', 'witness', wrong_witness, 'Source expression identity mismatch')
    def wrong_lift(r): last(r)['lifted_type'] = r['statement']
    edit('wrong-lifted-type', 'dependent', wrong_lift, 'Source expression identity mismatch')
    def altered_binder(r):
        n = next(n for n in r['exprs'] if n['tag']=='forall')
        n['name'] = named('differentLabel')
    edit('alpha-equivalent-label', 'siblingNames', altered_binder, 'Source expression identity mismatch')
    def altered_annotation(r):
        n = next(n for n in r['exprs'] if n['tag']=='forall')
        n['binder'] = 'implicit'
    edit('alpha-equivalent-annotation', 'siblingNames', altered_annotation, 'Source expression identity mismatch')
    edit('extra-expression-field', 'twoProofs', lambda r: r['exprs'][0].update(certificate=True), 'Unexpected or missing expression-record fields')
    edit('wrong-expression-constructor', 'twoProofs', lambda r: r['exprs'][0].update(tag='fvar'), 'Unknown expression constructor')
    return tests


def expected_count(record: dict) -> int:
    return 1 + sum(2 + (len(f['application']['arguments']) + 1 if f['application'] else 0)
                   for f in record['frames'])


def run_gate(binary: str, output: Path, project: Path | None, archive: Path | None) -> dict:
    report = {'schema':'leanglish.source-expression-observation/v1', 'status':'failed',
              'commands':[], 'english_certified':False, 'original_project_replayed':False,
              'observations_authenticated':False, 'fixed_openai_cohort_checked':False}
    write_json(output/'observation.json', report)
    try:
        found = shutil.which(binary)
        if not found: raise ValueError('Lean executable unavailable')
        binary = str(Path(found).resolve())
        report['invoked_executable_sha256'] = file_digest(Path(binary))
        report['module_sha256'] = {n:file_digest(ROOT/'lean'/n) for n in MODULES}
        report['gate_sha256'] = file_digest(Path(__file__))
        report['python_checker_sha256'] = file_digest(ROOT/'proofreader/source_expressions.py')
        extra, names = '', list(TARGETS)
        original = None
        if project is not None:
            from scripts.check_source_cancellation import check_project, SOURCE, SOURCE_SHA, UPSTREAM, TARGET
            report['environment'] = check_project(project, archive)
            source = ROOT/SOURCE
            if file_digest(source) != SOURCE_SHA: raise ValueError('Original Bezout source changed')
            header = 'import OAI.Algebra.AffineCancellation.Model\n'
            original = source.read_text(encoding='utf-8')
            if not original.startswith(header): raise ValueError('Unexpected original import header')
            original = original.replace(header,'import Mathlib.Algebra.EuclideanDomain.Basic\nimport Mathlib.Tactic.Ring\n',1)
            report['original_source'] = {'sha256':SOURCE_SHA, 'upstream_commit':UPSTREAM,
                                         'import_adaptation':True, 'adapted_sha256':content_digest(original)}
            names += [TARGET]; extra = 'import OriginalBezout'
        report['targets'] = names
        with tempfile.TemporaryDirectory(prefix='leanglish-expressions-') as temporary:
            work = Path(temporary)
            for n in MODULES: shutil.copyfile(ROOT/'lean'/n,work/n)
            search = [work]
            if project:
                search += [project/'.lake/build/lib/lean', *sorted((project/'.lake/packages').glob('*/.lake/build/lib/lean'))]
            env = os.environ.copy(); env['LEAN_PATH'] = os.pathsep.join(map(str,search))
            # Persist driver sources and request inventories, not compiler objects.
            inputs = output/'inputs'; inputs.mkdir()
            def save(name: str, text: str) -> None:
                (work/name).write_text(text,encoding='utf-8'); (inputs/name).write_text(text,encoding='utf-8')
            def execute(label: str, arguments: list[str], expected_error: str | None = None) -> str:
                entry = {'label':label,'arguments':arguments,'expected_error':expected_error,'returncode':None}
                report['commands'].append(entry)
                write_json(output/'observation.json',report)
                try:
                    p = subprocess.run([binary,*arguments],cwd=work,env=env,stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,timeout=240,check=False)
                    data = p.stdout; entry['returncode'] = p.returncode
                except subprocess.TimeoutExpired as exc:
                    (output/(label+'.log')).write_bytes(exc.stdout or b'');entry['timed_out']=True
                    raise ValueError('Lean timeout: '+label) from exc
                path = output/(label+'.log');path.write_bytes(data);entry['log_sha256']=file_digest(path)
                write_json(output/'observation.json',report)
                text = data.decode('utf-8',errors='strict')
                if expected_error:
                    if p.returncode == 0 or expected_error not in text or 'SOURCE_EXPRESSION_REPLAY_COMPLETE' in text:
                        raise ValueError('Expected rejection absent or wrong: '+label)
                elif p.returncode or 'declaration uses' in text or 'sorryAx' in text:
                    raise ValueError('Lean command failed: '+label)
                return text
            version = execute('version',['--version']).strip();report['lean_version']=version
            if not version.startswith('Lean (version 4.34.1,'): raise ValueError('Unexpected compiler version')
            for n in MODULES: execute('compile-'+Path(n).stem,['-o',Path(n).stem+'.olean',n])
            if original:
                save('OriginalBezout.lean',original)
                execute('compile-OriginalBezout',['-o','OriginalBezout.olean','OriginalBezout.lean'])
            save('targets.json',canonical_json([named(n) for n in names]))
            for label in ('first','repeat'):
                save('Export-'+label+'.lean',export_driver(extra,label))
                log=execute('export-'+label,['Export-'+label+'.lean'])
                if log.count('SOURCE_EXPRESSION_EXPORT_COMPLETE')!=1: raise ValueError('Missing export completion')
            first={p.name:file_digest(p) for p in (work/'first').iterdir()}
            repeat={p.name:file_digest(p) for p in (work/'repeat').iterdir()}
            if len(first)!=2*len(names) or first!=repeat: raise ValueError('Export repeat differs or inventory incomplete')
            shutil.copytree(work/'first',output/'records')
            records, requests, summaries = {}, [], []
            for k,n in enumerate(names):
                r=json.loads((work/f'first/{k}.json').read_text()); snapshot=json.loads((work/f'first/{k}.snapshot.json').read_text())
                view=Expressions(r);binding=view.bind_snapshot(snapshot)
                if r['name']!=named(n): raise ValueError('Export target differs')
                if not original and k < len(FIXTURES):
                    for suffix in ('.json','.snapshot.json'):
                        with ZipFile(ROOT/'tests/fixtures/source-expressions/records.zip') as fixture:
                            original_bytes=json.loads(fixture.read('records.json'))[FIXTURES[k]+suffix].encode('utf-8')
                        if original_bytes != (work/'first'/(str(k)+suffix)).read_bytes():
                            raise ValueError('Committed regression fixture differs from fresh export')
                records[n]=r; requests.append({'name':named(n),'paths':[f['path'] for f in snapshot['frames']],
                                              'file':f'first/{k}.json','snapshot_file':f'first/{k}.snapshot.json'})
                summaries.append({**view.summary(),'snapshot_sha256':binding['snapshot_sha256'],
                                  'kernel_judgements_expected':expected_count(r)})
                if original and n==names[-1]:
                    frozen=json.loads((ROOT/'artifacts/companion/native/current/snapshot.json').read_text())
                    if snapshot!=frozen: raise ValueError('Fresh Bezout snapshot differs from retained source')
                    report['bezout_snapshot_matches_retained']=True
            save('requests.json',canonical_json(requests))
            save('Replay.lean',replay_driver(extra,'requests.json'))
            log=execute('fresh-replay',['Replay.lean'])
            if log.count('SOURCE_EXPRESSION_REPLAY_COMPLETE')!=1: raise ValueError('Missing native replay completion')
            replay=json.loads((work/'replayed.json').read_text())
            expected=[{'name':r['name'],'frames':len(r['frames']),'kernel_judgements':expected_count(r)} for r in records.values()]
            if replay!=expected: raise ValueError('Native judgement inventory differs')
            shutil.copyfile(work/'replayed.json',output/'replayed.json')
            # Repeat replay in another process and check its whole result inventory.
            execute('fresh-replay-repeat',['Replay.lean'])
            if (work/'replayed.json').read_bytes()!=(output/'replayed.json').read_bytes():
                raise ValueError('Replay inventory differs on repeat')
            save('Extract.lean',extraction_driver(extra))
            log=execute('extract-and-reapply',['Extract.lean'])
            if log.count('SOURCE_EXPRESSION_EXTRACTION_COMPLETE')!=1:
                raise ValueError('Lemma extraction did not finish')
            extracted=json.loads((work/'extracted.json').read_text())
            wanted=[(r['name'],f['path'],f['required_context'],f['display']['lifted'])
                    for r in records.values() for f in r['frames']]
            actual=[(r['source'],r['path'],r['required_context'],r['signature']) for r in extracted]
            if actual!=wanted or len({canonical_json(r['name']) for r in extracted})!=len(wanted):
                raise ValueError('Extracted lemma inventory differs')
            shutil.copyfile(work/'extracted.json',output/'extracted.json')
            negatives=mutations(records); cases=[]
            for label,target,changed,error in negatives:
                filename='negative-'+label+'.json';save(filename,canonical_json(changed))
                request=deepcopy(requests[names.index(target)]);request['file']=filename
                cases.append({'label':label,'expected_error':error,'request':request})
            save('negative-cases.json',canonical_json(cases))
            save('Reject.lean',negative_driver(extra))
            log=execute('negative-controls',['Reject.lean'])
            if log.count('SOURCE_EXPRESSION_REJECTIONS_COMPLETE')!=1:
                raise ValueError('Native negative suite did not finish')
            rejected=json.loads((work/'rejected.json').read_text())
            if [r['label'] for r in rejected]!=[c['label'] for c in cases]+['kernel-bypass','extraction-type','extraction-overwrite']:
                raise ValueError('Native negative-control inventory differs')
            corrupted=json.loads((work/'first/0.snapshot.json').read_text())
            corrupted['frames'][-1]['statement']='False'
            save('changed-snapshot.json',canonical_json(corrupted))
            bad_request=deepcopy(requests[0]);bad_request['snapshot_file']='changed-snapshot.json'
            save('changed-snapshot-request.json',canonical_json([bad_request]))
            save('RejectSnapshot.lean',replay_driver(extra,'changed-snapshot-request.json'))
            execute('reject-changed-snapshot',['RejectSnapshot.lean'],'Snapshot source replay mismatch')
            rejected.append({'label':'changed-snapshot','diagnostic':'Snapshot source replay mismatch'})
            write_json(output/'rejected.json',rejected)
            write_json(output/'summaries.json',summaries)
            write_json(output/'requests.json',requests)
            # Provide inspection text from source records, not an English paraphrase.
            lines=['# Extracted local lemmas','', 'Signatures printed by Lean. Local definitions are retained; `⋯` hides their values.', '']
            for k,n in enumerate(names):
                r=records[n]; candidate=next((f for f in reversed(r['frames']) if f['required_context']),r['frames'][-1])
                lines += ['## '+n,'','Source path: `'+str(candidate['path'])+'`','', '```lean',candidate['display']['lifted'],'```','']
            (output/'lemmas.md').write_text('\n'.join(lines),encoding='utf-8')
            report.update(status='passed', declarations=len(names), synthetic_declarations=len(FIXTURES),
                          library_declarations=len(LIBRARY), openai_declarations=int(original is not None),
                          frames=sum(len(r['frames']) for r in records.values()),
                          extracted_lemmas=len(extracted), extraction_kernel_judgements=2*len(extracted),
                          kernel_judgements=sum(expected_count(r) for r in records.values()),
                          negative_controls=[r['label'] for r in rejected], exported_files_sha256=first,
                          export_repeat_identical=True,replay_repeat_identical=True)
    except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError) as exc:
        report['error']=str(exc)
    finally:
        report['evidence_sha256']={str(p.relative_to(output)):file_digest(p) for p in sorted(output.rglob('*'))
                                   if p.is_file() and p.name!='observation.json'}
        write_json(output/'observation.json',report)
    return report


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lean',default='lean'); parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--project',type=Path,help='Pinned Mathlib environment; adds unchanged Bezout body with the import adapter')
    parser.add_argument('--retained-environment',type=Path)
    parser.add_argument('--trust-project',action='store_true')
    args=parser.parse_args()
    if not args.trust_project: parser.error('Lean execution requires --trust-project')
    output=args.output.resolve(); project=args.project.resolve() if args.project else None
    if output.exists() and (not output.is_dir() or any(output.iterdir())): parser.error('Use a new or empty evidence directory')
    if project and (output.is_relative_to(project) or project.is_relative_to(output)):
        parser.error('Evidence and project directories must be separate')
    if args.retained_environment and not project: parser.error('--retained-environment requires --project')
    output.mkdir(parents=True,exist_ok=True)
    report=run_gate(args.lean,output,project,args.retained_environment)
    print(json.dumps({k:report[k] for k in ('status','declarations','frames','kernel_judgements','error') if k in report}))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__': raise SystemExit(main())
