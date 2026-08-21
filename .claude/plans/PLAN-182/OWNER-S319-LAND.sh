#!/bin/bash
# OWNER-S319-LAND.sh — aplica o pack SENT-S319 (PLAN-182 W1).
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao
# (o gerador da W3 do PLAN-174 ainda nao emite cortes de wave); revisado
# pelo rail codex na S319.
#
#   bash .claude/plans/PLAN-182/OWNER-S319-LAND.sh --dry-run
#   bash .claude/plans/PLAN-182/OWNER-S319-LAND.sh
#
# ORDEM OBRIGATORIA (o rail r1 P1-3 exigiu que fosse explicita):
#   1. CUSTODIA da cadeia historica (archive ou inherit)
#   2. aplicar o tree/ nos paths canonicos
#   3. verify_chain() no destino + controle positivo de permissao
#   4. commit
# O --dry-run faz TUDO num clone descartavel; a arvore viva e o
# $HOME/.claude/projects/ nao sao tocados.
set -Eeuo pipefail

REPO="$HOME/canhada-labs/ceo-orchestration"
PACK_REL=".claude/plans/PLAN-182/staged-w1"
SENTINEL_REL=".claude/plans/PLAN-182/S319-approved.md"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

say() { printf '\n== %s\n' "$*"; }
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }

cd "$REPO"

# ---------------------------------------------------------------- 0. gates
say "G0. pre-condicoes"
[ -f "$SENTINEL_REL" ] || die "sentinel ausente: $SENTINEL_REL"
[ -f "$SENTINEL_REL.asc" ] || die "assinatura ausente: $SENTINEL_REL.asc"
gpg --verify "$SENTINEL_REL.asc" "$SENTINEL_REL" 2>/dev/null \
  || die "assinatura do sentinel NAO verifica"
( cd "$PACK_REL/tree" && shasum -a 256 -c ../MANIFEST.sha256 --status ) \
  || die "pack corrompido (shasum -c)"
PACK_N="$(wc -l < "$PACK_REL/MANIFEST.sha256" | tr -d ' ')"
echo "   sentinel assinado OK; pack integro ($PACK_N arquivos)"

# Anchor-SHA do sentinel tem de casar o HEAD (assinatura fresca).
ANCHOR="$(grep -m1 '^Anchor-SHA:' "$SENTINEL_REL" | sed 's/^[^:]*: *//')"
HEAD_SHA="$(git rev-parse HEAD)"
[ "$ANCHOR" = "$HEAD_SHA" ] \
  || die "Anchor-SHA ($ANCHOR) != HEAD ($HEAD_SHA) — re-assine o sentinel"
echo "   anchor casa o HEAD"

# Custodia: le do sentinel ASSINADO (nunca de argumento de linha de comando).
CUSTODY="$(grep -m1 '^Custódia\|^Custodia' "$SENTINEL_REL" \
           | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
case "$CUSTODY" in
  ARCHIVE|INHERIT) : ;;
  *) die "custodia invalida no sentinel: '$CUSTODY' (esperado ARCHIVE ou INHERIT)" ;;
esac
echo "   custodia (do sentinel assinado): $CUSTODY"

# touched - scope = 0: todo path do MANIFEST tem de existir na arvore alvo
# OU ser arquivo novo declarado (runtime_paths.py + os 2 testes novos).
say "G1. touched - scope"
NOVOS=".claude/hooks/_lib/runtime_paths.py
.claude/hooks/tests/test_runtime_paths.py
.claude/hooks/tests/test_audit_family_two_projects.py"
MISSING=0
while read -r _sha _f; do
  rel="${_f#./}"
  if [ ! -f "$rel" ] && ! printf '%s\n' "$NOVOS" | grep -qxF "$rel"; then
    echo "   ALVO INEXISTENTE e nao declarado novo: $rel"; MISSING=1
  fi
done < "$PACK_REL/MANIFEST.sha256"
[ "$MISSING" -eq 0 ] || die "MANIFEST tem alvo fora do scope"
echo "   todo alvo existe (ou e novo declarado)"

# ------------------------------------------------------- destino do trabalho
if [ "$DRY" -eq 1 ]; then
  WORK="$(mktemp -d)/clone"
  say "DRY-RUN: clone descartavel em $WORK"
  git clone --local --quiet "$REPO" "$WORK"
  FAKE_HOME="$(mktemp -d)"
  mkdir -p "$FAKE_HOME/.claude/projects/ceo-orchestration"
  # semente de cadeia legada para exercitar a custodia de verdade
  printf 'legacy-key-32-bytes-placeholder!\n' \
    > "$FAKE_HOME/.claude/projects/ceo-orchestration/audit-key"
  chmod 600 "$FAKE_HOME/.claude/projects/ceo-orchestration/audit-key"
  printf '{"action":"agent_spawn"}\n' \
    > "$FAKE_HOME/.claude/projects/ceo-orchestration/audit-log.jsonl"
  head -c 32 /dev/urandom \
    > "$FAKE_HOME/.claude/projects/ceo-orchestration/.salt"
  chmod 600 "$FAKE_HOME/.claude/projects/ceo-orchestration/.salt"
  TARGET_HOME="$FAKE_HOME"
else
  WORK="$REPO"
  TARGET_HOME="$HOME"
  st="$(git status --porcelain --untracked-files=all \
        | grep -v 'S319-approved' || true)"
  [ -z "$st" ] || die "arvore suja — o land exige arvore limpa:
$st"
fi

# rollback do apply em qualquer falha (a licao do residuo meio-aplicado)
if [ "$DRY" -eq 0 ]; then
  trap 'echo "ERRO no land — revertendo a arvore" >&2; \
        git -C "$WORK" checkout HEAD -- . 2>/dev/null || true' ERR
fi

# --------------------------------------------------- 1. CUSTODIA (PRIMEIRO)
say "G2. custodia da cadeia historica ($CUSTODY)"
LEGACY_DIR="$TARGET_HOME/.claude/projects/ceo-orchestration"
NEW_SLUG="-$(printf '%s' "$REPO" | sed 's|^/||; s|/|-|g')"
NEW_DIR="$TARGET_HOME/.claude/projects/$NEW_SLUG"
echo "   legado: $LEGACY_DIR"
echo "   novo:   $NEW_DIR"
mkdir -p "$NEW_DIR"; chmod 700 "$NEW_DIR"

if [ -d "$LEGACY_DIR" ]; then
  case "$CUSTODY" in
    ARCHIVE)
      ARCH="$LEGACY_DIR.pre-W1-archive"
      [ -e "$ARCH" ] && die "arquivo de destino ja existe: $ARCH"
      mv "$LEGACY_DIR" "$ARCH"
      chmod -R a-w "$ARCH" 2>/dev/null || true
      echo "   ARQUIVADO em $ARCH (somente leitura)"
      echo "   este projeto nasce limpo: salt e chave NOVOS (mint registrado)"
      ;;
    INHERIT)
      for f in audit-key .salt audit-log.jsonl audit-log.last-hmac \
               audit-log.chain-length; do
        [ -f "$LEGACY_DIR/$f" ] || continue
        cp -p "$LEGACY_DIR/$f" "$NEW_DIR/$f"
        echo "   herdado byte-a-byte: $f"
      done
      chmod 600 "$NEW_DIR/audit-key" 2>/dev/null || true
      chmod 600 "$NEW_DIR/.salt" 2>/dev/null || true
      echo "   HERDADO — correlacao historica preservada NESTE projeto"
      ;;
  esac
else
  echo "   nao ha dir legado — nada a custodiar"
fi

# ------------------------------------------------------------ 2. APLICAR
say "G3. aplicar o pack ($PACK_N arquivos)"
N=0
while read -r _sha _f; do
  rel="${_f#./}"
  mkdir -p "$WORK/$(dirname "$rel")"
  cp -p "$REPO/$PACK_REL/tree/$rel" "$WORK/$rel"
  N=$((N + 1))
done < "$PACK_REL/MANIFEST.sha256"
echo "   $N arquivo(s) aplicados"
# bit de execucao (a licao do cp que perde exec bit)
find "$WORK/.claude/hooks" -maxdepth 1 -name '*.py' -exec chmod +x {} \; \
  2>/dev/null || true

# ------------------------------------------------- 3. VERIFICACAO (GATE)
say "G4. verificacao pos-migracao"
( cd "$WORK" && python3 .claude/scripts/derive-audit-family.py \
    --assert-migrated ) || die "assert-migrated != 0 apos o apply"

# NAO sobrescrever HOME aqui: os testes ja isolam HOME internamente
# (TestEnvContext) e mudar HOME esconde o user-site onde o pytest vive.
( cd "$WORK" && CLAUDE_PROJECT_DIR="$WORK" \
    python3 -m pytest .claude/hooks/tests/test_runtime_paths.py \
    .claude/hooks/tests/test_audit_family_two_projects.py -q ) \
  || die "aceitacao P0 vermelha apos o apply"

# controle POSITIVO de permissao: chave 0644 tem de ser detectada
say "G5. controle positivo de permissao (chave 0644 => erro)"
CTRL="$(mktemp -d)"; mkdir -p "$CTRL/.claude/projects/ctrl"
head -c 32 /dev/urandom > "$CTRL/.claude/projects/ctrl/audit-key"
chmod 644 "$CTRL/.claude/projects/ctrl/audit-key"
if ( cd "$WORK" && CEO_AUDIT_KEY_PATH="$CTRL/.claude/projects/ctrl/audit-key" \
     python3 -c 'import sys; sys.path.insert(0, ".claude/hooks"); \
from _lib import audit_hmac; audit_hmac.get_or_create_key()' 2>/dev/null ); then
  die "controle positivo FALHOU: chave 0644 foi aceita"
fi
echo "   OK: chave 0644 rejeitada (o gate de permissao esta vivo)"

# ------------------------------------------------------------- 4. COMMIT
if [ "$DRY" -eq 1 ]; then
  say "DRY-RUN VERDE — nada foi tocado na arvore viva nem no seu \$HOME"
  echo "   clone:     $WORK"
  echo "   home fake: $TARGET_HOME"
  exit 0
fi

say "G6. commit"
git add -A
git commit -q -m "ceremony(SENT-S319): PLAN-182 W1 — runtime state POR PROJETO (resolvedor unico; assert-migrated 102->0)

Custodia da cadeia historica: $CUSTODY (decisao do Owner no sentinel).
Pack: $PACK_N arquivos, MANIFEST.sha256 verificado fail-closed.
Rail codex: 12 rodadas ate rodada limpa, 35 achados curados.
Suite CI-equivalente: P1=0/P2=0/P3=0. assert-migrated: 0.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
echo "   commit: $(git rev-parse --short HEAD)"
trap - ERR

cat <<'DONE'

============================================================
 SENT-S319 LANDADO (commit local). Proximo:
   git push origin main
 Depois:
   - PLAN-182 W2 (custodia formal + F12 dois-locks + emissores
     do campo project) fica destravada.
   - PLAN-174 W2 (ceremony-lint no CI) pode ir na sequencia.
============================================================
DONE
