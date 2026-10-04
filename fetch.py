#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import tomllib

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(ROOT, 'sources')


def git(*args, cwd, check=True):
    return subprocess.run(['git', *args], cwd=cwd, check=check, capture_output=True, text=True)


def fetched(path):
    try:
        with open(os.path.join(path, '.commit')) as f:
            return f.read().strip()
    except OSError:
        return None


def fetch(p):
    dst = os.path.join(SOURCES, p['name'])
    if fetched(dst) == p['commit']:
        return 'up to date'
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst)
    git('init', '-q', cwd=dst)
    git('remote', 'add', 'origin', p['url'], cwd=dst)
    patterns = ['/' + g for g in p['files'] + p.get('extra', []) + p['licenses']]
    git('sparse-checkout', 'set', '--no-cone', *patterns, cwd=dst)
    r = git('fetch', '-q', '--depth', '1', '--filter=blob:none', 'origin', p['commit'], cwd=dst, check=False)
    if r.returncode != 0:
        git('fetch', '-q', '--depth', '1', 'origin', 'HEAD', cwd=dst)
    for attempt in range(3):
        if git('checkout', '-q', 'FETCH_HEAD', cwd=dst, check=attempt == 2).returncode == 0:
            break
    head = git('rev-parse', 'HEAD', cwd=dst).stdout.strip()
    if head != p['commit']:
        raise SystemExit(f"{p['name']}: fetched {head}, expected {p['commit']}")
    shutil.rmtree(os.path.join(dst, '.git'))
    with open(os.path.join(dst, '.commit'), 'w') as f:
        f.write(head + '\n')
    return 'fetched'


def main():
    with open(os.path.join(ROOT, 'projects.toml'), 'rb') as f:
        projects = tomllib.load(f)['project']
    names = set(sys.argv[1:])
    for p in projects:
        if names and p['name'] not in names:
            continue
        print(f"{p['name']}: {fetch(p)}", flush=True)


if __name__ == '__main__':
    main()
