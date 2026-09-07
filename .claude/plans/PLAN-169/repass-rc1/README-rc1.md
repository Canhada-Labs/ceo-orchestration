---
plan: PLAN-169
release: v1.4.0-rc.1
status: kit
---

# Re-pass do candidato v1.4.0-rc.1 — escopo, orçamento e o que fica de fora

## 1. O problema de tamanho, medido

O delta da base GA v1.3.0 (cortada em 2026-08-17) até o candidato é grande
demais para uma revisão exaustiva. Medido em `v1.3.0..e242544` (o proxy do
candidato usado para dimensionar; o candidato REAL é o commit do bump, que
só acrescenta os sítios de versão):

| dimensão | valor |
|---|---|
| arquivos alterados, árvore inteira | 1.318 |
| linhas adicionadas, árvore inteira | 470.864 |
| arquivos alterados, excluindo testes | 1.178 |
| commits na faixa | 436 |

Com teto de 180 KB de payload redigido por parte e orçamento de **6
invocações**, o máximo teórico revisável é ~1,08 MB de diff. Este kit cobre
**848.309 bytes em 42 arquivos** — a superfície que o adotante realmente
recebe e executa. O resto está declarado no §4, não escondido.

## 2. As seis partes, na ordem de risco para o adotante

A ordem não é arbitrária: é a ordem em que uma regressão machucaria alguém
que instalou a v1.3.0 e roda o upgrade.

| # | conteúdo | arquivos | bytes de diff |
|---|---|---|---|
| 1 | `scripts/upgrade.sh` | 1 | 135.668 |
| 2 | `install.sh`, `_framework_manifest_set.sh`, `delivery-routes.tsv` | 3 | 111.809 |
| 3 | `doctor.sh`, `uninstall.sh`, `templates/**` | 11 | 111.488 |
| 4 | `SPEC/**`, `npm/**`, `CHANGELOG.md`, `VERSION`, `.claude/settings.json`, `.claude-plugin/**`, `.github/workflows/**` | 13 | 163.400 |
| 5 | hooks da família de continuidade de compaction | 6 | 162.268 |
| 6 | núcleo de cadeia e auditoria em `_lib/` | 8 | 163.676 |

Todas abaixo de 180 KB. A parte 4 é a de menor folga (16,6 KB) porque a
seção `[1.4.0]` do CHANGELOG landou em `e242544`; o bump acrescenta a ela
`VERSION`, `npm/package.json` e os dois manifestos de plugin, poucas linhas
cada. O redator do ADR-114 preserva linhas e hunks (o
runner **prova** isso por controle a cada parte), e o cabeçalho do prompt
soma cerca de 3 KB. O teto duro do runner é 200.000 bytes de payload cru:
acima disso ele recusa e manda re-particionar.

### O manifesto é DERIVADO, nunca uma lista fixa

Cada parte carrega uma **pathspec** — a intenção — e o runner deriva o
manifesto com `git diff --name-only v1.3.0..CANDIDATO -- <pathspec>` no
momento da execução. Isso não é elegância: uma lista fixa medida em
`e242544` esqueceria os arquivos que **só mudam no commit do bump**
(`VERSION`, `npm/package.json`, `.claude-plugin/plugin.json` e
`marketplace.json`), e o re-pass reviraria uma árvore diferente da que vai
ser taggeada. É a classe do instrumento verde cuja pergunta envelheceu.

Os `paths-rc1-N.manifest.txt` que viajam neste diretório são o **snapshot
da medição** feita em `e242544`; o runner os reescreve com o que
efetivamente revisou, e é essa versão que entra no `MANIFEST-rc1.sha256`
assinado. A receita `part_pathspec()` do regenerador do snapshot é
byte-idêntica à do runner — verificado.

`scripts/install-npm.sh` mudou **zero bytes** na faixa. Ele está na
pathspec da parte 2 por completude de intenção, mas um arquivo sem mudança
nunca aparece no manifesto derivado, e portanto não vira payload.

## 3. Cobertura anterior citada no próprio prompt

Cada parte carrega, dentro do prompt, as rodadas de rail que já revisaram
aquele conteúdo quando ele landou. Isso existe para que o revisor possa dar
**GO-WITH-CONDITIONS com a condição nomeando a cobertura**, em vez de tratar
como inédito algo que já passou por rail cruzado.

| parte | cobertura anterior citada |
|---|---|
| 1 | PLAN-183 W5 (D1, 8 rodadas); pacote E da S329 (7 rodadas sobre a sombra re-derivada, 4 P1 reais); PLAN-185 W1–W3 (5 rodadas) |
| 2 | PLAN-185 W1–W3 (e2e 105/0 em bytes; controle 22/33 pré-cura); PLAN-183 W5 D3 |
| 3 | PLAN-183 W5 (`doctor.sh` no mesmo leitor de rotas); wave-s330-F (11 rodadas, 15 defeitos reais) |
| 4 | wave-s330-F (`settings.user.json` derivado, `--check` byte-a-byte no CI); S337 (Smoke Install executa o CI entregue; docker ubuntu 24.04, 10/10 steps verdes) |
| 5 | PLAN-179 wave-179close (27 rodadas de pair-rail, 83 defeitos reais) |
| 6 | PLAN-182 W1 (censo M4 16→7→0); S326 wave-cli (Axis 3, 9 rodadas) |

O prompt diz explicitamente que a cobertura anterior **não é motivo para
pular**: o que nenhuma rodada por wave teve é a visão de INTEGRAÇÃO — o
delta inteiro de uma vez, contra uma tag que um adotante instalou de fato.

## 4. O que fica FORA, e por quê

Nada disto é "não importa". É orçamento, e a decisão está escrita para que
uma condição do veredito possa apontá-la.

**Fora por orçamento, com cobertura anterior:**

- `.claude/hooks/check_ledger_checkpoint.py` (56.835 B) e
  `check_arbitration_kernel.py` (11.822 B) — mesma família do PLAN-179 da
  parte 5, revisados nas mesmas 27 rodadas. Ficaram de fora porque a parte 5
  já está em 162 KB e admiti-los estouraria o teto.
- `.claude/hooks/_lib/scratchpad_lib.py` (27.271 B) — mesma família do
  PLAN-182 da parte 6.
- Os 15 hooks e 12 módulos `_lib` restantes, todos abaixo de 12 KB de diff.
- `.claude/scripts/**` (cerca de 1,85 MB de diff). É superfície entregue ao
  adotante, e portanto uma omissão REAL, não uma isenção por natureza. Cabe
  numa condição do veredito.

**Fora por natureza (não entregue ao adotante):**

- Toda a árvore de testes (`*/tests/*`, `test_*`): 140 arquivos, ~62 mil
  linhas. O predicado de exclusão do próprio framework
  (`_framework_path_excluded`) as mantém fora da entrega.
- `.claude/plans/**`, `.claude/adr/**`, `docs/**` e o material de cerimônia:
  são o registro da governança, não o produto instalado.

## 5. Orçamento e critério de parada

- **6 invocações de codex**, uma por parte. O runner não repete parte.
- Cada parte é julgada de forma independente; o `RUNNER-OVERALL` é 0 apenas
  se as **seis** terminarem em `GO` ou `GO-WITH-CONDITIONS`.
- Exatamente **uma** linha `VERDICT:` por parte. Duas linhas é ambiguidade,
  não aprovação, e o runner a registra como tal (classe CM-03 do corpus de
  defeitos S348).
- Evidência completa de tentativa anterior **aborta** o runner: um NO-GO
  exige triagem e `mv` para `repass-rc1-<data>-NOGO/` antes de re-rodar.

## 6. Condições-rascunho para o envelope

Se o veredito agregado for `GO-WITH-CONDITIONS` — o desfecho esperado dado o
tamanho do delta — estas são as condições que o material assinado deve
carregar. Elas descrevem o que a revisão **não** cobriu, para que a
assinatura não afirme mais do que aconteceu.

1. **Cobertura declarada.** O re-pass cobriu 42 arquivos e cerca de 848 mil
   bytes de diff, escolhidos por risco ao adotante. `.claude/scripts/**` ficou fora
   por orçamento e permanece coberto apenas pelas rodadas por wave.
2. **Limite same-UID permanece.** A separação de cadeias HMAC por projeto é
   por diretório e chave, não por privilégio: sob o mesmo UID um processo lê
   o diretório e a chave do outro projeto. Está no CHANGELOG e no
   `docs/threat-model.md`; nenhuma parte deste re-pass o fecha.
3. **Checksums por tarball continuam não automatizados.** A honestidade da
   `npm/INTEGRITY.md` foi a rota escolhida na v1.3.0-rc.4; a implementação
   real segue como item nomeado, agora da v1.5.0.
3-b. **O CHANGELOG `[1.4.0]` foi escrito por outro pacote** (`e242544`) e a
   cerimônia `rel-meta` apenas o CONFERE. O texto entra no re-pass pela
   parte 4, mas nenhuma etapa deste kit o produziu.
4. **Fence-shadow variante 5** (bloco YAML escondido em comentário HTML cru
   pelo PRÓPRIO signatário de um envelope assinado) permanece fora do modelo
   de ameaça, com signatário igual ao Owner. Cura definitiva = envelope de
   formato fixo nos dois twins.
5. **Residuais herdados do trem** que o CHANGELOG [1.4.0] nomeia seguem
   abertos por decisão registrada, não por omissão.

O gerador (`gen-envelope-rc1.py --stage fields --conditions-file`) exige o
arquivo de condições sempre que o veredito agregado for
`GO-WITH-CONDITIONS`, e as condições entram nos **fields**, isto é, no
material que o Owner assina.

## 7. Codex pinado, sem tocar na máquina

`codex --version` na máquina do maintainer está em **0.153.4**.
`.claude/governance/codex-cli-pin.txt` exige `>=0.128.0,<0.148.0` e
`codex-cli-pin-manifest.json` pina o payload de **0.147.0**. Os dois são
canônicos e este kit **não os edita**.

O runner resolve a 0.147.0 por `npx` num cache próprio
(`repass-rc1/.npx-cache`), verifica o sha256 do payload nativo contra o
manifesto pelo mesmo oráculo do `pair-rail-gate`
(`check_pair_rail.py --verify-codex-pin <launcher>`, fail-closed) e põe um
diretório-shim no início do `PATH` para que qualquer `codex` invocado durante
o run seja o pinado. O `codex` global fica fora do `PATH` do processo.

Medido em 2026-09-07, nesta máquina:

```
npx -y @openai/codex@0.147.0 --version   ->  codex-cli 0.147.0
sha256 do payload nativo resolvido       ->  19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37
sha256 no pin-manifest                   ->  19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37
--verify-codex-pin <launcher do npx>     ->  {"status": "verified", "target_triple": "aarch64-apple-darwin"}
--verify-codex-pin (codex GLOBAL)        ->  {"status": "mismatch", "sha256": "b973d440..."}
```

A última linha é o controle negativo, e ele é gratuito: o binário global
falha o mesmo oráculo que o pinado passa.

## 8. Onde o candidato entra

O runner **não** carrega o SHA do candidato numa constante. Ele o lê de
`repass-rc1/CANDIDATE.sha`, que o `OWNER-RC1-CUT.sh` escreve depois do
`release.sh bump` e do push. O runner recusa se o arquivo estiver ausente,
se o conteúdo não for um sha40 minúsculo, se o commit não existir, se a base
não for ancestral dele, ou se `origin/main` tiver avançado para outro
commit. O candidato real é o commit do bump: a tag rc.1 ainda não existe
quando a revisão roda, e exigir um worktree da tag seria circular.
