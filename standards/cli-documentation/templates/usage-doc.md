# toolname

## NAME

`toolname` — one-line description of the command.

## SYNOPSIS

```bash
toolname [OPTIONS] <input>
toolname <command> [COMMAND OPTIONS] [ARGS]...
toolname {--help | --version}
```

## DESCRIPTION

Explain what the command does, what problem it solves, what it does not do, and the default operating model. Mention stdin/stdout/stderr behavior if relevant.

## OPTIONS

### Global options

#### `--help`, `-h`

Show help and exit.

#### `--version`, `-V`

Show version information and exit.

#### `--verbose`, `-v`

Increase diagnostic output.

Default: off.

#### `--output <file>`, `-o <file>`

Write primary output to `<file>` instead of standard output.

Default: standard output.

Environment: overrides `TOOLNAME_OUTPUT`.

### Command options

#### `--format <fmt>`, `-f <fmt>`

Select the output format.

Allowed values: `text`, `json`, `markdown`.

Default: `text`.

Mutually exclusive with `--raw`.

Since: `1.2.0`.

#### `--jobs <n>`, `-j <n>`

Run up to `<n>` tasks concurrently.

Allowed values: positive integers.

Default: number of available CPUs.

Mutually exclusive with `--sequential`.

Safety: higher values may increase system load and remote API rate usage.

Environment: overrides `TOOLNAME_JOBS`.

## EXIT STATUS

| Code | Meaning                          |
| ---- | -------------------------------- |
| `0`  | Success                          |
| `1`  | Runtime or operational failure   |
| `2`  | Usage error or invalid arguments |

## ENVIRONMENT

- `TOOLNAME_FORMAT` — default format when `--format` is not provided.
- `NO_COLOR` — disable ANSI color output when supported.

## FILES

- `$XDG_CONFIG_HOME/toolname/config.toml` — optional per-user configuration.
- `$XDG_STATE_HOME/toolname/` — optional state directory.

## EXAMPLES

### Validate one file

```bash
toolname check ./input.txt
```

### Write JSON output to a file

```bash
toolname inspect --format json --output report.json ./input.txt
```

### Preview a destructive operation

```bash
toolname apply --dry-run ./workspace
```

### Export Markdown without ANSI color

```bash
NO_COLOR=1 toolname report --format markdown ./input > report.md
```

## NOTES

- Output format is stable within a major version.
- Paths are interpreted relative to the current working directory unless absolute.

## SEE ALSO

`toolname-config(5)`, related-command(1)
