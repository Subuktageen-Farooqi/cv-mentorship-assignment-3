from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


def _find_project_root() -> Path:
    cwd = Path.cwd()

    direct = cwd / "app" / "main.py"
    if direct.exists():
        return cwd

    for candidate in cwd.iterdir():
        if not candidate.is_dir():
            continue
        nested = candidate / "app" / "main.py"
        if nested.exists():
            return candidate

    raise FileNotFoundError(
        "Could not find 'app/main.py'. Run this command from the repository root "
        "or its immediate parent directory."
    )


def main() -> None:
    root = _find_project_root()
    sys.path.insert(0, str(root))
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, app_dir=str(root))


if __name__ == "__main__":
    main()
