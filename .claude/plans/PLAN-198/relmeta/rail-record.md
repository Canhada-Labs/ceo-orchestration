# rail-record — relmeta-144 (PLAN-198, RM da v1.4.4; molde sign-min): duas rodadas, respostas da rodada 2 por remoção e conferência do delta

Rail-Subject: .claude/plans/PLAN-198/relmeta/relmeta.patch
Rail-Subject-sha256: e01de880df3c069edc2af778071ec8fc931b5411c39ad53665a2870f72e2234b
Rail-Sentinel: .claude/plans/PLAN-198/relmeta-approved.md
Rail-Sentinel-sha256: 48c2307e4468e378cfc4dbcb551bcc720b71571e70c5e26eeb5bdebfed841da1
Rail-Data: .claude/plans/PLAN-198/relmeta/sign.tsv
Rail-Data-sha256: 95751caaa6141dbb3cd67ff79ae80bdc5fcb5d69c020818b834c2c1813f0f55a
Rail-Reviewer: codex-cli 0.166.0 (`exec review`, `sandbox_mode="read-only"`; rota de piso de versão da decisão OQ-2 do PLAN-198: o oráculo `check_pair_rail.py --verify-codex-pin` deu `compatible` / `version_floor_only`, triple aarch64-apple-darwin, sha256 do payload 39acf979729dd290f9a24ee38b2914e036c91b65952872e28ae2a6b88a7db7c1) e três lanes Claude (Opus 5.5: texto da tag, dados do SIGN e vazamento, derivador como terceira lane) nas duas rodadas; um refutador Claude único na conferência do delta
Rail-Date: 2026-11-04 (rodada 1: Codex 05:36:09Z a 05:41:25Z; rodada 2: Codex 12:40:39Z a 12:49:42Z; conferência do delta depois da rodada 2)
Rail-Reviewer-Verdict: rodada 1 — Codex APPROVE; lane texto 2 P3; lane dados 3 P3; lane derivador 1 P1 e 2 P3; rodada 2 — Codex REJECT (1 P1); lane texto 1 P1; lane dados 1 P1 (a mesma classe do P1 do Codex) e 2 P3; lane derivador 1 P2 (a mesma classe) e 1 P3; conferência do delta — 1 P1, curado por remoção
Rail-Verdict: DECLARED-P2
Rail-Findings: P0=0; o P1 da rodada 1 curado em código antes da rodada 2; os P1 da rodada 2 e o da conferência do delta curados por REMOÇÃO de texto; a classe do envoltório não autenticado pelo molde fica declarada abaixo, com a mitigação que existe

Informativos (o SIGN não os confere):

- Derivador `.claude/plans/PLAN-198/relmeta/apply-relmeta144-edits.py`: sha256 a5a49eaaae58335e6319cca164c78079259923c0d8ef2b7a9fbdf2496545cdf7.
- Envoltório `.claude/plans/PLAN-198/relmeta/hard-relmeta.sh`: sha256 fb653b73535171bd8917e9c9f7693ec89fcf9e7607439e5827ef6cd4f68a00fe.
- Registro do controle vermelho `.claude/plans/PLAN-198/relmeta/red-control.txt`: sha256 a51cdccc896c00c8ac1067bc84ad089f0a5ffb54fff52087e3e77907b00be81a.
- Sujeito de cada passo: rodada 1 = os materiais sobre o `Derived-From` da cadeia de então (o commit do plano
  com `executing`; a cadeia foi re-composta depois, sobre as mesmas condições e o mesmo CHANGELOG, com um commit
  só de testes trocado); rodada 2 = `23c47920` sobre o `Derived-From` `2af40687`; respostas da rodada 2 =
  `569261bb` e `e6b27ac1`; resposta da conferência do delta = `e67ddb11`. A cada passo, `derive-relmeta144.sh`
  re-derivou e conferiu as âncoras.
- Depois do rail, a cadeia foi re-composta com um commit de dados fora do pacote, abaixo dele: o inventário de
  variáveis de ambiente regenerado (`env-inventory-check.py --check`, um dos gates do SIGN, saía 1 nesta árvore).
  Os materiais foram re-derivados sobre o novo `Derived-From` (`ba867cde`, o commit do plano com `executing`
  re-aplicado): o patch é byte a byte o revisado e o sentinel difere do revisado só na linha `Derived-From`.
- Saídas verbatim, prompts e logs de cada lane: fora do repositório, com estes sha256: rodada 1 —
  `cd7fca9a7eae1dfc23106d6824eeb26866403acc3d32783ed3331ed4058cdb87` (saída do Codex),
  `9c8256cff880b9ec0d50bf5fe37bf57e28f90a51014a79824c2e349eafdf49af` (prompt do Codex),
  `b86c60854c09b2d8a43a7c4724ace3eb85d5fc46ae3ea19115300e23641636dd` (lanes Claude); rodada 2 —
  `1538490a8508c5d0dbc006be966d8ea8ba50a868a1f014919165eb23bd781b30` (saída do Codex),
  `e6c5b30429110472db6497cecdb58e6bfb604d9661d9c919bf3e1d157febff88` (prompt do Codex),
  `e3fce2bff987ac8c5754265c0b9c23ae40262ed4d7f16814866bc852b5e08900` (lanes Claude); conferência do delta —
  `0f540b09cab4f8dea140a7b2dde6dd414103a3a0cdbcbcf1368615d8a28b5b4b`.

## Regra de parada (pré-registrada neste esqueleto, ANTES de qualquer rodada)

- Rodada 1, completa: o Codex, dois refutadores Claude e o derivador como terceira lane, na MESMA rodada, sobre
  os mesmos materiais commitados (o patch, o sentinel com os quatro campos por preencher, os dados, o derivador,
  o `hard-relmeta.sh` e o `red-control.txt`), re-derivados sobre a cadeia final (o último land fora do pacote é
  o `Derived-From`). Nenhuma lane sai antes das outras terminarem. Pauta mínima: cada frase da headline contra
  as seções `[1.4.4]` e `[1.4.3]` e o código, inclusive as frases sobre a condição 58 e as curas do anexo da
  v1.4.0 (os parágrafos 5 e 7 da headline).
- Rodada 2: a ÚLTIMA para código e afirmações (as âncoras do derivador e as frases da headline). Entre a
  rodada 1 e a 2, cada correção re-deriva e re-commita os materiais (`derive-relmeta144.sh`), e a rodada 2
  revisa os materiais re-commitados, não o delta.
- Depois da rodada 2, um achado abaixo de P0 só se cura estreitando ou removendo texto da headline (ou do
  título), sem frase nova de resultado no lugar, ou fica declarado na seção «Declarados» deste registro. Não há
  rodada 3 para código: um P0 depois da rodada 2 para o corte e volta ao CEO e ao Owner.
- NO-GO só por condição falsa ou P0; a correção re-deriva e re-commita os materiais, e só então este registro é
  preenchido. Um texto que mude depois da rodada 2 (por remoção) recebe uma conferência de refutador único só
  para P0/P1 sobre o delta, registrada aqui; ela não abre rodada.
- O `Rail-Verdict` que o SIGN aceita é `APPROVE` ou `DECLARED-P2`, escrito sem qualificação na linha própria.

## Rodada 1

Lane Codex — última mensagem, verbatim:

```text
APPROVE: no actionable defects found. Read-only checks confirmed the derived patch bytes, sentinel consistency, and the kernelfix/redactor/annex/paragrafos controls. Filesystem-writing rehearsals and the full SIGN battery were not rerun under the read-only sandbox.
```

Lanes Claude, resumo:

- Texto da tag: P3 — o parágrafo 1 dizia que a entrada `[1.4.3]` faz parte desta release sem a ressalva que o
  CHANGELOG usa; P3 — o parágrafo 5 («cada correção é um commit que o mantenedor assinou») sugeria um contraste
  com o merge do PR #7, assinado pela mesma chave. O resto conferiu contra o código (233 e 15 recontados,
  gates do harness rodados de novo, sondas vivas).
- Dados do SIGN e vazamento: três P3 de redação (SHAs antigos no cabeçalho do `red-control.txt`; «CI» na lista
  de siglas; «uma frase sua» para os parágrafos 2 e 3, que dividem uma frase). As linhas hard rodaram neste Mac;
  `touched − scope` vazio; o oráculo concorda (o manifesto é o único alvo canônico).
- Derivador: P1 — a linha `--verify` dos dados rodava o derivador sem `-I`, e um commit só do pacote que
  acrescentasse um módulo com nome da biblioteca padrão (`argparse.py`) fazia a linha sair 0 sem as
  conferências; a frase de congelamento do sentinel afirmava mais do que o `--verify` faz. Mais dois P3.

Curas antes da rodada 2: o `--verify` sai dos dados e vira o passo 6 do `hard-relmeta.sh`, rodado com
`python3 -I -B` depois do passo 0 (a gramática do molde recusa opção antes do caminho do script); os dados
ficam com cinco linhas hard; os parágrafos 1 e 5 estreitados; as redações corrigidas; o controle vermelho
re-medido, com o controle novo do `argparse.py` (a forma antiga sai 0, o `hard-relmeta.sh` recusa).

## Rodada 2 (sujeito `23c47920`, `Derived-From` `2af40687`)

Lane Codex — última mensagem, verbatim (caminhos absolutos encurtados para `<wt>`):

```text
REJECT: a pack-only wrapper replacement can bypass the mandatory verifier without changing the rail-bound documents. The requested four claim controls and byte-exact derivation checks passed read-only probes; full clone/SIGN execution was not run under the read-only sandbox.

Review comment:

- [P1] Authenticate the wrapper before entrusting it with verification — <wt>/.claude/plans/PLAN-198/relmeta/sign.tsv:9-9
  Moving the sole `--verify` invocation into this wrapper leaves a pack-only bypass: prepend `exit 0` before its `set -u`, leaving the derivator, patch, sentinel and sign.tsv unchanged. The wrapper skips its own hash check, while sign-min's `p0_rail()` authenticates only the patch, sentinel and data hashes. In a read-only, in-memory HEAD substitution, the actual `p0_data/mat/patch/sent/rail` functions passed; running the modified wrapper through `/bin/bash -s` returned `rc=0, stdout=b''`, and `passo_hard()` accepted it without executing verification. Unlike before this change, no independent verifier follows. The existing self-check disclaimer therefore now permits skipping the mandatory derivation/freeze gate too; under the stop rule, explicitly declare this remaining bypass rather than treating isolation as its complete cure.
```

Lanes Claude, resumo:

- Texto da tag: P1 — o parágrafo 3 dizia que, numa instalação que registrou à mão o hook do envelope de custo,
  um bloqueio fica registrado no log de auditoria; com a saída limitada dos hooks desta release, o evento espera
  no spool e não está provado que chegue ao log (sonda: 0 linhas no log e 1 no spool pelo shim; 1 linha no log
  rodando o hook direto). O resto conferiu.
- Dados do SIGN e vazamento: P1 — a mesma classe do P1 do Codex (a frase de congelamento dizia que o
  `hard-relmeta.sh` confere o derivador e a si mesmo); P3 — um resíduo dizia que o `--verify` não confere outros
  arquivos da árvore (ele roda o `verify-counts` sobre a árvore); P3 — este registro citava a pasta de
  ferramentas do Owner.
- Derivador: P2 — a mesma classe; P3 — a ressalva nova do parágrafo 1 não tem âncora própria.

Respostas (regra de parada: só remoção ou declaração), em `569261bb` e `e6b27ac1`: a frase do parágrafo 3 sai
da headline, e com ela a âncora que só a sustentava (o derivador passa a conferir 16 afirmações; as contagens
do sentinel, do `red-control.txt` e do ensaio acompanham, cada controle restante tão estrito quanto antes); a
cláusula da frase de congelamento sobre o que o `hard-relmeta.sh` confere sai; as duas cláusulas de resíduo
saem. Estas remoções tocam também o corpo do sentinel e a tabela de afirmações, não só a headline; nenhuma
frase nova de resultado entrou no lugar.

## Conferência do delta (refutador único, só P0/P1, sobre `23c47920..e6b27ac1`)

P1 — a remoção da cláusula de congelamento deixou sem o contexto que definia «outro» a frase «nenhuma linha dos
dados executa outro arquivo do pacote»; lida sozinha, ela é falsa, porque uma linha dos dados roda o
`hard-relmeta.sh`. Resposta por remoção, em `e67ddb11`: a cláusula sai. O resto do delta conferiu (nenhuma
referência solta à âncora removida, `--self-check` e `--claims-only` 16/16 num clone, expectativas do ensaio e
asserções do controle vermelho não mais fracas que antes). A frase de congelamento fica: «O patch, este texto e
os dados são conferidos pelo registro do rail que o SIGN confere; o derivador roda isolado (`python3 -I -B`), sem
o diretório dele no `sys.path`.»

## Declarados (P2/P3 que ficam)

- O molde sign-min pina, por este registro, o patch, o sentinel e os dados; ele não autentica por hash o
  `hard-relmeta.sh` nem o derivador antes de rodá-los. Um commit só do pacote, depois deste registro, que mude o
  `hard-relmeta.sh` faria a linha hard 2 sair 0 sem o `--verify`. O que impede isso na assinatura é o comando do
  Owner, fora do repositório: ele só assina o commit exato que o CEO fixa nos valores do comando depois do
  commit deste registro (o `main` do origin tem de ser esse commit, e o clone também), e para antes da primeira
  linha hard se não for. Cura estrutural (o molde pinar os scripts do pacote): sem release atribuída.
- A ressalva «as changed by the v1.4.4 entry» do parágrafo 1 não tem âncora própria; ela remete à entrada
  `[1.4.4]` inteira, e a frase do CHANGELOG que a sustenta («together with the changes below») pode mudar sem
  que uma âncora reprove.
- Os commits de materiais anteriores à re-composição da cadeia citam, nas mensagens, SHAs que não são ancestrais
  do HEAD; o `red-control.txt` registra os SHAs desta cadeia.
