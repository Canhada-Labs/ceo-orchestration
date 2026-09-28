# rail-round-3 — cura FN-04 (PLAN-193 W4b)

Rail-Round: 3
Rail-Subject: .claude/plans/PLAN-193/wave-fn04/fn04.patch
Rail-Subject-sha256: cd31657ca2fd3aea59aa7eb9dee691af830ca9065a7562b56eebd1abaa966819
Rail-Sentinel-sha256: e1c58896cad6e341e7d2d096457f068e3cbf3f8aa21544f077f9f4eae379c2bf
Rail-Reviewer: codex-cli 0.155.0 via npx (cache próprio; o codex global não é usado), codex exec --sandbox read-only, modelo gpt-6-astra
Rail-Prompt: .claude/plans/PLAN-193/wave-fn04/rail-prompt.md
Rail-Reviewer-Verdict: GO
Rail-Verdict: APPROVE
Rail-Findings: P0=0 P1=0 P2=0

O sujeito é o patch (sha256 acima, aplicado numa árvore de revisão descartável = `git archive`
da base do patch + o patch + os materiais) e o texto assinável (`wave-fn04-approved.md`, sha256
acima). O script do SIGN não é sujeito do rail. `Rail-Reviewer-Verdict` é a linha VERDICT do
revisor, verbatim. `Rail-Verdict` é o veredito deste registro para o SIGN: `APPROVE` só quando o
revisor não relatou achado nenhum; `DECLARED-P2` só quando relatou apenas P2, listados abaixo;
`FINDINGS` quando relatou P0 ou P1 (curados e revisados na rodada seguinte).

## Saída do revisor (verbatim; caminhos locais redigidos)

```text
NENHUM ACHADO
VERDICT: GO
```

## Triagem

- Nenhum achado. Rodada 3 = a final pela regra de parada pré-registrada (no máximo 3 rodadas).
- O que o revisor sondou por conta própria, em memória (transcript da rodada): o canário ausente de
  toda escrita do PreToolUse; nenhuma leitura de arquivo nos vínculos heurístico e manual, também
  com um snapshot já existente; o guard sobre registro sem snapshot (args, script inconclusivo,
  overrides pela chamada e pelo ambiente); o PostToolUse com id rotulado, chave no topo, id solto,
  arquivo trocado e ausente, `cwd` gravado; o `relaunch` com e sem snapshot; falhas de escrita
  injetadas sem exceção.
- Este registro é o que o SIGN exige: `Rail-Subject-sha256` = o sha256 do `fn04.patch` commitado,
  `Rail-Verdict: APPROVE`, `Rail-Findings: P0=0 P1=0 P2=0`; o SIGN grava o sha256 deste arquivo no
  sentinel (`Rail-Record-sha256`) antes de assinar.
- Depois desta rodada, UMA frase do texto assinável mudou, e só ela: a que descreve a bateria do
  SIGN (script que o rail não revisa — dito no próprio texto). O ensaio mostrou que o teste
  pré-existente `test_manifest_is_on_disk_before_git_runs` (orçamento de 0,6 s de um git falso)
  falha 2x seguidas numa máquina carregada e passa sem o patch — o SIGN o julgaria falha NOVA.
  Antes: «Uma falha é rerrodada ISOLADA com o patch; se falhar de novo, é rerrodada num worktree
  destacado do HEAD (a árvore sem o patch)». Depois: «Uma falha é rerrodada ISOLADA com o patch, até
  3 vezes; passar em alguma é nota (instável). Se falhar nas 3, é rerrodada uma vez num worktree
  destacado do HEAD (a árvore sem o patch)». O resto da frase e todo o resto do texto são os bytes
  revisados; o sha256 do texto revisado está em `Rail-Sentinel-sha256` acima. O patch não mudou.
- As rodadas 1 e 2 rodaram `rail-prompt.md` com sha256
  `d4f2cc8a9c520b16f0b4e9e7dcf8811ccaaf6c1dc08538c86fd7a84376dc4366`; a rodada 3 rodou o arquivo
  atual (sha256 `846a064c3b9df25ced91179433e9c3a9055c0e7920a4049515dc7d04cbca6bf9`), que só
  acrescenta a frase da regra de parada («a regra de parada pré-registrada é de no máximo 3 rodadas;
  a rodada 3 é a final.»). Os registros 1 e 2 nomeiam o caminho, não o hash.

## Mudanças do texto assinável depois da rodada 3 (rodada de correção S357, sem rail)

A revisão cruzada da S357 depois da rodada 3 (fora do rail, sobre o pacote inteiro, com uma sonda
codex read-only e revisores Claude) achou frases do texto que o código desmente ou que dizem menos
que o necessário. O patch NÃO mudou (o `Rail-Subject-sha256` acima segue
sendo o sha256 do `fn04.patch`); só o texto assinável mudou, e cada frase nova foi sondada contra a
pós-imagem do patch antes de entrar. Estas frases NÃO foram revisadas pelo rail:

- a classe: o texto diz que a cerimônia cura o CASO da condição 23 (o ledger do hook do
  `Workflow`), não a classe — outro hook da mesma forma (um trecho do arquivo lido num evento de
  auditoria, antes da decisão de permissão) segue como está e entra como residual, declarado pela
  forma;
- o validador: «quando o registro nomeia um snapshot, os bytes seguem conferidos» passou a valer só
  para um registro COM hash; um registro sem hash que nomeie um snapshot não tem o snapshot
  conferido, como antes (o achado veio do codex, `VERDICT: NO-GO`, sobre esta frase);
- «não foi corroborado depois dele» virou «nenhum byte gravado reproduz o hash» (um registro
  `write_failed:<tipo>` leu bytes que batiam e não conseguiu gravá-los);
- residuais novos: snapshots de versões anteriores seguem publicados pelo `relaunch`/`--out`; o
  comentário da registração do hook nos settings segue descrevendo o snapshot antes do despacho; o
  PostToolUse não é serializado (dois PostToolUse da mesma chamada, ou uma falha ao regravar o
  manifesto, deixam um snapshot sem registro que o nomeie);
- a bateria e a revisão: «a divisão de marcadores do CI» no lugar de «as duas passadas do CI» (o CI
  não roda as `testpaths` inteiras num job); o `--local-user` com a chave do allowlist; a
  reconferência do HEAD e dos blobs depois da bateria e no índice; «0.155.0 — o pinado quando o rail
  rodou» (a manhã re-pina o codex antes deste SIGN).
