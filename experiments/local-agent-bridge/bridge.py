#!/usr/bin/env python3
"""Outbound GitHub relay for a single locally controlled agent worker.

Pairing runs version probes only. Model execution requires a private repository,
a locally configured profile, and --enable-profile-execution on this invocation.
This program is a queue transport, not a filesystem or network sandbox.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

REQUEST = '<!-- leanglish-agent-request:v1 -->'
RESPONSE = '<!-- leanglish-agent-response:v1 -->'
SCHEMA = 'leanglish.agent-request/v1'
MAX_REQUEST = 32768
MAX_REPLY = 48000


class BridgeError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise BridgeError(message)


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'Duplicate JSON key')
        out[key] = value
    return out


def loads(text):
    return json.loads(text, object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(BridgeError('Nonfinite JSON')))


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def envelope(marker, value):
    return marker + '\n```json\n' + canonical(value) + '\n```'


def parse_request(body):
    require(isinstance(body, str) and len(body.encode()) <= MAX_REQUEST, 'Request is too large')
    match = re.fullmatch(re.escape(REQUEST) + r'\n```json\n(.*)\n```\s*', body, re.S)
    require(match is not None, 'Not a bridge request')
    job = loads(match[1])
    require(isinstance(job, dict) and set(job) == {
        'schema', 'job_id', 'worker', 'action', 'profile', 'expires_at', 'payload'}, 'Invalid request fields')
    require(job['schema'] == SCHEMA, 'Unsupported request schema')
    require(isinstance(job['job_id'], str) and str(uuid.UUID(job['job_id'])) == job['job_id'], 'Invalid job ID')
    require(isinstance(job['worker'], str) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', job['worker']), 'Invalid worker ID')
    require(job['action'] in ('probe', 'run_profile'), 'Action is not permitted')
    require(isinstance(job['payload'], dict), 'Payload must be an object')
    if job['action'] == 'probe':
        require(job['profile'] is None and not job['payload'], 'Probe takes no commands or arguments')
    else:
        require(isinstance(job['profile'], str) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', job['profile']), 'Invalid profile')
    require(isinstance(job['expires_at'], str) and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', job['expires_at']), 'Invalid expiration')
    datetime.fromisoformat(job['expires_at'].replace('Z', '+00:00'))
    return job


class GitHub:
    """Use the local gh login; no key is sent to ChatGPT or a job subprocess."""
    def __init__(self, repo):
        require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) is not None, 'Invalid repository')
        self.repo = repo
        self.exe = shutil.which('gh')
        require(self.exe is not None, 'Install GitHub CLI and run gh auth login locally first')

    def api(self, path, method='GET', body=None, pages=False):
        argv = [self.exe, 'api', '--hostname', 'github.com', '--method', method, path]
        if pages:
            argv += ['--paginate', '--slurp']
        if body is not None:
            argv += ['--input', '-']
        p = subprocess.run(argv, input=None if body is None else canonical(body).encode(),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        # Do not echo diagnostic output that could contain local credentials.
        require(p.returncode == 0, 'GitHub request failed; check gh auth status locally')
        return loads(p.stdout.decode())

    def metadata(self):
        return self.api(f'repos/{self.repo}')

    def identity(self):
        return self.api('user')

    def issue(self, number):
        return self.api(f'repos/{self.repo}/issues/{number}')

    def messages(self, number):
        issue = self.issue(number)
        if issue['state'] != 'open':
            return issue, []
        pages = self.api(f'repos/{self.repo}/issues/{number}/comments?per_page=100', pages=True)
        return issue, [issue] + [comment for page in pages for comment in page]

    def post(self, number, body):
        return self.api(f'repos/{self.repo}/issues/{number}/comments', 'POST', {'body': body})


def version_probe(program):
    executable = shutil.which(program)
    if not executable:
        return {'installed': False, 'version': None}
    try:
        with tempfile.TemporaryFile() as output:
            p = subprocess.run([executable, '--version'], stdin=subprocess.DEVNULL,
                               stdout=output, stderr=subprocess.STDOUT, timeout=12)
            output.seek(0)
            text = output.read(4096).decode('utf-8', errors='replace')
        # Return only a version token, never executable paths or full stdout.
        match = re.search(r'(?<!\d)(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.]+)?)', text)
        return {'installed': True, 'version': match[1] if p.returncode == 0 and match else None}
    except (OSError, subprocess.TimeoutExpired):
        return {'installed': True, 'version': None}


def probe():
    return {'os': platform.system(), 'architecture': platform.machine(),
            'python': platform.python_version(),
            'programs': {name: version_probe(name) for name in ('gh', 'claude', 'codex', 'lean', 'lake', 'docker')},
            'model_inference_performed': False, 'local_files_uploaded': False,
            'auth_entitlement_tested': False}


@contextmanager
def state_store(root):
    root = Path(root).expanduser()
    require(not root.is_symlink(), 'State directory must not be a symlink')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(root.stat().st_uid == os.getuid() and root.stat().st_mode & 0o077 == 0,
            'State directory must be owned by you with mode 700')
    with (root / 'worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BridgeError('Another worker holds this state directory') from exc
        db = sqlite3.connect(root / 'jobs.sqlite3')
        db.execute('CREATE TABLE IF NOT EXISTS jobs (key TEXT PRIMARY KEY, request_hash TEXT NOT NULL, response TEXT)')
        db.commit()
        try:
            yield root.resolve(), db
        finally:
            db.close()


def run_profile(profile, job, run_dir, cancelled):
    """Run an operator-selected argv, without a shell. Payload arrives on stdin.

    The operator must provide isolation in the chosen profile. Removing credential
    environment variables does not stop a same-user subprocess reading the host.
    """
    require(isinstance(profile, dict) and set(profile) == {'argv', 'timeout_seconds'}, 'Invalid local profile')
    argv = profile['argv']
    require(isinstance(argv, list) and argv and all(isinstance(s, str) for s in argv), 'Invalid local argv')
    require(Path(argv[0]).is_absolute() and os.access(argv[0], os.X_OK), 'Profile executable must be an executable absolute path')
    limit = profile['timeout_seconds']
    require(type(limit) is int and 1 <= limit <= 7200, 'Profile timeout must be 1..7200 seconds')
    env = dict(os.environ)
    for name in ('GH_TOKEN', 'GITHUB_TOKEN', 'GH_ENTERPRISE_TOKEN', 'GITHUB_ENTERPRISE_TOKEN', 'SSH_AUTH_SOCK'):
        env.pop(name, None)
    env['LEANGLISH_JOB_DIR'] = str(run_dir)
    env['LEANGLISH_JOB_ID'] = job['job_id']
    start = time.monotonic()
    (run_dir / 'request.json').write_text(canonical(job) + '\n')
    cause = None
    with (run_dir / 'stdin.json').open('wb+') as inp, (run_dir / 'stdout.log').open('wb') as out, (run_dir / 'stderr.log').open('wb') as err:
        inp.write((canonical(job) + '\n').encode()); inp.seek(0)
        child = subprocess.Popen(argv, cwd=run_dir, stdin=inp, stdout=out, stderr=err,
                                 env=env, start_new_session=True)
        try:
            next_check = 0.0
            while child.poll() is None:
                elapsed = time.monotonic() - start
                if elapsed >= limit:
                    cause = 'timeout'; break
                if out.tell() + err.tell() > 20_000_000:
                    cause = 'output_limit'; break
                if elapsed >= next_check:
                    if cancelled():
                        cause = 'cancelled'; break
                    next_check = elapsed + 5
                time.sleep(0.2)
        finally:
            # Kill surviving descendants too; detached processes require a real sandbox.
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
    files = {}
    for name in ('stdout.log', 'stderr.log'):
        p = run_dir / name
        files[name] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
    # Logs remain local. A local supervisor can publish selected result artifacts
    # to an approved private destination, but this transport never uploads logs.
    return {'status': cause or ('completed' if child.returncode == 0 else 'failed'),
            'returncode': child.returncode, 'wall_seconds': round(time.monotonic() - start, 3),
            'logs': files, 'log_contents_uploaded': False}


class Worker:
    def __init__(self, api, config, root, db, enable_profiles=False, max_new_jobs=1, deadline=None):
        self.api, self.config, self.root, self.db = api, config, root, db
        self.enable_profiles = enable_profiles
        self.remaining_jobs = max_new_jobs
        self.deadline = deadline
        self.seen_messages = set()
        self.meta = api.metadata()
        require(self.meta['full_name'].lower() == config['repo'].lower(), 'Repository mismatch')
        require(type(self.meta['id']) is int, 'Missing stable repository ID')
        me = api.identity()
        require(me['id'] == config['controller_id'], 'Local GitHub login differs from the approved controller')

    def handle(self, message, approved_sha=None):
        if message.get('user', {}).get('id') != self.config['controller_id']:
            return None
        body = message.get('body', '')
        if not isinstance(body, str) or not body.startswith(REQUEST):
            return None
        job = parse_request(body)
        if job['worker'] != self.config['worker']:
            return None
        fingerprint = digest(job)
        if approved_sha is not None:
            require(fingerprint == approved_sha, 'Pairing request differs from the locally approved hash')
        key = f"{self.meta['id']}/{self.config['issue']}/{job['job_id']}"
        existing = self.db.execute('SELECT request_hash,response FROM jobs WHERE key=?', (key,)).fetchone()
        if existing:
            require(existing[0] == fingerprint, 'A prior job ID was reused with different content')
            if existing[1] is not None:
                response = loads(existing[1])
            else:
                response = self.reply(job, fingerprint, {'status': 'interrupted', 'rerun_performed': False})
                self.save(key, response)
        else:
            expires = datetime.fromisoformat(job['expires_at'].replace('Z', '+00:00'))
            require(expires > datetime.now(timezone.utc), 'Job has expired')
            if job['action'] == 'run_profile':
                require(self.meta.get('private') is True, 'Execution jobs require a private queue repository')
                require(self.enable_profiles, 'Profile execution was not enabled locally')
                require(job['profile'] in self.config.get('profiles', {}), 'Profile is not locally approved')
                require(self.remaining_jobs > 0, 'Local job limit reached')
                require(self.deadline is None or time.monotonic() < self.deadline, 'Local lease expired')
                self.remaining_jobs -= 1
            self.db.execute('INSERT INTO jobs VALUES (?,?,NULL)', (key, fingerprint)); self.db.commit()
            if job['action'] == 'probe':
                result = {'status': 'completed', 'capabilities': probe()}
            else:
                run_dir = self.root / hashlib.sha256(key.encode()).hexdigest()
                run_dir.mkdir(mode=0o700)
                try:
                    profile = dict(self.config['profiles'][job['profile']])
                    if self.deadline is not None:
                        profile['timeout_seconds'] = min(profile['timeout_seconds'], max(1, int(self.deadline - time.monotonic())))
                    result = run_profile(profile, job, run_dir,
                        lambda: self.api.issue(self.config['issue'])['state'] != 'open')
                except Exception as exc:
                    result = {'status': 'failed', 'error_class': type(exc).__name__, 'details_retained_locally': False}
            response = self.reply(job, fingerprint, result)
            self.save(key, response)
        result_body = envelope(RESPONSE, response)
        require(len(result_body.encode()) < MAX_REPLY, 'Response too large')
        _, messages = self.api.messages(self.config['issue'])
        # A lost POST response does not cause the model operation to be repeated.
        # Recheck for the exact response before posting again. This is not a
        # distributed exactly-once guarantee; use one worker/state directory.
        if not any(m.get('user', {}).get('id') == self.config['controller_id'] and m.get('body') == result_body for m in messages):
            self.api.post(self.config['issue'], result_body)
        return response

    def reply(self, job, fingerprint, result):
        return {'schema': 'leanglish.agent-response/v1', 'job_id': job['job_id'],
                'request_sha256': fingerprint, 'worker': self.config['worker'],
                'repo_id': self.meta['id'], 'result': result}

    def save(self, key, response):
        self.db.execute('UPDATE jobs SET response=? WHERE key=?', (canonical(response), key)); self.db.commit()

    def poll(self):
        issue, messages = self.api.messages(self.config['issue'])
        require('pull_request' not in issue and issue['user']['id'] == self.config['controller_id'], 'Queue must be an owner-created issue')
        if issue['state'] != 'open':
            return False
        for message in messages:
            message_key = digest({'author': message.get('user', {}).get('id'), 'body': message.get('body')})
            if message_key in self.seen_messages:
                continue
            try:
                response = self.handle(message)
                self.seen_messages.add(message_key)
                if response:
                    print(canonical({'job_id': response['job_id'], 'status': response['result']['status']}), flush=True)
            except (ValueError, KeyError, TypeError) as exc:
                print(f'Rejected request: {type(exc).__name__}', file=sys.stderr)
        return True


def config_file(path):
    p = Path(path).expanduser()
    require(p.is_file() and not p.is_symlink() and p.stat().st_uid == os.getuid()
            and p.stat().st_mode & 0o022 == 0, 'Config must be locally owned and not writable by other users')
    cfg = loads(p.read_text())
    require(set(cfg) == {'repo', 'issue', 'controller_id', 'worker', 'state_dir', 'profiles'}, 'Invalid config fields')
    require(type(cfg['issue']) is int and cfg['issue'] > 0 and type(cfg['controller_id']) is int and cfg['controller_id'] > 0, 'Invalid issue/controller')
    require(isinstance(cfg['profiles'], dict), 'Profiles must be an object')
    return cfg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    pair = sub.add_parser('pair', help='One diagnostic job, no inference, then exit')
    pair.add_argument('--repo', required=True); pair.add_argument('--issue', required=True, type=int)
    pair.add_argument('--controller-id', required=True, type=int); pair.add_argument('--worker', required=True)
    pair.add_argument('--request-sha256', required=True)
    pair.add_argument('--state-dir', default='~/.local/state/leanglish-bridge')
    serve = sub.add_parser('serve', help='Poll one issue for a bounded local lease')
    serve.add_argument('--config', required=True)
    serve.add_argument('--lease-seconds', type=int, default=3600)
    serve.add_argument('--poll-seconds', type=int, default=15)
    serve.add_argument('--enable-profile-execution', action='store_true')
    serve.add_argument('--max-new-jobs', type=int, default=1)
    args = parser.parse_args()
    try:
        if args.command == 'pair':
            cfg = dict(repo=args.repo, issue=args.issue, controller_id=args.controller_id,
                       worker=args.worker, state_dir=args.state_dir, profiles={})
        else:
            cfg = config_file(args.config)
            require(1 <= args.lease_seconds <= 86400 and 5 <= args.poll_seconds <= 300
                    and 1 <= args.max_new_jobs <= 10, 'Invalid lease, poll interval or job count')
        with state_store(cfg['state_dir']) as (root, db):
            api = GitHub(cfg['repo'])
            deadline = None if args.command == 'pair' else time.monotonic() + args.lease_seconds
            worker = Worker(api, cfg, root, db, getattr(args, 'enable_profile_execution', False),
                            getattr(args, 'max_new_jobs', 1), deadline)
            if args.command == 'pair':
                issue = api.issue(cfg['issue'])
                require(issue['state'] == 'open' and 'pull_request' not in issue, 'Pairing issue is not open')
                require(parse_request(issue['body'])['action'] == 'probe', 'Pairing never executes agent jobs')
                result = worker.handle(issue, args.request_sha256)
                require(result is not None, 'Request author or worker does not match')
                print('Diagnostic reply posted to GitHub. No model was called. No service remains running.')
            else:
                end = deadline
                while time.monotonic() < end and worker.poll():
                    time.sleep(min(args.poll_seconds, max(0, end - time.monotonic())))
                print('Worker stopped. No new jobs will be started.')
        return 0
    except (BridgeError, ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f'Bridge stopped: {exc}', file=sys.stderr); return 1
    except KeyboardInterrupt:
        print('Worker stopped by operator; in-flight outcome may require review.', file=sys.stderr); return 130


if __name__ == '__main__':
    raise SystemExit(main())
