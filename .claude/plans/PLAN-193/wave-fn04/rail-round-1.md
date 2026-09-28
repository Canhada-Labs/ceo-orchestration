# rail-round-1 — cura FN-04 (PLAN-193 W4b)

Rail-Round: 1
Rail-Subject: .claude/plans/PLAN-193/wave-fn04/fn04.patch
Rail-Subject-sha256: 1ba76cce72ab1e03b6b646d6891a593c008f8d800552e35a2c08e91483c8c5bf
Rail-Sentinel-sha256: 26d5d182f4554710b3fa18071741f4e657580af7a1c15fd63b51d57fe6be7323
Rail-Reviewer: codex-cli 0.155.0 via npx (cache próprio; o codex global não é usado), codex exec --sandbox read-only, modelo gpt-6-astra
Rail-Prompt: .claude/plans/PLAN-193/wave-fn04/rail-prompt.md
Rail-Reviewer-Verdict: NO-GO
Rail-Verdict: FINDINGS
Rail-Findings: P0=0 P1=1 P2=2

O sujeito é o patch (sha256 acima, aplicado numa árvore de revisão descartável = `git archive`
da base do patch + o patch + os materiais) e o texto assinável (`wave-fn04-approved.md`, sha256
acima). O script do SIGN não é sujeito do rail. `Rail-Reviewer-Verdict` é a linha VERDICT do
revisor, verbatim. `Rail-Verdict` é o veredito deste registro para o SIGN: `APPROVE` só quando o
revisor não relatou achado nenhum; `DECLARED-P2` só quando relatou apenas P2, listados abaixo;
`FINDINGS` quando relatou P0 ou P1 (curados e revisados na rodada seguinte).

## Saída do revisor (verbatim; caminhos locais redigidos)

```text
- **P1 — O vínculo heurístico ainda lê o arquivo.** `.claude/hooks/_lib/launch_ledger.py:992` passa `persisted_script_path` a `bind_run()`, que o lê na linha 725, mesmo sem snapshot. Reproduzido em memória: `scriptPath=/review/workflows/secret.js` e PostToolUse sem `tool_use_id`, contendo esse caminho e `Run ID: wf_0badf00d-1a`, provocam a leitura do próprio script. Isso torna falsa a afirmação de `.claude/plans/PLAN-193/wave-fn04-approved.md:46`. **Cura:** impedir leituras também pela rota de comparação da cópia no vínculo heurístico; acrescentar teste que confirme zero chamadas ao leitor.

- **P2 — O texto assinável generaliza diagnósticos que o código não fornece.** `.claude/plans/PLAN-193/wave-fn04-approved.md:45` promete motivo em `script_snapshot_why`; a linha 52 promete hash e estado do original para registros de `scriptPath` sem snapshot. Se o arquivo estiver ilegível no PreToolUse, um PostToolUse válido mantém `script_snapshot_why: null` (`launch_ledger.py:678`), e `relaunch` imprime os argumentos, mas nenhum hash ou estado atual do original (`ceo-launches.py:426`). **Cura:** restringir essas afirmações aos registros com hash obtido antes do despacho e descrever explicitamente o caso ilegível.

- **P2 — A documentação atribui ao índice um tamanho que ele não registra.** `docs/workflow-recovery.md:254` afirma que hash e tamanho são registrados no manifesto e no índice. `write_manifest()`, em `.claude/hooks/_lib/launch_ledger.py:470`, inclui somente `script_sha256` no índice. **Cura:** esclarecer que o tamanho fica apenas no manifesto.

VERDICT: NO-GO
```

## Triagem

- P1 (vínculo heurístico lia o arquivo): CONFIRMADO. `bind_run` lia o caminho da «cópia do
  harness» que a resposta nomeia mesmo sem snapshot para comparar — e esse caminho pode ser o
  próprio `scriptPath`. Cura: `bind_run` só lê esse caminho quando o registro já tem snapshot; teste
  `test_no_bind_reads_a_file_for_a_script_path_record_without_a_snapshot` (conta as chamadas ao
  leitor num vínculo heurístico e num `bind` manual: zero); mutante M9 (ler sem snapshot) morto. O
  texto assinável passou a dizer exatamente isso (a cópia do harness só é lida para comparar com um
  snapshot que o registro já tem).
- P2 (diagnóstico generalizado): CONFIRMADO. O texto assinável e o doc restringem `script_snapshot_why`
  e a saída do `relaunch` sem snapshot aos registros de `scriptPath` COM hash, e dizem que o ilegível
  antes do despacho segue como antes (sem hash, sem snapshot, sem leitura depois; rc 7 «not recorded
  at launch»).
- P2 (tamanho no índice): CONFIRMADO. O doc diz agora que o tamanho fica só no manifesto (o `sha256`
  também na linha do índice).
- Próxima rodada: 2, sobre o patch regenerado.
