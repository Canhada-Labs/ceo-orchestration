"""Tests for optimizer.types — frozen immutability + constant integrity."""

from __future__ import annotations

import dataclasses

import pytest

from optimizer import types as T


def test_route_and_complexity_constants_distinct():
    routes = {T.ROUTE_PASSTHROUGH, T.ROUTE_SINGLE, T.ROUTE_FANOUT}
    assert len(routes) == 3
    assert T.COMPLEXITY_ORDER == (
        T.COMPLEXITY_TRIVIAL, T.COMPLEXITY_SIMPLE, T.COMPLEXITY_MODERATE, T.COMPLEXITY_COMPLEX,
    )


def test_model_slugs_match_framework():
    # Must match .claude/hooks/_lib/model_routing.py _ROUTING_TABLE values.
    assert T.MODEL_HAIKU == "claude-haiku-4-5"
    assert T.MODEL_SONNET == "claude-sonnet-4-6"
    assert T.MODEL_OPUS == "claude-opus-4-8"
    assert T.VALID_MODELS == (T.MODEL_HAIKU, T.MODEL_SONNET, T.MODEL_OPUS)


def test_ceilings_sane():
    assert T.MAX_FANOUT_WIDTH == 8
    assert T.MAX_UNIT_COUNT >= T.MAX_FANOUT_WIDTH


def test_dataclasses_are_frozen():
    g = T.GateResult(route=T.ROUTE_FANOUT, complexity=T.COMPLEXITY_COMPLEX,
                     parallelizable=True, suggested_width=4, reason="x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        g.route = T.ROUTE_SINGLE  # type: ignore[misc]

    st = T.SubTask(index=0, label="a", model=T.MODEL_HAIKU, est_tokens_in=10)
    with pytest.raises(dataclasses.FrozenInstanceError):
        st.model = T.MODEL_OPUS  # type: ignore[misc]

    mc = T.ModelChoice(model=T.MODEL_SONNET, confidence_basis_points=900,
                       cost_governed=False, fell_back_to_static=False)
    with pytest.raises(dataclasses.FrozenInstanceError):
        mc.model = ""  # type: ignore[misc]


def test_confidence_is_int_not_float():
    mc = T.ModelChoice(model=T.MODEL_OPUS, confidence_basis_points=950,
                       cost_governed=True, fell_back_to_static=False)
    assert isinstance(mc.confidence_basis_points, int)
    assert not isinstance(mc.confidence_basis_points, bool)
