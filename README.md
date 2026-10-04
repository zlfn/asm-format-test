# asm-format-test

Tests [asm-format](https://github.com/llvm-z80/asm-format) on the assembly
sources of other projects listed in `projects.toml`.

[Compare the original and formatted sources](https://zlfn.github.io/asm-format-test/)

`sources/` holds the original files and `formatted/` the same files formatted
with asm-format.

```sh
python3 fetch.py
python3 check.py [--verify] [--commit]
```

`check.py` updates `formatted/` and `files.json`, and `--commit` commits them.
To view the page locally, run `python3 -m http.server` here and open
http://localhost:8000/.
