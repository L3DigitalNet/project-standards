# toolname

One-line description.

## Quick start

Run directly:

```bash
./toolname --help
```

Or, if your runtime requires an interpreter/runner:

```bash
runtime toolname --help
```

## Synopsis

```bash
toolname [OPTIONS] <input>
toolname (--help | --version)
```

## Common tasks

### Inspect a file

```bash
toolname inspect ./input.txt
```

### Write output to a file

```bash
toolname inspect --output result.txt ./input.txt
```

### Preview changes

```bash
toolname apply --dry-run ./workspace
```

## Options summary

- `-h`, `--help` — show help and exit
- `-V`, `--version` — show version and exit
- `-v`, `--verbose` — increase diagnostic output
- `-o`, `--output <file>` — write output to a file
- `-n`, `--dry-run` — preview actions without changing anything

For full option details, run:

```bash
./toolname --help
```

## Exit status

- `0` success
- `1` runtime failure
- `2` usage error, if the selected parser uses that convention

Replace this example list with the executable's actual exit contract; do not infer code `2` from the implementation language.

## Environment

- `NO_COLOR` — disable ANSI color output
- `TOOLNAME_*` — project-specific defaults, if supported

## Notes

- Relative paths are resolved from the current working directory.
- Prefer `--dry-run` before destructive operations.
