"""Fast, offline validation of changed Markdown and persistent project summaries."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

CORE = ('docs/SIMPLE-BOARD.md', 'docs/PROJECT-HANDOFF.md', 'docs/WORK-HANDOFF.md', 'AGENTS.md')


def prose(text):
    lines = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if marker:
            value, tail = marker.groups()
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence) and not tail.strip():
                fence = None
            continue
        if fence is None:
            lines.append(re.sub(r'`+[^`]*`+', '', line))
    if fence is not None:
        raise ValueError('unclosed_code_fence')
    return '\n'.join(lines)


def local_links(path):
    text = path.read_text(encoding='utf-8')
    if re.search(r'^(<<<<<<< |=======\s*$|>>>>>>> )', text, re.M):
        raise ValueError('merge_conflict_marker:' + str(path))
    body = prose(text)
    targets = re.findall(r'!?\[[^\]\n]*\]\(<?([^\s)>]+)>?(?:\s+"[^"\n]*")?\)', body)
    targets += re.findall(r'^ {0,3}\[[^\]\n]+\]:\s*<?([^\s>]+)>?', body, re.M)
    for target in targets:
        link = urlsplit(target)
        if link.scheme or link.netloc or not link.path:
            continue
        if link.path.startswith('/'):
            continue  # Historical absolute owner paths are not portable repo links.
        yield path.parent / unquote(link.path)


def validate(root, changed):
    targets = {root / name for name in CORE}
    targets.update(root / p for p in changed if p.endswith('.md') and (root / p).is_file())
    for path in sorted(targets):
        for target in local_links(path):
            if not target.exists():
                raise ValueError(f'broken_local_link:{path.relative_to(root)}:{target}')
    # Renames are delete/add: catch unchanged documents newly broken by a deletion.
    deleted = {(root / p).resolve() for p in changed if not (root / p).exists()}
    if deleted:
        tracked = subprocess.check_output(['git', 'ls-files', '-z', '*.md'], cwd=root).split(b'\0')
        for name in filter(None, tracked):
            path = root / name.decode('utf-8')
            if path.is_file():
                for target in local_links(path):
                    if target.resolve() in deleted:
                        raise ValueError('deleted_link_target:' + str(path.relative_to(root)))
    print(f'PASS: {len(targets)} Markdown files; UTF-8, conflict markers, fences and local links')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    validate(Path.cwd(), json.loads(args.manifest.read_text())['paths'])
