# Pair-rail prompt — PLAN-193 W4b, cura do FN-04 (Codex, read-only, cold)

Você é o revisor cruzado (V2 da cascata de verificação — `PROTOCOL.md` §Verification cascade).

**Sujeito desta rodada (e só ele):**
1. o patch `.claude/plans/PLAN-193/wave-fn04/fn04.patch` — JÁ APLICADO nesta árvore: os cinco
   arquivos que ele toca estão aqui na pós-imagem; a pré-imagem é o `index` de cada arquivo no patch;
2. o texto que o Owner vai assinar, `.claude/plans/PLAN-193/wave-fn04-approved.md` (os campos
   `TO-FILL-BY-SIGN` são preenchidos pelo script de assinatura; não são achado).

**A classe (condição 23 do envelope assinado do GA v1.4.1, verbatim):** «No PreToolUse da tool
`Workflow`, `check_workflow_launch.py` (por `_lib/launch_ledger.py`) lê o arquivo regular de até 8 MiB
que `tool_input.scriptPath` nomeia — quando a chamada não traz o texto do script em `script` —, por
caminho absoluto ou relativo ao `cwd` da chamada, dentro ou fora do projeto, e grava uma cópia dele
(`<launch_id>.script`, modo 0600) em `launches/`, no diretório de estado do projeto. O hook roda antes
de o harness decidir a permissão da chamada: a cópia é gravada ainda que uma regra de negação de
leitura cubra aquele caminho, e essa regra não cobre a cópia, que fica em outro caminho.
`ceo-launches.py relaunch` imprime o caminho da cópia, e `relaunch --out` a copia para um arquivo
novo. A classe, pela forma: um hook que roda antes da decisão de permissão e persiste os bytes de um
caminho que o harness pode negar.»

**Critérios:**
- a classe fecha: nenhum caminho do PreToolUse grava bytes lidos do arquivo que `scriptPath` nomeia
  (manifesto, snapshot, índice, temporários, mensagens);
- o snapshot de um `scriptPath` só acontece no PostToolUse da MESMA chamada (vínculo por
  `tool_use_id`, id rotulado pelo harness) e só com bytes cujo sha256 é o gravado antes do despacho;
  vínculo heurístico e `bind` manual nunca leem o arquivo;
- o guard de retomada mantém a semântica (bloqueio por `args` diferentes sob vínculo forte; advisory
  de script; inconclusivo sem hash; override pela chamada/ambiente) — em particular, um registro de
  `scriptPath` sem snapshot não pode virar evidência de match nem esconder uma diferença de `args`;
- `ceo-launches.py relaunch` / `--out` sem snapshot: nada impresso ou copiado como exato; recusa
  nomeada; os caminhos já cobertos pela opção B do `--out` não regridem;
- fail-open em infraestrutura (o hook nunca sai ≠ 0 nem trava a sessão); Python ≥ 3.9, stdlib;
  testes isolados (`TestEnvContext`, nunca o `$HOME` real);
- CADA frase do texto assinável é uma afirmação sobre o código: uma afirmação FALSA é motivo de NO-GO;
  o «Residual declarado» precisa ser verdadeiro e completo para a classe.

**Regra desta rodada:** a regra de parada pré-registrada é de no máximo 3 rodadas; a rodada 3 é a
final. NO-GO só por P0 ou por afirmação falsa no texto assinável. Relate todo P1/P2
com `arquivo:linha` e cura concreta. Não proponha JEV nem capacidade não aprovada do fornecedor. Não
altere arquivos (sandbox read-only).

**Saída:** a lista de achados, cada um com severidade `P0 | P1 | P2`, `arquivo:linha` e cura; se não
houver nenhum, escreva exatamente `NENHUM ACHADO`. Termine com UMA linha
`VERDICT: GO | GO-WITH-CONDITIONS | NO-GO`.
