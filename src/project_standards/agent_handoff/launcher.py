"""Runtime probe for the interpreter a pre-1.8 SessionStart launcher depends on.

Package versions 1.1 through 1.7 register the hook as a bare path to
`session_start.py`, whose `#!/usr/bin/env python3` shebang resolves the
interpreter from `PATH` at startup. 1.8 replaced that registration with an
interpreter probe that falls back to `uv run` (issue #80), and 1.10 replaced the
script with a compiled executable that consults `PATH` for nothing at all. Only
the pre-1.8 window is exposed to whatever `python3` happens to be first.

Those payloads are immutable, so the diagnostic cannot live in them, and the
condition is not visible in repository bytes at all: the composition is
*correct* — the managed hook, its mode, and both registrations match the
selected payload exactly — while the launcher still cannot start. That is why
`validate` and `drift-check` reported clean for a consumer whose sessions were
silently injecting nothing (issues #138, #141). The engine is the only side that
can observe the runtime, so the probe lives here and its finding is raised by
the command layer rather than by any selected provider.

The probe is the same expression 1.8's launcher runs, deliberately: a shim that
rejects `python3` invocations, a missing interpreter, and an interpreter older
than the hook's 3.14 floor are one failure class from the consumer's side —
automatic startup is registered and cannot run — and all three are answered by
the same upgrade.
"""

from __future__ import annotations

import shutil
import subprocess

from project_standards.package_contract.paths import PackageVersion

# The first version whose registration no longer resolves `python3` from `PATH`.
_PATH_INTERPRETER_FLOOR = (1, 8)

# Byte-for-byte the condition 1.8's registered launcher evaluates before it
# execs the hook. Keeping them identical is what makes a green probe evidence
# about the launcher rather than about Python in general.
_PROBE = "import sys; raise SystemExit(sys.version_info < (3, 14))"

_PROBE_TIMEOUT_SECONDS = 10.0


def resolves_interpreter_from_path(version: PackageVersion) -> bool:
    """Report whether this package version's launcher depends on `PATH` `python3`."""
    return (version.major, version.minor) < _PATH_INTERPRETER_FLOOR


def path_interpreter_starts_the_hook() -> bool:
    """Report whether the first `python3` on `PATH` can run the pre-1.8 hook.

    Any failure to prove otherwise answers False. A probe that cannot be spawned
    is exactly the case a shebang launcher cannot recover from either, so
    treating an unspawnable interpreter as usable would report clean for the
    repository that most needs the finding.
    """
    interpreter = shutil.which("python3")
    if interpreter is None:
        return False
    try:
        completed = subprocess.run(
            # A fixed argument vector against the resolved interpreter: the shebang
            # launcher selects the same file, and no consumer value reaches the call.
            [interpreter, "-c", _PROBE],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        return False
    return completed.returncode == 0
