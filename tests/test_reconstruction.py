"""Byte-identical reconstruction of every stimulus from corpus/logs (Phase 7)."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_stimuli_rebuild_byte_identical_from_corpus_logs():
    if not (ROOT / "corpus/stimuli.jsonl").exists():
        pytest.skip("corpus/stimuli.jsonl not frozen yet")
    r = subprocess.run([sys.executable, str(ROOT / "corpus/build_stimuli.py"), "verify"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "verify PASS" in r.stdout
