---
plan: PLAN-185
round: 1
created_at: 2026-08-26T19:23:35Z
---

# PLAN-185 — Proposta em debate (round 1): curas W1+W2 de segurança de escrita do installer

> Destilação da tese do plano. Plano completo: `.claude/plans/PLAN-185-installer-write-safety.md`.
> Censo W0 (4ª passada, INVERTIDA): `.claude/plans/PLAN-185/w0-censo-S329.md` (4ª passada EM DERIVAÇÃO nesta night-run — agente U1.1; até ele devolver, a referência disponível é o censo S326 e os 35 achados abertos do rail listados no plano §4).

## Tese

Dois defeitos GRAVES de escrita do `scripts/install.sh`, ambos REPRODUZIDOS em installs reais
(S325), com curas pequenas e uma CLASSE a fechar:

### F1 — escrita FORA do `$TARGET` via symlink pendente
`install_docs_template` guarda o destino com `[[ -e "$dst" ]]` (`install.sh:1466-1472`). `-e`
SEGUE o symlink: link pendente ⇒ `-e` falso ⇒ o `cp` escreve ATRAVÉS do link, fora da árvore do
target, com `exit 0` e log `COPIED:`. A defesa correta JÁ existe no mesmo arquivo para outra
árvore (`install.sh:2139-2159`) — é a classe "ramo local por omissão".

### F2 — `--github-owner` com `/` corrompe CODEOWNERS para sempre
`sed "s/{{OWNER_HANDLE}}/$GITHUB_OWNER/g" > "$dst"` (`install.sh:1508`): valor com `/` ⇒ `sed`
aborta DEPOIS de o `>` criar o destino ⇒ arquivo de 0 bytes que vira EXISTS-skipped para sempre
(`:1504`) — nenhum install/upgrade posterior corrige.

## Desenho das curas (o que está em debate)

1. **W1 (F1):** `install_docs_template` recusa destino que seja symlink, pendente ou não,
   reusando a guarda de `install.sh:2139-2159` extraída para UMA função compartilhada — não uma
   guarda nova paralela. Os DOIS sítios passam a chamar a MESMA função (AC-3: a classe fecha).
   Prova: fixture symlink PENDENTE para fora ⇒ falha nomeada + asserção nos BYTES do alvo
   externo (não no exit code); fixture symlink RESOLVIDO ⇒ mesma recusa; sem symlink ⇒
   não-regressão; teste VERMELHO com a guarda revertida.
2. **W2 (F2):** substituição de handle SEM `sed` interpolável: validação do valor contra
   conjunto fechado de caracteres de handle ANTES de qualquer escrita + escrita ATÔMICA
   (tmp + `mv`) + recuperação: destino de 0 bytes pré-existente NÃO é EXISTS-skip, é corrigido.
   Prova: 3 fixtures (a) `a/b` ⇒ falha nomeada e NENHUM arquivo criado; (b) handle válido ⇒
   1442 bytes, 33 linhas, handle ≥1×, e SÓ DEPOIS `grep -c '{{OWNER_HANDLE}}' == 0`; (c) 0-byte
   pré-existente ⇒ curado. As três VERMELHAS com a cura revertida.
3. **Censo em CI (AC-3):** o instrumento invertido da W0 (allowlist de formas provadas seguras;
   resto = indeterminado) entra no `validate.yml` — wiring canônico, mesma cerimônia.
4. **UMA cerimônia (AC-4):** W1+W2 num único pacote (`PLAN-185/s329-ceremony-C/`), Scope
   DERIVADO do patch, `touched − scope = ∅` no land.

## Decisões já tomadas (não re-debater; contexto)

- Owner 2026-08-25 (verbatim): «4ª passada INVERTIDA + W1/W2 em pacote (Recomendado)» — a
  arquitetura invertida do censo é decisão ratificada; o debate é sobre o DESENHO DAS CURAS.
- Flips `draft→reviewed` (após consensus `design-coherent`) e `reviewed→executing` (no commit da
  W0) já autorizados pelo Owner.
- F3 (ramos do CODEOWNERS não exclusivos no tempo) está FORA — PLAN-183 §9.3.
- O debate NÃO autoriza shipping (V0 apenas); o pacote vai a V2 (rail codex) + V3 (GPG do Owner).

## Perguntas abertas para os críticos

- A função de guarda compartilhada deve viver onde? (mesmo arquivo `install.sh` vs
  `scripts/_lib-sh` — considerar que `upgrade.sh` e `doctor.sh` têm sítios da mesma classe no
  censo; o escopo desta cerimônia é `install.sh`, mas a ASSINATURA da função não pode fechar a
  porta para os outros consumidores.)
- O conjunto fechado de caracteres de handle do GitHub: `[A-Za-z0-9-]` (com regra de hífen não
  inicial/final, ≤39 chars) é suficiente? Orgs com `.`? (GitHub orgs/users: alfanumérico + hífen;
  validar contra a regra REAL, citando fonte.)
- A recuperação da fixture (c) (0-byte ⇒ re-escrever) pode mascarar um CODEOWNERS
  DELIBERADAMENTE esvaziado pelo adopter? (0 bytes é sempre corrupção? Um CODEOWNERS de 0 bytes
  é sem função no GitHub — mas o critério "corrige sem perguntar" merece o olhar do crítico.)
- Riscos que o CEO não viu; onde o plano pode falhar; o que falta (formato DEBATE-SCHEMA §4).
