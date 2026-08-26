#!/usr/bin/env bash
# OWNER-S328-MORNING.sh — o ÚNICO comando da manhã da night-run S328.
# CEREMONY-LINT: handwritten-exception: orquestrador da manhã — compõe scripts gerados/clonados, não substitui nenhum
#
# O QUE ELE FAZ
#   Roda, na ordem B -> A -> C -> D, a cerimônia de cada pacote que EXISTIR:
#     finalize (re-base no HEAD vivo) -> SIGN (GPG) -> LAND --dry-run -> LAND
#     -> confere que o push aconteceu
#   Para no PRIMEIRO vermelho, com diagnóstico e o comando exato de retomada.
#
# O QUE ELE NÃO FAZ
#   Não commita, não empurra, não assina, não aplica patch. Quem faz isso são
#   os scripts de cada pacote — este arquivo só decide QUEM roda, em QUE ordem,
#   e QUANDO parar. Nenhum editor abre em momento nenhum.
#
# POR QUE A ORDEM É B -> A -> C -> D
#   B  cura o gate de hook-latency: sem ele o CI `Validate` continua vermelho.
#   A  fecha a W5-b do PLAN-183 (ADR-194 + discriminante do CODEOWNERS).
#   C  (PLAN-185 W1/W2) toca os MESMOS arquivos de A e de B — só pode entrar
#      depois dos dois. A ou B fora ⇒ C NÃO roda.
#   D  (PLAN-179 W2+W4) é o land mais longo; vai por último para não segurar
#      a fila se algo travar nele.
#
# DESCOBERTA EM RUNTIME, NUNCA POR SUPOSIÇÃO
#   Um pacote pode não existir (a noite pode não ter chegado nele). Presença,
#   tipo (patch ou manifesto), sentinel, patch, script de finalize e argumentos
#   do LAND são todos DERIVADOS dos scripts reais de cada pacote — do bloco de
#   constantes e do bloco `# Uso:` deles. Nada aqui é lembrado de cabeça.
#
# USO
#   bash .claude/plans/PLAN-183/OWNER-S328-MORNING.sh
#   bash .claude/plans/PLAN-183/OWNER-S328-MORNING.sh --dry-run
#   bash .claude/plans/PLAN-183/OWNER-S328-MORNING.sh --from A
#   bash .claude/plans/PLAN-183/OWNER-S328-MORNING.sh --only D
#   bash .claude/plans/PLAN-183/OWNER-S328-MORNING.sh --ownership-e2e=run
#
# CÓDIGOS DE SAÍDA (distintos por etapa — o número diz onde parou)
#    0  tudo que existia foi landado
#    2  erro de uso (argumento desconhecido ou inválido)
#    3  pré-condição global (não é repo git, não está em `main`, árvore suja)
#    7  terminou SEM vermelho, mas nem tudo rodou (pacote ausente ou pulado)
#   1X  pacote B    2X  pacote A    3X  pacote C    4X  pacote D
#       X1 finalize · X2 SIGN · X3 LAND --dry-run · X4 LAND · X5 pós-land
#       X6 anomalia de estado do pacote (ver a mensagem)
set -uo pipefail

# ---------------------------------------------------------------------------
# 0 — localização (resolve por git a partir da LOCALIZAÇÃO DO SCRIPT, nunca
#     por `../..` nem pelo cwd: o Owner pode chamar de qualquer diretório).
# ---------------------------------------------------------------------------
_SD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
SCRIPT_PATH="$_SD/$( basename "${BASH_SOURCE[0]}" )"
ROOT="$( cd "$_SD" && git rev-parse --show-toplevel 2>/dev/null || printf '' )"
if [ -z "$ROOT" ]; then
  printf '\033[31mABORT:\033[0m %s não está dentro de um repositório git.\n' "$_SD" >&2
  exit 3
fi
cd "$ROOT" || exit 3

# ---------------------------------------------------------------------------
# 1 — argumentos
# ---------------------------------------------------------------------------
ORDER="B A C D"
# Os argumentos ORIGINAIS, guardados ANTES do parser: o bloco do `tee` re-executa
# este script e `"$@"` já teria sido consumido pelos `shift` daqui de baixo —
# o filho nasceria sem `--dry-run`, sem `--from`, sem `--only`.
ORIG_ARGS=( "$@" )
DRY_RUN=0
FROM=""
ONLY=""
OWNERSHIP_E2E="defer"
OWNERSHIP_E2E_EXPLICIT=0

_usage() {
  sed -n '2,44p' "$SCRIPT_PATH" | sed -e '/CEREMONY-LINT/d' -e 's/^# \{0,1\}//'
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --help|-h) _usage; exit 0 ;;
    --dry-run) DRY_RUN=1 ;;
    --from)
      shift
      FROM="${1:-}"
      [ -n "$FROM" ] || { printf '\033[31mABORT:\033[0m --from exige um pacote (B|A|C|D)\n' >&2; exit 2; } ;;
    --from=*) FROM="${1#--from=}" ;;
    --only)
      shift
      ONLY="${1:-}"
      [ -n "$ONLY" ] || { printf '\033[31mABORT:\033[0m --only exige um pacote (B|A|C|D)\n' >&2; exit 2; } ;;
    --only=*) ONLY="${1#--only=}" ;;
    --ownership-e2e=run)   OWNERSHIP_E2E="run";   OWNERSHIP_E2E_EXPLICIT=1 ;;
    --ownership-e2e=defer) OWNERSHIP_E2E="defer"; OWNERSHIP_E2E_EXPLICIT=1 ;;
    --ownership-e2e=*)
      printf '\033[31mABORT:\033[0m valor inválido em %s (use run ou defer)\n' "$1" >&2; exit 2 ;;
    *)
      printf '\033[31mABORT:\033[0m argumento desconhecido: %s\n' "$1" >&2
      printf '  rode  bash %s --help\n' "$SCRIPT_PATH" >&2
      exit 2 ;;
  esac
  shift
done

_valid_pkg() {
  case " $ORDER " in
    *" $1 "*) return 0 ;;
    *) return 1 ;;
  esac
}
if [ -n "$FROM" ] && ! _valid_pkg "$FROM"; then
  printf '\033[31mABORT:\033[0m --from %s: pacote desconhecido (use B, A, C ou D)\n' "$FROM" >&2; exit 2
fi
if [ -n "$ONLY" ] && ! _valid_pkg "$ONLY"; then
  printf '\033[31mABORT:\033[0m --only %s: pacote desconhecido (use B, A, C ou D)\n' "$ONLY" >&2; exit 2
fi
if [ -n "$FROM" ] && [ -n "$ONLY" ]; then
  printf '\033[31mABORT:\033[0m --from e --only são mutuamente exclusivos\n' >&2; exit 2
fi

# ---------------------------------------------------------------------------
# 2 — log completo desta execução (tee); o rc do script é preservado
# ---------------------------------------------------------------------------
LOG_DIR="$ROOT/.claude/plans/PLAN-183/s328-ceremony-main"
if [ "${MORNING_TEE:-0}" != "1" ]; then
  mkdir -p "$LOG_DIR" 2>/dev/null || printf ''
  if [ -d "$LOG_DIR" ] && [ -w "$LOG_DIR" ]; then
    _LF="$LOG_DIR/morning-$( date +%Y%m%d-%H%M%S ).log"
    printf 'log completo desta execução: %s\n\n' "$_LF"
    MORNING_TEE=1 MORNING_LOG_FILE="$_LF" bash "$SCRIPT_PATH" \
      ${ORIG_ARGS[@]+"${ORIG_ARGS[@]}"} 2>&1 | tee -a "$_LF"
    exit "${PIPESTATUS[0]}"
  fi
  printf '\033[33mAVISO\033[0m não consegui escrever em %s — seguindo SEM log em arquivo.\n' "$LOG_DIR"
fi
LOG_FILE="${MORNING_LOG_FILE:-}"
STEP_LOG_DIR="$LOG_DIR"
if [ ! -d "$STEP_LOG_DIR" ] || [ ! -w "$STEP_LOG_DIR" ]; then
  STEP_LOG_DIR="${TMPDIR:-/tmp}"
fi

# O pinentry do GPG precisa do terminal. `tty` lê o STDIN, que este script
# nunca redireciona — mesmo com o stdout em pipe para o `tee`.
GPG_TTY="${GPG_TTY:-$( tty 2>/dev/null || printf '' )}"
export GPG_TTY

# ---------------------------------------------------------------------------
# 3 — saída
# ---------------------------------------------------------------------------
say()  { printf '%s\n' "$*"; }
ok()   { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
warn() { printf '\033[33m  AVISO\033[0m %s\n' "$*"; }
info() { printf '      %s\n' "$*"; }
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }
head1(){ printf '\n\033[1m========================================================================\033[0m\n\033[1m%s\033[0m\n\033[1m========================================================================\033[0m\n' "$*"; }

# Comando de retomada, com as MESMAS opções globais desta execução.
_resume_cmd() {
  local pkg="$1" extra=""
  [ "$OWNERSHIP_E2E_EXPLICIT" = "1" ] && extra=" --ownership-e2e=$OWNERSHIP_E2E"
  printf 'bash %s --from %s%s' "$SCRIPT_PATH" "$pkg" "$extra"
}

# Um único ponto de parada: imprime diagnóstico + o que fazer + como retomar.
# Nada é desfeito aqui — cada LAND já restaura a própria árvore ao abortar.
_red() {  # <pacote> <etapa> <rc> <exit-code> <diagnóstico> [o-que-fazer...]
  local pkg="$1" etapa="$2" rc="$3" code="$4" diag="$5"; shift 5
  printf '\n\033[31m========================================================================\033[0m\n'
  printf '\033[31mVERMELHO\033[0m — pacote %s, etapa %s (rc=%s)\n' "$pkg" "$etapa" "$rc"
  printf '\033[31m========================================================================\033[0m\n\n'
  printf '  DIAGNÓSTICO\n    %s\n\n' "$diag"
  if [ "$#" -gt 0 ]; then
    printf '  O QUE FAZER\n'
    while [ "$#" -gt 0 ]; do printf '    %s\n' "$1"; shift; done
    printf '\n'
  fi
  printf '  RETOMAR (depois de resolver, copie e cole a linha inteira)\n\n'
  printf '    %s\n\n' "$( _resume_cmd "$pkg" )"
  [ -n "$LOG_FILE" ] && printf '  LOG COMPLETO\n    %s\n\n' "$LOG_FILE"
  _print_summary
  exit "$code"
}

# ---------------------------------------------------------------------------
# 4 — estado por pacote (sem arrays associativos: bash 3.2 do macOS)
# ---------------------------------------------------------------------------
ST_B="não avaliado"; ST_A="não avaliado"; ST_C="não avaliado"; ST_D="não avaliado"
LANDED_B=0; LANDED_A=0; LANDED_C=0; LANDED_D=0
SKIPPED_ANY=0
B_MISSING_CI_WARNED=0

_set_status() { case "$1" in B) ST_B="$2";; A) ST_A="$2";; C) ST_C="$2";; D) ST_D="$2";; esac; }
_get_status() { case "$1" in B) printf '%s' "$ST_B";; A) printf '%s' "$ST_A";; C) printf '%s' "$ST_C";; D) printf '%s' "$ST_D";; esac; }
_mark_landed() { case "$1" in B) LANDED_B=1;; A) LANDED_A=1;; C) LANDED_C=1;; D) LANDED_D=1;; esac; }
_is_landed()   { case "$1" in B) [ "$LANDED_B" = 1 ];; A) [ "$LANDED_A" = 1 ];; C) [ "$LANDED_C" = 1 ];; D) [ "$LANDED_D" = 1 ];; *) return 1;; esac; }

_exit_code_for() {  # <pacote> <offset 1..6>
  local base
  case "$1" in B) base=10 ;; A) base=20 ;; C) base=30 ;; D) base=40 ;; *) base=90 ;; esac
  printf '%s' "$(( base + $2 ))"
}

# Os DOIS scripts de cada pacote. É o único par de caminhos que este
# orquestrador precisa saber de antemão — tudo o mais sai de dentro deles.
PKG_SIGN=""; PKG_LAND=""; PKG_PLAN=""
_pkg_scripts() {
  case "$1" in
    B) PKG_PLAN=".claude/plans/PLAN-169"
       PKG_SIGN="$PKG_PLAN/OWNER-S328-B-SIGN.sh"
       PKG_LAND="$PKG_PLAN/OWNER-S328-B-LAND.sh" ;;
    A) PKG_PLAN=".claude/plans/PLAN-183"
       PKG_SIGN="$PKG_PLAN/OWNER-S328-A-SIGN.sh"
       PKG_LAND="$PKG_PLAN/OWNER-S328-A-LAND.sh" ;;
    C) PKG_PLAN=".claude/plans/PLAN-185"
       PKG_SIGN="$PKG_PLAN/OWNER-S328-C-SIGN.sh"
       PKG_LAND="$PKG_PLAN/OWNER-S328-C-LAND.sh" ;;
    D) PKG_PLAN=".claude/plans/PLAN-179"
       PKG_SIGN="$PKG_PLAN/OWNER-W179-W24-SIGN.sh"
       PKG_LAND="$PKG_PLAN/OWNER-W179-W24-LAND.sh" ;;
  esac
}

_pkg_label() {
  case "$1" in
    B) printf 'B (PLAN-169 — emenda ADR-163 + gate de hook-latency)' ;;
    A) printf 'A (PLAN-183 W5-b — ADR-194 + discriminante do CODEOWNERS)' ;;
    C) printf 'C (PLAN-185 W1/W2 — symlink + handle validado)' ;;
    D) printf 'D (PLAN-179 W2+W4 — ledger checkpoint)' ;;
  esac
}

# ---------------------------------------------------------------------------
# 5 — derivação a partir dos scripts REAIS do pacote
# ---------------------------------------------------------------------------

# Lê `NOME="valor"` do bloco de constantes (só no início da linha: comentários
# que citem a constante não contam).
_const() {  # <script> <NOME>
  [ -f "$1" ] || return 0
  awk -v k="$2" '
    index($0, k "=") == 1 {
      v = substr($0, length(k) + 2)
      sub(/[[:space:]]*#.*$/, "", v)
      gsub(/^"|"$/, "", v)
      print v
      exit
    }' "$1"
}

# Expande $PLAN_DIR / $CEREMONY_DIR (as duas únicas variáveis usadas nos
# valores das constantes destes scripts).
_expand() {  # <valor> <plan_dir> <cer_dir>
  local v="$1"
  v="${v//\$\{PLAN_DIR\}/$2}"
  v="${v//\$PLAN_DIR/$2}"
  v="${v//\$\{CEREMONY_DIR\}/$3}"
  v="${v//\$CEREMONY_DIR/$3}"
  printf '%s' "$v"
}

# Argumentos NÃO-dry-run do LAND, lidos do bloco `# Uso:` do próprio LAND.
# Derivar em vez de lembrar: um pacote novo pode exigir uma flag que este
# orquestrador não conhece, e ela está documentada lá.
_land_args() {  # <land script>
  [ -f "$1" ] || return 0
  local base; base="$( basename "$1" )"
  awk -v base="$base" '
    /^#[[:space:]]*Uso:/            { inblk = 1; next }
    inblk && $0 !~ /^#/             { exit }
    inblk && index($0, base) > 0 && index($0, "--dry-run") == 0 {
      i = index($0, base)
      rest = substr($0, i + length(base))
      gsub(/^[[:space:]]+/, "", rest)
      gsub(/[[:space:]]+$/, "", rest)
      print rest
      exit
    }' "$1"
}

FINALIZE_COUNT=0
_find_finalize() {  # <ceremony dir>
  local d="$1" n=0 f="" x
  FINALIZE_COUNT=0
  [ -d "$d" ] || return 0
  for x in "$d"/finalize-*.sh; do
    [ -f "$x" ] || continue
    n=$(( n + 1 )); f="$x"
  done
  FINALIZE_COUNT="$n"
  printf '%s' "$f"
}

# Campos preenchidos por _pkg_load.
P_KIND=""; P_CER=""; P_SENTINEL=""; P_PATCH=""; P_FINALIZE=""; P_LAND_ARGS=""; P_SUBJECT=""
_pkg_load() {  # <pacote> -> 0 se os dois scripts existem, 1 se ausente
  local pkg="$1" plan cer
  _pkg_scripts "$pkg"
  P_KIND=""; P_CER=""; P_SENTINEL=""; P_PATCH=""; P_FINALIZE=""; P_LAND_ARGS=""; P_SUBJECT=""
  if [ ! -f "$PKG_SIGN" ] || [ ! -f "$PKG_LAND" ]; then
    return 1
  fi
  plan="$( _const "$PKG_SIGN" PLAN_DIR )"
  [ -n "$plan" ] || plan="$PKG_PLAN"
  cer="$( _expand "$( _const "$PKG_SIGN" CEREMONY_DIR )" "$plan" "" )"
  P_CER="$cer"
  P_SENTINEL="$( _expand "$( _const "$PKG_SIGN" SENTINEL )" "$plan" "$cer" )"
  P_PATCH="$( _expand "$( _const "$PKG_SIGN" PATCH )" "$plan" "$cer" )"
  # O discriminante do TIPO é o próprio pacote: quem declara PATCH é
  # patch-based; quem não declara é manifesto (o pack do PLAN-179).
  if [ -n "$P_PATCH" ]; then P_KIND="patch"; else P_KIND="manifesto"; fi
  P_FINALIZE="$( _find_finalize "$cer" )"
  P_LAND_ARGS="$( _land_args "$PKG_LAND" )"
  # Rede de segurança: se o LAND fala em --ownership-e2e mas o bloco `# Uso:`
  # não rendeu a flag, injeta o modo escolhido — esquecer a flag é abort.
  case "$P_LAND_ARGS" in
    *--ownership-e2e=*)
      P_LAND_ARGS="$( printf '%s' "$P_LAND_ARGS" | sed "s/--ownership-e2e=[A-Za-z]*/--ownership-e2e=$OWNERSHIP_E2E/" )" ;;
    *)
      if grep -q -F -- '--ownership-e2e' "$PKG_LAND" 2>/dev/null; then
        P_LAND_ARGS="$( printf '%s %s' "$P_LAND_ARGS" "--ownership-e2e=$OWNERSHIP_E2E" | sed 's/^ *//' )"
      fi ;;
  esac
  # Assunto do commit do pacote, para reconhecer um pacote JÁ landado.
  local msg
  for msg in "$cer"/COMMIT-MSG-*.txt; do
    [ -f "$msg" ] || continue
    P_SUBJECT="$( head -1 "$msg" )"
    break
  done
  return 0
}

# Um pacote já landado não pode ser landado de novo. Duas provas independentes:
# o patch reverte limpo (patch-based) OU o assunto do commit já está no log.
_already_landed() {  # <pacote>
  local subj_hits
  if [ "$P_KIND" = "patch" ] && [ -n "$P_PATCH" ] && [ -f "$P_PATCH" ]; then
    if git apply --reverse --check "$P_PATCH" >/dev/null 2>&1; then
      return 0
    fi
  fi
  if [ -n "$P_SUBJECT" ]; then
    subj_hits="$( git log --format=%s -n 200 2>/dev/null | grep -c -F -x -- "$P_SUBJECT" )"
    [ "${subj_hits:-0}" -gt 0 ] && return 0
  fi
  return 1
}

# ---------------------------------------------------------------------------
# 6 — pré-condições globais
# ---------------------------------------------------------------------------
ORACLE=".claude/hooks/check_canonical_edit.py"

# Untracked que a noite deixa para trás de propósito. Um untracked FORA desta
# lista não é motivo de parada — o SIGN de cada pacote é quem decide, com o
# oráculo de canonicidade. Aqui ele só aparece nomeado, para o Owner ver.
_untracked_expected() {  # <path>
  case "$1" in
    .claude/plans/PLAN-183/NIGHT-S328-RUNBOOK.md) return 0 ;;
    .claude/plans/PLAN-185/*|.claude/plans/PLAN-185) return 0 ;;
    .claude/scripts/check-installer-write-safety.py) return 0 ;;
    .claude/scripts/data/*|.claude/scripts/data) return 0 ;;
    .claude/scripts/tests/test_check_installer_write_safety.py) return 0 ;;
    .claude/plans/PLAN-183/s328-ceremony-main/*) return 0 ;;
    *) return 1 ;;
  esac
}

# --- docs/threat-model.md: sujeira que NINGUÉM editou ----------------------
# `.claude/scripts/check-threat-model-freshness.py` reescreve o arquivo como
# EFEITO COLATERAL de rodar: `:188-195` troca `^(\*\*Status:\*\*)\s+accepted`
# por `\1 stale` e sai 1. Medido em clone limpo de 560dad0: sha256
# 44be302b… → 4017fd86…, porcelain ` M docs/threat-model.md`, diff -U0 com
# exatamente uma linha removida e uma adicionada. Como o P0 de TODO SIGN
# recusa árvore com modificação rastreada, essa sujeira aborta a cerimônia
# acusando um arquivo que ninguém tocou.
#
# A cura é PONTUAL e provada por conteúdo: só este path, só quando ele é a
# ÚNICA modificação rastreada, e só quando o diff é exatamente a troca de
# status. Qualquer outra coisa continua sendo motivo de parada — reverter
# arquivo por adivinhação seria destruir trabalho de outra pessoa.
THREAT_MODEL="docs/threat-model.md"

_tm_is_only_status_flip() {
  local ns removed added
  ns="$( git diff --numstat -- "$THREAT_MODEL" \
         | awk '{ n++; a=$1; d=$2 } END { if (n==1) printf "%s/%s", a, d; else printf "many" }' )"
  [ "$ns" = "1/1" ] || return 1
  removed="$( git diff -U0 -- "$THREAT_MODEL" | sed -n 's/^-\([^-].*\)$/\1/p' )"
  added="$(   git diff -U0 -- "$THREAT_MODEL" | sed -n 's/^+\([^+].*\)$/\1/p' )"
  # DIREÇÃO EXATA, não "uma das duas". O checker só escreve num sentido —
  # `flip_status_to_stale` (`check-threat-model-freshness.py:179-200`) aplica
  # `re.sub(r"^(\*\*Status:\*\*)\s+accepted", r"\1 stale", count=1)` e não tem
  # caminho inverso. Aceitar `stale` → `accepted` faria esta função reverter em
  # silêncio a edição de quem RE-ACEITOU o modelo de ameaças de propósito —
  # exatamente o trabalho que a cura existe para não destruir.
  case "$removed" in '**Status:** accepted') : ;; *) return 1 ;; esac
  case "$added"   in '**Status:** stale')    : ;; *) return 1 ;; esac
  return 0
}

TREE_TRACKED_DIRTY=""
TREE_DIRTY_COUNT=0
TREE_TM_XY=""
TREE_HEAL_NOTE=""

_note_dirty() {  # <xy> <path> — registra uma modificação RASTREADA
  TREE_TRACKED_DIRTY="$TREE_TRACKED_DIRTY  $1 $2
"
  TREE_DIRTY_COUNT=$(( TREE_DIRTY_COUNT + 1 ))
  [ "$2" = "$THREAT_MODEL" ] && TREE_TM_XY="$1"
  return 0
}

# Texto extra do abort quando o threat-model está entre os sujos e a cura NÃO
# se aplicou. `git checkout --` só com o Owner reconhecendo que não editou.
_tm_abort_hint() {
  [ -n "$TREE_TM_XY" ] || return 0
  printf '\n  SOBRE %s\n' "$THREAT_MODEL"
  printf '    Esse arquivo costuma ficar sujo sozinho: o checker de frescor\n'
  printf '    (.claude/scripts/check-threat-model-freshness.py) troca o Status\n'
  printf '    de accepted para stale ao rodar. Eu reverto isso sozinho quando o\n'
  printf '    diff é SÓ essa troca de uma linha — aqui não era, então parei.\n'
  printf '    Veja o que mudou de fato:\n'
  printf '      cd %s && git diff -- %s\n' "$ROOT" "$THREAT_MODEL"
  printf '    Se (e SÓ se) você reconhecer que não editou nada ali:\n'
  printf '      cd %s && git checkout -- %s\n' "$ROOT" "$THREAT_MODEL"
}

_tree_check() {  # imprime o estado da árvore; devolve 1 se há modificação RASTREADA
  local entry xy path verdict unexpected="" tolerated=""
  TREE_TRACKED_DIRTY=""
  TREE_DIRTY_COUNT=0
  TREE_TM_XY=""
  TREE_HEAL_NOTE=""
  while IFS= read -r -d '' entry; do
    xy="${entry:0:2}"; path="${entry:3}"
    case "$xy" in
      "??")
        if _untracked_expected "$path"; then
          tolerated="$tolerated  $path
"
        else
          verdict=""
          if [ -f "$ORACLE" ]; then
            verdict="$( python3 "$ORACLE" --is-canonical "$path" 2>/dev/null | awk -F'\t' 'NR==1{print $2}' )"
          fi
          case "$verdict" in
            1) unexpected="$unexpected  $path   \033[31m(CANÔNICO — o SIGN vai recusar)\033[0m
" ;;
            *) unexpected="$unexpected  $path
" ;;
          esac
        fi ;;
      *R*|*C*)
        # rename/copy: o porcelain -z emite o caminho de ORIGEM num registro
        # próprio logo depois — consumir aqui evita lê-lo como se fosse outra
        # entrada.
        IFS= read -r -d '' _from || printf ''
        _note_dirty "$xy" "$path" ;;
      *)
        _note_dirty "$xy" "$path" ;;
    esac
  done < <( git status --porcelain=v1 -z )

  # Cura pontual do docs/threat-model.md (ver o bloco de comentário acima).
  # Só dispara quando ele é a ÚNICA modificação rastreada, está NÃO-staged, e
  # o diff é exatamente a troca de status. Nunca reverte outro arquivo.
  if [ "$TREE_DIRTY_COUNT" = "1" ] && [ "$TREE_TM_XY" = " M" ]; then
    if _tm_is_only_status_flip; then
      if git checkout -- "$THREAT_MODEL" 2>/dev/null; then
        TREE_HEAL_NOTE="revertido"
        TREE_TRACKED_DIRTY=""; TREE_DIRTY_COUNT=0; TREE_TM_XY=""
      else
        TREE_HEAL_NOTE="falha-ao-reverter"
      fi
    else
      TREE_HEAL_NOTE="nao-e-o-flip"
    fi
  fi
  case "$TREE_HEAL_NOTE" in
    revertido)
      warn "$THREAT_MODEL estava modificado e eu REVERTI."
      info "Ninguém editou esse arquivo: quem o reescreve é"
      info "\`.claude/scripts/check-threat-model-freshness.py\`, que troca"
      info "\`**Status:** accepted\` por \`stale\` como efeito colateral de rodar."
      info "Confirmei que o diff era EXATAMENTE essa troca de uma linha, e nada"
      info "mais, antes de reverter. Sem isso o P0 de todo SIGN abortaria"
      info "acusando um arquivo que ninguém tocou." ;;
    nao-e-o-flip)
      warn "$THREAT_MODEL está modificado, mas o diff NÃO é só a troca de status."
      info "NÃO vou reverter: há conteúdo real aí que eu destruiria." ;;
    falha-ao-reverter)
      warn "tentei reverter $THREAT_MODEL e o \`git checkout\` falhou." ;;
  esac

  if [ -n "$tolerated" ]; then
    info "untracked esperados da noite (não entram em commit nenhum):"
    printf '%s' "$tolerated"
  fi
  if [ -n "$unexpected" ]; then
    warn "untracked que eu NÃO esperava — confira se algum deveria ter sido commitado:"
    printf '%b' "$unexpected"
  fi
  [ -z "$TREE_TRACKED_DIRTY" ]
}

# ---------------------------------------------------------------------------
# 7 — execução de um passo (com log próprio e rc preservado)
# ---------------------------------------------------------------------------
STEP_RC=0
STEP_LOG=""
_run() {  # <pacote> <nome-da-etapa> <cmd...>
  local pkg="$1" name="$2"; shift 2
  STEP_LOG="$STEP_LOG_DIR/step-$pkg-$name.log"
  printf '\n  \033[1m$\033[0m %s\n\n' "$*"
  if [ "$DRY_RUN" = "1" ]; then
    printf '      [--dry-run global] não executei nada.\n'
    STEP_RC=0
    return 0
  fi
  "$@" 2>&1 | tee "$STEP_LOG"
  STEP_RC="${PIPESTATUS[0]}"
  return 0
}

# ---------------------------------------------------------------------------
# 8 — resumo (impresso no fim e também em qualquer parada)
# ---------------------------------------------------------------------------
_print_summary() {
  local p
  step "RESUMO"
  for p in $ORDER; do
    printf '  %s  %-58s %s\n' "$p" "$( _pkg_label "$p" )" "$( _get_status "$p" )"
  done
  printf '\n  HEAD agora: %s  (%s)\n' "$( git rev-parse --short HEAD 2>/dev/null || printf '?' )" "$( git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '?' )"
}

# ---------------------------------------------------------------------------
# 9 — a cerimônia de UM pacote
# ---------------------------------------------------------------------------
_pkg_run() {
  local pkg="$1" ec asc
  head1 "PACOTE $( _pkg_label "$pkg" )"

  if ! _pkg_load "$pkg"; then
    _pkg_scripts "$pkg"
    # Um pacote pela METADE (só um dos dois scripts) é um estado real: a noite
    # pode ter caído no meio da montagem. Dizer QUAL falta poupa uma investigação.
    if [ -f "$PKG_SIGN" ] || [ -f "$PKG_LAND" ]; then
      warn "pacote INCOMPLETO — a noite começou a montá-lo e não terminou."
      if [ -f "$PKG_SIGN" ]; then info "presente: $PKG_SIGN"; else info "FALTA   : $PKG_SIGN"; fi
      if [ -f "$PKG_LAND" ]; then info "presente: $PKG_LAND"; else info "FALTA   : $PKG_LAND"; fi
      info "Sem os DOIS scripts não dá para assinar nem landar — pulando."
      _set_status "$pkg" "INCOMPLETO (pulado)"
    else
      warn "pacote AUSENTE — a noite não chegou a montá-lo."
      info "esperado em: $PKG_SIGN"
      info "             $PKG_LAND"
      _set_status "$pkg" "AUSENTE (pulado)"
    fi
    SKIPPED_ANY=1
    if [ "$pkg" = "B" ]; then
      B_MISSING_CI_WARNED=1
      printf '\n'
      warn "SEM O PACOTE B O CI \`Validate\` CONTINUA VERMELHO."
      info "O vermelho é o gate de hook-latency (mede o runner, não os hooks —"
      info "S327/S328). O pacote B PUBLICA a medida que explica esse vermelho,"
      info "mas na fase 1 é advisory: não muda veredito nenhum. Ou seja, ele"
      info "não deixaria o Validate verde nem se tivesse entrado — quem faz"
      info "isso é o rerun de madrugada. Seguindo para o próximo pacote."
    fi
    return 0
  fi

  info "SIGN     : $PKG_SIGN"
  info "LAND     : $PKG_LAND  ${P_LAND_ARGS:-(sem argumentos extras)}"
  info "tipo     : $P_KIND"
  [ -n "$P_CER" ]      && info "materiais: $P_CER"
  [ -n "$P_SENTINEL" ] && info "sentinel : $P_SENTINEL"
  [ -n "$P_FINALIZE" ] && info "finalize : $P_FINALIZE"

  if [ "$FINALIZE_COUNT" -gt 1 ]; then
    ec="$( _exit_code_for "$pkg" 6 )"
    _red "$pkg" "carga" "-" "$ec" \
      "há mais de um finalize-*.sh em $P_CER — não sei qual é o certo." \
      "Não adivinho. Chame o CEO com a lista:" \
      "  ls -la $ROOT/$P_CER/finalize-*.sh"
  fi

  # ---- já landado? --------------------------------------------------------
  if _already_landed "$pkg"; then
    ok "este pacote JÁ está no repositório — nada a fazer."
    [ -n "$P_SUBJECT" ] && info "commit: $P_SUBJECT"
    _set_status "$pkg" "já estava landado"
    _mark_landed "$pkg"
    return 0
  fi

  # ---- dependências (só C tem) -------------------------------------------
  if [ "$pkg" = "C" ]; then
    if ! _is_landed A || ! _is_landed B; then
      local falta=""
      _is_landed B || falta="B"
      _is_landed A || falta="${falta:+$falta e }A"
      warn "PACOTE C NÃO RODA: o pacote $falta não está no repositório."
      info "O C mexe nos MESMOS arquivos de A e de B (validate.yml, install.sh)."
      info "Assinar C sobre uma árvore sem eles produziria um patch que não"
      info "aplica — ou, pior, um que aplica no lugar errado."
      info "Quando A e B estiverem landados, rode:  $( _resume_cmd C )"
      _set_status "$pkg" "PULADO (falta o pacote $falta)"
      SKIPPED_ANY=1
      return 0
    fi
  fi

  # ---- árvore limpa -------------------------------------------------------
  step "[$pkg] 1/5 — estado da árvore"
  if ! _tree_check; then
    ec="$( _exit_code_for "$pkg" 6 )"
    printf '%s' "$TREE_TRACKED_DIRTY"
    _tm_abort_hint
    _red "$pkg" "árvore" "-" "$ec" \
      "há modificações RASTREADAS na árvore (as linhas acima)." \
      "Assinar com a árvore suja produz uma âncora que não descreve o que" \
      "será landado — o SIGN recusaria de todo jeito." \
      "Isto NÃO é para você resolver sozinho: chame o CEO com a lista acima."
  fi
  ok "nenhuma modificação rastreada"

  asc=""
  [ -n "$P_SENTINEL" ] && asc="$P_SENTINEL.asc"

  # ---- 2/5 finalize + 3/5 SIGN (ou pulados, se já assinado) --------------
  if [ -n "$asc" ] && [ -f "$asc" ]; then
    step "[$pkg] 2/5 e 3/5 — finalize e SIGN"
    ok "o sentinel JÁ está assinado ($asc) — pulando os dois."
    info "re-finalizar reescreveria o sentinel e invalidaria a assinatura."
  else
    if [ -n "$P_SENTINEL" ] && [ "$P_KIND" = "manifesto" ] && [ -f "$P_SENTINEL" ]; then
      # O SIGN de pacote-manifesto materializa o sentinel a partir do draft e
      # PERGUNTA antes de regerar um que já exista. Com o stdout em pipe essa
      # pergunta ficaria invisível e o script pareceria travado.
      ec="$( _exit_code_for "$pkg" 6 )"
      _red "$pkg" "estado do sentinel" "-" "$ec" \
        "existe $P_SENTINEL mas não existe a assinatura $asc." \
        "O SIGN abriria uma pergunta interativa que ficaria invisível aqui." \
        "Apague o sentinel não assinado e retome — o SIGN o recria do draft:" \
        "  rm $ROOT/$P_SENTINEL"
    fi

    step "[$pkg] 2/5 — re-base do pacote no HEAD vivo (finalize)"
    if [ -z "$P_FINALIZE" ]; then
      ok "este pacote não tem finalize (é $P_KIND) — nada a re-basear."
      if [ "$P_KIND" = "manifesto" ]; then
        info "o frescor dele é o BASELINE.sha256, conferido dentro do SIGN."
      fi
    else
      # Rodar SEMPRE: o próprio finalize compara BASE-SHA.txt com o HEAD e sai
      # dizendo 'NADA a fazer' quando já está no lugar. Decidir aqui por conta
      # própria duplicaria essa comparação — e duas cópias divergem.
      _run "$pkg" finalize bash "$P_FINALIZE"
      if [ "$STEP_RC" -ne 0 ]; then
        ec="$( _exit_code_for "$pkg" 1 )"
        _red "$pkg" "finalize" "$STEP_RC" "$ec" \
          "o re-base do pacote falhou — leia a mensagem do script acima." \
          "Causa mais comum: o patch não re-aplica porque alguém editou os" \
          "mesmos arquivos depois que o pacote foi montado." \
          "NÃO force nada. Copie a saída inteira e mande para o CEO." \
          "Log desta etapa: ${STEP_LOG:-<sem log>}"
      fi
      ok "pacote baseado no HEAD vivo"
    fi

    step "[$pkg] 3/5 — assinatura do sentinel (GPG)"
    info "o script vai pedir a senha da sua chave. Digite e dê Enter."
    _run "$pkg" sign bash "$PKG_SIGN"
    if [ "$STEP_RC" -ne 0 ]; then
      # "No pinentry" é o modo de falha conhecido deste setup. Uma retentativa,
      # e só uma: se falhar de novo, o problema não é o agente do GPG.
      # `grep -c` IMPRIME "0" e sai 1 quando não casa — um `|| printf 0` aqui
      # concatenaria um segundo zero e a comparação numérica explodiria.
      local pin=""
      if [ -n "${STEP_LOG:-}" ] && [ -f "$STEP_LOG" ]; then
        pin="$( grep -c -i -- 'pinentry' "$STEP_LOG" 2>/dev/null )"
      fi
      case "${pin:-0}" in ''|*[!0-9]*) pin=0 ;; esac
      if [ "$pin" -gt 0 ]; then
        warn "falha de pinentry — reiniciando o agente do GPG e tentando UMA vez mais."
        gpgconf --kill gpg-agent >/dev/null 2>&1 || printf ''
        GPG_TTY="$( tty 2>/dev/null || printf '' )"; export GPG_TTY
        _run "$pkg" sign-retry bash "$PKG_SIGN"
      fi
    fi
    if [ "$STEP_RC" -ne 0 ]; then
      ec="$( _exit_code_for "$pkg" 2 )"
      _red "$pkg" "SIGN" "$STEP_RC" "$ec" \
        "a assinatura do sentinel falhou — nada foi aplicado." \
        "Se a mensagem falar em \"No pinentry\", rode no SEU terminal:" \
        "  export GPG_TTY=\$(tty); gpgconf --kill gpg-agent" \
        "e depois retome com o comando abaixo." \
        "Qualquer outra mensagem: o script já restaurou o sentinel sozinho;" \
        "copie a saída inteira e mande para o CEO." \
        "Log desta etapa: ${STEP_LOG:-<sem log>}"
    fi
    ok "sentinel assinado"
  fi

  # ---- 4/5 LAND --dry-run -------------------------------------------------
  step "[$pkg] 4/5 — ensaio do land (--dry-run: não altera nada em definitivo)"
  # shellcheck disable=SC2086  # P_LAND_ARGS é derivado do próprio LAND e não tem espaços nos valores
  _run "$pkg" land-dry bash "$PKG_LAND" --dry-run $P_LAND_ARGS
  if [ "$STEP_RC" -ne 0 ]; then
    ec="$( _exit_code_for "$pkg" 3 )"
    _red "$pkg" "LAND --dry-run" "$STEP_RC" "$ec" \
      "o ensaio do land reprovou — NADA foi commitado nem empurrado." \
      "O ensaio roda todos os portões e a bateria de verificação e depois" \
      "desfaz tudo. Reprovar aqui significa que o land de verdade também" \
      "reprovaria — e é exatamente para isso que o ensaio existe." \
      "Se a saída falar em RESTAURAÇÃO INCOMPLETA: pare tudo e chame o CEO." \
      "Log desta etapa: ${STEP_LOG:-<sem log>}"
  fi
  ok "ensaio verde"

  # ---- 5/5 LAND de verdade ------------------------------------------------
  step "[$pkg] 5/5 — land de verdade (aplica, commita e empurra)"
  case "$P_LAND_ARGS" in
    *--ownership-e2e=run*)
      info "este land inclui o e2e de ownership (~25 min). Não interrompa." ;;
    *--ownership-e2e=defer*)
      info "e2e de ownership adiado (defer): quem confirma é o nightly de"
      info "ownership do CI, com o conjunto RED exato. Veja o fim desta saída." ;;
  esac
  # shellcheck disable=SC2086  # ver acima
  _run "$pkg" land bash "$PKG_LAND" $P_LAND_ARGS
  if [ "$STEP_RC" -ne 0 ]; then
    ec="$( _exit_code_for "$pkg" 4 )"
    _red "$pkg" "LAND" "$STEP_RC" "$ec" \
      "o land falhou. O script restaura a árvore ao abortar — mas CONFIRME:" \
      "  cd $ROOT && git status --short" \
      "Se aparecer qualquer coisa modificada, pare e chame o CEO." \
      "Se o land chegou a commitar e falhou DEPOIS, a mensagem diz isso com" \
      "todas as letras — nesse caso NÃO rode nada, chame o CEO." \
      "Log desta etapa: ${STEP_LOG:-<sem log>}"
  fi

  if [ "$DRY_RUN" = "1" ]; then
    _set_status "$pkg" "ENSAIO (--dry-run): rodaria os 5 passos"
    _mark_landed "$pkg"   # para o ensaio mostrar a ordem real de dependências
    return 0
  fi

  # ---- confere o push -----------------------------------------------------
  step "[$pkg] pós-land — o commit chegou no origin?"
  local sha sb ahead upstream
  sha="$( git rev-parse --short HEAD 2>/dev/null || printf '?' )"
  upstream="$( git rev-parse --abbrev-ref '@{u}' 2>/dev/null || printf '' )"
  sb="$( git status -sb 2>/dev/null | head -1 )"
  info "$sb"
  if [ -z "$upstream" ]; then
    warn "este checkout não tem upstream configurado — não dá para conferir o push aqui."
  else
    ahead=""
    case "$sb" in
      *"[ahead "*) ahead="sim" ;;
    esac
    if [ -n "$ahead" ]; then
      ec="$( _exit_code_for "$pkg" 5 )"
      _red "$pkg" "pós-land" "-" "$ec" \
        "o commit foi criado mas NÃO chegou no origin ($sb)." \
        "O land empurra sozinho; se ficou 'ahead', o push falhou (rede, ou" \
        "alguém empurrou antes). NÃO force. Chame o CEO — ele decide entre" \
        "empurrar de novo e refazer o pacote sobre o novo HEAD."
    fi
    ok "em dia com $upstream"
  fi
  ok "LANDADO — $sha"
  _set_status "$pkg" "LANDADO ($sha)"
  _mark_landed "$pkg"
  return 0
}

# ---------------------------------------------------------------------------
# 10 — plano da manhã
# ---------------------------------------------------------------------------
head1 "S328 — CERIMÔNIA DA MANHÃ"
say ""
info "data      : $( date '+%Y-%m-%d %H:%M:%S %Z' )"
info "repo      : $ROOT"
info "branch    : $( git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '?' )"
info "HEAD      : $( git rev-parse --short HEAD 2>/dev/null || printf '?' ) — $( git log -1 --format=%s 2>/dev/null | cut -c1-70 )"
info "ordem     : B → A → C → D"
info "ownership : --ownership-e2e=$OWNERSHIP_E2E"
[ "$DRY_RUN" = "1" ] && info "modo      : --dry-run GLOBAL (não executo nada; só mostro o que faria)"
[ -n "$FROM" ]       && info "retomada  : começando no pacote $FROM"
[ -n "$ONLY" ]       && info "escopo    : SÓ o pacote $ONLY"
say ""

_cur_branch="$( git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '' )"
if [ "$_cur_branch" != "main" ]; then
  printf '\n\033[31mABORT:\033[0m o checkout está em "%s", não em "main".\n' "$_cur_branch" >&2
  printf '  A cerimônia só roda no main. Chame o CEO.\n' >&2
  exit 3
fi

step "PACOTES ENCONTRADOS"
for _p in $ORDER; do
  if _pkg_load "$_p"; then
    _extra="$P_KIND"
    [ -n "$P_LAND_ARGS" ] && _extra="$_extra, LAND $P_LAND_ARGS"
    if _already_landed "$_p"; then _extra="$_extra, JÁ LANDADO"
    elif [ -n "$P_SENTINEL" ] && [ -f "$P_SENTINEL.asc" ]; then _extra="$_extra, já assinado"
    fi
    printf '  \033[32m✓\033[0m %s  %s   (%s)\n' "$_p" "$( _pkg_label "$_p" )" "$_extra"
  else
    # _pkg_load já chamou _pkg_scripts: PKG_SIGN/PKG_LAND valem mesmo no ausente.
    _why="ausente"
    if [ -f "$PKG_SIGN" ] || [ -f "$PKG_LAND" ]; then _why="INCOMPLETO — só um dos dois scripts"; fi
    printf '  \033[33m—\033[0m %s  %s   (%s)\n' "$_p" "$( _pkg_label "$_p" )" "$_why"
  fi
done

step "ÁRVORE DE TRABALHO"
if _tree_check; then
  ok "nenhuma modificação rastreada"
else
  printf '%s' "$TREE_TRACKED_DIRTY"
  _tm_abort_hint
  printf '\n\033[31mABORT:\033[0m há modificações RASTREADAS na árvore (linhas acima).\n' >&2
  printf '  Nenhum pacote pode ser assinado assim: a âncora da assinatura não\n' >&2
  printf '  descreveria o que será landado. Chame o CEO com a lista acima.\n' >&2
  exit 3
fi

# ---------------------------------------------------------------------------
# 11 — execução
# ---------------------------------------------------------------------------
RUN_LIST=""
if [ -n "$ONLY" ]; then
  RUN_LIST="$ONLY"
else
  _started=0
  for _p in $ORDER; do
    if [ -z "$FROM" ] || [ "$_started" = "1" ] || [ "$_p" = "$FROM" ]; then
      _started=1
      RUN_LIST="$RUN_LIST $_p"
    else
      # Pacote anterior ao --from: não roda, mas o estado dele no repositório
      # ainda conta para a dependência do C.
      if _pkg_load "$_p" && _already_landed "$_p"; then
        _mark_landed "$_p"
        _set_status "$_p" "já estava landado (antes do --from)"
      else
        _set_status "$_p" "pulado por --from $FROM"
        SKIPPED_ANY=1
      fi
    fi
  done
fi
if [ -n "$ONLY" ]; then
  for _p in $ORDER; do
    [ "$_p" = "$ONLY" ] && continue
    if _pkg_load "$_p" && _already_landed "$_p"; then
      _mark_landed "$_p"
      _set_status "$_p" "já estava landado (fora do --only)"
    else
      _set_status "$_p" "fora do --only $ONLY"
      SKIPPED_ANY=1
    fi
  done
fi

for _p in $RUN_LIST; do
  _pkg_run "$_p"
done

# ---------------------------------------------------------------------------
# 12 — CI
# ---------------------------------------------------------------------------
head1 "CI — O QUE ESPERAR AGORA"

step "runs recentes"
if command -v gh >/dev/null 2>&1; then
  gh run list --limit 8 || warn "gh falhou (rede? autenticação?) — abra o GitHub no navegador."
else
  warn "o \`gh\` não está instalado aqui — veja os runs no GitHub, aba Actions."
fi

# O conjunto RED do nightly de ownership é DECLARADO pelos pacotes, não
# lembrado: sai do EXPECTED-BASELINE.txt de quem o declarar.
RED_IDS=""; RED_SRC=""
for _p in $ORDER; do
  if _pkg_load "$_p" && [ -n "$P_CER" ] && [ -f "$P_CER/EXPECTED-BASELINE.txt" ]; then
    _v="$( awk -F= '/^EXPECTED_OWNERSHIP_RED_IDS=/{ v=$2; gsub(/^"|"$/,"",v); print v; exit }' "$P_CER/EXPECTED-BASELINE.txt" )"
    if [ -n "$_v" ]; then RED_IDS="$_v"; RED_SRC="$P_CER/EXPECTED-BASELINE.txt"; break; fi
  fi
done

step "baseline esperado"
# O pacote B NÃO deixa o Validate verde, e dizer que deixa daria ao Owner a
# expectativa operacional oposta à verdade. O próprio pacote declara isso:
# `PLAN-169/s328-ceremony-B/README-B.md:93-97` ("Ele não deixa o `Validate`
# verde") e `EXPECTED-BASELINE.txt` com `EXPECTED_VBLOCK_RUN_PHASE="1-advisory"`.
# A fase 1 PUBLICA a métrica relativa e preserva os vereditos/exit codes de
# hoje; o verde vem do rerun de madrugada, ou da fase 2 com o K calibrado.
if [ "$B_MISSING_CI_WARNED" = "1" ] || ! _is_landed B; then
  printf '  \033[33mValidate\033[0m       CONTINUA VERMELHO. O pacote B não entrou — mas atenção:\n'
  printf '                   mesmo COM o B ele não ficaria verde sozinho (veja abaixo).\n'
else
  printf '  \033[33mValidate\033[0m       ainda pode reprovar, e isso NÃO é regressão do land.\n'
  printf '                   O pacote B entrou em FASE 1 (advisory): ele publica a\n'
  printf '                   medida nova e mantém os vereditos de hoje — de propósito,\n'
  printf '                   porque fixar o limiar sem dados seria inventar um número.\n'
fi
printf '                   Quem deixa o Validate verde é o RERUN de madrugada (03:03),\n'
printf '                   ou a fase 2, com o K calibrado depois de ≥10 execuções.\n'
printf '                   O vermelho do gate mede a velocidade do runner do CI,\n'
printf '                   não o seu código.\n'
printf '  \033[32mSmoke Install\033[0m  esperado VERDE.\n'
if [ -n "$RED_IDS" ]; then
  printf '  \033[32mownership\033[0m      nightly (~07:00Z): conjunto RED EXATO { %s }.\n' "$RED_IDS"
  printf '                   declarado em %s\n' "$RED_SRC"
else
  printf '  \033[33mownership\033[0m      nenhum pacote declarou EXPECTED_OWNERSHIP_RED_IDS —\n'
  printf '                   confira o conjunto RED com o CEO antes de aceitar o run.\n'
fi
printf '                   Um nightly TODO VERDE é sinal de PARADA, não de sucesso:\n'
printf '                   significa que a tabela-verdade mudou sem ninguém decidir.\n'

# ---------------------------------------------------------------------------
# 13 — fecho
# ---------------------------------------------------------------------------
_print_summary

FINAL=0
if [ "$SKIPPED_ANY" = "1" ]; then FINAL=7; fi

step "FIM"
if [ "$DRY_RUN" = "1" ]; then
  say "  Isto foi um ENSAIO (--dry-run): nada foi assinado, aplicado ou empurrado."
  say "  Para valer, rode a mesma linha SEM --dry-run."
elif [ "$FINAL" = "0" ]; then
  say "  Tudo que existia foi landado. Nada mais a fazer nesta manhã."
else
  say "  Nenhum vermelho — mas nem todos os pacotes rodaram (veja o resumo acima)."
  say "  Isso é esperado quando a noite não chegou a montar algum pacote."
fi
[ -n "$LOG_FILE" ] && say "  Log completo: $LOG_FILE"
say ""
exit "$FINAL"
