"""STK-081: conservative CI selection from the complete checked-out Git diff.

No API pagination/path-filter limits. Unknown paths or unavailable history select
all suites. This script also validates the stable required checks fan-in.
"""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

SUITES = ('unit', 'postgres', 'ui')


def documentation(path):
    p = PurePosixPath(path)
    return (path in ('README.md', 'AGENTS.md') or
            (path.startswith('docs/') and p.suffix == '.md' and
             not path.startswith(('docs/contracts/', 'docs/policies/', 'docs/licenses/'))))


def select(paths):
    required = set()
    if not paths:
        return dict.fromkeys(SUITES, True)
    for path in paths:
        parts = PurePosixPath(path).parts
        name = PurePosixPath(path).name.lower()
        if (not parts or path.startswith('/') or '..' in parts or
                any(word in name for word in ('security', 'auth', 'grant', 'permission', 'role',
                                              'session', 'cookie', 'login', 'secret', 'token', 'credential', 'access')) or
                name.startswith(('dockerfile', 'requirements')) or
                name in ('package.json', 'package-lock.json', 'pyproject.toml') or name.endswith('.lock')):
            return dict.fromkeys(SUITES, True)
        if documentation(path):
            continue
        if (path.startswith(('frontend/src/', 'frontend/tests/', 'frontend/public/')) and
                PurePosixPath(path).suffix.lower() in ('.ts', '.tsx', '.js', '.jsx', '.css', '.json',
                                                        '.svg', '.png', '.jpg', '.jpeg', '.ico', '.txt', '.csv')):
            required.add('ui')
        elif path.startswith(('backend/tests/', 'worker/tests/')) and 'chartink_delivery' not in name:
            required.update(('unit', 'postgres'))
        else:
            # Runtime Python reaches API/UI contracts. Workflow/dependency/schema,
            # fixtures under docs, infrastructure and unknown files all fail broad.
            required.update(SUITES)
    return {suite: suite in required for suite in SUITES}


def git(*args, cwd=None):
    return subprocess.check_output(['git', *args], cwd=cwd, stderr=subprocess.PIPE)


def changed_paths(event, event_name, checkout, cwd=None):
    """Compare the actual test tree, including merge resolution, to its event base."""
    if event_name == 'pull_request':
        base = event['pull_request']['base']['sha']
        head = event['pull_request']['head']['sha']
    elif event_name == 'push':
        base, head = event['before'], event['after']
        if checkout != head:
            raise ValueError('push_checkout_mismatch')
    else:
        raise ValueError('unsupported_event')
    for sha in (base, head, checkout):
        if not re.fullmatch(r'[0-9a-f]{40}', sha) or sha == '0' * 40:
            raise ValueError('invalid_or_initial_commit')
        git('cat-file', '-e', sha + '^{commit}', cwd=cwd)
    if git('rev-parse', 'HEAD', cwd=cwd).decode().strip() != checkout:
        raise ValueError('checkout_mismatch')
    if event_name == 'pull_request':
        git('merge-base', '--is-ancestor', base, checkout, cwd=cwd)
        git('merge-base', '--is-ancestor', head, checkout, cwd=cwd)
    raw = git('diff', '--no-ext-diff', '--no-renames', '--name-only', '-z', base, checkout, '--', cwd=cwd)
    return [p.decode('utf-8') for p in raw.split(b'\0') if p]


def plan(event, event_name, checkout, cwd=None):
    try:
        paths = changed_paths(event, event_name, checkout, cwd)
        return dict(required=select(paths), paths=paths, reason='complete_git_diff')
    except (KeyError, TypeError, ValueError, UnicodeError, subprocess.CalledProcessError):
        return dict(required=dict.fromkeys(SUITES, True), paths=[], reason='unavailable_diff_full_suite')


def verify_gate(needs):
    if set(needs) != {'changes', *SUITES} or needs['changes']['result'] != 'success':
        raise ValueError('selection_or_documentation_job_not_successful')
    outputs = needs['changes'].get('outputs', {})
    for suite in SUITES:
        selected = outputs.get(suite)
        if selected not in ('true', 'false'):
            raise ValueError('invalid_selection_output:' + suite)
        expected = 'success' if selected == 'true' else 'skipped'
        if needs[suite]['result'] != expected:
            raise ValueError('required_job_result_mismatch:' + suite)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gate', action='store_true')
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    if args.gate:
        verify_gate(json.loads(os.environ['CI_NEEDS_JSON']))
        print('PASS: required jobs succeeded; only explicitly unaffected suites skipped')
        return
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    result = plan(event, os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_SHA'])
    if args.manifest:
        args.manifest.write_text(json.dumps(result))
    with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
        for suite, selected in result['required'].items():
            out.write(f'{suite}={str(selected).lower()}\n')
    # JSON escapes changed filenames; they never enter shell commands or outputs.
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
