#!/usr/bin/env bash
# Build dist/validate-id.pyz — a self-contained Python zipapp for the validate-id
# validator.  Copy the output to any repo; run with:
#   python3 validate-id.pyz --config .project-standards.yml
#   python3 validate-id.pyz --fix --config .project-standards.yml
#
# What gets bundled:
#   - project_standards package (validate_id, validate_frontmatter, registry,
#     schemas/) — source-of-truth copy, no drift possible
#   - PyYAML pure Python (binary .so extension stripped; zipimport can't load it)
#   - Minimal jsonschema stub: validate_id never calls jsonschema functions; the
#     stub only exists because validate_frontmatter.py declares the import at the
#     top level.  jsonschema's real transitive dep (rpds-py, a Rust extension)
#     cannot be bundled in a zipapp, so we stub rather than bundle.
#
# Requires: Python 3.14+, uv
# Usage (from anywhere):
#   bash build-validate-id-pyz.sh
#   bash build-validate-id-pyz.sh /path/to/project-standards/src/project_standards
# Or via env var:
#   PS_SRC=/path/to/project-standards/src/project_standards bash build-validate-id-pyz.sh
# Default source: this repo's src/project_standards (falls back to ~/projects/project-standards)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Output goes next to the script (or its parent if inside a scripts/ subdir).
if [[ "$(basename "$SCRIPT_DIR")" == "scripts" ]]; then
    REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    REPO_DIR="$SCRIPT_DIR"
fi

# Source package: argument > env var > this repo > workstation fallback.
if [[ -n "${1:-}" ]]; then
    PS_PKG="$(cd "$1" && pwd)"
elif [[ -n "${PS_SRC:-}" ]]; then
    PS_PKG="$(cd "$PS_SRC" && pwd)"
elif [[ -d "$SCRIPT_DIR/../src/project_standards" ]]; then
    PS_PKG="$(cd "$SCRIPT_DIR/../src/project_standards" && pwd)"
elif [[ -d "$HOME/projects/project-standards/src/project_standards" ]]; then
    PS_PKG="$HOME/projects/project-standards/src/project_standards"
else
    echo "error: cannot find project_standards source." >&2
    echo "  Pass the path as an argument: $0 /path/to/project-standards/src/project_standards" >&2
    exit 1
fi
echo "→ source: $PS_PKG"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

echo "→ staging in $STAGING"

# ── 1. PyYAML (pure Python) ────────────────────────────────────────────────
# uv removed the legacy `uv pip install --target` interface; resolve PyYAML into
# an ephemeral uv environment and copy the yaml package out of it.  Copying only
# the `yaml/` directory drops the top-level `_yaml` C extension, so PyYAML uses
# its pure Python implementation — zipimport only handles pure Python modules.
uv run --quiet --no-project --with PyYAML python3 - "$STAGING" <<'EOF'
import pathlib
import shutil
import sys

import yaml

package = pathlib.Path(yaml.__file__).parent
shutil.copytree(package, pathlib.Path(sys.argv[1]) / "yaml")
EOF

# Strip compiled extensions bundled inside the package directory itself.
find "$STAGING" -name "*.so" -delete
find "$STAGING" -name "*.pyd" -delete

# ── 2. Minimal jsonschema stub ─────────────────────────────────────────────
# validate_frontmatter.py declares `from jsonschema import Draft202012Validator`
# and `from jsonschema.exceptions import SchemaError` at module level.
# validate_id.py imports from validate_frontmatter (triggering that top-level
# import) but never calls any jsonschema function itself.  These stubs make the
# import succeed without pulling in jsonschema's binary transitive deps.
mkdir -p "$STAGING/jsonschema"

cat > "$STAGING/jsonschema/exceptions.py" <<'EOF'
class SchemaError(Exception):
    pass
EOF

cat > "$STAGING/jsonschema/__init__.py" <<'EOF'
from .exceptions import SchemaError as SchemaError  # noqa: F401


class Draft202012Validator:
    def __init__(self, schema: object) -> None: ...
    def iter_errors(self, instance: object):
        raise NotImplementedError(
            "jsonschema is stubbed out in validate-id.pyz; schema validation is unavailable"
        )

    @classmethod
    def check_schema(cls, schema: object) -> None:
        raise NotImplementedError(
            "jsonschema is stubbed out in validate-id.pyz; schema validation is unavailable"
        )
EOF

# ── 3. project_standards package ──────────────────────────────────────────
cp -r "$PS_PKG" "$STAGING/project_standards"

# Remove bytecode — the zipapp compiler regenerates it on first run.
find "$STAGING/project_standards" -name "__pycache__" -type d \
    -exec rm -rf {} + 2>/dev/null || true

# ── 4. Entry point ────────────────────────────────────────────────────────
# project_standards reads two JSON data files at module-import time via
# Path(__file__).parent.  In a zipapp, that path resolves *inside* the zip
# file and pathlib.Path.read_text() raises NotADirectoryError.  We extract
# the full archive to a tempdir before importing so all Path reads hit real
# filesystem paths.
cat > "$STAGING/__main__.py" <<'EOF'
"""validate-id.pyz entry point.

Extracts the zip archive to a tempdir before importing the package so that
pathlib reads of bundled data files (schemas/*.json) hit real filesystem
paths rather than paths inside the zip (which pathlib cannot open).
"""
import atexit
import shutil
import sys
import tempfile
import zipfile
import zipimport

# Locate the zip archive reliably from the loader (more robust than argv[0]).
_loader = __loader__  # type: ignore[name-defined]
if isinstance(_loader, zipimport.zipimporter):
    _zip = _loader.archive
else:
    _zip = sys.path[0]  # fallback: Python always puts the zipapp at sys.path[0]

_tmpdir = tempfile.mkdtemp(prefix="validate-id-")
atexit.register(shutil.rmtree, _tmpdir, ignore_errors=True)
with zipfile.ZipFile(_zip) as _zf:
    _zf.extractall(_tmpdir)

# Prepend so extracted paths take precedence over the zip.
sys.path.insert(0, _tmpdir)

from project_standards.validate_id import main  # noqa: E402
sys.exit(main())
EOF

# ── 5. Bundle ─────────────────────────────────────────────────────────────
mkdir -p "$REPO_DIR/dist"
OUTPUT="$REPO_DIR/dist/validate-id.pyz"
python3 -m zipapp "$STAGING" --output "$OUTPUT" --python "/usr/bin/env python3"
chmod +x "$OUTPUT"

SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo "✓  built $OUTPUT ($SIZE)"
echo "   python3 dist/validate-id.pyz --help"
echo "   dist/validate-id.pyz --config .project-standards.yml"
