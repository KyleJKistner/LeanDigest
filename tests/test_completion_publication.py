from copy import deepcopy
import hashlib
import json
import zipfile
import pytest
from proofreader.original_project import digest,file_hash
from scripts.publish_completion_release import validate_identity,check_site_archive,publish

APP='a'*40


def identities():
    coverage={'documented_findings':242,'expected_theorem_targets':536,
        'expected_statement_entries':602,'elaborated_statement_entries':602,
        'all_documented_findings_indexed':True,'all_specification_entries_accessible':True,
        'rendering_failures':0,'proof_readings':513}
    status={'proof_summary':{'expected_theorem_targets':536,'total_readings':513},
            'build_summary':{'comparator_expected':416,'comparator_passed':361,
                             'library_expected':25,'library_passed':15}}
    status['status_sha256']=digest(status)
    release={'schema':'leanglish.completion-reading-delivery/v1','application_commit':APP,
        'application_tracked_tree_clean':True,'coverage':coverage,'status_sha256':status['status_sha256'],
        'static_audit':{'passed':True},'browser_audit':{'passed':True,'navigation_backend':'real-offline-file-navigation'},
        'english_formally_verified':False,'native_lean_executed_by_builder':False}
    return release,status,coverage


def test_valid_separate_reading_and_project_counts():
    validate_identity(*identities(),APP)


@pytest.mark.parametrize('change',['application','browser','ledger','baseline','english'])
def test_publication_cannot_upgrade_or_relabel_an_observation(change):
    release,status,coverage=identities()
    if change=='application':release['application_commit']='b'*40
    elif change=='browser':release['browser_audit']['navigation_backend']='document-harness'
    elif change=='ledger':status['proof_summary']['total_readings']=536
    elif change=='baseline':coverage['proof_readings']=100
    else:release['english_formally_verified']=True
    with pytest.raises(ValueError):validate_identity(release,status,coverage,APP)


def site(tmp_path, extra=None, changed=False):
    release={'application_commit':APP}
    files={'release.json':json.dumps(release).encode(),'index.html':b'<h1>Proofs</h1>'}
    if extra:files[extra]=b'x'
    manifest={name:hashlib.sha256(body).hexdigest() for name,body in files.items()}
    if changed:files['index.html']=b'<h1>Changed</h1>'
    archive=tmp_path/'site.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for name,body in files.items():z.writestr('Leanglish/'+name,body)
        z.writestr('Leanglish/SHA256SUMS.json',json.dumps(manifest))
    return archive,release


def test_all_packaged_files_are_checked(tmp_path):
    archive,release=site(tmp_path)
    assert check_site_archive(archive,release,file_hash(archive))==2


@pytest.mark.parametrize('extra',['../outside.txt','font.woff2'])
def test_unsafe_paths_and_font_files_are_excluded(tmp_path,extra):
    archive,release=site(tmp_path,extra)
    with pytest.raises(ValueError):check_site_archive(archive,release,file_hash(archive))


def test_outer_hash_does_not_substitute_for_internal_manifest(tmp_path):
    archive,release=site(tmp_path,changed=True)
    with pytest.raises(ValueError):check_site_archive(archive,release,file_hash(archive))


def test_publication_requires_explicit_permission(tmp_path):
    with pytest.raises(PermissionError):
        publish(1,2,'a'*64,APP,'leanglish-original-project-aaaaaaa',tmp_path/'out')
    assert not (tmp_path/'out').exists()
