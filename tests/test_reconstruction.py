"""Byte-identical reconstruction of every stimulus from corpus/logs (Phase 7)."""
import subprocess
import sys
import shutil
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


def test_frozen_construction_recipes_rebuild_final_stimuli(tmp_path):
    """Replay top-up through freeze in isolation; candidate IDs must not drift."""
    fake = tmp_path / "repo"
    shutil.copytree(
        ROOT, fake,
        ignore=shutil.ignore_patterns(".git", "results", "__pycache__", ".pytest_cache"))
    (fake / "corpus/candidates.jsonl").write_bytes(
        (fake / "corpus/candidates.pre-topup.jsonl").read_bytes())
    script = fake / "corpus/build_stimuli.py"
    commands = [
        [sys.executable, str(script), "topup", "-n", "30"],
        [sys.executable, str(script), "select"],
        [sys.executable, str(script), "assemble"],
        [sys.executable, str(script), "freeze", "--src-logs", str(ROOT / "corpus/logs")],
        [sys.executable, str(script), "verify"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=fake, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
    assert (fake / "corpus/candidates.jsonl").read_bytes() == \
           (ROOT / "corpus/candidates.jsonl").read_bytes()
    assert (fake / "corpus/selection.json").read_bytes() == \
           (ROOT / "corpus/selection.json").read_bytes()
    assert (fake / "corpus/pairing_draft.jsonl").read_bytes() == \
           (ROOT / "corpus/pairing_draft.jsonl").read_bytes()
    assert (fake / "corpus/stimuli.jsonl").read_bytes() == \
           (ROOT / "corpus/stimuli.jsonl").read_bytes()
