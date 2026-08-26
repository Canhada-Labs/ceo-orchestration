---
plan: PLAN-185
round: 1
rounds_synthesized: [round-1]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "§1 — âncoras re-derivadas contra HEAD f787cf2; a afirmação «a defesa já existe em :2139-2159» é FALSA e foi substituída pelos dois mecanismos reais"
  - "§1 — F1 deixa de ser um sítio e passa a ser a população medida de 7 escritores desguardados"
  - "§2 — hard link entra em escopo; harnesses de vendor e F3 continuam fora, agora por escrito"
  - "§3 W1 — novo [P0] do predicado de confinamento de destino, com o dono decidido e justificado"
  - "§3 W1 — escopo passa de install_docs_template para o CONJUNTO de escritores; política FALHA-vs-PULA resolvida"
  - "§3 W1 — novo [P0] de pré-voo (o rollback do install não cobre docs/ nem .github/)"
  - "§3 W2 — gramática de handle REUSADA de upgrade.sh:3700 por dono compartilhado; upgrade.sh vira consumidor no mesmo patch"
  - "§3 W2 — validação no parse (:479) e antes de persistir (:2829); os DOIS sed nomeados (:1635 e :1643)"
  - "§3 W2 — spec de escrita atômica (mktemp no diretório de destino, 0644 explícito, trap)"
  - "§3 W2 — fixture (b): as constantes 1442/33 saem, entram asserções DERIVADAS + modo do arquivo"
  - "§3 W2 — auto-cura de 0 bytes passa a exigir PROVENIÊNCIA, não contagem de bytes"
  - "§3 — nova W3 (threat-model + ADR da classe)"
  - "§AC-1 — assere BYTES fora do target + mensagem nomeada, nunca exit code"
  - "§AC-2 — ganha a perna do install-state e declara que upgrade.sh não recupera"
  - "§AC-3 — absorve a rota (i) do censo §5.1 (19 → 0) e especifica o wiring de CI com controle negativo"
  - "§AC-4 — Scope enumera o conjunto esperado (5 canônicos + os não-canônicos que a cura obriga)"
  - "§4 — dimensionamento do Scope comunicado ao Owner antes da assinatura"
  - "§6 — cinco OQs numeradas, cada uma com o default conservador que a noite implementa"
synthesized_at: 2026-08-26T19:45:00Z
synthesized_by: CEO (síntese delegada e anonimizada — DEBATE-SCHEMA §13.2)
---

# PLAN-185 round-1 — consenso

> Identidades em `anonymization-map.md`. As três críticas saíram **ADJUST**; nenhuma
> REJECT, nenhum VETO. Todas as âncoras abaixo foram **re-verificadas por mim contra
> HEAD `f787cf2`** antes de entrar no plano — inclusive as dos próprios críticos, e
> **duas delas estavam erradas** (registradas em §"Correções aos críticos").

## Consensus findings (2+ agents flagged)

### C1 — As âncoras do plano estão mortas, e a afirmação central da §1 é FALSA
- **Críticos:** A (R-A1, R-A9), B (Must-fix 1), C (Must-fix 7) — **os três**.
- **Severidade acordada:** HIGH (bloqueante para revisibilidade; o V2 e o Owner leem a prosa).
- **Medido por mim:** `install.sh:2139`/`:2142` são os dois `_render_protocol_pointer … > "$TARGET/PROTOCOL.md"` de `install_protocol_pointer` (`case` em `:2137`). **Não há uma linha de symlink ali** — aquele sítio é ele próprio uma escrita desguardada. Os mecanismos reais são dois, com semânticas OPOSTAS: `_assert_no_symlink_parents()` (`:863`, componentes INTERMEDIÁRIOS, `exit 1`, **um único chamador** — `install_one:910`) e o disjunto de FOLHA `[[ -e "$dst" || -L "$dst" ]]` (`:900` dry-run, `:913` real), que **PULA** e continua. Um terceiro precedente: o skip `-L "$f"` de `apply_placeholder_substitutions` (`:2293`, mensagem em `:2301`), que também PULA.
- **Mitigação:** §1 reescrita com as coordenadas vivas **e com o nome da função ao lado da linha** — nome de função não apodrece. `:1466-1472` hoje é `_install_src_refuses` (`:1470`); `install_docs_template` está em `:1483`, o EXISTS-skip em `:1514`, o `cp` em `:1520`; o `sed` da F2 está em `:1643`, não `:1508`.
- **Onde aterrissa:** §1 (ambos os defeitos).

### C2 — O escopo da W1 é o CONJUNTO de escritores, não `install_docs_template`
- **Críticos:** A (R-A6, 4 sítios), B (R-B1, 5 sítios), C (R-C2, 3 call-sites) — **os três**, com populações diferentes.
- **Severidade acordada:** CRITICAL.
- **Medido por mim — a população real é 7**, e nenhum dos três a acertou inteira:

  | # | Função (def) | Predicado que segue o link | Escrita | Ancestral | Folha |
  |---|---|---|---|---|---|
  | 1 | `install_template` (`:939`) | `-e "$dst"` `:959` | `mkdir` `:964` + `cp` `:965` | não | não |
  | 2 | `install_reference_personas` (`:1430`) | `-e "$dst"` `:1446` | `mkdir` `:1449` + `cp` `:1450` | não | não |
  | 3 | `install_docs_template` (`:1483`) | `-e "$dst"` `:1514` | `mkdir` `:1519` + `cp` `:1520` | não | não |
  | 4 | CODEOWNERS em `install_github_templates` (`:1603`) | `-e "$dst"` `:1626` | `mkdir` `:1642` + `sed >` `:1643` | não | não |
  | 5 | `build_settings` (`:1693`) | `-e "$SETTINGS_DST"` `:1720` | `cp` `:1729`/`:1737`, `jq >` `:1761`, `cp` `:1774` | não | não |
  | 6 | `install_protocol_pointer` (`:2112`) | `-e "$TARGET/PROTOCOL.md"` `:2113` | redirect `:2139`/`:2142` | não | não |
  | 7 | `portable_sed_inplace` (`:2171`) | — | tmp de nome PREVISÍVEL `:2174` + `mv` `:2175` | não | não |

  Guardados: só `install_one` (`:884`, os dois mecanismos) e `apply_placeholder_substitutions` (`:2293`, só folha). Correções: o sítio que A chamou de `:1575 (build_settings)` é `_register_delivered_template`; `build_settings` está em `:1693` e os predicados dele são `:1689`/`:1720`. B não listou `install_template` (`:959`/`:965`), que tem a forma byte-idêntica.
- **Mitigação:** a W1 cura os 7 pela MESMA função, com prova COMPORTAMENTAL (reverter a função ⇒ os 7 testes vermelhos), nunca por `grep`. Um censo que sai zero enquanto seis seguem desguardados é falso-verde, e o AC-3 depende dele.
- **Onde aterrissa:** §3 W1 `[P0]`/`[P1]`, §1.

### C3 — O sítio da F2 é ELE PRÓPRIO um sítio da F1; a partição W1/W2 deixa o vetor aberto
- **Críticos:** B (R-B2), C (R-C2).
- **Severidade acordada:** CRITICAL.
- **Medido por mim:** o render do CODEOWNERS não passa por `install_docs_template`. `:1626` testa `[[ -e "$dst" ]]` (segue o link), `:1642` faz `mkdir -p "$TARGET/.github"` sem checar componentes, `:1643` escreve com `>`. Symlink pendente em `$TARGET/.github/CODEOWNERS` — ou um `$TARGET/.github` que seja symlink — escreve FORA do target.
- **Mitigação:** F1 e F2 são **uma superfície só**. O sítio `:1626-1643` recebe a guarda de destino antes de qualquer decisão de escrita, e a fixture (a) da W2 ganha uma perna com symlink pendente, com asserção nos bytes do alvo externo.
- **Onde aterrissa:** §3 W1 `[P0]` (o CONJUNTO inclui `:1626`), §3 W2 fixture (a).

### C4 — A guarda é um predicado de CONFINAMENTO DE DESTINO, não um `-L` na folha
- **Críticos:** A (R-A1 + Nice-to-have 1), B (R-B4), C (R-C10) — **os três**.
- **Severidade acordada:** CRITICAL.
- **Medido por mim:** `_wbm_source_confined` existe em `scripts/_framework_manifest_set.sh:621` com o motivo publicado em `_WBM_SRC_CONFINE_WHY` (`:620`) — é o espelho exato do que falta no lado do DESTINO. E o guard de hard link também já existe do outro lado: `_up_tpl_multilink_refuses` (`scripts/upgrade.sh:3857`) sobre `_up_tpl_nlink` (`:3842`). `_assert_no_symlink_parents` caminha os componentes mas **não recusa `..`**, e o `for comp in $parent_rel` de `:872` roda sem aspas e sem `set -f` (expansão de pathname num componente com `*`).
- **Mitigação:** o predicado recusa relpath não confinado (vazio, absoluto, com `..`), caminha os componentes com `-L`, recusa a folha symlink e recusa `nlink > 1`; publica o motivo numa variável (`_WBM_DST_REFUSE_WHY`) espelhando a de origem; fail-CLOSED quando o predicado falta, igual a `_install_src_refuses` (`:1470-1481`).
- **Onde aterrissa:** §3 W1 `[P0]` novo.

### C5 — FALHA-vs-PULA: o plano pede as duas coisas ao mesmo tempo
- **Críticos:** A (R-A2), B (R-B9).
- **Severidade acordada:** HIGH.
- **O conflito:** o plano manda "reusar a mesma guarda" e exige FALHA nomeada na folha; mas `install_one:913` trata folha symlink como EXISTS-skip e SEGUE, e `apply_placeholder_substitutions:2301` também pula. Reusar sem separar quebra o comportamento hoje testado; falhar em cinco sítios multiplica os pontos de aborto parcial.
- **Mitigação acordada:** separar **PREDICADO** de **POLÍTICA**. A função compartilhada só responde "este destino deve ser recusado?" e publica o motivo; cada chamador escolhe. Veredito em dois níveis (B): recusar a ESCRITA de forma nomeada, ACUMULAR, e falhar a RUN no fim com o sumário — nem aborto no meio da entrega, nem silêncio. `install_one` preserva o SKIP que os testes atuais fixam.
- **Onde aterrissa:** §3 W1 `[P0]`, AC-1.

### C6 — A cura da W2 já existe no corpus; escrevê-la de novo É a classe
- **Críticos:** A (R-A3, R-A4), B (R-B3).
- **Severidade acordada:** HIGH.
- **Medido por mim:** `scripts/upgrade.sh:3700` embute `^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$`, e o comentário de `:3674-3678` diz textualmente que existe para que o `upgrade.sh` não possa reproduzir o defeito, **citando o `install.sh:1508` do PLAN-183 §9.2** — o mesmo defeito da F2. Do lado do `install.sh`, `_add_sub` (`:2183`, escape de `[|&\]` em `:2188`, delimitador `|`) já substitui o MESMO `$GITHUB_OWNER` (`:2193`) com segurança. Uma terceira implementação é o quarto ramo local do mesmo valor.
- **Risco de contrato, medido:** gramáticas divergentes quebram install→upgrade. `install.sh:2829` grava `github_owner` no `.install-state.json`; `_read_install_state_github_owner` (`upgrade.sh:3679`) sai `3` ao ler um handle que a regex recusa, e o upgrade degrada em silêncio para handle vazio.
- **Mitigação:** a gramática vira **um dono compartilhado** em `scripts/_framework_manifest_set.sh` (a biblioteca que os três scripts já carregam), adotada **verbatim** da regex viva; `upgrade.sh:3700` é convertido em consumidor **no MESMO patch**. Deixar duas cópias divergirem é o mecanismo exato de D1–D4 (PLAN-183).
- **Onde aterrissa:** §3 W2 `[P0]`.

### C7 — Validar no PARSE e antes de PERSISTIR, não no sítio de escrita
- **Críticos:** A (R-A3), B (R-B5), C (R-C4) — **os três**.
- **Severidade acordada:** HIGH.
- **Medido por mim:** `--github-owner` é aceito cru em `:479` (`GITHUB_OWNER="${2:-}"`), sem uma linha de validação; os consumidores são `:1618`, `:1624`, `:1635`, `:1643`, `:1644`, `:2193`, `:2829`.
- **Mitigação:** validar em `:479` (único ponto que cobre os três sítios de interpolação de uma vez) **e** antes de persistir em `:2829` (`GITHUB_OWNER` é global; o próximo chamador não passa pelo parse). Não é duplicação: é o mesmo predicado compartilhado invocado em duas fronteiras. AC-2 ganha a perna do install-state.
- **Onde aterrissa:** §3 W2 `[P0]`, AC-2.

### C8 — O segundo `sed` (`:1635`) muda o veredito de POSSE, e o plano não o nomeia
- **Críticos:** A (R-A7), B (R-B5), C (R-C4) — **os três**.
- **Severidade acordada:** HIGH.
- **Medido por mim:** `:1635` é o mesmo `sed "s/{{OWNER_HANDLE}}/$GITHUB_OWNER/g"` dentro da sonda de byte-compare do ramo EXISTS, com `2>/dev/null`. Handle inválido ⇒ a sonda aborta em SILÊNCIO, o `cmp` nunca roda, `_append_delivered_template ".github/CODEOWNERS"` (`:1637`) nunca é chamado, e o veredito de posse muda — do lado do upgrade isso aterrissa em `PRESERVED (unclaimed)`. É exatamente o ramo que a fixture (c) percorre.
- **Mitigação:** a W2 declara os DOIS sítios; validar no parse torna ambos seguros por construção; a fixture (c) assere que a sonda também recusa.
- **Onde aterrissa:** §3 W2 `[P0]`, fixture (c).

### C9 — Escrita atômica: os dois precedentes no repo têm defeito
- **Críticos:** B (R-B6), C (R-C8).
- **Severidade acordada:** MEDIUM.
- **Medido por mim:** `portable_sed_inplace:2174` usa nome PREVISÍVEL (`${file}.ceo-sed-tmp`) dentro da árvore do target — um symlink pré-plantado nesse path escreve através. `install.sh:1634` faz `mktemp "${TMPDIR:-/tmp}/…"`, ou seja, possivelmente noutro filesystem: `mv` a partir dali degrada para copy+unlink, **não é atômico**, e sob ENOSPC reintroduz o 0-byte que a W2 existe para matar. A forma correta já existe: `_up_tpl_write` (`upgrade.sh:3800`) faz `mktemp "$_utw_dir/.ceo-deliver.XXXXXX"` (`:3803`) dentro de `dirname "$dst"`.
- **Mitigação:** `mktemp` no DIRETÓRIO DE DESTINO, nome imprevisível, `chmod 0644` explícito (o `mktemp` cria `0600`; sem isso o CODEOWNERS entregue fica ilegível para o time — regressão que bytes e linhas não pegam), remoção do temporário em `trap`. A fixture (b) assere **também o modo**.
- **Onde aterrissa:** §3 W2 `[P0]` (spec de escrita atômica), fixture (b).

### C10 — "0 bytes ⇒ reescreve" é o predicado errado; o certo é PROVENIÊNCIA
- **Críticos:** A (R-A8), B (R-B7).
- **Severidade acordada:** MEDIUM (é de AUTORIZAÇÃO, não de dados).
- **O argumento:** o tamanho não distingue "o `sed` abortou" de "o adopter esvaziou o arquivo de propósito" — truncar para zero é um modo real de DESLIGAR roteamento de revisão obrigatória. Reescrever re-liga donos num repositório de terceiro: é a classe D4 do PLAN-183 outra vez, que já custou uma sessão.
- **Mitigação:** auto-curar só quando o framework pode PROVAR que foi ele quem escreveu — `_append_delivered_template` (`:1637`/`:1645`) e o `.claude/.install-state.json` (`:2829`) já respondem isso. Sem prova: `WARNING` nomeado com a instrução manual, nunca escrita silenciosa. Com prova: recuperação RUIDOSA (`RECOVERED:` + `_state_record_op`).
- **Onde aterrissa:** §3 W2 `[P0]` (fixture c), OQ-1.

### C11 — O Scope da cerimônia está subdimensionado em 5×
- **Críticos:** A (Must-fix 6), C (R-C5).
- **Severidade acordada:** HIGH — é previsão mecânica, não opinião.
- **Medido por mim (oráculo `check_canonical_edit.py --is-canonical` em HEAD `f787cf2`):** `scripts/install.sh`=**1**, `scripts/upgrade.sh`=**1**, `scripts/_framework_manifest_set.sh`=**1**, `.github/workflows/validate.yml`=**1**, `.github/workflows/smoke-install.yml`=**1**; e do outro lado `scripts/doctor.sh`=0, `scripts/delivery-routes.tsv`=0, `.claude/scripts/check-installer-write-safety.py`=0, `.claude/scripts/data/installer-write-safety-baseline.txt`=0, `scripts/tests/smoke-install.sh`=0, `docs/threat-model.md`=0. São **cinco** canônicos, não um (C disse "4", listou 5).
- **E o gate é mais estrito do que "canônicos":** li a implementação (`PLAN-182/OWNER-S326-LAND.sh:186-195`) — o G4 compara `git apply --numstat | awk '{print $3}'` (TODO path do patch) contra o bloco Scope assinado. Logo os artefatos NÃO-canônicos que a cura obriga a tocar (instrumento do censo, baseline, testes novos, `threat-model.md`, o ADR) **também** têm de estar no Scope, ou `touched − scope = ∅` reprova o land.
- **Mitigação:** o Scope continua DERIVADO do patch no finalize (AC-4), mas o plano publica o conjunto ESPERADO e o §4 comunica o dimensionamento ao Owner antes da assinatura.
- **Onde aterrissa:** AC-4, §4.

### C12 — AC-3 como está é inalcançável; o wiring de CI tem duas armadilhas
- **Críticos:** A (R-A5), C (R-C6, R-C7).
- **Severidade acordada:** HIGH.
- **Medido por mim:** o baseline tem **27 entradas** (10 `upgrade.sh`, 9 `install.sh`, 4 `_codex_harness.sh`, 2 `_framework_manifest_set.sh`, 1 `install-npm.sh`, 1 `measure-repo-size.sh`; por veredito: 10 `symlink-follow:desguardado`, 14 `symlink-follow:indeterminado`, 2 `sed-interp:desguardado`, 1 `sed-interp:indeterminado`), e o cabeçalho define que "removing a line is how a cure is recorded" — logo o gate passa COM sítios desguardados listados. `install.sh`+`upgrade.sh` somam **19** — exatamente a rota (i) do censo §5.1, que o CEO já recomendou e o plano §3 ainda não absorveu.
- **As duas armadilhas de CI, verificadas:** (a) `validate.yml` roda em `pull_request:` **sem filtro `paths:`** — então o censo pode entrar ali sem a armadilha de "gate que a mudança não dispara"; (b) `smoke-install.yml` tem **duas** listas `paths:` (`pull_request` em `:5`, `push` em `:108`) que o próprio arquivo manda manter idênticas, e `scripts/tests/*.sh` roda SÓ ali — um e2e novo fora das duas listas, ou sem `run:` próprio, é um teste que ninguém roda.
- **Mitigação:** AC-3 vira "zero BLOQUEANTES de classe A em `install.sh` e `upgrade.sh` (19 → 0)", com os 8 restantes no baseline com razão registrada; o wiring inclui as DUAS listas + um step invocador + **controle negativo** (renomear o e2e ⇒ o step falha por arquivo ausente, não passa calado). Polaridade do gate per-PR em OQ-3.
- **Onde aterrissa:** AC-3, §3 W0/W2.

### C13 — A classe não está no contrato de ameaça, e falta o ADR
- **Críticos:** B (Must-fix 9), A (Nice-to-have 3).
- **Severidade acordada:** MEDIUM.
- **Medido por mim:** `docs/threat-model.md` modela symlink/hardlink/absoluto/`..` **só** para extração de tarball (T-004, `:631-644`, `squad-import.py`). A superfície de ESCRITA DE DESTINO do installer não está no contrato.
- **Aviso operacional (do CLAUDE.md §5, e é real):** `check-threat-model-freshness.py` REESCREVE esse arquivo (`accepted→stale`) e derruba o P0 de qualquer SIGN. Planejar o passo, não descobri-lo na cerimônia.
- **Mitigação:** nova W3 com o item do threat-model e o ADR "predicado na biblioteca, política no chamador" (3+ consumidores previstos: `install.sh`, `upgrade.sh`, `doctor.sh` — a fronteira que o próprio gate de arquitetura exige).
- **Onde aterrissa:** §3 W3 (nova).

### C14 — O rollback do install não cobre as árvores que W1/W2 tocam
- **Críticos:** C (R-C1, o lado do snapshot), B (Unseen 6, o lado do aborto parcial).
- **Severidade acordada:** HIGH.
- **Medido por mim:** o snapshot (`install.sh:821-824`) copia **apenas** `$TARGET/.claude`, e `cleanup_on_failure` (`:737`) restaura **apenas** `.claude`. Sob `set -euo pipefail`, o `sed` que falha em `:1643` aborta o script, o trap dispara, `.claude` volta — e o `.github/CODEOWNERS` de 0 bytes **fica**. A permanência da F2 não é só o EXISTS-skip: é o rollback com buraco. E se a guarda da W1 abortar (`exit 1`, como `_assert_no_symlink_parents:878` já faz) no meio da entrega de `docs/`, o target fica MISTO.
- **Mitigação:** **pré-voo** — a guarda compartilhada roda sobre TODOS os destinos de `install_docs_templates`/`install_github_templates` **antes da primeira escrita**, recusando ali (zero estado parcial). Alternativa (estender o snapshot a `docs/`+`.github/`) em OQ-4.
- **Onde aterrissa:** §3 W1 `[P0]` novo, OQ-4.

### C15 — O ramo `--dry-run` mente sobre um symlink pendente
- **Críticos:** B (Nice-to-have 2), C (Nice-to-have 3).
- **Severidade acordada:** LOW — não escreve, mas é o output com que o adopter decide.
- **Medido por mim:** os ramos dry-run usam `-e` puro: `:951`, `:1438`, `:1506`, `:1621`, `:1695`.
- **Mitigação:** `[P2]` na W1 — o dry-run consulta o mesmo predicado e imprime a recusa que o run real faria.
- **Onde aterrissa:** §3 W1 `[P2]`.

## Correções aos críticos (a síntese verificou, e dois números não sobreviveram)

1. **A aritmética da fixture (b) está errada em C, mas a conclusão está certa.** C escreveu «só um handle de exatamente 17 caracteres reproduz 1442 — e aí o `grep -c == 0` contradiz a asserção de tamanho». **Medido:** `{{OWNER_HANDLE}}` tem **16** caracteres, não 17; o template tem 1442 bytes / 33 linhas / 11 ocorrências; renderizado dá `1266 + 11 × len(handle)` — `a`⇒1277, `alice`⇒1321, `ceo-test-handle`⇒1431, 17 chars⇒**1453**. Logo é um handle de **16** caracteres que reproduz 1442, e **não há contradição**: com 16 chars as duas asserções valem juntas. O defeito real é mais simples e igualmente decisivo — 1442 é o tamanho do NÃO-renderizado, então a fixture só passa para handles de exatamente 16 caracteres e fica vermelha na próxima edição legítima do template. **A recomendação de C (asserções derivadas) é adotada; a justificativa aritmética é corrigida.**
2. **`:1575` não é `build_settings`.** A citou "`:1575` (`build_settings`) com a mesma forma". `:1575` está dentro de `_register_delivered_template`; `build_settings` está em `:1693` e os predicados dele são `:1689`/`:1720`, com escritas em `:1729`, `:1737`, `:1761`, `:1774` e um tmp de nome previsível em `:1880`. **A afirmação de FUNÇÃO sobrevive** (é sítio da classe) e entra na tabela do C2; a linha citada não.
3. **"4 canônicos" é 5.** C disse "4 canônicos, não 1" e listou cinco paths com oráculo=1. O número medido é **5**.
4. **O G4 não é sobre canônicos.** Nenhum crítico leu a implementação. O gate compara TODO path do patch contra o Scope assinado, então os não-canônicos também precisam estar lá — o que ALARGA o Must-fix 6 de A em vez de o confirmar apenas.

## Single-agent insights kept

1. **A fixture (b) como escrita nunca passa (C, R-C3).** Aceito com a aritmética corrigida acima. Vira asserções derivadas: linhas do renderizado == linhas da fonte; `grep -c "$HANDLE"` == `grep -c '{{OWNER_HANDLE}}'` da fonte (11 hoje, derivado no teste, nunca fixado); bytes `> 0`; e o MODO do arquivo (C9).
2. **`--github-owner org/team` é sintaxe VÁLIDA de CODEOWNERS (B, R-B8).** Verifiquei: `templates/.github/CODEOWNERS.template:14` é `@{{OWNER_HANDLE}}`, então o valor completa `@org/team`. O input que dispara a F2 não é um erro de digitação — é um caso de uso legítimo que a gramática estreita REJEITA. O plano tem de declarar isso, não descobri-lo em campo. → OQ-2.
3. **`upgrade.sh` não consegue recuperar o 0-byte, por construção (C, R-C9).** O install aborta no `sed` (`:1643`) ANTES de `_write_install_state` gravar `github_owner` (`:2829`); sem handle registrado o upgrade cai em `PRESERVED (unclaimed)` e nunca re-renderiza. O AC-2 fala em "um install subsequente" e está certo, mas o plano não declara que a rota de upgrade — o comando que o adopter roda por reflexo — é impotente. → AC-2 ganha a declaração.
4. **A contagem de baseline não fecha a classe; um teste de FORMA fecha (A, Nice-to-have 2).** A métrica mede delta contra uma allowlist. O que fecha é estrutural: nenhuma decisão de escrita por teste de existência fora do predicado compartilhado. → entra como `[P1]` na W1, com a contagem de baseline como evidência secundária.
5. **TOCTOU é residual irredutível em shell (B, Unseen 5).** Não é motivo para não guardar; é motivo para DECLARAR — e o alvo compartilhado do §5 é exatamente o cenário onde importa. → §5.
6. **`mv` sobre um destino que é symlink SUBSTITUI o link (B, Unseen 4).** Mais seguro que o `cp`, mas destrói em silêncio um symlink deliberado do adopter. Precisa de guarda, não de sorte — coberto pelo predicado (C4), mas registrado para que a cura da W2 não reintroduza a F1.

## Single-agent insights rejected / deferred

1. **Alargar a W1 aos 24 bloqueantes, incluindo harnesses de vendor (rota (ii) do censo).** **DEFERIDO.** Mistura entrega com harness de vendor, que o §2 declara fora. 14 dos 24 são `indeterminado` porque o matcher não situa a escrita dentro de funções de 177–253 linhas — para vários deles a cura é *encurtar a função*, uma conversa de refatoração que esta wave não abre. → plano futuro, com os 8 restantes vigiados pelo baseline.
2. **Exatidão da gramática perante a doc do GitHub (A R-A4 pede a regra real; B advisory 1 relativiza).** **DEFERIDO como nit.** A regex viva aceita hífen final e hífens consecutivos, que o GitHub recusa. A propriedade que importa aqui é o conjunto fechado `[A-Za-z0-9-]` não conter `/`, `&`, `\`, `|`, newline nem espaço — e essa vale. Apertar a regex divergiria de `upgrade.sh` (C6) sem ganho de segurança. B não verificou a doc (sem rede) e disse isso; eu também não. → item próprio, com fonte citada, quando alguém tiver rede.
3. **`portable_sed_inplace` imprime `SUBSTITUTED` incondicionalmente (B advisory 3).** **DEFERIDO.** Real, mas hoje `set -euo pipefail` (`:209`) salva o caso, e não é escrita fora do target.
4. **Dois commits dentro do mesmo Scope assinado (A resposta 2).** **ACEITO como mecânica de cerimônia, não como § do plano.** Preserva `git revert <sha>` por defeito e o Scope é o mesmo conjunto de paths. Fica registrado aqui; a montagem do pacote decide.
5. **Fixture de segunda execução (C advisory 2).** **DEFERIDO para `[P2]`.** Rodar o install duas vezes com o mesmo handle e assertar que a segunda registra a entrega pela sonda de `:1635` — é o mesmo furo "result-only" que o comentário de `:1562-1569` diz já ter passado verde uma vez. Bom teste, não bloqueante.
6. **Estender o censo a `doctor.sh` (B advisory 4).** **DEFERIDO para a 4ª passada da W0**, que está em derivação em paralelo. O baseline atual não tem entrada de `doctor.sh`, e não sei dizer se isso é ausência de sítio ou ausência de escopo — a passada invertida responde.

## Plan adjustments

Índice das seções alteradas (as edições vivem no plano):

- **§1** — âncoras re-derivadas com nome de função; a frase "a defesa já existe em `:2139-2159`" removida e substituída pelos dois mecanismos reais; F1 passa a declarar a população de 7 escritores; F2 passa a declarar os dois `sed` e a persistência não validada.
- **§2** — hard link ENTRA em escopo por escrito; harnesses de vendor, F3 e a exatidão da gramática perante o GitHub ficam FORA, cada um com a razão.
- **§3 W0** — checkbox do censo absorve a rota (i) (19 → 0) e a cláusula de CI ganha o controle negativo.
- **§3 W1** — reescrita: `[P0]` predicado de confinamento com dono decidido; `[P0]` os 7 sítios pela mesma função com prova comportamental; `[P0]` pré-voo antes da primeira escrita; `[P1]` teste de FORMA; `[P2]` dry-run coerente.
- **§3 W2** — reescrita: `[P0]` gramática reusada por dono compartilhado com `upgrade.sh` convertido a consumidor; `[P0]` validação no parse e antes de persistir, os dois `sed` nomeados; `[P0]` escrita atômica especificada; fixtures (a)/(b)/(c) reescritas.
- **§3 W3** — nova: threat-model + ADR da classe, com o aviso do `check-threat-model-freshness.py`.
- **AC-1..AC-4** — reescritos conforme C2, C5, C7, C10, C11, C12.
- **§4** — dimensionamento do Scope comunicado ao Owner; nota sobre os dois commits.
- **§5** — TOCTOU declarado como residual.
- **§6** — OQ-1..OQ-5, cada uma com o default conservador que a noite implementa.

## Round verdict

**PROCEED** — registrado como `design-coherent` (DEBATE-SCHEMA §13.1).

As três críticas saíram ADJUST e nenhuma abriu uma bifurcação que o CEO não possa resolver: os 15 achados de consenso são emendas ao TEXTO e ao ESCOPO de um desenho cuja direção os três defenderam explicitamente em "What I would NOT change" (predicado compartilhado, validação antes da escrita, escrita atômica, uma cerimônia, asserção nos bytes, censo invertido). Nenhum crítico propôs desenho alternativo; todos propuseram o MESMO desenho aplicado a uma população maior e a coordenadas vivas.

Uma segunda rodada re-criticaria um texto que estou reescrevendo agora, ao custo de ~90k tokens, para produzir o que o V2 produz melhor: o rail codex revisa o PATCH, não a prosa. As cinco perguntas que sobraram são de política (`org/team`, auto-cura, polaridade do gate, rollback, empacotamento), não de desenho, e cada uma vai ao §6 com o default conservador que a noite implementa — o Owner reverte de manhã se discordar.

**Este PROCEED não autoriza shipping.** Ele satisfaz V0 apenas. V1 (testes/hooks/CI), V2 (pair-rail codex, o único gate de verdade LLM, fail-closed ao Owner) e V3 (cerimônia GPG do Owner) continuam inteiros e obrigatórios.
