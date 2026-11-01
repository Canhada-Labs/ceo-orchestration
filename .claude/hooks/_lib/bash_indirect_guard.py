"""Additive, bounded shell-command position scanner for PLAN-195.

This is deliberately not a shell evaluator: it follows only source-visible
command positions and shell bodies, and never expands variables or executes
subprocesses.  Unrecognised input is left to the existing guards.
"""

from __future__ import annotations

import os
import fnmatch
import itertools
import re
import shlex
from dataclasses import dataclass
from typing import List, Optional


MAX_DEPTH = 8
MAX_BODY_BYTES = 16384
MAX_WORDS = 1024
SEPARATORS = frozenset((";", "|", "||", "&", "&&", "(", ")", "{", "}", "\n"))
SHELLS = frozenset(("sh", "bash", "dash", "zsh", "ksh"))
RESERVED = frozenset((
    "if", "then", "elif", "else", "fi", "while", "until", "do", "done",
    "for", "in", "case", "esac", "select", "time", "!", "function",
))
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*=")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z_0-9]*)\1[^\n]*\n")
STATIC_PRINTF = re.compile(
    r"\$\(\s*printf\s+(?:['\"]%s['\"]\s+)?([A-Za-z0-9_./-]+)\s*\)"
)
VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z_0-9]*)\}|([A-Za-z_][A-Za-z_0-9]*))")
_QUOTED_OPERATORS = {ch: chr(0xF100 + index) for index, ch in enumerate(";&|(){}")}
_RESTORE_OPERATORS = {value: key for key, value in _QUOTED_OPERATORS.items()}


@dataclass(frozen=True)
class GuardHit:
    reason_code: str
    reason: str


def _hit(code: str) -> GuardHit:
    return GuardHit(
        code,
        "BLOCKED: indirect shell execution (%s). Write the executable "
        "command in direct form so the Bash safety guard can judge it."
        % code,
    )


def _prelex(command: str) -> str:
    """Keep literal mid-word # and newline boundaries; strip true comments.

    The shell opens a comment only outside quotes at the start of a word.
    An escaped # never introduces a comment.  Quote characters occurring
    inside comments do not change parser state.
    """
    out: List[str] = []
    quote = ""
    escaped = False
    word_start = True
    commenting = False
    for ch in command:
        if commenting:
            if ch == "\n":
                out.append(ch)
                commenting = False
                word_start = True
            continue
        if escaped:
            out.append(ch)
            escaped = False
            word_start = False
            continue
        if ch == "\\" and quote != "'":
            out.append(ch)
            escaped = True
            continue
        if ch == quote:
            quote = ""
            out.append(ch)
            word_start = False
            continue
        if ch in ("'", '"') and not quote:
            quote = ch
            out.append(ch)
            word_start = False
            continue
        if ch == "#" and not quote and word_start:
            commenting = True
            continue
        out.append(ch)
        if not quote:
            word_start = ch.isspace() or ch in ";&|(){}<>"
    return "".join(out)


def _words(command: str) -> List[str]:
    text = _prelex(command)
    shielded: List[str] = []
    quote = ""
    escaped = False
    for ch in text:
        if escaped:
            shielded.append(ch)
            escaped = False
        elif ch == "\\" and quote != "'":
            shielded.append(ch)
            escaped = True
        elif ch == quote:
            quote = ""
            shielded.append(ch)
        elif ch in ("'", '"') and not quote:
            quote = ch
            shielded.append(ch)
        else:
            shielded.append(_QUOTED_OPERATORS.get(ch, ch) if quote else ch)
    lexer = shlex.shlex("".join(shielded), posix=True,
                        punctuation_chars=";&|()<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    words = list(lexer)
    if len(words) > MAX_WORDS:
        raise ValueError("word ceiling")
    return words


def _unshield(value: str) -> str:
    for hidden, literal in _RESTORE_OPERATORS.items():
        value = value.replace(hidden, literal)
    return value


def _command_substitutions(command: str, depth: int,
                           heuristics: bool = True,
                           source_comments: bool = True) -> Optional[GuardHit]:
    """Inspect executable $(...) even inside double quotes, never single."""
    # Strip comments in shell SOURCE.  Unquoted here-doc bodies are DATA:
    # their `# $(...)` still undergoes command substitution before delivery.
    if source_comments:
        command = _prelex(command)
    index = 0
    quote = ""
    while index < len(command):
        ch = command[index]
        if ch == "\\" and quote != "'":
            index += 2
            continue
        if ch == quote:
            quote = ""
        elif ch in ("'", '"') and not quote:
            quote = ch
        elif (quote != "'" and command[index:index + 2] == "$(") or (
            not quote and command[index:index + 2] in ("<(", ">(")
        ):
            start = index + 2
            level = 1
            cursor = start
            while cursor < len(command):
                if command[cursor:cursor + 2] == "$(":
                    level += 1
                    cursor += 2
                    continue
                if command[cursor] == ")":
                    level -= 1
                    if level == 0:
                        hit = _scan(command[start:cursor], depth + 1,
                                    strict=True, heuristics=heuristics)
                        if hit:
                            return hit
                        index = cursor + 1
                        break
                cursor += 1
            else:
                return _hit("bash_indirect_unparseable_shell")
            continue
        elif ch == "`" and quote != "'":
            cursor = index + 1
            while cursor < len(command):
                if command[cursor] == "\\":
                    cursor += 2
                    continue
                if command[cursor] == "`":
                    hit = _scan(command[index + 1:cursor], depth + 1,
                                strict=True, heuristics=heuristics)
                    if hit:
                        return hit
                    index = cursor + 1
                    break
                cursor += 1
            else:
                return _hit("bash_indirect_unparseable_shell")
            continue
        index += 1
    return None


def _extract_heredocs(command: str, depth: int,
                      heuristics: bool = True) -> tuple:
    """Strip here-doc DATA; parse a shell consumer's PROGRAM body.

    A nonquoted delimiter expands command substitutions even when the
    consumer is a data-only tool.  This is separate from interpreting the
    heredoc as shell source, which only a visible shell consumer does.
    """
    bodies: List[str] = []
    output: List[str] = []
    cursor = 0
    while True:
        match = HEREDOC.search(command, cursor)
        if match is None:
            output.append(command[cursor:])
            break
        begin = match.end()
        closing = re.search(r"(?m)^" + re.escape(match.group(2)) + r"[ \t]*(?:\n|$)",
                            command[begin:])
        if closing is None:
            output.append(command[cursor:])
            break
        body = command[begin:begin + closing.start()]
        prefix = command[cursor:match.start()]
        output.append(prefix + command[match.start():begin])
        consumer_tokens = prefix.strip().split()
        consumer = os.path.basename(consumer_tokens[0]) if consumer_tokens else ""
        if not match.group(1):
            substitutions = _command_substitutions(
                body, depth, heuristics, source_comments=False
            )
            if substitutions:
                return "", [substitutions]
        if consumer in SHELLS or consumer == "eval":
            bodies.append(body)
        cursor = begin + closing.end()
    return "".join(output), bodies


def _normalise(argv: List[str]) -> List[str]:
    """Consume known launchers, flags, and same-command env assignments."""
    tokens = list(argv)
    for _ in range(12):
        if not tokens:
            break
        head = os.path.basename(tokens[0].lstrip("\\")).lower()
        if ASSIGNMENT.match(tokens[0]):
            tokens.pop(0)
            continue
        if head in ("sudo", "doas", "nocorrect", "command", "builtin", "nohup"):
            tokens.pop(0)
            while tokens and tokens[0].startswith("-"):
                flag = tokens.pop(0)
                if flag in ("-u", "--user", "-g", "--group") and tokens:
                    tokens.pop(0)
            continue
        if head == "env":
            tokens.pop(0)
            while tokens and (tokens[0].startswith("-") or ASSIGNMENT.match(tokens[0])):
                flag = tokens.pop(0)
                if flag in ("-u", "--unset", "-C", "--chdir") and tokens:
                    tokens.pop(0)
            continue
        tokens[0] = head
        break
    return tokens


def _git_verb(argv: List[str]) -> Optional[str]:
    if not argv or argv[0] != "git":
        return None
    idx = 1
    while idx < len(argv) and argv[idx].startswith("-"):
        flag = argv[idx]
        idx += 1
        if flag in ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"):
            idx += 1
    if idx >= len(argv):
        return None
    verb = argv[idx].lower()
    rest = argv[idx + 1:]
    if verb == "reset" and "--hard" in rest:
        return "bash_indirect_git_reset"
    if verb == "push" and any(item in ("-f", "--force") for item in rest):
        return "bash_indirect_git_push"
    return None


def _destructive(argv: List[str]) -> Optional[str]:
    tokens = _normalise(argv)
    if not tokens:
        return None
    if tokens[0] == "rm":
        flags = [token for token in tokens[1:] if token.startswith("-")]
        recursive = any(
            token.split("=", 1)[0].lower() in ("--recursive", "--r")
            or (not token.startswith("--") and "r" in token.lower())
            for token in flags
        )
        force = any(
            token.split("=", 1)[0].lower() == "--force"
            or (not token.startswith("--") and "f" in token.lower())
            for token in flags
        )
        if recursive and force:
            return "bash_indirect_rm_rf"
    return _git_verb(tokens)


def _shell_body(argv: List[str]) -> Optional[str]:
    if not argv or argv[0] not in SHELLS:
        return None
    for index, token in enumerate(argv[1:], 1):
        if token in ("-c", "--command") or (
            token.startswith("-") and not token.startswith("--") and "c" in token[1:]
        ):
            return argv[index + 1] if index + 1 < len(argv) else ""
    return None


def _brace_commands(token: str) -> List[str]:
    opening = token.find("{")
    closing = token.find("}", opening + 1)
    if opening < 0 or closing < 0:
        return [token]
    body = token[opening + 1:closing]
    if "," in body:
        variants = body.split(",")
    else:
        numeric = re.fullmatch(r"(-?\d+)\.\.(-?\d+)(?:\.\.(-?\d+))?", body)
        if numeric is None:
            return [token]
        first, last = int(numeric.group(1)), int(numeric.group(2))
        # Bash takes the magnitude of an explicit step, chooses direction
        # from the endpoints, and treats a zero step as one.
        stride = abs(int(numeric.group(3))) if numeric.group(3) else 1
        step = (stride or 1) * (1 if first <= last else -1)
        count = abs(last - first) // abs(step) + 1
        if count > 128:
            raise ValueError("brace ceiling")
        variants = [str(first + i * step) for i in range(count)]
    if len(variants) > 128:
        raise ValueError("brace ceiling")
    return [token[:opening] + item + token[closing + 1:] for item in variants]


def _scan_segment(argv: List[str], depth: int,
                  heuristics: bool = True) -> Optional[GuardHit]:
    if not argv:
        return None
    head = os.path.basename(argv[0].lstrip("\\")).lower()
    if head == "env":
        for index, arg in enumerate(argv[1:], 1):
            if arg in ("-S", "--split-string"):
                return _scan(" ".join(_unshield(w) for w in argv[index + 1:]),
                             depth + 1, strict=True, heuristics=heuristics)
        if heuristics and any(arg.startswith("--") and arg not in (
            "--ignore-environment", "--null", "--debug", "--unset",
            "--chdir", "--argv0", "--split-string",
        ) for arg in argv[1:]):
            if any(marker in argv for marker in ("-rf", "-fr", "--hard", "--force")):
                return _hit("bash_indirect_ambiguous_launcher")
    try:
        expanded = [_brace_commands(word) for word in argv]
    except ValueError:
        return _hit("bash_indirect_limit")
    combinations = 1
    for options in expanded:
        combinations *= len(options)
        if combinations > 128:
            return _hit("bash_indirect_limit")
    for candidate in itertools.product(*expanded):
        code = _destructive(list(candidate))
        if code:
            return _hit(code)
    normal = _normalise(argv)
    if not normal:
        return None
    shell_body = _shell_body(normal)
    if shell_body is not None:
        return _scan(_unshield(shell_body), depth + 1,
                     strict=True, heuristics=heuristics)
    if normal[0] == "eval" and len(normal) > 1:
        return _scan(" ".join(_unshield(w) for w in normal[1:]), depth + 1,
                     strict=True, heuristics=heuristics)
    if normal[0] == "xargs":
        pos = 1
        while pos < len(normal) and normal[pos].startswith("-"):
            flag = normal[pos]
            pos += 1
            if flag in ("-I", "-L", "-n", "-P", "-s", "-d", "-E") and pos < len(normal):
                pos += 1
        return _scan_segment(normal[pos:], depth + 1, heuristics)
    if normal[0] == "find":
        for index, token in enumerate(normal):
            if token in ("-exec", "-execdir", "-ok", "-okdir"):
                tail = normal[index + 1:]
                return _scan_segment([w for w in tail if w not in (";", "+")],
                                     depth + 1, heuristics)
    if heuristics and ("$" in normal[0] or "`" in normal[0]) and any(
        w in ("--hard", "--force", "-rf", "-fr", "-r", "-f") for w in normal[1:]
    ):
        return _hit("bash_indirect_computed_verb")
    return None


def _canonical_target(target: str, cwd: str, assignments: dict) -> bool:
    """Bounded textual resolution: no glob expansion or filesystem access."""
    try:
        from check_canonical_edit import _CANONICAL_GUARDS, _fnmatch_segments
    except ImportError:
        return False  # infrastructure failures must fail-open
    value = target.strip("'\"")
    value = VARIABLE.sub(
        lambda match: assignments.get(match.group(1) or match.group(2), ""), value
    )
    if not value:
        return False
    if value.startswith("/"):
        project = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project or not value.startswith(project.rstrip("/") + "/"):
            return False
        value = value[len(project.rstrip("/")) + 1:]
    else:
        value = os.path.normpath(os.path.join(cwd, value))
    for pattern in _CANONICAL_GUARDS:
        if _fnmatch_segments(value, pattern):
            return True
        # Glob target: prefer static-pattern membership with >=4 literal
        # characters to avoid locking out ordinary variable-driven scripts.
        if any(ch in value for ch in "*?[") and sum(
            ch.isalnum() for ch in value
        ) >= 4 and not any(ch in pattern for ch in "*?["):
            if fnmatch.fnmatchcase(pattern.lower(), value.lower()):
                return True
    return False


def _computed_target(argv: List[str], cwd: str, assignments: dict) -> Optional[GuardHit]:
    if not argv:
        return None
    targets: List[str] = []
    for idx, word in enumerate(argv[:-1]):
        if word in (">", ">>", ">|", "&>", "<>" ):
            targets.append(argv[idx + 1])
    normal = _normalise(argv)
    if normal and normal[0] == "tee":
        targets += [arg for arg in normal[1:] if not arg.startswith("-")]
    if normal and normal[0] == "sed" and any(
        arg.startswith("-i") for arg in normal[1:]
    ):
        targets += normal[2:][-1:]
    if normal and normal[0] == "dd":
        targets += [arg[3:] for arg in normal[1:] if arg.startswith("of=")]
    if normal and normal[0] in ("python", "python3", "node", "ruby", "perl"):
        for index, argument in enumerate(normal[1:], 1):
            if argument in ("-c", "-e", "-E", "--eval") and index + 2 < len(normal):
                for operand in normal[index + 2:]:
                    if _canonical_target(operand, cwd, assignments):
                        return _hit("bash_computed_canonical_target")
                break
    for target in targets:
        if _canonical_target(target, cwd, assignments) and (
            "$" in target or any(ch in target for ch in "*?[") or cwd
        ):
            return _hit("bash_computed_canonical_target")
    return None


def _scan(command: str, depth: int, *, strict: bool = False,
          heuristics: bool = True) -> Optional[GuardHit]:
    if depth > MAX_DEPTH or len(command) > MAX_BODY_BYTES:
        return _hit("bash_indirect_limit")
    command, heredoc_bodies = _extract_heredocs(command, depth, heuristics)
    for body in heredoc_bodies:
        if isinstance(body, GuardHit):
            return body
        hit = _scan(body, depth + 1, strict=True, heuristics=heuristics)
        if hit:
            return hit
    substitution_hit = _command_substitutions(command, depth, heuristics)
    if substitution_hit:
        return substitution_hit
    # A small, statically decidable output producer for same-command targets.
    # No process is started and anything beyond this exact printf form stays
    # unresolved (and therefore is not blindly blocked).
    command = STATIC_PRINTF.sub(lambda match: match.group(1), command)
    try:
        words = _words(command)
    except ValueError as exc:
        if str(exc) == "word ceiling":
            return _hit("bash_indirect_limit")
        return _hit("bash_indirect_unparseable_shell") if strict else None
    segment: List[str] = []
    cwd = ""
    assignments: dict = {}
    aliases: dict = {}
    previous_separator = ""
    for token in words + [";"]:
        if token in SEPARATORS or (token and all(ch in ";&|(){}" for ch in token)):
            normal = _normalise(segment)
            if normal and normal[0] == "alias":
                for definition in normal[1:]:
                    if ASSIGNMENT.match(definition):
                        name, value = definition.split("=", 1)
                        aliases[name] = _unshield(value)
            elif normal and normal[0] in aliases:
                expanded_alias = aliases[normal[0]] + " " + " ".join(
                    shlex.quote(_unshield(arg)) for arg in normal[1:]
                )
                hit = _scan(expanded_alias, depth + 1,
                            strict=True, heuristics=heuristics)
                if hit:
                    return hit
            if normal and normal[0] in SHELLS and _shell_body(normal) is None:
                if "<<<" in segment:
                    position = segment.index("<<<")
                    if position + 1 < len(segment):
                        hit = _scan(_unshield(segment[position + 1]), depth + 1,
                                    strict=True, heuristics=heuristics)
                        if hit:
                            return hit
                if heuristics and (previous_separator in ("|", "|&") or "<" in segment):
                    return _hit("bash_indirect_opaque_stdin")
            hit = _scan_segment(segment, depth, heuristics)
            if hit:
                return hit
            if segment and segment[0] == "cd" and len(segment) >= 2:
                cwd = os.path.normpath(os.path.join(cwd, segment[1]))
            for word in segment:
                if ASSIGNMENT.match(word):
                    key, value = word.split("=", 1)
                    if "$" not in value and "`" not in value:
                        assignments[key] = value
            target_hit = _computed_target(segment, cwd, assignments)
            if target_hit:
                return target_hit
            segment = []
            previous_separator = token
        elif token.lower() in RESERVED and not segment:
            continue
        else:
            segment.append(token)
    return None


def scan(command: str, *, heuristics: bool = True) -> Optional[GuardHit]:
    """Return a monotonic additional veto, never an ALLOW override."""
    return _scan(command, 0, heuristics=heuristics)
