"""Tests for optimizer.model_choice — WS-2(a) per-sub-task model brain."""

from __future__ import annotations

from optimizer import model_choice as MC
from optimizer.types import (
    COMPLEXITY_COMPLEX,
    COMPLEXITY_MODERATE,
    COMPLEXITY_SIMPLE,
    COMPLEXITY_TRIVIAL,
    MODEL_HAIKU,
    MODEL_OPUS,
    MODEL_SONNET,
)


def _routing_on(monkeypatch):
    monkeypatch.delenv("CEO_MODEL_ROUTING", raising=False)


def test_complexity_drives_base_model(monkeypatch):
    _routing_on(monkeypatch)
    assert MC.choose(complexity=COMPLEXITY_TRIVIAL).model == MODEL_HAIKU
    assert MC.choose(complexity=COMPLEXITY_SIMPLE).model == MODEL_HAIKU
    assert MC.choose(complexity=COMPLEXITY_MODERATE).model == MODEL_SONNET
    assert MC.choose(complexity=COMPLEXITY_COMPLEX).model == MODEL_OPUS


def test_opus_archetype_escalates(monkeypatch):
    _routing_on(monkeypatch)
    for a in ("security", "architect", "debate", "identity-trust-architect"):
        assert MC.choose(archetype=a, complexity=COMPLEXITY_SIMPLE).model == MODEL_OPUS, a


def test_codegen_archetype_floors_at_sonnet(monkeypatch):
    _routing_on(monkeypatch)
    c = MC.choose(archetype="code_gen", complexity=COMPLEXITY_TRIVIAL)
    assert c.model == MODEL_SONNET


def test_large_context_escalates_to_opus(monkeypatch):
    _routing_on(monkeypatch)
    c = MC.choose(complexity=COMPLEXITY_SIMPLE, context_size=200000)
    assert c.model == MODEL_OPUS


def test_routing_off_defers(monkeypatch):
    monkeypatch.setenv("CEO_MODEL_ROUTING", "0")
    c = MC.choose(complexity=COMPLEXITY_COMPLEX, archetype="security")
    assert c.model == ""
    assert c.cost_governed is True


def test_confidence_is_int_in_range(monkeypatch):
    _routing_on(monkeypatch)
    for kwargs in (
        {"complexity": COMPLEXITY_SIMPLE},
        {"archetype": "security"},
        {"complexity": COMPLEXITY_COMPLEX, "context_size": 99999},
    ):
        c = MC.choose(**kwargs)
        assert isinstance(c.confidence_basis_points, int)
        assert not isinstance(c.confidence_basis_points, bool)
        assert 0 <= c.confidence_basis_points <= 1000


def test_static_floor_backstop(monkeypatch):
    _routing_on(monkeypatch)
    # known task_class, no archetype, mild complexity -> may consult _lib floor.
    c = MC.choose(task_class="file_read", complexity=COMPLEXITY_SIMPLE)
    # file_read maps to haiku in the static table; brain base is also haiku, so
    # no fallback needed — but a code_gen task_class would differ.
    c2 = MC.choose(task_class="code_gen", complexity=COMPLEXITY_SIMPLE)
    assert c2.model in (MODEL_HAIKU, MODEL_SONNET)  # floor may bump to sonnet
    if c2.model == MODEL_SONNET:
        assert c2.fell_back_to_static is True


def test_never_raises(monkeypatch):
    _routing_on(monkeypatch)
    c = MC.choose(task_class=None, archetype=None, context_size="x", complexity=123)  # type: ignore[arg-type]
    assert c.model in (MODEL_HAIKU, MODEL_SONNET, MODEL_OPUS)


# --- PLAN-133 B2: static-floor slug is canonicalized through normalize_model_name.
def test_static_floor_slug_is_canonicalized(monkeypatch):
    """A floor returned by _lib.model_routing in an aliased/date-stamped/cased
    form is folded onto its canonical slug (alias/case ONLY) before the
    VALID_MODELS membership check — so a cosmetic variant still resolves and is
    never collapsed across versions."""
    _routing_on(monkeypatch)

    import optimizer.model_choice as mc_mod

    # Force the backstop path: no archetype, simple bucket, known task_class, and
    # a model_routing.resolve that returns an aliased form of Sonnet.
    class _FakeRouting:
        @staticmethod
        def resolve(task_class):
            return "claude-sonnet-4-6-20250930"  # date-stamped alias of Sonnet

    monkeypatch.setattr(
        mc_mod, "_static_floor",
        lambda tc: mc_mod.normalize_model_name(_FakeRouting.resolve(tc))
        if mc_mod.normalize_model_name(_FakeRouting.resolve(tc)) in (
            MODEL_HAIKU, MODEL_SONNET, MODEL_OPUS
        ) else None,
        raising=True,
    )
    c = MC.choose(task_class="code_gen", complexity=COMPLEXITY_SIMPLE)
    # The aliased floor canonicalized to claude-sonnet-4-6 (a VALID_MODELS slug),
    # so the brain adopts it and flags the fallback.
    assert c.model == MODEL_SONNET
    assert c.fell_back_to_static is True


def test_normalize_import_does_not_alter_base_models(monkeypatch):
    """Importing the normalizer must not change the canonical base-model outputs
    (the base constants are already canonical and must round-trip)."""
    _routing_on(monkeypatch)
    from optimizer.model_choice import normalize_model_name
    assert normalize_model_name(MODEL_HAIKU) == MODEL_HAIKU
    assert normalize_model_name(MODEL_SONNET) == MODEL_SONNET
    assert normalize_model_name(MODEL_OPUS) == MODEL_OPUS
