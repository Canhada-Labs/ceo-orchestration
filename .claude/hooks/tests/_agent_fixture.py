"""PLAN-106-FOLLOWUP Wave A.1 — agent-binding sandbox fixture helper.

Materializes `.claude/agents/<name>.md` files inside a TestEnvContext
sandbox so the VETO floor (ADR-052 + PLAN-045 Wave 1 P0-03 model-binding
check) allows dispatch through in test scenarios.

**Source-of-truth pattern** (Codex iter-2 fold): we READ the real
on-disk `.claude/agents/<name>.md` and copy its frontmatter into the
sandbox. We do NOT hardcode model strings, because hardcoding caused
the Codex iter-2 P0 — qa-architect ships with `model: claude-sonnet-4-6`
on disk; a hardcoded `claude-opus-4-8` constant would silently
contradict the real binding.

**Containment** (identity-trust M1 / security M1): writes are refused
if the resolved sandbox_dir is NOT inside the test_env's `_tmp_root`.
There is zero way for this helper to write under the REAL repo's
`.claude/agents/` directory.

Public API:
    materialize_agent_binding(sandbox_dir: Path, name: str,
                              real_agents_dir: Optional[Path] = None,
                              tmp_root: Optional[Path] = None) -> Path

Returns the Path of the materialized file inside sandbox_dir.
Raises FileNotFoundError if the real binding does not exist.
Raises ValueError if sandbox_dir escapes tmp_root containment.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


_REAL_AGENTS_DIR_DEFAULT = (
    Path(__file__).resolve().parents[3] / ".claude" / "agents"
)

# Whitelist of frontmatter keys we faithfully copy from the real binding.
# Anything else (e.g. `tools:` YAML inline list) is dropped — they are
# not relevant to the VETO-floor enforcement gate.
_COPYABLE_KEYS = ("name", "description", "model", "veto_floor", "version")


def _parse_flat_frontmatter(text: str) -> dict:
    """Stdlib-only YAML-flat-frontmatter parser; same shape as apply-patches."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if m is None:
        raise ValueError("missing `---` frontmatter delimiter pair")
    fm: dict = {}
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if value.lower() == "true":
            fm[key] = True
        elif value.lower() == "false":
            fm[key] = False
        elif (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            fm[key] = value[1:-1]
        else:
            fm[key] = value
    return fm


def _render_frontmatter(fm: dict) -> str:
    lines = ["---"]
    for k in _COPYABLE_KEYS:
        if k not in fm:
            continue
        v = fm[k]
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            # Avoid pathological YAML edge cases by quoting strings that
            # contain `:` or start with special chars.
            sv = str(v)
            if any(c in sv for c in (":", "#", "[", "]", "{", "}")):
                # Use double-quoted form; escape any embedded `"`.
                escaped = sv.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{k}: "{escaped}"')
            else:
                lines.append(f"{k}: {sv}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def materialize_agent_binding(
    sandbox_dir: Path,
    name: str,
    real_agents_dir: Optional[Path] = None,
    tmp_root: Optional[Path] = None,
) -> Path:
    """Materialize `.claude/agents/<name>.md` inside sandbox_dir.

    Args:
        sandbox_dir: The sandbox root (typically TestEnvContext.project_dir).
            The materialized file is written to
            `<sandbox_dir>/.claude/agents/<name>.md`.
        name: Agent name (basename without `.md`). Must match an
            existing file under real_agents_dir.
        real_agents_dir: Optional override for the source agent dir. If
            None, defaults to the repo's `.claude/agents/`. Used by
            tests to point at a custom on-disk binding.
        tmp_root: Optional sandbox containment root. If provided, this
            helper REFUSES to write anywhere outside this root (raises
            ValueError). Pass `test_env._tmp_root` from TestEnvContext
            to enforce defense-in-depth.

    Returns:
        Path to the materialized binding file.

    Raises:
        FileNotFoundError: real binding does not exist.
        ValueError: sandbox_dir escapes tmp_root containment.
    """
    src_dir = real_agents_dir if real_agents_dir is not None else _REAL_AGENTS_DIR_DEFAULT
    src = src_dir / f"{name}.md"
    if not src.is_file():
        raise FileNotFoundError(
            f"real agent binding does not exist: {src}"
        )

    sandbox_dir_resolved = sandbox_dir.resolve()
    if tmp_root is not None:
        tmp_root_resolved = tmp_root.resolve()
        try:
            sandbox_dir_resolved.relative_to(tmp_root_resolved)
        except ValueError as exc:
            raise ValueError(
                f"sandbox_dir {sandbox_dir_resolved} escapes tmp_root "
                f"{tmp_root_resolved} — refusing to materialize agent binding"
            ) from exc

    real_text = src.read_text(encoding="utf-8")
    fm = _parse_flat_frontmatter(real_text)
    # Defensive: pin name to the parameter to avoid drift if disk says otherwise.
    fm.setdefault("name", name)
    new_text = (
        _render_frontmatter(fm)
        + f"\n# {fm.get('name', name)} — sandbox fixture\n"
        + "\nSandbox-materialized binding for TestEnvContext fixture.\n"
    )

    dst = sandbox_dir_resolved / ".claude" / "agents" / f"{name}.md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(new_text, encoding="utf-8")
    return dst
