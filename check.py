#!/usr/bin/env python3
import argparse
import filecmp
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import PurePosixPath

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(ROOT, 'sources')
OUT = os.path.join(ROOT, 'out')
FORMATTED = os.path.join(ROOT, 'formatted')
BIN = os.environ.get('ASM_FORMAT') or os.path.join(ROOT, '..', 'asm-format', 'target', 'release', 'asm-format')


def matching(root, patterns, exclude=()):
    found = set()
    for pattern in patterns:
        for path in glob.glob(pattern, root_dir=root, recursive=True):
            if os.path.isfile(os.path.join(root, path)) and not any(
                    PurePosixPath(path).full_match(e) for e in exclude):
                found.add(path)
    return sorted(found)


def run_batches(args, files, cwd):
    lines = []
    for i in range(0, len(files), 500):
        r = subprocess.run([BIN, *args, *files[i:i + 500]], cwd=cwd, capture_output=True, text=True)
        lines += [line for line in r.stderr.splitlines() if ': error: ' in line or ': warning: ' in line]
    return lines


def objdump(path):
    r = subprocess.run(['llvm-objdump', '-d', '-r', '-s', path], capture_output=True, text=True)
    return r.stdout.split('\n', 2)[-1] if r.returncode == 0 else None


def assemble(command, tree, path, out):
    cmd = command.replace('{file}', path).replace('{out}', out)
    return subprocess.run(['bash', '-c', cmd], cwd=tree, capture_output=True).returncode == 0


def verify(p, src, out, log):
    same = differ = skipped = 0
    for v in p.get('verify', []):
        with tempfile.TemporaryDirectory() as tmp:
            for path in matching(src, v['files']):
                a, b = os.path.join(tmp, 'a'), os.path.join(tmp, 'b')
                if not assemble(v['command'], src, path, a):
                    skipped += 1
                    continue
                ok = assemble(v['command'], out, path, b)
                if ok and v.get('compare') == 'bytes':
                    ok = filecmp.cmp(a, b, shallow=False)
                elif ok:
                    ok = objdump(a) == objdump(b)
                if ok:
                    same += 1
                else:
                    differ += 1
                    log.append(f'{path}: assembled result differs')
    return same, differ, skipped


def check(p, run_verify):
    name = p['name']
    src = os.path.join(SOURCES, name)
    out = os.path.join(OUT, name)
    orig = out + '.orig'
    trees = [out, orig] if run_verify else [out]
    for tree in [out, orig]:
        shutil.rmtree(tree, ignore_errors=True)
    for tree in trees:
        shutil.copytree(src, tree)
        if 'setup' in p:
            subprocess.run(['bash', '-c', p['setup']], cwd=tree, check=True)
    with open(os.path.join(out, '.asm-format'), 'w') as f:
        f.write(p['style'])
    files = matching(src, p['files'], p.get('exclude', []))
    errors = run_batches(['-i'], files, out)
    failed = {line.split(': error: ')[0] for line in errors}
    unstable = [line for line in run_batches(['-n', '--Werror'], files, out)
                if line.split(':')[0] not in failed]
    changed = sum(not filecmp.cmp(os.path.join(src, f), os.path.join(out, f), shallow=False) for f in files)
    log = errors + unstable
    same, differ, skipped = verify(p, orig, out, log) if run_verify else (0, 0, 0)
    with open(os.path.join(OUT, f'{name}.log'), 'w') as f:
        f.write(''.join(line + '\n' for line in log))
    summary = f'{name:14} {len(files):6} files {changed:6} changed {len(failed):5} errors {len(unstable):5} unstable'
    if run_verify:
        summary += f'   assembled: {same} same, {differ} differ, {skipped} skipped'
    print(summary, flush=True)


def dump(*args, cwd=None):
    out = subprocess.run([BIN, '--dump-config', *args], cwd=cwd, capture_output=True, text=True, check=True).stdout
    return '\n'.join(line for line in out.splitlines() if line not in ('---', '...'))


def configs(style, files):
    """The options for each file, as printed by --dump-config, and the index of each file's options."""
    rules = [json.loads(globs) for globs in re.findall(r'-\s*Files:\s*(\[.*?\])', style)]
    texts, which, seen = [], [], {}
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, '.asm-format'), 'w') as f:
            f.write(style)
        for f in files:
            key = tuple(i for i, globs in enumerate(rules) if any(PurePosixPath(f).full_match(g) for g in globs))
            if key not in seen:
                seen[key] = len(texts)
                texts.append(dump('--assume-filename', f, cwd=d))
            which.append(seen[key])
    return texts, which


def git(*args, cwd=ROOT, check=True):
    return subprocess.run(['git', *args], cwd=cwd, check=check, capture_output=True, text=True)


def version():
    where = os.path.dirname(os.path.realpath(BIN))
    head = git('rev-parse', '--short', 'HEAD', cwd=where, check=False)
    if head.returncode != 0:
        return subprocess.run([BIN, '--version'], capture_output=True, text=True).stdout.strip()
    dirty = git('status', '--porcelain', '--untracked-files=no', cwd=where).stdout.strip()
    return head.stdout.strip() + ('-dirty' if dirty else '')


def listing(projects):
    stats = {}
    for p in projects:
        diff = git('diff', '--no-index', '--numstat', f"sources/{p['name']}", f"formatted/{p['name']}", check=False)
        for line in diff.stdout.splitlines():
            added, removed, path = line.split('\t')
            if path.startswith('{sources => formatted}/'):
                stats[path.removeprefix('{sources => formatted}/')] = [int(added), int(removed)]
    result = {'asm-format': version(), 'defaults': dump('--style', '{}'), 'projects': []}
    for p in projects:
        files = matching(os.path.join(SOURCES, p['name']), p['files'], p.get('exclude', []))
        texts, which = configs(p['style'], files)
        result['projects'].append({'name': p['name'], 'style': p['style'].strip(), 'configs': texts, 'files': [
            [f, *stats.get(f"{p['name']}/{f}", [0, 0]), d] for f, d in zip(files, which)]})
    return result


def publish(projects, ran, commit):
    for p in ran:
        target = os.path.join(FORMATTED, p['name'])
        shutil.rmtree(target, ignore_errors=True)
        for f in matching(os.path.join(SOURCES, p['name']), p['files'], p.get('exclude', [])):
            os.makedirs(os.path.dirname(os.path.join(target, f)), exist_ok=True)
            shutil.copyfile(os.path.join(OUT, p['name'], f), os.path.join(target, f))
    present = [p for p in projects if os.path.isdir(os.path.join(FORMATTED, p['name']))]
    result = listing(present)
    with open(os.path.join(ROOT, 'files.json'), 'w') as f:
        json.dump(result, f, separators=(',', ':'))
    if not commit:
        return
    git('add', 'formatted', 'files.json')
    if git('diff', '--cached', '--quiet', '--', 'formatted', 'files.json', check=False).returncode == 0:
        print('formatted: no changes')
        return
    git('commit', '-q', '-m', f"Format with asm-format {result['asm-format']}", '--', 'formatted', 'files.json')
    print('formatted:', git('rev-parse', '--short', 'HEAD').stdout.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*')
    parser.add_argument('--verify', action='store_true', help='assemble both trees and compare')
    parser.add_argument('--commit', action='store_true', help='commit formatted/ and files.json')
    args = parser.parse_args()
    with open(os.path.join(ROOT, 'projects.toml'), 'rb') as f:
        projects = tomllib.load(f)['project']
    os.makedirs(OUT, exist_ok=True)
    ran = [p for p in projects if not args.names or p['name'] in args.names]
    for p in ran:
        check(p, args.verify)
    publish(projects, ran, args.commit)


if __name__ == '__main__':
    main()
