"""Small dependency-free CLI. Reading never implicitly compiles a project."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from . import __version__
from .branding import PRODUCT_NAME
from .model import Document, report
from .render import load_document, markdown_document, write_html
from .source import merge_documents, parse_source


def source_document(paths: list[str], title: str | None = None) -> Document:
    documents = []
    for value in paths:
        p = Path(value)
        if p.is_dir():
            for f in sorted(p.rglob("*.lean")):
                if {".lake", ".git", "_proofreader_cache", ".venv"}.intersection(f.parts) or f.is_symlink(): continue
                documents.append(parse_source(f.read_text(encoding="utf-8"), f.relative_to(p).as_posix()))
        elif p.suffix == ".json":
            d=load_document(p.read_bytes())
            if len(paths)!=1: raise ValueError("Reading JSON must be the only input")
            if title:d.title=title
            return d
        else:
            documents.append(parse_source(p.read_text(encoding="utf-8"), p.name))
    return merge_documents(documents, title or f"{PRODUCT_NAME} · source library")


def write_outputs(d: Document, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix==".json": output.write_text(d.to_json(),encoding="utf-8")
    elif output.suffix==".md": output.write_text(markdown_document(d),encoding="utf-8")
    else: write_html(d,output)


def parser(prog: str = "proofreader") -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(prog=prog,description=f"{PRODUCT_NAME}: deterministic, evidence-labelled reading views for Lean. Source outlines are not checked English proofs.")
    p.add_argument("--version",action="version",version=f"{PRODUCT_NAME} {__version__}")
    commands=p.add_subparsers(dest="command",required=True)
    read=commands.add_parser("read",help="Read Lean source or a reading JSON file without compiling")
    read.add_argument("inputs",nargs="+");read.add_argument("--output","-o",type=Path,default=Path("proofreader.html"));read.add_argument("--title")
    serve=commands.add_parser("serve",help="Serve an offline reader on 127.0.0.1; no execution endpoints")
    serve.add_argument("inputs",nargs="*");serve.add_argument("--port",type=int,default=8765)
    demo=commands.add_parser("demo",help="Write the bundled six-file OpenAI source demo")
    demo.add_argument("--output","-o",type=Path,default=Path("proofreader-demo.html"))
    doctor=commands.add_parser("doctor",help="Check whether a local Lean toolchain is usable")
    doctor.add_argument("--project",type=Path)
    f=commands.add_parser("from-export",help="Render a typed export; does not authenticate the export")
    f.add_argument("input",type=Path);f.add_argument("--module",default="");f.add_argument("--output","-o",type=Path,default=Path("proofreader.html"));f.add_argument("--fixture",action="store_true")
    r=commands.add_parser("replay-source",help="Generate a Lean raw-term round-trip check; does not execute it")
    r.add_argument("input",type=Path);r.add_argument("--module",required=True);r.add_argument("--output","-o",type=Path,required=True)
    ex=commands.add_parser("extract",help="Build and export an existing trusted Lean module")
    ex.add_argument("module");ex.add_argument("--project",type=Path,required=True);ex.add_argument("--output","-o",type=Path,required=True);ex.add_argument("--trust-project",action="store_true");ex.add_argument("--replay",action="store_true");ex.add_argument("--timeout",type=float,default=600)
    c=commands.add_parser("fetch-openai",help="Fetch every source artifact at a pinned OpenAI commit")
    c.add_argument("destination",type=Path);c.add_argument("--commit",default=None);c.add_argument("--workers",type=int,default=6)
    b=commands.add_parser("benchmark",help="Index every expected Lean file and report all failures")
    b.add_argument("root",type=Path);b.add_argument("--output","-o",type=Path,required=True)
    e=commands.add_parser("extract-corpus",help="Opt-in sharded build/export/replay of the complete Lean library")
    e.add_argument("root",type=Path);e.add_argument("--output","-o",type=Path,required=True);e.add_argument("--trust-project",action="store_true");e.add_argument("--timeout",type=float,default=600);e.add_argument("--shard-index",type=int,default=0);e.add_argument("--shard-count",type=int,default=1);e.add_argument("--no-replay",action="store_true");e.add_argument("--engine",choices=["kernel","legacy"],default="kernel")
    a=commands.add_parser("aggregate",help="Reconcile complete module inventories and replays across every shard")
    a.add_argument("root",type=Path);a.add_argument("reports",nargs="+",type=Path);a.add_argument("--output","-o",type=Path,required=True)
    g=commands.add_parser("gate",help="Fail closed on incomplete or unproven corpus coverage")
    g.add_argument("report",type=Path);g.add_argument("--level",choices=["inventory","replay","english"],default="english")
    k=commands.add_parser("kernel-read",help="Create a mathematical reader, raw argument and replay source from a v2 export; no execution")
    k.add_argument("input",type=Path);k.add_argument("--output","-o",type=Path,required=True)
    k.add_argument("--source",type=Path);k.add_argument("--module");k.add_argument("--context",type=Path);k.add_argument("--receipt",type=Path)
    kr=commands.add_parser("check-reading",help="Regenerate English and reject modified mathematics; does not run Lean")
    kr.add_argument("input",type=Path);kr.add_argument("reading",type=Path)
    kv=commands.add_parser("verify-kernel",help="Verify original and intermediate judgements in a pinned Lean environment")
    kv.add_argument("input",type=Path);kv.add_argument("--output","-o",type=Path,required=True)
    kv.add_argument("--backend",choices=["native","axle"],default="native")
    kv.add_argument("--project",type=Path);kv.add_argument("--module");kv.add_argument("--context",type=Path)
    kv.add_argument("--trust-project",action="store_true");kv.add_argument("--allow-remote",action="store_true")
    kv.add_argument("--timeout",type=float,default=180);kv.add_argument("--permit-axiom",action="append",default=[])
    kd=commands.add_parser("kernel-demo",help="Write the bundled actual typed-proof demonstration; no network or Lean required")
    kd.add_argument("--output","-o",type=Path,default=Path("proofreader-typed-demo.html"))
    ke=commands.add_parser("extract-kernel",help="Extract every theorem in a module/source into the v2 reader; execution is explicit")
    ke.add_argument("--output","-o",type=Path,required=True);ke.add_argument("--module");ke.add_argument("--context",type=Path)
    ke.add_argument("--project",type=Path);ke.add_argument("--backend",choices=["native","axle"],default="native")
    ke.add_argument("--lean-version",default="4.34.0");ke.add_argument("--trust-project",action="store_true")
    ke.add_argument("--allow-remote",action="store_true");ke.add_argument("--verify",action="store_true")
    ke.add_argument("--timeout",type=float,default=180);ke.add_argument("--permit-axiom",action="append",default=[])
    nd=commands.add_parser("narrative-demo",help="Write the substantial Bézout-frame mathematical reader; no execution")
    nd.add_argument("--output","-o",type=Path,default=Path("proofreader-narrative.html"))
    nr=commands.add_parser("narrative-read",help="Render a source-bound snapshot and exact polynomial certificates offline")
    nr.add_argument("input",type=Path);nr.add_argument("--output","-o",type=Path,required=True)
    nr.add_argument("--source",type=Path);nr.add_argument("--receipt",type=Path)
    nr.add_argument("--title");nr.add_argument("--provenance-note")
    nc=commands.add_parser("check-narrative",help="Regenerate displayed mathematics and independently replay supplied certificates")
    nc.add_argument("input",type=Path);nc.add_argument("reading",type=Path);nc.add_argument("--certificates",type=Path)
    ne=commands.add_parser("extract-narrative",help="Opt-in Lean extraction of one source-bound theorem snapshot")
    nv=commands.add_parser("verify-narrative",help="Freshly re-extract the source and compare a supplied snapshot")
    ne.add_argument("theorem");ne.add_argument("--lean-version",default="4.34.1")
    nv.add_argument("input",type=Path)
    for cmd in (ne,nv):
        cmd.add_argument("--output","-o",type=Path,required=True)
        cmd.add_argument("--context",type=Path);cmd.add_argument("--module");cmd.add_argument("--driver",type=Path)
        cmd.add_argument("--project",type=Path);cmd.add_argument("--backend",choices=["native","axle"],default="native")
        cmd.add_argument("--trust-project",action="store_true");cmd.add_argument("--allow-remote",action="store_true")
        cmd.add_argument("--timeout",type=float,default=180)
    return p


def demo_document() -> Document:
    p=Path(__file__).parent / "data" / "demo.json"
    if not p.is_file(): raise ValueError("Demo data is not packaged. Run scripts/build_demo.py from the source checkout.")
    return load_document(p.read_bytes())


def main(argv: list[str] | None = None, *, prog: str = "proofreader") -> int:
    args=parser(prog).parse_args(argv)
    try:
        if args.command=="narrative-demo":
            d=load_document((Path(__file__).parent/"data/narrative-demo.json").read_bytes())
            write_outputs(d,args.output);print(args.output);return 0
        if args.command=="narrative-read":
            from .narrative import Snapshot
            from .narrative_io import write_bundle
            from .kernel_io import strict_json
            result=write_bundle(Snapshot.read(args.input).record,args.output,
               source=args.source.read_text(encoding="utf-8") if args.source else "",file=str(args.source or args.input),
               receipt=strict_json(args.receipt.read_bytes()) if args.receipt else None,
               title=args.title,provenance_note=args.provenance_note)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0
        if args.command=="check-narrative":
            from .narrative import Snapshot,check_reading
            from .narrative_io import verify_certificates
            from .kernel_io import strict_json
            record=Snapshot.read(args.input).record
            check_reading(record,load_document(args.reading.read_bytes()))
            if args.certificates:verify_certificates(record,strict_json(args.certificates.read_bytes()))
            print(json.dumps({"regeneration":"passed","supplied_certificates_replayed":bool(args.certificates),
                              "lean_rerun":False,"english_formally_verified":False}));return 0
        if args.command in {"extract-narrative","verify-narrative"}:
            from .narrative import Snapshot
            from .narrative_io import extract_narrative
            expected=Snapshot.read(args.input).record if args.command=="verify-narrative" else None
            result=extract_narrative(expected["theorem"] if expected else args.theorem,args.output,
               context=args.context.read_text(encoding="utf-8") if args.context else None,module=args.module,
               version=expected["lean_version"] if expected else args.lean_version,backend=args.backend,
               project=args.project,trust_project=args.trust_project,allow_remote=args.allow_remote,
               timeout=args.timeout,expected=expected,driver=args.driver.read_text(encoding="utf-8") if args.driver else None)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result["status"]=="passed" else 2
        if args.command=="extract-kernel":
            from .kernel_pipeline import extract_kernel
            result=extract_kernel(args.output,module=args.module,context=args.context.read_text(encoding="utf-8") if args.context else None,
                 project=args.project,backend=args.backend,version=args.lean_version,trust_project=args.trust_project,
                 allow_remote=args.allow_remote,verify=args.verify,timeout=args.timeout,permitted_axioms=args.permit_axiom)
            print(json.dumps({k:v for k,v in result.items() if k!="rows"},ensure_ascii=False,indent=2))
            return 0 if result["status"]=="complete" else 2
        if args.command=="kernel-read":
            from .kernel_io import strict_json,write_bundle
            from .kernel import read_record
            source=args.source.read_text(encoding="utf-8") if args.source else ""
            receipt=strict_json(args.receipt.read_bytes()) if args.receipt else None
            result=write_bundle(read_record(args.input),args.output,source=source,file=str(args.source or args.input),receipt=receipt,
                                imports=[args.module] if args.module else [],context=args.context.read_text(encoding="utf-8") if args.context else None)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0
        if args.command=="check-reading":
            from .kernel import read_record
            from .english import check_reading
            check_reading(read_record(args.input),load_document(args.reading.read_bytes()))
            print(json.dumps({"deterministic_regeneration":"passed","lean_rerun":False,"english_formally_verified":False}));return 0
        if args.command=="verify-kernel":
            from .kernel import read_record
            from .kernel_io import verify_native,verify_remote
            context=args.context.read_text(encoding="utf-8") if args.context else None
            record=read_record(args.input)
            if args.backend=="native":
                if args.project is None:raise ValueError("Native verification requires --project")
                result=verify_native(record,args.project,args.output,module=args.module,context=context,trust_project=args.trust_project,
                                     timeout=args.timeout,permitted_axioms=args.permit_axiom)
            else:
                if context is None:raise ValueError("Remote verification requires --context with the exact original source prefix")
                if args.module:raise ValueError("Remote verification uses source context, not a local module")
                result=verify_remote(record,args.output,context=context,allow_remote=args.allow_remote,
                                     timeout=args.timeout,permitted_axioms=args.permit_axiom)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result["status"]=="passed" else 2
        if args.command=="kernel-demo":
            path=Path(__file__).parent/"data"/"kernel-demo.json"
            d=load_document(path.read_bytes());write_outputs(d,args.output);print(args.output);return 0
        if args.command=="read":
            d=source_document(args.inputs,args.title);write_outputs(d,args.output)
            print(json.dumps({"output":str(args.output),**report(d)},indent=2));return 0
        if args.command=="demo":
            d=demo_document();write_outputs(d,args.output);print(args.output);return 0
        if args.command=="serve":
            from .server import serve
            serve(source_document(args.inputs) if args.inputs else load_document((Path(__file__).parent/"data/reader-demo.json").read_bytes()),args.port);return 0
        if args.command=="doctor":
            from .lean import doctor
            status=doctor(args.project);print(json.dumps(status,indent=2));return 0 if status["can_extract"] else 2
        if args.command=="from-export":
            from .core import export_document
            d=export_document(json.loads(args.input.read_text()),args.module,fixture=args.fixture);write_outputs(d,args.output);print(args.output);return 0
        if args.command=="replay-source":
            from .core import replay_source
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(replay_source(json.loads(args.input.read_text()),args.module),encoding="utf-8");print(args.output);return 0
        if args.command=="extract":
            from .lean import extract_module
            result=extract_module(args.project,args.module,args.output,trust_project=args.trust_project,timeout=args.timeout,replay=args.replay)
            print(json.dumps(result,indent=2));return 0 if result["status"]=="exported" else 2
        if args.command=="fetch-openai":
            from .corpus import fetch_snapshot,OPENAI_COMMIT
            result=fetch_snapshot(args.destination,args.commit or OPENAI_COMMIT,workers=args.workers)
            print(json.dumps({k:v for k,v in result.items() if k!="files"},indent=2));return 0 if result["state"]=="complete" else 2
        if args.command=="benchmark":
            from .corpus import benchmark_sources
            result=benchmark_sources(args.root,args.output)
            print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2));return 0 if result["failed_or_missing_files"]==0 and result["expected_lean_files"]>0 else 2
        if args.command=="extract-corpus":
            from .corpus import extract_corpus
            result=extract_corpus(args.root,args.output,trust_project=args.trust_project,timeout=args.timeout,replay=not args.no_replay,shard_index=args.shard_index,shard_count=args.shard_count,engine=args.engine)
            print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2));return 0 if result["shard_expected"]>0 and all(r["status"]=="exported" for r in result["rows"]) else 2
        if args.command=="aggregate":
            from .corpus import aggregate_extractions
            result=aggregate_extractions(args.root,args.reports,args.output)
            print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2));return 0 if result["all_formal_proofs_replayed"] else 2
        if args.command=="gate":
            from .corpus import coverage_gate
            passed,reason=coverage_gate(json.loads(args.report.read_text()),args.level)
            print(json.dumps({"passed":passed,"level":args.level,"reason":reason}));return 0 if passed else 2
    except (OSError,ValueError,PermissionError,RuntimeError,RecursionError) as exc:
        print(f"{prog}: {exc}",file=sys.stderr);return 2
    return 2

if __name__=="__main__": raise SystemExit(main())
