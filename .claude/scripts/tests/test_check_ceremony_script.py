"""Testes do check-ceremony-script.py (PLAN-174 W2).

Cobrem: caso-vermelho por classe BLOCKING (positive control do §2b),
re-arme de waiver por sha256, unlock sem motivo mantém bloqueio, piso
de descoberta, linha de autolimitação, e o controle positivo de escopo
sobre o corpus REAL (a classe R3 TEM de ser achada nos 4 run-*.sh de
PLAN-166/repass-*/ — debate r1 F4).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LINT = os.path.join(REPO_ROOT, ".claude", "scripts", "check-ceremony-script.py")


def run_lint(*args, env_extra=None, cwd=None):
    env = dict(os.environ)
    env.pop("CEO_CEREMONY_LINT_UNLOCK", None)
    env.pop("CEO_CEREMONY_LINT_UNLOCK_REASON", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, LINT, *args],
        capture_output=True, text=True, env=env, cwd=cwd or REPO_ROOT, timeout=120,
    )


def make_repo(tmp_path, body, name="OWNER-FIXTURE.sh", mode=0o644):
    root = tmp_path
    d = root / ".claude" / "plans" / "PLAN-999"
    d.mkdir(parents=True)
    f = d / name
    f.write_text(body)
    f.chmod(mode)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-f", "."], check=True)
    return root, f


BASE = "#!/bin/bash\n# fixture de cerimonia\ngit tag -s v0.0.0 || exit 1\n"


def _json_result(proc):
    assert proc.stdout, proc.stderr
    return json.loads(proc.stdout)


class TestRedFixturesPerBlockingClass:
    def test_r1_provenance_missing_is_blocking(self, tmp_path):
        root, _ = make_repo(tmp_path, BASE)
        p = run_lint("--root", str(root), "--floor", "1", "--json")
        d = _json_result(p)
        assert p.returncode == 1
        rules = {x["rule"] for f in d["files"] for x in f["findings"]}
        assert "R1" in rules

    def test_r1_exception_comment_passes(self, tmp_path):
        body = BASE + "# CEREMONY-LINT: handwritten-exception: fixture de teste\n"
        root, _ = make_repo(tmp_path, body)
        p = run_lint("--root", str(root), "--floor", "1", "--json")
        d = _json_result(p)
        rules = {x["rule"] for f in d["files"] for x in f["findings"]}
        assert "R1" not in rules

    def test_r2_or_true_on_irreversible_is_blocking(self, tmp_path):
        body = BASE + "gh release create v1 || true\n"
        root, _ = make_repo(tmp_path, body)
        p = run_lint("--root", str(root), "--floor", "1", "--json")
        d = _json_result(p)
        assert any(x["rule"] == "R2" for f in d["files"] for x in f["findings"])
        assert p.returncode == 1

    def test_r2a_bare_or_true_is_advisory_only(self, tmp_path):
        body = (BASE + "# CEREMONY-LINT: handwritten-exception: fixture\n"
                "rm -f /tmp/x || true\n")
        root, _ = make_repo(tmp_path, body)
        p = run_lint("--root", str(root), "--floor", "1", "--json")
        d = _json_result(p)
        assert d["advisory_rates"].get("R2a", 0) >= 1
        assert d["blocking_unwaived"] == 0
        assert p.returncode == 0

    def test_r3_grep_tail_is_blocking(self, tmp_path):
        body = BASE + "V=$(grep VERDICT out.md | tail -1)\n"
        root, _ = make_repo(tmp_path, body)
        p = run_lint("--root", str(root), "--floor", "1", "--json")
        d = _json_result(p)
        assert any(x["rule"] == "R3" for f in d["files"] for x in f["findings"])

    def test_r4_git_add_dir_is_blocking(self, tmp_path):
        body = BASE + "git add -A\n"
        root, _ = make_repo(tmp_path, body)
        p = run_lint("--root", str(root), "--floor", "1", "--json")
        d = _json_result(p)
        assert any(x["rule"] == "R4" for f in d["files"] for x in f["findings"])

    def test_r8_exec_bit_under_plans_is_blocking(self, tmp_path):
        body = BASE + "# CEREMONY-LINT: handwritten-exception: fixture\n"
        root, _ = make_repo(tmp_path, body, mode=0o755)
        p = run_lint("--root", str(root), "--floor", "1", "--json")
        d = _json_result(p)
        assert any(x["rule"] == "R8" for f in d["files"] for x in f["findings"])


class TestWaiverMechanics:
    def test_waiver_by_sha_passes_and_rearms_on_edit(self, tmp_path):
        root, f = make_repo(tmp_path, BASE)
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        wdir = root / ".claude" / "scripts"
        wdir.mkdir(parents=True, exist_ok=True)
        (wdir / "ceremony-lint-waivers.json").write_text(json.dumps(
            [{"sha256": sha, "path_hint": "x", "reason": "fixture", "date": "2026-08-20"}]))
        p = run_lint("--root", str(root), "--floor", "1", "--json")
        assert _json_result(p)["blocking_unwaived"] == 0
        assert p.returncode == 0
        # edicao re-arma: sha muda, waiver deixa de casar
        f.write_text(BASE + "echo extra\n")
        subprocess.run(["git", "-C", str(root), "add", "-f", "."], check=True)
        p2 = run_lint("--root", str(root), "--floor", "1", "--json")
        assert _json_result(p2)["blocking_unwaived"] >= 1
        assert p2.returncode == 1

    def test_unlock_without_reason_keeps_block(self, tmp_path):
        root, f = make_repo(tmp_path, BASE)
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        p = run_lint("--root", str(root), "--floor", "1", "--json",
                     env_extra={"CEO_CEREMONY_LINT_UNLOCK": sha})
        assert _json_result(p)["blocking_unwaived"] >= 1
        assert p.returncode == 1

    def test_unlock_with_reason_unblocks_this_run(self, tmp_path):
        root, f = make_repo(tmp_path, BASE)
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        p = run_lint("--root", str(root), "--floor", "1", "--json",
                     env_extra={"CEO_CEREMONY_LINT_UNLOCK": sha,
                                "CEO_CEREMONY_LINT_UNLOCK_REASON": "corte de madrugada"})
        assert _json_result(p)["blocking_unwaived"] == 0


class TestScopeControls:
    def test_floor_violation_is_red_even_without_findings(self, tmp_path):
        body = BASE + "# CEREMONY-LINT: handwritten-exception: fixture\n"
        root, _ = make_repo(tmp_path, body)
        p = run_lint("--root", str(root), "--floor", "5", "--json")
        d = _json_result(p)
        assert d["blocking_unwaived"] == 0 and not d["floor_ok"]
        assert p.returncode == 1

    def test_self_limitation_line_always_present(self, tmp_path):
        root, _ = make_repo(tmp_path, BASE)
        p = run_lint("--root", str(root), "--floor", "1")
        assert "NÃO cobre retomada" in p.stdout

    def test_untracked_blocking_does_not_gate(self, tmp_path):
        root, f = make_repo(tmp_path, BASE)
        # segundo arquivo com blocking, NUNCA adicionado ao index
        g = f.parent / "OWNER-UNTRACKED.sh"
        g.write_text(BASE)
        p = run_lint("--root", str(root), "--floor", "1", "--json")
        d = _json_result(p)
        untracked = [x for x in d["files"] if x["file"].endswith("OWNER-UNTRACKED.sh")]
        assert untracked and not untracked[0]["tracked"]
        # o achado aparece no relatorio, mas so o rastreado conta no gate
        assert d["blocking_unwaived"] == sum(
            1 for x in d["files"] if x["tracked"]
            for y in x["findings"] if y["sev"] == "BLOCKING")


class TestRealCorpusPositiveControl:
    """Debate r1 F4: o escopo TEM de enxergar o alvo real."""

    def test_r3_found_in_the_four_run_scripts(self):
        p = run_lint("--json")
        d = _json_result(p)
        hits = {f["file"] for f in d["files"]
                if any(x["rule"] == "R3" for x in f["findings"])}
        expected = {
            ".claude/plans/PLAN-166/repass-ga/run-ga-repass.sh",
            ".claude/plans/PLAN-166/repass-r2/run-repass-r2.sh",
            ".claude/plans/PLAN-166/repass-rc3-cures/run-rc3-cure-review.sh",
            ".claude/plans/PLAN-166/repass-rc3-scripts/run-rc3-scripts-review.sh",
        }
        assert expected <= hits, f"escopo não enxerga o alvo: faltam {expected - hits}"

    def test_repo_gate_is_green_with_pinned_waivers(self):
        p = run_lint("--json")
        d = _json_result(p)
        assert d["floor_ok"], "conjunto rastreado encolheu abaixo do piso"
        assert d["blocking_unwaived"] == 0, (
            "blocking novo sem waiver — ou uma cerimônia nova violou uma "
            "classe, ou um arquivo waivado foi editado (re-arme por sha256)")
