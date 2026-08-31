"""PLAN-183 W2 — Ramo B: subconjunto congelado do validate.yml.template.

O vínculo template↔vivo escolhido na abertura da wave (S334) é o Ramo B
do Check: em vez de um gate de drift contra o validate.yml vivo (71
steps, superfície de cerimônia própria), o template entregue ao adopter
é DECLARADO aqui como subconjunto mínimo congelado — cada step nomeado —
e este teste falha se o template divergir da declaração em qualquer
direção: step a mais, a menos, fora de ordem, pin perdido, ou o retorno
de um dos três steps removidos por `4f750f0` (verde-vácuo / falso-verde
no adopter, `PLAN-183/resposta-ao-campo.md` §A2).

Stdlib-only por contrato (CLAUDE.md §4): o parse é textual, sem PyYAML.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402
TEMPLATE = (
    REPO_ROOT / "templates" / ".github" / "workflows" / "validate.yml.template"
)

# A declaração congelada (Ramo B). Ordem incluída — o template é lido
# pelo adopter de cima a baixo e a ordem carrega intenção (checkout
# primeiro, actionlint depois dos geradores de YAML, bits por último).
FROZEN_STEPS = [
    "Checkout",
    "Run validate-governance.sh",
    "Run check-skill-health.sh --ci",
    "Run check-pitfall-regression.sh",
    "Contamination check (no private-project/personal refs outside allowlist)",
    "Placeholder lint (core/frontend skills only)",
    "Validate settings.json and YAML catalogs",
    "Shellcheck hooks and scripts (excluding legacy/)",
    "Check tier boundaries (core/frontend must not reference domains)",
    "actionlint",
    "Hook and script executable bits",
]

# Os três steps que `4f750f0` removeu; reaparecer é regressão da classe
# "verde no framework, vácuo ou vermelho no adopter".
REMOVED_STEPS = [
    "Run Python hook unit tests",
    "Run Python script unit tests",
    "Skill inventory idempotency",
]

# Pins congelados junto com o subconjunto: perdê-los é divergência tão
# real quanto perder um step.
PIN_CHECKOUT_SHA = re.compile(
    r"uses:\s*actions/checkout@[0-9a-f]{40}\b"
)
PIN_ACTIONLINT = re.compile(r"VERSION=\"1\.7\.7\"")
PIN_TIMEOUT = re.compile(r"^\s*timeout-minutes:\s*15\s*$", re.M)


def _template_text() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _step_names(text: str) -> list:
    return re.findall(r"^\s+- name:\s*(.+?)\s*$", text, re.M)


class TestFrozenSubsetDeclaration(TestEnvContext):
    """Read-only over the live tree, but `TestEnvContext` is still the
    base: env isolation is the corpus-wide contract for new tests
    (check-test-env-hygiene gate), and it costs nothing here."""
    def test_template_exists(self) -> None:
        self.assertTrue(TEMPLATE.is_file(), TEMPLATE)

    def test_steps_match_declaration_exactly_in_order(self) -> None:
        got = _step_names(_template_text())
        self.assertEqual(
            got,
            FROZEN_STEPS,
            "validate.yml.template divergiu do subconjunto congelado "
            "(Ramo B, PLAN-183 W2). Divergência DELIBERADA exige editar "
            "a declaração FROZEN_STEPS neste teste no MESMO patch, com a "
            "razão no plano.",
        )

    def test_removed_steps_do_not_return(self) -> None:
        text = _template_text()
        for name in REMOVED_STEPS:
            self.assertNotIn(
                name,
                text,
                f"step removido por 4f750f0 reapareceu no template: {name!r}",
            )

    def test_checkout_is_sha_pinned(self) -> None:
        self.assertRegex(_template_text(), PIN_CHECKOUT_SHA)

    def test_actionlint_is_version_pinned(self) -> None:
        self.assertRegex(_template_text(), PIN_ACTIONLINT)

    def test_timeout_is_frozen_at_15(self) -> None:
        self.assertRegex(_template_text(), PIN_TIMEOUT)

    def test_declaration_is_honest_about_size(self) -> None:
        # O Check do plano nomeia 11 steps; se a declaração crescer sem
        # o plano acompanhar, este número denuncia.
        self.assertEqual(len(FROZEN_STEPS), 11)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
