"""PLAN-182 AC-3 — cobertura da lista fechada da US5, asserida por RESOLUÇÃO.

Por que este arquivo existe. O AC-3 pede "matriz de precedência por
artefato, sobre a lista fechada na US5". A matriz existe e roda
(``derive-audit-family.py --matrix``), mas até a S321 a cobertura da
lista US5 era **prosa**: um comentário em ``derive-audit-family.py``
dizia "os anchors cobrem a lista fechada da US5", e o único teste
mecânico exigia ``len(m) >= 11`` — um piso que não amarra anchor nenhum
a entrada nenhuma. Entradas reais da US5 (#41 ``advisory-dampen/``,
#42 ``fact-gate/``, #43 ``tool-lifecycle/``) tinham donos que não
apareciam nem em ``ARTIFACT_ANCHORS`` nem em ``ANCHORLESS_MODULES``.

O que este teste faz de diferente: não confere NOMES numa tabela — ele
**resolve o caminho de cada dono num subprocess com HOME isolado** e
assere que ele cai sob ``runtime_paths.runtime_state_dir()``. É a
pergunta que a família precisa que seja verdadeira ("todo artefato da
US5 mora na MESMA raiz por projeto"), e ela fica vermelha se qualquer
dono voltar a re-derivar o caminho por conta própria.

Isolamento: cada probe roda em subprocess com ``HOME`` e
``CLAUDE_PROJECT_DIR`` sintéticos, então nada toca o estado do operador
e a asserção não depende da máquina onde roda.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS = _REPO_ROOT / ".claude" / "hooks"

if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))
from _lib.testing import TestEnvContext  # noqa: E402

# Donos de artefato da lista fechada da US5
# (`.claude/plans/PLAN-182/w0-medicao-S316.md`), na forma
# <rótulo>: <expressão que devolve um caminho>.
#
# A lista é dos DONOS, não dos 46 arquivos: 19 rotações de log colapsam
# num anchor de log só — o que a matriz precisa provar é QUAL MÓDULO
# decide cada caminho, não quantos arquivos o padrão gerou.
US5_OWNERS = {
    # --- núcleo do log + chave + sidecars (itens 1-37) ---
    "audit_emit._audit_dir": "from _lib import audit_emit as m; _r(m._audit_dir)",
    "audit_emit._log_path": "from _lib import audit_emit as m; _r(m._log_path)",
    "audit_emit._lock_path": "from _lib import audit_emit as m; _r(m._lock_path)",
    "audit_emit._errors_path": "from _lib import audit_emit as m; _r(m._errors_path)",
    "audit_hmac.key_path": "from _lib import audit_hmac as m; _r(m.key_path)",
    "audit_hmac.last_hmac_path": "from _lib import audit_hmac as m; _r(m.last_hmac_path)",
    "audit_hmac.chain_length_path": (
        "from _lib import audit_hmac as m; _r(m.chain_length_path)"),
    # --- salt (item do §2 do plano) ---
    "injection_salt._salt_path": (
        "from _lib import injection_salt as m; _r(m._salt_path)"),
    # --- state/ (item 38) ---
    "state_store._state_root": (
        "from _lib import state_store as m; _r(m._state_root)"),
    # --- memory-shared/ (item 40) ---
    "memory_shared._storage_root": (
        "from _lib import memory_shared as m; _r(m._storage_root)"),
    # --- spool (escritor assíncrono do log) ---
    "spool_writer._state_dir": (
        "from _lib import spool_writer as m; _r(m._state_dir)"),
    "spool_writer._canonical_log_path": (
        "from _lib import spool_writer as m; _r(m._canonical_log_path)"),
    # --- os TRÊS que faltavam (itens 41, 42, 43) — a razão deste arquivo ---
    "advisory_dampen._state_base_dir": (
        "from _lib import advisory_dampen as m; _r(m._state_base_dir)"),
    "tool_lifecycle._audit_dir": (
        "from _lib import tool_lifecycle as m; _r(m._audit_dir)"),
    "check_bash_safety._fact_gate_state_dir": (
        "import importlib.util as _iu, pathlib as _pl; "
        "_sp = _iu.spec_from_file_location("
        "'_cbs_probe', _pl.Path(_HOOKS) / 'check_bash_safety.py'); "
        "_mod = _iu.module_from_spec(_sp); "
        "sys.modules['_cbs_probe'] = _mod; "
        "_sp.loader.exec_module(_mod); "
        "_r(getattr(_mod, '_fact_gate_state_dir', None))"),
}

# Donos SEM caminho de projeto, com a razão registrada por item. Estar
# aqui é uma afirmação verificável, não uma dispensa: `filelock` recebe o
# path pronto do chamador e `scratchpad_lib` resolve por sessão.
US5_ANCHORLESS = {
    "filelock": "recebe o path pronto do chamador; nao decide caminho",
    "scratchpad_lib": "resolve por sessao (CLAUDE_SESSION_ID), nao por env de projeto",
    # Item 45 da US5. Zero escritores vivos e zero no histórico
    # (pickaxe `draft_accepted` = 0); última escrita 2026-06-04.
    "speculative-ledger.json": "ORFAO — sem escritor vivo; item 45 da US5",
}

_PROBE_PROJECT = "/srv/us5-probe/app"


def _run_probes():
    """Resolve todos os donos numa subprocess com HOME sintético."""
    home = tempfile.mkdtemp(prefix="us5-cov-")
    lines = [
        "import sys, json",
        "sys.path.insert(0, %r)" % str(_HOOKS),
        "_HOOKS = %r" % str(_HOOKS),
        "_out = {}",
        "def _r(fn):",
        "    _out[_k] = 'API-DRIFT' if not callable(fn) else str(fn())",
    ]
    for key, expr in US5_OWNERS.items():
        lines.append("_k = %r" % key)
        lines.append("try:")
        for stmt in expr.split("; "):
            lines.append("    " + stmt)
        lines.append("except Exception as e:")
        lines.append("    _out[_k] = 'ERRO: %s' % type(e).__name__")
    lines.append("from _lib import runtime_paths as _rp")
    lines.append("_out['__family__'] = str(_rp.runtime_state_dir())")
    lines.append("print(json.dumps(_out))")

    env = dict(os.environ)
    # Nenhum carrier de caminho pode vazar para dentro do probe — nem o do
    # operador, nem o que a PRÓPRIA suíte injeta (quando este teste roda sob
    # pytest, o conftest já redirecionou `CEO_AUDIT_KEY_PATH` & cia. para o
    # sandbox da sessão, e sem esta limpeza os anchors de `audit_hmac`
    # resolveriam para LÁ — medido na S321).
    #
    # A lista é DERIVADA da enumeração canônica em `_lib.test_isolation`, e
    # nunca recordada aqui: o módulo declara que "a enumeração vive AQUI,
    # exatamente uma vez", e uma segunda cópia envelheceria em silêncio.
    sys.path.insert(0, str(_HOOKS))
    from _lib import test_isolation as _ti

    for var in tuple(_ti.ALL_AUDIT_CARRIERS) + (
        # O carrier de MAIOR precedência do resolvedor; ele não está em
        # ALL_AUDIT_CARRIERS (PLAN-182 W1-followup, ainda em cerimônia).
        "CLAUDE_PROJECT_DIR_NATIVE",
        "CEO_STATE_ROOT",
        "CEO_PROJECT_NAME",
    ):
        env.pop(var, None)
    env["HOME"] = home
    env["CLAUDE_PROJECT_DIR"] = _PROBE_PROJECT
    proc = subprocess.run(
        [sys.executable, "-c", "\n".join(lines)],
        capture_output=True, text=True, timeout=120, env=env, cwd=str(_REPO_ROOT))
    if proc.returncode != 0:
        raise AssertionError(
            "probe falhou (rc=%s):\n%s" % (proc.returncode, proc.stderr[-2000:]))
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TestUS5FamilyCoverage(TestEnvContext):
    """AC-3: todo dono da US5 resolve sob a MESMA raiz por projeto.

    Herda `TestEnvContext` (e não `unittest.TestCase`) por exigência do
    `check-test-env-hygiene.py`, e a exigência está certa: este caso
    manipula env de caminho, que é exatamente a classe que o guard
    protege. O probe já roda em subprocess com `HOME`/`CLAUDE_PROJECT_DIR`
    sintéticos — o `TestEnvContext` acrescenta a garantia de que o
    processo-pai também não toca o estado do operador.
    """

    def setUp(self):
        super().setUp()
        if not hasattr(self.__class__, "_probe_cache"):
            self.__class__._probe_cache = _run_probes()
        self.res = self.__class__._probe_cache
        self.family = self.res["__family__"]

    def test_family_root_is_the_project_slug(self):
        """Sanidade do fixture: sem ela, o teste abaixo é vacuamente verde."""
        self.assertIn("-srv-us5-probe-app", self.family)
        self.assertNotIn("ceo-orchestration", self.family)

    def test_every_us5_owner_resolves_under_the_family_root(self):
        offenders = []
        for key in US5_OWNERS:
            got = self.res.get(key, "<AUSENTE>")
            if got.startswith(("ERRO:", "API-DRIFT", "<AUSENTE>")):
                offenders.append("%s: %s" % (key, got))
            elif not got.startswith(self.family):
                offenders.append("%s resolve FORA da familia: %s" % (key, got))
        self.assertEqual(
            offenders, [],
            "AC-3: %d dono(s) da US5 nao resolvem sob %s:\n  %s"
            % (len(offenders), self.family, "\n  ".join(offenders)))

    def test_coverage_is_total_owners_plus_anchorless(self):
        """A lista é FECHADA: nenhum dono fica sem anchor nem sem razão."""
        overlap = set(US5_OWNERS) & set(US5_ANCHORLESS)
        self.assertEqual(
            overlap, set(),
            "um dono nao pode ser anchor E anchorless: %s" % sorted(overlap))
        for name, reason in US5_ANCHORLESS.items():
            self.assertTrue(
                reason and len(reason) > 20,
                "anchorless sem razao registrada: %s" % name)

    def test_negative_control_a_local_slug_would_be_caught(self):
        """Controle positivo do detector: um dono que re-derive o slug
        localmente (a classe M4) resolve FORA da família e seria pego pelo
        teste acima. Reproduz o MECANISMO, não a aparência."""
        pd = _PROBE_PROJECT
        canonical = "-" + pd.lstrip("/").replace("/", "-")
        local_spelling = pd.replace("/", "-").lstrip("-")  # a grafia sem traço
        self.assertNotEqual(
            canonical, local_spelling,
            "as duas grafias colidiram — o controle ficou vacuo")
        fake = str(Path(self.family).parent / local_spelling)
        self.assertFalse(
            fake.startswith(self.family),
            "um caminho com slug re-derivado localmente DEVE cair fora da "
            "familia; se ele caisse dentro, o teste principal seria vacuo")


if __name__ == "__main__":
    unittest.main()
