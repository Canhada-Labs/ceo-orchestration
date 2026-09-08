"""Per-instance salt for hash identifier privacy (ADR-079).

Provides ``get_instance_salt() -> bytes`` returning a 32-byte salt
loaded from ``~/.claude/projects/<slug>/.salt``. Generates the salt
on first call (``os.urandom(32)`` + file mode ``0o600``).

PLAN-058 Round-23 (2026-04-24) — closes the REAL identifier-privacy
issue at ``UserPromptSubmit.py:182`` (``prompt_sha`` is unsalted
SHA-256 of the user prompt; correlation oracle for any party with
audit-log read access). The Phase B audit's F-SEC-03 finding
referenced a phantom ``_hash_injection_prefix`` that does not exist;
the real attack surface is ``prompt_sha256`` published by every
``prompt_submitted`` audit event. See ADR-079 §Phantom rejection
for the full forensic record.

## Fail-open contract (ADR-005, ADR-010)

On any I/O failure (permission denied, disk full, broken symlink)
the function returns ``b""`` instead of raising. Callers compose the
empty salt with their input — the resulting hash degrades to the
pre-fix unsalted form. Confidentiality is best-effort; availability
is invariant.

## No rotation — with exactly ONE sanctioned, REGISTERED exception

Salt is generated once per PROJECT (ADR-079 S318 amendment: the salt
unit is the project, resolved via ``_lib/runtime_paths`` — the
per-``$HOME`` reading made ``prompt_sha256`` correlate ACROSS projects,
the exact oracle this module exists to close) and never rotated.
Rotating the salt would invalidate ``prompt_sha256`` correlations
across all historical audit events (the chief use of the field).

The one exception is the PLAN-182 migration itself: the project that
inherits the historical chain (W2 custody decision) inherits the
legacy ``.salt`` byte-for-byte; every OTHER project mints fresh — and
that minting is OBSERVABLE, never silent (the pre-S318 code minted
with no error, no log, no signal — silent rotation against this very
section). Every mint now (a) writes a ``salt-minted.json`` marker
sidecar next to the salt (forensic ground truth) and (b) best-effort
emits the registered ``salt_rotation_registered`` chain event.

## Thread safety

The module-level ``_CACHED_SALT`` is read-once-write-once, and the
FIRST MINT is elected by the filesystem: ``_generate_and_persist``
creates with ``O_CREAT|O_EXCL|O_NOFOLLOW``, so exactly one process
wins and every loser RE-READS the winner's bytes.

rc.1 re-pass part 6 C2 — this section used to accept the race, on the
grounds that "the winner's bytes seed the cache for both processes on
next call". That was false: the cache is a hit before any disk read
(``get_instance_salt`` returns at the ``_CACHED_SALT`` check), so each
loser kept and used the value it had generated, and the ``.salt`` on
disk was whatever the last ``write_bytes`` left behind. The re-pass
reproduced it with a spin barrier: **5 of 5 rounds, 6 of 6 processes
holding DISTINCT salts, 5 of them orphaned** — and every
``prompt_sha256`` an orphan emitted is irreproducible from the
persisted salt, which is the one thing this module exists to keep
reproducible. The window is small and opens at most once per project,
but the upgrade to v1.4 re-opens it in EVERY project at once.

A salt that is already on disk and MALFORMED is a different case: that
is a deliberate rotation (``reason="other"``), and it still replaces
the file — with ``O_NOFOLLOW`` but without ``O_EXCL``.

## Stdlib-only

Per hook discipline (ADR-002): stdlib only. The only intra-``_lib``
import is ``runtime_paths`` (itself a stdlib-only leaf), so the module
stays loadable from any hook; ``audit_emit`` is imported LAZILY inside
the mint branch only (mint happens at most once per project lifetime).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional, Tuple

try:  # loaded as package member (_lib.injection_salt)
    from . import runtime_paths as _runtime_paths
except ImportError:  # loaded bare (sys.path -> _lib/)
    import runtime_paths as _runtime_paths  # type: ignore[no-redef]


_SALT_FILENAME = ".salt"
_SALT_BYTES = 32
_SALT_MODE = 0o600
_DIR_MODE = 0o700


_MINT_MARKER_FILENAME = "salt-minted.json"


def _slug_dir() -> Path:
    """Return the per-PROJECT state directory (ADR-079 S318 amendment).

    Delegates to the single family resolver (``runtime_paths``,
    ADR-001 S318) so the salt sits next to the audit log it protects —
    per project, no longer per ``$HOME``. Still avoids importing
    ``audit_emit`` at module load to stay loadable from any hook
    (including hooks that emit no audit events).

    rail r13 P1-5 — FAMILY-ATOMICITY: quando os overrides movem a
    familia (`CEO_AUDIT_LOG_PATH` / `CEO_AUDIT_LOG_DIR`), o `.salt`
    acompanha. Deixa-lo em `runtime_state_dir()` enquanto log, key, lock
    e errors se mudam contradiz o invariante do ADR-001 S318 item 3 (e a
    claim do CLAUDE.md §5), e faria custodia/backup do dir efetivo
    PERDEREM o salt. Mesma cascata de `audit_hmac._audit_dir_from_env`.
    """
    env_path = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env_path:
        try:
            return Path(env_path).resolve().parent
        except OSError:
            pass
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    return _runtime_paths.runtime_state_dir()


def _salt_path() -> Path:
    return _slug_dir() / _SALT_FILENAME


# PLAN-182 W1 rail r2 B2: keyed pelo _salt_path() resolvido — a troca de
# projeto mid-process re-resolve; o salt do A nunca vaza para o B (a
# garantia por-projeto do ADR-079 S318 vale SEM reset manual de teste).
_CACHED_SALT = None  # type: Optional[tuple]  # (path_str, salt_bytes)


def _read_existing(path: Path) -> Optional[bytes]:
    """Read salt file if present and well-formed.

    Returns the bytes if size matches ``_SALT_BYTES``; ``None`` if
    the file is absent, the wrong size, or unreadable. Callers
    treat ``None`` as "regenerate".
    """
    try:
        if not path.exists():
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) != _SALT_BYTES:
        return None
    return data


def _generate_and_persist(
    path: Path, replace_existing: bool = False
) -> Tuple[bytes, str]:
    """Generate a new 32-byte salt and write it to ``path``.

    Returns ``(salt, outcome)`` where outcome is one of:

    * ``"created"`` — this process won the race and the returned bytes
      are the ones now on disk;
    * ``"exists"`` — another process created the file first; NOTHING was
      written and the caller must read the winner's bytes;
    * ``"error"`` — an I/O failure; the salt is ``b""`` (fail-open, the
      caller degrades to the unsalted hash).

    rc.1 re-pass part 6 C2 — the outcome is the whole point of the
    signature. Pre-cure this returned bare bytes written with
    ``path.write_bytes``, which TRUNCATES: two processes minting at once
    both "succeeded", each cached its own value, and one of the two was
    orphaned from the file. A caller that cannot tell "I created it"
    from "someone else did" also cannot tell whether it may register a
    mint, and the loser used to write a ``salt-minted.json`` marker for
    a mint it never performed.

    ``replace_existing`` selects ``O_TRUNC`` over ``O_EXCL`` for the one
    case that must overwrite: a pre-existing MALFORMED salt, which
    ``_read_existing`` rejected and ``get_instance_salt`` records as a
    rotation rather than a first mint. ``O_NOFOLLOW`` holds in both
    arms. Sets file mode ``0o600`` and parent dir mode ``0o700``.
    """
    try:
        # rail r2 F + r5: cria e aperta SO no caminho default — um dir
        # inteiro escolhido via CLAUDE_PROJECT_DIR_NATIVE preserva o modo
        # que o operador definiu.
        # rail r14: TODO override capaz de escolher `_slug_dir()` desliga
        # o tighten — inclusive os de familia que a cura P1-5 passou a
        # honrar. Apertar um dir 0750 escolhido pelo operador revogaria
        # acesso de auditor, contra a promessa assinada do sentinel.
        _overridden = any(os.environ.get(_k) for _k in (
            "CLAUDE_PROJECT_DIR_NATIVE",
            "CEO_AUDIT_LOG_PATH",
            "CEO_AUDIT_LOG_DIR",
        ))
        _runtime_paths.ensure_state_dir(path.parent, tighten=not _overridden)
    except Exception:
        return b"", "error"
    salt = os.urandom(_SALT_BYTES)
    # O_EXCL is the election; O_NOFOLLOW refuses a symlink squatting on
    # the salt path (same discipline as the marker below, and as the
    # audit writer PLAN-024 already ratified). O_TRUNC only on the
    # deliberate replace-a-malformed-salt arm.
    _flags = os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    _flags |= os.O_TRUNC if replace_existing else os.O_EXCL
    try:
        _fd = os.open(str(path), _flags, _SALT_MODE)
    except FileExistsError:
        # Lost the race. Writing nothing is the entire cure: the winner's
        # bytes stay on disk and the caller re-reads them.
        return b"", "exists"
    except OSError:
        return b"", "error"
    try:
        with os.fdopen(_fd, "wb") as _fh:
            _fh.write(salt)
    except OSError:
        return b"", "error"
    try:
        os.chmod(path, _SALT_MODE)
    except OSError:
        # Permission failure on chmod is non-fatal — the salt is
        # written but with default umask perms. Caller still gets
        # the salt; future readers may face stricter access but the
        # current process succeeds.
        pass
    return salt, "created"


def get_instance_salt() -> bytes:
    """Return the per-installation salt; generate + persist on first call.

    Caches the salt in module memory after first successful read or
    generation. Subsequent calls return the cached bytes without
    touching the filesystem.

    Returns ``b""`` on persistent I/O failure; callers must compose
    the result with their input ``hashlib.sha256(salt + payload)``
    such that an empty salt degrades to the unsalted hash.
    """
    global _CACHED_SALT
    path = _salt_path()
    # rail r6: identidade ABSOLUTA (override relativo + chdir nao pode
    # servir o salt do projeto anterior).
    path_id = os.path.abspath(str(path))
    cached = _CACHED_SALT
    if cached is not None and cached[0] == path_id:
        return cached[1]

    existing = _read_existing(path)
    if existing is not None:
        _CACHED_SALT = (path_id, existing)
        return existing

    # rail r15 P2-4: distinguir CRIACAO de RECUPERACAO. Um `.salt`
    # existente porem malformado (tamanho errado) faz `_read_existing`
    # devolver None e cair aqui — registrar isso como `first_mint`
    # esconderia uma ROTACAO real (que invalida a correlacao de
    # prompt_sha256) e sobrescreveria o marcador anterior.
    #
    # rc.1 re-pass part 6 C2 — that distinction used to be drawn by a
    # `path.exists()` probe right here, and the probe cannot draw it: it
    # cannot tell "was already there, malformed" from "appeared one
    # microsecond ago because another process just won the mint". A loser
    # that read the file as absent and then found it present concluded
    # ROTATION and truncated the winner — which is the very defect this
    # cure exists to close, re-introduced by the classifier. The first
    # cut of this cure did exactly that, and its own concurrency test
    # caught it.
    #
    # So the classification moves AFTER the exclusive create, which is the
    # only race-free moment available: O_EXCL succeeding IS "first mint",
    # and O_EXCL failing hands us a file we can then read and judge.
    _rotation = False
    salt, _outcome = _generate_and_persist(path)
    if _outcome == "exists":
        _winner = _read_existing(path)
        if _winner is not None:
            # We lost the race. The winner's bytes are on disk, so they are
            # what every future reader reproduces `prompt_sha256` from — we
            # adopt them and register NO mint, because we minted nothing and
            # a marker here would be forensic ground truth for an event that
            # never happened.
            _CACHED_SALT = (path_id, _winner)
            return _winner
        # Present but malformed: the rotation case (rail r15 P2-4). Replace
        # it ONCE — never a retry loop, since a second EEXIST would mean a
        # third writer we would simply lose to again. A well-formed salt
        # landing between the read above and this replace would be
        # overwritten; that window is a few instructions wide and only
        # opens when the file was already corrupt, which is strictly
        # narrower than the pre-cure behaviour of always truncating.
        _rotation = True
        salt, _outcome = _generate_and_persist(path, replace_existing=True)
    if _outcome == "created" and salt:
        _CACHED_SALT = (path_id, salt)
        _register_mint(path, reason="other" if _rotation else "first_mint")
    return salt


def _register_mint(salt_path: Path, reason: str = "first_mint") -> None:
    """Make the mint OBSERVABLE (ADR-079 S318 amendment §2). Fail-open.

    (a) Marker sidecar next to the salt — forensic ground truth that
        survives even when no emitter ever runs in this project.
    (b) Best-effort lazy chain event ``salt_rotation_registered``
        (kwargs top-level; the SLUG travels only as a 16-hex sha256
        prefix, and the salt path text is never sent).

    rc.1 re-pass part 6 C5 — this used to say "the path text never
    reaches the wire" without qualification, which reads as a claim
    about the whole event and is false: ``project`` is a REQUIRED base
    field of every registered line (SPEC/v1/audit-log.schema.md) and
    carries the repository path here exactly as it does on every other
    event, in this version and in v1.3.0. What this arm keeps off the
    wire is the SLUG text and the salt's own path, not the repository
    identifier the schema requires.

    Neither arm may raise: salt availability is invariant (ADR-005).
    """
    slug = ""
    try:
        slug = _runtime_paths.project_slug()
    except Exception:
        pass
    slug_sha16 = (
        hashlib.sha256(slug.encode("utf-8")).hexdigest()[:16] if slug else ""
    )
    try:
        marker = {
            "minted_at_epoch": int(time.time()),
            "reason": reason,
            "salt_scope": "project",
            "slug_sha256": slug_sha16,
            "pid": os.getpid(),
        }
        marker_path = salt_path.parent / _MINT_MARKER_FILENAME
        # rc.1 re-pass part 6 C3 — `write_text` FOLLOWS a symlink and
        # truncates its target, and the `chmod` that used to follow it
        # dropped that target to 0600. The re-pass reproduced both against
        # a file outside the state tree. Planting the link needs write
        # access to a 0700 directory, so this is same-UID hardening rather
        # than a modelled threat (docs/threat-model.md) — but the write
        # side of this library already refuses to follow links (PLAN-024),
        # and one writer in the family behaving differently is the
        # inconsistency, not the risk calculation.
        if os.path.islink(str(marker_path)):
            # Named refusal, fail-open like the rest of this arm: the salt
            # is minted and usable; only the forensic sidecar is skipped.
            _breadcrumb_target = str(marker_path)
            raise OSError(
                "mint marker path is a symlink, refusing to follow: %s"
                % _breadcrumb_target
            )
        _tmp_path = marker_path.parent / (
            "." + _MINT_MARKER_FILENAME + "." + os.urandom(6).hex() + ".tmp"
        )
        _mfd = os.open(
            str(_tmp_path),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            _SALT_MODE,
        )
        try:
            with os.fdopen(_mfd, "w", encoding="utf-8") as _mfh:
                _mfh.write(json.dumps(marker, sort_keys=True) + "\n")
            try:
                os.chmod(str(_tmp_path), _SALT_MODE)
            except OSError:
                pass
            # `os.replace` renames ONTO the destination: it does not follow
            # a symlink there, it replaces it. The islink check above is
            # what makes the refusal explicit rather than incidental.
            os.replace(str(_tmp_path), str(marker_path))
        except Exception:
            try:
                os.unlink(str(_tmp_path))
            except OSError:
                pass
            raise
    except Exception:
        pass
    try:
        # Lazy, one-shot, mint-time only: no module-load coupling on the
        # emit stack for the 99.999% of calls that never mint.
        try:  # package member first, bare fallback (mirrors header import)
            from . import audit_emit as _audit_emit  # type: ignore
        except ImportError:
            import audit_emit as _audit_emit  # type: ignore
        # rail r13 P1-4: `session_id` e `project` sao campos REQUERIDOS
        # da linha registrada no SPEC v2.58 e `_write_event` nao os
        # sintetiza — sem eles o evento de migracao nasce sem atribuicao.
        _sid = os.environ.get("CLAUDE_SESSION_ID") or ""
        try:
            _proj = str(_runtime_paths.project_dir())
        except Exception:
            _proj = ""
        _audit_emit.emit_generic(
            "salt_rotation_registered",
            session_id=_sid,
            project=_proj,
            reason=reason,
            salt_scope="project",
            slug_sha256=slug_sha16 or "invalid",
        )
    except Exception:
        pass


def reset_cache_for_test() -> None:
    """Test-only: clear the module-level salt cache.

    Production code MUST NOT call this. The cache invariant —
    salt is loaded at most once per process — is part of the
    fail-open guarantee (filesystem failures after the first
    successful load do not affect subsequent calls).
    """
    global _CACHED_SALT
    _CACHED_SALT = None
