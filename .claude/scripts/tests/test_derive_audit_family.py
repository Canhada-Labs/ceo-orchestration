"""Testes do derive-audit-family.py (PLAN-182 W0-US1/US2).

Controles: membros conhecidos classificados por comportamento; a regra
de allowlist mantém SPEC/doc fora da cura (grep não é oráculo); a
matriz US2 reproduz as divergências medidas; o gate --assert-migrated
é VERMELHO hoje (positive control — um gate que já nasce verde é
suspeito).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TOOL = os.path.join(REPO_ROOT, ".claude", "scripts", "derive-audit-family.py")


def run_tool(*args):
    return subprocess.run([sys.executable, TOOL, *args],
                          capture_output=True, text=True, cwd=REPO_ROOT, timeout=300)


def census():
    p = run_tool("--json")
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


class TestCensusBehavioral:
    def test_known_writer_is_in_family(self):
        d = census()
        by = {f["modulo"]: f for f in d["familia"]}
        ae = by.get(".claude/hooks/_lib/audit_emit.py")
        assert ae is not None, "audit_emit.py fora da família — censo quebrado"
        assert ae["artefato"] == "hook" and "writer" in ae["papel"]

    def test_salt_module_flagged(self):
        d = census()
        by = {f["modulo"]: f for f in d["familia"]}
        s = by.get(".claude/hooks/_lib/injection_salt.py")
        assert s is not None and "salt" in s["papel"]

    def test_allowlist_spec_doc_out_of_cure(self):
        d = census()
        for f in d["familia"]:
            if f["artefato"] in ("spec", "doc"):
                assert f["na_cura_w1"] is False, (
                    f"{f['modulo']}: spec/doc entrou no conjunto de cura — "
                    "a allowlist explícita da AC-1 quebrou")

    def test_family_floor(self):
        d = census()
        # censo S316: 587 no total, 562 na cura, ≥100 runtime
        # constroem o literal. Pisos protegem contra encolhimento
        # silencioso do escopo (classe guard-verde-sem-ver-o-alvo).
        assert d["total_familia"] >= 400
        assert d["na_cura_w1"] >= 400


class TestAssertMigratedGate:
    def test_gate_is_red_today_by_design(self):
        p = run_tool("--assert-migrated")
        assert p.returncode == 1, (
            "o gate de migração passou ANTES da W1 executar — ou a W1 "
            "landou (atualize este teste junto), ou o censo ficou cego")
        assert "constroem o caminho literal" in p.stdout


class TestEnvMatrixUS2:
    def test_matrix_reproduces_measured_divergences(self):
        p = run_tool("--matrix")
        assert p.returncode == 0, p.stderr
        m = json.loads(p.stdout)
        ae = m["audit_emit._audit_dir"]
        ss = m["state_store._state_root"]
        salt = m["injection_salt(dir do salt)"]
        # audit_emit: só CEO_AUDIT_LOG_DIR muda o caminho
        assert ae["CEO_AUDIT_LOG_DIR"] == "/tmp/fake-audit"
        assert ae["CEO_PROJECT_NAME"].endswith("/projects/ceo-orchestration")
        assert ae["CLAUDE_PROJECT_DIR"].endswith("/projects/ceo-orchestration")
        # state_store: honra CEO_STATE_ROOT e CEO_PROJECT_NAME
        assert ss["CEO_STATE_ROOT"] == "/tmp/fake-state-root"
        assert ss["CEO_PROJECT_NAME"].endswith("/projects/outro-projeto/state")
        # salt: NENHUM override — mesma célula em todas as colunas
        assert len({v for v in salt.values()}) == 1, (
            "o salt ganhou override de env — se isso é a cura da W1, "
            "atualize a matriz esperada JUNTO com o plano")
        # a divergência em si (a razão do PLAN-182): sob CEO_PROJECT_NAME,
        # state_store acompanha e audit_emit NÃO — dois artefatos do mesmo
        # projeto em namespaces distintos
        assert "outro-projeto" in ss["CEO_PROJECT_NAME"]
        assert "outro-projeto" not in ae["CEO_PROJECT_NAME"]
