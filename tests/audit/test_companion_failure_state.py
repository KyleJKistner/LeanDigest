"""A failed native preflight must not leave an earlier successful observation."""
import json
from pathlib import Path
import subprocess
import sys

import proofreader


def test_failed_native_project_preflight_invalidates_old_green_summary(tmp_path):
    root = Path(proofreader.__file__).resolve().parents[1]
    output = tmp_path / "native-evidence"
    output.mkdir()
    summary = output / "observation.json"
    summary.write_text(json.dumps({"status": "passed", "previous_run": True}))
    # The LeanDigest checkout is deliberately not the pinned Mathlib project.
    # This fails before any Lean code executes or dependencies are downloaded.
    result = subprocess.run([sys.executable, str(root / "scripts/check_bezout_companion.py"),
        "--project", str(root), "--output", str(output), "--trust-project"],
        capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert not summary.exists() or json.loads(summary.read_bytes())["status"] == "failed"
