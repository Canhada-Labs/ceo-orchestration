#!/bin/bash
# OWNER-RC2-CUT.sh - corte da v1.3.0-rc.2 em UM comando (S300).
#
#   bash .claude/plans/PLAN-166/OWNER-RC2-CUT.sh
#
# O que faz, na ordem (fail-closed em tudo):
#   1. assina o pre-registro W5 (pinentry 1)
#   2. commit 1: evidencia repass-r2 + W5 + docs da sessao
#   3. gera verdict-fields (parent_sha = commit 1) e voce assina (pinentry 2)
#   4. monta o verdito com a assinatura embutida, commit 2, guard local
#   5. push + espera CI ficar verde (ate ~90 min; pode deixar rodando)
#   6. preflight --rc 2 + tag assinada (pinentry 3 - avisa com som/notificacao)
#   7. push da tag + pre-release GitHub (pede confirmacao "SIM")
#
# Se falhar em QUALQUER passo, para com mensagem clara. Rodar de novo e
# seguro ANTES do commit 1 (passo 2). DEPOIS do commit 1, o HEAD ja
# moveu e o G0 vai recusar de proposito — NAO re-rode nem resete nada:
# me chame no Claude, que eu retomo do ponto exato (r5-P2 do rail).
set -euo pipefail

REPO="$(git rev-parse --show-toplevel)"; cd "$REPO"
EXPECTED_HEAD="c0295e15a9d2ef869e44c4cab8b56022acd7b4b7"
TAG="v1.3.0-rc.2"
KEY="CFCFACF00335DC74"
P166=".claude/plans/PLAN-166"
P169=".claude/plans/PLAN-169"
VF="$P166/verdict-fields-v1.3.0-rc.2.md"
VD=".claude/governance/pair-rail-verdict-v1.3.0-rc.2.md"
VF_TPL="$P166/verdict-fields-v1.3.0-rc.2.TEMPLATE.md"
VD_TPL="$P166/pair-rail-verdict-v1.3.0-rc.2.TEMPLATE.md"

say() { printf '\n== %s\n' "$*"; }
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
bell() { printf '\a'; osascript -e "display notification \"$1\" with title \"rc.2\"" 2>/dev/null || true; }

GPG_TTY="$(tty 2>/dev/null || true)"; export GPG_TTY
gpgconf --kill gpg-agent 2>/dev/null || true

say "G0 pre-condicoes"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] \
  || die "nao esta em main (branch/detached) - os commits do corte iriam para o lugar errado e o push de main subiria stale (r6-P2)"
[ "$(git rev-parse HEAD)" = "$EXPECTED_HEAD" ] \
  || die "HEAD nao e $EXPECTED_HEAD. Se o script ja rodou ate o commit 1
e falhou depois, NAO resete: me chame no Claude que eu retomo do ponto
exato. Se main andou por outro motivo, tambem me chame."
git fetch --quiet origin main
[ "$(git rev-parse origin/main)" = "$EXPECTED_HEAD" ] \
  || die "origin/main moveu - investigar antes de cortar"
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1 \
  && die "tag $TAG ja existe"
command -v gh >/dev/null 2>&1 || die "gh CLI ausente"
[ -f "$VF_TPL" ] || die "template verdict-fields ausente"
[ -f "$VD_TPL" ] || die "template do verdito ausente"
[ -f "$P169/W5-preregistration.md" ] || die "W5-preregistration.md ausente"
grep -q "Anchor-SHA: $EXPECTED_HEAD" "$P169/W5-preregistration.md" \
  || die "Anchor-SHA do W5 nao bate com HEAD"
ls "$P166"/repass-r2/payload-*.raw.txt >/dev/null 2>&1 \
  && die "payloads raw ainda na arvore - o Claude devia ter movido"

# Allowlist FECHADA do commit 1 (pair-rail S300 P1-1: git add -A absorveria
# qualquer arquivo alheio e o guard de delta o trataria como parte do
# parent revisado). Entrada terminada em / cobre o diretorio inteiro.
COMMIT1_ALLOW="$P166/OWNER-GA-CUT.sh
$P166/OWNER-RC2-CUT.sh
$P166/pair-rail-verdict-v1.3.0-rc.2.TEMPLATE.md
$P166/pair-rail-verdict-v1.3.0.TEMPLATE.md
$P166/repass-ga/run-ga-repass.sh
$P166/repass-r2/MANIFEST-r2.sha256
$P166/repass-r2/PROVENANCE-r2.md
$P166/verdict-fields-v1.3.0-rc.2.TEMPLATE.md
$P166/verdict-fields-v1.3.0.TEMPLATE.md
$P169/OWNER-MORNING.md
$P169/OWNER-RETURN-CHECKLIST.md
$P169/OWNER-W3-LAND.sh
$P169/W2.8-free-script-gate-family.md
$P169/W3-approved-draft.md
$P169/W5-preregistration.md
$P169/W5-preregistration.md.asc
$P169/e0-serial-fraction.py
$P169/staged-w3/"

check_tree_is_exactly_the_prep() {
  _bad=""
  while IFS= read -r _line; do
    [ -n "$_line" ] || continue
    _path="${_line#???}"
    _hit=0
    while IFS= read -r _allow; do
      [ -n "$_allow" ] || continue
      case "$_allow" in
        */) case "$_path" in "$_allow"*|"${_allow%/}") _hit=1 ;; esac ;;
        *)  [ "$_path" = "$_allow" ] && _hit=1 ;;
      esac
      [ "$_hit" -eq 1 ] && break
    done <<ALLOW
$COMMIT1_ALLOW
ALLOW
    [ "$_hit" -eq 1 ] || _bad="$_bad
   $_path"
  done <<STATUS
$(git status --porcelain --untracked-files=all)
STATUS
  [ -z "$_bad" ] || die "arquivo(s) FORA da allowlist do commit 1 (nao revisados pelo rail):$_bad
Remova/stash antes de cortar, ou me chame no Claude."
}
# staged-w3/ e o UNICO prefixo de diretorio da allowlist; ele fecha por
# CONTEUDO (pair-rail S300 r3 P1-2): shasum -c do MANIFEST do pack +
# igualdade EXATA de conjunto entre os arquivos no disco e
# manifest + {MANIFEST,BASELINE}.sha256 — um verdict-ga ensaiado ou
# qualquer arquivo perdido dentro do staged aborta aqui.
say "G0b: staged-w3 fechado por manifesto"
( cd "$P169/staged-w3" && shasum -a 256 -c MANIFEST.sha256 --status ) \
  || die "staged-w3 nao confere com o MANIFEST do pack"
_st_odd="$( cd "$P169/staged-w3" && find . ! -type f ! -type d | head -5 )"
[ -z "$_st_odd" ] || die "entrada NAO-regular dentro de staged-w3 (symlink/fifo?) — find -type f nao a veria e o git add a commitaria (r5-P2):
$_st_odd"
_st_disk="$( cd "$P169/staged-w3" && find . -type f | sed 's|^\./||' | sort )"
_st_want="$( { awk '{print $2}' "$P169/staged-w3/MANIFEST.sha256"; \
  echo "MANIFEST.sha256"; echo "BASELINE.sha256"; } | sort )"
[ "$_st_disk" = "$_st_want" ] || die "conjunto de arquivos em staged-w3 difere do MANIFEST:
$(diff <(printf '%s\n' "$_st_want") <(printf '%s\n' "$_st_disk") | sed 's/^/   /')"
echo "   OK: staged-w3 = exatamente os $(printf '%s\n' "$_st_want" | grep -c .) arquivos do pack"

check_tree_is_exactly_the_prep
say "mudancas que entram no commit 1 (todas dentro da allowlist):"
git status --short
printf '\nEnter para seguir (ctrl-C para abortar): '; read -r _

say "1/7 assinar W5 (pinentry 1)"
rm -f "$P169/W5-preregistration.md.asc"
gpg --armor --detach-sign -u "$KEY" "$P169/W5-preregistration.md"
gpg --verify "$P169/W5-preregistration.md.asc" "$P169/W5-preregistration.md" \
  || die "assinatura do W5 nao verifica"

say "2/7 commit 1 (evidencia + W5 + docs - SO a allowlist)"
check_tree_is_exactly_the_prep
while IFS= read -r _p; do
  [ -n "$_p" ] || continue
  git add -- "$_p"
done <<ADD
$COMMIT1_ALLOW
ADD
git diff --quiet \
  || die "sobrou mudanca tracked NAO-staged apos o add da allowlist - investigar"
[ -z "$(git status --porcelain --untracked-files=all | grep '^??' || true)" ] \
  || die "sobrou arquivo untracked apos o add da allowlist - investigar"
git commit -m "docs(PLAN-166/169): evidencia repass-r2 final + W5 assinado + preparo do corte rc.2

Manifesto r2 em basenames (mesmos hashes), pins dos payloads raw na
PROVENANCE, W5-preregistration assinado (anchor $EXPECTED_HEAD),
decisao W2.8 registrada, scripts de corte rc.2/GA e templates do
verdito. Nenhum delta de produto."
PARENT="$(git rev-parse HEAD)"
printf 'commit 1 = %s\n' "$PARENT"

say "3/7 verdict-fields (parent=$PARENT) - revisar e assinar (pinentry 2)"
GEN="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
awk 'f{print} /-->/{f=1}' "$VF_TPL" \
  | sed -e "s/@@PARENT_SHA@@/$PARENT/" -e "s/@@GENERATED_AT@@/$GEN/" > "$VF"
printf '\n----- CONTEUDO QUE VOCE VAI ASSINAR -----\n'
cat "$VF"
printf -- '----- FIM -----\n\nEnter para assinar (ctrl-C aborta): '; read -r _
rm -f "$VF.asc"
gpg --armor --detach-sign -u "$KEY" "$VF"
gpg --verify "$VF.asc" "$VF" || die "assinatura do verdict-fields nao verifica"

say "4/7 montar verdito + commit 2 + guard local"
SIG="$(base64 < "$VF.asc" | tr -d '\n')"
sed -e "s/@@PARENT_SHA@@/$PARENT/" -e "s/@@GENERATED_AT@@/$GEN/" \
    -e "s|@@SIG_B64@@|$SIG|" "$VD_TPL" > "$VD"
mkdir -p "$HOME/.rc2-backup"
mv "$VF.asc" "$HOME/.rc2-backup/verdict-fields-v1.3.0-rc.2.md.asc"
git add "$VF" "$VD"
git commit -m "governance(PLAN-166 W2): verdito pair-rail v1.3.0-rc.2 assinado

GO-WITH-CONDITIONS: 4 excecoes de produto nomeadas (V1/V2/V4/V5,
curas staged no pack W3 pos-GA) + ratificacao approx/collect-errors
no material assinado. Evidencia: repass-r2 (4 rodadas multi-part)."
python3 .claude/scripts/local/_release_tag_guard.py delta \
  --repo "$REPO" --tag "$TAG" || die "guard delta recusou - NAO pushe"

say "5/7 push + espera CI (pode demorar 15-40 min; deixe rodando)"
git push origin main
HEADSHA="$(git rev-parse HEAD)"
i=0
while :; do
  i=$((i+1))
  [ "$i" -le 90 ] || die "CI nao terminou em 90 min - veja gh run list"
  sleep 60
  info="$(gh run list --limit 20 --json headSha,status,conclusion \
    --jq "[.[]|select(.headSha==\"$HEADSHA\")] | \
{n:length, p:[.[]|select(.status!=\"completed\")]|length, \
b:[.[]|select(.status==\"completed\" and .conclusion!=\"success\" \
and .conclusion!=\"skipped\")]|length}" 2>/dev/null || echo "")"
  [ -n "$info" ] || { printf '  ... gh falhou, tentando de novo\n'; continue; }
  n="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["n"])')"
  p="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["p"])')"
  b="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["b"])')"
  printf '  ... runs=%s pendentes=%s vermelhos=%s\n' "$n" "$p" "$b"
  [ "$b" -eq 0 ] || die "workflow vermelho no commit do verdito - me chame no Claude"
  if [ "$n" -gt 0 ] && [ "$p" -eq 0 ]; then break; fi
done
# Envelope verde nao basta (pair-rail S300 r10 P1-1): com
# CEO_SOTA_DISABLE=1 o validate.yml PULA os jobs e o run continua
# "success". Exigimos ao nivel de JOB: >=1 job success e 0 failure.
VID="$(gh run list --workflow validate.yml --limit 20 \
  --json headSha,databaseId \
  --jq "[.[]|select(.headSha==\"$HEADSHA\")][0].databaseId" 2>/dev/null || echo "")"
[ -n "$VID" ] && [ "$VID" != "null" ] || die "nenhum run do validate.yml para o HEAD"
VJ="$(gh run view "$VID" --json jobs \
  --jq '{s:[.jobs[]|select(.conclusion=="success")]|length, f:[.jobs[]|select(.conclusion=="failure")]|length}' 2>/dev/null || echo "")"
vs="$(printf '%s' "$VJ" | python3 -c 'import json,sys;print(json.load(sys.stdin)["s"])')"
vf="$(printf '%s' "$VJ" | python3 -c 'import json,sys;print(json.load(sys.stdin)["f"])')"
[ "$vf" -eq 0 ] || die "job vermelho dentro do validate.yml"
[ "$vs" -ge 1 ] || die "validate.yml sem NENHUM job executado (CEO_SOTA_DISABLE ligado? break-glass fora de incidente viola ADR-191) - me chame no Claude"
echo "   validate.yml: $vs job(s) success, 0 failure (nivel de job)"
bell "CI verde - vamos assinar a tag"

say "6/7 preflight + tag assinada (pinentry 3)"
bash .claude/scripts/local/release.sh preflight --rc 2
bash .claude/scripts/local/release.sh tag --rc 2

say "7/7 push da tag + pre-release"
printf 'push da tag %s e pre-release GitHub? digite SIM: ' "$TAG"
read -r ans
[ "$ans" = "SIM" ] || die "abortado pelo Owner (tag assinada local, nao pushada)"
git push origin "$TAG"
printf 'esperando release.yml da tag...\n'
TAGSHA="$(git rev-parse "$TAG^{commit}")"
i=0
while :; do
  i=$((i+1)); [ "$i" -le 40 ] || die "release.yml nao terminou em 40 min"
  sleep 60
  c="$(gh run list --workflow release.yml --limit 10 \
    --json headSha,status,conclusion \
    --jq "[.[]|select(.headSha==\"$TAGSHA\")][0].conclusion" 2>/dev/null || echo "")"
  s="$(gh run list --workflow release.yml --limit 10 \
    --json headSha,status,conclusion \
    --jq "[.[]|select(.headSha==\"$TAGSHA\")][0].status" 2>/dev/null || echo "")"
  printf '  ... release.yml: %s/%s\n' "${s:-?}" "${c:-?}"
  [ "$c" = "failure" ] && die "release.yml vermelho - me chame no Claude"
  [ "$s" = "completed" ] && [ "$c" = "success" ] && break
done
# O job await-release-gate do npm-publish.yml roda TAMBEM em tag rc —
# e o controle positivo VIVO do gate de publish do GA (pair-rail S300
# r10 P1-2): se ele falha na rc, o hold de 24h comecaria sobre um
# caminho de publish nunca validado. Exigimos o JOB verde (o run
# inteiro pode ficar aguardando aprovacao production-npm - normal).
printf 'esperando o job await-release-gate do npm-publish.yml (controle positivo)...\n'
i=0
while :; do
  i=$((i+1)); [ "$i" -le 30 ] || die "await-release-gate nao concluiu em 30 min"
  sleep 60
  NID="$(gh run list --workflow npm-publish.yml --limit 10 \
    --json headSha,databaseId \
    --jq "[.[]|select(.headSha==\"$TAGSHA\")][0].databaseId" 2>/dev/null || echo "")"
  if [ -z "$NID" ] || [ "$NID" = "null" ]; then
    printf '  ... run do npm-publish ainda nao apareceu\n'; continue
  fi
  AC="$(gh run view "$NID" --json jobs \
    --jq '[.jobs[]|select(.name|startswith("Await release-gate"))][0].conclusion' 2>/dev/null || echo "")"
  printf '  ... await-release-gate: %s\n' "${AC:-pendente}"
  [ "$AC" = "failure" ] && die "await-release-gate FALHOU na rc - controle positivo do publish morto; me chame no Claude"
  [ "$AC" = "success" ] && break
done
echo "   controle positivo do npm-gate: verde"

# O release.yml (job publish-release) CRIA o GitHub Release sozinho,
# idempotente, com --prerelease para tags rc (pair-rail S300 r6 P1-1:
# um gh release create aqui SEMPRE falharia com "already exists").
# Aqui so VERIFICAMOS o resultado.
_pr="$(gh release view "$TAG" --json isPrerelease --jq .isPrerelease 2>/dev/null || echo "")"
[ "$_pr" = "true" ] \
  || die "GitHub Release da $TAG ausente ou sem flag pre-release (isPrerelease='$_pr') - me chame no Claude"
echo "   GitHub pre-release confirmado (criado pelo release.yml)"

bell "rc.2 cortada"
cat <<'DONE'

============================================================
 rc.2 CORTADA. A partir de agora MAIN CONGELADO ate o GA.
 - Hold ADR-103: >= 24h a partir de agora.
 - Amanha: bash .claude/plans/PLAN-166/OWNER-GA-CUT.sh
 - Me chame no Claude: rodo o E0 (W5 esta assinado) e o
   fechamento da sessao.
============================================================
DONE
