"""Supporting lemma readings (dependency cone, level 1) in the offline catalog.

A catalog can include the readings of a dependency-cone campaign: readings of
the project lemmas that its documented-target readings cite. They are a
separate denominator, written under ``cone/<id>/``. They never enter the
theorem-target coverage, the explanation-gap inventory or the reading KPIs, and
a supporting lemma reading never changes the status of a documented target.

A campaign directory is accepted only through ``dependency_cone.reconcile``,
which validates every shard against the plan and the original environment.
This module adds the bindings to the catalog: the plan was derived from exactly
the catalog's readings, its original plan and environment audit equal the
catalog's own records when the catalog bundles them, and every environment
module's bundled source has the planned hash. Shard artifacts remain unsigned
observations: these checks establish consistency, not authenticity.
"""
from __future__ import annotations
from collections import Counter
import html
from pathlib import Path
import shutil
from typing import Any, Callable

from .declaration_index import CONE_DENOMINATOR, link_kind, reading_map
from .dependency_cone import DENOMINATOR, FLAGS, REPORT, bind_original, lemma_id, reconcile, validate_plan
from .kernel_io import strict_json
from .model import digest
from .narrative_io import write_bundle
from .original_project import digest as data_digest

if CONE_DENOMINATOR != DENOMINATOR:  # declaration_index cannot import dependency_cone (import cycle)
    raise ImportError('Citation links and the dependency-cone plan name different denominators')

SCHEMA = 'leanglish.catalog-dependency-cone/v1'
DIRECTORY = 'cone'
PLAN = 'dependency-cone-plan'
PLAN_FILES = ('plan.json', 'original-plan.json', 'environment.json')
SUMMARY_RECORD = 'evidence/dependency-cone-summary.json'
# Retained evidence in each cone reading directory: the shard artifact's bytes.
EVIDENCE = ('snapshot.json', 'receipt.json', 'run.json', 'stdout.txt', 'Extract.lean')
# The context the shard worker supplied: the extraction driver imports the environment module.
FILE = 'Context.lean'
HEADING = 'Supporting lemma readings'
ROW = 'Supporting lemma readings (dependency cone, level 1)'
LINK_ROW = '… linked to a supporting lemma reading of the same constant (dependency cone, level 1)'


def context(module: str) -> str:
    return 'import '+module+'\n'


def note(module: str) -> str:
    return ('Supporting lemma reading (dependency cone, level 1): retained native observation of a project lemma, extracted '
            'after importing the unchanged original module '+module+', whose documented-target reading cites it. The lemma '
            'may be declared in a module that it imports. A separate denominator: it does not count toward the theorem '
            'targets, and it is not a Comparator or complete-project replay.')


def scope_label(scope: str) -> str:
    return 'pilot scope' if scope == 'pilot' else 'dispatch scope '+scope


def load(directory: Path, readings: dict[str, tuple[str, str, str]], sources: dict[str, str], *,
         scope: str = 'pilot', summary: Path | None = None, original: dict | None = None,
         environment: dict | None = None) -> dict:
    """Validate a campaign directory for this catalog.

    ``directory`` holds ``dependency-cone-plan/`` (the plan, the original plan and
    the environment audit) and the shard directories, as the workflow's summary
    job downloads them. ``readings`` maps each catalog reading identifier to
    (module, theorem, snapshot SHA-256); ``sources`` holds the bundled solution
    modules. ``original`` and ``environment`` are the catalog's own original-project
    records, when it bundles them. ``summary``, when given, is the campaign's
    summary and must equal the reconciliation. Any mismatch raises ValueError.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError('The dependency-cone input is not a directory')
    if any(p.is_symlink() for p in [directory, *directory.rglob('*')]):
        raise ValueError('The dependency-cone input contains a symbolic link')
    folder = directory/PLAN
    if not all((folder/n).is_file() for n in PLAN_FILES):
        raise ValueError('The dependency-cone input lacks '+PLAN+'/ with '+', '.join(PLAN_FILES))
    plan, original_, environment_ = (strict_json((folder/n).read_text(encoding='utf-8')) for n in PLAN_FILES)
    validate_plan(plan)
    if original is not None and original_ != original:
        raise ValueError("The cone plan's original plan differs from the catalog's original-project plan")
    if environment is not None and environment_ != environment:
        raise ValueError("The cone plan's environment audit differs from the catalog's original environment")
    bind_original(plan, original_, environment_)
    planned = {r['id']: (r['module'], r['theorem'], r['snapshot_sha256']) for r in plan['readings']}
    if planned != readings:
        raise ValueError("The dependency-cone plan was derived from other readings than this catalog's "
                         f'({len(planned)} planned, {len(readings)} in the catalog, {len(planned.items() & readings.items())} in common)')
    roots = [p.parent for p in sorted(directory.rglob(REPORT))]
    result, accepted = reconcile(plan, environment_, roots, scope)
    if summary is not None and strict_json(Path(summary).read_text(encoding='utf-8')) != result:
        raise ValueError('The reconciled dependency-cone summary differs from the supplied campaign summary')
    names = {theorem for _, theorem, _ in readings.values()}
    shards = {s['id']: s for s in plan['shards']}
    for name, a in sorted(accepted.items()):
        # validate_plan already keeps read names out of the cone; the precedence rule is never exercised.
        if name in names:
            raise ValueError('A supporting lemma reading duplicates a documented-target reading: '+name)
        if a['id'] != lemma_id(a['module'], name):
            raise ValueError('Noncanonical supporting lemma identifier: '+name)
        source = sources.get(a['module'])
        if source is None or digest(source) != shards[a['shard_id']]['source_sha256']:
            raise ValueError('The bundled source of a cone environment module differs from the planned source: '+a['module'])
    return {'plan': plan, 'summary': result, 'accepted': accepted, 'scope': scope,
            'campaign_summary_supplied': summary is not None,
            'original_records_compared': original is not None and environment is not None}


def supporting_map(cone: dict, available: set[str] | None = None) -> dict[str, list[tuple[str, str]]]:
    """Lemma name -> [(environment module, identifier)], for declaration_index.citation_links."""
    return reading_map({(a['module'], name): a['id'] for name, a in cone['accepted'].items()
                        if available is None or name in available})


def write_readings(output: Path, cone: dict, link: Callable[[Any, str], dict], *,
                   available: set[str] | None = None) -> tuple[dict, list]:
    """Write each accepted reading to cone/<id>/ and restore its shard evidence byte for byte.

    ``link(document, environment module)`` returns the reading's citation links.
    Returns (rows by lemma name, rendering failures). A failed reading leaves no directory.
    """
    rows, failures = {}, []
    for name, a in sorted(cone['accepted'].items()):
        if available is not None and name not in available:
            continue
        dest = Path(output)/DIRECTORY/a['id']; made = []
        try:
            if dest.exists():
                shutil.rmtree(dest)
            coverage = write_bundle(a['record'], dest, source=context(a['module']), file=FILE, receipt=a['receipt'],
                                    title=name, provenance_note=note(a['module']),
                                    links=lambda d, a=a: made.append(link(d, a['module'])) or made[-1])
            for n in EVIDENCE:
                data = (a['directory']/n).read_bytes(); path = dest/n
                if path.is_file() and path.read_bytes() != data and (not n.endswith('.json') or strict_json(path.read_bytes()) != strict_json(data)):
                    raise ValueError('Rewritten supporting lemma evidence differs: '+n)
                path.write_bytes(data)
            rows[name] = {'id': a['id'], 'module': a['module'], 'shard_id': a['shard_id'],
                          'frames': a['record']['judgements_checked'], 'gaps': coverage['source_bound_unexpanded_steps'],
                          'snapshot_sha256': a['receipt']['snapshot_sha256'], 'links': made[-1]}
        except (ValueError, OSError, RuntimeError, RecursionError) as exc:
            shutil.rmtree(dest, ignore_errors=True)
            failures.append({'name': name, 'module': a['module'], 'id': a['id'], 'error': str(exc)[:500]})
    return rows, failures


def cited(payload: dict) -> list[str]:
    """The names one reading's links resolve to supporting lemma readings."""
    return sorted(n for n, v in payload['names'].items() if link_kind(v) == 'cone-reading')


def section(cone: dict, rows: dict, failures: list, target_payloads: list[dict], links_summary: dict) -> dict:
    """The ``dependency_cone`` section of coverage.json: its own denominator, never merged."""
    s, plan = cone['summary'], cone['plan']
    pairs = [(p['module'], n) for p in target_payloads for n in cited(p)]
    return {'schema': SCHEMA, 'denominator_name': DENOMINATOR, 'level': 1, 'scope': cone['scope'],
            'cone_plan_sha256': plan['plan_sha256'], 'summary_sha256': data_digest(s), 'summary_record': SUMMARY_RECORD,
            'planned_lemmas': s['planned_lemmas'], 'readings_accepted': s['readings_generated'], 'readings': len(rows),
            'rendering_failures': failures, 'statuses': s['statuses'],
            'shards_in_scope': s['shards_in_scope'], 'shards_retained': s['shards_retained'],
            'missing_shards': s['missing_shards'], 'dependency_routes': s['dependency_routes'],
            'denominator': plan['denominator'],
            'selected_checked_frames': sum(r['frames'] for r in rows.values()),
            'explicit_explanation_gaps': sum(r['gaps'] for r in rows.values()),
            'readings_without_gaps': sum(r['gaps'] == 0 for r in rows.values()),
            'from_target_readings': {'citations_linked': len(pairs), 'names_linked': len({n for _, n in pairs}),
                                     'readings_linking': sum(bool(cited(p)) for p in target_payloads)},
            'citation_links': links_summary,
            'campaign_summary_matched': True if cone['campaign_summary_supplied'] else None,
            'original_records_compared': cone['original_records_compared'],
            'evidence_files': len(rows)*len(EVIDENCE), 'evidence_names': list(EVIDENCE),
            'evidence_byte_identical_to_shard_artifacts': True,
            'lean_executed_by_catalog': False, **FLAGS}


def finding_items(payloads: list[tuple[str, dict]], rows: dict) -> list[dict]:
    """Supporting lemma readings cited by these (target name, links) pairs, with the citing targets."""
    items: dict[str, dict] = {}
    for theorem, payload in payloads:
        for name in cited(payload):
            r = rows[name]
            items.setdefault(name, {'name': name, **{k: r[k] for k in ('id', 'module', 'frames', 'gaps')}, 'cited_by': []})
            items[name]['cited_by'].append(theorem)
    return [dict(v, cited_by=sorted(set(v['cited_by']))) for _, v in sorted(items.items())]


def finding_section(items: list[dict], scope: str) -> str:
    if not items:
        return ''
    code = lambda x: '<code>'+html.escape(x)+'</code>'
    body = ('<section id="supporting-lemmas"><h2>'+HEADING+'</h2><p class="muted">Readings of project lemmas that the proofs '
            'above cite. Each was extracted separately in the unchanged original environment of a citing module (dependency '
            'cone, level 1; '+scope_label(scope)+'). They are a separate denominator: they do not count toward the theorem '
            'targets above, and a link does not mean that the citation is explained or checked.</p><ul class="supporting-readings">')
    for it in items:
        body += ('<li><a href="../'+DIRECTORY+'/'+it['id']+'/reader.html">'+code(it['name'])+'</a> · cited by '
                 +', '.join(code(t) for t in it['cited_by'])+' · '+str(it['frames'])+' checked frames · '
                 +str(it['gaps'])+' explicit explanation gaps</li>')
    return body+'</ul></section>'


def coverage_rows(sec: dict) -> str:
    """A separate table body for coverage.html; never part of the theorem-target rows."""
    n = lambda x: f'{x:,}'; d = sec['denominator']
    rows = [(ROW, f"{n(sec['readings'])} of {n(sec['planned_lemmas'])} planned; {scope_label(sec['scope'])}"),
            ('… counted toward the theorem-target coverage', 'No; separate denominator'),
            ('… cited project constants in the target readings (the level-1 cone)', n(d['cited_constants'])),
            ('… already read as documented targets', n(d['already_read'])),
            ('… excluded by a recorded name rule', n(d['excluded'])),
            *[('… planned lemmas with recorded outcome <code>'+html.escape(k)+'</code>', n(v)) for k, v in sorted(sec['statuses'].items())],
            ('… shards retained / in run scope', f"{n(sec['shards_retained'])} / {n(sec['shards_in_scope'])}"),
            ('… selected proof frames checked', n(sec['selected_checked_frames'])),
            ('… explicit explanation gaps', n(sec['explicit_explanation_gaps'])),
            *([('… accepted readings that failed to render in this catalog', n(len(sec['rendering_failures'])))] if sec['rendering_failures'] else [])]
    return '</tbody><tbody class="separate-denominator">'+''.join('<tr><td>'+a+'</td><td>'+b+'</td></tr>' for a, b in rows)


NOTE = ('<p>Supporting lemma readings are readings of the project lemmas that the theorem-target readings cite (dependency cone, '
        'level 1). Each comes from a retained shard artifact of the dependency-cone campaign: the lemma was extracted after '
        'importing an unchanged original module whose target reading cites it, and the campaign loader accepted the shard only '
        'after checking it against the plan and the original environment audit. They are a separate denominator, listed on the '
        'finding pages that cite them. They do not count toward the theorem targets, and a lemma reading does not change the '
        'status of any target. A citation links to a supporting lemma reading only when the environment module of that reading '
        'is the citing module or is visibly imported by it. Shard artifacts are unsigned observations.</p>')
EVIDENCE_LINK = ' · <a href="'+SUMMARY_RECORD+'">Dependency-cone outcomes</a>'


def validate_section(sec: Any) -> dict:
    """Shape and flags of a coverage section, for the audit and the preview."""
    if (not isinstance(sec, dict) or sec.get('schema') != SCHEMA or sec.get('denominator_name') != DENOMINATOR or
        any(sec.get(k) is not v for k, v in FLAGS.items()) or sec.get('evidence_names') != list(EVIDENCE) or
        type(sec.get('readings')) is not int or sec.get('readings') + len(sec.get('rendering_failures', [])) != sec.get('readings_accepted')):
        raise ValueError('Malformed dependency-cone coverage section')
    if Counter(sec['statuses'])['reading-generated'] != sec['readings_accepted'] or sum(sec['statuses'].values()) != sec['planned_lemmas']:
        raise ValueError('Dependency-cone coverage counts do not reconcile')
    return sec
