---
id: PLAN-195
title: Guarda de Bash — execução indireta e alvo de escrita computado (classe GuardFall)
status: draft
created: 2026-09-30
owner: CEO
depends_on: []
level: L3
budget_tokens: "estimado — W0 (doc-only) ~60-120k; W1 (cura A + rail) ~300-600k; W2 (cura B + rail) ~300-600k; W3 (medição do sandbox, sem código) ~40-80k"
budget_sessions: "estimado 2-3 (W0 e a medição do sandbox cabem numa; cada cura canônica pede a sua cerimônia)"
context_risk: medium
external_wait: "Owner: assinatura GPG de cada wave canônica (W1, W2); decisão de ligar ou não o sandbox do SO DEPOIS da medição (W3 — «Medir antes de ligar» já decidido na S359). Debate L3 antes de W1/W2 (Security Engineer tem VETO). Vaga canônica: parte A na 2.ª vaga; parte B e sandbox sem vaga reservada (ver «Regra de WIP»)."
eta_calendar: "mesmo-dia a D+1 por wave (CEO-only fora das assinaturas e do debate); calendário estica só pelas cerimônias do Owner"
tags: [security, bash-guard, canonical-edit, threat-model, guardfall, fail-closed]
---

> **Regra de WIP (trabalho em voo) — este plano divide as vagas com o PLAN-194 e o PLAN-183.** A
> regra vale como está escrita no bloco «Regra de WIP» do topo do PLAN-194 (no máximo 3 pacotes
> canônicos em voo; cada um com ≤ 400 linhas e ≤ 8 paths; nunca dois pacotes tocando o mesmo
> arquivo) e não se repete aqui. Canônico = arquivo que só muda por cerimônia (pacote revisado +
> sentinel assinado por GPG do Owner). **Ordem das vagas — decisão do Owner (S359, 2026-09-30):
> «Codex automático, depois adopter (Recomendado)»:** 1.ª vaga = W1 do PLAN-194 (CI no Ubuntu 26.04,
> prazo 2026-10-19); **2.ª vaga = parte A deste plano (a W1 daqui)**; 3.ª vaga = W3 do PLAN-194 (pin
> automático verificado do Codex). Quando a W1 do PLAN-194 landar, a vaga liberada vai para a W7a do
> PLAN-183 (conserto do A1), com a W7b logo depois; em seguida vem a W2 do PLAN-194 (estado da
> auditoria) e, depois dela, a W5c do PLAN-194 (adoção do Sonnet 5.5), salvo se o debate dela pedir
> antes. **Dentro deste plano:** se a ADR da parte A sair num pacote próprio (W1-ADR, ver W1), a
> W1-ADR e a W1 usam a MESMA vaga, uma depois da outra (ADR primeiro). A parte B (W2 daqui) e a
> eventual edição do sandbox (W3 daqui) **não têm vaga reservada**: entram quando uma vaga liberar, na
> fila da OQ-11 do PLAN-194; a parte B nunca antes do land da parte A (mesmo arquivo). A W0 (docs,
> land livre), o debate e as medições não ocupam vaga canônica.

## Context

**De onde veio.** A triagem pós-GA v1.4.2 (S359, 30/09/2026; workflow `wf_87f0dc89`,
15 frentes só-de-leitura, cada achado com verificador adversarial) confirmou uma
classe pública de bypass de guardas de shell — **GuardFall** (nota da Cloud Security
Alliance / Adversa AI, 30/06/2026; ref. externa, tratada como DADO não verificado por
rede) — reproduzível no nosso hook. O próprio CEO re-verificou por sonda (payload cru no
`stdin` do hook, **sem executar** o comando) em 30/09 sobre o HEAD `429a5b39`.

**Decisões do Owner (S359, 2026-09-30) que este plano aplica — RESOLVIDAS, não são perguntas
abertas** (frase exata da opção escolhida no chat, entre aspas):

| decisão | efeito neste plano |
|---|---|
| Estrutura: «ok salva memory e claude e segue como vc sugeriu» (resposta à proposta: PLAN-194 = trem de manutenção; PLAN-195 = guarda de Bash; achados A1–A7 como ondas novas no PLAN-183; fechar PLAN-192/193/170) | este plano segue como L3 próprio; a recomendação da antiga OQ-5 foi aceita: a correção GENÉRICA do doc de ameaças (W0) sai já, sem esperar o debate e sem listar desvios |
| Publicação: «Commit e push no main (Recomendado)» | o plano vai público no `main` só com a CLASSE, descrita pela forma; a matriz concreta fica na evidência privada do Owner, fora do repositório; o teste com strings concretas entra só no commit da cura |
| Sandbox: «Medir antes de ligar (Recomendado)» | resolve a parte «segue ou espera a medição» da OQ-6; fica aberto só ligar ou não depois da medição (W3) |
| Medições pagas: «Só quando chegar a vez (Recomendado)» | nenhuma medição paga é adiantada; se uma wave daqui precisar de uma, ela roda na vez dessa wave |
| Ordem das vagas: «Codex automático, depois adopter (Recomendado)» | parte A na 2.ª vaga (ver «Regra de WIP» acima) |
| Sonnet 5.5: «Adotar» | a W5c do PLAN-194 passa a ser adoção e toca o `.claude/settings.json` — entra na colisão da W3 daqui |
| Python: «Manter 3.9 (Recomendado)» | nenhum path deste plano; os testes da cura continuam compatíveis com Python 3.9 |
| Codex: «Pin automático verificado (Recomendado)» | nenhum path deste plano; define a 3.ª vaga inicial (W3 do PLAN-194), citada na «Regra de WIP» |
| Limpeza da auditoria: «Script pronto, você roda depois (Recomendado)» | nenhum path deste plano |

**O que o guarda faz e não faz hoje.** Sigla: *hook* = script `PreToolUse` que o
Claude Code chama antes de rodar uma ferramenta. O `check_bash_safety.py`
(`decide_command`, `.claude/hooks/check_bash_safety.py:3818`) recebe a string CRUA do
comando e:

- **Bloqueia** a forma DIRETA e literal de remoção recursiva, `git reset --hard` e
  `git push --force` — via `_check_rm_rf` / `_check_git_reset_hard` /
  `_check_git_push_force` sobre os tokens `shlex` de cada subcomando (laço em
  `check_bash_safety.py:3891-3896`; definições em `:364`, `:426`, `:447`). Um SEGUNDO
  sítio aplica o mesmo trio: `_recheck_whole_command` (`:587-611`, laço em `:601`),
  chamado só quando o `shlex` rejeita um pedaço do comando (ramo fail-closed do
  *rawscan*, `:3874-3888`). A cura tem de cobrir ou reusar os DOIS sítios (ver OQ-2).
- **Bloqueia** a escrita DIRETA e literal em caminho canônico (redirect, `tee`,
  `sed -i`, corpo de interpretador `-c`, shell-aninhado, `eval`/`xargs`/`find`) — via
  `_e3_check_canonical_path_write` + `_scan_blob` (`check_bash_safety.py:2167`, `:2304`).

**A assimetria que abre a classe (verificado por sonda, `git status` idêntico
antes/depois):** a recursão do E3 (`_scan_blob`) só procura REFERÊNCIA A CAMINHO
CANÔNICO dentro do corpo de interpretadores/indireção. Os matchers DESTRUTIVOS
(`rm -rf` etc.) **não** recursam para dentro desses corpos. Resultado, pela FORMA:

1. **Execução indireta de comando destrutivo** — quando o verbo destrutivo vive dentro
   de um interpretador aninhado (`sh -c`/`bash -c`/…), de uma avaliação dinâmica
   (`eval`), de um encadeador (`xargs`, `find -exec`), de um cano para interpretador
   (pipe-to-shell), ou quando o NOME do comando é produzido por expansão (variável,
   substituição de comando, separador de campo, glob), o token literal que os matchers
   esperam nunca aparece ⇒ **ALLOW**. (Há cobertura nativa parcial para um caso de cano
   para interpretador — uma regra `deny` de `permissions` no `.claude/settings.json`; o
   hook não cobre a classe.)
2. **Escrita em caminho protegido com alvo COMPUTADO** — quando o destino canônico é
   alcançado por variável, glob, `cd` relativo ou posição `argv` em vez de literal, o
   `_scan_blob` não casa a referência ⇒ **ALLOW**.

As formas DIRETAS correspondentes seguem **BLOQUEADAS** — a assimetria é exatamente
entre a forma literal e a forma computada/indireta. A matriz concreta (esperado ×
observado, strings de comando e método de sonda) fica **FORA do repo público**, na
evidência privada do Owner, fora do repositório (decisão de divulgação do Owner, S359: o
repo é público; aqui descreve-se a CLASSE pela FORMA, nunca receitas que funcionem).

**Por que é em escopo.** `SECURITY.md:23` define literalmente "Bypass of the
destructive-command block list" do `check_bash_safety.py` como vulnerabilidade em
escopo. O repositório é público. Camadas que atenuariam: o sandbox do SO está
**desligado** (`.claude/settings.json:8`, `enabled:false`, composto mas inerte) e a
sessão do Owner roda em modo auto (`~/.claude/settings.json:17`, `defaultMode:auto`,
sobrepõe o `manual` do projeto em `.claude/settings.json:819`). A exploração real exige
um modelo dirigido por injeção; o classificador nativo do modo auto do Claude Code
2.1.285 **não** foi medido contra estas formas (dado ausente, não prova de cobertura).

**Documentação que hoje mente sobre a cobertura (a corrigir na W0).** O
`docs/security-bash-canonical-guards.md` §6 (oráculo 0, NÃO entregue a adopters —
ausente de `scripts/delivery-routes.tsv`) afirma mitigações inexistentes no substrato:
que "Bash evaluates `$(...)` before sending tokens" (`:286` — falso: o `PreToolUse`
recebe o texto bruto), que os filhos do `xargs` "hit the PreToolUse matcher AGAIN"
(`:259-263` — falso: subprocessos não reentram no hook) e que um detector forense
`PostToolUse` vê a forma expandida (`:290-306` — falso: o
`check_bash_canonical_forensic.py` é regex sobre a MESMA string bruta, docstring
"pure command-string heuristic"). Correções de fato apuradas: a linha 19 (`find -exec`)
JÁ é bloqueada (`_E3_INDIRECTION_VERBS` inclui `find`, `check_bash_safety.py:2157`); a
linha 33 (`$(eval …)`) GRADUOU para bloqueada na S207. O honesto: rows 17/18/34
continuam descobertas (advisory na matriz de teste, `_ADVISORY_ROWS={17,18,34}`), e a
classe destrutiva-por-expansão/indireção não está representada em lugar nenhum. O
`docs/threat-model.md:2131` (vetor 2) diz "29/34 BLOCK, 5 advisory" e dono "HOOK" —
defasado e sem a classe.

**Verificação independente registrada nas frentes** (DADOS; retorno integral e síntese
na evidência privada do Owner, fora do repositório): frente `academia` LIT-01 (severidade
P1, `verification: confirmado`, dois votos não-refutados) e LIT-02 (doc com mitigações
falsas); frente `adopter-A2-A3` A3-1..A3-6 (a mensagem enganosa da recusa de LEITURA e a
lacuna argv). Síntese: §U2 e §6.

## Goal

O `check_bash_safety.py` recusa (ou pede confirmação) comandos destrutivos e escritas em
caminho canônico **pela FORMA** — inclusive quando o verbo ou o alvo chegam por
interpretador aninhado, avaliação dinâmica, encadeador, cano para interpretador ou
expansão/glob/`cd` relativo/`argv` — sem virar um lockout do uso legítimo; e a
documentação de ameaças descreve a cobertura REAL.

## Thesis

Curar a CLASSE pela FORMA, não por lista de exemplos (CLAUDE.md §4; regra "cure a
classe, não o exemplo"). O substrato JÁ tem o instrumento certo: o E4
(`_e4_globify_expansions` / `_e4_expansion_replacement`, `check_bash_safety.py:3442`,
`:3377`) constrói um "esqueleto de expansão" com **piso de literais** (`_E4_GLOB_MIN_LITERALS`)
que evita o lockout (`python3 $SCRIPT` → `python3 *` = casa tudo, logo casa nada, ALLOW)
e foi provado contra bypass real (rounds Codex S292, com controle vermelho→verde). A
cura reusa esse esqueleto e a doutrina **fail-CLOSED em entrada não parseável**
(precedente `_recheck_whole_command`, PLAN-152 debate C4): (1) recursar os matchers
destrutivos nos corpos de `-c`/`eval`/`xargs`/`find -exec` e no cano-para-interpretador,
reusando o `_scan_blob`; (2) resolver expansão/glob/`cd` relativo no ALVO antes de casar
o caminho canônico, com o esqueleto do E4 e o piso de literais para não bloquear o uso
normal. Prova obrigatória vermelho→verde com a sonda (payload no `stdin`, sem executar).

**Alternativas descartadas (registradas nas frentes, não repetir o trabalho):**
- Fail-closed CEGO em toda expansão em posição de comando/alvo — o próprio arquivo
  documenta que isso "would deny most variable-driven interpreter calls in the repo — a
  fail-closed gate turned into a lockout" (`check_bash_safety.py:3464-3465`). Rejeitado: a
  cura tem de usar o esqueleto com piso de literais, não o bloqueio cru.
- Allowlist de LEITURA no corpo de interpretador (para o A3) — abre bypass de escrita
  (`open(p,'r+')`, `os.replace`, `exec`, etc.) e contraria a doutrina escrita no próprio
  hook (`check_bash_safety.py:2492-2495`). Rejeitado (frente A3-2). A cura do A3 é só a
  MENSAGEM (ver W1).
- Ligar o sandbox como substituto da cura do hook — cobre exfiltração e alvos fora da
  árvore, mas não `rm -rf` DENTRO do repo nem escrita canônica dentro da árvore; é
  decisão ORTOGONAL do Owner (W3), não substitui o matcher.

## Oráculo canônico (rodado em 30/09, HEAD 429a5b39; re-rodado na revisão S359 para o ADR-201 e o `test_check_harness_config.py`; registrar de novo antes de editar)

Sigla: *canônico* = exige cerimônia (pacote revisado + sentinel assinado por GPG do
Owner). `python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>` →
`<path>\t1` (canônico) ou `\t0`.

| Path | Oráculo | Wave |
|---|---|---|
| `.claude/hooks/check_bash_safety.py` | **1 (canônico)** | W1, W2 |
| `.claude/hooks/check_bash_canonical_forensic.py` | **1 (canônico)** | nenhuma — a docstring já é honesta ("pure command-string heuristic"); a W0 NÃO toca este arquivo (tocar = cerimônia própria) |
| `dist/ceo-plugin/hooks/check_bash_safety.py` | 0 (espelho gerado; **ignorado pelo git**) | nenhuma como path — só a bateria local de W1/W2 (regenerar + `cmp`) |
| `npm/.claude/hooks/check_bash_safety.py` | 0 (espelho gerado; **ignorado pelo git**) | nenhuma como path — só a bateria local de W1/W2 (regenerar + `cmp`) |
| `.claude/hooks/tests/test_check_bash_safety_indirect_exec.py` (novo) | 0 | W1 |
| `.claude/hooks/tests/test_check_bash_safety_canonical_matrix.py` | 0 | W2 |
| `.claude/hooks/tests/test_check_bash_safety.py` | 0 | W1 (só se um teste existente precisar de ajuste) |
| `.claude/hooks/tests/test_check_harness_config.py` | 0 | nenhuma como path — só a bateria de W1/W2 (ver W1) |
| `docs/security-bash-canonical-guards.md` | **0** (não canônico; não entregue a adopter) | W0 |
| `docs/threat-model.md` | **0** | W0 |
| `SECURITY.md` | **0** | W0 (se atualizar a linha da classe) |
| `.claude/settings.json` | **1 (canônico)** | W3 (se o Owner ligar o sandbox) |
| `templates/settings/settings.stack.sandbox.json` | **1 (canônico)** | W3 |
| `.claude/adr/ADR-201-bash-guard-indirect-execution.md` (novo; número reservado — ver nota; oráculo rodado sobre este nome) | **1 (canônico)** | W1 (decisão L3) |
| `.claude/governance/gate-scripts-manifest.txt` | **1 (canônico)** | nenhuma (não tocado — ver nota) |

Nota: `check_bash_safety.py` **não** é membro do manifesto ADR-192
(`.claude/governance/gate-scripts-manifest.txt`: 9 entradas, lista lida do arquivo em
30/09; `check_bash_safety` ausente) ⇒ sem bump de manifesto para o hook.

**Espelhos `dist/` e `npm/` (medido 30/09).** São hoje byte-idênticos ao hook (`cmp`) e
são SAÍDA LOCAL de build, **ignorada pelo git** (`.gitignore`: `dist/` e `npm/.claude/`;
`git ls-files` = 0 para os dois; `git check-ignore` confirma) ⇒ não entram no commit, nem
no Scope do sentinel, nem na contagem de paths do pacote. O CI regenera o `npm/` do zero
(passo `verify-npm-bundle-sync` do `validate.yml`). A bateria local regenera os dois
(`python3 scripts/build-plugin.py` e `bash scripts/npm-rebuild.sh`) e prova a identidade
por `cmp`. **Correção de premissa:** o `python3 scripts/build-plugin.py --check` confere só
os manifestos commitados em `.claude-plugin/` (docstring e `main()` do script) — NÃO prova
o espelho do hook; fica na bateria só porque o CI o roda.

**Contagem do tamanho do pacote (modelo v2: ≤ 400 linhas e ≤ 8 paths):** conta-se o diff
commitado (fonte do hook, testes, ADR). Os espelhos não entram (nota acima). A antiga
OQ-7 (se os espelhos contavam) perdeu o objeto e saiu.

**Número do ADR (medido 30/09).** O maior arquivo em `.claude/adr/` é o ADR-197, mas
contar arquivos não diz qual número está livre: 198 já está reivindicado por material de
outros planos (paths da W2a do PLAN-175, em `reviewed`; material do debate round-4 do
PLAN-186), 199 pelo PLAN-186 e 200 pelo PLAN-188 — o PLAN-176 já pagou essa lição quando o
seu ADR saiu do 198. O primeiro número sem nenhuma menção no repositório é o **201** ⇒
**ADR-201 fica reservado para este plano**. Outros planos (ex.: a W7b do PLAN-183) pegam, na
abertura, o próximo número SEM MENÇÃO, medido por busca de menções, não pelo maior arquivo.

## Waves

### W0 — correção honesta do doc de ameaças (livre, sem cerimônia)
Check: python3 .claude/scripts/check-canonical-doc-freshness.py && grep -n '^### §6.6 ' docs/security-bash-canonical-guards.md && ! grep -nF -e 'hits the PreToolUse matcher AGAIN' -e 'before sending tokens to Claude' -e 'Five vector classes remain advisory' docs/security-bash-canonical-guards.md

**Quando sai: já.** A decisão de estrutura do Owner (S359, 2026-09-30, tabela no Context)
aceitou a recomendação da antiga OQ-5: a correção GENÉRICA do doc sai agora, pela forma e
sem listar desvios, SEM esperar o debate L3 (que é pré-requisito só de W1/W2). Esta
revisão do texto não muda o status do plano (segue `draft`); o CEO faz o flip
`draft → reviewed` com base nessa aprovação em chat (PLAN-SCHEMA §4: `reviewed` = o Owner
leu e aceitou; §10: revisão informal em chat é o contrato) antes do primeiro commit da W0.
Não ocupa vaga canônica. Paths: 3 (os dois docs + `SECURITY.md`), todos oráculo 0; tamanho
estimado ~60-150 linhas.

**Fora de qualquer janela de SIGN.** A W0 landa e é commitada FORA de qualquer janela de
assinatura — de preferência antes do SIGN da W1 do PLAN-194 — e nunca fica edição sem
commit na árvore quando houver assinatura marcada: o SIGN aborta (P0) com arquivo
rastreado modificado; o `check-threat-model-freshness.py` ESCREVE `docs/threat-model.md`
(flip `accepted→stale`) como efeito colateral; e, pela regra do Owner, enquanto ele assina
nada se escreve no repositório.

Controle negativo do Check (registrado em 30/09, HEAD `429a5b39`): hoje não existe
heading `### §6.6` (`grep -c '§6.6'` = 0) e as três âncoras das afirmações falsas casam
em `:231`, `:262` e `:286` ⇒ o Check sai VERMELHO antes da W0. (O `grep 'not covered'`
antigo já casava hoje o título da §1.2, `:53`, e por isso não provava nada.)

- [ ] Reescrever `docs/security-bash-canonical-guards.md` §6 (`:229-308`), começando pelo
  parágrafo de abertura (`:231-232`, texto atual: "Five vector classes remain advisory
  post-Wave-B-3 (forensic-only). Each has documented mitigation; none is a "free"
  bypass."), que conta 5 classes e promete mitigação para todas. Criar a seção nova
  `### §6.6 Indirect execution and computed write target — NOT covered` (o doc é em
  inglês) declarando a CLASSE (execução indireta de destrutivo por interpretador
  aninhado/avaliação/encadeador/cano, e escrita com alvo computado) como **NÃO coberta**
  de forma genérica — pela FORMA, **sem** listar desvios concretos. Corrigir as
  afirmações falsas de substrato (§6.2 filhos do xargs `:260-266`, §6.4 expansão
  pré-hook `:286-291`, §6.5 forense pós-fato `:304-306`) e marcar 19/33 como BLOQUEADAS e
  17/18/34 como descobertas.
- [ ] Atualizar `docs/threat-model.md` vetor 2 (`:2131`) para nomear a classe aberta e a
  contagem real. **CUIDADO:** `check-threat-model-freshness.py` ESCREVE esse arquivo
  (flip `accepted→stale`) como efeito colateral — rodar por último e commitar o flip
  conscientemente (lição S328), no mesmo commit da W0 e fora de janela de SIGN.
- [ ] `SECURITY.md`: confirmar que a linha 23 (classe já em escopo) permanece honesta;
  ajustar só se necessário — Check: none (doc-only)

### W1 — cura parte A: execução indireta de comando destrutivo (canônica, L3)
Check: python3 -m pytest .claude/hooks/tests/test_check_bash_safety_indirect_exec.py .claude/hooks/tests/test_check_bash_safety_canonical_matrix.py .claude/hooks/tests/test_check_bash_safety.py .claude/hooks/tests/test_check_harness_config.py -q && python3 scripts/build-plugin.py --check && cmp .claude/hooks/check_bash_safety.py dist/ceo-plugin/hooks/check_bash_safety.py && cmp .claude/hooks/check_bash_safety.py npm/.claude/hooks/check_bash_safety.py

**Vaga:** 2.ª vaga canônica (ver «Regra de WIP»).

Testes novos que provam a cura (arquivo novo
`.claude/hooks/tests/test_check_bash_safety_indirect_exec.py`, oráculo 0):
`TestIndirectDestructiveBlocks` (uma linha por forma da classe A da matriz privada,
ids A-1..A-9 ⇒ BLOCK/ASK), `TestIndirectLegitAllow` (controles legítimos ⇒ ALLOW,
inclusive o texto destrutivo entre aspas num `echo`) e `TestReadRefusalMessage` (texto
da recusa de leitura). **Controle negativo obrigatório:** em árvore descartável, com o
arquivo de teste novo e o hook do HEAD SEM a cura,
`python3 -m pytest .claude/hooks/tests/test_check_bash_safety_indirect_exec.py -k TestIndirectDestructiveBlocks -q`
tem de sair com **exit 1** (falha real). Exit 5 ("nenhum teste coletado") NÃO vale
como controle. Depois da cura: exit 0, e `TestIndirectLegitAllow` verde nos dois lados.
(O pytest da matriz canônica sozinho NÃO prova nada: hoje ele já passa, porque as linhas
17/18/34 são `xfail`, `_ADVISORY_ROWS`, `test_check_bash_safety_canonical_matrix.py:122`.)
**Divulgação:** o arquivo de teste novo carrega strings concretas; ele só entra no repo
público NO MESMO commit da cura, nunca antes.

**Bateria do land (além dos testes novos):** `test_check_harness_config.py` entra na
bateria (já no Check acima). Motivo: o gate do harness (`check_harness_config.py:151`)
re-executa a fixture `bash_safety_destructive.json` contra este hook, e a W7a do PLAN-183
move essa fixture de pasta — as duas ondas não têm arquivo em comum, mas uma pode quebrar o
teste da outra. O inverso (testes do `check_bash_safety` na bateria da W7a) é do PLAN-183.

Tamanho (estimado): fonte do hook ~80-150 linhas + testes ~100-150 + ADR-201 ~80-120 =
~260-420 linhas revisáveis. Paths: até 4 (hook, teste novo, `test_check_bash_safety.py` se
preciso, ADR-201) ≤ 8; os espelhos `dist/` e `npm/` não são paths do pacote (ignorados pelo
git — nota do oráculo). Se, ao montar o pacote, a estimativa passar de 400, a ADR-201 sai
num pacote canônico PRÓPRIO (W1-ADR, arquivo distinto — não viola "nunca dois pacotes no
mesmo arquivo"), landado antes do código, NA MESMA vaga (ver «Regra de WIP»).

- [ ] Debate L3 `/debate start PLAN-195` fechado com PROCEED (Security Engineer tem VETO)
  antes de qualquer edição do hook — Check: none (debate gate)
- [ ] Recursar `_check_rm_rf`/`_check_git_reset_hard`/`_check_git_push_force` nos corpos de
  `-c`/`eval`/`xargs`/`find -exec` reusando o `_scan_blob` do E3 e o esqueleto do E4 (piso
  de literais), e recusar/pedir confirmação no cano-para-interpretador — CURA PELA FORMA,
  nunca por lista de exemplos. Cobrir os DOIS sítios do trio (`decide_command`
  `:3891-3896` e `_recheck_whole_command` `:601`). Controle vermelho→verde pela sonda e
  pelo `-k TestIndirectDestructiveBlocks` acima (RED primeiro, em árvore descartável).
- [ ] Corrigir SÓ a mensagem da recusa de LEITURA por `python3 -c` (A3-1/A3-3): apontar
  Read/`cat`/`grep` para leitura e separar o ramo fail-closed de parse (dizer "corpo não
  tokenizável/grande; nenhum caminho canônico identificado"), sem criar allowlist de
  leitura. Fixar o texto em `TestReadRefusalMessage`.
- [ ] Regenerar os espelhos LOCAIS (`python3 scripts/build-plugin.py` e
  `bash scripts/npm-rebuild.sh`) antes da bateria e provar a identidade por `cmp`; eles não
  entram no commit nem no Scope do sentinel (ignorados pelo git).
- [ ] Rail codex nas duas lanes até rodada limpa; sentinel; SIGN/LAND (GPG do Owner).

### W2 — cura parte B: escrita em caminho protegido com alvo computado (canônica, L3)
Check: python3 -m pytest .claude/hooks/tests/test_check_bash_safety_canonical_matrix.py .claude/hooks/tests/test_check_harness_config.py -q && python3 scripts/build-plugin.py --check && cmp .claude/hooks/check_bash_safety.py dist/ceo-plugin/hooks/check_bash_safety.py && cmp .claude/hooks/check_bash_safety.py npm/.claude/hooks/check_bash_safety.py

**Vaga:** sem vaga reservada — entra quando uma vaga liberar, na fila da OQ-11 do PLAN-194,
e nunca antes do land da parte A (mesmo arquivo).

Testes novos que provam a cura: classe `TestComputedCanonicalTarget` em
`.claude/hooks/tests/test_check_bash_safety_canonical_matrix.py` (uma linha por forma da
classe B da matriz privada, ids B-1..B-6, + os controles legítimos que seguem ALLOW, como
o esqueleto `python3 *`). **Controle negativo:** em árvore descartável, com os testes
novos e o hook SEM a cura,
`python3 -m pytest .claude/hooks/tests/test_check_bash_safety_canonical_matrix.py -k TestComputedCanonicalTarget -q`
sai com exit 1 (não 5); depois da cura, exit 0. Mesma regra de divulgação da W1; mesma
bateria do harness da W1 (`test_check_harness_config.py`, já no Check acima).
Tamanho (estimado): hook ~80-150 + testes ~60-120 = ~140-270 linhas revisáveis; paths: 2
(hook, matriz) ≤ 8 — os espelhos não são paths do pacote.

- [ ] Resolver expansão (variável/substituição), glob e `cd` relativo no ALVO de escrita
  (redirect/`tee`/`sed -i`/`dd of=`/interpretador) antes de casar o caminho canônico,
  reusando o esqueleto do E4 com piso de literais — sem fail-closed cego. Decidir a
  lacuna argv (A3-4: caminho canônico passado como `argv` a `python3 -c`) aqui ou em W1
  (OQ-4). Controle vermelho→verde pela sonda e pelo `-k TestComputedCanonicalTarget` acima.
- [ ] Regenerar os espelhos LOCAIS e provar a identidade por `cmp` (como na W1); fora do
  commit e do Scope.
- [ ] Rail codex nas duas lanes; sentinel; SIGN/LAND. Sequencial DEPOIS da W1 (mesmo
  arquivo — nunca dois pacotes canônicos no mesmo arquivo em voo).

### W3 — sandbox do SO: medir antes de ligar (decisão do Owner S359)
Check: none (medição + decisão do Owner; sem edição de código nesta wave)

Decisão do Owner (S359, 2026-09-30): «Medir antes de ligar (Recomendado)». A medição vem
primeiro; ligar ou não depois dela é a única pergunta que segue aberta (OQ-6). Sem vaga
reservada (ver «Regra de WIP»).

**Colisão no `.claude/settings.json` (nunca dois pacotes no mesmo arquivo).** Se o Owner
ligar o sandbox, a edição canônica do `.claude/settings.json` colide com a W6 (retenção do
log de auditoria) e com a W5c (adoção do Sonnet 5.5) do PLAN-194, que tocam o mesmo
arquivo. Ordem: a **W6 do PLAN-194 vai primeiro**, pela data de risco da retenção (~2026-11-21);
o sandbox vem depois, em pacote próprio — ou dentro do pacote da W6, se as duas decisões
ficarem prontas juntas (OQ-14 do PLAN-194); com a W5c, sequencial, sem pacote em comum
salvo decisão explícita. O `templates/settings/settings.stack.sandbox.json` só é tocado por
esta wave.

- [ ] Medir, em árvore/container descartável com orçamento de disco, o que quebra ao ligar
  `.claude/settings.json` `sandbox.enabled:true` (codex pair-rail, gpg, rede/egress,
  workflows que clonam, ceremony scripts) contra a `allowedDomains` atual.
- [ ] Owner decide ligar ou não depois da medição (OQ-6); se ligar, é edição canônica de
  `.claude/settings.json` (+ `templates/settings/settings.stack.sandbox.json`) em cerimônia,
  na ordem da colisão acima.

## Open questions

Saíram daqui, respondidas pelo Owner na S359 (2026-09-30; ver a tabela de decisões no
Context): a antiga **OQ-5** (a correção do doc sai já, na W0, sem esperar o debate e sem
listar desvios — decisão de estrutura, «ok salva memory e claude e segue como vc sugeriu») e
a parte «segue ou espera a medição» da **OQ-6** («Medir antes de ligar (Recomendado)»). A
antiga **OQ-7** (se os espelhos `dist/`/`npm/` contavam no limite do pacote) perdeu o
objeto: os espelhos são ignorados pelo git e não entram no pacote. Os números das outras
ficam iguais, para não quebrar referências.

- OQ-1 (debate/Owner): nível de fail-closed aceitável sem travar o uso normal. O
  audit-log só registra BLOQUEIOS do hook (corpus de comandos PERMITIDOS não existe), logo
  o FPR (taxa de falso-positivo) da regra proposta **não é medível** do log — decidir o
  orçamento de FPR (§4.4 do guards doc, ≤3/7d) por outro caminho (dogfood observado).
- OQ-2 (debate): tratamento de heredoc e de aspas — o E3 já é fail-CLOSED em `shlex`
  malformado; confirmar que a recursão destrutiva herda o mesmo fail-closed sem regressão
  nos controles negativos existentes (`echo "…rm -rf…"` deve continuar ALLOW). O trio
  destrutivo roda em DOIS sítios (`decide_command` `:3891-3896` e, no ramo de `shlex`
  rejeitado, `_recheck_whole_command` `:601`): decidir se a recursão nova entra nos dois
  ou num helper único chamado pelos dois — um sítio só deixaria o ramo de parse sem a cura.
- OQ-3 (debate): `.mcp.json` e `CLAUDE.md` entram no conjunto de caminhos protegidos da
  parte B? (Hoje não são `_CANONICAL_GUARDS`.)
- OQ-4 (Owner): a lacuna argv (A3-4) fecha na W1 (é indireção de execução) ou na W2 (é
  alvo de escrita computado)? Padrão do CEO: W2, com uma linha na matriz.
- OQ-6 (Owner, W3) — só o que resta: **ligar ou não o sandbox depois da medição.** (Medir
  antes de ligar já está decidido.)

## How to continue

Ler este plano, a evidência privada do Owner fora do repositório (matriz concreta + método
de sonda; síntese §U2/§6) e a memória `project-s359-urgency-triage`. **W0:** executar já
(decisão do Owner S359), fora de qualquer janela de SIGN, depois do flip `draft → reviewed`
feito pelo CEO com base na aprovação em chat. **W1 (parte A):** na 2.ª vaga, depois da W1 do
PLAN-194 ocupar a 1.ª (ver «Regra de WIP»); `/debate start PLAN-195 "<proposta>"` ANTES de
tocar o hook (L3, Security Engineer com VETO); rodar o oráculo `--is-canonical` de novo em
cada path; provar vermelho→verde com a sonda e com o `-k` nomeado de cada wave (exit 1
antes, exit 0 depois) em árvore descartável; regenerar os espelhos LOCAIS e provar por
`cmp` (fora do commit); bateria com `test_check_harness_config.py`; rail nas duas lanes;
SIGN/LAND do Owner. **W2 (parte B):** sem vaga reservada, depois do land da W1. **W3:**
medir; o Owner decide ligar ou não; se ligar, na ordem da colisão com a W6 do PLAN-194.

## Success criteria

- [ ] `docs/security-bash-canonical-guards.md` §6 e `docs/threat-model.md` vetor 2
  descrevem a cobertura REAL (classe indireta/computada declarada não-coberta ou curada) —
  Check: grep -n '^### §6.6 ' docs/security-bash-canonical-guards.md && ! grep -nF -e 'hits the PreToolUse matcher AGAIN' -e 'before sending tokens to Claude' -e 'Five vector classes remain advisory' docs/security-bash-canonical-guards.md
- [ ] O hook recusa/pergunta nas formas indiretas de destrutivo e de escrita canônica com
  alvo computado, e os controles negativos legítimos seguem ALLOW (sem lockout) — Check:
  python3 -m pytest .claude/hooks/tests/test_check_bash_safety_indirect_exec.py .claude/hooks/tests/test_check_bash_safety_canonical_matrix.py -q -k 'TestIndirectDestructiveBlocks or TestIndirectLegitAllow or TestComputedCanonicalTarget'
- [ ] Espelhos LOCAIS `dist/` e `npm/` idênticos ao hook depois de regenerados (saída de
  build ignorada pelo git) — Check: cmp .claude/hooks/check_bash_safety.py dist/ceo-plugin/hooks/check_bash_safety.py && cmp .claude/hooks/check_bash_safety.py npm/.claude/hooks/check_bash_safety.py
- [ ] Cada wave canônica com sentinel assinado por GPG do Owner e rail limpo — Check: none (ceremony record)

## Session history

- S359 (2026-09-30): plano aberto em `draft` a partir da triagem pós-GA v1.4.2. Classe
  GuardFall confirmada por sonda do CEO (HEAD `429a5b39`) e por dois verificadores
  adversariais (frente `academia` LIT-01/LIT-02, `verification: confirmado`). Matriz
  concreta e método de sonda na evidência privada do Owner, fora do repositório. Oráculo
  canônico registrado acima. Aguardando decisões do Owner (OQ-5/OQ-6) e debate L3 antes de W1.
- S359 (2026-09-30, revisão): correções dos revisores aplicadas após conferência no
  disco — Check da W0 e do critério 1 trocados por marcador que NÃO existe hoje (heading
  `§6.6` + três âncoras das afirmações falsas; o `grep 'not covered'` antigo já passava
  pelo título da §1.2); linhas do trio destrutivo corrigidas para `:3891-3896` e segundo
  sítio `:601` ligado à OQ-2; manifesto ADR-192 = 9 entradas; abertura da §6 citada
  verbatim (`:231-232`); testes nomeados com controle negativo exit 1 (não 5); regra de
  contagem dos espelhos declarada (OQ-7) e tamanhos estimados por wave; gatilho da W0
  (`reviewed`, sem esperar o debate) explicitado na OQ-5. Ajustes achados na mesma
  conferência: nota de lockout em `:3464-3465` (não `:3468`); o hook forense sai do
  escopo da W0 (canônico, docstring já honesta); espelho `npm/` sem `--check` ⇒ `cmp`.
  Oráculo re-rodado em 30/09 sobre todos os paths da tabela.
- S359 (2026-09-30, decisões do Owner + checagem cruzada entre PLAN-183/194/195): decisões
  registradas como RESOLVIDAS com a frase exata (tabela no Context); antiga OQ-5 resolvida
  (W0 sai já, genérica), OQ-6 reduzida a «ligar ou não depois da medição», OQ-7 apagada
  (sem objeto). Bloco «Regra de WIP» apontando para o do PLAN-194, com a ordem das vagas
  (parte A na 2.ª; W1-ADR e W1 na mesma vaga, em sequência; parte B e sandbox sem vaga
  reservada). Espelhos `dist/`/`npm/` reconhecidos como saída ignorada pelo git (fora do
  commit, do Scope e da contagem): paths recontados (W1 ≤ 4, W2 = 2); correção de premissa
  medida — `build-plugin.py --check` confere só os manifestos de `.claude-plugin/`, então os
  Checks passam a provar os dois espelhos por `cmp`. Colisão da W3 no `.claude/settings.json`
  com a W6 e a W5c do PLAN-194 (W6 primeiro, pela data). ADR reservado = **201**, não 198:
  medido que 198, 199 e 200 já estão reivindicados por outros planos (ver nota do oráculo).
  Deny nativo do cano-para-interpretador reescrito como cobertura parcial, sem dizer quais
  variantes passam; caminhos da pasta privada do Owner trocados por «evidência privada do
  Owner, fora do repositório». Bateria de W1/W2 com `test_check_harness_config.py` (a W7a do
  PLAN-183 move a fixture que esse gate re-executa). W0 fora de qualquer janela de SIGN.
  Status inalterado (`draft`); nada executado.
