---
plan: PLAN-195
round: 1
created_at: 2026-10-01T02:31:34Z
---

# PLAN-195 — debate rodada 1: proposta

Plano completo: [`../../../PLAN-195-bash-guard-indirect-execution.md`](../../../PLAN-195-bash-guard-indirect-execution.md).
Este arquivo destila tese, escopo, decisões e perguntas abertas. Em caso de divergência, vale o plano.

> **Regra de divulgação (decisão do Owner, S359).** O repositório é PÚBLICO. Esta proposta e
> as críticas descrevem a CLASSE pela FORMA. Nenhuma string de comando que funcione como
> desvio entra aqui; a matriz concreta (ids A-1..A-9 e B-1..B-6, esperado × observado,
> método de sonda) fica na evidência privada do Owner, fora do repositório. Críticas
> referem-se às linhas da matriz só pelo id.

## 1. Problema

O hook `PreToolUse` `.claude/hooks/check_bash_safety.py` (canônico) recebe a string CRUA
do comando Bash. Hoje ele:

- **bloqueia** a forma DIRETA e literal de remoção recursiva, `git reset --hard` e
  `git push --force` — trio `_check_rm_rf` / `_check_git_reset_hard` /
  `_check_git_push_force` (definições `:364`, `:426`, `:447`) sobre os tokens `shlex` de
  cada subcomando, em DOIS sítios: o laço de `decide_command` (`:3891-3896`) e
  `_recheck_whole_command` (`:587-611`, laço em `:601`), chamado só no ramo fail-closed do
  *rawscan* quando o `shlex` rejeita um pedaço (`:3874-3888`);
- **bloqueia** a escrita DIRETA e literal em caminho canônico (redirect, `tee`, `sed -i`,
  corpo de interpretador `-c`, shell aninhado, `eval`/`xargs`/`find`) — E3,
  `_e3_check_canonical_path_write` + `_scan_blob` (`:2167`, `:2304`).

**Assimetria (verificada por sonda do CEO em 30/09, HEAD `429a5b39`, payload no `stdin` do
hook, sem executar o comando; `git status` idêntico antes/depois):** a recursão do E3 só
procura REFERÊNCIA A CAMINHO CANÔNICO dentro de corpos de interpretador/indireção. O trio
destrutivo NÃO recursa nesses corpos. Pela forma:

- **Classe A — execução indireta de destrutivo:** o verbo destrutivo vive dentro de
  interpretador aninhado, avaliação dinâmica, encadeador (`xargs`, `find -exec`), cano para
  interpretador, ou o NOME do comando é produzido por expansão (variável, substituição,
  separador de campo, glob) ⇒ o token literal esperado nunca aparece ⇒ ALLOW.
- **Classe B — escrita canônica com alvo COMPUTADO:** o destino canônico chega por
  variável, glob, `cd` relativo ou posição `argv` ⇒ o `_scan_blob` não casa ⇒ ALLOW.

As formas DIRETAS correspondentes seguem bloqueadas. Classe pública: "GuardFall" (nota
externa de 30/06/2026; dado não verificado por rede). Em escopo por `SECURITY.md:23`
("Bypass of the destructive-command block list"). Camadas que atenuariam: sandbox do SO
desligado (`.claude/settings.json:8`); sessão do Owner em modo auto; classificador nativo
do modo auto NÃO medido contra estas formas (ausência de dado, não prova de cobertura).

## 2. Tese

Curar a CLASSE pela FORMA, não por lista de exemplos. O substrato já tem o instrumento:
o E4 (`_e4_globify_expansions` `:3442` / `_e4_expansion_replacement` `:3377`) constrói um
"esqueleto de expansão" com **piso de literais** (`_E4_GLOB_MIN_LITERALS`) — uma expansão
que vira glob que casa tudo casa nada, e o uso legítimo dirigido por variável segue ALLOW
(nota de lockout em `:3462-3465`). Provado contra bypass real nos rounds Codex S292, com
controle vermelho→verde. A cura reusa esse esqueleto e a doutrina **fail-CLOSED em
entrada não parseável** (precedente `_recheck_whole_command`, PLAN-152 debate C4).

## 3. Escopo proposto

**W0 (livre, sem cerimônia, já autorizada pelo Owner; NÃO está em debate):** corrigir o
doc de ameaças (`docs/security-bash-canonical-guards.md` §6, `docs/threat-model.md`
vetor 2) declarando a classe NÃO coberta, pela forma, sem listar desvios; remover três
afirmações falsas de substrato (expansão antes do hook; filhos do `xargs` reentrando no
hook; forense pós-fato vendo a forma expandida).

**W1 — parte A (canônica, L3, 2.ª vaga):**
1. Recursar o trio destrutivo nos corpos de `-c`/`eval`/`xargs`/`find -exec` e no
   cano-para-interpretador, reusando `_scan_blob` do E3 e o esqueleto do E4 com piso de
   literais; cobrir os DOIS sítios do trio; herdar o fail-closed de parse sem regressão
   nos controles legítimos (texto destrutivo entre aspas num `echo` segue ALLOW).
2. Corrigir SÓ a MENSAGEM da recusa de leitura por `python3 -c` (apontar Read/`cat`/`grep`;
   separar o ramo de parse falho), sem allowlist de leitura.
3. ADR-201 registra a decisão (número reservado; 198-200 já reivindicados por outros planos).
4. Paths: hook, teste novo `test_check_bash_safety_indirect_exec.py`,
   `test_check_bash_safety.py` (se preciso), ADR-201 — ≤ 4 paths; ~260-420 linhas. Se passar
   de 400, a ADR sai num pacote próprio (W1-ADR) na MESMA vaga, antes do código.

**W2 — parte B (canônica, L3, sem vaga reservada, sempre depois da W1 — mesmo arquivo):**
aplicar o esqueleto do E4 ao ALVO de escrita (variável, substituição, glob, `cd`
relativo, `argv`) ANTES de casar o caminho canônico. Paths: hook + matriz canônica.

**W3 (sem código):** medir o sandbox do SO em árvore descartável; o Owner decide ligar
depois («Medir antes de ligar», S359). Fora deste debate salvo como alternativa.

## 4. Prova exigida

- Testes nomeados: `TestIndirectDestructiveBlocks` (uma linha por forma da classe A ⇒
  BLOCK/ASK), `TestIndirectLegitAllow` (controles legítimos ⇒ ALLOW),
  `TestReadRefusalMessage`, e na W2 `TestComputedCanonicalTarget`.
- **Controle negativo:** em árvore descartável, teste novo + hook do HEAD SEM a cura ⇒
  `pytest -k TestIndirectDestructiveBlocks` sai **exit 1** (exit 5 = nada coletado NÃO
  vale); depois da cura exit 0; `TestIndirectLegitAllow` verde nos dois lados.
- O pytest da matriz canônica sozinho NÃO prova nada hoje (linhas 17/18/34 são `xfail`,
  `_ADVISORY_ROWS`).
- **Divulgação:** o teste novo carrega strings concretas; entra no repo público só NO
  MESMO commit da cura, nunca antes.
- Bateria inclui `test_check_harness_config.py` (o gate do harness re-executa a fixture
  `bash_safety_destructive.json` contra este hook; a W7a do PLAN-183 move essa fixture).
- Espelhos `dist/` e `npm/` (ignorados pelo git) regenerados e provados por `cmp`.
- Rail codex nas duas lanes até rodada limpa; sentinel; SIGN/LAND com GPG do Owner.

## 5. Alternativas rejeitadas

1. **Fail-closed cego em toda expansão** em posição de comando/alvo — lockout documentado
   no próprio arquivo (`:3462-3465`: negaria a maioria das chamadas de interpretador
   dirigidas por variável).
2. **Allowlist de LEITURA em corpo de interpretador** — abre bypass de escrita e contraria
   a doutrina do hook (`:2492-2495`).
3. **Sandbox do SO como substituto** — cobre exfiltração e alvo fora da árvore, mas não
   remoção recursiva nem escrita canônica DENTRO da árvore; decisão ortogonal (W3).

## 6. Perguntas abertas para o debate

- **OQ-1 — orçamento de falso-positivo.** O audit-log só registra BLOQUEIOS; não existe
  corpus de comandos PERMITIDOS ⇒ o FPR da regra nova não é medível pelo log. Como
  decidir o orçamento (§4.4 do guards doc fala em ≤ 3/7d) — dogfood observado? corpus
  sintético de controles? ASK em vez de BLOCK em alguma sub-forma?
- **OQ-2 — heredoc, aspas e os dois sítios.** A recursão herda o fail-closed de `shlex`
  malformado sem regressão nos controles existentes? Recursão nos dois sítios ou num
  helper único chamado pelos dois (um sítio só deixaria o ramo de parse sem a cura)?
- **OQ-3 — conjunto protegido da parte B.** `.mcp.json` e `CLAUDE.md` entram nos caminhos
  protegidos? (Hoje não são `_CANONICAL_GUARDS`.)
- **OQ-4 — lacuna argv** (caminho canônico passado como `argv` a interpretador): fecha na W1
  (indireção de execução) ou na W2 (alvo computado)? Padrão do CEO: W2, uma linha na matriz.

## 7. O que este debate NÃO decide

Ligar o sandbox (OQ-6, Owner, depois da medição da W3); a ordem das vagas (decidida pelo
Owner na S359); o conteúdo da W0 (já autorizada).

## 8. Regra de parada (pré-registrada)

No máximo 3 rodadas. NO-GO só por P0 ou por afirmação FALSA no plano. Saída limpa =
`design-coherent`, que NÃO autoriza ship — só a cascata (V2 rail Codex + V3 GPG do Owner).
