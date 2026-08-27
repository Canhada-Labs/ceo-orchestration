# wave-s329-C — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `PLAN-183/w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` —
> nunca escrito à mão. O `Anchor-SHA` é preenchido pelo `OWNER-S329-C-SIGN.sh`
> com `git rev-parse HEAD` no momento da assinatura; o `OWNER-S329-C-LAND.sh`
> aborta no G1 se não casar. Reescrever um byte deste arquivo depois de assinar
> invalida o `.asc`.

Plans: PLAN-185
Wave: wave-s329-C (PLAN-185 W1+W2 — o installer deixa de poder escrever FORA do diretório que recebeu, e `--github-owner` deixa de poder zerar o `.github/CODEOWNERS` para sempre)
Patch: .claude/plans/PLAN-185/s329-ceremony-C/C.patch
Patch-sha256: 85c725fadd64414bfb77ebb5af00d294299684f59760a2fcd4662f03646e8642
Patch-base: b0e992f3b6df478eacbce2afc2641153a934e9c0
Anchor-SHA: TO-FILL-AT-SIGN
Data: TO-FILL-AT-SIGN

## Os dois defeitos, medidos

**F1 — escrita fora do `$TARGET`.** Todo escritor de destino do `install.sh`
decidia se escrevia testando o destino por EXISTÊNCIA, e `-e` **segue symlink**.
Um link PENDENTE plantado no destino responde falso, o escritor toma o ramo
"ainda não tem nada aí", e o `cp`/`>` escreve ATRAVÉS do link. Medido contra o
installer pré-cura (S329): com `docs/rotation-log.md` apontando para fora do
alvo, a execução **saiu 0**, registrou `COPIED:` e **536 bytes aterrissaram no
caminho externo**. Um link RESOLVIDO e um ANCESTRAL symlink escapam do mesmo
jeito; um HARD LINK escapa com todas as checagens de caminho passando, porque
um segundo nome para um inode não é um link que caminhada nenhuma encontra.

**F2 — `--github-owner` zerando o CODEOWNERS.** O valor era interpolado CRU num
comando `sed s`. Um valor contendo `/` termina o comando cedo: o `sed` sai com
"bad flag in substitute command" **depois** de o `>` já ter truncado o destino.
O `.github/CODEOWNERS` sobrevive com **0 bytes** — pulado por EXISTS para
sempre, fora do snapshot de rollback, e lido pelo GitHub como "sem donos".
Medido pré-cura (S329): rc 1, 0 bytes.

## O que esta wave entrega

**Seis arquivos canônicos** e **três não-canônicos**, todos no mesmo patch
porque a cura e a vigilância não podem se separar: um teste que landasse depois
seria uma janela em que a classe não tem guarda, e o wiring de CI é canônico.

1. **`scripts/_framework_manifest_set.sh`** (canônico, +177) — o predicado
   compartilhado `_wbm_dst_refuses <target_root> <rel_path>`, num bloco único
   após `_wbm_source_confined`. **Predicado na biblioteca, política no
   chamador**: ele RESPONDE (`rc 0` = recusar) e não decide o que fazer.
   Também a gramática de handle e o dono do `nlink`.

2. **`scripts/install.sh`** (canônico, +457/−20, 26 hunks) — os sete escritores
   de destino passam a consultar o predicado; substituição segura + escrita
   atômica; recuperação do CODEOWNERS de 0 bytes **só com evidência**; pré-voo
   sem mexer na semântica de rollback.

3. **`scripts/upgrade.sh`** (canônico, +40/−20) — vira CONSUMIDOR do mesmo
   predicado, no MESMO patch (OQ-5). Pôr o corpo dentro do `install.sh`
   fecharia a porta para o upgrader e recriaria a classe das cópias divergentes
   — que é exatamente a forma dos quatro defeitos D1..D4 da S323.

4. **`.github/workflows/smoke-install.yml`** e **`.github/workflows/validate.yml`**
   (canônicos) — o e2e novo nas DUAS listas de `paths:` mais o step que executa
   (FU-2), e a linha do censo no `validate.yml`, que não tem filtro `paths:` e
   portanto não tem a armadilha de "gate que a mudança não dispara" (FU-3).

5. **`.claude/adr/ADR-196-installer-write-confinement.md`** (canônico) —
   "predicado na biblioteca, política no chamador", com os três consumidores
   previstos (`install.sh`, `upgrade.sh`, `doctor.sh`) (FU-6).

6. **`scripts/tests/test-installer-write-safety-e2e.sh`** (não-canônico, +641) —
   15 fixtures, **50 asserções**, ~7 min. Toda asserção F1 é sobre o **caminho
   EXTERNO**, nunca só sobre o exit code, porque o defeito pré-cura **sai 0**:
   uma asserção de exit code teria passado contra ele.

7. **`docs/threat-model.md`** (não-canônico) — a superfície de escrita de
   destino do installer entra no contrato (hoje só T-004, extração de tarball).

8. **`.claude/plans/PLAN-185/s329-ceremony-C/DESIGN-C.md`** (não-canônico) — o
   registro de desenho: contrato do predicado, gramática, escrita atômica,
   regra de evidência, testes, censo, residuais e OQs.

## Controle positivo, em bytes

Contra a árvore PRÉ-CURA do MESMO commit o e2e vai a **22 passed / 33 failed,
rc 1**, e as falhas NOMEIAM o defeito: `536 bytes written OUTSIDE the target`,
`8468 bytes`, `454 bytes`, `48708 bytes`, `.github/CODEOWNERS was created
(0 bytes)`. A receita está no cabeçalho do próprio teste. Um controle verde
significaria que o arquivo está asserindo outra coisa.

**Não-regressão medida, não afirmada:** install a partir das duas árvores no
MESMO path de destino — **566 arquivos idênticos por sha256** (exceto
`PROTOCOL.md`, cujo diff é 100% o path do checkout embutido no ponteiro, e o
manifesto que o hasheia) e **modos idênticos em 567**.

## Autorização de governança

- Achados de origem F1/F2: decisões do Owner de 2026-08-24 (`PLAN-185`).
- Debate round-1 (S329): **PROCEED / design-coherent**, 3 críticas ADJUST,
  síntese anonimizada; plano re-derivado sobre âncoras vivas e `draft → reviewed`.
- Unidade da night-run S329 (`.claude/plans/PLAN-185/NIGHT-S329-RUNBOOK.md`).
- Desenho e medições: `.claude/plans/PLAN-185/s329-ceremony-C/DESIGN-C.md`.
- Pair-rail: registros em
  `.claude/plans/PLAN-185/s329-ceremony-C/rail-round-*.md`. O
  `OWNER-S329-C-SIGN.sh` recusa assinar se o registro de MAIOR número não
  carregar `Rail-Verdict: APPROVE`.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs TO-FILL-AT-SIGN
Plans: PLAN-185
Scope:
  - .claude/adr/ADR-196-installer-write-confinement.md
  - .claude/plans/PLAN-185/s329-ceremony-C/DESIGN-C.md
  - .claude/scripts/data/installer-write-safety-baseline.txt
  - .github/workflows/smoke-install.yml
  - .github/workflows/validate.yml
  - CHANGELOG.md
  - CLAUDE.md
  - README.md
  - README.pt-BR.md
  - docs/ARCHITECTURE.md
  - docs/CTO-GUIDE.md
  - docs/FAQ.md
  - docs/GUIA-COMPLETO.md
  - docs/README.md
  - docs/threat-model.md
  - npm/README.md
  - scripts/_framework_manifest_set.sh
  - scripts/install.sh
  - scripts/tests/test-installer-write-safety-e2e.sh
  - scripts/upgrade.sh
<!-- END SIGNED SCOPE -->

## Residual declarado

- **TOCTOU permanece, e é irredutível em bash.** Entre o predicado responder e
  a escrita acontecer, nada impede o destino de VIRAR symlink. Bash não oferece
  `openat`/`O_NOFOLLOW`. A guarda **estreita** a janela; não a fecha. O cenário
  onde isso importa é alvo compartilhado ou clone de terceiro.
- **`install_one` continua PULANDO, não recusando**, por decisão do plano: o
  predicado é consultado, a política é a antiga, deliberadamente — os testes
  atuais fixam esse comportamento.
- **`install_mcp_secrets_dir` NÃO foi guardado.** Não está entre os sete
  escritores que o plano enumera, e alargar o conjunto no meio de um pacote
  assinado é como o Scope estoura. Sítio conhecido, não curado.
- **F1.2 e F1.4 já passam a asserção de BYTES na árvore pré-cura** (o código
  antigo pegava o ramo EXISTS e pulava): nessas duas pernas o vermelho do
  controle vem da asserção de "recusa NOMEADA", não de um escape vivo. Dito
  aqui para que ninguém leia as 33 falhas como 33 escapes.
- **`scripts/doctor.sh` é o terceiro consumidor previsto e NÃO foi convertido**
  (FU-7). Enquanto não for, a classe segue aberta lá. O `EXPECTED-BASELINE.txt`
  registra `0` referências ao predicado no doctor, para que a conversão futura
  apareça como divergência consciente e não como surpresa.
- **O censo NÃO enxerga a forma que o plano mandou construir, e isso é
  estrutural** (FU-1). As formas provadas seguras do instrumento exigem, para a
  família symlink, um teste `-L` no mesmo arquivo ou um helper DEFINIDO NO
  MESMO ARQUIVO com polaridade `|| abort`. A cura viola as duas **por decisão
  do plano**: o corpo com o `-L` vive em outro arquivo (senão a porta para
  `upgrade.sh` e `doctor.sh` fecha) e a polaridade é de RECUSA. Reformar a cura
  para caber no instrumento seria deixar o instrumento ditar a arquitetura.
  **Consequência declarada: o AC-3 como escrito ("19 → 0") NÃO é satisfeito por
  este pacote**, e não por falta de cura — ver OQ-6 no `DESIGN-C.md`.
- **O ratchet do censo entra REGENERADO neste patch, e isso é uma condição de
  land, não um resíduo.** A cura acrescenta 177 linhas à biblioteca e reescreve
  26 hunks do `install.sh`; sob a regra INVERTIDA da 5.ª passada, tudo que não
  está provado seguro nasce `indeterminado`, então **45 fingerprints nascem e 15
  morrem** na baseline. O `validate.yml` deste **mesmo** patch instala um step
  que roda o censo **fail-closed** (`set -euo pipefail`, sem `|| true`, sem
  `continue-on-error`), logo landar com o ratchet sujo deixaria o `Validate`
  vermelho no primeiro push — por um gate que o próprio pacote instala. O V4 do
  LAND e o passo 4f do `finalize-C.sh` **abortam** enquanto ele não estiver
  limpo. Regenerar não é silenciar: o cabeçalho da própria baseline diz que uma
  linha ali significa "este sítio é CONHECIDO do censo", explicitamente **não**
  uma revisão humana por sítio; o que o ratchet impede é um sítio novo entrar
  **calado**, e entrar por um commit assinado é o oposto de calado.
  Direção medida: `desguardado` **cai** de 220 para 217 no corpus e de 57 para
  54 no `install.sh`.
- **A suíte e2e roda ~7 min** (≈13 installs reais). É e2e, não unitário; não há
  substituto barato, porque asserção sobre BYTES exige escrita de verdade.
