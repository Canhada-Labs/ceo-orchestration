---
id: PLAN-195
title: Guarda de Bash — execução indireta e alvo de escrita computado (classe GuardFall)
status: reviewed
created: 2026-09-30
reviewed_at: 2026-10-01
reviewed_by: "Owner — aceite em bloco, no chat da S361 (2026-10-01), da recomendação sobre o plano revisto no debate: corpo do debate (sha 9894151f, PROCEED) + apêndice «Correções pós-debate S360»; OQ-8 mantida como o CEO resolveu no debate"
owner: CEO
depends_on: []
level: L3
budget_tokens: "estimado (refeito no debate r1, S360) — W0 (doc-only) ~60-120k; instrumento de replay de falso-positivo ~60-120k; parte A = W1-ADR ~80-150k + W1a ~350-650k + W1b ~300-600k (total ~0,8-1,5 M, rail com teto de 4 rodadas por pacote); W2 (cura B + mensagem A3 + argv + rail) ~350-700k; W3 (medição do sandbox, sem código) ~40-80k; debate L3 ~0,5-1 M"
budget_sessions: "estimado 5-7 (W0 e a medição do sandbox cabem numa; parte A 3-4 sessões em 3 pacotes na mesma vaga; W2 1-2; cada pacote canônico pede a sua cerimônia)"
context_risk: medium
external_wait: "Owner: assinatura GPG de cada wave canônica (W1, W2); decisão de ligar ou não o sandbox do SO DEPOIS da medição (W3 — «Medir antes de ligar» já decidido na S359). Debate L3 antes de W1/W2 (Security Engineer tem VETO; a reconfirmação dos dois VETOs sobre o sha novo do plano segue PENDENTE — item C11). Vaga canônica: parte A na 2.ª vaga; parte B e sandbox sem vaga reservada (ver «Regra de WIP»)."
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

As formas DIRETAS correspondentes seguem **BLOQUEADAS só na grafia canônica** — verbo no
início de um pedaço delimitado por `&&`, `||`, `;` ou `|`. **Correção do debate r1 (S360,
conferida no código):** a raiz não é só a indireção; o trio decide sobre `tokens[0]`
(`check_bash_safety.py:378`, `:433-437`, `:456`) de pedaços de um fatiamento que só conhece
esses quatro operadores (`:275`, `:526-584`), sem caixa baixa e com o `git` casado por posição
fixa. Por isso também passam formas DIRETAS irmãs, sem nenhuma indireção: separadores e
agrupadores que o fatiamento não modela, palavras reservadas do shell, lançadores fora dos
quatro prefixos normalizados (`:107`), grafia em outra caixa, opção global do `git` antes do
subcomando, e a divergência da regra de comentário entre o tokenizador do E3 e o dos pedaços
do trio combinada com o `continue` fail-open de `_recheck_whole_command` (`:597-600`). A
matriz concreta (esperado ×
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

O `check_bash_safety.py` **eleva o custo** de chegar a um comando destrutivo ou a uma escrita
em caminho canônico por forma não literal — formas diretas irmãs, interpretador aninhado,
avaliação dinâmica, encadeador, alimentador opaco, expansão/glob no verbo ou no alvo, `cd`
relativo, `argv` — recusando **pela FORMA**, sem virar um lockout do uso legítimo; o que segue
aberto fica como **residual declarado pela forma** (análise estática de shell é incompleta por
construção — molde do E4, `check_bash_safety.py:2468-2478`); e a documentação de ameaças
descreve a cobertura REAL.

**Residuais declarados pela forma — FONTE ÚNICA** (a §6.6 da W0 e a ADR-201 remetem a esta
lista; debate r1 C11 + r2):

1. APIs destrutivas da própria linguagem do interpretador, sem verbo de shell.
2. Script em arquivo, inclusive escrito antes pela ferramenta Write.
3. Funções e aliases vindos do perfil do shell ou de chamadas anteriores.
4. Configuração de ferramenta que executa um valor como programa (aliases de shell do `git`,
   chaves executáveis de configuração).
5. Variáveis de arquivo de inicialização do shell (dono: o env guard, advisory por padrão).
6. Argumentos que chegam ao `xargs` pela entrada padrão.
7. Palavra de comando E argumentos totalmente computados (sem marcador destrutivo literal).
8. Remoção por busca de arquivos com ação de remoção (A-8), com ou sem predicado — fora da W1
   pela OQ-8; volta junto com a remoção recursiva sem força se o Owner decidir a OQ-10.
9. Remoção recursiva sem a opção de força (hoje ALLOW no trio, `:383-418`) — política, OQ-10.
10. Sub-formas de alimentador opaco rebaixadas para advisory pela regra da OQ-9, se houver
    (a ADR-201 lista quais, depois do replay).
11. O `cd` entre CHAMADAS (o hook não recebe o `cwd`); a W2 cobre só o `cd` dentro do mesmo
    comando.
12. Ponto cego de comentário no normalizador de quebra de linha do E4 (guarda de toggle): o E4
    fica byte-idêntico na W1; FU `PLAN-195-FOLLOWUP-e4-comment-normaliser`.

## Thesis

Curar a CLASSE pela FORMA, não por lista de exemplos (CLAUDE.md §4; regra "cure a
classe, não o exemplo"). **Tese revista no debate r1 (S360; `PLAN-195/debate/round-1/consensus.md`,
afirmações conferidas no código pelo `wf_430c1885-742`):**

1. **Raiz.** O trio destrutivo decide sobre `tokens[0]` de pedaços de um fatiamento ingênuo.
   Esta é a 4.ª ocorrência histórica da classe «o trio não vê o verbo» (PLAN-019 P0-02,
   PLAN-153.E5, PLAN-152 rawscan, agora) ⇒ cura estrutural.
2. **Mecanismo da parte A: UMA passada nova e aditiva** — uma chamada só, na cauda de
   `decide_command` (depois do laço legado, antes do `return` de ALLOW), que anda pelas
   POSIÇÕES DE PALAVRA DE COMANDO de tudo o que o bash executaria e que está estaticamente
   visível, sobre a configuração de léxico do E3 (`shlex` com `punctuation_chars`, `:2190`), e
   roda o trio sobre cada comando simples achado. O laço legado e `_recheck_whole_command` ficam
   byte-idênticos (a passada nova cobre o escopo dos dois sítios porque anda no comando
   inteiro e só ACRESCENTA BLOCK — é monotônica); E3 e E4 ficam byte-idênticos na W1.
   **Pré-léxico fiel ao bash (debate r2):** o léxico do E3 não é fiel ao bash em dois pontos —
   no estado de palavra o `shlex` encerra o token num `#` e descarta o resto da linha
   (`shlex.py`, ramo `state in ('a','c')`), enquanto no bash `#` só abre comentário no INÍCIO de
   palavra; e no modo POSIX ele apaga o TIPO de aspas. Por isso, antes do léxico (mesma
   `punctuation_chars`, `commenters` vazio), UMA varredura ciente de aspas: (a) trata `#` como
   comentário só no início de palavra e fora de aspas, com aspas inertes dentro do comentário,
   que termina na quebra de linha; (b) trata a quebra de linha como separador fora de aspas e
   fora de corpo de here-doc; (c) delimita os corpos de here-doc, distinguindo delimitador
   citado de não citado; (d) guarda o tipo de aspas, para que corpo de substituição de comando
   fora de aspas simples seja recursado — inclusive dentro de aspas duplas e em here-doc de
   delimitador não citado, seja qual for o consumidor.
3. **Reuso por leitura, não por refatoração.** `_scan_blob` é closure dentro do laço do E3 e
   devolve caminho (`:2245`, `:2304`) — não é peça reutilizável. Reusam-se, por chamada ou
   leitura, as tabelas e funções do E4: `_E4_PREFIX_RUNNERS` (`:2652`),
   `_E4_PREFIX_RUNNER_FLAGS` (`:2699`), `_e4_classify_prefix_flag` (`:3154`), o padrão de
   atribuição no mesmo comando (`assigned_toggle`, `:3680-3685`, `:3740-3743`), o de substituição
   em posição de comando (`:2888`) e a decodificação de aspas estáticas (`:3377`).
4. **Verbo computado SEM piso de literais.** O piso do E4 (`_E4_GLOB_MIN_LITERALS = 4`,
   `:2569`, `:2935`) foi desenhado para a posição de OPERANDO (`:3461-3466`); na posição do
   verbo as grafias comuns de nomes de 2 e 3 letras ficam abaixo dele e viram ALLOW. Regra do
   verbo computado, em ordem: (a) propagar atribuições literais feitas no MESMO comando; (b) se o
   verbo continua computado E o segmento traz marcadores destrutivos LITERAIS do trio, BLOCK;
   (c) senão ALLOW, e a forma entra na lista de residuais. O piso continua sendo a ferramenta
   da W2 (alvo de caminho).
5. **Invariante (ADR-201):** nenhuma forma que a passada reconhece recebe veredito mais
   permissivo que a sua forma direta.
6. **Fail-closed de parse:** o léxico do topo já bloqueia a montante se falhar (`:2193-2208`).
   Corpo de SHELL reconhecido pela passada (shell `-c` em qualquer grafia reconhecida, inclusive
   aglomerado de opções; argumentos do `eval` concatenados; here-doc/here-string consumidos por
   shell; corpo de função) que não tokeniza ⇒ **BLOCK, com ou sem assinatura do trio** — é o
   que o E3 já faz para o `-c` exato (`:2307-2315`), e fazer menos para a grafia nova violaria o
   invariante do item 5 (correção da revisão Codex da rodada 1, P2). A assinatura do trio na
   forma achatada (precedente E4, `:3644-3665`) serve só para escolher o `reason_code` e a
   mensagem (destrutivo × corpo não analisável). Teto iterativo de profundidade e tamanho ⇒
   BLOCK acima do teto (crash em matcher é fail-open, `:4227-4233`). Corpo NÃO-shell
   (python/node/perl) nunca recebe fail-closed cego desta passada — a W1 não estende a ele o
   ruído da A3.
7. **Decisão = BLOCK** com mensagem acionável («escreva o comando na forma direta; ela é julgada
   pelo próprio mérito»), `destructive=True` (paridade com a forma direta) e `reason_code`
   próprio por classe (K1 do debate trata os alimentadores opacos — OQ-9).

A parte B (W2) resolve expansão/glob/`cd` relativo/`argv` no ALVO antes de casar o caminho
canônico, com o esqueleto do E4 e o piso de literais, que ali é a ferramenta certa. Prova
obrigatória vermelho→verde em árvore descartável, sem executar nenhum comando da classe.

**Alternativas descartadas (registradas nas frentes, não repetir o trabalho):**
- Fail-closed CEGO em toda expansão em posição de OPERANDO/alvo — o próprio arquivo
  documenta que isso "would deny most variable-driven interpreter calls in the repo — a
  fail-closed gate turned into a lockout" (`check_bash_safety.py:3464-3465`; o exemplo da nota
  é o operando de script de interpretador). Rejeitado: no alvo (W2) a cura usa o esqueleto com
  piso de literais, não o bloqueio cru. Na posição do VERBO vale a Thesis item 4 (conjunção,
  sem piso) — correção do debate r2, que apontou a contradição desta linha com a Thesis.
- Allowlist de LEITURA no corpo de interpretador (para o A3) — abre bypass de escrita
  (`open(p,'r+')`, `os.replace`, `exec`, etc.) e contraria a doutrina escrita no próprio
  hook (`check_bash_safety.py:2492-2495`). Rejeitado (frente A3-2). A cura do A3 é só a
  MENSAGEM (ver W1).
- Ligar o sandbox como substituto da cura do hook — cobre exfiltração e alvos fora da
  árvore, mas não `rm -rf` DENTRO do repo nem escrita canônica dentro da árvore; é
  decisão ORTOGONAL do Owner (W3), não substitui o matcher.
- (debate r1) Reusar o esqueleto do E4 COM o piso de literais na posição do VERBO — o piso
  foi feito para operando; no verbo, as grafias comuns de nomes curtos ficam abaixo dele e
  viram ALLOW por aritmética. Rejeitado (Thesis item 4).
- (debate r1) Recursão em dois sítios (ou helper chamado pelos dois) — duas segmentações é a
  forma de defeito que o próprio arquivo registra (`check_bash_safety.py:3249-3251`) e que o
  achado C16 reproduz. Rejeitado em favor da passada única (Thesis item 2).
- (debate r1) ASK puro — o hook não tem esse canal: `Decision` só tem allow/block/rewrite-ask
  e o `ask` só sai com `updatedInput` (`:299-322`, `:3947-3963`); sem humano (subagente,
  night-run) uma permissão pendente é silêncio, não recusa. Rejeitado (OQ-9 trata o
  falso-positivo dos alimentadores opacos por outro caminho).

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
| `.claude/hooks/tests/test_bash_posture_toggle_invocation.py` | 0 | nenhuma como path — bateria de W1a/W1b/W2 (debate r1) |
| `.claude/hooks/tests/test_check_bash_safety_cp_chaining.py` | 0 | nenhuma como path — bateria de W1a/W1b/W2 (debate r1) |
| `.claude/hooks/tests/test_check_bash_safety_h5_rewrite.py` | 0 | nenhuma como path — bateria de W1a/W1b/W2 (debate r1) |
| `.claude/hooks/tests/test_byte_identity_fuzzer.py` | 0 | W1a/W1b só se a relação hook × gêmeo YAML virar asserção de mão única (ADR-201); senão só bateria |
| `.claude/hooks/tests/test_byte_identity_harness.py` | 0 | bateria de W1a/W1b/W2 (paridade com o gêmeo YAML) |
| `.claude/policies/bash-safety.policy.yaml` | **1 (canônico)** | nenhuma — gêmeo declarativo do trio; a W1 NÃO o toca (relação decidida na ADR-201) |
| `.claude/hooks/_lib/policy_preprocessors.py` | **1 (canônico)** | nenhuma — espelho do trio para o gêmeo YAML; a W1 NÃO o toca |
| `.claude/hooks/_lib/audit_emit.py` | **1 (canônico)** | W1a-1 ou W1a-2 SÓ se a ADR-201 escolher estender `_LEARNING_RAIL_ENUM`/`_LEARNING_SWITCH_ENUM` para o evento de desarme do kill-switch (debate r2); senão nenhuma (**→ item C3 (2): nesse caso entra também `SPEC/v1/audit-log.schema.md`, canônico**) |
| `docs/security-bash-canonical-guards.md` | **0** (não canônico; não entregue a adopter) | W0 |
| `docs/threat-model.md` | **0** | W0 |
| `SECURITY.md` | **0** | W0 (se atualizar a linha da classe) |
| `.claude/settings.json` | **1 (canônico)** | W3 (se o Owner ligar o sandbox) |
| `templates/settings/settings.stack.sandbox.json` | **1 (canônico)** | W3 |
| `.claude/adr/ADR-201-bash-guard-indirect-execution.md` (novo; número reservado — ver nota; oráculo rodado sobre este nome) | **1 (canônico)** | W1 (decisão L3); o leque de arquivos que um ADR novo arrasta (índice canônico, documentos de contagem) → «Correções pós-debate S360», item C2 |
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
**→ corrigido em «Correções pós-debate S360», item C6: o flip é decisão do Owner; o CEO só o
registra no cabeçalho depois do aceite explícito dele em chat (feito em 2026-10-01).**
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
  **→ corrigido em «Correções pós-debate S360», item C1: NÃO seguir este texto ao pé da letra —
  rodar só com `--dry-run --verbose`, nunca commitar o flip nem mover `Last updated`, e incluir
  `tests/integration/test_threat_model_coverage.py` na bateria da W0.**
- [ ] (debate r1) No mesmo texto da W0: (a) não afirmar que as formas DIRETAS seguem
  bloqueadas sem qualificar — só a grafia canônica; as formas diretas irmãs entram na §6.6 pela
  forma; (b) registrar que, para as classes A e B, o `PreToolUse` é a ÚNICA detecção — o
  forense pós-fato só casa quatro formas literais de escrita canônica
  (`check_bash_canonical_forensic.py`) e não vê destrutivo indireto nem alvo computado; (c)
  §6.6 traz a lista de residuais pela forma — a FONTE ÚNICA é a lista do Goal deste plano
  (12 itens), reproduzida pela forma, sem receitas. — Check: none (doc-only; coberto pelo
  Check da W0)
- [ ] `SECURITY.md`: confirmar que a linha 23 (classe já em escopo) permanece honesta;
  ajustar só se necessário — Check: none (doc-only)

### W1 — cura parte A: execução indireta e formas diretas irmãs (canônica, L3) — dividida no debate r1 em W1-ADR → W1a → W1b
Check: python3 -m pytest .claude/hooks/tests/test_check_bash_safety_indirect_exec.py .claude/hooks/tests/test_check_bash_safety_canonical_matrix.py .claude/hooks/tests/test_check_bash_safety.py .claude/hooks/tests/test_check_harness_config.py .claude/hooks/tests/test_bash_posture_toggle_invocation.py .claude/hooks/tests/test_check_bash_safety_cp_chaining.py .claude/hooks/tests/test_check_bash_safety_h5_rewrite.py .claude/hooks/tests/test_byte_identity_fuzzer.py .claude/hooks/tests/test_byte_identity_harness.py -q && python3 scripts/build-plugin.py --check && cmp .claude/hooks/check_bash_safety.py dist/ceo-plugin/hooks/check_bash_safety.py && cmp .claude/hooks/check_bash_safety.py npm/.claude/hooks/check_bash_safety.py

**Vaga:** 2.ª vaga canônica (ver «Regra de WIP»). W1-ADR, W1a e W1b usam a MESMA vaga, uma
depois da outra: W1a e W1b tocam o mesmo arquivo do hook; a ADR é arquivo distinto, mas
precede o código.

**Pré-requisitos comuns:** debate L3 fechado com PROCEED (**→ item C11:** inclui a
reconfirmação dos dois VETOs sobre o sha do plano que contém o apêndice, registrada em
`PLAN-195/debate/`; enquanto não estiver registrada, a W1 não começa); instrumento de replay de
falso-positivo pronto e medido sobre o HEAD (OQ-1) — fora do repo ou em teste não canônico;
só contagens entram no pacote.

#### W1-ADR — ADR-201 (`PROPOSED`)
Conteúdo mínimo: a tese (raiz, passada única aditiva, reuso por leitura); o invariante de
não-permissividade; a taxonomia de contêineres — RUNNERS (operando é argv: a tabela do E4),
TOMADORES DE CORPO (operando é texto de shell: shell `-c`, avaliação com todos os argumentos,
here-doc consumido por shell), ALIMENTADORES OPACOS (definição pela forma na OQ-9), VERBO
INDECIDÍVEL (expansão na palavra de comando); o pré-léxico fiel ao bash (Thesis item 2); o
escopo de recursão pela forma; a regra do verbo computado (Thesis item 4); o fail-closed de
parse de corpo de shell reconhecido (BLOCK com ou sem assinatura do trio; a assinatura só
escolhe `reason_code` e mensagem — Thesis item 6); a decisão BLOCK + `destructive=True` +
`reason_code` por classe, com técnica mapeada (paridade com o forense) e o `reason_code`
separando o trio do vocabulário estendido; a **mudança de contrato da tag `destructive`**
(hoje o docstring de `Decision`, `check_bash_safety.py:315-320`, a reserva ao trio; estendê-la
ao vocabulário novo muda o que é liberável por citação e o que entra no
`fact_gate_shadow_deny` — declarar); a **observabilidade sem ação nova**: o evento é
`veto_triggered` (ação já registrada e passthrough em `_lib/audit_emit.py`), UM por comando,
porque `emit_generic` com ação não registrada só deixa breadcrumb e retorna em silêncio —
nenhuma ação nova é criada, e o `_lib/audit_emit.py` (canônico) só é tocado no caso do
kill-switch descrito abaixo; a regra dos alimentadores opacos com as
condições da OQ-9 resolvida — (a) a definição pela forma; (b) tabela POR SUB-FORMA com classe
(EQUIVALÊNCIA com a forma direta ⇒ meta zero; HEURÍSTICA ⇒ limite — a regra do verbo
computado e os alimentadores opacos são heurísticas), o limite como NÚMERO ABSOLUTO de
comandos legítimos distintos no corpus de replay, o denominador registrado junto (janela UTC,
comandos, comandos distintos, sessões) e a definição operacional de falso-positivo (bloqueio
novo de comando cuja forma direta equivalente seria ALLOW; bloqueio de comando cuja forma
direta também é bloqueada é «consistente com a política»), tudo fixado ANTES de o replay
rodar; (c) rebaixamento POR SUB-FORMA, nunca da classe, decidido em cerimônia (emenda da ADR +
constante no código), não por configuração de runtime; (d) a sub-forma rebaixada continua
emitindo o MESMO `reason_code` com desfecho distinto («faria bloquear») e entra na lista de
residuais; (e) piso de segurança: sub-forma cujo produtor visível é um baixador de rede NUNCA é
rebaixada (o uso legítimo de instalador tem a rota humana `!`); o **kill-switch** próprio, lido
do snapshot `trusted_env`, ligado por padrão, com DOIS níveis — «só as sub-formas heurísticas»
e «a passada inteira» — e que, desligado, emite `learning_rail_disabled` uma vez por sessão
(precedente `check_bash_safety.py:1715-1732`); **essa ação COAGE os campos** — `rail` fora de
`_LEARNING_RAIL_ENUM` vira `observe` e `switch` fora de `_LEARNING_SWITCH_ENUM` vira `other`
(`_lib/audit_emit.py:7585-7591`, enumerações em `:8316-8321`) —, então emitir com o nome do
kill-switch novo gravaria uma atribuição falsa no registro forense; a ADR escolhe e declara uma
de duas saídas: estender as duas enumerações (o `_lib/audit_emit.py`, canônico, entra como path
da W1a-1 ou da W1a-2, na mesma cerimônia; **→ item C3 (2): o `SPEC/v1/audit-log.schema.md`,
canônico, entra junto**) ou usar outra ação já registrada cujo esquema caiba
(achado da confirmação de VETO da rodada 2); o vocabulário destrutivo (A-9 dentro; A-8 fora,
OQ-8; remoção recursiva sem força conforme a OQ-10); a relação com o gêmeo YAML (hook ⊇ YAML;
a W1 não toca os arquivos canônicos do gêmeo); a rota de limpeza sancionada (lição S358:
agente apaga o próprio clone por helper confinado invocado por caminho) fixada como ALLOW; por
que o retorno antecipado da reescrita de força-push antes da passada é inerte (re-citação token
a token, `:736`); o risco latente do piloto de citação (busca por substring sem filtro de papel
— armar só com filtro por papel `user`, FU); as limitações do corpus de replay (um
repositório, viés de sobrevivência, retenção dos transcripts); e os residuais pela forma (a
FONTE ÚNICA é a lista do Goal). Landa `PROPOSED`; o flip para `ACCEPTED` vai no pacote de
código que entrega o comportamento (W1b). Paths: 1. **→ corrigido em «Correções pós-debate
S360», item C2: o leque real é o ADR-201 mais o índice canônico, 8 documentos de contagem, o
`CLAUDE.md:54` e o preâmbulo do `CHANGELOG.md`; landar o ADR-201 sozinho deixa três gates
vermelhos.** Estimativa: 150-220 linhas.

#### W1a — passada aditiva: segmentação, lançadores, corpos de shell
Escopo: a chamada única na cauda de `decide_command`; o pré-léxico fiel ao bash (Thesis item 2:
comentário só no início de palavra, quebra de linha como separador fora de aspas e de here-doc,
corpos de here-doc com delimitador citado × não citado, tipo de aspas preservado); o
caminhador de posições de palavra de comando sobre a configuração de léxico do E3 (corridas
de pontuação que contêm terminador; palavras reservadas do shell em lista fechada; abertura de
contexto em parêntese, substituição de comando, crase e substituição de processo — **dono
explícito da substituição de comando entre aspas duplas e da substituição em here-doc de
delimitador não citado, que EXECUTAM seja qual for o consumidor**); o normalizador de palavra
de comando (lançadores pela tabela do E4, com flag desconhecida tratada como ambígua; `env` com
divisão de string tratado como corpo; caixa baixa com `str.lower`; nome-base; aspas estáticas;
**expansão de chaves por PERTENÇA** — se qualquer palavra expandida de um token na posição de
comando for verbo do trio, os marcadores são avaliados sobre a união das palavras expandidas
com o resto do segmento; acima de `_E4_BRACE_MAX_WORDS`, `check_bash_safety.py:2603`, BLOCK,
precedente `:2597-2600`); a gramática do `git` (opção global
antes do subcomando; opção destrutiva depois de operando); a recursão em corpo de shell `-c`
(inclusive aglomerado de opções curtas que contém `c`), em todos os argumentos do `eval`, no
argv depois das flags do `xargs`, no verbo de busca com `-exec`/`-execdir`/`-ok`/`-okdir` e em
here-doc/here-string consumidos por shell (here-doc para arquivo é DADO); o teto iterativo; o
`reason_code` próprio, emitido uma vez por comando; o kill-switch próprio da passada (lido do
snapshot `trusted_env`, ligado por padrão), separado do `CEO_BASH_RAWSCAN`. Linhas da matriz:
A-4, A-5 e a família de formas diretas irmãs (inclusive a divergência de comentário entre
tokenizadores). Paths: hook, teste novo, `test_check_bash_safety.py` se preciso, e
`_lib/audit_emit.py` só se a ADR-201 estender as enumerações do evento de desarme (≤ 4;
**→ item C3 (2): nesse caso entra também `SPEC/v1/audit-log.schema.md`, canônico, ≤ 5**).
Estimativa: 360-500 linhas ⇒ **divisão pré-registrada como provável (debate r2):** W1a-1
(pré-léxico + separadores + palavras reservadas + chaves) → W1a-2 (lançadores, gramática do
`git`, recursão em corpos, teto), na mesma vaga, cada uma ≤ 400 linhas; o controle N de N vale
por pacote.

#### W1b — verbo computado, alimentadores opacos, vocabulário
Escopo: a regra do verbo computado (Thesis item 4; A-1/A-2/A-3); os alimentadores opacos
(A-6/A-7) com a decisão da OQ-9; corpo de função e valor de alias definidos no mesmo comando;
a extensão de vocabulário — A-9 com controle ALLOW para arquivo comum, com `reason_code` de
vocabulário estendido distinto do trio (A-8 fica FORA — OQ-8, residual 8 do Goal); o flip da
ADR-201 para `ACCEPTED`. Paths: hook, teste novo, ADR-201 (≤ 3; **→ item C2: o flip muda a
linha de status do índice canônico `.claude/adr/README.md`, que entra no pacote: ≤ 4**). Estimativa:
250-400 linhas.

#### Prova (W1a e W1b)
Testes no arquivo novo `.claude/hooks/tests/test_check_bash_safety_indirect_exec.py` (oráculo 0):
`TestIndirectDestructiveBlocks`, `TestIndirectLegitAllow` e a bateria combinatória.

- (a) **Controle negativo POR PACOTE** em árvore descartável, com o teste do pacote e o hook
  do HEAD de ANTES do pacote (para a W1a, o HEAD sem a W1a; para a W1b, o HEAD com a W1a já
  landada): CADA linha NOVA deste pacote em `TestIndirectDestructiveBlocks` falha — contagem N
  de N das linhas novas, registrada no pacote, não só «exit 1» —, e as linhas que vieram de
  pacotes anteriores seguem VERDES (regressão). Exit 5 ("nenhum teste coletado") NÃO vale.
  Depois da cura: todas verdes. (Correção da revisão Codex da rodada 1, P2: a W1b não pode
  exigir N de N vermelho sobre linhas da W1a que o HEAD dela já cura.)
- (b) Cada linha afirma a CLASSE do motivo (`reason_code` ou prefixo estável do ramo novo), não
  só `allow=False` — mata o falso-verde do fail-closed cego do `_scan_blob`
  (`check_bash_safety.py:2307-2315`).
- (c) Bateria combinatória gerada de verbo × invólucro × grafia × separador × lançador da
  tabela do E4 × **comentário** (início de palavra, meio de palavra, com aspas dentro) ×
  **tipo de aspas** (sem aspas, simples, duplas, here-doc citado e não citado), com a matriz
  privada como semente, não como universo.
- (d) Aninhamento até o teto e acima dele; p95 do `test_perf_p95_under_50ms_advisory`
  (`test_check_bash_safety_canonical_matrix.py:300`, que é `assert` duro) antes e depois.
- (e) `TestIndirectLegitAllow`: corpus sintético representativo (interpretador dirigido por
  variável, `xargs` e busca de arquivos não destrutivos, shell `-c` com verbo legítimo, texto
  destrutivo citado — inclusive o controle do `echo` —, here-doc para arquivo), verde antes e
  depois.
- (f) Mutação por sub-regra: desligar cada regra nova deixa ao menos uma linha vermelha.
- (g) Força-push dentro de contêiner nunca vira reescrita nem `ask`.
- (h) A rota de limpeza sancionada segue ALLOW.
- (i) Replay offline (OQ-1), DIFERENCIAL nos dois sentidos: ALLOW→BLOCK contado e
  classificado pela definição de falso-positivo da ADR-201; BLOCK→ALLOW tem de ser ZERO (a
  passada é aditiva, qualquer caso é defeito). Contagens e denominador registrados no pacote; o
  delta é classificado à mão na evidência privada do Owner.
- (k) **Prova de emissão** (debate r2): com o diretório de auditoria isolado pelo `conftest`,
  cada linha BLOCK da passada nova grava EXATAMENTE UM evento `veto_triggered` com o
  `reason_code` da classe e o campo de técnica; os controles de `TestIndirectLegitAllow` gravam
  ZERO eventos da classe nova; o kill-switch desligado grava o evento de desarme escolhido na
  ADR-201 uma vez, e o teste afirma o CONTEÚDO (campos `rail` e `switch` com os valores do
  kill-switch novo, não os coagidos `observe`/`other`), não só a contagem;
  a sub-forma rebaixada (se houver) grava o mesmo `reason_code` com desfecho «faria bloquear».
  Nenhuma ação nova é criada. **→ item C3 (3): o teste do evento de desarme distingue os DOIS
  níveis do kill-switch («só heurísticas» × «passada inteira») no conteúdo.**
- (j) Paridade com o gêmeo YAML: `test_byte_identity_fuzzer.py` e `test_byte_identity_harness.py`
  verdes, com a relação declarada na ADR-201.

O pytest da matriz canônica sozinho NÃO prova nada (as linhas 17/18/34 são `xfail`,
`_ADVISORY_ROWS`, `test_check_bash_safety_canonical_matrix.py:122`). **Divulgação:** o arquivo
de teste novo carrega strings concretas; ele só entra no repo público NO MESMO commit da cura
(de W1a e de W1b), nunca antes.

**Bateria do land:** as 9 suítes do Check acima. `test_check_harness_config.py` entra porque
o gate do harness (`check_harness_config.py:151`) re-executa a fixture
`bash_safety_destructive.json` contra este hook, e a W7a do PLAN-183 move essa fixture de pasta
— quem landar por SEGUNDO roda a bateria do outro sobre a árvore composta. As 3 suítes do hook
e as 2 de paridade entraram no debate r1 (nenhuma estava no plano).

**Regra de parada do rail (pré-registrada no debate r1):** no máximo 4 rodadas por pacote;
NO-GO só por P0 ou por afirmação falsa; achado que é nova grafia de um residual já declarado
pela forma vai para o anexo da rodada final e não bloqueia; P1 da mesma subclasse em duas
rodadas seguidas ⇒ parar e estreitar a afirmação (troca de arquitetura), não remendar.

**Fora da W1 (vai para a W2):** a mensagem da recusa de leitura por `python3 -c` (A3), porque
toca o E3 e a W1 deixa o E3 byte-idêntico. Custo aceito: entre W1 e W2, um corpo destrutivo
malformado segue BLOQUEADO pelo E3, mas com a mensagem de caminho canônico.

**Tamanho:** cada pacote ≤ 400 linhas e ≤ 8 paths; os espelhos `dist/` e `npm/` não são paths
do pacote (ignorados pelo git — nota do oráculo). **→ item C2: o pacote que cria arquivo de ADR
ou de emenda tem uma exceção a este teto (índice e documentos de contagem fora da conta,
re-derivados no LAND).**

- [ ] Debate L3 `/debate start PLAN-195` fechado com PROCEED (Security Engineer e Threat
  Detection Engineer com VETO) antes de qualquer edição do hook (**→ item C11:** inclui a
  reconfirmação dos dois VETOs sobre o sha do plano que contém o apêndice, registrada em
  `PLAN-195/debate/`; PENDENTE até esse registro) — Check: none (debate gate)
- [ ] Instrumento de replay de falso-positivo (OQ-1) pronto e medido sobre o HEAD
  — Check: none (instrumento fora do repo; contagens registradas no pacote)
- [ ] W1-ADR: ADR-201 `PROPOSED` com o conteúdo mínimo acima; cerimônia — Check: test -f .claude/adr/ADR-201-bash-guard-indirect-execution.md
- [ ] W1a: passada aditiva, caminhador, normalizador, gramática do `git`, recursão nos corpos,
  teto, `reason_code` e kill-switch próprios, pré-léxico e chaves; prova (a)-(k) — Check: python3 -m pytest .claude/hooks/tests/test_check_bash_safety_indirect_exec.py -q
- [ ] W1b: verbo computado, alimentadores opacos (OQ-9), função/alias do mesmo comando,
  vocabulário (A-9; A-8 fora pela OQ-8), flip da ADR-201; prova (a)-(k) — Check: python3 -m pytest .claude/hooks/tests/test_check_bash_safety_indirect_exec.py -q
- [ ] Regenerar os espelhos LOCAIS (`python3 scripts/build-plugin.py` e
  `bash scripts/npm-rebuild.sh`) antes da bateria de cada pacote e provar a identidade por
  `cmp`; eles não entram no commit nem no Scope do sentinel (ignorados pelo git) — Check: cmp .claude/hooks/check_bash_safety.py npm/.claude/hooks/check_bash_safety.py
- [ ] Rail codex nas duas lanes com a regra de parada acima; sentinel; SIGN/LAND (GPG do
  Owner) por pacote — Check: none (ceremony record)

### W2 — cura parte B: escrita em caminho protegido com alvo computado (canônica, L3)
Check: python3 -m pytest .claude/hooks/tests/test_check_bash_safety_canonical_matrix.py .claude/hooks/tests/test_check_bash_safety_indirect_exec.py .claude/hooks/tests/test_check_bash_safety.py .claude/hooks/tests/test_check_harness_config.py .claude/hooks/tests/test_bash_posture_toggle_invocation.py .claude/hooks/tests/test_check_bash_safety_cp_chaining.py .claude/hooks/tests/test_check_bash_safety_h5_rewrite.py .claude/hooks/tests/test_byte_identity_fuzzer.py .claude/hooks/tests/test_byte_identity_harness.py -q && python3 scripts/build-plugin.py --check && cmp .claude/hooks/check_bash_safety.py dist/ceo-plugin/hooks/check_bash_safety.py && cmp .claude/hooks/check_bash_safety.py npm/.claude/hooks/check_bash_safety.py

**Vaga:** sem vaga reservada — entra quando uma vaga liberar, na fila da OQ-11 do PLAN-194,
e nunca antes do land da parte A (mesmo arquivo).

**Herdado no debate r1 (a W2 é a onda que toca o E3):** (1) a mensagem da recusa de leitura
por `python3 -c` (A3), que saiu da W1 — a regra de argv torna essa recusa MAIS frequente, então
a mensagem certa chega no mesmo land ou antes; (2) a lacuna argv (OQ-4: o ramo `-c` de
interpretador faz `break` depois do corpo, `check_bash_safety.py:2335-2345`); (3) o ramo do
verbo de busca de arquivos no E3 varre TODOS os tokens restantes do comando e dispara também
quando o nome do verbo aparece como argumento (`:2430-2432`, `:2247`) — falso-positivo A3-5,
**observado duas vezes ao vivo** (**→ item C10: há uma terceira ocorrência**): na rodada 1 do
debate, um comando composto só de leitura de um crítico; e na S360 um comando do CEO que
gravava texto de plano por here-doc, sem executar o verbo de busca, mas citando o nome dele
como texto e um caminho de ADR adiante — os dois foram
recusados com a mensagem de edição por `-exec sed`, que não se aplicava; a varredura fica
limitada ao segmento, como já são `tee`/`sed`/`cp` (**→ item C3 (1): o limite é o fim da
EXPRESSÃO do verbo de busca em termos de bash, não o segmento do léxico do E3**); (4) o contrato
de `cwd`: `NormalizedEvent` não carrega `cwd` (`_lib/contract.py:50-85`) e `decide_command(command)` não o
recebe (`:3818`) ⇒ **decidido no debate r2: a W2 fecha só o `cd` DENTRO do mesmo comando**;
o `cd` entre chamadas é o residual 11 do Goal, com FU próprio
(`PLAN-195-FOLLOWUP-cwd-between-calls`) — ler o `cwd` do stdin mudaria a assinatura de
`decide_command` e o `main()`, e as suítes que chamam `decide_command(command)` precisariam de
default compatível com Python 3.9; (5) a parte B usa o
MESMO caminhador e o mesmo localizador de corpo da W1 (aglomerado de opções, corpo que não vem
logo depois do `-c`); (6) `reason_code` próprio para o bloqueio de escrita canônica com alvo
computado — hoje o bloqueio canônico do E3 não emite NENHUM evento (`:3838-3841` sem
`destructive`; o fact-gate só roda sob `destructive`, `:4166-4180`).

Testes novos que provam a cura: classe `TestComputedCanonicalTarget` em
`.claude/hooks/tests/test_check_bash_safety_canonical_matrix.py` (uma linha por forma da
classe B da matriz privada, ids B-1..B-6, + os controles legítimos que seguem ALLOW, como
o esqueleto `python3 *`). **Controle negativo:** em árvore descartável, com os testes
novos e o hook SEM a cura,
`python3 -m pytest .claude/hooks/tests/test_check_bash_safety_canonical_matrix.py -k TestComputedCanonicalTarget -q`
sai com exit 1 (não 5); depois da cura, exit 0. Mesma regra de divulgação da W1; mesma
bateria do harness da W1 (`test_check_harness_config.py`, já no Check acima).
Prova com as mesmas regras (a), (b), (e), (f), (i) e (k) da W1 (N de N vermelho no HEAD de
antes do pacote; classe do motivo afirmada; controles legítimos; mutação por sub-regra; replay
diferencial; prova de emissão — o bloqueio de escrita canônica com alvo computado grava
EXATAMENTE UM `veto_triggered` com `reason_code` próprio, coisa que o bloqueio canônico do E3
hoje não faz). **Exceção declarada ao «BLOCK→ALLOW = zero» da prova (i)** (revisão Codex da
rodada 2, P2): a W2 corrige de propósito o falso-positivo A3-5, então as transições
BLOCK→ALLOW PERMITIDAS são só as do ramo do verbo de busca de arquivos limitado ao segmento,
cada uma classificada à mão no replay como falso-positivo corrigido (o comando não faz edição
canônica no próprio segmento; **→ item C3 (1): «segmento» = a expressão do verbo de busca em
termos de bash, não o segmento do léxico do E3**); qualquer outra transição BLOCK→ALLOW segue sendo defeito. A
mensagem A3 não muda veredito, só texto.
Tamanho (estimado, refeito no debate r1/r2): hook ~150-250 + testes ~100-150 = ~250-400 linhas
revisáveis; paths: 2-3 (hook, matriz, `test_check_bash_safety.py` se preciso) ≤ 8 — os
espelhos não são paths do pacote. **Divisão pré-registrada como provável (debate r2):** W2a
(mensagem A3 + segmento do verbo de busca) PRIMEIRO, depois W2b (alvo computado + argv +
`reason_code`), na mesma vaga — assim a mensagem A3 nunca chega depois da regra de argv, que
torna a recusa de leitura mais frequente; se couber, as duas num pacote só.

- [ ] Resolver expansão (variável/substituição), glob e `cd` relativo no ALVO de escrita
  (redirect/`tee`/`sed -i`/`dd of=`/interpretador) antes de casar o caminho canônico,
  reusando o esqueleto do E4 com piso de literais — sem fail-closed cego. Lacuna argv aqui
  (OQ-4, decidida 3/3 no debate r1): caminho canônico entre os operandos posicionais depois
  de um corpo `-c`/`-e` de interpretador ⇒ BLOCK, sem tentar provar se o corpo lê ou escreve.
  Controle vermelho→verde pelo `-k TestComputedCanonicalTarget` acima. — Check: python3 -m pytest .claude/hooks/tests/test_check_bash_safety_canonical_matrix.py -q -k TestComputedCanonicalTarget
- [ ] Mensagem da recusa de LEITURA por `python3 -c` (A3-1/A3-3): apontar Read/`cat`/`grep`
  para leitura e separar o ramo de parse falho («corpo não tokenizável/grande; nenhum caminho
  canônico identificado»), sem allowlist de leitura; texto fixado em `TestReadRefusalMessage`.
  — Check: python3 -m pytest .claude/hooks/tests/test_check_bash_safety_indirect_exec.py -q -k TestReadRefusalMessage
- [ ] Limitar ao segmento a varredura do verbo de busca de arquivos no E3 (A3-5), com controle
  ALLOW para o comando composto só de leitura e controle BLOCK para a edição real (**→ item C3
  (1): «segmento» = a expressão do verbo de busca; mais uma linha BLOCK com edição canônica
  depois do terminador escapado**).
  — Check: python3 -m pytest .claude/hooks/tests/test_check_bash_safety_canonical_matrix.py -q
- [ ] Regenerar os espelhos LOCAIS e provar a identidade por `cmp` (como na W1); fora do
  commit e do Scope.
- [ ] Rail codex nas duas lanes (**→ item C7:** no máximo 4 rodadas por pacote, W2a e W2b);
  sentinel; SIGN/LAND. Sequencial DEPOIS da W1 (mesmo arquivo — nunca dois pacotes canônicos
  no mesmo arquivo em voo).

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

- OQ-1 (RESOLVIDA no debate r2, 3/3 — suficiente com denominador, definição de
  falso-positivo e replay diferencial nos dois sentidos): nível de fail-closed aceitável
  sem travar o uso normal. **Premissa corrigida:** o «≤ 3 em 7 dias» do §4.4 do guards doc
  é o orçamento de USO do kill-switch de bypass, não de falso-positivo de regra
  (`docs/security-bash-canonical-guards.md:162-168`, conferido). E o log não serve de corpus
  nem de bloqueios: o bloqueio de escrita canônica não emite nada e o destrutivo só aparece
  via shadow do fact-gate; os 685 eventos retidos do hook têm `session_id` vazio. **Direção:**
  (a) corpus sintético versionado de controles legítimos (`TestIndirectLegitAllow`); (b) replay
  offline dos comandos Bash dos transcripts locais contra `decide_command` HEAD × cura, com
  `HOME`/`CLAUDE_PROJECT_DIR` isolados (**→ item C4: isso NÃO basta; a cadeia viva exige também
  `CLAUDE_PROJECT_DIR_NATIVE` neutralizado, `CEO_AUDIT_LOG_PATH` em rascunho e controle POSITIVO
  de delta 0**) e sem executar nada — só contagens no repo, delta
  classificado à mão na evidência privada; meta: as regras de EQUIVALÊNCIA com a forma direta
  não geram nenhum bloqueio novo legítimo, e as regras heurísticas ficam abaixo de um limite
  pré-registrado na ADR-201; (c) `reason_code` por classe + contagem por 7 dias por PROJETO
  para ver a regra disparar depois do land.
- OQ-2 (RESOLVIDA no debate r2, 3/3 — a passada única aditiva e monotônica atende «os dois
  sítios consomem o mesmo caminhador»): heredoc, aspas e os dois sítios. **Decisão:** nem recursão nos dois sítios nem helper chamado pelos dois — UMA passada
  aditiva na cauda de `decide_command` sobre o léxico do E3 (Thesis item 2), que cobre o
  escopo dos dois sítios legados, tem um só ponto de evento e uma só segmentação nova (o
  achado C16 mostra o custo de duas). Here-doc é DADO, salvo quando o consumidor é shell ou
  avaliação; substituição de comando em here-doc de delimitador não citado e dentro de aspas
  duplas é PROGRAMA; o controle do `echo` com texto destrutivo citado segue ALLOW.
- OQ-3 (RESOLVIDA no debate r1, 3/3): `.mcp.json` e `CLAUDE.md` **fora** do PLAN-195. O
  oráculo dá 0 para os dois e o `CLAUDE.md` foi excluído de propósito
  (`check_canonical_edit.py:200-204`, editado a cada closeout); bloquear só no Bash criaria
  assimetria (Bash bloqueado, Write livre). A W2 consome `_CANONICAL_GUARDS` como está;
  ampliar o conjunto é decisão do guarda de edição canônica em plano próprio (FU
  `PLAN-195-FOLLOWUP-canonical-guards-set`), com a recomendação registrada de medir antes o
  custo de cerimônia do `CLAUDE.md`.
- OQ-4 (RESOLVIDA no debate r1, 3/3): a lacuna argv fecha na **W2** — é alvo de escrita
  computado, não verbo destrutivo; uma linha na matriz e o controle ALLOW correspondente
  (operando não canônico).
- OQ-8 (RESOLVIDA no debate r2 pelo CEO, com fato do código; o Owner pode reverter): **A-8**
  (remoção por busca de arquivos com ação de remoção) **sai da W1 e da prova (opção b)** e
  vira o residual 8 do Goal. Os críticos dividiram: um pediu (b) — a separação segura/insegura
  é do ALVO, e a regra (a) recusaria a limpeza confinada do próprio clone (lição S358); outro
  pediu (a) estreita — BLOCK só quando a expressão da busca não tem nenhum teste, por paridade
  com a forma direta. **O fato que decide:** o trio só bloqueia a remoção recursiva quando há
  as opções recursiva E de força juntas (`check_bash_safety.py:383-418`); a remoção recursiva
  SEM força passa hoje, e sem terminal na entrada padrão ela não pergunta antes de remover
  arquivo protegido contra escrita, removendo tanto quanto a busca sem teste (comportamento
  especificado pelo POSIX para a remoção; inferido, não medido no substrato). Logo o
  equivalente direto da A-8 é uma forma que o trio PERMITE, e o invariante de
  não-permissividade (Thesis item 5) não exige bloqueá-la. A pergunta de fundo é de POLÍTICA e
  vale para as duas formas juntas — vai para a OQ-10.
- OQ-9 (RESOLVIDA no debate r2, 3/3 — conflito K1 fechado): **alimentadores opacos.**
  Definição pela forma: um interpretador chamado SEM operando de programa, que lê o programa da
  entrada padrão, de um descritor ou de uma substituição de processo; ou a avaliação da saída
  de uma substituição. Um interpretador com programa VISÍVEL que recebe DADOS pela entrada
  padrão NÃO é opaco. Decisão: BLOCK com mensagem acionável + `reason_code` próprio, nunca ASK
  (o hook não tem esse canal; sem humano, ASK é travamento). Condições escritas no conteúdo
  mínimo da W1-ADR: tabela por sub-forma (equivalência × heurística; limite como número
  absoluto; denominador; definição de falso-positivo), fixada ANTES do replay; rebaixamento por
  sub-forma decidido em cerimônia, não em runtime; a sub-forma rebaixada continua emitindo o
  mesmo `reason_code` com desfecho «faria bloquear» e vira residual; baixador de rede como
  produtor visível nunca é rebaixado; kill-switch com dois níveis que emite
  `learning_rail_disabled` quando desligado.
- OQ-10 (nova, debate r2 — **Owner**, decidir depois do replay da OQ-1): **remoção recursiva
  sem a opção de força** — hoje ALLOW no trio — e a A-8 (busca com remoção) são a MESMA
  pergunta de política: bloquear a remoção recursiva mesmo sem força? Consequência de SIM: as
  duas entram juntas, com paridade, e a limpeza do próprio clone passa a exigir a rota
  sancionada (que a forma direta com força já exige hoje). Consequência de NÃO: as duas seguem
  residuais declarados (itens 8 e 9 do Goal). O replay (OQ-1) mede quantos comandos legítimos
  cada opção recusaria antes de o Owner decidir. **→ item C8: regra padrão fixada pelo Owner em
  2026-10-01 — decide pelas contagens do replay; sem replay pronto na abertura da W1b, a
  resposta é NÃO, e o SIM vira o pacote W1c.**
- OQ-6 (Owner, W3) — só o que resta: **ligar ou não o sandbox depois da medição.** (Medir
  antes de ligar já está decidido.)

## How to continue

Ler este plano, a evidência privada do Owner fora do repositório (matriz concreta + método
de sonda; síntese §U2/§6) e a memória `project-s359-urgency-triage`. **W0:** executar já
(decisão do Owner S359), fora de qualquer janela de SIGN, depois do flip `draft → reviewed`
feito pelo CEO com base na aprovação em chat (**→ item C6: o flip é do Owner; o CEO só o
registra**). **Debate L3:** rodadas 1 e 2 (S360) — ler
`PLAN-195/debate/round-1/consensus.md` e `round-2/consensus.md`; a rodada 2 fechou OQ-1/2/8/9,
abriu a OQ-10 (Owner, depois do replay) e reduziu os dois VETOs a texto, aplicado neste plano;
os portadores confirmam a retirada no próprio arquivo da rodada 2 (sobre o sha `9894151f…`;
**→ item C11:** a reconfirmação sobre o sha que contém o apêndice é pré-requisito da W1 e da
edição do hook, e segue PENDENTE até ser registrada em `PLAN-195/debate/`). O flip
`draft → reviewed` é do Owner (portão humano, PLAN-SCHEMA §4), sobre o plano revisto (feito em
2026-10-01). **W1 (parte A):** na 2.ª
vaga, depois da W1 do PLAN-194 ocupar a 1.ª (ver «Regra de WIP»; **→ item C2:** a W1-ADR landa
depois da W1 do PLAN-194), em três pacotes na mesma
vaga — W1-ADR (`PROPOSED`) → W1a → W1b; antes, o instrumento de replay de falso-positivo
(OQ-1); rodar o oráculo `--is-canonical` de novo em cada path; provar N de N vermelho→verde
em árvore descartável, sem executar nenhum comando da classe; regenerar os espelhos LOCAIS e
provar por `cmp` (fora do commit); bateria com as 9 suítes do Check da W1; rail nas duas
lanes com teto de 4 rodadas por pacote; SIGN/LAND do Owner. **W2 (parte B):** sem vaga
reservada, depois do land da W1b; herda a mensagem A3, a argv, o segmento do verbo de busca
de arquivos e o contrato de `cwd`. **W3:** medir; o Owner decide ligar ou não; se ligar, na
ordem da colisão com a W6 do PLAN-194.

## Success criteria

- [ ] `docs/security-bash-canonical-guards.md` §6 e `docs/threat-model.md` vetor 2
  descrevem a cobertura REAL (classe indireta/computada declarada não-coberta ou curada) —
  Check: grep -n '^### §6.6 ' docs/security-bash-canonical-guards.md && ! grep -nF -e 'hits the PreToolUse matcher AGAIN' -e 'before sending tokens to Claude' -e 'Five vector classes remain advisory' docs/security-bash-canonical-guards.md
- [ ] O hook recusa as formas da classe que a ADR-201 declara cobertas (formas diretas
  irmãs, indireção de destrutivo, verbo computado com marcador destrutivo literal, escrita
  canônica com alvo computado), nenhuma forma reconhecida recebe veredito mais permissivo que
  a sua forma direta, os controles legítimos seguem ALLOW (sem lockout) e o resto da classe
  fica como residual declarado pela forma na ADR-201 e na §6.6 — Check:
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
- S360 (2026-10-01, debate L3 rodada 1): proposta em `PLAN-195/debate/round-1/proposal.md`;
  três críticos (Opus, só leitura, proibidos de executar formas da classe): 3× ADJUST, dois
  VETOs condicionais a TEXTO (um de escopo estreito — cobertura/FPR/operabilidade; outro sobre
  a W1 como especificada). Revisão Codex `--uncommitted` da proposta e das críticas: APPROVE.
  Seis verificadores read-only conferiram 36 afirmações das críticas no código
  (`wf_430c1885-742`): 28 TRUE, 8 PARTIAL, 0 FALSE, mais um achado novo (divergência da regra
  de comentário entre tokenizadores, descrito pela forma; detalhe na evidência privada).
  Ajustes aplicados neste plano (índice em `round-1/consensus.md` §Plan adjustments): raiz =
  decisão posicional sobre fatiamento ingênuo; passada aditiva única; piso de literais fora da
  posição do verbo; ASK puro rejeitado; W1 → W1-ADR (`PROPOSED`) → W1a → W1b; prova N de N com
  classe do motivo; bateria de 9 suítes; observabilidade; regra de parada do rail; W2 herda a
  mensagem A3, a argv, o segmento do verbo de busca de arquivos e o `cwd`; OQ-1 corrigida
  (premissa do §4.4 era falsa); OQ-3/OQ-4 resolvidas 3/3; OQ-8/OQ-9 novas; orçamento refeito
  (parte A ~0,8-1,5 M, 3-4 sessões). Veredito da rodada: RUN-ANOTHER-ROUND. O falso-positivo
  A3-5 bloqueou ao vivo um comando do próprio CEO durante a edição (registrado na W2).
  Status inalterado (`draft`).
- S360 (2026-10-01, debate L3 rodada 2): os três críticos retomados com contexto. Um ACCEPT e
  dois ADJUST com VETO reduzido a texto, sem pedir rodada 3. Fato novo conferido no código: o
  léxico do E3 não é fiel ao bash (o `shlex` encerra token num `#` no meio de palavra e apaga o
  tipo de aspas; o normalizador do E4 não conhece comentário) ⇒ pré-léxico fiel ao bash na
  Thesis item 2 e na W1a. Aplicado: lista de residuais escrita UMA vez no Goal (12 itens);
  chaves por pertença; dono da substituição entre aspas duplas e em here-doc não citado;
  observabilidade sem ação nova (`veto_triggered` passthrough; `emit_generic` descarta ação não
  registrada em silêncio, conferido) e prova de emissão (k); OQ-9 resolvida com definição pela
  forma e condições; kill-switch de dois níveis com `learning_rail_disabled`; mudança de
  contrato da tag `destructive` declarada; OQ-1/OQ-2 resolvidas; OQ-8 resolvida pelo CEO com
  fato do código (o trio só bloqueia recursiva + força; a forma sem força passa) ⇒ A-8 fora da
  W1, e a política vai para a OQ-10 (Owner); `cwd` entre chamadas fora (residual 11);
  divisões W1a-1/W1a-2 e W2a/W2b pré-registradas como prováveis; Alternativa 1 corrigida
  (contradição com a Thesis item 4). Status inalterado (`draft`).
- S361 (2026-10-01, aceite do Owner): sobre o plano revisto no debate, o Owner aceitou em
  bloco, no chat, a recomendação — o corpo revisto no debate (sha256 `9894151f…`, PROCEED) mais
  o apêndice «Correções pós-debate S360»; o flip `draft → reviewed` ficou registrado no
  cabeçalho (`reviewed_at`, `reviewed_by`). Além do cabeçalho e desta entrada, o corpo mudou
  por remissões «→ item Cn» nos pontos principais que o apêndice corrige (guias de leitura, não
  exaustivas; algumas trazem tetos de paths ajustados); as correções C1 a C11 estão no fim do
  arquivo. A reconfirmação dos dois VETOs sobre o novo sha está pendente
  (item C11). Nada executado; a transição `reviewed → executing` é do CEO e ocorre no commit da
  W0.

## Correções pós-debate S360 (aceitas pelo Owner na S361, 2026-10-01)

O corpo acima é o texto fechado no debate (sha256 `9894151f…0406`, PROCEED), acrescido do
cabeçalho novo, das remissões «→ item Cn» e da entrada S361 do histórico; por isso o sha256 do
arquivo inteiro já não é o do debate (item C11). O Owner aceitou o plano revisto em bloco na
S361 (decisão de 2026-10-01 sobre o plano revisto no debate: aceitar, com as correções num
apêndice) e escolheu registrar as correções achadas depois do debate neste apêndice, e não
reescrever o corpo. **Onde o corpo e este apêndice divergem, vale o apêndice.** Os pontos
principais do corpo que o apêndice corrige carregam a remissão «→ item Cn»; elas são guias de
leitura e não esgotam os pontos afetados. O item C5 reafirma regra que o corpo já traz (Prova,
«Divulgação»), e o item C9 só registra a decisão do Owner sobre a OQ-8; nenhum dos dois tem
remissão no corpo. Na dúvida, vale o apêndice. Os fatos abaixo foram conferidos no disco em
2026-10-01, sobre o `HEAD` `e2e6bd1b`.

**C1 — W0, item 2: o doc de ameaças NÃO recebe o flip de status.** O item 2 da W0 manda rodar
`check-threat-model-freshness.py` por último e commitar o flip. Não siga esse texto. Faça assim:

- Rode SÓ `python3 .claude/scripts/check-threat-model-freshness.py --dry-run --verbose`. Sem
  `--dry-run`, o script grava `Status: stale` em `docs/threat-model.md` e emite o evento
  `threat_model_freshness_breach` na cadeia de auditoria viva (`emit_freshness_breach`, chamada
  só no ramo sem a flag).
- Nunca commite `Status: stale` e nunca mova `Last updated`. `docs/threat-model.md:24` e
  `:35-44` registram a decisão da S329: sem re-revisão real, o status permanece `accepted`.
  Commitar o flip derruba `test_status_is_accepted`
  (`tests/integration/test_threat_model_coverage.py:316-318`) e bloqueia qualquer mudança não
  relacionada.
- Acrescente ao cabeçalho de `docs/threat-model.md` uma NOTA ESCOPADA, no molde das duas já
  existentes (PLAN-179 W4; S329 / PLAN-185 W3): diga o que foi revisto de fato (o vetor 2 e a
  classe da W0) e não afirme re-revisão do documento inteiro.
- Inclua `python3 -m pytest tests/integration/test_threat_model_coverage.py -q` na bateria do
  land da W0, além do Check da W0.

**C2 — Leque real da W1-ADR e regra sobre emendas e arquivos de ADR (decisão do Owner, S361,
2026-10-01).** O «Paths: 1» da W1-ADR
está errado. Um arquivo de ADR novo arrasta outros arquivos, e landar o ADR-201 sozinho deixa
três gates vermelhos (índice, contagem em documentos, contagem no `CLAUDE.md`). O leque real:

- o ADR-201 (novo);
- o índice `.claude/adr/README.md` — oráculo 1 (canônico), tabela gerada; o passo «ADR index
  drift (generate-adr-index --check)» do `validate.yml` reprova qualquer deriva. Rode
  `python3 .claude/scripts/generate-adr-index.py --write` na rodada com sentinel, nunca à mão;
- oito documentos de contagem que citam 198 ADRs: `README.md`, `README.pt-BR.md`,
  `docs/README.md`, `docs/ARCHITECTURE.md`, `npm/README.md`, `docs/CTO-GUIDE.md`,
  `docs/FAQ.md` e `docs/GUIA-COMPLETO.md`. O `verify-counts.sh` os confere (lista `DOCS`);
  `INSTALL.md` e `docs/WHAT-WE-ARE.md` estão na mesma lista, mas não citam esse número;
- `CLAUDE.md:54` («198 ADRs»): o `check-claude-md-claims.py` o confere, regex de ADRs com
  tolerância 0 (`:141-147`), no `validate.yml`. O `CLAUDE.md` só muda no fechamento de sessão
  (`CLAUDE.md` §0, disciplina de cache) — por isso o pacote landa junto de um fechamento. O
  arquivo tem 39.912 bytes e o gate reprova em 40.000 ou mais (`validate-governance.sh:632-633`,
  perfil completo): trocar 198 por 199 não muda o tamanho, e cabem no máximo 87 bytes de
  crescimento em qualquer outra edição do pacote;
- o preâmbulo do `CHANGELOG.md` (a afirmação «as of v1.4.1: … 198 ADRs …»): conferido — uma
  regra própria do `verify-counts.sh` (CHANGELOG HEADER RULE) exige contagem exata e reprova
  também o matcher morto. Ele conta como décimo documento de contagem; a pergunta feita ao
  Owner sobre os arquivos de ADR contou nove (os 8 documentos mais o `CLAUDE.md`). O `CHANGELOG.md` é também path da W7 do PLAN-194 (tabela
  «Paths × oráculo» de lá): os dois pacotes não podem estar em voo ao mesmo tempo, e quem
  landar por último re-deriva a contagem.

A W1b (flip para `ACCEPTED`) muda a linha de status do índice; as contagens não mudam no flip,
porque o número de arquivos fica igual. **Regra decidida pelo Owner (2026-10-01) sobre emendas e
arquivos de ADR:**

- Emenda DENTRO do ADR existente só quando for aditiva (precedente: ADR-149 A3; exemplo dado ao
  Owner: a W7a do PLAN-183 sobre o ADR-158). Mudança semântica ganha arquivo de emenda, pela doutrina
  anti-churn (`.claude/adr/README.md:59-64`). O ADR-201 é arquivo novo; a W2 do PLAN-194
  (drenagem forçada contra o ADR-055-AMEND-3) e a W3 do PLAN-194 (pin automático contra o
  ADR-182) provavelmente exigem arquivo de emenda — o debate delas confirma.
- O pacote que cria arquivo de ADR ou de emenda (ADR-201, W7b do PLAN-183 e, provavelmente, W2
  e W3 do PLAN-194) ganha uma 4.ª exceção ao teto de 8 paths: o índice e os documentos de
  contagem ficam fora da conta e se re-derivam no LAND. O texto do bloco «Regra de WIP» que
  lista as exceções mora no PLAN-194.
- Um pacote de ADR por vez, landado junto de um fechamento de sessão.

**Ordem de LAND da W1-ADR (regra nova da S361; o corpo fixava só a ordem das vagas).** A
W1-ADR landa depois da W1 do PLAN-194, que ocupa a 1.ª vaga (decisão do Owner da S359, bloco
«Regra de WIP»). As duas não landam juntas porque há UM lander e UMA janela de SIGN: um pacote
canônico passa pela cerimônia de cada vez. O motivo NÃO é colisão de arquivos nem o leque que o
ADR arrasta. A W1 do PLAN-194 toca só workflows de CI: `.github/workflows/validate.yml` e, só se
o censo W0.1 os marcar, outros workflows (item W1.5); o template do adopter entra em land livre
separado (item W1.4). Fonte: PLAN-194, seção «W1 — CI pronto para Ubuntu 26.04», campo
«Paths». Nenhum desses arquivos é o ADR-201, o índice ou um documento de contagem.

**C3 — Três itens que o consenso da rodada 2 deixou para a abertura da wave dona**
(`PLAN-195/debate/round-2/consensus.md:169-190`). Eles não bloqueiam. A wave dona os incorpora
ao abrir, e o rail do pacote confere.

1. *W2 — limite da varredura do verbo de busca.* O critério da exceção A3-5 («sem edição
   canônica no próprio segmento») não pode usar o segmento do léxico do E3. O léxico corta por
   pertença de string a `_E3_TERMINATORS` (`check_bash_safety.py:2097`), e no modo POSIX o
   terminador escapado ou citado da ação de execução do verbo de busca vira a mesma string do
   separador real. O limite é o fim da EXPRESSÃO do verbo de busca em termos de bash, com o
   tipo de aspas do pré-léxico (Thesis item 2 (d)). A classificação manual do replay julga a
   invocação inteira. Entra uma linha BLOCK de controle com edição canônica depois do
   terminador escapado.
2. *W1-ADR e W1a — documento do esquema.* Se a ADR-201 estender `_LEARNING_RAIL_ENUM` e
   `_LEARNING_SWITCH_ENUM`, o `SPEC/v1/audit-log.schema.md:484` (canônico; oráculo 1, conferido)
   documenta as mesmas enumerações fechadas, com a coerção, na linha do `learning_rail_disabled`.
   Ele muda no mesmo pacote (e a linha de versão do SPEC, se a convenção pedir). A tabela
   «Oráculo canônico» do corpo não lista esse arquivo: ele entra como path condicional da W1a,
   que passa de ≤ 4 para ≤ 5 paths nesse caso. A W1-ADR registra isso em uma oração.
3. *Prova (k).* O teste do evento de desarme distingue os DOIS níveis do kill-switch («só
   heurísticas» e «passada inteira») no conteúdo do evento. Os dois níveis são riscos
   diferentes.

**C4 — Isolamento da cadeia viva no replay (OQ-1).** O replay chama `decide_command`, e o hook
emite eventos de auditoria. Isolar `HOME` e `CLAUDE_PROJECT_DIR`, como o texto da OQ-1 pede, não
basta. O replay deve:

- neutralizar `CLAUDE_PROJECT_DIR_NATIVE` — o portador de maior precedência do resolvedor
  (`_lib/runtime_paths.py`), que um `HOME` ou `CLAUDE_PROJECT_DIR` isolado não redireciona;
- apontar `CEO_AUDIT_LOG_PATH` para um ARQUIVO dentro de um diretório de rascunho (a variável é o
  caminho do arquivo de log; log, chave, trava, erros e sal resolvem do diretório dele);
- trazer um controle POSITIVO de delta 0: no mesmo processo e com o mesmo isolamento, emitir um
  evento de controle e provar que ele aterrissa no diretório de rascunho, enquanto a cadeia viva
  fica com delta 0 (tamanho e último elo, antes e depois). Delta 0 sem esse controle não
  distingue «isolou» de «não emitiu».

Precedente: a suíte já gravou 2.356 eventos na cadeia viva pela janela de coleta. O
`pytest --collect-only` do `verify-counts.sh` importava um módulo que emitia antes de qualquer
fixture de sessão, e a isolação de fixture não cobria essa janela. Ali, apontar o portador de
maior precedência para um rascunho não redirecionou: delta 124 na viva (`CLAUDE.md` §5, S326;
`_lib/test_isolation.py`, Axis 3).

**C5 — Strings concretas fora do repositório público até o commit da cura.** O teste novo da
W1a/W1b (`test_check_bash_safety_indirect_exec.py`) e o da W2 (`TestComputedCanonicalTarget`)
carregam strings concretas da classe. Elas entram no repositório público SÓ no commit da cura do
pacote correspondente. A regra já consta no corpo (Prova, «Divulgação», e a tabela de decisões
do Context) e fica reafirmada. Ela vale para qualquer cópia versionada do teste, por exemplo um
patch de cerimônia ou um registro de rodada de rail. A matriz privada e a classificação manual do
replay ficam fora do repositório.

**C6 — Quem faz o flip `draft → reviewed` (contradição resolvida).** O corpo diz duas coisas: a
W0 afirma que «o CEO faz o flip» com base na aprovação em chat (l. 319-321 da versão do debate);
o «How to continue» afirma que o flip «é do Owner» (l. 718-719). Vale a segunda leitura, por três
apoios do texto do debate: o consenso da rodada 2 diz duas vezes que o flip é «do Owner»,
portão humano (`round-2/consensus.md:34` e `:193`); o PLAN-SCHEMA §4 define `draft → reviewed`
como o human-gate; e o trecho da W0 foi escrito na S359, antes do debate, para liberar a W0
sem esperar o debate. As duas leituras se conciliam: a DECISÃO é
do Owner, em chat (PLAN-SCHEMA §10: revisão informal em chat é o contrato), e o CEO só EDITA o
cabeçalho depois do aceite explícito. Foi o que ocorreu: aceite em bloco na S361 (2026-10-01,
sobre o plano revisto no debate), registrado em `reviewed_at` e `reviewed_by`. O CEO não faz o flip por conta
própria. A transição `reviewed → executing` é o self-gate do CEO (PLAN-SCHEMA §4) e ocorre no
commit da W0.

**C7 — Rail com no máximo 4 rodadas por pacote.** A regra de parada do corpo («Regra de parada
do rail», pré-registrada no debate r1) permanece sem mudança, e o Owner a reafirmou na decisão de
2026-10-01 sobre o plano revisto no debate. Ela
vale para cada pacote da parte A — W1-ADR, W1a (ou W1a-1 e W1a-2, cada uma com o seu teto), W1b e
o eventual W1c. Vale também para a W2 (W2a e W2b): o corpo não repete o número ali, e esta é a
leitura adotada, porque o modelo de operação v2 pede parada pré-registrada por pacote
(`CLAUDE.md` §5). Não existe quinta rodada: o que sobra vai para o anexo da rodada final, e
NO-GO só por P0 ou por afirmação falsa.

**C8 — OQ-10: regra padrão (decisão do Owner, S361).** A OQ-10 (remoção recursiva sem a opção
de força e A-8) se decide pelas contagens do replay da OQ-1: quantos comandos legítimos distintos
cada opção recusaria, que é o que o corpo da OQ-10 já pede. Se o replay não estiver pronto na
abertura da W1b, a resposta é NÃO, e os itens 8 e 9 do Goal seguem residuais declarados. O SIM,
quando vier, vira o pacote W1c: as duas formas entram juntas, com paridade, no mesmo arquivo do
hook, depois do land da W1b e na mesma vaga (um pacote canônico por arquivo). Se o W1c exigir
emenda ao ADR-201, vale a regra sobre emendas decidida pelo Owner (item C2). A decisão continua
do Owner (OQ-10), tomada sobre essas contagens.

**C9 — OQ-8 mantida.** O Owner manteve a OQ-8 como o CEO a resolveu no debate r2 (decisão de
2026-10-01 sobre o plano revisto no debate): a remoção por busca de arquivos com ação de
remoção (A-8) sai da W1 e da prova, e vira o residual 8 do Goal. O fato do código que decide: o trio só bloqueia a remoção recursiva COM a opção de
força (`check_bash_safety.py:383-418`); a forma sem força passa hoje. O Owner pode reverter,
como a própria OQ-8 registra; a reversão passa pela OQ-10 (item C8).

**C10 — Dado novo de falso-positivo para o replay (OQ-1).** Houve uma terceira ocorrência ao
vivo do falso-positivo A3-5, durante a revisão de planejamento que originou estas correções: o
guard bloqueou um comando de busca de arquivos somente de leitura, na mesma linha de um `grep`
sobre um arquivo canônico, com a mensagem de edição por `-exec sed`/`-i` — que o comando não
tinha. Fonte: relato do CEO. Não há log que o reproduza, porque o bloqueio canônico do E3 não
emite evento (W2, item 6). Uso: o replay da OQ-1 inclui esse comando, ou a forma dele, como
caso rotulado. Com a cura da W2, a transição BLOCK→ALLOW dele só vale pela exceção da prova (i)
se o comando não fizer edição canônica no PRÓPRIO segmento (o limite está no item C3 (1)); fora
disso, é defeito. Registre contagem e denominador no pacote, e mantenha as strings fora do
repositório (item C5).

**C11 — Reconfirmação dos VETOs: PENDENTE.** A retirada dos VETOs da rodada 2 está presa ao
sha256 `9894151f…0406` do plano (`round-2/consensus.md:8-9` e `:151-167`), e o Threat Detection
Engineer declarou que a confirmação não se estende a outro texto. O novo cabeçalho, as
remissões «→ item Cn» no corpo, a entrada S361 do histórico e este apêndice mudam os bytes do
plano. Os dois portadores — Security Engineer e Threat Detection Engineer — reconfirmam sobre o
sha que contém este apêndice. A reconfirmação será registrada no diretório do debate
(`.claude/plans/PLAN-195/debate/`) DEPOIS do commit deste apêndice; este texto não registra
nenhum resultado. O estado dos dois VETOs sobre o texto novo é «não reconfirmado» até lá. O
meio, conforme a decisão do Owner de 2026-10-01 sobre o plano revisto: `SendMessage` ao nome do
agente, se ainda resolver; senão, um re-spawn com o diff integral do arquivo contra o sha
`9894151f…0406` (cabeçalho, remissões, histórico e apêndice); o portador computa o sha256 do
arquivo inteiro, como na rodada 2. A pendência não bloqueia a W0 (doc-only; o debate L3 é
pré-requisito só de W1 e W2). Para a W1, valem os pré-requisitos comuns e o checklist da W1
(debate fechado com PROCEED, o que inclui esta reconfirmação): ela precisa estar registrada
antes do início da W1 e, em qualquer caso, antes de qualquer edição do hook (W1a, W1b e W2).
