from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.backend.config import settings  # noqa: E402
from src.backend.database import session as db_session  # noqa: E402
from src.backend.demo import rebuild_demo_dataset, reset_demo_dataset  # noqa: E402
from src.backend.demo.validator import validate_demo_dataset  # noqa: E402

_CONFIRM = "RESET-DEMO"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate or rebuild the synthetic demo dataset")
    parser.add_argument("command", choices=("validate", "reset", "rebuild"))
    parser.add_argument("--data-dir", default=settings.DEMO_DATA_DIR)
    parser.add_argument("--confirm", default="", help=f"Required for mutation: {_CONFIRM}")
    return parser


def _require_safe_runtime() -> None:
    if settings.DB_BACKEND != "sqlite":
        raise SystemExit("Demo reset/rebuild is limited to SQLite runtimes")
    if settings.APP_MODE not in {"local", "research", "demo"}:
        raise SystemExit("Demo reset/rebuild is disabled outside local/research/demo mode")


async def _mutate(command: str, data_dir: Path) -> dict:
    _require_safe_runtime()
    await db_session.ensure_db_initialized()
    if db_session.async_session_factory is None:
        raise RuntimeError("Database session factory is unavailable")
    try:
        if command == "reset":
            return {"deleted": await reset_demo_dataset(db_session.async_session_factory, data_dir)}
        return await rebuild_demo_dataset(db_session.async_session_factory, data_dir)
    finally:
        await db_session.close_db()


def main() -> int:
    args = _parser().parse_args()
    data_dir = Path(args.data_dir).expanduser().resolve()
    validation = validate_demo_dataset(data_dir)
    if args.command == "validate":
        print(json.dumps({"ok": validation.ok, "counts": validation.counts, "errors": validation.errors}, indent=2))
        return 0 if validation.ok else 2

    if not validation.ok:
        print(json.dumps({"ok": False, "errors": validation.errors}, indent=2))
        return 2
    if args.confirm != _CONFIRM:
        raise SystemExit(f"Refusing mutation without --confirm {_CONFIRM}")

    result = asyncio.run(_mutate(args.command, data_dir))
    print(json.dumps({"ok": True, "command": args.command, **result}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
