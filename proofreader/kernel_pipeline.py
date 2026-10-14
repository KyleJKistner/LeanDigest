"""Source/project → typed exports → deterministic reader → opt-in kernel checks.

A full module inventory means all *theorem declarations* in that module. It
neither means all papers are formalized nor includes proof-valued `def`s yet.
No source is executed or transmitted without the corresponding explicit flag.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import json
import re
from .kernel import Argument, InvalidExport, SCHEMA, display_name, name_key, require
from .kernel_io import strict_json, axle_request, verify_remote, verify_native, write_bundle, _write_json
from .lean import run_bounded, driver_file, MODULE_RE
from .model import Document, digest
from .english import English
from .render import write_html

PREFIX = 'PROOFREADER_KERNEL:'
INVENTORY = 'proofreader.kernel-inventory/v2'
FAILURE = 'proofreader.kernel-failure/v2'


def extractor_source() -> str:
    return (Path(__file__).parent / 'data/KernelExport.lean').read_text(encoding='utf-8')


def extraction_source(*, module: str | None = None, context: str | None = None) -> tuple[str,str]:
    require((module is None) != (context is None), 'Supply exactly one imported module or source context')
    source = extractor_source()
    marker = 'open Lean Meta Elab Command'
    require(marker in source, 'Packaged extractor boundary is missing')
    if module:
        require(bool(MODULE_RE.fullmatch(module)), 'Unsafe module name')
        prefix = source.replace(marker, f'import {module}\n\n{marker}',1)
        return prefix + f'\n#proofreader_kernel_module "{module}"\n', prefix
    require(isinstance(context,str) and bool(context.strip()), 'Empty source context')
    # Keep the caller's complete source prefix. Kernel rechecking reuses this
    # exact combined context, including any notation/macros and the exporter.
    prefix = context.rstrip() + '\n' + source[source.index(marker):]
    return prefix + '\n#proofreader_kernel_local\n', prefix


def parse_stream(stdout: str) -> dict:
    records=[];failures=[];inventories=[]
    for line in stdout.splitlines():
        match=re.fullmatch(r'(?:[^\n]*?\binfo: )?'+re.escape(PREFIX)+r'(.*)',line)
        if not match: continue
        obj=strict_json(match[1]);require(isinstance(obj,dict),'Exporter record must be an object')
        tag=obj.get('schema')
        if tag==SCHEMA:Argument(obj);records.append(obj)
        elif tag==FAILURE:
            name_key(obj.get('name'));require(isinstance(obj.get('error'),str),'Missing failure description');failures.append(obj)
        elif tag==INVENTORY:inventories.append(obj)
        else:raise InvalidExport('Unknown exporter record schema')
    require(len(inventories)==1,'Missing or duplicated theorem inventory')
    inv=inventories[0]
    require(inv.get('declaration_kind')=='theorem','Unsupported inventory scope')
    require(isinstance(inv.get('names'),list),'Missing expected theorem names')
    expected=[name_key(n) for n in inv['names']]
    observed=[name_key(n['name']) for n in records+failures]
    require(len(expected)==len(set(expected)),'Duplicate inventory name')
    require(len(observed)==len(set(observed)),'Duplicate export outcome')
    require(set(observed)==set(expected),'Theorem inventory and outcomes do not reconcile')
    require(isinstance(inv.get('lean_version'),str),'Missing inventory Lean version')
    require(all(x['lean_version']==inv['lean_version'] for x in records),'Mixed export Lean versions')
    return {'records':records,'failures':failures,'inventory':inv,'complete':not failures}


def _response_stdout(response: dict, source: str) -> str:
    require(response.get('okay') is True, 'AXLE did not successfully compile the complete source')
    require(not response.get('failed_declarations'), 'AXLE reported failed declarations')
    for key in ('lean_messages','tool_messages'):
        messages=response.get(key,{})
        require(isinstance(messages,dict),'Malformed AXLE messages')
        require(not messages.get('errors'), 'AXLE reported errors')
    require(isinstance(response.get('content'),str) and response['content'].strip()==source.strip(),
            'AXLE changed the submitted source')
    infos=response.get('lean_messages',{}).get('infos',[])
    require(isinstance(infos,list) and all(isinstance(x,str) for x in infos),'Malformed AXLE info messages')
    return '\n'.join(infos)


def extract_kernel(output: Path, *, module: str | None = None, context: str | None = None,
                   project: Path | None = None, backend: str = 'native', version: str = '4.34.0',
                   trust_project: bool = False, allow_remote: bool = False,
                   verify: bool = False, timeout: float = 180,
                   permitted_axioms: list[str] | None = None) -> dict:
    require(backend in ('native','axle'),'Unknown execution backend')
    if backend=='native' and not trust_project:
        raise PermissionError('Lean source can execute arbitrary code. Pass --trust-project for a trusted or isolated project.')
    if backend=='axle' and not allow_remote:
        raise PermissionError('This uploads the complete source context to AXLE. Pass --allow-remote to consent.')
    require(0<timeout<=900,'Timeout must be between 0 and 900 seconds')
    if backend=='native':
        require(project is not None and project.is_dir(),'Native extraction needs an existing --project')
        project=project.resolve()
    else:
        require(context is not None and module is None,'Remote extraction requires self-contained --context, not a local module')
    source,prefix=extraction_source(module=module,context=context)
    output.mkdir(parents=True,exist_ok=True)
    (output/'Extract.lean').write_text(source,encoding='utf-8')
    (output/'Context.lean').write_text(prefix,encoding='utf-8')
    result={'schema':'proofreader.kernel-run/v2','status':'started','module':module,
            'backend':backend,'extractor_sha256':digest(extractor_source()),
            'submitted_source_sha256':digest(source),'verify_requested':verify,
            'inventory_scope':'theorem-declarations-only','english_formally_verified':False,
            'dependency_artifacts_authenticated':False,'rows':[],'failures':[]}
    def save():_write_json(output/'result.json',result)
    save()
    try:
        if backend=='native':
            if module:
                build=run_bounded(['lake','build',module],project,timeout=timeout)
                _write_json(output/'build.json',asdict(build))
                require(build.status=='passed' and build.exit_code==0,'Module build failed; see build.json')
            with driver_file(project,source) as driver:
                run=run_bounded(['lake','env','lean',str(driver)],project,timeout=timeout)
            _write_json(output/'export-run.json',asdict(run))
            (output/'stdout.txt').write_text(run.stdout,encoding='utf-8')
            require(run.status=='passed' and run.exit_code==0,'Exporter failed; see export-run.json')
            stdout=run.stdout
        else:
            response=axle_request(source,version,allow_remote=True,timeout=timeout)
            _write_json(output/'axle-export-response.json',response)
            stdout=_response_stdout(response,source)
            require(response.get('info',{}).get('environment')=='lean-'+version,'AXLE environment mismatch')
        stream=parse_stream(stdout)
        if backend=='axle':require(stream['inventory']['lean_version']==version,'Requested/exported versions differ')
        _write_json(output/'inventory.json',stream['inventory'])
        result['inventory']=stream['inventory'];result['failures']=stream['failures']
        docs=[]
        for record in stream['records']:
            a=Argument(record);key=a.sha256[:20];dest=output/'proofs'/key;receipt=None
            row={'name':a.name,'argument_sha256':a.sha256,'directory':f'proofs/{key}',
                 'exported':True,'rendered':False,'checked':False,**a.coverage()}
            result['rows'].append(row);save()
            try:
                if verify:
                    if backend=='native':
                        receipt=verify_native(record,project,dest/'verification',module=module,
                                              context=prefix if context is not None else None,
                                              trust_project=True,timeout=timeout,permitted_axioms=permitted_axioms)
                    else:
                        receipt=verify_remote(record,dest/'verification',context=prefix,allow_remote=True,
                                              timeout=timeout,permitted_axioms=permitted_axioms)
                    row['checked']=receipt['status']=='passed'
                write_bundle(record,dest,source=context or '',file=module or 'Source.lean',receipt=receipt,
                             imports=[module] if module else [],context=prefix if context is not None else None)
                docs.append(English(record).document(source=context or '',file=module or 'Source.lean',receipt=receipt))
                row['rendered']=True
            except (OSError,ValueError,RuntimeError,RecursionError) as ex:
                row['error']=str(ex)
            save()
        combined=Document('Typed proof library',[],[d for doc in docs for d in doc.declarations],
                          provenance={'backend':backend,'theorems_expected':len(stream['inventory']['names']),
                                      'scope':stream['inventory']['scope'],'whole_corpus_coverage':False,
                                      'source_sha256':digest(source),'pipeline_model_calls':0})
        (output/'reading.json').write_text(combined.to_json(),encoding='utf-8');write_html(combined,output/'index.html')
        good=stream['complete'] and all(r['rendered'] and (r['checked'] or not verify) for r in result['rows'])
        result['status']='complete' if good else 'partial'
        result['theorems_expected']=len(stream['inventory']['names'])
        result['theorems_exported']=len(result['rows'])
        result['theorems_checked']=sum(r['checked'] for r in result['rows'])
        result['checked_english_proofs']=0
    except (OSError,ValueError,RuntimeError,RecursionError) as ex:
        result['status']='failed';result['error']=str(ex)
    save();return result
