import shutil
import subprocess
import sys
from pathlib import Path

GENERATOR = Path(__file__).parents[1] / "docs/handoff/bugs/_regen_index.py"


def test_regeneration__single_quoted_frontmatter__renders_plain_index_values(
    tmp_path: Path,
) -> None:
    bugs = tmp_path / "bugs"
    bugs.mkdir()
    generator = bugs / "_regen_index.py"
    shutil.copyfile(GENERATOR, generator)
    (bugs / "007-quoted-fields.md").write_text(
        """---
bug_id: '007'
date: '2026-07-19'
title: 'quoted bug index fields'
services: '[handoff, docs]'
status: 'fixed'
---

# Fixture
""",
        encoding="utf-8",
    )

    subprocess.run([sys.executable, str(generator)], check=True)

    index = (bugs / "INDEX.md").read_text(encoding="utf-8")
    assert "| 007 | 2026-07-19 | quoted bug index fields | handoff, docs | fixed |" in index
    assert "'007'" not in index
    assert "[handoff, docs]" not in index
