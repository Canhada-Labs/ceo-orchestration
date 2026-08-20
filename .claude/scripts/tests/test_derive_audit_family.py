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


class TestArtifactEnvMatrixUS2Extended:
    """US2 estendida — matriz ARTEFATO x env, uma assercao por celula.

    A US2 pedia "as 11+ celulas da lista fechada na US5 + bounding rule
    sobre as 33 vars". Duas correcoes de numero, ambas medidas:

    - **anchors**: sao 19, cobrindo a lista da US5 colapsada por DONO (as 19
      rotacoes de `audit-log-*.jsonl` tem um unico dono, entao um anchor
      responde por todas — a matriz prova QUEM decide o caminho, nao quantos
      arquivos o padrao gerou). `filelock` e `scratchpad_lib` ficam de FORA
      por declaracao (`ANCHORLESS_MODULES`): o primeiro recebe o path pronto,
      o segundo resolve por sessao. Anchor inventado para eles seria celula
      verde sem sujeito.
    - **vars**: nem 33 nem as 500 do `env-inventory.json`. O dominio real e
      derivado do CODIGO por `--env-domain` — as vars que os 8 modulos da
      familia LEEM — e da **21**, das quais `HOME`, `USER` e
      `PYTEST_CURRENT_TEST` nem constam do inventario. Essa e a bounding
      rule: o que esta fora do dominio nao pode mover caminho nenhum.
    """

    def test_every_cell_resolves_a_real_path(self):
        # "cada celula asserta o caminho resolvido de cada modulo" (Check da
        # US2). Uma celula degradada (ERRO/API-DRIFT/vazio) e falha: seria
        # matriz verde sem medicao por tras.
        p = run_tool("--matrix")
        assert p.returncode == 0, p.stderr
        m = json.loads(p.stdout)
        assert len(m) >= 11, "a US2 exige 11+ anchors; achei %d" % len(m)
        degraded = [
            (anchor, col, val)
            for anchor, row in m.items()
            for col, val in row.items()
            if str(val).startswith("ERRO")
            or val in ("API-DRIFT", "(vazio)", "")
        ]
        assert not degraded, "celulas degradadas: %r" % (degraded[:5],)
        for anchor, row in m.items():
            for col, val in row.items():
                assert val.startswith("/"), (anchor, col, val)

    def test_log_dir_moves_the_whole_family_together(self):
        # CEO_AUDIT_LOG_DIR e o botao COERENTE: log, lock, errors e a chave
        # HMAC vao juntos para o dir novo. realpath pelo mesmo motivo do
        # teste acima — no macOS /tmp e symlink e a comparacao por prefixo
        # mede formato em vez de destino.
        p = run_tool("--matrix")
        m = json.loads(p.stdout)
        col = "CEO_AUDIT_LOG_DIR"
        moved_dir = os.path.realpath("/tmp/fake-audit")
        for anchor in ("audit_emit._log_path", "audit_emit._lock_path",
                       "audit_emit._errors_path", "audit_hmac.key_path"):
            got = os.path.realpath(m[anchor][col])
            assert got.startswith(moved_dir + os.sep), (anchor, got)

    def test_log_path_leaves_lock_and_errors_behind(self):
        # O ACHADO da US2, e a correcao do enunciado: o plano dizia que o
        # lock e o errors nao acompanham o log "sob PATH-only". Medido: sob
        # PATH-only tudo fica co-locado; quem PARTE a familia e
        # CEO_AUDIT_LOG_PATH — move o log e deixa para tras o LOCK e o
        # ERRORS. Consequencia de tenancy: dois projetos com logs distintos
        # ainda serializam no MESMO lock e despejam breadcrumb no MESMO
        # arquivo de errors.
        #
        # A `audit-key` NAO entra nesta lista — ela ACOMPANHA o log. A
        # primeira redacao deste teste dizia que ela ficava para tras: era
        # artefato do symlink /tmp -> /private/tmp do macOS lido por
        # comparacao de prefixo de string. O CI (Linux) reprovou, e com
        # razao. Dai o realpath abaixo: sem ele a assercao mede o formato do
        # caminho, nao o destino dele.
        p = run_tool("--matrix")
        m = json.loads(p.stdout)
        col = "CEO_AUDIT_LOG_PATH"
        moved_dir = os.path.realpath("/tmp/fake-audit")

        def _under_moved(value):
            return os.path.realpath(value).startswith(moved_dir + os.sep)

        assert _under_moved(m["audit_emit._log_path"][col])
        # a chave HMAC acompanha o log (mede o DESTINO, nao o prefixo)
        assert _under_moved(m["audit_hmac.key_path"][col]), (
            "a audit-key parou de acompanhar o log — isso muda a conclusao "
            "de tenancy do plano, atualize os dois")
        # o lock e o errors NAO acompanham: e essa a divergencia
        for left_behind in ("audit_emit._lock_path", "audit_emit._errors_path"):
            assert not _under_moved(m[left_behind][col]), (
                "%s acompanhou o log — a divergencia sumiu, atualize o plano"
                % left_behind)
        # controle negativo do mesmo fato: sob PATH-only (sem-env) os tres
        # compartilham o dir, entao a divergencia NAO e do caminho default.
        base = "sem-env"
        log_dir = os.path.realpath(m["audit_emit._log_path"][base]).rsplit("/", 1)[0]
        for anchor in ("audit_emit._lock_path", "audit_emit._errors_path"):
            got = os.path.realpath(m[anchor][base]).rsplit("/", 1)[0]
            assert got == log_dir, (anchor, got, log_dir)

    def test_env_domain_is_derived_not_recalled(self):
        # Bounding rule: o dominio vem do codigo, e o teste falha se alguem
        # trocar por um numero de memoria.
        p = run_tool("--env-domain")
        assert p.returncode == 0, p.stderr
        d = json.loads(p.stdout)
        assert d["domain_size"] == len(d["domain"])
        assert d["domain_size"] >= 15, d["domain_size"]
        # toda coluna path-relevante da matriz TEM de estar no dominio —
        # senao a matriz estaria testando env que modulo nenhum le.
        for col in d["path_relevant_columns"]:
            if col == "sem-env":
                continue
            assert col in d["domain"], "coluna fora do dominio: %s" % col
        # o inventario NAO cobre o dominio inteiro — achado registrado.
        assert "HOME" in d["domain_absent_from_inventory"]
        assert d["inventory_total"] > d["domain_size"]

    def test_anchorless_modules_are_declared_not_forgotten(self):
        p = run_tool("--env-domain")
        d = json.loads(p.stdout)
        assert set(d["anchorless_modules"]) == {"filelock", "scratchpad_lib"}
        for mod, reason in d["anchorless_modules"].items():
            assert reason.strip(), mod
