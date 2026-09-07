---
round: 2
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — o arquétipo não tem bloco de persona em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-07T00:20:00Z
---

## Verdict

ADJUST — 3 itens BLOQUEANTES.

## Summary (≤ 3 bullets)

- A revisão de `35aa149` cura de fato o núcleo do round 1: a perna 0 de
  elegibilidade existe (§2.1), a autofagia virou controle de bloqueio com
  controle POSITIVO ao lado (AC-0.2/AC-0.3), o leitor ganhou invocação
  completa (§1 passo 1) e os 25 critérios têm `Check:`. Verifiquei em disco
  o censo do §4.7: `grep -rln "166 skills"` fora de `.claude/plans/` devolve
  **exatamente 10 arquivos**, 8 de produto + 2 de governança — a figura
  reproduz.
- **Onde é forte:** AC-0.3 e AC-0.4 são os únicos `Check:` do plano que
  asseveram um VEREDITO (saída ≠ 0, `"verdict": "RECUSA"`); AC-0.6 pode
  ficar vermelho HOJE (`rag_router.py:32` ainda carrega a referência ao
  plano inexistente). Isso é falsificabilidade real.
- **Onde é fraco:** três defeitos que só aparecem na EXECUÇÃO — um `Check:`
  que a árvore ignora silenciosamente, uma justificativa atribuída a um
  arquivo que não a contém, e uma ordem de ondas em que a AC-2.2 não pode
  ficar verde.

## Risks

**R-VP1 — P1 (BLOQUEANTE) — O `Check:` da AC-3.3 é inerte: `smoke-install.sh`
não lê argumento nenhum.**
A AC-3.3 (plano:407-408) é declarada «a perna que de fato regride» e seu
`Check:` é `bash scripts/tests/smoke-install.sh --profile core,<domínio>`.
Em disco, `scripts/tests/smoke-install.sh` **não faz parse de argv**: não há
`case "$1"`, nem `shift`, nem `"$@"` (os três `$1` do arquivo são parâmetros
de função locais — linhas 45, 53 e 386). O perfil é HARDCODED dentro do
script, `install.sh "$TARGET" --profile core,frontend` (linha 34), com
outras três instalações fixas em `--profile core` (linhas 311, 398, 453).
Consequência: a bandeira é engolida sem erro e a AC-3.3 executa **a mesma
suíte** que a AC-3.2 — duas ACs distintas com efeito idêntico, e a perna que
o §1 passo 3 nomeia como a que regride nunca é exercida. É a classe
«instrumento verde cuja pergunta envelheceu», aqui na forma «o instrumento
nunca ouviu a pergunta».
*Cura:* ou a W3 ganha uma AC própria para ENSINAR o `smoke-install.sh` a
receber o perfil (e ela vem antes da AC-3.3), ou a AC-3.3 nomeia o comando
que hoje existe e exerce o caminho `.claude/skills/domains/<parte>`.

**R-VP2 — P1 (BLOQUEANTE) — «o `CLAUDE.md` manda operar em português» é falso
no HEAD, e a frase é a que proíbe ligar a Fase 1.**
Plano:282-285: «o `CLAUDE.md` deste projeto manda operar em português, então
o caminho REAL de uso é exatamente o ramo degradado […] Ligar a sugestão por
similaridade em sessão em português é **regressão medida**». Censo em disco:
`grep -rniE "portugu"` sobre `CLAUDE.md`, `PROTOCOL.md`, `.claude/team.md`,
`.claude/frontend-team.md` e a `SKILL.md` do Gate 2 devolve **uma única
linha, e não é mandato**: `PROTOCOL.md:3`, que aponta para o espelho
`PROTOCOL.pt-BR.md` e diz que o inglês é a fonte de verdade. `CLAUDE.md`:
zero ocorrências. O idioma de operação é hábito medido, não regra escrita —
e o plano constrói sobre essa atribuição a conclusão mais forte do §4.4 (2/8
como LIMITE, Fase 1 proibida sobre ele).
*Cura:* trocar a frase pela evidência que existe (a fração medida de
consultas em português nos spawns da janela, gerada pelo instrumento) ou
rebaixar a conclusão de «regressão medida» para «regressão sob a hipótese de
consulta em português, hipótese ainda não medida». Como está, a AC-1.3
re-mede o gap sem nunca medir a PREMISSA que o torna decisivo.

**R-VP3 — P1 (BLOQUEANTE) — A ordem das ondas torna a AC-2.2 impossível de
ficar verde: `verify-counts.sh` é BIDIRECIONAL contra os documentos.**
A AC-2.2 (plano:390-391) promete «a contagem cai de 166 para 165 no patch
que arquiva a primeira skill», com `Check: bash
.claude/scripts/local/verify-counts.sh`. Mas o contrato do próprio script
(`verify-counts.sh:25-34`) diz: «The check is BIDIRECTIONAL (a doc number
that disagrees with live fails) and CROSS-FILE», com `skills (total) … exact
(166)`. Arquivar uma skill move o vivo para 165 e deixa VERMELHOS os 8
documentos de produto que carregam o literal (censo da AC-4.1, reproduzido
hoje: `CHANGELOG.md`, `CLAUDE.md`, `README.md`, `README.pt-BR.md`,
`docs/FAQ.md`, `docs/GUIA-COMPLETO.md`, `docs/GUIA-COMPLETO.pt-BR.md`,
`npm/README.md`). Ou seja: a W4 (contagem DERIVADA) é pré-requisito da W2, e
o plano a coloca DEPOIS — §1 põe «despinar o 166» como passo 5, e o §5
ordena W2 antes de W4. Duas seções que se leem como regras diferentes.
*Cura:* inverter a ordem declarada (W4 antes de W2) ou escrever na AC-2.2
que o patch de arquivamento CARREGA as superfícies derivadas — o que empurra
a W2 para além do teto de 8 caminhos (ver R-VP5).

**R-VP4 — P2 — O `Check:` da AC-1.4 não roda: `grep` sem `-r` sobre
diretório, e o diretório não existe.**
Plano:374-375: `grep -n "decisao-b" .claude/plans/PLAN-175/decisions/`.
`.claude/plans/PLAN-175/decisions` **não existe no HEAD** (a árvore tem só
`debate/` e `p1/`), e mesmo depois de criado o comando erra com «Is a
directory» — nunca devolve «o registro datado e assinado». Uma AC de
RATIFICAÇÃO do Owner cujo verificador falha por sintaxe é pior que ausência
de verificador: ela parece cumprida quando ninguém a roda.
*Cura:* `grep -rn` mais o nome do arquivo esperado, e o caminho declarado na
onda que o cria.

**R-VP5 — P2 — O teto de 8 caminhos morde a W2, e o §3 diz que morde só o
P3.**
§3 (plano:172-176) conclui: «é o que faz o teto de 8 caminhos por pacote
morder o P3 (116 skills)». Mas pela R-VP3 o patch mínimo de arquivamento é
1 `SKILL.md` movido (canônico, assinatura) + até 8 documentos de produto +
possivelmente `verify-counts.sh` (membro do manifesto do ADR-192, cerimônia
mesmo com oráculo «livre», como o próprio §6 reconhece) — 10 caminhos, dois
regimes de cerimônia, num pacote só. A W2 não cabe no modelo v2 como está
escrita e não tem decomposição própria (a W3 tem: «um pacote por vez»).
*Cura:* declarar a W2 em dois pacotes (W2a superfícies derivadas — livre;
W2b o primeiro arquivamento — canônico, ≤ 8 caminhos).

**R-VP6 — P2 — Sete `Check:` são invocações sem asserção: ficam vermelhos por
CRASH, nunca por RESPOSTA ERRADA.**
AC-0.1, AC-1.1, AC-1.3, AC-1.7, AC-2.1, AC-2.4 e AC-4.4 são da forma
«rode este programa e ele imprime JSON» (linhas 349-350, 368-369, 372-373,
380-381, 388-389, 394-395, 423-424). Nenhuma nomeia o valor que reprova. O
contraste é interno ao próprio plano: AC-0.3 exige saída ≠ 0 e AC-0.4 exige
o literal `"verdict": "RECUSA"`. O critério do round 1 (C6: «o critério não
pode ficar vermelho») foi curado no passo 5 e reintroduzido em sete outros
pontos, em forma mais fraca.
*Cura:* cada uma dessas ACs ganha o predicado que reprova (limiar, chave do
JSON, ou `--assert-*` como as da W0).

**R-VP7 — P3 — O `external_wait` está ratificado no mundo e PENDENTE no
texto.**
`§6` afirma «Uma só fonte de espera externa» e o frontmatter diz
`external_wait: none` (plano:16), mas o último item do Progress log
(plano:528) ainda diz «**PENDENTE de ratificação do Owner**». O contexto
deste round registra a ratificação («Sim, ratificar junto com o flip»,
2026-09-06 23:5x). Enquanto a linha 528 não for emendada, o plano tem duas
leituras sobre o mesmo campo — exatamente a forma que o C1 fechou.

## O que falta antes de executar (OQ para o Owner)

- **OQ-1.** Ratificar por escrito o `external_wait: none` no Progress log
  (emendar a linha 528) e flipar `status: reviewed → executing` (decisão
  4.10). O plano não se autoriza.
- **OQ-2.** Decidir a ordem: W4 antes de W2, ou AC-2.2 reescrita para
  carregar as superfícies derivadas no mesmo patch (com a W2 partida em duas
  para caber no teto).
- **OQ-3.** Decidir o destino da AC-3.3: ensinar o `smoke-install.sh` a
  receber perfil (AC nova, W3) ou substituir o comando.
- **OQ-4.** Decidir se a premissa de idioma é medida (fração real de
  consultas em português) ou rebaixada — a AC-1.4 depende dessa decisão.

## Nota de escopo

Este parecer certifica COERÊNCIA DE DESENHO do texto em `35aa149` contra a
árvore no HEAD. Não autoriza execução, não substitui o pair-rail (regra R1:
plano é docs, zero codex) e não examinou o anexo §7, que o próprio plano
marca como não revisado (plano:459-461). Caminhos pessoais elididos como
`<ROOT>` por convenção; todos os comandos citados são relativos à raiz do
repositório.
