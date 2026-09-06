"""The freeze must be enforced by the code, not only by the sidecar files.

AUDIT-2026-08-08 B2: `frozen_inputs()` and `contract_sha256()` used to read the
text of `corpus/stimuli.sha256` / `labeling/labels.sha256` instead of hashing the
artifacts, so editing either artifact left the contract, the cache stamp and
`run_meta.json` completely unchanged. These tests fail if that regresses.
"""
import hashlib
import json
from pathlib import Path

import pytest

import judging.profile_judge as PJ
import judging.run_study as RS

ROOT = Path(__file__).resolve().parents[1]
SIDECARS = [(ROOT / "corpus/stimuli.jsonl", ROOT / "corpus/stimuli.sha256"),
            (ROOT / "labeling/labels.jsonl", ROOT / "labeling/labels.sha256")]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_recorded_sidecars_match_their_artifacts():
    for artifact, sidecar in SIDECARS:
        assert sidecar.read_text().split()[0] == _sha(artifact), artifact


def test_frozen_inputs_hashes_the_artifact_not_the_sidecar(tmp_path, monkeypatch):
    """Point the runner at a copy of the repo whose sidecar lies; it must refuse."""
    import shutil
    fake = tmp_path / "repo"
    for artifact, sidecar in SIDECARS:
        (fake / artifact.parent.relative_to(ROOT)).mkdir(parents=True, exist_ok=True)
        shutil.copy2(artifact, fake / artifact.relative_to(ROOT))
        shutil.copy2(sidecar, fake / sidecar.relative_to(ROOT))
    for sub in ("profiles/profiles.yaml", "vendor/configs/models.yaml",
                "vendor/analysis/judge_pedagogy.py", "judging/profile_judge.py",
                "judging/run_study.py", "requirements.txt",
                "corpus/candidates_topup.jsonl",
                "vendor/supplement/judge_pedagogy_rubric.md",
                "analysis/analyze.py", "protocol/PREREGISTRATION.md"):
        (fake / sub).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / sub, fake / sub)
    monkeypatch.setattr(RS, "ROOT", fake)

    assert RS.frozen_inputs()["stimuli_sha256"] == _sha(ROOT / "corpus/stimuli.jsonl")

    # append a byte to the artifact and leave the sidecar alone
    target = fake / "corpus/stimuli.jsonl"
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(SystemExit, match="FROZEN INPUT MISMATCH"):
        RS.frozen_inputs()


def test_contract_changes_when_a_stimulus_changes(tmp_path, monkeypatch):
    """Swapping one stimulus's poles must move contract_sha256 even if the sidecar
    is left untouched; that edit flips the sign of that stimulus's Delta."""
    import shutil
    fake = tmp_path / "repo"
    (fake / "corpus").mkdir(parents=True)
    (fake / "profiles").mkdir(parents=True)
    for sub in ("corpus/stimuli.jsonl", "corpus/stimuli.sha256",
                "profiles/profiles.yaml", "judging/profile_judge.py",
                "judging/run_study.py", "vendor/analysis/judge_pedagogy.py"):
        (fake / sub).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / sub, fake / sub)
    monkeypatch.setattr(PJ, "ROOT", fake)

    spec = RS.judge_spec()["spec"]
    before = PJ.contract_sha256(spec)

    rows = [json.loads(l) for l in (fake / "corpus/stimuli.jsonl").read_text().splitlines()]
    rows[0]["r_high"], rows[0]["r_low"] = rows[0]["r_low"], rows[0]["r_high"]
    (fake / "corpus/stimuli.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n")

    assert PJ.contract_sha256(spec) != before, (
        "contract_sha256 did not move when the stimuli changed — the freeze is "
        "trusting the sidecar again")


def test_contract_changes_when_executed_request_code_changes(tmp_path, monkeypatch):
    import shutil
    fake = tmp_path / "repo"
    for sub in ("corpus/stimuli.jsonl", "profiles/profiles.yaml",
                "judging/profile_judge.py", "judging/run_study.py",
                "vendor/analysis/judge_pedagogy.py"):
        (fake / sub).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / sub, fake / sub)
    monkeypatch.setattr(PJ, "ROOT", fake)
    spec = RS.judge_spec()["spec"]
    before = PJ.contract_sha256(spec)
    path = fake / "judging/run_study.py"
    path.write_text(path.read_text() + "\n# transport mutation\n")
    assert PJ.contract_sha256(spec) != before


def test_live_git_freeze_requires_tag_and_rejects_unexpected_drift(monkeypatch):
    monkeypatch.setattr(RS, "_git_freeze_snapshot", lambda allow_runtime_results=False: {
        "git_commit": "abc", "git_tags_at_head": ["prereg-final-test"],
        "unexpected_git_status": [" M analysis/analyze.py"]})
    with pytest.raises(SystemExit, match="FROZEN TREE TO BE CLEAN"):
        RS.require_git_freeze(allow_runtime_results=True)

    monkeypatch.setattr(RS, "_git_freeze_snapshot", lambda allow_runtime_results=False: {
        "git_commit": "abc", "git_tags_at_head": [], "unexpected_git_status": []})
    with pytest.raises(SystemExit, match="REQUIRES A TAG AT HEAD"):
        RS.require_git_freeze()

    monkeypatch.setattr(RS, "_git_freeze_snapshot", lambda allow_runtime_results=False: {
        "git_commit": "abc", "git_tags_at_head": ["prereg-final-test"],
        "unexpected_git_status": []})
    assert RS.require_git_freeze(allow_runtime_results=True) == {
        "git_commit": "abc", "git_freeze_tags": ["prereg-final-test"]}


def test_analyze_refuses_stimuli_that_changed_since_scoring(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "lve_analyze_freeze", ROOT / "analysis/analyze.py")
    AN = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(AN)

    (tmp_path / "corpus").mkdir()
    (tmp_path / "corpus/stimuli.jsonl").write_text('{"stimulus_id": "S01"}\n')
    monkeypatch.setattr(AN, "ROOT", tmp_path)

    good = _sha(tmp_path / "corpus/stimuli.jsonl")
    AN.assert_stimuli_unchanged({"frozen_inputs": {"stimuli_sha256": good}})
    with pytest.raises(SystemExit, match="STIMULI CHANGED SINCE SCORING"):
        AN.assert_stimuli_unchanged({"frozen_inputs": {"stimuli_sha256": "0" * 64}})
    with pytest.raises(SystemExit, match="records no stimuli hash"):
        AN.assert_stimuli_unchanged({"frozen_inputs": {}})
