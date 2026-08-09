# Proveniência do re-pass round 2 (multi-part) — candidato rc.2
- Base: v1.3.0-rc.1 · Candidato: d1b6f14ba492ba1d7c08abd4a03461faca902e62
- Worktree detached limpo: sim · Pipeline: prompt+diff → codex_egress_redact --outgoing → controles → codex exec --sandbox read-only
- Partição por cap do redactor (256KB): 5 partes; hunks preservados assertados por parte; truncamento = FATAL
- Data: 2026-08-09T03:51Z


## Resultado agregado
- part a (framework scripts (install/upgrade/generator) + root hygiene): VERDICT: NEEDS-CHANGES [codex rc=0]
- part b (e2e harness scripts/tests (W1 Linux port + riders)): VERDICT: NEEDS-CHANGES [codex rc=0]
- part c (governance scripts .claude/scripts (W2 fixes)): VERDICT: NEEDS-CHANGES [codex rc=0]
- part d (script test suites .claude/scripts/tests): VERDICT: NEEDS-CHANGES [codex rc=0]
- part e (hooks tests + docs + workflows + root docs): VERDICT: NEEDS-CHANGES [codex rc=0]
- OVERALL: HÁ PARTE SEM APPROVE — triagem antes do corte

## Triagem final (S299/S300, pré-corte rc.2)

Round 4 (candidato `3138deb`+`d1b6f14`): parte d achou 2 reais NOVOS no
teste do injector (env vazando p/ HOME real via subprocess; rc só-não-2
aceitava crash) — CURADOS em `c0295e1` (env sanitizado HOME-tempdir +
CEO_*/CLAUDE_* strip; rc∈{0,3}). Residuais das partes a/b/c/e triados:
produto 167/168 = 4 exceções nomeadas no verdito rc.2 (V1/V2/V4/V5,
fixes no pack W3); instrumento harness/parity = wave própria;
release.yml P2 = candidato ao pack W3. Candidato final rc.2 = `c0295e1`.

## Payloads raw (não commitados — precedente r1; pin por conteúdo)

Os `payload-*.raw.txt` (pré-redação) não entram no repo público; os
bytes ficam no arquivo local do Owner. Pins sha256 no momento do corte:

- payload-a.raw.txt `a0e556e2e8ca33a574cd93ecc2ec4e15ce619e7f2a66d7e3a0f96b02c04eac03` (byte-idêntico ao redacted — redação no-op na parte a)
- payload-b.raw.txt `fe772f4b118b6835a91c5cfc7783889a22018b6b34e3f88830f3115e88412667` (byte-idêntico ao redacted)
- payload-c.raw.txt `77ee43eebc2db7d75ce6e65a9af7300d58bb5b9a4ffc0c41c91917659f884a6e` (difere do redacted — redação ativa)
- payload-d.raw.txt `c2f024df71b1d5ad4bab23d7c244032bd92140db2468726d9e3890170cc2f57c` (byte-idêntico ao redacted)
- payload-e.raw.txt `bfc2841ef74af3a75d0140f3be8ea817b8c85c3f5ecc8d7829555f4a7637d5fd` (difere do redacted — redação ativa)

Nota: o `MANIFEST-r2.sha256` foi reescrito em BASENAMES (mesmos 10
hashes, só o formato do caminho) para satisfazer o guard da tag
(`shasum -c` com cwd no dir do manifesto + igualdade de conjunto por
nome, espelhável server-side).
