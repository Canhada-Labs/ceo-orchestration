"""Testes do lint de vacuidade + cura do caso vivo (PLAN-178 W-C Lote A, C3).

Duas pernas da cura, ambas com positive control (consenso r1 must-fix
10; codex pos-debate P1/AC-6):

R1 (lint): fixture com check deliberadamente vacuoso TEM de ser
reprovada; fixture com waiver/indirecao TEM de passar; parse error e
fail-loud.

R2 (caso vivo): ``check_tier_a_spec_version_drift`` era o exemplar da
classe S287 "registered-vacuous" (lia VERSION e SPEC e nunca
comparava). A regressao aqui e FUNCIONAL, nao estrutural: extrai a
funcao do ceo-boot.py real via AST, executa com REPO_ROOT stubbado e
exige red no drift / green no match — se alguem reverter a cura, o
teste de drift volta a receber green e FALHA.
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib
import subprocess
import sys
from typing import Any, Tuple

REPO = pathlib.Path(__file__).resolve().parents[3]
LINT = REPO / ".claude" / "scripts" / "check-vacuous-checks.py"
CEO_BOOT = REPO / ".claude" / "scripts" / "ceo-boot.py"


def _load_lint():
    spec = importlib.util.spec_from_file_location("vacuous_lint", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------- R1: lint

def test_positive_control_flags_deliberately_vacuous_check(tmp_path):
    fixture = tmp_path / "fake_boot.py"
    fixture.write_text(
        'def check_always_green():\n'
        '    """decorativo de proposito (fixture do positive control)."""\n'
        '    return ("green", "sempre", None)\n'
    )
    mod = _load_lint()
    code, flagged = mod.scan_file(str(fixture))
    assert code == 1, "lint DEVE reprovar o check vacuoso da fixture"
    assert any("check_always_green" in f for f in flagged)


def test_discriminating_check_passes(tmp_path):
    fixture = tmp_path / "fake_boot.py"
    fixture.write_text(
        'def check_real(v):\n'
        '    if v > 2:\n'
        '        return ("red", "drift", v)\n'
        '    return ("green", "ok", v)\n'
    )
    mod = _load_lint()
    code, flagged = mod.scan_file(str(fixture))
    assert code == 0 and not flagged


def test_waiver_is_honored(tmp_path):
    fixture = tmp_path / "fake_boot.py"
    fixture.write_text(
        '# CEO-INFORMATIONAL-ONLY: contador informativo, sem limiar\n'
        'def check_counter():\n'
        '    return ("green", "n=3", 3)\n'
    )
    mod = _load_lint()
    code, flagged = mod.scan_file(str(fixture))
    assert code == 0 and not flagged


def test_distractor_literals_do_not_count_as_discrimination(tmp_path):
    """codex Lote-A P2-2: literal de status em docstring/dict/branch
    morto NAO pode salvar um check sempre-verde."""
    fixture = tmp_path / "fake_boot.py"
    fixture.write_text(
        'def check_distractor():\n'
        '    """No drift retornaria "red" — mas nunca retorna."""\n'
        '    labels = {"green": 1, "red": 2}\n'
        '    return ("green", "always", labels)\n'
    )
    mod = _load_lint()
    code, flagged = mod.scan_file(str(fixture))
    assert code == 1, "distrator em docstring/dict passou como discriminacao"
    assert any("check_distractor" in f for f in flagged)


def test_nested_helper_return_does_not_count(tmp_path):
    """codex r2 P2-3: return de helper ANINHADO nao salva o pai."""
    fixture = tmp_path / "fake_boot.py"
    fixture.write_text(
        'def check_with_nested():\n'
        '    def _helper():\n'
        '        return ("red", "inner", None)\n'
        '    _helper()\n'
        '    return ("green", "always", None)\n'
    )
    mod = _load_lint()
    code, flagged = mod.scan_file(str(fixture))
    assert code == 1 and any("check_with_nested" in f for f in flagged)


def test_dead_branch_return_does_not_count(tmp_path):
    """codex r2 P2-3: `if False: return red` e branch morto."""
    fixture = tmp_path / "fake_boot.py"
    fixture.write_text(
        'def check_dead_branch():\n'
        '    if False:\n'
        '        return ("red", "unreachable", None)\n'
        '    return ("green", "always", None)\n'
    )
    mod = _load_lint()
    code, flagged = mod.scan_file(str(fixture))
    assert code == 1 and any("check_dead_branch" in f for f in flagged)


def test_waiver_in_docstring_does_not_waive(tmp_path):
    """codex r2 P2-4: mencao em docstring/string NAO e waiver."""
    fixture = tmp_path / "fake_boot.py"
    fixture.write_text(
        'def check_sneaky():\n'
        '    """Not a CEO-INFORMATIONAL-ONLY check, honest."""\n'
        '    return ("green", "always", None)\n'
    )
    mod = _load_lint()
    code, flagged = mod.scan_file(str(fixture))
    assert code == 1 and any("check_sneaky" in f for f in flagged)


def test_waiver_requires_nonempty_reason(tmp_path):
    fixture = tmp_path / "fake_boot.py"
    fixture.write_text(
        '# CEO-INFORMATIONAL-ONLY:\n'
        'def check_no_reason():\n'
        '    return ("green", "always", None)\n'
    )
    mod = _load_lint()
    code, flagged = mod.scan_file(str(fixture))
    assert code == 1, "waiver sem razao nao pode waivar"


def test_indirect_status_is_skipped_not_flagged(tmp_path):
    fixture = tmp_path / "fake_boot.py"
    fixture.write_text(
        'def _helper(v):\n'
        '    return ("red" if v else "green", "x", v)\n'
        'def check_delegating(v):\n'
        '    status, summary = _helper(v)[0], _helper(v)[1]\n'
        '    return status, summary, v\n'
    )
    mod = _load_lint()
    code, flagged = mod.scan_file(str(fixture))
    assert code == 0 and not flagged


def test_parse_error_is_loud(tmp_path):
    fixture = tmp_path / "broken.py"
    fixture.write_text("def check_(:\n")
    mod = _load_lint()
    code, flagged = mod.scan_file(str(fixture))
    assert code == 2 and any("PARSE-ERROR" in f for f in flagged)


def test_cli_clean_on_real_ceo_boot():
    """O ceo-boot.py REAL fica limpo: cura + waivers completos.

    Este e o teto do C3 — se um check novo nascer vacuoso sem waiver,
    este teste (e o lint no CI, quando wirado) ficam vermelhos.
    """
    proc = subprocess.run(
        [sys.executable, str(LINT), str(CEO_BOOT)],
        capture_output=True, text=True, timeout=60,
    )
    assert "INPUTS:" in proc.stdout, proc.stderr
    assert proc.returncode == 0, (
        "check_* vacuoso sem waiver em ceo-boot.py:\n" + proc.stdout
    )


# ------------------------------------------------- R2: caso vivo (funcional)

def _extract_spec_drift_fn(repo_root: pathlib.Path):
    """Extrai check_tier_a_spec_version_drift do ceo-boot.py real e a
    executa num namespace com REPO_ROOT stubbado (sem importar o script
    inteiro — top-level do ceo-boot tem efeitos de sessao)."""
    src = CEO_BOOT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "check_tier_a_spec_version_drift"
    )
    segment = ast.get_source_segment(src, fn)
    ns: dict = {"REPO_ROOT": repo_root, "Tuple": Tuple, "Any": Any,
                "subprocess": subprocess}
    exec(compile(segment, str(CEO_BOOT), "exec"), ns)  # noqa: S102
    return ns["check_tier_a_spec_version_drift"]


def _seed_fw(tmp_path: pathlib.Path, version: str,
             delivered: bool = True) -> None:
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude" / ".framework-version").write_text(version + "\n")
    if delivered:
        # registro de entrega (ADR-155-AMEND-1): baseline manifest com
        # record do marker => proveniencia verificada
        (tmp_path / ".claude" / ".install-manifest.sha256").write_text(
            "0" * 64 + "  .claude/.framework-version\n"
        )


def test_bug_178_spec_version_drift_red_on_major_mismatch(tmp_path):
    _seed_fw(tmp_path, "2.0.0")
    (tmp_path / "SPEC" / "v1").mkdir(parents=True)
    fn = _extract_spec_drift_fn(tmp_path)
    status, summary, detail = fn()
    assert status == "red", (
        "REGRESSAO S287: framework major 2 vs SPEC v1 tem de dar red; "
        "recebeu %r (%s) — a cura do PLAN-178 C3 foi revertida?"
        % (status, summary)
    )
    assert detail["repo_version"] == "2.0.0"


def test_bug_178_spec_version_drift_green_on_match(tmp_path):
    _seed_fw(tmp_path, "1.3.0")
    (tmp_path / "SPEC" / "v1").mkdir(parents=True)
    fn = _extract_spec_drift_fn(tmp_path)
    status, _summary, detail = fn()
    assert status == "green"
    assert detail["spec_versions"] == ["v1"]


def test_bug_178_spec_version_drift_yellow_on_garbage(tmp_path):
    _seed_fw(tmp_path, "not-a-version")
    (tmp_path / "SPEC" / "v1").mkdir(parents=True)
    fn = _extract_spec_drift_fn(tmp_path)
    status, _summary, _detail = fn()
    assert status == "yellow"


def test_bug_178_adopter_own_version_never_reds(tmp_path):
    """codex Lote-A P2-1: adopter com VERSION proprio (app 2.0.0) e SEM
    .framework-version atribuivel NAO pode dar red — o root VERSION
    nao e do framework (ADR-155-AMEND-1 §2)."""
    (tmp_path / "VERSION").write_text("2.0.0\n")  # versao do APP
    (tmp_path / "SPEC" / "v1").mkdir(parents=True)
    fn = _extract_spec_drift_fn(tmp_path)
    status, summary, _detail = fn()
    assert status == "green", (
        "false-red de adopter: %r (%s)" % (status, summary)
    )
    assert "not attributable" in summary


def test_bug_178_adopter_with_framework_version_compares_it(tmp_path):
    """Adopter app 9.9.9 + .framework-version 1.3.0 + SPEC/v1 => green
    (compara o FRAMEWORK, ignora o VERSION do app)."""
    (tmp_path / "VERSION").write_text("9.9.9\n")
    _seed_fw(tmp_path, "1.3.0")
    (tmp_path / "SPEC" / "v1").mkdir(parents=True)
    fn = _extract_spec_drift_fn(tmp_path)
    status, _summary, detail = fn()
    assert status == "green"
    assert detail["repo_version"] == "1.3.0"


def test_bug_178_unverified_marker_mismatch_is_yellow_not_red(tmp_path):
    """codex r2 P2-1 (ADR-155-AMEND-1 §5): marker SEM registro de
    entrega e SEM git-tracking nao sustenta red — mismatch vira yellow
    'drift suspected'."""
    _seed_fw(tmp_path, "2.0.0", delivered=False)
    (tmp_path / "SPEC" / "v1").mkdir(parents=True)
    fn = _extract_spec_drift_fn(tmp_path)
    status, summary, detail = fn()
    assert status == "yellow", (
        "marker nao-atribuivel deu %r (%s) — red exige proveniencia"
        % (status, summary)
    )
    assert "suspected" in summary
    assert detail["provenance_verified"] is False


def test_bug_178_delivered_marker_mismatch_is_red(tmp_path):
    """Com registro de entrega, o mesmo mismatch E red (o caminho red
    continua alcancavel — a cura da vacuidade nao regrediu)."""
    _seed_fw(tmp_path, "2.0.0", delivered=True)
    (tmp_path / "SPEC" / "v1").mkdir(parents=True)
    fn = _extract_spec_drift_fn(tmp_path)
    status, _summary, detail = fn()
    assert status == "red"
    assert detail["provenance_verified"] is True


def test_dead_symbol_lesson_render_safe_is_gone():
    """C4: o simbolo morto nao volta ao arquivo vivo (a referencia
    correta e _validate_boot_lesson)."""
    src = CEO_BOOT.read_text(encoding="utf-8")
    assert "_lesson_render_safe" not in src
    assert "_validate_boot_lesson" in src
