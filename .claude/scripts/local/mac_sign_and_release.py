#!/usr/bin/env python3
"""Run the Mac signing and release steps using the repository release driver."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TRACK = "tracks/m16-ceo-orchestration-reforma-v144"
RELEASE = ".claude/scripts/local/release.sh"
REPO_ROOT = Path(__file__).resolve().parents[3]
CI_TIMEOUT_SECONDS = 3 * 60 * 60


def run(args, capture=False, timeout=None):
    print("+ " + " ".join(args), flush=True)
    options = {"timeout": timeout} if timeout is not None else {}
    return subprocess.run(args, check=True, text=True, cwd=REPO_ROOT,
                          stdout=subprocess.PIPE if capture else None, **options)


def require_tools(*names):
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise RuntimeError("Ferramentas ausentes: " + ", ".join(missing))


def clean_tree():
    if run(["git", "status", "--porcelain"], capture=True).stdout:
        raise RuntimeError("Árvore de trabalho suja; resolva antes de trocar de branch.")


def signing_probe():
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "probe"
        source.write_text("signing probe\n", encoding="utf-8")
        try:
            run(["gpg", "--yes", "--armor", "--detach-sign", str(source)])
        except subprocess.CalledProcessError as exc:
            try:
                run(["gpgconf", "--kill", "gpg-agent"])
            except (OSError, subprocess.CalledProcessError):
                pass
            raise RuntimeError("Assinatura falhou; tente export GPG_TTY=$(tty) e execute novamente.") from exc


def watch_main(sha):
    """Wait for runs on this exact main commit, then require a green verdict."""
    deadline = time.monotonic() + CI_TIMEOUT_SECONDS
    while True:
        if time.monotonic() >= deadline:
            raise RuntimeError("Tempo esgotado aguardando CI do commit " + sha)
        result = run(["gh", "run", "list", "--branch", "main", "--commit", sha,
                      "--event", "push", "--limit", "100", "--json",
                      "databaseId,headSha,status,conclusion,workflowName,event"],
                     capture=True, timeout=max(0.001, deadline - time.monotonic()))
        runs = json.loads(result.stdout)
        if not isinstance(runs, list):
            raise RuntimeError("Resposta de CI inválida.")
        if any(not isinstance(item, dict) or item.get("headSha") != sha or
               item.get("event") != "push" for item in runs):
            raise RuntimeError("Resposta de CI não corresponde ao commit solicitado.")
        if any(item.get("status") == "completed" and
               item.get("conclusion") not in ("success", "skipped") for item in runs):
            raise RuntimeError("CI não está verde para o commit " + sha)
        pending = [item for item in runs if item.get("status") != "completed"]
        for item in pending:
            run_id = item.get("databaseId")
            if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
                raise RuntimeError("Execução de CI sem identificador válido.")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("Tempo esgotado aguardando CI do commit " + sha)
            run(["gh", "run", "watch", str(run_id), "--exit-status"], timeout=remaining)
        if pending:
            continue
        if not pending and any("Validate" in (item.get("workflowName") or "") and
                               item.get("conclusion") == "success" for item in runs):
            return
        time.sleep(min(5, max(0, deadline - time.monotonic())))


def current_head():
    sha = run(["git", "rev-parse", "HEAD"], capture=True).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40,64}", sha):
        raise RuntimeError("SHA do commit inválido.")
    return sha


def verify_main_head(sha):
    clean_tree()
    branch = run(["git", "branch", "--show-current"], capture=True).stdout.strip()
    if branch != "main" or current_head() != sha:
        raise RuntimeError("Branch ou HEAD mudou; operação cancelada.")


def sign_merge(watch=False):
    require_tools("git", "gpg", "gh")
    clean_tree()
    signing_probe()
    run(["git", "fetch", "origin", "main", TRACK])
    run(["git", "checkout", "main"])
    run(["git", "pull", "--ff-only", "origin", "main"])
    previous = current_head()
    run(["git", "merge", "--no-ff", "-S", "origin/" + TRACK, "-m",
         "Merge pull request #7 from Canhada-Labs/" + TRACK])
    run(["git", "verify-commit", "HEAD"])
    sha = current_head()
    if sha == previous:
        raise RuntimeError("O merge não criou um novo commit; envio cancelado.")
    verify_main_head(sha)
    run(["git", "push", "origin", "main"])
    if watch:
        watch_main(sha)
    return sha


def cut_release(stable=False, push=False):
    flags = ["--stable"] if stable else []
    print("Pré-requisito: revise npm/README.md antes do corte; o bump registra essa revisão.", flush=True)
    run(["bash", RELEASE, "preflight"] + flags)
    before = current_head()
    run(["bash", RELEASE, "bump"] + flags + ["--npm-readme-reviewed"])
    after = current_head()
    if after != before:
        if not push:
            raise RuntimeError("O bump criou um commit. Envie main com git push origin main, "
                               "aguarde a CI e execute release.sh tag com as opções do corte.")
        verify_main_head(after)
        run(["git", "push", "origin", "main"])
        watch_main(after)
    verify_main_head(after)
    result = run(["bash", RELEASE, "tag"] + flags, capture=True)
    print(result.stdout, end="", flush=True)
    # The release driver is the source of the tag, including its RC ordinal.
    matches = re.findall(r"^TAG (v[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?) IS SIGNED LOCALLY AND NOT PUSHED\.$",
                         result.stdout, re.MULTILINE)
    if len(matches) != 1:
        raise RuntimeError("Não foi possível identificar a tag produzida pelo release.sh.")
    tag = matches[0]
    if stable == ("-rc." in tag):
        raise RuntimeError("A tag produzida não corresponde ao tipo de release.")
    if push:
        tagged = run(["git", "rev-parse", "--verify", "refs/tags/" + tag + "^{}"], capture=True).stdout.strip()
        head = current_head()
        if tagged != head:
            raise RuntimeError("A tag não aponta para o commit atual.")
        run(["git", "push", "origin", "refs/tags/" + tag])
        print("Tag enviada; acompanhe os workflows remotos para verificar a publicação.")
    return tag


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog="Antes do corte, revise npm/README.md; o bump registra essa revisão.")
    commands = parser.add_subparsers(dest="command", required=True)
    merge = commands.add_parser("sign-merge", help="assinar, verificar e enviar o merge")
    merge.add_argument("--watch", action="store_true", help="aguardar CI do commit da main")
    for name in ("cut-rc", "cut-ga"):
        command = commands.add_parser(name, help="executar as fases de release")
        command.add_argument("--push", action="store_true", help="enviar commit do bump se criado, aguardar CI e enviar a tag")
    combined = commands.add_parser("all-in-one", help="merge, CI verde e corte de release")
    combined.add_argument("--stable", action="store_true", help="cortar GA em vez de RC")
    combined.add_argument("--push", action="store_true", help="enviar commit do bump se criado, aguardar CI e enviar a tag")
    args = parser.parse_args(argv)
    try:
        if args.command == "sign-merge":
            sign_merge(args.watch)
        elif args.command == "all-in-one":
            sign_merge(watch=True)
            cut_release(stable=args.stable, push=args.push)
        else:
            cut_release(stable=args.command == "cut-ga", push=args.push)
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError) as exc:
        print("Falha: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
