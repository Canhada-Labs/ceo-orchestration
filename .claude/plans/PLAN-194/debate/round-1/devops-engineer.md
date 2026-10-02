---
round: 1
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: "DevOps Engineer (Principal) — CI/CD, pipeline de release, toolchains pinados, SRE do estado local"
generated_at: 2026-10-02T00:05:00Z
---

> **Legenda de evidência** (a mesma da proposta). **[disco]**: li no HEAD `6a9abb10`. **[plano]**: o
> plano afirma e eu não refiz. **[medido agora]**: medi só com leitura, em 2026-10-02T00:00Z, nesta
> máquina, com outras sessões do Owner abertas. **[inferência]**: dedução minha, a conferir.
> Estimativas em tokens e sessões (ADR-081). Nenhuma fonte externa trouxe «semanas de trabalho» para converter.

## Verdict

**ADJUST** no geral. Uma linha por onda:

- **W2 — ADJUST.** O desenho é viável. Proponho trocar a relocação (W2.3) por uma cura na origem,
  sem migração de layout, e um GC que aproveita a listagem do drain com teto por execução. A
  revisão de não-perda e o gatilho de reversão têm de usar instrumentos que estejam ligados.
- **W3 — ADJUST.** O ganho chega ANTES do corte, porque a rota 2 do runner do re-pass já separa o
  corte do binário global (L-7 cai). Duas premissas precisam mudar: a verificação de procedência
  fica fora do hook, porque dentro dele o timeout abriria o rail; e a CLI que três ferramentas de
  release chamam sem flag continua só-manifesto por padrão.
- **W5c — ADJUST.** O mapa de colisões está incompleto. O precedente tocou 76 paths, entre eles
  `install.sh`, o baseline do censo do instalador e `audit_log.py`. A migração do adopter precisa
  do derivador de baselines na bateria, porque o CI não pega a falha.
- **L-1:** cada onda pode liberar sozinha. As três não compartilham código, e as superfícies comuns
  já estão serializadas no mapa. Peço veredito por onda no `consensus.md`.

## Summary (≤ 3 bullets)

- O plano junta três L3 independentes: o estado da auditoria (W2), o pin automático do Codex (W3) e
  a adoção do Sonnet 5.5 (W5c). Cada onda tem must-fix próprio e todas ficam bloqueadas até o PROCEED.
- **Fortes:** o manifesto assinado continua sendo a âncora do release (o passo 15 fica intocado), a
  W2.6 é operação do Owner, com simulação por padrão, e há controles vermelho→verde em árvore
  descartável. O plano também mede e re-mede o que vai citar.
- **Fracos (lado operacional):**
  - a W3 põe rede e download dentro de um hook com timeout;
  - a W2 propõe migrar layout com processos em voo, apoiada num gatilho de reversão que hoje não
    mede nada;
  - a W5c subestima a própria pegada;
  - a amarra «Codex parado até o fim da W7» é mais conservadora do que o código exige.

## Risks

1. **R-DO1 — HIGH — W3 — fail-open por timeout no caminho que a W3 quer fechar.**
   - **Descrição:** o desenho (a) confere a procedência «na 1.ª vez que o rail vê uma versão nova»,
     ou seja, dentro do hook PreToolUse do rail, cujo timeout é 210 s (`.claude/settings.json:285`)
     [disco]. A conferência baixa o pacote de plataforma, ~331 MB [plano]. O próprio plano registra
     que um hook que estoura o timeout deixa a ação passar sem decisão (lane CC285-05) [plano]. Com
     rede lenta, a escrita L3+ passaria sem revisão cruzada.
   - **Mitigação:** o hook nunca usa rede. Ele só lê um registro local. A verificação roda fora do
     hook (must-fix 9), e um sha desconhecido gera `block`.
2. **R-DO2 — HIGH — W3 — versão nova quebrada degrada o rail em silêncio.**
   - **Descrição:** saída ≠ 0 do codex vira `CodexUnavailable` (`check_pair_rail.py:1058-1064`), e o
     hook responde «fail-OPEN advisory mode» (`:1512-1524`) [disco]. Basta um subcomando ou uma flag
     removidos (o A7 do PLAN-183 foi assim) para que as escritas L3+ passem sem revisão.
   - **Mitigação:** a sentinela de qualidade (b) «avisa, não trava» e não mede liveness. Por isso
     proponho sonda e canário BLOQUEANTES na adoção (must-fix 12), rollback nomeado (must-fix 13) e a
     contagem de falhas por versão no boot.
3. **R-DO3 — HIGH — W3 × W7 — mudança silenciosa de semântica de uma CLI de release.**
   - **Descrição:** `check_pair_rail.py --verify-codex-pin` é chamada SEM flag por
     `pair-rail-gate.sh:208` (o arquivo está em `.claude/scripts/local/`, não em `scripts/local/`) e
     por `run-ga-repass.sh:251` e `:283` [disco]. Se o kernel passar a aceitar o registro automático
     por padrão, um binário auto-registrado passa nesses pré-voos e só falha no `gen-envelope-ga.py`
     ou no passo 15 (`validate-pair-rail-verdict.py:745-763`), depois das rodadas PAGAS do re-pass.
   - **Mitigação:** manter o padrão só-manifesto (must-fix 11).
4. **R-DO4 — HIGH — W2 — o sintoma cresce enquanto o debate corre.**
   - **Descrição:** medi agora 226.811 entradas no state dir, das quais 226.573 são arquivos de 0 byte
     nos 3 padrões (eram 223.100 às ~20:08Z [plano]). O `audit-log.errors` tem 29.464 linhas, e 29.280
     delas são `drain canonical lock timeout` (19.568 em 2026-09-30 [plano]) [medido agora]. Cada uma
     dessas linhas é um drain forçado que esperou os 2,5 s inteiros (`SPOOL_LOCK_TIMEOUT`,
     `spool_writer.py:66`) [disco].
   - **Mitigação:** rodar a W2.6 já. A pré-condição dela pode encolher (nice-to-have 1).
5. **R-DO5 — MEDIUM — W2 — a migração de layout (W2.3) deixa resíduo permanente.**
   - **Descrição:** a compactação sai cedo quando o journal não existe no caminho novo
     (`spool_writer.py:2265`) [disco]. Durante a transição, um processo em voo com o código antigo
     grava o journal no lugar antigo, e o drainer novo não o encontra. Esse journal fica com conteúdo
     para sempre, porque o GC nunca apaga journal com conteúdo [inferência sobre o desenho da W2.4].
     Hoje já existem 214 journals com conteúdo [medido agora].
   - **Mitigação:** tirar a W2.3 (must-fix 1). Se ela ficar, vale a leitura dupla (must-fix 3).
6. **R-DO6 — MEDIUM — W2 — o custo de um GC de varredura própria não cabe em hook.**
   - **Descrição:** uma passada `os.scandir` com `stat` por entrada levou 50,7 s [medido agora]. É uma
     medição única, com disco frio e outras sessões abertas, mas mostra a ordem de grandeza. O
     `SessionStart` tem timeout de 5 s (`settings.json:565`) [disco].
   - **Mitigação:** GC de carona na listagem do drain, com teto (must-fix 4). O estoque é da W2.6.
7. **R-DO7 — MEDIUM — W2 — o gatilho de reversão do AMEND-3 não mede nada.**
   - **Descrição:**
     - O `revert_trigger_truly_lost_7d: 1` do AMEND-3 depende de `reconcile_journal_at_session_start`.
       A função não tem chamador em produção: o grep acha só a definição, um teste, uma cópia
       antiga em árvore de staging, um script histórico de cerimônia e textos de plano.
       O campo `truly_lost` nunca é incrementado (`spool_writer.py:136` e `:2562` são as únicas
       ocorrências) [disco].
     - Não existe nenhum evento `audit_flush_dropped_count` nos 16 arquivos de log, do de agosto ao
       vivo [medido agora].
     - A «perna session-start» do drain forçado, citada no frontmatter do AMEND-3, não roda em
       produção.
   - **Mitigação:** o AMEND-4 não herda esse gatilho. Usar gatilhos ligados (must-fix 6).
8. **R-DO8 — MEDIUM — W3 — a regra «== `latest` + carência» quase nunca se cumpre.**
   - **Descrição:** a cadência das estáveis do npm desde 2026-08-25 tem mediana de 22,5 h entre
     versões: 13 de 22 intervalos ficam abaixo de 24 h e 16 de 22 abaixo de 48 h [medido agora,
     `npm view @openai/codex time`]. Exigir «== latest com idade ≥ 48 h» deixaria o pin automático
     parado em ~73% dos dias. As correções que vieram logo depois de uma versão saíram em 2,8 h a 6,8 h
     (0.150.1, 0.153.2, 0.153.4, 0.156.1, 0.159.2).
   - **Mitigação:** critério de elegibilidade no must-fix 14.
9. **R-DO9 — MEDIUM — W3 × L1/L2 — alarme perpétuo no boot recomendando o caminho que o Owner recusou.**
   - **Descrição:** `check-substrate-drift.py` compara o instalado com o MANIFESTO e recomenda re-pin
     pelo `re-pin-codex.py` (`:10-30`, `:75`) [disco]. Depois da W3.6, o instalado ≠ manifesto vira o
     estado normal.
   - **Mitigação:** nice-to-have 2, antes da W3.6.
10. **R-DO10 — MEDIUM — W5c — pegada e colisões subestimadas.**
    - **Descrição:** o `WOPUS55.patch` (precedente da wave-opus55) tem **76** entradas `diff --git`
      [disco]. Entre elas estão:
      - `scripts/install.sh` (colide com a W5b e com a W1a/W1b do PLAN-183);
      - `.claude/scripts/data/installer-write-safety-baseline.txt`;
      - `.claude/hooks/audit_log.py` (colide com a cura da corrida do risco 11);
      - `templates/settings/settings.user.json` (colide com a W6);
      - `.claude/hooks/_lib/test_isolation.py`.

      O baseline do censo é indexado por LINHA (`scripts/upgrade.sh:103:symlink-follow:…`) e cobre
      `scripts/**/*.sh` (`check-installer-write-safety.py:127`, `:3964`; 254 entradas do
      `upgrade.sh`) [disco]. Mudar a contagem de linhas do `upgrade.sh` obriga a regenerar o baseline.
    - **Mitigação:** must-fix 19.
11. **R-DO11 — MEDIUM — W5c — a migração do adopter falha em silêncio.**
    - **Descrição:** o literal `superseded` mora no `upgrade.sh` (`:195-198`) [disco]. O derivador
      `derive-settings-baselines.py` existe, mas não está no CI: o grep em `.github/` e no
      `validate-governance.sh` dá 0. O teste do literal vivo pula em clone raso
      (`test_derive_settings_baselines.py`, docstring), e o `validate.yml` não define `fetch-depth`
      [disco]. O parity e2e aceita a divergência do `settings.json`.
    - **Mitigação:** must-fix 20.
12. **R-DO12 — MEDIUM — W3 × W7 — o revisor da trilha de release herda config global.**
    - **Descrição:** o runner do re-pass fixa só o modelo, por `-m`, com origem no ambiente ou no
      `~/.codex/config.toml` (`run-ga-repass.sh:633-658`, `:859`) [disco]. Esforço e `memories` vêm
      do config global, sem registro na PROVENANCE. O argv fixo da W3 vive no `codex_cli_shape.py` e
      não alcança o kit.
    - **Mitigação:** must-fix 16.
13. **R-DO13 — LOW — W3 — custo de cota da sentinela.**
    - **Descrição:** com cerca de uma estável por dia, adotar toda versão significa rodar a sentinela
      (Codex pago) quase diariamente, contra o freio Q2 (nenhuma rodada nova acima de 80% do semanal).
    - **Mitigação:** nice-to-have 3.
14. **R-DO14 — LOW — W3 — registro dentro da árvore git suja o SIGN.**
    - **Descrição:** os moldes de SIGN abortam com modificação rastreada (risco 9 do plano) [plano].
    - **Mitigação:** registro no state dir (must-fix 10).
15. **R-DO15 — LOW — W2 — um evento por arquivo apagado inundaria a cadeia.**
    - **Descrição:** seriam até ~226 mil elos. Além disso, um evento emitido por um processo que não
      tinha spool cria justamente os 3 arquivos que o caminho rápido quer evitar [inferência a partir
      de `spool_append`, `spool_writer.py:976-1040`].
    - **Mitigação:** observar pelo resultado (must-fix 5).

## Must-fix (blocking)

**W2** (dono sugerido: builder da W2; VETO de Segurança pelo ADR-052)

1. **[W2] Cura na ORIGEM no lugar da relocação (W2-1, L-5, L-4).**
   - **O que fazer:** como ÚLTIMO passo da saída de um processo que emitiu (depois do drain final e
     do flush do buffer do journal), apagar o próprio `audit-pending.<pid>.journal` de 0 byte e as
     duas travas próprias. Condições: o próprio spool está ausente ou vazio, o journal tem 0 byte e o
     buffer está vazio.
   - **Por que não precisa da trava canônica:** enquanto o PID vive, nenhum drainer toca os arquivos
     dele. A fase 2 só renomeia o próprio spool ou o de PID morto (`spool_writer.py:1343`, `:1350`), e
     a compactação de outro PID só acontece para spools que ela mesma drenou [disco].
   - **Ganho operacional:** a W2.3 sai do pacote, e não há layout novo nem leitura dupla para migrar.
     Fica o resíduo de processo morto por SIGKILL (hook morto por timeout), que é do GC (item 4).
2. **[W2] O caminho rápido da W2.2 confere só o PRÓPRIO spool (W2-2).**
   - Um `stat` por saída; nunca checar `.draining` do diretório, porque isso exige listar.
   - O AMEND-4 reescreve a união de não-perda do AMEND-3 (`ADR-055-AMEND-3:71`): a perna 2 vale só
     para quem tem spool próprio. Órfãos e `.draining.*` esperam o drain seguinte de QUALQUER processo
     emissor deste projeto (perna 3). Recuperar fica mais lento, mas nada se perde, porque o dado
     segue no disco.
3. **[W2, só se o debate mantiver a W2.3] Transição sem perda.**
   - Spools e `.draining.*` NUNCA mudam de lugar.
   - Leitura dupla (subdiretório, depois diretório plano) por uma versão inteira (1.4.3 → 1.4.4).
   - Teste de transição: processo com o código antigo grava no plano; o drainer novo compacta e não
     deixa journal com conteúdo órfão.
4. **[W2] Onde o GC roda e com que teto (W2-4).**
   - **Onde:** de carona na listagem que a fase 2 do drain forçado JÁ faz (`spool_writer.py:1273`),
     executado DEPOIS de soltar a trava canônica.
   - **Teto:** ≤ 200 arquivos e ≤ 50 ms por execução (valores a confirmar na W0.5).
   - **Predicado:** o do plano (0 byte, um dos 3 padrões, PID morto, trava obtida sem bloquear).
   - **Proibido:** varredura própria do diretório inteiro dentro de hook (R-DO6). O estoque de ~226
     mil arquivos é da W2.6, não do hook.
   - **Residual a declarar:** um PID reusado entre a checagem e o `unlink` pode ficar com a trava num
     inode desligado. A janela é estreita, e a cura na origem (item 1) evita o caso para os arquivos
     do próprio processo.
5. **[W2] Observabilidade pelo RESULTADO (W2-7).**
   - Uma checagem advisory no `/ceo-boot` (a L2 já abre o `ceo-boot.py`, que é livre) mostra a
     contagem de 0 byte nos 3 padrões e a idade do `.draining.*` mais velho. Breadcrumb só quando o
     teto do GC estourar.
   - Nada de evento por arquivo, e o `audit_emit.py` fica fora da W2.
   - Se o debate exigir um evento: UM pacote de registro de ações (W2, W3 e a promoção do
     `pair_rail_codex_pin_mismatch`, que hoje é só breadcrumb: `check_pair_rail.py:1204`, ausente do
     `_KNOWN_ACTIONS`), serializado com a W1a do PLAN-195.
   - Ação desconhecida vira breadcrumb e retorno silencioso (`audit_emit.py:5260-5262`) [disco].
6. **[W2] ADR-055-AMEND-4 em arquivo próprio (W2-6).**
   - **Limiar ABSOLUTO:** proposta de ≤ 1.000 arquivos nos 3 padrões depois de 24 h de uso normal,
     medido com as sessões DESTE projeto paradas. Um limiar relativo a uma base que cresce envelhece.
   - **Gatilhos de reversão em instrumentos ligados:**
     (a) resíduo acima do limiar em 3 medições diárias seguidas;
     (b) qualquer linha `drain canonical lock timeout` com carimbo depois do LAND, sob a carga da W0.5;
     (c) `.draining.*` com mais de 24 h.
   - Declarar que o `truly_lost` do AMEND-3 não mede nada hoje (R-DO7).
7. **[W2] A W0.5 mede latência, não só contagem.**
   - p50/p95 da saída de um hook em 4 células: (dir com ~220 mil entradas × vazio) × (processo
     emissor × não emissor), com 9 ou mais saídas concorrentes.
   - Antes e depois da cura, com o resultado no LEDGER. Sem isso, «a latência fica igual à do dir
     vazio» não tem base.
8. **[W2] A corrida do `audit_log.py` vem antes ou junto (W2-5).**
   - O estresse da W2.5 tem de incluir escritores `agent_spawn` concorrentes. Enquanto a corrida do
     risco 11 existir (`audit_log.py:1262-1283` [plano]), a W2 não pode afirmar «`verify_chain()`
     íntegro».
   - Recomendo pacote próprio, landado ANTES da W2 (150–300k tokens [plano]). Se faltar vaga, ele cabe
     dentro da W2 (+2 paths, 5–7 de 8).

**W3** (dono sugerido: builder da W3; VETO de Segurança pela cadeia de suprimento)

9. **[W3] Adoção em duas fases, fora do hook (W3-2, W3-5, L-9).**
    - **Fluxo:** o verificador instala a versão candidata num prefixo de staging próprio
      (`npm i --prefix <dir>`, com piso de `df` e diretório confinado, sem `-g`). Lá ele confere a
      procedência (cripto com Segurança), roda a sonda e o canário (item 12) e só então registra o sha.
      A promoção para o global (`npm i -g` da MESMA versão, com sha igual ao do staging) vem depois.
    - **Ganho:** «o rail segue na última versão verificada» passa a ser verdade, porque o global só é
      sobrescrito depois da aprovação.
    - **Gatilhos:** o Owner roda um comando, ou o `/ceo-boot` detecta uma versão elegível. Sem GPG, o
      que preserva «não mexer a cada versão».
    - **Se o Owner rodar um `npm i -g` cru:** o hook vê um sha fora do registro e responde `block`
      (fail-closed), nomeando o verificador. O hook não usa rede, e uma falha de rede é INFRA do
      verificador (versão não registrada), nunca INFRA do hook.
10. **[W3] Onde o registro mora e quem o lê (W3-1).**
    - **Local:** state dir do projeto (fora da árvore git; risco 9), escrita atômica, chave
      (versão, tripla).
    - **Campos:** sha256, digest da procedência, data, resultado da sonda, do canário e da sentinela,
      e `quarantined`.
    - **Leitores:** o passo 15 NÃO o lê, e o release continua ancorado no manifesto.
    - **Escopo:** só este repositório. Adopters não recebem `.claude/governance/` e seguem `infra`
      (CLAUDE.md §4).
    - **A declarar:** sob o mesmo UID não há fronteira de adulteração (CLAUDE.md §5).
11. **[W3] A CLI continua só-manifesto por padrão (R-DO3).**
    - `--verify-codex-pin` sem flag mantém a semântica de hoje. O aceite pelo registro exige flag
      explícita (ex.: `--allow-auto-pin`), usada pelo hook e pelo Check da W3. O JSON de saída ganha
      `pin_source: manifest|registry`.
    - **Controle:** um kit de corte com binário só auto-registrado falha no pré-voo, ANTES de qualquer
      rodada paga.
12. **[W3] Sonda e canário BLOQUEANTES na adoção (W3-8).**
    - **Quando:** depois da procedência e antes do registro.
    - **Sonda:** `--help` dos subcomandos e das FLAGS que os chamadores usam. A lista é a união dos
      chamadores: `exec`, `review`, `app-server`; `--sandbox`, `-o`, `--output-last-message`,
      `--output-schema`, `--color`, `--model`, `-m`, `--skip-git-repo-check`, `--ignore-user-config`,
      `-c`.
    - **Canário:** um `exec` mínimo com o argv REAL sobre um diff fixo, que tem de devolver JSON de
      veredito parseável.
    - **Falha:** não registra, e o rail segue na anterior.
    - A sentinela de QUALIDADE (b) continua não-bloqueante, como o Owner decidiu. O canário é
      LIVENESS e cobre o R-DO2.
13. **[W3] Rollback nomeado e testado.**
    - Reinstalar a versão anterior já registrada (verifica sem rede).
    - Comando de quarentena: uma versão com procedência válida passa a ser recusada.
    - Contagem diária de `pair_rail_codex_unavailable` no boot, por versão. O evento
      `codex_invoke_dispatched` já carrega `exit_code` (`check_pair_rail.py:1054`).
    - **Controles:** versão em quarentena ⇒ `mismatch`; reinstalar a anterior ⇒ `verified` offline.
14. **[W3] Elegibilidade (W3-4).**
    - A versão elegível é a estável mais nova (semver sem pré-release) com idade ≥ **24 h**, sem
      `deprecated` e ≤ `latest`. NÃO exigir «== latest» (R-DO8).
    - 24 h cobre as correções observadas (≤ 6,8 h); 48 h não acrescenta proteção medida e paralisa a
      adoção.
    - A `latest` serve de teto, não de prova de estabilidade.
    - A carência fica em constante canônica, com teste.
15. **[W3 × W7] W3-7 e L-7: o corte já tem rota própria; usar a rota.**
    - **Fato:** o runner do re-pass resolve a versão do MANIFESTO por `npx` num cache próprio quando o
      global é outra versão (rota 2), confere pelo mesmo oráculo e põe um shim no PATH
      (`run-ga-repass.sh:242-306`) [disco]. O GA 1.4.1 rodou assim: «rota do codex: npx (cache
      proprio)», com 0.155.0 (`PLAN-192/repass-ga/PROVENANCE-ga.md:5-6`) [disco].
    - **Must-fix:** o derivador do kit da 1.4.3 herda a rota 2, a igualdade de versão (`:253`) e a
      verificação pelo manifesto. O pré-voo do corte declara a rede e os ~331 MB.
    - **Consequência:** a W3.6 deixa de esperar o fim da W7, e o Codex global pode subir assim que a W3
      landar (L-7 cai). O manifesto só muda quando o Owner quiser mover a trilha de release (plano B
      sob demanda, não a cada versão). A regra W3.1 («0.156.1 até o land») fica.
16. **[W3 × W7] Mesmo argv do revisor nas duas trilhas (W3-10).**
    - O derivador do kit aplica a base da W3: modelo e esforço explícitos e `--ignore-user-config`,
      se o debate o adotar. Se não aplicar, declara a divergência no material assinado.
    - O pré-voo da Q11 (sha do config, modelo, esforço, `memories`) vale para o re-pass da rc e do GA,
      não só para as rodadas do rail.
17. **[W3] Dois eixos separados no AMEND-1 (W3-10).**
    - **BINÁRIO:** automático, cadência diária.
    - **MODELO e ESFORÇO:** constante canônica, cadência de geração. Aqui uma cerimônia é aceitável e
      coerente com «modelo novo ⇒ RE-TESTAR».
    - O id fixado entra no `model-deprecations.json` (instrumento da W3b) para receber o WARN de
      aposentadoria.
    - Hoje um id indisponível degrada para advisory (`codex_cli_shape.py:93`). Exigir visibilidade no
      boot (contagem diária), nunca silêncio.
18. **[W3] Chamadores fora do hook (W3-6).**
    - `codex_invoke.py` e `run-promotion-gate.py` são livres (oráculo 0): passam pelo kernel com a
      flag do item 11. Custo baixo e fora do teto canônico.
    - `codex_review_user_code.py` (hook ligado, `settings.json:642`) e `council-audit.js` (canônicos)
      ficam declarados no material assinado e vão para o backlog. O daemon `app-server` também fica
      declarado.
    - **A declarar:** depois da promoção do item 9, o binário do PATH JÁ é verificado. O buraco real
      das rodadas manuais é a janela de um `npm i -g` cru, e o hook a fecha no próximo uso.

**W5c** (dono sugerido: builder da W5c; QA/upgrade)

19. **[W5c] Censo da abertura comparado ao `WOPUS55.patch` (76 paths), com linhas novas no mapa de
    colisões.** Para cada uma, o outro pacote envolvido:
    - `scripts/install.sh`: W5b; W1a/W1b do PLAN-183;
    - `installer-write-safety-baseline.txt`: os mesmos, mais a W8 do PLAN-183;
    - `audit_log.py`: a cura do risco 11;
    - `settings.user.json`: W6;
    - `_lib/test_isolation.py`.

    O `check-installer-write-safety.py` entra na bateria. A W5c landa por ÚLTIMO no núcleo e
    re-deriva sobre o HEAD.
20. **[W5c] Migração do adopter (W5c-6).**
    - `derive-settings-baselines.py --check` entra na bateria, rodado num clone com TODAS as tags GA,
      porque em clone raso o teste pula.
    - O array de 8 ids da 1.4.2 entra em `superseded`, e o `new` acrescenta `claude-sonnet-5-5` NO
      FIM. O casamento é byte a byte, com a ordem (`upgrade.sh:184-186`).
    - Caso novo em `test_upgrade_settings_migration.py`: adopter com o array da 1.4.2 ⇒ MIGRATE;
      array customizado ⇒ PRESERVED.
    - A emenda 4 repete as duas cláusulas do A2.2 (itens 5 e 6) por referência ao derivador.
21. **[W5c × W7] Linha de corte (W5c-4).**
    - Se a W5c não estiver LANDADA quando começar a derivação do kit da W7, ela vai para depois do GA.
      `CHANGELOG.md`, o manifesto ADR-192 e o leque de ADR não podem ficar em voo junto com a W7.
    - Nenhum fato operacional antecipa a W5c. As colisões do item 19 empurram para depois.

**Transversal**

22. **[Transversal, L-1] Veredito por onda.**
    - O `consensus.md` registra PROCEED (ou volta) separado para W2, W3 e W5c. Uma onda com must-fix
      aberto não segura as outras.
    - Não há código compartilhado entre as três. As superfícies comuns (leque de ADR, `CLAUDE.md`,
      `CHANGELOG.md`, `audit_emit.py`) já são serializadas pelo mapa.

## Nice-to-have (advisory)

1. **[W2.6, operação] Destravar a limpeza hoje.**
   - A pré-condição «todas as sessões do Claude fechadas» vira «nenhum processo vivo DESTE projeto».
     O state dir é por projeto (CLAUDE.md §5; W1 do PLAN-182), e o predicado já é por arquivo (PID
     morto, mtime > 10 min).
   - O plano registra que a W2.6 está PENDENTE porque o Owner tem sessões em OUTROS repositórios
     («How to continue», Q1) [plano]; essas sessões não tocam este state dir.
   - O script confere os PIDs dos próprios nomes.
2. **[W3 × L1/L2, antes da W3.6] O detector de deriva lê o registro.**
   - Instalado ∈ registro verificado = sem deriva.
   - Instalado ≠ manifesto vira informação para o próximo corte, não recomendação de re-pin (R-DO9).
   - Os dois arquivos são livres.
3. **[W3, cota] Adoção sob demanda.**
   - Adotar quando o Owner atualiza, ou no máximo uma vez por semana.
   - A sentinela roda uma vez por versão adotada e fica adiada, de forma VISÍVEL («sentinela
     pendente» no boot), acima de 80% do semanal (Q2).
   - O gatilho do ADR-111 §2 (desvio > 5 pp do catch_rate) fica preservado como AVISO quando o corpus
     da sentinela for o corpus travado; a reabertura do corpus continua sendo do Owner (W3-9).
4. **[L-6] Ordem dos pacotes de ADR.**
   - O primeiro que ficar pronto landa primeiro, um por fechamento.
   - Nenhum fica em voo entre o início da derivação do kit da W7 e a publicação do GA.
   - Pela ordem das vagas, a ADR-201 (parte A do PLAN-195) tende a ser a primeira.
5. **[W5c × Q13-h] Viés na métrica de custo.**
   - Até a W5c landar, a medição de custo de cada onda no LEDGER reporta os tokens do
     `claude-sonnet-5-5` separados. Hoje eles saem a US$ 0 [plano], e a métrica de −1/3 fica enviesada
     para baixo.
   - Isso não antecipa a W5c.
6. **[W3-2, custo operacional] Reaproveitar o cache do npm.**
   - Depois de um `npm i`, o tarball de plataforma fica no cache do npm (`_cacache`), endereçado por
     sha512, que é o mesmo valor de `dist.integrity`.
   - O verificador pode ler dali antes de baixar de novo. A parte criptográfica é de Segurança.
7. **[W3-3] Declarar no AMEND-1 um limite do validador.**
   - `parse_semver` do validador do veredito usa `re.match` de prefixo
     (`validate-pair-rail-verdict.py:355-359`), então «0.159.0-alpha.12.1» conta como 0.159.0 [disco].
   - Se a faixa for alargada, o passo 15 não garante «só estável»; quem garante é o sha do manifesto.
   - Recomendo NÃO alargar a faixa na W3. Ela fica como gate da trilha de release, coerente com o
     must-fix 15.
8. **[W5c-4 × L3] Ordem entre o `adopt-model.py` e a W5c.**
   - A W5c é a 3.ª adoção. A regra «cure a CLASSE» pede o L3, que é land livre e não ocupa vaga,
     ANTES da W5c.
   - Se o L3 não estiver pronto quando a vaga da W5c abrir, a W5c clona o molde
     `apply-opus55-edits.py` e o L3 é extraído dos dois derivadores.
9. **[W2] Re-medir `SPOOL_LOCK_TIMEOUT` depois da cura.** Com o diretório pequeno, a espera de 2,5 s
   na saída dos processos emissores pode baixar; decidir pela W0.5, não agora.

## Unseen by the original plan

1. **A reconciliação de início de sessão não roda em produção.**
   - `reconcile_journal_at_session_start` não tem chamador em produção, e `truly_lost` nunca é
     incrementado. Há 0 eventos `audit_flush_dropped_count` em 16 logs [disco + medido agora].
   - Consequências: (a) o gatilho de reversão do AMEND-3 é vazio; (b) a «perna session-start» citada
     no frontmatter do AMEND-3 não existe em produção; (c) a L-10 trata de código morto, e a listagem
     de `:2480` não custa nada hoje; (d) os 214 journals com conteúdo não têm leitor em produção. A W2
     precisa decidir entre ligar a reconciliação (com custo limitado) e declarar os journals
     forense-only.
2. **A W3 pode abrir o rail por timeout do hook** (R-DO1). A doutrina do plano sobre timeout de
   PreToolUse vale também para o hook do rail.
3. **O corte já é independente do binário global** pela rota 2 do runner (must-fix 15). A amarra
   «Codex parado até o fim da W7» (W3.1, W3.6, `external_wait`) é mais conservadora do que o código.
4. **Esforço e `memories` do revisor da trilha de release vêm do config global, sem registro**
   (R-DO12). A Q11 hoje cobre só as rodadas do rail.
5. **A semântica da CLI usada por três ferramentas de release** (R-DO3). O plano não lista nenhum
   molde de corte como consumidor da CLI.
6. **O detector de deriva vira alarme permanente depois da W3.6** (R-DO9).
7. **A pegada real da W5c** (76 paths no precedente) inclui o baseline do censo do instalador (indexado
   por linha) e o `audit_log.py` (R-DO10).
8. **Com a cadência medida, «== latest + 48 h» quase nunca vale** (R-DO8).
9. **Emitir um evento de GC a partir de um processo sem spool recria os 3 arquivos** que o caminho
   rápido quer evitar (R-DO15).
10. **Números envelhecidos** (risco 11) [medido agora]: 226.811 entradas e 226.573 de 0 byte; 29.280
    linhas de timeout; a tag `alpha` está em 0.162.0-alpha.1 (a proposta cita 0.161.0-alpha.13).

## What I would NOT change

- **O manifesto assinado como âncora da trilha de release.** O passo 15 e o validador (membro do
  ADR-192) ficam intocados. O pin automático vale para o hook do rail, não para o corte.
- **O fail-closed em sha divergente** (ADR-182 §2): nenhuma variável de ambiente relaxa a comparação.
  O hook nunca troca `mismatch` por `infra`.
- **A W2.6 como operação do Owner, fora do repositório**, com simulação por padrão, `--apply` explícito
  e a regra de que journal com conteúdo NUNCA é apagado.
- **Debate único com must-fix por onda; a W3b antes da W3 (Q8); a W5c como primeira a sair se a cota
  apertar (Q7).**
- **O formato da Amendment 2 para a W5c** (só o working set, com piso, fallback e pin inalterados). É o
  menor pacote que cumpre «Adotar», derivado por script.
- **A W3.1** (Codex no 0.156.1 até a W3 landar), o hold de 24 h entre rc e GA, os materiais de
  cerimônia como último land, o `check-ceremony-script.py` na bateria e a poda do `CLAUDE.md` antes da
  W3.
- **A medição W0.5 como controle vermelho da W2** e a prova no VIVO no critério de sucesso (estado
  inteiro, com o subdiretório incluído, se houver).

## Respostas às perguntas da proposta (índice para o `consensus.md`)

| id | resposta (DevOps) | onde |
|---|---|---|
| W2-1 / L-5 | Cura na origem como último passo da saída, sem trava; GC só para o resíduo de processos mortos | MF 1, 4 |
| W2-2 | Caminho rápido confere só o próprio spool; órfãos ficam com o drain seguinte de qualquer processo emissor (perna 3) | MF 2 |
| W2-3 / L-4 | Tirar a W2.3. Se ficar: spools e `.draining` não mudam de lugar, e a leitura é dupla por uma versão | MF 1, 3 |
| W2-4 | De carona na fase 2 do drain, depois de soltar a trava; ≤ 200 arquivos e ≤ 50 ms; o estoque é da W2.6 | MF 4 |
| W2-5 | A cura da corrida do `audit_log.py` vem antes (ou dentro, com +2 paths); o estresse inclui `agent_spawn` | MF 8 |
| W2-6 | Arquivo próprio; limiar absoluto (≤ 1.000); gatilhos de reversão em instrumentos ligados | MF 6 |
| W2-7 | Pelo resultado, no `/ceo-boot`; nenhum evento por arquivo; `audit_emit.py` fora | MF 5 |
| W3-1 | Registro no state dir; o passo 15 não o lê; só este repositório | MF 10 |
| W3-2 | Fora do hook, com staging; a parte criptográfica é de Segurança; dá para reaproveitar o cache do npm | MF 9; NTH 6 |
| W3-3 | A faixa fica (gate da trilha de release); declarar o limite do `parse_semver` | NTH 7 |
| W3-4 | Estável mais nova com idade ≥ 24 h, sem `deprecated`, ≤ `latest`; sem «== latest»; constante canônica | MF 14 |
| W3-5 / L-9 | O hook bloqueia um sha desconhecido; falha de rede é INFRA do verificador; o staging mantém a última versão verificada | MF 9, 13 |
| W3-6 | Os chamadores livres passam pelo kernel; os canônicos e o daemon ficam declarados | MF 18 |
| W3-7 / L-7 | A rota 2 do runner já separa o corte do global; a W3.6 não espera a W7 | MF 15 |
| W3-8 | Sonda de subcomandos e flags, mais canário funcional, bloqueantes na adoção | MF 12 |
| W3-9 | O gatilho do ADR-111 §2 fica como aviso, com o corpus travado na sentinela | NTH 3 |
| W3-10 | Eixos separados; argv fixo também no kit; o id fixado entra no instrumento de aposentadoria | MF 16, 17 |
| W5c-4 | Nenhum fato antecipa a W5c; ela landa por último no núcleo; linha de corte com a W7 | MF 19, 21 |
| W5c-6 | `derive-settings-baselines.py --check` num clone com todas as tags; o array de 8 ids vai para `superseded` | MF 20 |
| L-1 | Veredito por onda | MF 22 |
| L-6 | Primeiro pronto, primeiro a landar; nada em voo durante o kit e o GA | NTH 4 |
| L-10 | A reconciliação é código morto em produção (Unseen 1) | — |

**Esforço revisado (ADR-081, estimado):**

| onda | estimativa | observação |
|---|---|---|
| W2 | 0,8–1,2 M tokens, 1–2 sessões | Sai a W2.3 e entra a cura na origem; +150–300k se a corrida do risco 11 vier junto |
| W3 | 1,2–2,0 M tokens, 2–3 sessões, provavelmente em 2 pacotes de ≤ 8 paths | (a) kernel, registro, verificador, sonda, canário e AMEND-1; (b) argv fixo e chamadores livres. O plano estimava 0,8–1,5 M |
| W5c | 2–4 M tokens | Mantida, + ~100–200k para o censo contra o precedente |
| W7 | +100–200k tokens dentro do 1–2 M dela | Herdar a rota 2 e o argv |
