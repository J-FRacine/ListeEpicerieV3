# Généré automatiquement par refactor_finances_flat.py
# Les fragments sont placés directement à la racine pour faciliter l'upload GitHub.
from __future__ import annotations

from pathlib import Path as _Path

_BASE = _Path(__file__).parent
_PARTS = sorted(_BASE.glob("finances_part_*.pyfrag"))

if not _PARTS:
    raise RuntimeError(
        "Fragments Finances introuvables pour finances.py"
    )

_source = "".join(
    part.read_text(encoding="utf-8")
    for part in _PARTS
)

exec(
    compile(
        _source,
        str(_BASE / "finances.py"),
        "exec",
    ),
    globals(),
    globals(),
)

del _source, _PARTS, _BASE, _Path
