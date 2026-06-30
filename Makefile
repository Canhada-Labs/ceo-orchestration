# Makefile — ceo-orchestration framework
# PLAN-063 DIM-06 P2d. Provides stable wrapper commands so docs can cite
# `make test-collect` instead of long pytest invocations that drift.

.PHONY: test-collect test-quick help

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

test-collect:  ## Print total test count (drives docs)
	@python3 -m pytest --collect-only -q 2>&1 | tail -1

test-quick:  ## Run hooks + scripts test roots only (fast, ~30s)
	python3 -m pytest .claude/hooks/tests .claude/scripts/tests -q
