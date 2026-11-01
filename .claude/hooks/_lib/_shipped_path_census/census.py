"""AST-based census of local imports versus selective installer delivery.

No shell is executed. An installer contract that cannot be established is
reported as unproven, never treated as evidence of successful delivery.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
from typing import Dict, List, Optional


def _function(shell: str, name: str) -> Optional[str]:
    match = re.search(r"(?m)^" + re.escape(name) + r"\(\)\s*\{\s*$", shell)
    if match is None:
        return None
    # The three target functions use shell blocks with closing braces at BOL.
    end = re.search(r"(?m)^}\s*$", shell[match.end():])
    return shell[match.end():match.end() + end.start()] if end else None


def _installer_evidence(path: Path) -> Dict[str, str]:
    try:
        shell = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {"scripts": "unproven: installer unreadable: " + str(exc),
                "hooks": "unproven: installer unreadable: " + str(exc),
                "lib": "unproven: installer unreadable: " + str(exc)}
    executable = "\n".join(line for line in shell.splitlines()
                           if not line.lstrip().startswith("#"))
    scripts = _function(executable, "install_scripts_selective")
    hooks = _function(executable, "install_hooks_selective")
    lib = _function(executable, "install_lib_selective")
    evidence = {}
    for name, body, glob, target in (
        ("scripts", scripts, r'"$SOURCE_DIR/.claude/scripts/"*.py', '.claude/scripts/$base'),
        ("hooks", hooks, r'"$SOURCE_DIR/.claude/hooks/"*.py', '.claude/hooks/$base'),
    ):
        if (body is not None and glob in body and
                'install_one "' + target + '"' in body and
                re.search(r'(?m)^install_' + re.escape(name) + r'_selective\s*$',
                          executable) is not None):
            evidence[name] = "proven: top-level Python files"
        else:
            evidence[name] = "unproven: selective top-level copy or invocation not established"
    if (lib is not None and hooks is not None and
            'install_lib_selective' in hooks and
            '"$SOURCE_DIR/.claude/hooks/_lib/"*' in lib and
            'install_one ".claude/hooks/_lib/$base"' in lib and
            evidence["hooks"].startswith("proven:")):
        evidence["lib"] = "proven: recursive package directories via install_one"
    else:
        evidence["lib"] = "unproven: recursive _lib package copy or invocation not established"
    # install_one may change from copying directories recursively.
    installer = _function(executable, "install_one")
    if installer is None or not re.search(r'\bcp\s+-[A-Za-z]*[Rr]', installer):
        evidence["lib"] = "unproven: recursive directory copy in install_one not established"
    return evidence


def _package_root(base: Path, module: str) -> Optional[Path]:
    """Return the first local directory package imported by a module."""
    first = module.split(".", 1)[0]
    directory = base / first
    if directory.is_dir() and (directory / "__init__.py").is_file():
        return directory
    return None


def census_shipped_paths(repo_root: Path) -> Dict[str, object]:
    """Report deterministic ``dependencies``, ``missing`` and ``unproven``.

    Local imports from either entrypoint directory are resolved against both
    their own directory and hooks/_lib (the framework's shared Python path).
    External and stdlib modules are not guessed to be local packages.
    """
    root = Path(repo_root)
    scripts = root / ".claude/scripts"
    hooks = root / ".claude/hooks"
    library = hooks / "_lib"
    evidence = _installer_evidence(root / "scripts/install.sh")
    dependencies: List[Dict[str, object]] = []
    missing: List[Dict[str, object]] = []
    unproven: List[Dict[str, object]] = []
    for delivery, status in evidence.items():
        if not status.startswith("proven:"):
            unproven.append({"source": "scripts/install.sh", "line": 0,
                             "reason": delivery + ": " + status})
    scanned = 0
    for directory, kind in ((scripts, "scripts"), (hooks, "hooks")):
        for source in sorted(directory.glob("*.py")):
            scanned += 1
            relative_source = source.relative_to(root).as_posix()
            if not evidence[kind].startswith("proven:"):
                unproven.append({"source": relative_source, "line": 0,
                                 "reason": evidence[kind]})
            try:
                tree = ast.parse(source.read_text(encoding="utf-8"), filename=relative_source)
            except (SyntaxError, OSError, UnicodeError) as exc:
                unproven.append({"source": relative_source, "line": 0,
                                 "reason": "AST unavailable: " + str(exc)})
                continue
            found = set()
            for node in ast.walk(tree):
                candidates = []
                if isinstance(node, ast.Import):
                    candidates = [(name.name, False) for name in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        # A relative import from a top-level module addresses
                        # package context that the direct installer cannot prove.
                        candidates = [(node.module or name.name, True)
                                      for name in node.names]
                    elif node.module:
                        candidates = [(node.module, False)]
                        if node.module == "_lib":
                            candidates.extend(("_lib." + name.name, False)
                                              for name in node.names)
                for module, relative in candidates:
                    package = None
                    delivery = kind
                    if module.startswith("_lib."):
                        package = _package_root(library, module[5:])
                        delivery = "lib"
                    elif module == "_lib":
                        package = library if (library / "__init__.py").is_file() else None
                        delivery = "lib"
                    else:
                        package = _package_root(directory, module)
                        if package is None:
                            package = _package_root(library, module)
                            if package is not None:
                                delivery = "lib"
                    if relative:
                        record = {"source": relative_source, "line": node.lineno,
                                  "module": "." + module,
                                  "reason": "relative import from top-level entrypoint is not proven"}
                        unproven.append(record)
                        continue
                    if package is None:
                        continue
                    if package.is_symlink():
                        unproven.append({"source": relative_source, "line": node.lineno,
                                         "module": module,
                                         "reason": "package path is a symlink; delivery target unproven"})
                        continue
                    package_path = package.relative_to(root).as_posix()
                    key = (node.lineno, module, package_path)
                    if key in found:
                        continue
                    found.add(key)
                    record = {"source": relative_source, "line": node.lineno,
                              "module": module, "package": package_path,
                              "delivery": delivery}
                    dependencies.append(record)
                    if delivery in ("scripts", "hooks"):
                        missing.append(dict(record, reason=delivery + " selective installer copies only top-level files"))
                    elif package.name in {"tests", "__pycache__"}:
                        missing.append(dict(record, reason="_lib package excluded by selective installer"))
                    elif not evidence[delivery].startswith("proven:"):
                        unproven.append(dict(record, reason=evidence[delivery]))
    if scanned == 0:
        unproven.append({"source": ".claude", "line": 0,
                         "reason": "no top-level Python entrypoints found to census"})
    key = lambda row: (row["source"], row["line"], row.get("module", ""), row.get("reason", ""))
    return {"ok": not missing and not unproven,
            "installer": evidence,
            "dependencies": sorted(dependencies, key=key),
            "missing": sorted(missing, key=key),
            "unproven": sorted(unproven, key=key)}
