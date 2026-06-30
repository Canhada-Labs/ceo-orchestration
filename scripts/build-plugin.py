#!/usr/bin/env python3
"""Build the Claude Code plugin `ceo` from the live .claude/ tree.

Generates dist/ceo-plugin/ (the plugin) + dist/ceo-marketplace/ (a marketplace
that lists it). Reproducible: re-run after changing .claude/ to refresh.

Scope = the `--ceremony user` (advisory) surface + the PLAN-128 accelerators.
The canonical/GPG self-protection hooks are copied (so imports don't break) but
NOT registered in hooks.json — they only protect the framework's own repo and
need the Owner's GPG key, which an adopter does not have.

Usage:  python3 scripts/build-plugin.py [--out dist]
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_ROOT = REPO / "dist"
PLUGIN = OUT_ROOT / "ceo-plugin"
MARKET = OUT_ROOT / "ceo-marketplace"
NS = "ceo"
VERSION = (REPO / "VERSION").read_text().strip()

# Accelerators (PLAN-128) to add on top of the advisory settings.user.json set.
ACCEL = {
    "PostToolUse": [
        {"matcher": "Edit|Write|MultiEdit", "hooks": [
            {"type": "command",
             "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh" accel_dispatch.py',
             "timeout": 20, "statusMessage": "Verifying edit..."}]},
    ],
    "Stop": [
        {"matcher": "", "hooks": [
            {"type": "command",
             "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh" codex_review_user_code.py',
             "timeout": 130, "statusMessage": "Checking for risky diff..."},
            {"type": "command",
             "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh" review_loop.py',
             "timeout": 60}]},
    ],
    "SessionStart": [
        {"matcher": "", "hooks": [
            {"type": "command",
             "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh" turbo_sessionstart.py',
             "timeout": 10}]},
    ],
}


def log(msg: str) -> None:
    print(f"[build-plugin] {msg}")


def clean() -> None:
    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    (PLUGIN / ".claude-plugin").mkdir(parents=True)
    (MARKET / ".claude-plugin").mkdir(parents=True)


def write_manifest() -> None:
    manifest = {
        "name": NS,
        "description": (
            "CEO Orchestration — run Claude Code as a governed team of specialist agents: "
            "Plan->Debate->Execute, tamper-evident audit chain, cross-LLM Codex review, "
            "151 skill checklists, and a zero-config edit->verify->review accelerator loop."
        ),
        "version": VERSION,
        "author": {"name": "CEO Orchestration"},
        "license": "MIT",
        "keywords": ["governance", "audit", "orchestration", "agents", "skills", "code-review"],
    }
    (PLUGIN / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n")
    log("wrote plugin.json")


def iter_skills():
    """Yield (profile, src_dir) for every SKILL.md-bearing directory."""
    core = REPO / ".claude/skills/core"
    front = REPO / ".claude/skills/frontend"
    domains = REPO / ".claude/skills/domains"
    for d in sorted(core.glob("*/")):
        if (d / "SKILL.md").exists():
            yield ("core", d)
    for d in sorted(front.glob("*/")):
        if (d / "SKILL.md").exists():
            yield ("frontend", d)
    for dom in sorted(domains.glob("*/")):
        sk = dom / "skills"
        if not sk.is_dir():
            continue
        for d in sorted(sk.glob("*/")):
            if (d / "SKILL.md").exists():
                yield (dom.name, d)


def copy_skills() -> int:
    dst_root = PLUGIN / "skills"
    dst_root.mkdir(parents=True, exist_ok=True)
    used: dict[str, str] = {}
    n = 0
    collisions = 0
    for profile, src in iter_skills():
        base = src.name
        name = base
        if name in used:
            # collision: prefix with profile to keep it unique + give context
            name = f"{profile}-{base}"
            collisions += 1
            while name in used:
                name = f"{profile}-{name}"
        used[name] = str(src)
        shutil.copytree(src, dst_root / name)
        n += 1
    log(f"copied {n} skills ({collisions} name collisions disambiguated)")
    return n


def copy_dir(rel_src: str, rel_dst: str, pattern: str = "*") -> int:
    src = REPO / rel_src
    dst = PLUGIN / rel_dst
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(src.glob(pattern)):
        if f.is_file():
            shutil.copy2(f, dst / f.name)
            n += 1
    return n


def _sanitize_frontmatter(text: str) -> str:
    """Re-emit risky frontmatter string fields as JSON-quoted so a strict YAML
    parser accepts them. The Claude Code native loader is tolerant; `claude
    plugin validate` is not. Only quotes scalar string fields that aren't
    already quoted and aren't flow collections (tools: [..])."""
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    fm, body = parts[1], parts[2]
    quote_keys = ("description", "whenToUse")
    out = []
    for line in fm.splitlines():
        m = re.match(r"^(\w+):[ \t]+(.*)$", line)
        if m and m.group(1) in quote_keys:
            key, val = m.group(1), m.group(2)
            v = val.strip()
            if not (v.startswith('"') or v.startswith("'") or v.startswith("[") or v.startswith("|") or v.startswith(">")):
                out.append(f"{key}: {json.dumps(val, ensure_ascii=False)}")
                continue
        out.append(line)
    return "---" + "\n".join(out) + "---" + body


def copy_agents() -> int:
    src = REPO / ".claude/agents"
    dst = PLUGIN / "agents"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(src.glob("*.md")):
        if f.name.startswith("_"):
            continue  # internal framework-dev agents (_probe_* test probes, _dispatch index)
        (dst / f.name).write_text(_sanitize_frontmatter(f.read_text()))
        n += 1
    return n


def copy_hooks() -> None:
    """Copy ALL hook .py + _lib + shim (so imports resolve), then write a
    hooks.json that registers ONLY the advisory + accelerator subset."""
    src = REPO / ".claude/hooks"
    dst = PLUGIN / "hooks"
    dst.mkdir(parents=True, exist_ok=True)
    # top-level .py + .sh shim
    npy = 0
    for f in sorted(src.glob("*.py")):
        shutil.copy2(f, dst / f.name)
        npy += 1
    for sh in src.glob("_python-hook.sh"):
        shutil.copy2(sh, dst / sh.name)
    # _lib (runtime only; skip tests/ AND fixtures/ — the latter ships attack
    # samples (yaml_bomb, prototype_pollution) + a 64KiB padding file that trips
    # Claude Code's zip-bomb/compression-ratio heuristic on install. No runtime
    # _lib code reads fixtures/, so excluding it is safe.)
    shutil.copytree(src / "_lib", dst / "_lib",
                    ignore=shutil.ignore_patterns("tests", "fixtures", "__pycache__",
                                                  "test_*.py", "*_test.py", "conftest.py",
                                                  "test_isolation.py", "testing.py"))
    log(f"copied {npy} hook .py + _lib + shim")

    # Build hooks.json: advisory set (settings.user.json) + accelerators, paths rewritten.
    advisory = json.loads((REPO / "templates/settings/settings.user.json").read_text())
    hooks = advisory.get("hooks", {})
    for ev, arr in ACCEL.items():
        hooks.setdefault(ev, [])
        hooks[ev].extend(arr)

    def rewrite(obj):
        if isinstance(obj, dict):
            return {k: rewrite(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [rewrite(v) for v in obj]
        if isinstance(obj, str):
            return obj.replace('"$CLAUDE_PROJECT_DIR/.claude/hooks/',
                               '"${CLAUDE_PLUGIN_ROOT}/hooks/')
        return obj

    hooks = rewrite(hooks)
    (dst / "hooks.json").write_text(json.dumps({"hooks": hooks}, indent=2) + "\n")
    log("wrote hooks/hooks.json (advisory + accelerators, ${CLAUDE_PLUGIN_ROOT} paths)")


def write_readme(nskills: int, nagents: int, ncmds: int) -> None:
    txt = f"""# ceo — CEO Orchestration (Claude Code plugin)

Run Claude Code as a **governed team of specialist agents**: Plan -> Debate -> Execute, a
tamper-evident HMAC audit chain, cross-LLM (Codex) review, **{nskills} skill checklists**, and a
zero-config **edit -> verify -> review** accelerator loop. Namespace: `ceo` (commands are `/ceo:<name>`).

## What you get that raw Claude Code doesn't
- **{nskills} skills** (core + frontend + domain profiles) auto-activated by task context.
- **{nagents} specialist agents** (code-reviewer, security-engineer, qa-architect, …) with veto authority.
- **{ncmds} commands** — `/ceo:ceo-boot`, `/ceo:spawn`, `/ceo:debate`, `/ceo:status`, …
- **Advisory governance hooks** — spawn protocol, bash-safety, secret/injection scanning, audit log.
- **Accelerators (PLAN-128)** — after-edit verify+self-repair, Codex review of your diff, turbo profile.

## Install
```
/plugin marketplace add <owner>/<your-marketplace-repo>
/plugin install ceo@<your-marketplace>
```
Or test locally: `claude --plugin-dir ./ceo-plugin`

## Honest limitations
1. **Subagent model tiering is per-agent, not packageable as a global env.** Set `model:` in each
   agent's frontmatter (the bundled agents already do: code-review/security = opus, qa/perf = sonnet,
   devops = haiku). Do **NOT** set a global `{{ "env": {{ "CLAUDE_CODE_SUBAGENT_MODEL": "haiku" }} }}` —
   that env var is documented to OVERRIDE per-agent `model:` frontmatter and silently downgrades every
   subagent (removed from the framework in S218). For a cheap one-off, pass `model` at spawn time.
2. **Codex review needs the `codex` CLI.** Without it, the cross-model accelerators fail-open (advisory only).
3. **Skills are namespaced** (`/ceo:<skill>`) to avoid conflicts.
4. **No canonical/GPG self-protection.** This is the adopter (advisory) tier by design. The audit chain
   (HMAC, tamper-evident) still works; the guards that need the framework Owner's GPG key are intentionally absent.
5. **Turn it off:** `export CEO_TURBO=0` (or `touch .claude/turbo-off`) disables the accelerators; the
   advisory governance stays on.

## Source
Generated from the ceo-orchestration framework via `scripts/build-plugin.py` (v{VERSION}).
"""
    (PLUGIN / "README.md").write_text(txt)
    log("wrote README.md")


def write_marketplace() -> None:
    mkt = {
        "name": "ceo-marketplace",
        "owner": {"name": "CEO Orchestration"},
        "plugins": [
            {
                "name": NS,
                "source": "./ceo-plugin",
                "description": "CEO Orchestration — governed multi-agent Claude Code with audit + accelerators.",
                "version": VERSION,
            }
        ],
    }
    (MARKET / ".claude-plugin" / "marketplace.json").write_text(json.dumps(mkt, indent=2) + "\n")
    # symlink the plugin into the marketplace tree so `source: ./ceo-plugin` resolves
    link = MARKET / "ceo-plugin"
    if not link.exists():
        try:
            link.symlink_to(PLUGIN.resolve(), target_is_directory=True)
        except OSError:
            shutil.copytree(PLUGIN, link)
    log("wrote marketplace.json")


def sanitize_paths() -> int:
    """Strip the Owner's absolute path from the generated plugin (safe: only
    touches dist/, never the canonical source). Personal paths -> portable vars."""
    n = 0
    for f in PLUGIN.rglob("*"):
        if not f.is_file():
            continue
        try:
            txt = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        if "/Users/devuser" not in txt:
            continue
        new = txt.replace("/Users/devuser/ceo-orchestration", "$CLAUDE_PROJECT_DIR")
        new = new.replace("/Users/devuser", "$HOME")
        if new != txt:
            f.write_text(new)
            n += 1
    log(f"sanitized personal absolute path in {n} file(s)")
    return n


def identity_report() -> None:
    """Quantify remaining Owner-identity tokens in the generated plugin (for the
    Owner to decide before public release — some 'acme' hits are by-design)."""
    import collections
    counts = collections.Counter()
    examples = {}
    for tok in ("canhada", "acme", "adopter-1", "/Users/devuser"):
        for f in PLUGIN.rglob("*"):
            if not f.is_file():
                continue
            try:
                txt = f.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            if tok.lower() in txt.lower():
                counts[tok] += 1
                examples.setdefault(tok, str(f.relative_to(PLUGIN)))
    log("identity scan of generated plugin (for Owner decision before PUBLIC release):")
    for tok in ("canhada", "acme", "adopter-1", "/Users/devuser"):
        if counts[tok]:
            log(f"   {tok}: {counts[tok]} file(s)  e.g. {examples.get(tok,'')}")
        else:
            log(f"   {tok}: 0 (clean)")


def main() -> int:
    clean()
    write_manifest()
    n_sk = copy_skills()
    n_ag = copy_agents()
    n_cmd = copy_dir(".claude/commands", "commands", "*.md")
    log(f"copied {n_ag} agents, {n_cmd} commands")
    copy_hooks()
    write_readme(n_sk, n_ag, n_cmd)
    write_marketplace()
    sanitize_paths()
    identity_report()
    log(f"DONE -> {PLUGIN}")
    log(f"validate: claude plugin validate {PLUGIN}")
    log(f"smoke:    claude --plugin-dir {PLUGIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
