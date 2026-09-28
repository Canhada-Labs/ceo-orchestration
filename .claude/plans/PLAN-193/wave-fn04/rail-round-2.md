# rail-round-2 — cura FN-04 (PLAN-193 W4b)

Rail-Round: 2
Rail-Subject: .claude/plans/PLAN-193/wave-fn04/fn04.patch
Rail-Subject-sha256: f2992cd6dbd7b3ca42f858bcd128e8935ce089ee6f7f334ff411b1392eacc4d3
Rail-Sentinel-sha256: 7038a40499808f2f33499c3ef80d6be826cc3faa094cb3eafa42d1774ed17ce5
Rail-Reviewer: codex-cli 0.155.0 via npx (cache próprio; o codex global não é usado), codex exec --sandbox read-only, modelo gpt-6-astra
Rail-Prompt: .claude/plans/PLAN-193/wave-fn04/rail-prompt.md
Rail-Reviewer-Verdict: GO-WITH-CONDITIONS
Rail-Verdict: FINDINGS
Rail-Findings: P0=0 P1=1 P2=1

O sujeito é o patch (sha256 acima, aplicado numa árvore de revisão descartável = `git archive`
da base do patch + o patch + os materiais) e o texto assinável (`wave-fn04-approved.md`, sha256
acima). O script do SIGN não é sujeito do rail. `Rail-Reviewer-Verdict` é a linha VERDICT do
revisor, verbatim. `Rail-Verdict` é o veredito deste registro para o SIGN: `APPROVE` só quando o
revisor não relatou achado nenhum; `DECLARED-P2` só quando relatou apenas P2, listados abaixo;
`FINDINGS` quando relatou P0 ou P1 (curados e revisados na rodada seguinte).

## Saída do revisor (verbatim; caminhos locais redigidos)

```text
- **P1 — [.claude/hooks/_lib/launch_ledger.py:653](.claude/hooks/_lib/launch_ledger.py#L653): registro sem snapshot vira `match`.** Reproduzi em memória: `PreToolUse(scriptPath)` → `bind` manual → retomada com mesmo hash e `args`, sem qualquer PostToolUse, resulta em `guard.result="match"`. O teste em `.claude/hooks/tests/test_check_workflow_launch.py:1140` exige esse comportamento, contrário ao critério desta rodada. **Cura:** impedir `match` quando o registro de `scriptPath` não tem snapshot, preservando a comparação independente de `args`, os bloqueios, advisories e overrides; corrigir o teste e ajustar o texto assinável.

- **P2 — [.claude/hooks/_lib/launch_ledger.py:735](.claude/hooks/_lib/launch_ledger.py#L735): vínculo heurístico ainda pode reler o arquivo original.** Com um registro legado contendo snapshot, um PostToolUse sem `tool_use_id` cuja resposta nomeie o próprio `scriptPath` sob `workflows/` provoca sua leitura em `bind_run`. Reproduzi `by_single_unbound` lendo esse caminho: a existência do snapshot dispensa a verificação do método de vínculo. Isso contraria o requisito de nenhuma leitura do original por vínculo heurístico. **Cura:** restringir também a leitura de `persisted_script_path` ao vínculo `by_tool_use` e cobrir o caso de snapshot legado.

VERDICT: GO-WITH-CONDITIONS
```

## Triagem

- P1 (registro sem snapshot vira `match`): CONFIRMADO e aceito na forma do revisor — é o princípio do
  próprio validador da W1 (o hash de script só é evidência quando bytes do snapshot o reproduzem).
  Cura: `compare()` trata o hash gravado de um registro de `scriptPath` sem snapshot como
  indisponível ⇒ comparação de script `inconclusive` (nunca `match`, nunca advisory nem bloqueio de
  script, também sob `CEO_WORKFLOW_SCRIPT_GUARD=enforce`); a comparação de `args` não muda (bloqueio
  sob vínculo forte). `ceo-launches.py check` sai rc 6 nesse caso. Teste reescrito
  (`test_a_script_path_record_without_a_snapshot_keeps_the_args_guard_and_no_script_verdict`),
  mutante M10 morto; texto assinável, docstrings e doc dizem exatamente isso.
- P2 (vínculo heurístico relia o original num registro legado com snapshot): CONFIRMADO. Cura:
  `bind_run` só carrega o snapshot e só lê a cópia do harness no vínculo por `tool_use_id`; o
  heurístico e o manual não leem arquivo algum além do índice e dos manifestos do ledger. O teste
  `test_heuristic_and_manual_binds_read_no_file` cobre também o registro legado (snapshot gravado no
  PreToolUse, a forma anterior à cura): zero chamadas ao leitor; mutante M9 morto.
- Próxima rodada: 3 (a final pela regra de parada), sobre o patch regenerado.
