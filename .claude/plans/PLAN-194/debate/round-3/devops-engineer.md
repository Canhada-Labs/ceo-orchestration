---
round: 3
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: "DevOps Engineer (Principal) — CI/CD, pipeline de release, toolchains pinados, SRE do estado local"
served_model_id: claude-opus-5-5
generated_at: 2026-10-02T04:30:00Z
scope: "só W3 — rodada final pela regra de parada pré-registrada"
inputs:
  - .claude/plans/PLAN-194/debate/round-2/consensus.md (lista (b))
  - .claude/plans/PLAN-194/debate/round-2/ADR-182-AMEND-1-draft.md (r3, commit 092377af)
  - .claude/plans/PLAN-194-maintenance-train-v1-4-3.md (W3 e W7, commit 092377af)
---

> **Legenda de evidência.**
> - **[AMEND-1 §x]**: rascunho r3. **[plano :N]**: PLAN-194 no commit `092377af`. **[disco]**: conferido
>   por mim no HEAD. **[inferência]**: dedução minha.
> - Estimativas em tokens e sessões (ADR-081).
> - Nenhum conteúdo lido trouxe instrução dirigida a mim.
> - **Regra desta rodada:** NO-GO só por P0 ou afirmação FALSA. Todo o resto é condição de execução.

## Verdict

**ACCEPT** (W3: **PROCEED**, `design-coherent`), condicionado a uma coisa fora do meu domínio: a
decisão 3 do Owner tem de ser o ramo (i) ou o ramo (ii). Se o Owner escolher «confiança no registro», vale
a regra do consenso da rodada 2: **ESCALATE-TO-OWNER**.

- **Não achei P0.**
- **Não achei afirmação falsa que invalide o desenho.** As divergências entre o plano e o AMEND-1 (paths,
  nomes, onde fica a mensagem do Gate 4, Checks com `-k` × node ids) são de TEXTO e de CONTAGEM e entram
  como condições.
- Dos meus must-fix da W3 na rodada 2 (5–10), cinco estão atendidos e um parcial (o 9: paths e
  colisões).

## Summary (≤ 3 bullets)

- **O que a rodada 3 julga:** se o AMEND-1 r3 e o plano incorporam a W0.6 e os 23 itens da lista (b).
  Eles incorporam:
  - `sigstore.verify` com política e os dois bundles;
  - vínculo pelo `subject` verificado;
  - caches novos a cada execução e lista fechada de hosts;
  - promoção pelos bytes verificados, com P-01 da árvore inteira e quiesce;
  - rota 2 invertida, com as células K-01 a K-06;
  - verificador, auxiliar e material de empacotamento sob o ADR-192;
  - o R-16 declarado.
- **Forte (lado operacional):**
  - a promoção só na MESMA execução da Fase 1, offline sobre o cache do staging, sob proxy morto (P-02,
    P-04, P-05);
  - o kit do corte deixa de executar antes do oráculo e passa a executar o `path` verificado (§17);
  - o H-07 amarra a confiança no registro aos shas do instrumento no manifesto ADR-192.
- **O que sobra (condições de execução):**
  - o plano subconta o pacote 1a, que dá 8 paths, não 6;
  - o mapa de colisões não tem linhas para os possíveis hospedeiros da guarda do registro;
  - o rollback passa pelo canário, que gasta cota do Codex;
  - trocar o verificador derruba a confiança do registro, e falta a rotina operacional para isso;
  - a camada 2 pode ficar verde por SKIP no Check.

## Risks

1. **R3-DO1 — MEDIUM — W3 — a recuperação depende de cota do Codex.**
   - **O que está escrito:** o rollback é «Fase 1 + Fase 2 da versão anterior» [AMEND-1 §15]. A Fase 1
     inclui o canário V-10, que chama o provedor sob o freio Q2 e a política da §4.5 (até 1 nova
     tentativa depois de ≥ 10 min).
   - **Por que pesa:** quarentenar a versão INSTALADA bloqueia todas as escritas L3+ (H-04). Se o canário
     do rollback esbarrar na cota acima de 80% do semanal, ou em capacidade, a recuperação espera a cota.
     O texto não diz se o rollback para um sha já registrado, ou para a versão do manifesto, pula o
     canário.
   - **Mitigação:** condição 3.
2. **R3-DO2 — MEDIUM — W3 — trocar o verificador bloqueia o rail logo depois do LAND.**
   - **O mecanismo:** pelo H-07, uma linha do registro só vale se `verifier_sha256`, `helper_sha256` e
     `sigstore_pkg_digest` forem IGUAIS aos do manifesto ADR-192 da árvore [AMEND-1 §4.1, §8]. Cada
     cerimônia que muda o verificador, o auxiliar ou o lockfile tira a confiança da versão auto-pinada
     instalada. O texto declara isso [AMEND-1 §23].
   - **O que falta:** a ROTINA operacional. Sem ela, o primeiro L3+ depois do LAND é BLOCK em todas as
     sessões, até o Owner rodar o verificador, o que pede rede, quiesce e talvez canário.
   - **Mitigação:** condição 4.
3. **R3-DO3 — MEDIUM — W3 — a guarda do registro pode cair em território do PLAN-195 sem linha no mapa.**
   - **Os hospedeiros candidatos** [AMEND-1 §24]: `check_bash_safety.py`, um guard de Edit/Write, o
     `permissions.deny` do `.claude/settings.json` e a linha de base do `check_harness_config.py`.
   - **O mapa de colisões:** a linha da guarda de Bash diz «nenhuma onda deste plano toca esses arquivos»
     [plano :263], e a linha do `.claude/settings.json` não cita a W3 [plano :243]. O
     `check_bash_safety.py` é o alvo central do PLAN-195, citado 48 vezes no plano dele [disco].
   - **Efeito:** pelo I8, a guarda é pré-condição para o núcleo consultar o registro. Uma colisão com a
     parte B do PLAN-195 atrasa a W3.6.
   - **Mitigação:** condição 2.
4. **R3-DO4 — LOW — W3 — o plano e o AMEND-1 contam e nomeiam os pacotes de jeito diferente.**
   - **Pacote 1a:**
     - o plano dá «6 paths» e nomeia só o lockfile, `codex-auto-pin-package-lock.json` [plano :1074-1079];
     - o AMEND-1 dá 8 no ramo (ii): `package.json` + `package-lock.json`, o arquivo de fixtures da
       camada 2 e o manifesto ADR-192 [AMEND-1 §24];
     - o `npm ci` não roda sem `package.json`.
   - **Pacote 1b:** o plano põe a mensagem do Gate 4 (`pair-rail-gate.sh`) no 1b; o AMEND-1, no pacote 2.
   - **Mitigação:** condição 1.
5. **R3-DO5 — LOW — W3 — a camada 2 pode ficar verde por vácuo no Check.**
   - O Check da W3.4 é `pytest -q -k "… crypto_real …"` [plano :1148]. Sem `node`, a camada 2 sai SKIP, e
     o pytest sai 0 com SKIP.
   - O AMEND-1 §19.2 exige «SKIP = falha» na bateria do LAND, mas o Check do plano não impõe isso.
   - O AMEND-1 §19.4 pede node ids de classe, e o plano usa `-k`.
   - **Mitigação:** condição 6.
6. **R3-DO6 — LOW — W3 — o tempo de execução do verificador não está declarado.**
   - Uma execução com download, `npm ci`, staging, sonda, canário e eventual nova tentativa de ≥ 10 min
     passa fácil de 30 min [inferência].
   - O Bash em segundo plano do CC morre aos 30 min por padrão, no máximo 2 h (plano, W0 e lane `CC-04`).
     Um verificador morto no meio da Fase 2 deixa o global num estado que o P-01 não conferiu.
   - **Mitigação:** condição 5.

## Must-fix (blocking)

Nenhum bloqueia o PROCEED: pela regra da rodada final, o que sobra vira condição de execução, na lista
abaixo. Cada condição tem dono e momento.

1. **[W3, CEO, antes de abrir o 1b]** Reconciliar plano e AMEND-1 nos paths:
   - 1a = 8 no ramo (ii), com `package.json` + `package-lock.json`, o arquivo de fixtures da camada 2 e o
     manifesto ADR-192; 7 no ramo (i);
   - a mensagem do Gate 4 num só pacote;
   - o 1c separado se a guarda passar o teto;
   - os nomes de arquivo iguais nos dois textos.
2. **[W3, CEO, antes de abrir o 1b/1c]** Escolher o hospedeiro da guarda do registro e pôr as linhas no
   mapa de colisões:
   - `settings.json` (`permissions.deny`) na ordem W6 → W5c → W3 (1c) / W3 do PLAN-195;
   - `check_bash_safety.py` em série com as partes A e B do PLAN-195, re-derivado sobre elas.
   - De preferência, um hospedeiro que não seja o `check_bash_safety.py` enquanto a parte B do PLAN-195
     estiver em voo.
3. **[W3, AMEND-1 §15]** Rollback sem depender de cota:
   - rollback para um sha JÁ registrado, ou para a versão do manifesto, re-verifica os bytes (V-0..V-9,
     sonda local incluída) e PULA o canário, que já passou para aquele sha;
   - o runbook nomeia a rota de emergência: instalar a versão do MANIFESTO (H-01), que não precisa de
     canário nem de cota. Se a instalação for crua, os irmãos ficam sem conferência (R-19) até a
     re-promoção ou o `--check-installed`.
4. **[W3, material da cerimônia ADR-192]** Todo LAND que muda o verificador, o auxiliar ou o lockfile
   inclui, logo depois, a re-verificação da versão instalada pelo verificador NOVO, ou a reinstalação da
   versão do manifesto. Declarado no material assinado, senão o rail bloqueia todas as escritas L3+ depois
   do LAND (R3-DO2).
5. **[W3, runbook do verificador]**
   - Modo de execução declarado: terminal do Owner em primeiro plano, ou segundo plano com timeout
     explícito ≥ o pior caso pré-registrado (downloads + `npm ci` + canário + 1 nova tentativa de ≥ 10
     min). Nunca o padrão de 30 min do CC.
   - Uma morte no meio da Fase 2 deixa o global num estado que o hook BLOQUEIA pelo `bin/codex` (P-01). A
     saída é a rota de emergência da condição 3.
6. **[W3, Checks]** O Check da W3.4 (bateria do LAND) falha quando a camada 2 (`crypto_real`) for SKIP,
   por contagem de SKIP no código de saída. Os Checks da W3.3 e da W3.4 seguem o AMEND-1 §19.4 (node ids
   de classe), ou o AMEND-1 passa a aceitar os `-k` do plano; vale UM texto.

## Nice-to-have (advisory)

1. **[W3, P-03]** A recusa do quiesce nomeia o PID e o caminho do executável de cada processo que segura o
   prefixo global: o daemon `app-server` e o app do Codex são os candidatos prováveis. O procedimento da
   janela de manutenção lista o que parar (coerente com a Q11).
2. **[W3 × W7, sequência]** Escrever a ordem que a regra «nenhum pacote de ADR em voo durante o kit»
   impõe:
   - o 1b (pacote de ADR) landa ANTES de começar a derivação do kit da W7, senão a W3.6 escorrega para
     depois do GA;
   - a inversão da rota 2 pode landar como PRIMEIRA peça da W7.1 (derivadores com oráculo 0, com os
     controles K-01 e K-02), para a W3.6 não esperar o kit inteiro.
3. **[W3, R-17]** O follow-up do kit chamar o verificador em modo só-verificação sobre a versão do
   manifesto também resolve a rota de emergência da condição 3, que passaria a ter os irmãos conferidos.
4. **[W3, custo]** O download duplo da Fase 1 (V-3 pelo `urllib` e V-8 pelo npm) fica. Se medir caro, o
   V-8 pode materializar a partir dos tarballs JÁ verificados do V-3.

## Unseen by the original plan

1. **Pelo H-07, toda cerimônia do verificador revoga a confiança no binário instalado** e bloqueia o rail
   até a re-verificação. É consequência direta do desenho, sem rotina operacional escrita.
2. **O rollback passa pelo canário**, então a recuperação depende de cota do Codex, que o freio Q2 limita.
3. **O hospedeiro da guarda do registro pode ser o `check_bash_safety.py`**, alvo do PLAN-195. Pelo I8,
   isso põe o PLAN-195 no caminho crítico da W3.6.
4. **O `npm ci` precisa de `package.json`**, e o plano lista só o lockfile.

## What I would NOT change

- A promoção só na MESMA execução da Fase 1, offline sobre o cache verificado, sob proxy morto, com P-01
  da árvore inteira e o prefixo efetivo igual ao do lançador do PATH (P-02..P-05).
- Quiesce por `lsof`/`ps` sobre o CAMINHO, nunca `pgrep -f`, e a promoção como janela curta de manutenção
  declarada.
- O R-16 declarado em vez de reter caches: a retenção vira follow-up nomeado.
- A rota 2 invertida (materializar sem executar → oráculo sem flag → `exec` do `path` verificado → só então
  `--version`), com o R-17 declarado.
- O verificador, o auxiliar e o material de empacotamento DENTRO do ADR-192, e o H-07 como lista permitida.
- A recomendação do ramo (ii): o código criptográfico fica governado pelo repositório, não pelo npm do
  Homebrew.
- Caches novos a cada execução com asserção de vazio, a lista fechada de hosts, os tetos medidos e as
  células F-01..F-09 todas como recusa.
- A CLI só-manifesto por padrão e o Gate 4 reprovando por desenho, com mensagem e nota de operador.

## Avaliação dos meus must-fix da W3 (rodada 2)

| MF (r2) | estado | evidência |
|---|---|---|
| 5 — rota 2 sem execução antes do oráculo e sem lançador | **atendido** | AMEND-1 §17 (4 passos), §9.K K-01..K-06, R-12 retirado, R-17 declarado; plano W3.6 (1) [:1155-1162], W7.1 [:1569-1571], «Pré-condições do corte» (i) [:1599-1605] |
| 6 — AMEND-1 reescrito com a W0.6 | **atendido** | §0 (as duas afirmações falsas corrigidas), §4.1 (`node` por caminho absoluto, versão mínima, ADR-192, identidade do instrumento), §4.2 V-4..V-6 (os dois bundles, vínculo pelo `subject` verificado), §4.4 (hosts, caches novos com F-08, tetos medidos), §2 (irmãos), §7 (ramos (i)/(ii) com testes), §24 (`SBOM.md`) |
| 7 — promoção pelos bytes verificados | **atendido** | §4.3 e §9.P: P-02 mesma execução, P-04 offline sob proxy morto, P-05 prefixo, P-01 árvore inteira; manifestos de membros na linha (§10.2); `--check-installed` (§15) |
| 8 — quiesce | **atendido** | P-03 (`lsof`/`ps` sobre o caminho, nunca `pgrep -f`); janela de manutenção declarada [AMEND-1 §22.5; plano «Declarar» (m)]; NTH 1 acrescenta a nomeação do processo |
| 9 — ADR-192 e paths | **parcial** | ADR-192 reconciliado: §4.1, §24 e plano [:1074-1077], mapa [:252] com a W3 (1a). Contagem e nomes divergem (1a: 6 × 8; Gate 4 em 1b × 2); faltam linhas de colisão para os hospedeiros da guarda → condições 1 e 2 |
| 10 — rollback sem rede, ou declarado | **atendido (declarado)** | R-16 [AMEND-1 §15, §21; plano :1004-1006, :1182]. O caminho do rollback passa pelo canário → condição 3 |

**Esforço (ADR-081, estimado):** as condições 1–6 somam ~80–150k tokens, entre texto, runbook e um teste
de contagem de SKIP. Isso cabe nos 1,6–2,8 M já orçados para a W3 em 3–4 sessões, que não mudam.
