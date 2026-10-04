# asm-format-test

Tests [asm-format](https://github.com/llvm-z80/asm-format) on the assembly
sources of other projects listed in `projects.toml`.

- [Original and formatted sources](https://github.com/zlfn/asm-format-test/compare/main..formatted)
- [Last change of the formatted sources](https://github.com/zlfn/asm-format-test/commit/formatted)

`main` holds the original sources and `formatted` the same files formatted
with asm-format.

```sh
python3 fetch.py
python3 check.py [--verify] [--commit]
git push origin formatted
```

`--commit` adds the results to `formatted`.
