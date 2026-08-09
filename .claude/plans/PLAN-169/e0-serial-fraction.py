#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E0 — gate-zero do pre-registro W5 (PLAN-169): fracao serial S.

Decompoe o wall-clock dos planos da amostra PINADA (M=155..168) em
tempo-maquina / tempo-humano / tempo-morto a partir do audit log HMAC
(+ arquivos rotacionados) e das janelas de commit do git, e aplica a
REGRA PRE-REGISTRADA:

    S = (humano + morto_nao_paralelizavel + maquina_serial_critica) / total
    S >= 0.40  => E1/E2 NAO financiados
    S <= 0.20  => E1/E2 liberados
    0.20 < S < 0.40 => E1 piloto (N/2), E2 nao financiado

Corte conservador pre-registrado: onde o grafo de dependencia da
maquina e irrecuperavel do log, a maquina conta 100% serial NAQUELE
plano (reportado por plano). Este runner nao tem como reconstruir o
grafo de dependencia dos passos a partir do log v2 (eventos nao
carregam arestas), entao TODA maquina conta serial — vies para CIMA
de S, ou seja, contra financiar E1/E2 (direcao segura).

Janela por plano: [primeiro, ultimo] commit cujo subject menciona
PLAN-<N> (git log). Dentro da janela:
  - maquina  = uniao de intervalos [ts_i, ts_i + GAP_MACHINE] dos
               eventos de audit (atividade instrumentada);
  - humano   = gaps entre eventos em (GAP_MACHINE, GAP_HUMAN_MAX];
  - morto    = gaps > GAP_HUMAN_MAX (CI/quota/sono — nao atribuivel
               a trabalho humano ativo; nao paralelizavel do ponto de
               vista do plano, entra no numerador por regra).
Thresholds sao INPUTS IMPRESSOS (feedback: medicao lista seus inputs).

AC-6 (W5): NAO execute sobre a amostra antes do pre-registro assinado
e commitado. O runner recusa rodar sem --i-confirm-w5-signed, que
verifica a existencia de W5-preregistration.md + .asc RASTREADOS.

Uso:
  python3 e0-serial-fraction.py --selftest          # sintetico, sempre ok
  python3 e0-serial-fraction.py --i-confirm-w5-signed   # a medicao real
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

PLANS = list(range(155, 169))          # M = 155..168, amostra PINADA
GAP_MACHINE_S = 120                    # atividade instrumentada cobre ate 2 min
GAP_HUMAN_MAX_S = 3600                 # gap > 1h = tempo morto (CI/quota/sono)


def _iso_to_epoch(ts):
    # "2026-08-08T01:03:46Z" — stdlib only, py>=3.9
    import datetime as dt
    try:
        return dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.timezone.utc).timestamp()
    except ValueError:
        return None


def verify_hmac_or_die(repo, paths):
    """Integridade da evidencia, com o que o substrato REALMENTE oferece.

    GATE fail-closed = check-audit-hmac-null.py (regressao S234:
    hmac=null / hmac_error em acao conhecida). DISCLOSURE obrigatoria =
    verify_chain() por arquivo, impressa no relatorio.

    Por que verify_chain NAO e gate (pair-rail S300 r2 P1-3, triado
    PARCIAL): (a) HMAC-483 — verify_chain cru da falso mismatch
    pos-rotacao; reproduzido na S300: 11/11 arquivos reais reportam
    'tamper', incluindo arquivos saudaveis com >13k entradas
    verificadas; (b) decisao S298 (PLAN-169): o trust model da cadeia
    HMAC como ORACULO foi descartado — escritor e verificador correm
    no MESMO UID, entao a cadeia e tamper-EVIDENT para auditoria
    externa, nao autorizacao. Fingir verificacao criptografica plena
    aqui seria um gate que nao pode falhar pelo motivo certo. O
    relatorio E0 imprime o estado por arquivo e a decisao de
    financiamento e tomada com essa ressalva EXPLICITA."""
    checker = os.path.join(repo, ".claude/scripts/check-audit-hmac-null.py")
    if not os.path.isfile(checker):
        print("FATAL: %s ausente — nao ha como verificar a evidencia." % checker)
        raise SystemExit(2)
    for p in paths:
        r = subprocess.run([sys.executable, checker, "--log", p],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("FATAL: verificador HMAC recusou %s (rc=%d):\n%s"
                  % (p, r.returncode, (r.stdout + r.stderr).strip()[:800]))
            raise SystemExit(2)
        print("- hmac-null-check OK: %s" % os.path.basename(p))
    # Disclosure verify_chain (nao-gate; ver docstring):
    try:
        sys.path.insert(0, os.path.join(repo, ".claude/hooks"))
        from _lib.audit_hmac import verify_chain  # type: ignore
        from pathlib import Path as _P
        print("- verify_chain por arquivo (DISCLOSURE, nao-gate — "
              "HMAC-483 + trust-model S298):")
        for p in paths:
            res = verify_chain(_P(p))
            print("    %s: status=%s verified=%s" % (
                os.path.basename(p), res.status,
                getattr(res, "verified_count", "?")))
    except Exception as exc:  # disclosure nunca derruba o gate-null
        print("- verify_chain indisponivel para disclosure: %s" % exc)


def load_events(audit_dir):
    """Todos os eventos (log vivo + arquivos rotacionados), ordenados.

    Fail-CLOSED em input malformado (P2-1): linha nao-JSON ou evento sem
    timestamp parseavel NAO e pulado silenciosamente — conta como defeito
    de evidencia e aborta (um log truncado/adulterado nao pode alimentar
    uma decisao de financiamento)."""
    paths = sorted(glob.glob(os.path.join(audit_dir, "audit-log*.jsonl")))
    events = []
    per_file = {}
    bad = 0
    for p in paths:
        n = 0
        with open(p, encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    print("EVIDENCIA MALFORMADA: %s:%d nao e JSON" % (p, lineno))
                    bad += 1
                    continue
                ts = _iso_to_epoch(str(ev.get("ts") or ev.get("rotation_ts") or ""))
                if ts is None:
                    print("EVIDENCIA MALFORMADA: %s:%d sem ts parseavel" % (p, lineno))
                    bad += 1
                    continue
                events.append((ts, ev.get("action", "?")))
                n += 1
        per_file[p] = n
    if bad:
        print("FATAL: %d linha(s) malformadas no log — evidencia recusada "
              "(fail-closed on input)." % bad)
        raise SystemExit(2)
    events.sort(key=lambda e: e[0])
    return events, per_file, paths


def plan_windows(repo):
    """[inicio, fim] por plano = commits cujo subject menciona PLAN-<N>."""
    out = subprocess.run(
        ["git", "-C", repo, "log", "--format=%ct %s", "--since=2026-06-01"],
        capture_output=True, text=True, check=True).stdout
    win = {}
    for line in out.splitlines():
        try:
            ct_s, subject = line.split(" ", 1)
            ct = int(ct_s)
        except ValueError:
            continue
        for n in PLANS:
            if ("PLAN-%d" % n) in subject:
                lo, hi = win.get(n, (ct, ct))
                win[n] = (min(lo, ct), max(hi, ct))
    return win


def decompose(events, lo, hi):
    """(maquina, humano, morto, n_eventos) dentro da janela [lo, hi].

    P2-2 do pair-rail S300: as fronteiras da janela ENTRAM na
    decomposicao — [lo, primeiro_evento] e [ultimo_evento, hi] sao gaps
    classificados pelos mesmos thresholds. Sem isso, 2 eventos vizinhos
    no meio de uma janela de 24h reduziriam o total medido ao gap curto
    entre eles, enviesando o floor_S para baixo."""
    ts = [t for t, _a in events if lo <= t <= hi]
    if len(ts) < 1:
        return 0.0, 0.0, float(hi - lo), len(ts)
    n_events = len(ts)
    ts = [float(lo)] + ts + [float(hi)]
    machine = human = dead = 0.0
    for a, b in zip(ts, ts[1:]):
        gap = b - a
        if gap <= GAP_MACHINE_S:
            machine += gap
        elif gap <= GAP_HUMAN_MAX_S:
            machine += GAP_MACHINE_S
            human += gap - GAP_MACHINE_S
        else:
            machine += GAP_MACHINE_S
            dead += gap - GAP_MACHINE_S
    return machine, human, dead, n_events


def apply_rule(S):
    if S >= 0.40:
        return "S >= 0.40 => E1/E2 NAO financiados"
    if S <= 0.20:
        return "S <= 0.20 => E1/E2 liberados"
    return "0.20 < S < 0.40 => E1 piloto (N/2), E2 NAO financiado"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(audit_dir, repo):
    orig_dir = audit_dir
    log_paths = sorted(glob.glob(os.path.join(orig_dir, "audit-log*.jsonl")))
    if not log_paths:
        print("FATAL: nenhum audit-log*.jsonl em %s" % orig_dir)
        return 2
    # SNAPSHOT imutavel (r12 P2-1 — TOCTOU) e ROTATION-SAFE (r15):
    # o log vivo pode receber appends/rotacao DURANTE a copia — uma
    # rotacao no meio deixaria o arquivo novo quase vazio no snapshot e
    # o archive recem-criado FORA dele. Estrategia: copiar e re-enumerar;
    # se o CONJUNTO de nomes mudou durante a copia, tentar de novo
    # (3x; falha = FATAL). Snapshot removido no finally (r15: ~105MB
    # por run nao podem acumular); a autenticacao posterior usa os
    # digests COMPLETOS impressos no relatorio contra os originais
    # (append-only + archives imutaveis).
    import shutil
    import tempfile
    snap_dir = tempfile.mkdtemp(prefix="e0-snap.")
    ok_snapshot = False
    for _attempt in range(3):
        names_before = sorted(
            os.path.basename(p)
            for p in glob.glob(os.path.join(orig_dir, "audit-log*.jsonl")))
        for n in os.listdir(snap_dir):
            os.unlink(os.path.join(snap_dir, n))
        for n in names_before:
            shutil.copy2(os.path.join(orig_dir, n), os.path.join(snap_dir, n))
        names_after = sorted(
            os.path.basename(p)
            for p in glob.glob(os.path.join(orig_dir, "audit-log*.jsonl")))
        if names_before == names_after:
            ok_snapshot = True
            break
        print("- rotacao detectada durante a copia (tentativa %d) — refazendo"
              % (_attempt + 1))
    if not ok_snapshot:
        print("FATAL: inventario de logs instavel em 3 tentativas — "
              "rode E0 num momento quieto.")
        return 2
    print("- snapshot imutavel: %s (%d arquivo(s) copiados de %s)"
          % (snap_dir, len(names_before), orig_dir))
    try:
        return _measure(snap_dir, repo)
    finally:
        shutil.rmtree(snap_dir, ignore_errors=True)
        print("- snapshot removido (digests completos acima autenticam os originais)")


def _measure(audit_dir, repo):
    log_paths = sorted(glob.glob(os.path.join(audit_dir, "audit-log*.jsonl")))
    verify_hmac_or_die(repo, log_paths)
    events, per_file, _paths = load_events(audit_dir)
    windows = plan_windows(repo)
    print("## E0 — fracao serial (amostra pinada M=155..168)")
    print("### INPUTS (a medicao lista seus inputs)")
    print("- audit_dir: %s" % audit_dir)
    for p, n in sorted(per_file.items()):
        print("  - %s: %d eventos" % (os.path.basename(p), n))
        print("    sha256 %s" % sha256_file(p))
    print("- GAP_MACHINE_S=%d GAP_HUMAN_MAX_S=%d" % (GAP_MACHINE_S, GAP_HUMAN_MAX_S))
    print("- janelas por plano: git log --format='%ct %s' (subject com PLAN-N)")
    print("- corte conservador: maquina 100%% serial em TODOS os planos")
    print("  (grafo de dependencia irrecuperavel do log v2) — vies p/ CIMA de S")
    print()
    print("| plano | janela h | maquina h | humano h | morto h | eventos | S_plano |")
    print("|---|---|---|---|---|---|---|")
    covered = 0
    missing = [n for n in PLANS if n not in windows]
    if missing:
        print("\nFATAL: amostra PINADA incompleta — sem janela de commits para: %s"
              % ", ".join("PLAN-%d" % n for n in missing))
        print("O pre-registro fixa os 14 planos; medir um subconjunto seria")
        print("desvio nao-assinado (r15 P2-2). Verifique profundidade do git")
        print("log / subjects antes de re-rodar.")
        return 2
    for n in PLANS:
        if n not in windows:
            continue
        lo, hi = windows[n]
        m, h, d, k = decompose(events, lo, hi)
        total = m + h + d
        s_p = (h + d + m) / total if total > 0 else 1.0
        covered += 1
        print("| PLAN-%d | %.1f | %.1f | %.1f | %.1f | %d | %.2f |" % (
            n, (hi - lo) / 3600.0, m / 3600, h / 3600, d / 3600, k, s_p))
    print()
    print("(linhas por plano sao DESCRITIVAS; janelas podem se sobrepor —")
    print(" o agregado abaixo usa a UNIAO das janelas, sem dupla contagem:")
    print(" pair-rail S300 r3 P1-4)")
    # Agregado sobre a UNIAO de intervalos (merge de janelas sobrepostas)
    ivs = sorted(windows[n] for n in PLANS if n in windows)
    merged = []
    for lo, hi in ivs:
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    tot_m = tot_h = tot_d = 0.0
    for lo, hi in merged:
        m, h, d, _k = decompose(events, lo, hi)
        tot_m += m; tot_h += h; tot_d += d
    grand = tot_m + tot_h + tot_d
    if grand <= 0:
        print("\nFATAL: nenhum tempo decomposto — janelas nao cobrem o log.")
        return 2
    S = (tot_h + tot_d + tot_m) / grand
    print("\n### Agregado (%d/%d planos; uniao de %d intervalo(s) disjunto(s))"
          % (covered, len(PLANS), len(merged)))
    print("- maquina=%.1fh humano=%.1fh morto=%.1fh total=%.1fh" % (
        tot_m / 3600, tot_h / 3600, tot_d / 3600, grand / 3600))
    print("- **S (conservador, maquina 100%% serial) = %.3f**" % S)
    print("- **REGRA PRE-REGISTRADA (a UNICA que decide): %s**" % apply_rule(S))
    print()
    print("Estatistica DESCRITIVA (nao decide nada — o pre-registro nao")
    print("define regra sobre ela; registrada apenas para leitura humana):")
    print("- fracao nao-maquina do wall-clock = %.3f" % ((tot_h + tot_d) / grand))
    print("- (pair-rail S300 r3 P1-5: uma regra de decisao sobre este piso")
    print("  seria pos-hoc e nao-assinada — removida; emenda so via novo")
    print("  pre-registro versionado.)")
    return 0


def selftest():
    ev = []
    t = 1000.0
    for _ in range(50):
        ev.append((t, "x")); t += 30           # maquina densa
    t += 1800; ev.append((t, "x"))             # gap humano (1830s do ultimo)
    t += 7200; ev.append((t, "x"))             # gap morto 2h
    m, h, d, k = decompose(ev, 900, t + 10)
    assert k == 52, k
    # fronteiras contam (P2-2): [900,1000]=100 e [ultimo, hi]=10, ambos
    # <= GAP_MACHINE => maquina
    assert abs(m - (49 * 30 + 2 * GAP_MACHINE_S + 100 + 10)) < 1, m
    assert abs(h - (1830 - GAP_MACHINE_S)) < 1, h
    assert abs(d - (7200 - GAP_MACHINE_S)) < 1, d
    # janela com 1 evento: fronteiras decompostas, nao "tudo morto"
    m1, h1, d1, k1 = decompose([(5000.0, "x")], 4000, 12000)
    assert k1 == 1, k1
    assert abs((m1 + h1 + d1) - 8000) < 1, (m1, h1, d1)
    assert abs(h1 - (1000 - GAP_MACHINE_S)) < 1, h1
    assert abs(d1 - (7000 - GAP_MACHINE_S)) < 1, d1
    assert apply_rule(0.5).startswith("S >= 0.40")
    assert apply_rule(0.1).startswith("S <= 0.20")
    assert apply_rule(0.3).startswith("0.20 <")
    print("selftest OK (decomposicao + regra)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--i-confirm-w5-signed", action="store_true",
                    help="afirma que W5-preregistration.md+.asc estao "
                         "ASSINADOS e COMMITADOS (AC-6)")
    ap.add_argument("--audit-dir", default=os.path.expanduser(
        "~/.claude/projects/ceo-orchestration"))
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.i_confirm_w5_signed:
        print("RECUSADO: E0 so roda APOS o pre-registro W5 assinado+commitado"
              " (AC-6). Use --i-confirm-w5-signed depois da assinatura.")
        return 3
    pre = os.path.join(args.repo, ".claude/plans/PLAN-169/W5-preregistration.md")
    asc = pre + ".asc"
    for p in (pre, asc):
        if not os.path.isfile(p):
            print("RECUSADO: %s ausente — assine o W5 primeiro (AC-6)." % p)
            return 3
    tracked = subprocess.run(
        ["git", "-C", args.repo, "ls-files", "--error-unmatch",
         ".claude/plans/PLAN-169/W5-preregistration.md",
         ".claude/plans/PLAN-169/W5-preregistration.md.asc"],
        capture_output=True, text=True)
    if tracked.returncode != 0:
        print("RECUSADO: W5 md+asc existem mas NAO estao commitados (AC-6).")
        return 3
    # P2-3 do pair-rail S300: ls-files prova so o NOME no indice. AC-6
    # exige os BYTES assinados: (a) working tree == HEAD nos dois paths
    # (nem staged nem unstaged); (b) a assinatura destacada VERIFICA.
    clean = subprocess.run(
        ["git", "-C", args.repo, "diff", "HEAD", "--quiet", "--",
         ".claude/plans/PLAN-169/W5-preregistration.md",
         ".claude/plans/PLAN-169/W5-preregistration.md.asc"],
        capture_output=True, text=True)
    if clean.returncode != 0:
        print("RECUSADO: W5 md/asc divergem do HEAD commitado — o conteudo "
              "assinado nao e o que esta no repo (AC-6).")
        return 3
    # Pair-rail S300 r2 P1-4: gpg --verify aceita QUALQUER chave do
    # keyring. O gate exige o signatario PINADO (Owner) — parse do
    # --status-fd por VALIDSIG e match do fingerprint no keyid longo.
    OWNER_KEYID = "CFCFACF00335DC74"
    sig = subprocess.run(["gpg", "--status-fd", "1", "--verify", asc, pre],
                         capture_output=True, text=True)
    if sig.returncode != 0:
        print("RECUSADO: gpg --verify falhou para o W5 (AC-6):\n%s"
              % sig.stderr.strip()[:400])
        return 3
    validsig = [ln for ln in sig.stdout.splitlines()
                if ln.startswith("[GNUPG:] VALIDSIG ")]
    fprs = []
    for ln in validsig:
        parts = ln.split()
        fprs.append(parts[2])          # fingerprint da assinatura
        fprs.append(parts[-1])         # fingerprint da chave primaria
    if not any(f.endswith(OWNER_KEYID) for f in fprs):
        print("RECUSADO: assinatura do W5 nao e da chave do Owner "
              "(%s); VALIDSIG=%s" % (OWNER_KEYID, fprs or "ausente"))
        return 3
    return run(args.audit_dir, args.repo)


if __name__ == "__main__":
    sys.exit(main())
