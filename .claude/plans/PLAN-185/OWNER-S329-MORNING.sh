#!/usr/bin/env bash
# OWNER-S329-MORNING.sh — o ÚNICO comando da manhã da night-run S329.
# CEREMONY-LINT: handwritten-exception: orquestrador da manhã — compõe scripts gerados/clonados, não substitui nenhum
#
# O QUE ELE FAZ
#   Roda, na ordem C -> E, a cerimônia de cada pacote que EXISTIR:
#     finalize (re-base no HEAD vivo) -> SIGN (GPG) -> LAND --dry-run -> LAND
#     -> confere que o push aconteceu
#   Para no PRIMEIRO vermelho, com diagnóstico e o comando exato de retomada.
#
# O QUE ELE NÃO FAZ
#   Não commita, não empurra, não assina, não aplica patch. Quem faz isso são
#   os scripts de cada pacote — este arquivo só decide QUEM roda, em QUE ordem,
#   e QUANDO parar. Nenhum editor abre em momento nenhum.
#
# POR QUE A ORDEM É C -> E
#   Não é dependência: nenhum dos dois precisa do outro para aplicar. É que o
#   C mexe no `scripts/install.sh` e o E no `scripts/upgrade.sh` mais o
#   `.github/workflows/smoke-install.yml` — e o `finalize` de cada pacote
#   re-baseia o patch no HEAD do momento. Rodar C primeiro e SÓ ENTÃO
#   finalizar o E significa que, se os dois tocarem um arquivo em comum, o E
#   já nasce baseado no resultado do C. A ordem inversa daria o mesmo
#   resultado com um re-base a mais.
#   O pacote D (PLAN-179 W2+W4) NÃO está nesta lista: ele foi assinado pelo
#   Owner e landado pela própria noite (`b07be9b`). Não há o que fazer com ele
#   de manhã.
#
# DESCOBERTA EM RUNTIME, NUNCA POR SUPOSIÇÃO
#   Um pacote pode não existir (a noite pode não ter chegado nele). Presença,
#   tipo (patch ou manifesto), sentinel, patch, script de finalize e argumentos
#   do LAND são todos DERIVADOS dos scripts reais de cada pacote — do bloco de
#   constantes e do bloco `# Uso:` deles. Nada aqui é lembrado de cabeça.
#
# POR QUE NÃO EXISTE UM `--phase`
#   Seria uma forma de pular o ensaio (`--dry-run`) e ir direto ao land — o
#   único gate barato que existe antes do caro. E não resolve nada: retomar
#   com `--from` já pula sozinho o que estava feito, porque o script detecta o
#   sentinel JÁ assinado (`.asc` no disco) e não re-assina. Ensaio de novo
#   custa menos de um minuto; assinar errado custa a manhã inteira.
#
# USO
#   bash .claude/plans/PLAN-185/OWNER-S329-MORNING.sh
#   bash .claude/plans/PLAN-185/OWNER-S329-MORNING.sh --dry-run
#   bash .claude/plans/PLAN-185/OWNER-S329-MORNING.sh --from E
#   bash .claude/plans/PLAN-185/OWNER-S329-MORNING.sh --only C
#   bash .claude/plans/PLAN-185/OWNER-S329-MORNING.sh --ownership-e2e=run
#
# CÓDIGOS DE SAÍDA (distintos por etapa — o número diz onde parou)
#    0  tudo que existia foi landado
#    2  erro de uso (argumento desconhecido ou inválido)
#    3  pré-condição global (não é repo git, não está em `main`, atrás do
#       origin, árvore suja)
#    7  terminou SEM vermelho, mas nem tudo rodou (pacote ausente, pela metade,
#       ou sem revisão cruzada aprovada — todos PULADOS com aviso, não erros)
#   1X  pacote C    2X  pacote E
#       X1 finalize · X2 SIGN (inclui GPG indisponível) · X3 LAND --dry-run
#       X4 LAND · X5 pós-land · X6 anomalia de estado do pacote
#
# POR QUE `set -uo pipefail` E NÃO `set -euo pipefail`
#   Este script não é um script de trabalho: é um CLASSIFICADOR de falhas dos
#   outros. Sob `-e` ele morreria no primeiro rc≠0 de qualquer auxiliar — e
#   rc≠0 é justamente o valor que `_tree_check`, `_already_landed` e `_run`
#   DEVOLVEM para dizer o que encontraram. Com `-e` o Owner veria o shell sair
#   em silêncio, sem diagnóstico, sem comando de retomada e sem resumo, no
#   exato momento em que mais precisa dos três. Cada falha aqui é tratada
#   explicitamente e sai por `_red`, com código próprio.
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
ORDER="C E"
# Os argumentos ORIGINAIS, guardados ANTES do parser: o bloco do `tee` re-executa
# este script e `"$@"` já teria sido consumido pelos `shift` daqui de baixo —
# o filho nasceria sem `--dry-run`, sem `--from`, sem `--only`.
ORIG_ARGS=( "$@" )
DRY_RUN=0
FROM=""
ONLY=""
OWNERSHIP_E2E="defer"
OWNERSHIP_E2E_EXPLICIT=0

# O texto da ajuda é o próprio cabeçalho: da linha 2 até o primeiro não-comentário.
# Faixa DERIVADA e não um par de números — um bloco a mais no cabeçalho não pode
# fazer a ajuda truncar no meio nem vazar o `set -uo pipefail` para a tela.
_usage() {
  awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$SCRIPT_PATH" \
    | sed '/CEREMONY-LINT/d'
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --help|-h) _usage; exit 0 ;;
    --dry-run) DRY_RUN=1 ;;
    --from)
      shift
      FROM="${1:-}"
      [ -n "$FROM" ] || { printf '\033[31mABORT:\033[0m --from exige um pacote (C|E)\n' >&2; exit 2; } ;;
    --from=*) FROM="${1#--from=}" ;;
    --only)
      shift
      ONLY="${1:-}"
      [ -n "$ONLY" ] || { printf '\033[31mABORT:\033[0m --only exige um pacote (C|E)\n' >&2; exit 2; } ;;
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
  printf '\033[31mABORT:\033[0m --from %s: pacote desconhecido (use C ou E)\n' "$FROM" >&2; exit 2
fi
if [ -n "$ONLY" ] && ! _valid_pkg "$ONLY"; then
  printf '\033[31mABORT:\033[0m --only %s: pacote desconhecido (use C ou E)\n' "$ONLY" >&2; exit 2
fi
if [ -n "$FROM" ] && [ -n "$ONLY" ]; then
  printf '\033[31mABORT:\033[0m --from e --only são mutuamente exclusivos\n' >&2; exit 2
fi

# ---------------------------------------------------------------------------
# 2 — log completo desta execução (tee); o rc do script é preservado
# ---------------------------------------------------------------------------
LOG_DIR="$ROOT/.claude/plans/PLAN-185/s329-ceremony-main"
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

# Aviso GRANDE, para o que o Owner não pode deixar passar rolando a tela.
bigwarn() {
  printf '\n\033[33m------------------------------------------------------------------------\033[0m\n'
  printf '\033[33mATENÇÃO\033[0m %s\n' "$1"
  printf '\033[33m------------------------------------------------------------------------\033[0m\n'
}

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
ST_C="não avaliado"; ST_E="não avaliado"
LANDED_C=0; LANDED_E=0
SKIPPED_ANY=0

_set_status() { case "$1" in C) ST_C="$2";; E) ST_E="$2";; esac; }
_get_status() { case "$1" in C) printf '%s' "$ST_C";; E) printf '%s' "$ST_E";; esac; }
_mark_landed() { case "$1" in C) LANDED_C=1;; E) LANDED_E=1;; esac; }
_is_landed()   { case "$1" in C) [ "$LANDED_C" = 1 ];; E) [ "$LANDED_E" = 1 ];; *) return 1;; esac; }

_exit_code_for() {  # <pacote> <offset 1..7>
  local base
  case "$1" in C) base=10 ;; E) base=20 ;; *) base=90 ;; esac
  printf '%s' "$(( base + $2 ))"
}

# Os DOIS scripts de cada pacote. É o único par de caminhos que este
# orquestrador precisa saber de antemão — tudo o mais sai de dentro deles.
PKG_SIGN=""; PKG_LAND=""; PKG_PLAN=""
_pkg_scripts() {
  case "$1" in
    C) PKG_PLAN=".claude/plans/PLAN-185"
       PKG_SIGN="$PKG_PLAN/OWNER-S329-C-SIGN.sh"
       PKG_LAND="$PKG_PLAN/OWNER-S329-C-LAND.sh" ;;
    E) PKG_PLAN=".claude/plans/PLAN-169"
       PKG_SIGN="$PKG_PLAN/OWNER-S329-E-SIGN.sh"
       PKG_LAND="$PKG_PLAN/OWNER-S329-E-LAND.sh" ;;
  esac
}

_pkg_label() {
  case "$1" in
    C) printf 'C (PLAN-185 W1+W2 — instalador: symlink e handle do GitHub)' ;;
    E) printf 'E (PLAN-169 — upgrade.sh: registro de hooks derivado)' ;;
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

# --- registros de revisão cruzada (pair-rail) ------------------------------
# Espelho EXATO do P0-e do SIGN (`OWNER-S329-E-SIGN.sh:201-231`): mesma
# descoberta por glob, mesma extração NUMÉRICA do N e mesmo parser do
# veredito. Está aqui por UMA razão prática: o SIGN roda DEPOIS do finalize, e
# o finalize reescreve o patch e o sentinel. Abortar no SIGN por um rail que
# não é APPROVE deixaria a árvore já re-baseada. Isto pergunta a mesma coisa
# antes de qualquer escrita — não é uma segunda autoridade, é a mesma pergunta
# feita mais cedo.
#
# UM RAIL QUE NÃO APROVOU **PULA** O PACOTE, NÃO PARA A MANHÃ.
#   Um vermelho de etapa é transitório: o Owner conserta e retoma. Um rail em
#   REJECT não é — repetir o comando bate na MESMA parede, porque o que falta é
#   trabalho, não sorte. Tratá-lo como vermelho imprimiria um `--from` que não
#   pode funcionar E ainda deixaria de landar o OUTRO pacote, que pode estar
#   aprovado e pronto. Um pacote sem APPROVE é, para esta manhã, exatamente o
#   que é um pacote ausente: não-assinável hoje. Aviso grande, pula, segue.
RAIL_COUNT=0; RAIL_LAST=""; RAIL_LAST_N=-1; RAIL_BAD=""
_rail_scan() {  # <ceremony dir>
  local d="$1" r b n
  RAIL_COUNT=0; RAIL_LAST=""; RAIL_LAST_N=-1; RAIL_BAD=""
  [ -d "$d" ] || return 0
  for r in "$d"/rail-round-*.md; do
    [ -f "$r" ] || continue
    b="$( basename "$r" )"
    n="${b#rail-round-}"; n="${n%.md}"
    case "$n" in
      ''|*[!0-9]*) RAIL_BAD="$RAIL_BAD  $r
"; continue ;;
    esac
    RAIL_COUNT=$(( RAIL_COUNT + 1 ))
    # Comparação NUMÉRICA, nunca por ordem de nome: lexicograficamente
    # `rail-round-10` vem ANTES de `rail-round-2`, e o veredito lido seria o
    # da rodada errada.
    if [ "$n" -gt "$RAIL_LAST_N" ]; then RAIL_LAST_N="$n"; RAIL_LAST="$r"; fi
  done
}
_rail_verdict() {  # <arquivo do rail>
  grep -m1 '^Rail-Verdict:' "$1" 2>/dev/null | sed 's/^[^:]*: *//' | tr -d '[:space:]'
}

# Devolve 0 se o pacote é assinável; 1 se não é (já tendo avisado em voz alta).
RAIL_SKIP_SHORT=""
_rail_gate() {  # <pacote> — usa P_CER
  local pkg="$1" verdict
  RAIL_SKIP_SHORT=""
  _rail_scan "$P_CER"
  if [ -n "$RAIL_BAD" ]; then
    bigwarn "pacote $pkg PULADO: registro de revisão com número inválido no nome."
    printf '%s' "$RAIL_BAD"
    info "Sem um número eu não sei qual é a ÚLTIMA rodada — e é o veredito DELA"
    info "que decide se o pacote pode ser assinado. O SIGN pararia aqui também."
    info "Correção (do CEO, não sua): renomear para rail-round-<N>.md."
    RAIL_SKIP_SHORT="registro de revisão com nome inválido"
    return 1
  fi
  if [ "$RAIL_COUNT" -eq 0 ]; then
    bigwarn "pacote $pkg PULADO: nenhuma revisão cruzada foi registrada."
    info "Procurei em: $P_CER/rail-round-*.md"
    info "O protocolo exige pelo menos uma rodada registrada antes de assinar."
    info "Isto NÃO se resolve repetindo o comando: falta rodar a revisão."
    info "Avise o CEO. Sigo para o próximo pacote."
    RAIL_SKIP_SHORT="sem revisão cruzada registrada"
    return 1
  fi
  verdict="$( _rail_verdict "$RAIL_LAST" )"
  if [ -z "$verdict" ]; then
    bigwarn "pacote $pkg PULADO: a última revisão não tem veredito legível."
    info "Registro: $RAIL_LAST"
    info "Falta nele uma linha começando por \`Rail-Verdict:\`. Sem veredito não"
    info "dá para saber se a revisão aprovou — e eu não assino no escuro."
    info "Avise o CEO. Sigo para o próximo pacote."
    RAIL_SKIP_SHORT="veredito de revisão ilegível"
    return 1
  fi
  if [ "$verdict" != "APPROVE" ]; then
    bigwarn "pacote $pkg PULADO: a revisão cruzada NÃO aprovou."
    info "A última rodada registrada terminou em \`$verdict\`, não em APPROVE."
    info "Registro: $ROOT/$RAIL_LAST"
    info "Assinar agora colocaria no repositório um trabalho que a própria"
    info "revisão recusa. Por isso eu nem re-baseio o pacote."
    info "Isto NÃO se resolve repetindo o comando: faltam curas e uma rodada"
    info "nova, e isso é trabalho do CEO — não seu. Avise-o."
    info "Sigo para o próximo pacote: um pacote reprovado não segura os outros."
    RAIL_SKIP_SHORT="revisão cruzada em $verdict"
    return 1
  fi
  ok "revisão cruzada: $RAIL_COUNT rodada(s); a última ($( basename "$RAIL_LAST" )) é APPROVE"
  return 0
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
  # patch-based; quem não declara é manifesto.
  if [ -n "$P_PATCH" ]; then P_KIND="patch"; else P_KIND="manifesto"; fi
  P_FINALIZE="$( _find_finalize "$cer" )"
  P_LAND_ARGS="$( _land_args "$PKG_LAND" )"
  # Rede de segurança: se o LAND fala em --ownership-e2e mas o bloco `# Uso:`
  # não rendeu a flag, injeta o modo escolhido — esquecer a flag é abort.
  case "$P_LAND_ARGS" in
    *--ownership-e2e=*)
      P_LAND_ARGS="$( printf '%s' "$P_LAND_ARGS" | sed "s/--ownership-e2e=[A-Za-z]*/--ownership-e2e=$OWNERSHIP_E2E/" )" ;;
    *)
      # `grep -c` sobre ARQUIVO (nunca `-q` no fim de um pipe: sob pipefail o
      # SIGPIPE mata o produtor e o rc vira 141). Ele IMPRIME "0" e sai 1 quando
      # não casa — por isso o valor é capturado e higienizado antes da comparação.
      local own_hits
      own_hits="$( grep -c -F -- '--ownership-e2e' "$PKG_LAND" 2>/dev/null )"
      case "${own_hits:-0}" in ''|*[!0-9]*) own_hits=0 ;; esac
      if [ "$own_hits" -gt 0 ]; then
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

# Um pacote já landado não pode ser landado de novo. TRÊS provas independentes,
# qualquer uma basta:
#   (a) a assinatura está RASTREADA no git — só o LAND commita o `.asc`; a
#       noite nunca o faz, porque só o Owner assina;
#   (b) o patch reverte limpo sobre a árvore (patch-based);
#   (c) o assunto do commit do pacote já está no log recente.
#
# QUAL delas respondeu fica registrado em LANDED_PROOF e é IMPRESSO. Um "já
# está landado" errado pula o pacote em silêncio — e um pulo silencioso é a
# falha mais cara desta manhã, porque nada mais nesta execução vai contradizê-lo.
# Dizendo por que ele acha isso, o erro fica diagnosticável em vez de invisível.
LANDED_PROOF=""
_already_landed() {  # <pacote>
  local subj_hits
  LANDED_PROOF=""
  if [ -n "$P_SENTINEL" ]; then
    if git ls-files --error-unmatch -- "$P_SENTINEL.asc" >/dev/null 2>&1; then
      LANDED_PROOF="a assinatura $P_SENTINEL.asc está commitada (só o LAND a commita)"
      return 0
    fi
  fi
  if [ "$P_KIND" = "patch" ] && [ -n "$P_PATCH" ] && [ -f "$P_PATCH" ]; then
    if git apply --reverse --check "$P_PATCH" >/dev/null 2>&1; then
      LANDED_PROOF="o patch já está aplicado na árvore (reverte limpo)"
      return 0
    fi
  fi
  if [ -n "$P_SUBJECT" ]; then
    subj_hits="$( git log --format=%s -n 200 2>/dev/null | grep -c -F -x -- "$P_SUBJECT" )"
    if [ "${subj_hits:-0}" -gt 0 ]; then
      LANDED_PROOF="o commit deste pacote está no histórico"
      return 0
    fi
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
    .claude/plans/PLAN-185/NIGHT-S329-RUNBOOK.md) return 0 ;;
    .claude/plans/PLAN-185/s329-ceremony-main/*) return 0 ;;
    .claude/plans/PLAN-183/NIGHT-S328-RUNBOOK.md) return 0 ;;
    .claude/plans/PLAN-183/s328-ceremony-main/*) return 0 ;;
    *) return 1 ;;
  esac
}

# --- GPG: disponível e com chave secreta -----------------------------------
# Só o SIGN precisa disto — e um pacote já assinado não precisa nem dele. Por
# isso aqui é MEDIÇÃO e aviso; a parada acontece no pacote, na hora de assinar,
# com o código do passo SIGN. Abortar no preflight puniria uma manhã em que os
# dois pacotes já estivessem assinados.
GPG_OK=0
GPG_WHY=""
_gpg_probe() {
  local secs n
  if ! command -v gpg >/dev/null 2>&1; then
    GPG_OK=0; GPG_WHY="o programa \`gpg\` não está instalado nesta máquina (ou não está no PATH)"
    return 0
  fi
  secs="$( gpg --list-secret-keys --with-colons 2>/dev/null )"
  n="$( printf '%s\n' "$secs" | grep -c '^sec:' )"
  case "${n:-0}" in ''|*[!0-9]*) n=0 ;; esac
  if [ "$n" -eq 0 ]; then
    GPG_OK=0; GPG_WHY="o \`gpg\` existe, mas não vejo NENHUMA chave secreta (GNUPGHOME=${GNUPGHOME:-<padrão>})"
    return 0
  fi
  GPG_OK=1; GPG_WHY="$n chave(s) secreta(s)"
  return 0
}

# --- origin: estamos em dia? ----------------------------------------------
# O `git fetch` é REDE, e rede é infraestrutura: falhar nele avisa e segue.
# Já estar ATRÁS do origin é outra coisa — o land empurraria e seria recusado,
# depois de gastar a assinatura e a bateria inteira. Isso para.
UPSTREAM_BEHIND=0
UPSTREAM_AHEAD=0
UPSTREAM_NOTE=""
_upstream_probe() {
  local behind ahead
  if ! git remote get-url origin >/dev/null 2>&1; then
    UPSTREAM_NOTE="sem remote \`origin\` — não dá para conferir"
    return 0
  fi
  if ! git fetch --quiet origin main 2>/dev/null; then
    UPSTREAM_NOTE="o \`git fetch\` falhou (rede?) — segui com o que já estava no disco"
  fi
  if ! git rev-parse --verify --quiet origin/main >/dev/null 2>&1; then
    UPSTREAM_NOTE="${UPSTREAM_NOTE:-não existe \`origin/main\` neste checkout}"
    return 0
  fi
  behind="$( git rev-list --count HEAD..origin/main 2>/dev/null )"
  ahead="$( git rev-list --count origin/main..HEAD 2>/dev/null )"
  case "${behind:-0}" in ''|*[!0-9]*) behind=0 ;; esac
  case "${ahead:-0}"  in ''|*[!0-9]*) ahead=0 ;; esac
  UPSTREAM_BEHIND="$behind"
  UPSTREAM_AHEAD="$ahead"
  return 0
}

# --- docs/threat-model.md: sujeira que NINGUÉM editou ----------------------
# `.claude/scripts/check-threat-model-freshness.py` reescreve o arquivo como
# EFEITO COLATERAL de rodar: `flip_status_to_stale` (`:179-200`) aplica
# `re.sub(r"^(\*\*Status:\*\*)\s+accepted", r"\1 stale", count=1)` e sai 1.
# Medido na manhã da S328 em clone limpo: porcelain ` M docs/threat-model.md`,
# diff -U0 com exatamente uma linha removida e uma adicionada. Como o P0 de
# TODO SIGN recusa árvore com modificação rastreada, essa sujeira aborta a
# cerimônia acusando um arquivo que ninguém tocou.
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
  # `flip_status_to_stale` não tem caminho inverso. Aceitar `stale` →
  # `accepted` faria esta função reverter em silêncio a edição de quem
  # RE-ACEITOU o modelo de ameaças de propósito — exatamente o trabalho que a
  # cura existe para não destruir.
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
      bigwarn "pacote $pkg INCOMPLETO — a noite começou a montá-lo e não terminou."
      if [ -f "$PKG_SIGN" ]; then info "presente: $PKG_SIGN"; else info "FALTA   : $PKG_SIGN"; fi
      if [ -f "$PKG_LAND" ]; then info "presente: $PKG_LAND"; else info "FALTA   : $PKG_LAND"; fi
      info "Sem os DOIS scripts não dá para assinar nem landar — PULANDO este"
      info "pacote e seguindo para o próximo. Isso NÃO é um erro seu."
      _set_status "$pkg" "INCOMPLETO (pulado)"
    else
      bigwarn "pacote $pkg AUSENTE — a noite não chegou a montá-lo."
      info "esperado em: $PKG_SIGN"
      info "             $PKG_LAND"
      info "PULANDO este pacote e seguindo para o próximo. Isso NÃO é um erro"
      info "seu: significa que o trabalho da noite não chegou até ele."
      _set_status "$pkg" "AUSENTE (pulado)"
    fi
    SKIPPED_ANY=1
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
    info "como eu sei: $LANDED_PROOF"
    [ -n "$P_SUBJECT" ] && info "commit: $P_SUBJECT"
    _set_status "$pkg" "já estava landado"
    _mark_landed "$pkg"
    return 0
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
    # ---- portão da revisão cruzada, ANTES de qualquer escrita ------------
    if ! _rail_gate "$pkg"; then
      _set_status "$pkg" "PULADO ($RAIL_SKIP_SHORT)"
      SKIPPED_ANY=1
      return 0
    fi

    # ---- portão do GPG, também antes de qualquer escrita -----------------
    if [ "$GPG_OK" != "1" ]; then
      ec="$( _exit_code_for "$pkg" 2 )"
      _red "$pkg" "SIGN" "-" "$ec" \
        "não dá para assinar: $GPG_WHY." \
        "A assinatura é a única coisa nesta manhã que só você pode fazer, e" \
        "sem uma chave secreta o passo 3/5 falharia depois de eu já ter" \
        "re-baseado o pacote. Parei antes disso." \
        "Confira no SEU terminal:  gpg --list-secret-keys" \
        "Se a chave estiver em outro lugar, exporte GNUPGHOME e retome." \
        "Chame o CEO se não fizer sentido."
    fi

    step "[$pkg] 2/5 — re-base do pacote no HEAD vivo (finalize)"
    if [ -z "$P_FINALIZE" ]; then
      ok "este pacote não tem finalize (é $P_KIND) — nada a re-basear."
      if [ "$P_KIND" = "manifesto" ]; then
        info "o frescor dele é o BASELINE.sha256, conferido dentro do SIGN."
      fi
    else
      # Rodar SEMPRE: o próprio finalize compara a base com o HEAD e sai
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
      "O ensaio roda os portões e depois desfaz tudo. Reprovar aqui significa" \
      "que o land de verdade também reprovaria — e é exatamente para isso que" \
      "o ensaio existe." \
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
  info "A bateria de verificação deste pacote roda AQUI, dentro do land."
  info "Alguns pacotes rodam instalações e upgrades de verdade e levam ~10 min."
  info "Deixe rodando: interromper no meio é o único jeito de fazer estrago."
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
    _mark_landed "$pkg"
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
head1 "S329 — CERIMÔNIA DA MANHÃ"
say ""
info "data      : $( date '+%Y-%m-%d %H:%M:%S %Z' )"
info "repo      : $ROOT"
info "branch    : $( git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '?' )"
info "HEAD      : $( git rev-parse --short HEAD 2>/dev/null || printf '?' ) — $( git log -1 --format=%s 2>/dev/null | cut -c1-70 )"
info "ordem     : C → E"
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

step "EM DIA COM O GITHUB?"
_upstream_probe
[ -n "$UPSTREAM_NOTE" ] && warn "$UPSTREAM_NOTE"
if [ "$UPSTREAM_BEHIND" -gt 0 ]; then
  printf '\n\033[31mABORT:\033[0m este checkout está %s commit(s) ATRÁS do origin/main.\n' "$UPSTREAM_BEHIND" >&2
  printf '  Landar daqui produziria um push recusado — depois de gastar a sua\n' >&2
  printf '  assinatura e a bateria inteira. Chame o CEO: alguém empurrou algo\n' >&2
  printf '  que este checkout ainda não tem.\n' >&2
  exit 3
fi
if [ "$UPSTREAM_AHEAD" -gt 0 ]; then
  warn "há $UPSTREAM_AHEAD commit(s) local(is) que ainda não foram empurrados."
  info "Isso costuma significar que um push da noite falhou. Não é impedimento"
  info "para a cerimônia, mas vale contar ao CEO no fim."
else
  [ "$UPSTREAM_BEHIND" = "0" ] && [ -z "$UPSTREAM_NOTE" ] && ok "em dia com origin/main"
fi

step "CHAVE DE ASSINATURA (GPG)"
_gpg_probe
if [ "$GPG_OK" = "1" ]; then
  ok "gpg disponível — $GPG_WHY"
else
  bigwarn "não vou conseguir assinar: $GPG_WHY"
  info "Se algum pacote precisar de assinatura, eu paro nele e digo isso de novo."
  info "Um pacote que a noite já deixou assinado não precisa de gpg nenhum."
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

say ""
info "O CI roda SOZINHO a partir do push. Você não precisa disparar nada nem"
info "ficar olhando: se algo reprovar, ele fica registrado e o CEO vê depois."

_CI_URL=""
_origin="$( git remote get-url origin 2>/dev/null || printf '' )"
case "$_origin" in
  git@github.com:*) _CI_URL="https://github.com/${_origin#git@github.com:}" ;;
  https://github.com/*) _CI_URL="$_origin" ;;
esac
[ -n "$_CI_URL" ] && _CI_URL="${_CI_URL%.git}/actions"

step "runs recentes"
if command -v gh >/dev/null 2>&1; then
  gh run list --limit 8 || warn "gh falhou (rede? autenticação?) — abra o GitHub no navegador."
else
  warn "o \`gh\` não está instalado aqui — veja os runs no GitHub, aba Actions."
fi
[ -n "$_CI_URL" ] && info "no navegador: $_CI_URL"

# O conjunto RED do nightly de ownership é DERIVADO, nunca lembrado. Primeira
# fonte: um pacote que o declare no próprio EXPECTED-BASELINE.txt. Segunda: o
# arquivo RASTREADO que o gate do nightly de fato compara
# (`ownership-nightly-gate.sh` lê `scripts/tests/ownership-expected-reds.txt`)
# — a autoridade, não uma cópia de memória.
RED_IDS=""; RED_SRC=""
for _p in $ORDER; do
  if _pkg_load "$_p" && [ -n "$P_CER" ] && [ -f "$P_CER/EXPECTED-BASELINE.txt" ]; then
    _v="$( awk -F= '/^EXPECTED_OWNERSHIP_RED_IDS=/{ v=$2; gsub(/^"|"$/,"",v); print v; exit }' "$P_CER/EXPECTED-BASELINE.txt" )"
    if [ -n "$_v" ]; then RED_IDS="$_v"; RED_SRC="$P_CER/EXPECTED-BASELINE.txt"; break; fi
  fi
done
if [ -z "$RED_IDS" ] && [ -f "scripts/tests/ownership-expected-reds.txt" ]; then
  RED_IDS="$( awk '/^OWN-[0-9]+$/ { printf "%s%s", (n++ ? " " : ""), $0 } END { printf "\n" }' \
              scripts/tests/ownership-expected-reds.txt )"
  [ -n "$RED_IDS" ] && RED_SRC="scripts/tests/ownership-expected-reds.txt (a tabela que o próprio gate compara)"
fi

# O tempo-limite do Smoke Install é DECLARADO pelo pacote que o muda. Só vale
# dizer alguma coisa sobre ele se esse pacote tiver de fato entrado agora.
YML_TIMEOUT=""; YML_TIMEOUT_PKG=""
for _p in $ORDER; do
  _is_landed "$_p" || continue
  if _pkg_load "$_p" && [ -n "$P_CER" ] && [ -f "$P_CER/EXPECTED-BASELINE.txt" ]; then
    _v="$( awk -F= '/^EXPECTED_YML_TIMEOUT_MINUTES=/{ v=$2; gsub(/^"|"$/,"",v); print v; exit }' "$P_CER/EXPECTED-BASELINE.txt" )"
    if [ -n "$_v" ]; then YML_TIMEOUT="$_v"; YML_TIMEOUT_PKG="$_p"; break; fi
  fi
done

step "baseline esperado"
# Nunca prometer verde. O gate de hook-latency do `Validate` mede a velocidade
# do runner do CI, não o código — o pacote B da S328 (landado em 4bd7def) entrou
# em FASE 1 (advisory): publica a medida nova e preserva os vereditos de hoje.
# Quem deixa o Validate verde é o RERUN de madrugada, ou a fase 2 do gate,
# depois de ≥10 execuções darem dados para calibrar o limiar.
printf '  \033[33mValidate\033[0m       pode reprovar, e isso NÃO é regressão do que você landou.\n'
printf '                   O gate de latência de hooks mede o runner do CI, não o\n'
printf '                   seu código. Ele está em fase advisory desde a S328.\n'
printf '                   Quem deixa verde é o RERUN de madrugada (03:03), ou a\n'
printf '                   fase 2 do gate, com o limiar calibrado.\n'
if [ -n "$YML_TIMEOUT" ]; then
  printf '  \033[33mSmoke Install\033[0m  vai demorar MAIS que de costume: o pacote %s acrescentou\n' "$YML_TIMEOUT_PKG"
  printf '                   um teste ponta-a-ponta e subiu o tempo-limite do job para\n'
  printf '                   %s minutos. Esse número é uma ESTIMATIVA: veja quanto o\n' "$YML_TIMEOUT"
  printf '                   PRIMEIRO run real leva e conte ao CEO — um tempo-limite\n'
  printf '                   curto demais corta um run que estava verde e reporta o\n'
  printf '                   erro num passo inocente.\n'
else
  printf '  \033[32mSmoke Install\033[0m  esperado VERDE.\n'
fi
if [ -n "$RED_IDS" ]; then
  printf '  \033[32mownership\033[0m      nightly (~07:00Z): conjunto RED EXATO { %s }.\n' "$RED_IDS"
  printf '                   fonte: %s\n' "$RED_SRC"
else
  printf '  \033[33mownership\033[0m      não consegui derivar o conjunto RED esperado —\n'
  printf '                   confira com o CEO antes de aceitar o run.\n'
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
  say "  O CI segue sozinho a partir daqui."
else
  say "  Nenhum vermelho — mas nem todos os pacotes rodaram (veja o resumo acima)."
  say "  Isso é esperado quando a noite não chegou a montar algum pacote."
fi
[ -n "$LOG_FILE" ] && say "  Log completo: $LOG_FILE"
say ""
exit "$FINAL"
