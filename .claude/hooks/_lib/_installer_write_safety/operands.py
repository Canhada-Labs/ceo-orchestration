from __future__ import annotations
from . import engine as _engine
for _engine_name in _engine.__all__:
    globals().setdefault(_engine_name, getattr(_engine, _engine_name))

# Operand canonicalisation and the occurrence index
# --------------------------------------------------------------------------

_RE_BRACED_NAME = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def canon_operand(tok_or_text) -> str:
    """Canonical shape of a word: quoting removed, ${x} normalised to $x."""
    text = tok_or_text.text if isinstance(tok_or_text, Tok) else tok_or_text
    out: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            out.append(text[i + 1])
            i += 2
            continue
        if c == "'":
            k = text.find("'", i + 1)
            if k < 0:
                out.append(text[i:])
                break
            out.append(text[i + 1:k])
            i = k + 1
            continue
        if c == '"':
            try:
                k, seg = _read_dquote(text, i)
            except ParseError:
                out.append(text[i + 1:])
                break
            out.append(seg[1:-1])
            i = k
            continue
        out.append(c)
        i += 1
    s = "".join(out)
    s = _RE_BRACED_NAME.sub(lambda m: "$" + m.group(1), s)
    return s


_RE_VARREF = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)")


def var_names(canon: str) -> Set[str]:
    return set(_RE_VARREF.findall(canon))


OCC_TEST = "test"
OCC_READ = "read"
OCC_WRITE = "write"
OCC_ALIAS = "alias"
OCC_UNKNOWN = "unknown"


class Occurrence(object):
    __slots__ = ("line_idx", "lineno", "kind", "cmd_name", "canon", "scope",
                 "argpos")

    def __init__(self, line_idx: int, lineno: int, kind: str,
                 cmd_name: Optional[str], canon: str,
                 scope: Tuple[int, ...], argpos: int = 0) -> None:
        self.line_idx = line_idx
        self.lineno = lineno
        self.kind = kind
        self.cmd_name = cmd_name
        self.canon = canon
        self.scope = scope
        self.argpos = argpos      # 1-based operand index, 0 when unknown


# --------------------------------------------------------------------------

__all__ = [name for name in globals() if not name.startswith("__") and name not in ("_engine", "_engine_name")]
