"""Public command alias. All parsing, execution and consent checks are shared."""
from __future__ import annotations

from proofreader.cli import main as proofreader_main


def main(argv: list[str] | None = None) -> int:
    return proofreader_main(argv, prog="leanglish")
