#!/usr/bin/env python3
import argparse
import filecmp
import glob
import os
import shutil
import subprocess
import tempfile
import tomllib

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(ROOT, 'sources')
OUT = os.path.join(ROOT, 'out')
BIN = os.environ.get('ASM_FORMAT') or os.path.join(ROOT, '..', 'asm-format', 'target', 'release', 'asm-format')


def matching(root, patterns):
    found = set()
    for pattern in patterns:
        for path in glob.glob(pattern, root_dir=root, recursive=True):
            if os.path.isfile(os.path.join(root, path)):
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
    files = matching(src, p['files'])
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*')
    parser.add_argument('--verify', action='store_true', help='assemble both trees and compare')
    args = parser.parse_args()
    with open(os.path.join(ROOT, 'projects.toml'), 'rb') as f:
        projects = tomllib.load(f)['project']
    os.makedirs(OUT, exist_ok=True)
    for p in projects:
        if not args.names or p['name'] in args.names:
            check(p, args.verify)


if __name__ == '__main__':
    main()
