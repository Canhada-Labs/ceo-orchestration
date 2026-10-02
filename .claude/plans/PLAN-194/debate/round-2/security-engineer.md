---
round: 2
archetype: Security Engineer
skill: security-and-auth
agent_persona: Security Engineer (Principal, auth/crypto VETO holder — ADR-052; supply chain, tamper-evidence, fail-closed matchers)
generated_at: 2026-10-02T01:40:00Z
served_model_id: claude-opus-5-5
plan: PLAN-194
plan_commit: 11c71a42
waves_in_scope: [W2, W3]
inputs:
  - .claude/plans/PLAN-194/debate/round-1/consensus.md
  - .claude/plans/PLAN-194-maintenance-train-v1-4-3.md (commit 11c71a42)
  - .claude/plans/PLAN-194/debate/round-2/ADR-055-AMEND-4-draft.md
  - .claude/plans/PLAN-194/debate/round-2/ADR-182-AMEND-1-draft.md
  - "medição W0.6 (relatório privado do Owner, fora do repositório; citada só pelas células e pelos números)"
veto:
  W2: "RETIRADO, condicionado a MF-R2-W2-1..4 no texto do ADR-055-AMEND-4 e do plano antes do pacote de ADR; SIGN só depois do LAND da W2.0"
  W3: "LEVANTADO até MF-R2-W3-1..8 no ADR-182-AMEND-1; «confiança no registro» como mecanismo deixa de ser resíduo aceitável depois da W0.6"
wave_verdicts:
  W2: PROCEED
  W3: RUN-ANOTHER-ROUND
---

# PLAN-194, debate L3 rodada 2: crítica do Security Engineer (só W2 e W3)

> **Legenda.** **[disco]**: li nesta rodada (HEAD `11c71a42`). **[rascunho]**: o rascunho afirma e eu conferi o ponto citado. **[W0.6]**: medição do Owner de 2026-10-02 (00:53Z–01:15Z), citada pelas células. **[inferência]**: dedução minha, a conferir.
> **Repositório público.** Classes de defeito e invariantes. Nenhuma receita de contorno de guarda.

## Verdict

**ADJUST** (posição geral).

- **W2: PROCEED** (`design-coherent`). **VETO RETIRADO, condicionado** a quatro pontos. MF-R2-W2-1 a MF-R2-W2-4 entram no texto do `ADR-055-AMEND-4` e do plano antes do pacote de ADR. A W2.0 (cura da condição 67) landa ANTES do SIGN da W2, como o rascunho já exige (`sign_precondition`, frontmatter).
- **W3: RUN-ANOTHER-ROUND. VETO LEVANTADO.** A W0.6 mudou a arquitetura da decisão de confiança: a assinatura passa a ser conferida pelo sigstore-js chamado por `node`, uma classe nova de dependência. O AMEND-1 ainda fala em «[a medir]», em «A-15 aceita e declarada» e em «confiança no registro», e a decisão pendente 3 do plano ficou PERIGOSA como está escrita. Há ainda três buracos de desenho novos: a promoção confere só o `bin/codex`; a rota 2 do corte executa antes de verificar; o registro não tem proteção contra escrita do PRÓPRIO agente. A rodada 3 fecha a W3 se o AMEND-1 revisado trouxer MF-R2-W3-1 a MF-R2-W3-8 e o Owner escolher o empacotamento do sigstore (i) ou (ii). Se o Owner escolher «confiança no registro», o VETO fica levantado e o impasse vai ao Owner (ESCALATE), conforme a regra de parada.

## Summary (≤ 3 bullets)

- **O que mudou:** o AMEND-4 aceita todos os MF da W2 e diverge, com razão, no gatilho `truly_lost`. O AMEND-1 traduz os 11 MF da W3 numa matriz de recusa completa (A-01..A-24, P-01/02, H-01..H-12, C/R).
- **Pontos fortes:** INV-NP por conjunto; nenhum `unlink` de `*.lock` em hook; journal removido na origem sob a própria trava; regex com `fullmatch` e `re.ASCII`; verificador fora de qualquer guard; hook só hash e consulta; registro fora de `state/` e da árvore git; evento antes da linha; CLI só-manifesto por padrão.
- **Pontos fracos:**
  - **W2:** o salto por prazo é silencioso e regride a observabilidade de travamento que o AMEND-3 garantiu por VETO. A âncora do prazo depende da ordem de import. Não há instrumento ligado de perda REAL.
  - **W3:** a W0.6 derruba o «a medir» e a fuga «confiança no registro». A promoção volta a confiar no registro para os executáveis irmãos. A rota 2 do corte executa antes do oráculo e, com a W3.6 antes do corte, vira o caminho PADRÃO.

## Risks

**R2-SEC1 [W3]. Severidade: HIGH.** A decisão pendente 3 do plano induz à variante mais fraca. O texto diz «só se a medição W0.6 reprovar o verificador do npm» e recomenda «confiança no registro» (`PLAN-194-maintenance-train-v1-4-3.md:1700-1704` **[disco]**). A W0.6 REPROVOU o comando `npm audit signatures`. Ele dá verde com payload adulterado (V-T2, V-R1), aceita atestado de outro repositório (S-11), passa com o atestado removido (V-P3) e passa offline com cache quente (V-N1/V-N3). Mas a biblioteca sigstore chamada com política SERVE: verde no íntegro e vermelho em toda adulteração e em toda identidade divergente (S-02..S-12). Lida ao pé da letra, a decisão 3 recomenda a confiança no registro justamente quando existe mecanismo medido que a dispensa. Nesse modo, um registro comprometido que sirva tarball e atestado assinados por OUTRO workflow, com o statement forjado, passa (W0.6 §1, razão 2).
*Mitigação:* MF-R2-W3-2.

**R2-SEC2 [W3]. Severidade: HIGH.** A promoção (Fase 2) volta a confiar no registro para os executáveis irmãos. O P-01 confere só o sha do `bin/codex` depois do `npm i -g` (`ADR-182-AMEND-1-draft.md:175-177` **[rascunho]**). O `npm i -g` BAIXA DE NOVO do registro, e o pacote de plataforma traz outros executáveis fora do sha pinado: `bin/codex-code-mode-host`, `codex-path/rg`, `codex-voice-host`, `zsh` e dylibs (W0.6 §6.8). Um registro comprometido na hora da promoção pode servir uma árvore com o `bin/codex` genuíno e um irmão malicioso: o P-01 passa, e o `codex` verificado lança o irmão. A procedência conferida na Fase 1 vale para os bytes do STAGING, não para os do global.
*Mitigação:* MF-R2-W3-4.

**R2-SEC3 [W3, W7]. Severidade: HIGH.** A rota 2 do re-pass executa o binário ANTES de verificar. A ordem é `npx -y <pacote> --version` em `PLAN-193/repass-ga/run-ga-repass.sh:266`, e só depois o oráculo, em `:282-286` **[disco]**. O `npx` usa o `.npmrc` do usuário (sem registro fixo) e roda os scripts de ciclo de vida. Hoje é caminho latente: a rota 1 serve quando o global é o pinado (`:249-258`). Com a W3.6 ANTES do corte (consenso §2(c)), o global deixa de ser o pinado, e a rota 2 vira o caminho PADRÃO de todo corte, na sessão em que o GPG do Owner está desbloqueado. O AMEND-1 propõe «inverter OU declarar» (R-12, `:488-493`, `:590`).
*Mitigação:* MF-R2-W3-6 (inverter; declarar não basta).

**R2-SEC4 [W3]. Severidade: MEDIUM-HIGH.** O registro concede confiança que dispensa a assinatura do Owner, e o próprio rascunho admite que a escrita dele «por shell dentro de uma sessão não tem guarda dedicada conhecida (a conferir)» (`:580-581` **[rascunho]**). O resíduo de mesmo UID (R-5) cobre um processo ALHEIO, que está fora do modelo. NÃO cobre o agente governado sob injeção de prompt, que está DENTRO do modelo: é para ele que existem os guardas de Edit/Write/Bash. Um agente injetado que acrescente uma linha coerente ao registro e instale um binário concede confiança a ele. O cruzamento do boot (linha sem evento ⇒ alarme, §14) só acusa DEPOIS.
*Mitigação:* MF-R2-W3-5.

**R2-SEC5 [W2]. Severidade: MEDIUM-HIGH.** O salto por prazo é silencioso e regride a observabilidade de travamento herdada do VETO do AMEND-3. O AMEND-3 só aceitou silenciar a contenção benigna com a condição de manter OBSERVÁVEL um portador travado da trava canônica (MF-1, `ADR-055-AMEND-3-opportunistic-drain-nonblocking.md:102-131` **[disco]**). Os detectores por contagem de linhas (`ceo-diagnose.py`, `status.py`) dependiam do breadcrumb do drain FORÇADO de saída. O AMEND-4 tira esse breadcrumb do caminho de saída (`exit_deadline_skip`, «sem breadcrumb», `ADR-055-AMEND-4-draft.md:285-287`, `:672-675` **[rascunho]**). O sinal que sobra é o G3 (`.draining.*` ou spool órfão com mais de 24 h, `:637`), visto só no boot. Hooks curtos raramente disparam o drain oportunista (o próprio rascunho admite, `:690`), então o breadcrumb `STARVED` gated também quase não sai. Resultado: com a trava canônica presa, a cadeia para de crescer em silêncio por até 24 h. Os eventos ficam em spool, que é PRÉ-cadeia (sem HMAC), e o tempo de residência fora da cadeia é a janela em que adulteração e remoção não deixam elo quebrado.
*Mitigação:* MF-R2-W2-1.

**R2-SEC6 [W2]. Severidade: MEDIUM.** A âncora do prazo depende da ordem de import. Ela é gravada no import do `spool_writer` (`:258-260` **[rascunho]**). O guarda canônico NÃO importa o `audit_emit` no topo: os imports de topo vão até `check_canonical_edit.py:73`, e o 1.º `from _lib import audit_emit` está dentro de função, em `:658` (e `:725`, `:1429`) **[disco]**. O `check_agent_spawn.py` faz o mesmo (`:2749`) **[disco]**. Num guard que trabalha antes de emitir, a âncora nasce TARDE, o tempo decorrido é subestimado, e a garantia S1 (decisão entregue) falha justamente nos guardas que mais importam. O rascunho declara isso como resíduo 1 (`:724-725`) e pergunta (R2-1).
*Mitigação:* MF-R2-W2-2.

**R2-SEC7 [W2]. Severidade: MEDIUM.** Não há instrumento LIGADO de perda real. O `truly_lost` está morto (consenso §0) e o rascunho o aposenta. A substituição proposta mede liveness (G3), cadeia (G5) e provas em teste (INV-NP), mas a única medida de PERDA de fato em produção, o G6, está «proposta; ver R2-3» (`:640`). Há ainda um caminho de perda real JÁ existente e sem gatilho: o `agent_spawn` descartado em `lock timeout (stale?) would-log=` (`audit_log.py:1324-1328` **[disco]**; resíduo 6 do rascunho, `:731-732`). A lição do AMEND-3 é exatamente esta: gatilho que não liga é pior que gatilho nenhum, porque dá falsa garantia.
*Mitigação:* MF-R2-W2-3.

**R2-SEC8 [W3]. Severidade: MEDIUM.** A afirmação pública «stdlib-only, zero third-party runtime deps — see SBOM.md» (`CLAUDE.md` §3) fica falsa quando a decisão de confiança passa a ser tomada pelo sigstore-js via `node`. Pela rota (i), é um módulo INTERNO do npm, não API pública, e muda com o npm do Homebrew. Pela rota (ii), é o `sigstore` com versão e integridade fixas (W0.6 §6.6).
*Mitigação:* MF-R2-W3-7.

**R2-SEC9 [W2, W3]. Severidade: LOW.** O plano e os rascunhos divergem em pontos de execução, e o plano é a fonte do builder:
- W2.3 do plano mantém «ou pelo dono na saída» (`:582-584`); o AMEND-4 a tira (§4.3, `:331-335`).
- W2.4 do plano descreve o GC em hook; o AMEND-4 o torna condicional (§4.5).
- W2.6 do plano diz «PID vivo ⇒ recusa»; o AMEND-4 diz «PID vivo ⇒ pula a família» (§5.2).
- W3.4 do plano mantém «senão ACEITA e DECLARADA» (`:892-893`).
- «Identidade do construtor» do plano ancora o digest no `dist.integrity` (`:821`); a W0.6 mostra que a âncora certa é o `subject` do bundle VERIFICADO.
*Mitigação:* MF-R2-W2-4 e MF-R2-W3-8.

## Must-fix (blocking)

**W2 (condições da retirada do VETO; dono: CEO no texto, builder no pacote)**

1. **MF-R2-W2-1.** Preservar a observabilidade de travamento do AMEND-3 (MF-1).
   - Uma trava canônica presa tem de virar sinal em ≤ T, valor pré-registrado (proposta: ≤ 1 h), sem volume por saída.
   - Controle positivo: um portador externo segura a trava pelo tempo T e o sinal aparece; um vermelho prova que o G3 de 24 h sozinho não basta.
   - O mecanismo fica com o builder. Exemplo aceitável: no salto por prazo, UM `stat` do log canônico; se ele não avança há mais que T, um breadcrumb `STARVED` com gate e taxa limitada, no formato que os detectores já contam.
2. **MF-R2-W2-2.** A âncora do prazo não pode depender da ordem de import.
   - Ela é a MAIS CEDO entre o instante do import e um marco de início do processo: o invólucro de hooks grava o marco incondicionalmente, ou cada guard o arma no início do `main`, com censo AST de todos os hooks registrados em PreToolUse.
   - Valor inválido, no futuro ou ausente ⇒ vale o do import. A direção do erro é sempre «menos tempo», que é segura.
   - Controle: um guard sintético que importa o `audit_emit` tarde, depois de trabalho simulado, entrega a decisão.
3. **MF-R2-W2-3.** O G6 entra NA W2, não em follow-up.
   - É um verificador só-leitura, fora de hook, com controle positivo, rodado no pós-LAND e no nightly. Conta como «quarentenado» (não perdido) o `record_id` que estiver em `.malformed.*`, `.quarantined.*` ou `.test-origin.*`.
   - Junto, o **G7**: a contagem datada de `would-log` (perda real de `agent_spawn`) depois do LAND, pelo mesmo método do G2, com controle positivo.
4. **MF-R2-W2-4.** Reconciliar o plano com o AMEND-4: W2.3, W2.4 (GC condicional, seletor `-k gc` só se o GC voltar), W2.5 (os mutantes M-a..M-d) e W2.6 (PID vivo ⇒ pula a família; mtime < 10 min ⇒ recusa a execução). Em cada divergência vale o texto do rascunho.

**W3 (condições da retirada do VETO na rodada 3; dono: CEO no AMEND-1 e no plano, Owner na escolha de empacotamento)**

5. **MF-R2-W3-1.** O V-5 é o sigstore-js chamado COM política.
   - Política: `certificateIdentityURI` exato (SAN do workflow de release do Codex com a tag amarrada à versão BASE `X.Y.Z`), `certificateIssuer` exato (emissor OIDC do GitHub Actions) e os ids IMUTÁVEIS do repositório e do dono em `certificateOIDs` (W0.6 §4), que barram renomeação ou recriação do repositório.
   - Nunca o comando `npm audit signatures`.
   - Os DOIS bundles (lançador e plataforma) são exigidos pelo verificador (A-12; o npm não reprova a falta, V-P3).
   - A-14 e A-15 viram RECUSA; some «aceita e declarada» (`:292`).
   - Os literais medidos entram no §6 como constantes canônicas com teste.
6. **MF-R2-W3-2.** Empacotamento do sigstore, uma decisão de desenho do Owner entre duas opções aceitáveis:
   - **(ii), preferida:** `sigstore` com lockfile de integridade de TODA a árvore, commitado sob a mesma governança do verificador (membro do manifesto ADR-192), instalado com `npm ci --ignore-scripts` em staging novo e com ambiente npm montado do zero;
   - **(i):** o módulo interno do npm, só com lista canônica de versões permitidas e recusa fora dela.
   Nos dois casos, a versão e o sha do lockfile (ou do módulo) vão na linha do registro e no evento HMAC (`signature_mode`). A decisão pendente 3 é REESCRITA nesses termos. «Confiança no registro» deixa de ser recomendação: se o Owner a escolher mesmo assim, o VETO fica LEVANTADO e o impasse vai ao Owner por múltipla escolha.
7. **MF-R2-W3-3.** Vínculo e frescor, conforme a W0.6:
   - o sha512 do tarball baixado é igual ao digest do `subject` do bundle VERIFICADO; o `dist.integrity` vira só um cruzamento (W0.6 §6.3);
   - caches do npm e do TUF NOVOS a cada execução, porque o cache quente dá verde sem rede (V-N1, V-N3);
   - o 2.º host (CDN do TUF do Sigstore) entra declarado na regra «mesmo host» (§4.4);
   - os tetos do §4.4 usam os valores medidos (W0.6 §6.7).
8. **MF-R2-W3-4.** A promoção confere a ÁRVORE INSTALADA inteira, lançador e plataforma, contra o manifesto de membros do tarball verificado (nome, tamanho e sha256, sem executável extra), OU instala a partir dos bytes verificados do staging. O P-01 deixa de olhar só o `bin/codex`. O §2 e o R-6 («escopo honesto») passam a dizer: o hook confere só o `bin/codex` a cada invocação; os irmãos são conferidos na promoção; a troca deles em tempo de execução é resíduo de mesmo UID.
9. **MF-R2-W3-5.** O registro fica protegido contra escrita do PRÓPRIO agente (Edit, Write e Bash, inclusive acréscimo por redirecionamento) pela mesma classe de guarda que protege a família do log de auditoria, com controle positivo (escrita no formato do agente ⇒ BLOCK). O «a conferir» do R-5 (`:580-581`) é resolvido no pacote 1, não declarado.
10. **MF-R2-W3-6.** A rota 2 do kit da 1.4.3 é INVERTIDA:
    - materializar sem executar, em prefixo novo, com ambiente npm montado do zero e `--ignore-scripts`;
    - oráculo sem flag;
    - só então qualquer execução, inclusive o `--version`.
    O R-12 sai da lista de resíduos aceitáveis: com a W3.6 antes do corte, essa rota é o padrão. É pré-condição da W3.6 (§16, item 6), com controle: espião prova zero execução antes do oráculo.
11. **MF-R2-W3-7.** `SBOM.md` declara a dependência de tempo de operação (`node` + sigstore-js, versão e integridade). A afirmação «stdlib-only» fica escopada ao runtime dos hooks, no MESMO pacote, sem afirmação pública falsa. (O `CLAUDE.md` só muda no fechamento; a poda já é pré-condição da W3.)
12. **MF-R2-W3-8.** Reconciliar o plano com o AMEND-1 e a W0.6:
    - resumo da W3.4: tirar «senão ACEITA e DECLARADA»;
    - «Identidade do construtor»: âncora no `subject` verificado e nos ids imutáveis;
    - paths do pacote 1: manifesto ADR-192, lockfile e `SBOM.md`;
    - o verificador como membro do ADR-192: o plano ainda o chama «livre» (`:848`), e o AMEND-1 o põe sob cerimônia (§4.1);
    - decisão pendente 3 reescrita (MF-R2-W3-2).

## Nice-to-have (advisory)

1. **[W2]** O auxiliar de saída faz `sys.stdout.flush()` ANTES da drenagem, mais uma célula da W0.5 que mede se o harness consome a decisão no EOF ou na saída do processo (ver Unseen 1). É barato e não substitui o prazo.
2. **[W2, R2-6]** O `_OWN_DRAIN_PENDING` é fail-safe: liga ANTES do rename e desliga só depois da remoção CONFIRMADA, com teste que injeta exceção entre o rename e a fase 5. Um erro aqui atrasa (perna 3), não perde, por isso fica como nice-to-have.
3. **[W2, R2-7]** Trocar o slug para algo sem «gc» (a emenda não tem GC em hook). Neutro para a segurança.
4. **[W3]** O shim da rota 2 executa o caminho do payload VERIFICADO (campo `path` do JSON do oráculo), não o lançador, coerente com o ADR-182 §2: «o artefato que foi hasheado é o que roda».
5. **[W3]** Ao reescrever o `_emit_audit()`, o sumidouro de teste (`check_pair_rail.py:1219`, honrado hoje sem o marcador de teste) passa a ser honrado SÓ no modo de teste, como as outras costuras do ADR-182 §2.
6. **[W3]** O H-07 inclui `verifier_sha256` e o sha do lockfile do sigstore no conjunto permitido pelas constantes atuais: linha gravada por verificador revogado ⇒ sem confiança.
7. **[W3]** Quando o global estiver auto-pinado, a mensagem de falha do Gate 4 da fase 6 (R-04) nomeia a rota 2. Um gate perpetuamente vermelho ensina a contorná-lo.
8. **[W3]** O canário (V-9) usa diff SINTÉTICO fixo, sem conteúdo do repositório (egresso).

## Unseen by the original plan

1. **[W2]** O CPython roda os `atexit` ANTES de esvaziar os buffers de `sys.stdout` na finalização [inferência; ordem do `Py_FinalizeEx`]. Num pipe, o JSON da decisão de um hook que não chama `flush` só sai DEPOIS da drenagem de saída. Isso reforça o prazo (MF-W2-3) e explica por que «fechar o stdout antes» (opção H do rascunho) não é trivial.
2. **[W2]** Spool é pré-cadeia. Todo mecanismo que aumenta a residência do evento fora da cadeia, como o salto por prazo, aumenta a janela em que adulteração ou remoção não deixam elo quebrado. Por isso a observabilidade do travamento (MF-R2-W2-1) é do domínio do VETO, não só de operação.
3. **[W2]** A âncora tardia atinge os guardas mais críticos (`check_canonical_edit.py`, `check_agent_spawn.py`), que importam o `audit_emit` dentro de função (R2-SEC6).
4. **[W3]** Depois da W0.6, a decisão pendente 3 do plano induz ao erro (R2-SEC1).
5. **[W3]** A Fase 2 baixa DE NOVO do registro, e os executáveis irmãos ficam fora do sha pinado (R2-SEC2).
6. **[W3, W7]** O caminho de release herda o vetor do `.npmrc` e dos scripts de ciclo de vida pela rota 2 (R2-SEC3).
7. **[W3]** A ameaça relevante ao registro é o agente governado sob injeção, não só o processo alheio de mesmo UID (R2-SEC4).
8. **[W3]** A afirmação «stdlib-only» do framework (R2-SEC8).

## What I would NOT change

**AMEND-4 (W2):**
- INV-NP por CONJUNTO, com (a) segurança, (b) unicidade e (c) vivacidade condicionada, e a quarentena contada, nunca apagada (`:154-175`).
- Nenhum `unlink` de `*.lock` em hook (T1), com T2 só em pacote de kernel próprio e condicional, e T3 fora (`:346-362`).
- Journal vazio removido pela compactação, sob a trava do PRÓPRIO journal, com reexame sob a trava e controle de intercalação por barreira (`:314-344`). É seguro porque o flush reabre pelo caminho, sob a mesma trava (`spool_writer.py:940-971` **[disco]**), e o censo mostra um único módulo abrindo `audit-pending.*` (`git grep` só acha o `spool_writer.py` **[disco]**).
- Versões mistas: nenhum caminho de trava ou de journal muda, então a dupla trava não se aplica (`:379-397`).
- Regex com `fullmatch` + `re.ASCII`, PID `[1-9][0-9]{0,9}`, e `_parse_spool_pid` proibido para decidir remoção (`:402-421`).
- A lista do que nunca se apaga, inclusive a família do log e as travas de outros módulos (`:423-439`).
- W2.6: `O_NOFOLLOW`, dono e modo do diretório, `unlink` com `dir_fd`, reexame por `(st_dev, st_ino)`, recusa sob `CEO_AUDIT_LOG_DIR`/`CEO_AUDIT_LOG_PATH`, manifesto de hash (`:452-493`).
- Reverter o prazo só com decisão escrita do Owner; nenhuma variável de ambiente nova (`:626-629`).
- `T_min` derivado dos settings, com teste de deriva. Conferi: o menor timeout é 3 s (uma registração), o resto ≥ 5 s (`grep '"timeout"'` em `.claude/settings.json` **[disco]**).

**AMEND-1 (W3):**
- Os invariantes I1–I7 (`:113-127`), sobretudo I2 (registro ausente ou duvidoso = zero confiança extra, nunca INFRA) e I7 (o registro nunca é lido pela trilha de release).
- A matriz A/P/H/C/R por célula, pré-registrada (`:269-331`).
- O verificador sob cerimônia (manifesto ADR-192) e o núcleo único reaproveitado (`:136-142`). Confirmo a escolha: o que ele grava substitui uma assinatura.
- Carência no relógio do REGISTRO (cabeçalho `Date` menos `time[...]`, o mais tardio das duas publicações), nunca «== `latest`», `deprecated` recusada, piso monotônico (`:200-224`).
- Evento ANTES da linha, com A-22 recusando sem evento (`:399-401`); quarentena terminal (`:438-442`).
- O achado do `_emit_audit()` (ver abaixo) e a decisão de LIGÁ-lo ao `emit_generic` no pacote 1.
- A faixa do `codex-cli-pin.txt`, o validador e o `release.yml` intocados (I1, §15).

---

## Julgamento dos must-fix da rodada 1

### W2

| MF | estado | evidência |
|---|---|---|
| MF-W2-1 (cura da condição 67 antes do SIGN) | **atendido no desenho**; execução pendente (decisão 1 do Owner) | AMEND-4 §7 `:589-610` (dentro da trava, DEPOIS do `rotate_if_needed`; barreira; censo AST; docstring); frontmatter `sign_precondition`; plano W2.0 `:543-554`. A trava do `audit_log.py` é a MESMA `audit-log.lock` do drain (`audit_log.py:320-323`; `spool_writer.py:429-434` **[disco, rodada 1]**), então a cura proposta fecha a corrida. Condição mantida: SIGN da W2 só depois do LAND da W2.0 |
| MF-W2-2 (nenhuma remoção de trava em hook; cura na origem) | **atendido** | AMEND-4 §4.3 `:314-344`, §4.4 `:346-362`, §4.5 `:364-377`, §5.2 `:484-485`; plano «Regra de travas» `:499-518`. Resta a reconciliação de texto (MF-R2-W2-4) |
| MF-W2-3 (prazo de saída + controle de entrega de decisão) | **parcialmente atendido** | Prazo, `min(SPOOL_LOCK_TIMEOUT, restante)`, reconferência antes da fase 2, controle W0.5 e prova estrutural: §4.2 `:256-312`; S1 em §6.1. Faltam a âncora independente da ordem de import (MF-R2-W2-2) e a observabilidade de travamento (MF-R2-W2-1) |
| MF-W2-4 (arquivo próprio, três pernas, versões mistas, regex, lista, reversão e gatilhos) | **atendido, com a divergência julgada abaixo** | §3.1–3.3 `:152-194`; §4.6–4.8; §8 `:614-652` |
| MF-W2-5 (estresse com todos os gravadores) | **atendido**, premissa corrigida aceita | §6.2 `:510-534` (`agent_spawn` com `desc_hash`, `kill -9`, reuso de PID, M-a..M-d, zero breadcrumb de perda). Aceito a refutação do consenso: não há drain no `SessionStart` (`SessionStart.py` sem `drain`/`spool`, consenso §0); a recuperação é pela perna 3 |
| MF-W2-6 (endurecimento do script da W2.6) | **atendido** | §5.1–5.3 `:452-493`. Aceito o refinamento da decisão pendente 2 (`:770-774`): «PID vivo ⇒ pula a família» é mais conservador que recusar tudo e não abre janela, porque «mtime < 10 min ⇒ recusa a execução» continua sinalizando sessão viva |

**Divergência do MF-W2-4 (gatilho `truly_lost`), julgada.** Aceito a troca. Pedi «`truly_lost_7d ≥ 1`» na rodada 1 porque supunha o contador vivo. O disco mostra que nenhum caminho o incrementa: só o padrão em `spool_writer.py:136` e a leitura em `:2562` (consenso §0, conferido). Manter um gatilho que nunca dispara é pior que não ter gatilho, porque dá falsa garantia; foi exatamente o que aconteceu com o AMEND-3. A substituição é correta NAS PROVAS (INV-NP por conjunto, com mutantes), em LIVENESS (G3) e na CADEIA (G5). Ela NÃO é completa sem um instrumento ligado de perda REAL em produção. Por isso o G6 deixa de ser «proposta» e entra na W2, e o G7 (`would-log`) cobre o escritor direto (MF-R2-W2-3). Com isso, a intenção do meu pedido («perda real dispara reversão») fica atendida por instrumentos que ligam.

### W3

| MF | estado | evidência |
|---|---|---|
| MF-W3-1 (todo «presente, mas não verificado» fail-CLOSED) | **atendido**, salvo a A-15 | I2/I5 `:115-123`; §7 `:249-267`; A-01..A-23 todos com saída 1; H-03..H-07 BLOCK; H-05/H-06 sem INFRA; §18.1 `:534-538`. A frase do L-9 foi corrigida (`:70`, `:178-180`). A exceção é a A-15 «aceita e declarada» (`:292`), que cai com MF-R2-W3-1 |
| MF-W3-2 (verificação fora de guard; confinamento) | **atendido**; ajustes da W0.6 em MF-R2-W3-3 | §4.1 `:131-145` (nunca em hook, guard, `/ceo-boot` ou Workflow); §4.4 `:182-193`; H-12 `:320`; §17 (guarda de socket com controle positivo) |
| MF-W3-3 (mecanismo de assinatura medido; nada de cripto à mão) | **parcialmente atendido**: o texto está superado pela W0.6 | V-5 «[a medir]» `:156`; A-15 `:292`; R-1 `:553-560`. A W0.6 mede que o comando do npm NÃO serve e que o sigstore-js com política SERVE. Fechamento em MF-R2-W3-1/2/3 |
| MF-W3-4 (identidade fixada; chave = membro único; gramática) | **parcialmente atendido** | Gramática estrita e armadilha medida: §5 item 1 `:204-210`. Membro único em fluxo: §6 `:244-247`, V-6. W0.6 L-M: 44 regulares, 0 links, 0 duplicatas. Faltam os literais (agora medidos), os ids imutáveis e os executáveis irmãos (MF-R2-W3-1, MF-R2-W3-4) |
| MF-W3-5 (registro: local, modos, leitores, contrato, resíduo) | **atendido**, salvo a escrita pelo agente | §9 `:333-360` (pelo `runtime_paths`, fora de `state/` e do git, `seq`/`prev_sha256`, esquema v1, fora de `*.jsonl` de topo); §10 `:362-373`; C-01/C-02. O «a conferir» do R-5 fica para MF-R2-W3-5 |
| MF-W3-6 (evento durável; kernel em série; promover o mismatch) | **atendido** | §11 `:375-401`; A-22; I6. Endosso o achado do `_emit_audit()` (abaixo) |
| MF-W3-7 (verificar → sondar → aceitar) | **atendido** | V-8 depois de V-7 `:159`; A-19/A-20; espião no §17 `:518-522` |
| MF-W3-8 (argv explícito; `--ignore-user-config`; `memories`; registro por rodada) | **atendido** (o valor do par é a decisão 5 do Owner) | §12 `:403-420` |
| MF-W3-9 (carência ≥ 48 h no relógio do registro; `latest` só teto) | **atendido** | §5 `:200-224`; A-08..A-11. O relógio é o `Date` do registro sob TLS, e a idade usa a mais tardia das duas publicações (a plataforma sai ~10 s antes do lançador, W0.6 §5) |
| MF-W3-10 (chamadores automáticos pelo núcleo ou declarados) | **atendido** | §13 `:422-434`; plano `:854-857` (livres no pacote 2, antes da W3.6, §16 item 1) |
| MF-W3-11 (faixa intocada; T-8 no mesmo pacote; W3.6 depois da W7) | **atendido**; a refutação da parte «depois da W7» é ACEITA, sob condição | §15 `:457-471`; §16 `:473-505`. O disco prova que a rota 2 ancora o corte no manifesto (consenso §0). A condição é a MF-R2-W3-6: a rota 2 hoje executa antes de verificar, e com a W3.6 antes do corte vira o padrão |

## Julgamento dos pontos novos

### AMEND-1 §19 (resíduos R-1..R-15)

| id | julgamento |
|---|---|
| R-1 «confiança no registro» | **RECUSADO como resíduo** depois da W0.6. Existe mecanismo medido (sigstore-js com política + vínculo stdlib) que fecha a A-14/A-15 sem cripto à mão. A decisão do Owner passa a ser o EMPACOTAMENTO (MF-R2-W3-2), não «assinatura ou não» |
| R-2 sentinela ausente | **aceito, declarado** (qualidade não é domínio do VETO). Sonda e canário cobrem a liveness, e o gatilho do ADR-111 §2 fica preservado como NÃO AVALIÁVEL |
| R-3 evidência só no registro | aceito **só** por decisão escrita do Owner; minha recomendação continua sendo o evento na cadeia |
| R-4 par modelo/esforço | fora do meu domínio; exijo só que seja explícito e registrado (atendido em §12) |
| R-5 mesmo UID | **aceito para processo ALHEIO; recusado como cobertura do agente governado** → MF-R2-W3-5 |
| R-6 escopo | aceito, com a correção dos executáveis irmãos (MF-R2-W3-4) |
| R-7 TOCTOU hash→exec | aceito (inalterado desde o ADR-182) |
| R-8 braços INFRA | aceito, com o `_emit_audit()` ligado, para a contagem do §14 ter instrumento durável |
| R-9 chamadores declarados | aceito |
| R-10 `parse_semver` por prefixo | aceito, declarado |
| R-11 adopters em INFRA aberto | aceito, declarado |
| R-12 ordem M4 na rota 2 | **RECUSADO como resíduo** → MF-R2-W3-6 |
| R-13 corte dependente de rede | aceito |
| R-14 carência ≠ detecção | aceito. A W0.6 §6.9 reforça: um comprometimento do próprio repositório ou do workflow de release produz atestado VÁLIDO com a identidade certa, e a carência é a única mitigação |
| R-15 downgrade dentro do registro | aceito. O piso monotônico do manifesto e a quarentena terminal limitam o efeito |

### AMEND-4 §14 (R2-1..R2-7)

| id | julgamento |
|---|---|
| R2-1 âncora | **o import NÃO basta** (R2-SEC6, com os sítios no disco) → MF-R2-W2-2 |
| R2-2 W2.4 condicional | **aceito.** Menos remoção em hook é menos superfície. O GC só volta como pacote próprio, com as condições do consenso já fixadas (`:369-377`) |
| R2-3 G6 | **entra na W2** → MF-R2-W2-3 |
| R2-4 sinais do check | **sim** ao spool órfão com conteúdo no check do boot. Uma linha no `audit-log.errors` saída do CHECK não basta para travamento, por causa da latência de boot → MF-R2-W2-1 |
| R2-5 valores | ε = 0,01; `EXIT_MARGIN_S` = 1,0 s e prazo de 2,0 s como VALORES INICIAIS, re-medidos na W0.5 antes de valer; N ≥ 1.000 elos; limite de 2.000 `stat`; teto de 1.000 só para journals sob T1; Linux de vida longa como gatilho da T2. Aceito todos |
| R2-6 sinalizador próprio | fail-safe recomendado (nice-to-have 2); o erro custa atraso, não perda |
| R2-7 slug | neutro |

### `_emit_audit()` do `check_pair_rail.py`

**Confirmo o achado.** `_emit_audit()` (`check_pair_rail.py:1212-1236` **[disco, rodada 1]**) escreve só no sumidouro de teste e no stderr, e não chama o `emit_generic` nem para ações JÁ registradas, como o `pair_rail_codex_unavailable` (registrado em `audit_emit.py:513` e `:1862` **[disco, rodada 1]**). Isso agrava o que apontei na rodada 1 (R-SEC8): o braço INFRA («o rail some», allow) nunca deixou registro durável vindo do hook, e o braço fail-closed do pin também não. A decisão do AMEND-1 (§11, `:389-395`) é correta e suficiente: REGISTRAR no pacote de kernel e LIGAR o sítio de emissão no pacote 1, com taxa limitada. Nada a acrescentar além do nice-to-have 5 (sumidouro de teste só no modo de teste).

### A ordem npx-antes-do-pin nos runners do re-pass

**Confirmo no disco.** `PLAN-193/repass-ga/run-ga-repass.sh:266` executa `npx -y "$CODEX_PKG" --version` antes do oráculo de `:282-286` **[disco]**. O comentário da rota 1 (`:245-246`) declara a «ordem M4» que a rota 2 viola. É o mesmo princípio que o `pair-rail-gate.sh` impõe ao Gate 4 («BEFORE any binary exec — M4», `.claude/scripts/local/pair-rail-gate.sh:180-181` **[disco, rodada 1]**). O npx também herda o `.npmrc` do usuário e roda scripts de ciclo de vida. Com a W3.6 antes do corte, esse deixa de ser caminho de exceção. Exigência: inverter (MF-R2-W3-6). Declarar não basta.

### A medição W0.6

Aceito as conclusões e as uso para fechar o MF-W3-3:
- o comando do npm não serve (V-T2, V-R1, V-P3, V-N1/V-N3, S-11);
- o sigstore-js com política serve (S-02..S-12);
- o vínculo stdlib pega o adulterado (L-T2, L-P3);
- o cache precisa ser novo a cada execução;
- os executáveis irmãos ficam fora do pin.

A escolha entre (i) e (ii) é de desenho, com custo declarado (W0.6 §6.6). Prefiro (ii): o código que toma a decisão criptográfica fica governado pelo repositório (lockfile com integridade, sob cerimônia), e não pelo npm do Homebrew, que se atualiza fora da governança.

## Esforço adicional (ADR-081: tokens e sessões)

- **W2** (MF-R2-W2-1..4): mais 100–200 mil tokens dentro do pacote da W2, sem sessão extra. O G6 é um script só-leitura livre (~50–100 mil).
- **W3** (MF-R2-W3-1..8): mais 0,3–0,6 M tokens e até +1 sessão: empacotamento do sigstore com lockfile, verificação da árvore na promoção, guarda do registro, inversão da rota 2 no kit e `SBOM.md`. A rodada 3 do debate para a W3 custa ~150–300 mil tokens.
- **external_wait:** inalterado (carência de 48 h no relógio do npm).

## Estado do VETO e veredito por onda

| onda | VETO | veredito | condição |
|---|---|---|---|
| **W2** | **RETIRADO, condicionado** | **PROCEED** (`design-coherent`) | MF-R2-W2-1..4 no texto do AMEND-4 e do plano antes do pacote de ADR; SIGN da W2 só depois do LAND da W2.0 |
| **W3** | **LEVANTADO** | **RUN-ANOTHER-ROUND** | MF-R2-W3-1..8 no AMEND-1 revisado; o Owner escolhe (i) ou (ii). Se o Owner escolher «confiança no registro» ⇒ ESCALATE (o VETO segue levantado) |

Nenhum conteúdo lido nesta rodada trouxe instrução dirigida a mim. Não houve injeção a relatar.
