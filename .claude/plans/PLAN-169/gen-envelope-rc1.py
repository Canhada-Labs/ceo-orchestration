#!/usr/bin/env python3
"""Gera verdict-fields + envelope pair-rail-verdict para a v1.4.0-rc.1 a
partir da evidencia CORRENTE em repass-rc1/. Fail-CLOSED em toda checagem
(nunca `assert`: PYTHONOPTIMIZE apagaria o gate). Uso:

  python3 gen-envelope-rc1.py --stage fields --parent <sha40> \\
      --conditions-file <md>          # OBRIGATORIO se algum rail = GWC
  # -> Owner: gpg --detach-sign --armor verdict-fields-v1.4.0-rc.1.md
  python3 gen-envelope-rc1.py --stage envelope --sig <.asc>

Clone do PLAN-177/gen-envelope-rc4.py com TAG, diretorio de plano e numero
de rails novos, MAIS duas mudancas de desenho que o rc.4 nao podia ter:

  1. `codex_cli` NAO vem de `codex --version`. O binario GLOBAL desta
     maquina esta em 0.153.4, FORA da faixa `>=0.128.0,<0.148.0` do
     `codex-cli-pin.txt`, e o step 15 do release.yml compara o valor
     DECLARADO contra essa faixa — um envelope gerado do global seria
     rejeitado no gate. A versao vem da linha `- codex:` da PROVENANCE, que
     o runner escreve a partir do pin que ele proprio VERIFICOU, e este
     gerador re-valida contra a faixa antes de escrever.
  2. `SIGNER_FPR` nao e uma constante digitada. Ele e DERIVADO de duas
     fontes independentes — o fingerprint dentro da assinatura do envelope
     PRECEDENTE e o registro `.claude/sentinel-signers.txt` — e as duas
     TEM de concordar.

Demais derivacoes, todas dos artefatos REAIS e nunca digitadas: inputs_hash
pela funcao do proprio validador; MANIFEST-rc1 verificado; transcript_hash =
sha256 da concatenacao ordenada dos 6 transcripts; parent VINCULADO ao
candidato do runner/PROVENANCE; a DECISAO agregada e DERIVADA dos 6 rails;
as CONDICOES entram nos FIELDS (material assinado); assinatura VERIFICADA
antes de embutir; escrita atomica sem seguir symlink. stdlib only, >= 3.9.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Tuple

REPO = pathlib.Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip())
PLAN = ".claude/plans/PLAN-169"
EV = REPO / PLAN / "repass-rc1"
TAG = "v1.4.0-rc.1"
FIELDS = REPO / PLAN / ("verdict-fields-%s.md" % TAG)
ENVELOPE = REPO / ".claude/governance" / ("pair-rail-verdict-%s.md" % TAG)
GOV = REPO / ".claude/governance"
PRECEDENT = GOV / "pair-rail-verdict-v1.3.0.md"
SIGNERS = REPO / ".claude/sentinel-signers.txt"
NPARTS = 6
PARTS = list(range(1, NPARTS + 1))

ARTIFACTS = ["MANIFEST-rc1.sha256", "PROVENANCE-rc1.md", "CANDIDATE.sha"]
for _p in PARTS:
    ARTIFACTS += [
        "diff-rc1-%d.patch" % _p,
        "paths-rc1-%d.manifest.txt" % _p,
        "payload-rc1-%d.redacted.txt" % _p,
        "transcript-rc1-%d.log" % _p,
        "verdict-rc1-%d.txt" % _p,
    ]
ARTIFACTS.append("run-rc1-repass.sh")
ARTIFACTS = sorted(set(ARTIFACTS))
# Este gerador vive em PLAN-169/ (FORA de repass-rc1/) de proposito — nao e
# evidencia do re-pass, nao entra no MANIFEST nem na delta_allowlist.


def die(msg: str) -> None:
    sys.stderr.write("FATAL: %s\n" % msg)
    sys.exit(2)


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_atomic_regular(path: pathlib.Path, text: str) -> None:
    """Recusa symlink/nao-regular; temporario no MESMO dir + rename atomico."""
    if path.is_symlink():
        die("%s e symlink — recuso escrever atraves dele" % path)
    if path.exists() and not path.is_file():
        die("%s existe e nao e arquivo regular" % path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".gen-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "v", str(REPO / ".github/scripts/validate-pair-rail-verdict.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def signer_fpr() -> str:
    """DUAS fontes independentes, que TEM de concordar.

    (a) o fingerprint embutido na assinatura do envelope PRECEDENTE
        (subpacote 33 `issuer fpr v4`, lido por `gpg --list-packets` sobre a
        assinatura decodificada — nao exige o material assinado);
    (b) o registro rastreado `.claude/sentinel-signers.txt`.

    Uma constante digitada seria uma terceira fonte, envelhecendo sozinha.
    """
    if not PRECEDENT.is_file():
        die("envelope precedente ausente: %s" % PRECEDENT)
    m = re.search(r"^gpg_signature: base64:(\S+)$",
                  PRECEDENT.read_text(encoding="utf-8"), re.M)
    if not m:
        die("envelope precedente sem gpg_signature base64")
    try:
        raw = base64.b64decode(m.group(1), validate=True)
    except Exception as exc:
        die("gpg_signature do precedente nao decodifica: %s" % exc)
    fd, tmp = tempfile.mkstemp(suffix=".asc")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
        proc = subprocess.run(["gpg", "--list-packets", tmp],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              universal_newlines=True)
    finally:
        os.unlink(tmp)
    if proc.returncode != 0:
        die("gpg --list-packets recusou a assinatura do precedente")
    mm = re.search(r"issuer fpr v4 ([0-9A-F]{40})", proc.stdout)
    if not mm:
        die("assinatura do precedente sem subpacote de issuer fpr")
    from_env = mm.group(1)

    if not SIGNERS.is_file():
        die("registro de signatarios ausente: %s" % SIGNERS)
    reg = [ln.strip() for ln in SIGNERS.read_text(encoding="utf-8").splitlines()
           if ln.strip() and not ln.strip().startswith("#")]
    fprs = [ln.split()[0].upper() for ln in reg]
    if from_env not in fprs:
        die("fingerprint do envelope precedente (%s) nao esta em %s: %r"
            % (from_env, SIGNERS, fprs))

    # Seam de AUTO-TESTE, recusado fora do scratchpad declarado. Existe so
    # para `test-rc1-kit.sh` exercitar fields -> assinatura -> envelope com
    # uma chave DESCARTAVEL. Relaxa EXATAMENTE uma coisa — qual fingerprint e
    # aceita — e nunca a exigencia de VALIDSIG nem a derivacao acima, que
    # continua rodando e podendo abortar. O valor vem por ARGUMENTO explicito
    # (variavel dedicada), nunca de sentinela dentro do material.
    if os.environ.get("RC1_SELFTEST") == "1":
        scratch = os.environ.get("RC1_SELFTEST_SCRATCH", "/nonexistent")
        if not (os.path.realpath(str(REPO)) + os.sep).startswith(
                os.path.realpath(scratch) + os.sep):
            die("RC1_SELFTEST=1 fora do scratchpad declarado — recusado")
        sub = os.environ.get("RC1_SELFTEST_SIGNER_FPR", "")
        if not re.fullmatch(r"[0-9A-F]{40}", sub):
            die("auto-teste exige RC1_SELFTEST_SIGNER_FPR (40 hex maiusculos)")
        sys.stderr.write(
            "AVISO: auto-teste — fingerprint aceita trocada para %s\n" % sub)
        return sub
    return from_env


def provenance_text() -> str:
    p = EV / "PROVENANCE-rc1.md"
    if not p.is_file():
        die("PROVENANCE-rc1.md ausente — o runner nao rodou")
    return p.read_text(encoding="utf-8")


def pinned_codex(prov: str) -> Dict[str, str]:
    """A tripla do codex vem da PROVENANCE, e e re-validada contra os pins."""
    m = re.search(r"^- codex: (\S+) / (\S+) / payload (\S+)$", prov, re.M)
    if not m:
        die("PROVENANCE sem a linha '- codex: <ver> / <triple> / payload <sha>'")
    ver, triple, payload = m.group(1), m.group(2), m.group(3)
    if "stub" in (ver, triple, payload):
        die("PROVENANCE de um run com CODEX_BIN=stub — evidencia de harness, "
            "nunca de release")
    if not re.fullmatch(r"[0-9a-f]{64}", payload):
        die("payload da PROVENANCE nao e um sha256: %r" % payload)
    # (a) a versao declarada tem de estar na faixa do pin — a MESMA checagem
    # que o step 15 do release.yml faz sobre o envelope.
    val = load_validator()
    min_v, max_v = val.parse_pin_range(GOV / "codex-cli-pin.txt")
    if not (min_v and max_v):
        die("codex-cli-pin.txt sem faixa parseavel — recuso gerar sem o gate")
    if not val.semver_in_range(ver, min_v, max_v):
        die("codex_cli %s fora da faixa do pin (%s .. %s) — o step 15 "
            "rejeitaria o envelope" % (ver, min_v, max_v))
    # (b) o payload declarado tem de ser o do manifesto ADR-182, para o triple.
    man = json.loads((GOV / "codex-cli-pin-manifest.json").read_text(encoding="utf-8"))
    entry = (man.get("payloads") or {}).get(triple)
    if not entry:
        die("pin-manifest sem entrada para o triple %r" % triple)
    if entry.get("sha256") != payload:
        die("payload declarado (%s) != manifesto (%s)" % (payload, entry.get("sha256")))
    if man.get("package_version") != ver:
        die("package_version do manifesto (%r) != versao declarada (%r)"
            % (man.get("package_version"), ver))
    return {"codex_cli": ver, "target_triple": triple, "sha256": payload}


def rail_decisions() -> List[str]:
    out = []
    for n in PARTS:
        v = (EV / ("verdict-rc1-%d.txt" % n)).read_text(encoding="utf-8")
        lines = [ln for ln in v.splitlines() if ln.startswith("VERDICT:")]
        if not lines:
            die("parte %d: nenhuma linha VERDICT" % n)
        toks = set()
        for ln in lines:
            m = re.match(r"VERDICT:\s*(GO-WITH-CONDITIONS|GO|NO-GO)\b", ln)
            if not m:
                die("parte %d: VERDICT ilegivel: %r" % (n, ln))
            toks.add(m.group(1))
        if len(toks) != 1:
            die("parte %d: decisoes divergentes na mesma saida: %r" % (n, toks))
        out.append(toks.pop())
    return out


def runner_candidate(prov: str) -> str:
    """O candidato que o runner efetivamente revisou (3 fontes concordando)."""
    m = re.search(r"Candidato: ([0-9a-f]{40})", prov)
    if not m:
        die("PROVENANCE sem 'Candidato: <sha40>'")
    prov_sha = m.group(1)
    cand_file = (EV / "CANDIDATE.sha").read_text(encoding="utf-8").strip()
    if cand_file != prov_sha:
        die("CANDIDATE.sha (%s) != candidato da PROVENANCE (%s)"
            % (cand_file, prov_sha))
    run = (EV / "run-rc1-repass.sh").read_text(encoding="utf-8")
    if 'CAND_FILE="$OUT/CANDIDATE.sha"' not in run:
        die("o runner nao le o candidato de CANDIDATE.sha — runner trocado?")
    return prov_sha


def build_fields(parent: str, conditions_text: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", parent or ""):
        die("--parent deve ser sha40")
    for a in ARTIFACTS:
        if not (EV / a).is_file():
            die("artefato ausente: %s" % a)
    rc = subprocess.call(["shasum", "-a", "256", "-c", "MANIFEST-rc1.sha256",
                          "--status"], cwd=str(EV))
    if rc != 0:
        die("MANIFEST-rc1 nao verifica")
    prov = provenance_text()
    if "RUNNER-OVERALL: rc=" not in prov:
        die("PROVENANCE sem RUNNER-OVERALL")
    cand = runner_candidate(prov)
    if parent != cand:
        die("--parent %s != candidato revisado %s (a evidencia cobre OUTRA "
            "arvore; re-rode o re-pass ou corrija o parent)" % (parent, cand))

    decisions = rail_decisions()
    if "NO-GO" in decisions:
        # Rota de fechamento ratificada pelo Owner: um rail NO-GO so viaja sob
        # um texto de CONDICOES que o nomeie como residual declarado.
        if not conditions_text or "RESIDUAL" not in conditions_text.upper():
            die("rail NO-GO (%s) sem secao de condicoes declarando o RESIDUAL "
                "ratificado pelo Owner" % ", ".join(decisions))
        verdict = "GO-WITH-CONDITIONS"
    elif "GO-WITH-CONDITIONS" in decisions:
        verdict = "GO-WITH-CONDITIONS"
    else:
        verdict = "GO"
    if verdict == "GO-WITH-CONDITIONS" and not conditions_text:
        die("GO-WITH-CONDITIONS exige --conditions-file (vai no material assinado)")

    val = load_validator()
    inputs_hash = val.compute_inputs_hash(
        REPO, GOV / "pair-rail-inputs-hash-manifest.txt")
    manifest_sha = sha256_file(GOV / "pair-rail-inputs-hash-manifest.txt")
    delta_manifest_sha = sha256_file(EV / "MANIFEST-rc1.sha256")
    th = hashlib.sha256()
    for n in PARTS:                      # ordem DECLARADA: 1..6
        th.update((EV / ("transcript-rc1-%d.log" % n)).read_bytes())
    transcript_hash = th.hexdigest()

    pin = pinned_codex(prov)
    py = "%d.%d.%d" % sys.version_info[:3]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "verdict: %s" % verdict,
        "generated_at: %s" % now,
        "ttl_hours: 24",
        "parent_sha: %s" % parent,
        "release_tag: %s" % TAG,
        "inputs_hash: %s" % inputs_hash,
        "inputs_hash_paths_manifest_sha: %s" % manifest_sha,
        "delta_allowlist:",
        "  - .claude/governance/pair-rail-verdict-%s.md" % TAG,
        "  - %s/verdict-fields-%s.md" % (PLAN, TAG),
    ]
    for a in ARTIFACTS:
        lines.append("  - %s/repass-rc1/%s" % (PLAN, a))
    lines += [
        "delta_manifest: %s/repass-rc1/MANIFEST-rc1.sha256" % PLAN,
        "delta_manifest_sha256: %s" % delta_manifest_sha,
        "tool_versions:",
        "  codex_cli: %s" % pin["codex_cli"],
        "  codex_target_triple: %s" % pin["target_triple"],
        "  codex_payload_sha256: %s" % pin["sha256"],
        "  claude_code: claude-fable-5",
        "  python: %s" % py,
        "transcript_hash: %s" % transcript_hash,
        "rail_decisions: [%s]" % ", ".join(
            "part%d=%s" % (n, d) for n, d in zip(PARTS, decisions)),
        "findings: [rc1-6-partes-por-risco-do-adotante, %s, "
        "cobertura-declarada-em-repass-rc1-README-rc1]"
        % ", ".join("p%d-%s" % (n, d.lower().replace("-", ""))
                    for n, d in zip(PARTS, decisions)),
    ]
    if conditions_text:
        # As condicoes SAO material assinado: entram nos fields como sub-mapa
        # de linhas (chave nua + lista indentada), grammar-safe.
        lines.append("conditions:")
        for ln in conditions_text.rstrip("\n").splitlines():
            ln = ln.rstrip()
            if not ln:
                continue
            item = ln.lstrip("- ").strip()
            item = item.replace("#", "\u2116")  # nunca introduzir comentario YAML
            lines.append("  - %s" % item)
    return "\n".join(lines) + "\n"


def verify_sig(sig_path: pathlib.Path, fpr: str) -> None:
    proc = subprocess.run(
        ["gpg", "--status-fd", "1", "--verify", str(sig_path), str(FIELDS)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    good = [ln for ln in proc.stdout.splitlines()
            if ln.startswith("[GNUPG:] VALIDSIG ")]
    if proc.returncode != 0 or not good:
        die("assinatura NAO verifica contra %s:\n%s" % (FIELDS, proc.stderr))
    if fpr not in good[0]:
        die("assinatura de OUTRO signatario: %s" % good[0])


def build_envelope(fields_text: str, sig_b64: str, fpr: str) -> str:
    verdict = [ln for ln in fields_text.splitlines()
               if ln.startswith("verdict:")][0].split(":", 1)[1].strip()
    body = fields_text.rstrip("\n") + "\ngpg_signature: base64:%s\n" % sig_b64
    parts = [
        "# Pair-Rail Verdict - %s" % TAG, "",
        "```yaml", body.rstrip("\n"), "```", "",
        "## Signature verification recipe", "",
        'base64 -d do valor apos "base64:" -> .asc destacado; verificar contra',
        "%s/verdict-fields-%s.md (commitado junto)." % (PLAN, TAG),
        "Signer %s. As CONDICOES fazem parte do material assinado" % fpr[-16:],
        "(sub-mapa `conditions:` dos fields).", "",
        "<!-- VERDICT: %s -->" % verdict,
        "## Review record - re-pass do CANDIDATO v1.4.0-rc.1 (advisory input)",
        "",
        "- Contexto: primeiro rc do trem pos-GA v1.3.0 (17/08). O delta e de",
        "  1318 arquivos / ~470k linhas adicionadas; o re-pass cobre a",
        "  superficie ENTREGUE ao adotante, em 6 partes ordenadas por raio de",
        "  dano, e o que fica de fora esta DECLARADO em",
        "  %s/repass-rc1/README-rc1.md §4 — nao omitido." % PLAN,
        "- Cada parte cita, dentro do proprio prompt, as rodadas de rail que",
        "  ja revisaram aquele conteudo ao landar, para que uma condicao possa",
        "  nomear a cobertura em vez de tratar o conteudo como inedito.",
        "- Reviewer: codex-cli PINADO em 0.147.0, resolvido por npx num cache",
        "  proprio e com o payload nativo VERIFICADO contra o manifesto ADR-182",
        "  antes de qualquer revisao. O binario global da maquina (0.153.4)",
        "  esta FORA da faixa do pin e falha o mesmo oraculo — controle",
        "  negativo gratuito, registrado no README §7.",
        "- Pipeline: prompt + diff atraves do redator ADR-114 como UM pipeline;",
        "  worktree DETACHED no SHA candidato (a tag rc.1 ainda nao existe).",
        "",
        "## Derivacoes (parte do material assinado)", "",
        "- transcript_hash = sha256(transcript-rc1-1.log || ... || "
        "transcript-rc1-%d.log), nesta ordem." % NPARTS,
        "- inputs_hash RECOMPUTADO nesta arvore com compute_inputs_hash do",
        "  proprio validador.",
        "- parent_sha VINCULADO ao candidato do runner/PROVENANCE/CANDIDATE.sha",
        "  (o gerador recusa qualquer outro SHA, e exige que as tres fontes",
        "  concordem).",
        "- tool_versions.codex_cli vem da PROVENANCE do run PINADO, nunca de",
        "  `codex --version` da maquina, e e re-validado contra",
        "  codex-cli-pin.txt pela funcao do PROPRIO validador.",
        "- delta_manifest_sha256 pina MANIFEST-rc1.sha256 (%d entradas, runner"
        % (NPARTS * 5 + 3),
        "  incluso). Payloads raw NAO commitados; pins em PROVENANCE-rc1.md.",
        "",
    ]
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("fields", "envelope"), required=True)
    ap.add_argument("--parent")
    ap.add_argument("--sig")
    ap.add_argument("--conditions-file")
    a = ap.parse_args()
    fpr = signer_fpr()
    if a.stage == "fields":
        conds = ""
        if a.conditions_file:
            conds = pathlib.Path(a.conditions_file).read_text(encoding="utf-8")
        write_atomic_regular(FIELDS, build_fields(a.parent, conds))
        print("wrote", FIELDS)
        return 0
    if not a.sig:
        die("--stage envelope exige --sig")
    sig_path = pathlib.Path(a.sig)
    verify_sig(sig_path, fpr)
    fields_text = FIELDS.read_bytes().decode("utf-8")
    val = load_validator()
    # O material assinado precisa passar na PROPRIA gramatica dos twins.
    probe = "```yaml\n%s```\n" % fields_text
    bad = val.noncanonical_top_level_lines(probe)
    if bad:
        die("fields nao passam na gramatica canonica: %r" % bad)
    write_atomic_regular(
        ENVELOPE,
        build_envelope(fields_text,
                       base64.b64encode(sig_path.read_bytes()).decode("ascii"),
                       fpr))
    # Re-verificar: o base64 embutido decodifica para a MESMA assinatura.
    env = ENVELOPE.read_bytes().decode("utf-8")
    m = re.search(r"^gpg_signature: base64:(\S+)$", env, re.M)
    if not m or base64.b64decode(m.group(1)) != sig_path.read_bytes():
        die("assinatura embutida != .asc")
    print("wrote", ENVELOPE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
