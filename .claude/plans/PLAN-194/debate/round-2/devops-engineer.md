---
round: 2
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: "DevOps Engineer (Principal) — CI/CD, pipeline de release, toolchains pinados, SRE do estado local"
served_model_id: claude-opus-5-5
generated_at: 2026-10-02T01:20:00Z
scope: "W2 e W3 (a W5c saiu PROCEED na rodada 1 e não é reaberta aqui)"
inputs:
  - .claude/plans/PLAN-194/debate/round-1/consensus.md
  - .claude/plans/PLAN-194-maintenance-train-v1-4-3.md (commit 11c71a42)
  - .claude/plans/PLAN-194/debate/round-2/ADR-055-AMEND-4-draft.md
  - .claude/plans/PLAN-194/debate/round-2/ADR-182-AMEND-1-draft.md
  - medição W0.6 (evidência fora do repositório, citada só por classe de achado)
---

> **Legenda de evidência.** **[disco]**: li no HEAD `11c71a42`. **[W0.6]**: medição da W0.6 (fora do
> repositório). **[rascunho]**: o rascunho afirma. **[inferência]**: dedução minha, a conferir.
> Estimativas em tokens e sessões (ADR-081). Nenhum conteúdo lido trouxe instrução dirigida a mim.
> **Uma premissa minha da rodada 1 estava errada e eu a retiro:** «enquanto o PID vive, nenhum drainer
> toca os arquivos dele». A fase 1 recupera `.draining.*` também de PID vivo (`spool_writer.py:1277-1316`),
> e a compactação trava o journal do PID drenado (`:2276`). A recusa do VETO à remoção de travas pelo dono
> está correta.

## Verdict

**ADJUST** no geral. Por onda:

- **W2 — PROCEED (`design-coherent`), com must-fix de execução.** O desenho fecha:
  - o caminho rápido;
  - o prazo de saída;
  - o journal vazio removido na origem, sob a própria trava;
  - a regra de travas T1;
  - o INV-NP por conjunto;
  - gatilhos em instrumentos ligados.

  O que falta não pede outra rodada:
  - alinhar o texto do plano ao do AMEND-4 (há um Check vermelho por construção);
  - fixar a âncora do prazo pelo início do processo;
  - declarar que, sob T1, a W2.6 vira manutenção recorrente.
- **W3 — RUN-ANOTHER-ROUND (rodada 3, a última pela regra de parada).**
  - O AMEND-1 foi escrito ANTES da W0.6, e a W0.6 tornou falsas duas afirmações dele: «verificador
    stdlib-only» (§4.1) e «todo download no MESMO host» (§4.4).
  - A rota 2 dos cortes tem duas falhas de ordem que o rascunho trata como «inverter OU declarar»: o npx
    executa o binário antes do oráculo, e o shim executa o lançador, não o payload verificado.
  - A promoção busca de novo no registro em vez de instalar os bytes verificados.
  - O plano e o AMEND-1 divergem sobre a entrada do verificador no manifesto ADR-192, o que cria uma
    colisão fora do mapa.

  Não há P0 nem afirmação falsa no PLANO que justifique NO-GO.
- **Transversal (L-1):** a liberação por onda está aplicada. A W2 pode seguir sem a W3.

## Summary (≤ 3 bullets)

- **Rodada 2:** o CEO aplicou os 48 ajustes e escreveu os dois rascunhos. A W0.6 mediu o verificador do
  npm: o comando `npm audit signatures` não serve; a biblioteca sigstore com política de identidade serve.
- **Forte:**
  - o AMEND-4 tem rastreabilidade por must-fix, gatilhos com controle positivo e o reconhecimento
    explícito de premissas mortas;
  - o AMEND-1 tem matriz de recusa completa (A-01..A-24, P-01/02, H-01..H-12, C/R), contrato por
    consumidor, registro fora de `state/` e da árvore, e CLI só-manifesto por padrão.
- **Fraco (lado operacional):**
  - a W3 ainda não absorveu a W0.6;
  - a trilha de release (rota 2) executa código não verificado;
  - a promoção reabre a janela registro→disco;
  - na W2, a âncora do prazo não cobre o padrão real de import tardio dos guards;
  - o crescimento medido das travas sob T1 torna a W2.6 recorrente, e o plano ainda a trata como única.

## Risks

1. **R2-DO1 — HIGH — W3 × W7 — a rota 2 do corte executa bytes que o manifesto não cobre.**
   - **Ordem de execução:** `run-ga-repass.sh:266` roda `npx -y @openai/codex@<v> --version`, que executa
     o lançador e o payload, ANTES do oráculo (`:281-286`) [disco].
   - **Shim:** o shim faz `exec` do LANÇADOR (`:295-306`, `exec "$CODEX_LAUNCHER"`), não do `path`
     verificado que o oráculo devolve. O lançador JS nunca foi pinado: o ADR-182 §2 fechou esse
     «verifica A, executa B» só no hook.
   - **Ambiente do npm:** a rota 2 não usa ambiente limpo. Ela herda o `~/.npmrc` e as variáveis
     `npm_config_*` (só o cache é trocado, `:266`) e roda sem `--ignore-scripts`.
   - **Efeito:** um registro redirecionado pela configuração do usuário serve um lançador que o shim
     executa em todas as partes do re-pass. A W0.6 mostrou que o redirecionamento pela configuração é real.
   - **Mitigação:** must-fix 5.
2. **R2-DO2 — HIGH — W3 — o AMEND-1 contradiz a W0.6 em três pontos.**
   - §4.1 diz «stdlib-only». A W0.6 mostrou que a assinatura só se confere chamando `node` com a
     biblioteca sigstore.
   - §4.4 diz «todo download no MESMO host». A raiz TUF vem de outro host.
   - V-4/§6 comparam o tarball com o `dist.integrity` cru. A W0.6 diz que a comparação certa é com o
     digest do `subject` do bundle VERIFICADO.
   - Também falta, da W0.6: cache novo do npm e do TUF a cada execução (com cache quente, «sem rede»
     passou: células V-N1 e V-N3) e a exigência dos DOIS bundles pelo próprio verificador (o npm não
     reprova a falta de atestado: V-P3).
   - **Mitigação:** must-fix 6.
3. **R2-DO3 — HIGH — W2 — a âncora do prazo na importação não cobre os guards reais.**
   - **Onde está a âncora:** o prazo conta da importação do `spool_writer` (AMEND-4 §4.2).
   - **O padrão real é import tardio:** vários guards importam o `audit_emit` DENTRO de funções. Exemplos:
     `check_canonical_edit.py:658`, `:725`, `:1429` (timeout 5 s, `settings.json:189`),
     `check_skill_reference_read.py:155`, `:311` (timeout 3 s), `check_pair_rail.py:938`, `:1052` [disco].
     Se nenhum import de topo puxar o `audit_emit` antes [inferência a conferir], a âncora cai DEPOIS do
     trabalho do guard. Aí o prazo de 2,0 s começa tarde, e a decisão volta a se perder justamente no
     guard mais crítico.
   - **O controle S1 pode passar pela razão errada:** um guard sintético que importe cedo fica verde
     enquanto os reais continuam perdendo a decisão.
   - **Mitigação:** must-fix 2.
4. **R2-DO4 — MEDIUM — W2 — sob T1, o alívio da W2.6 é temporário.**
   - **Ritmo:** ~15,8 mil travas por dia (~330 PIDs emissores por hora × 2) [rascunho §6.3, inferência a
     partir de medição].
   - **Estimativa:** com reuso de PID no macOS (espaço ~10⁵), o estoque volta a ~100–130 mil travas em ~2
     semanas de uso intenso e a ~150 mil em ~3–4 semanas. Usei N·(1−e^(−n/N)) com ~7,9 mil PIDs emissores
     por dia; é teto, pois supõe 24 h de uso intenso [inferência].
   - **Efeito:** a célula «~150 mil travas» da W0.5 é o REGIME PERMANENTE, não um caso de borda. Com ~150
     mil nomes, cada drain de emissor lista ~0,2 s sob a trava canônica (escala linear da lane H-02
     [inferência]). Com 9 saídas concorrentes, as últimas encostam no prazo de 2,0 s.
   - **Gap:** a H3 do AMEND-4 fica «sem limiar», e o plano ainda chama a W2.6 de «limpeza única».
   - **Mitigação:** must-fix 4.
5. **R2-DO5 — MEDIUM — W3 — a promoção reabre a janela registro→disco.**
   - **Hoje:** o §4.3 do AMEND-1 promove por `npm i -g @openai/codex@<v>`, uma busca NOVA no registro
     depois da Fase 1.
   - **O que escapa:** o P-01 confere depois só o `bin/codex`. A W0.6 achou OUTROS executáveis no pacote
     de plataforma, fora do sha pinado: `codex-code-mode-host` (65 MB), `rg`, `zsh`, o host de voz e
     dylibs. Um tarball diferente servido no momento da promoção passa com o `bin/codex` certo e os
     auxiliares trocados.
   - **Mitigação:** must-fix 7.
6. **R2-DO6 — MEDIUM — W3 — promover no meio do trabalho.**
   - **Durante o `npm i -g`:** um hook de outra sessão pode hashear o payload no meio da substituição.
     O resultado é `mismatch` e BLOCK, o que é seguro, mas é ruído.
   - **Rodada em voo:** uma rodada de rail em andamento pode chamar auxiliares (`rg`, `zsh`,
     `code-mode-host`) da versão NOVA, já com o binário VELHO na memória. O desvio de versão vira
     `exit ≠ 0`, que vira `CodexUnavailable`, que vira advisory (`check_pair_rail.py:1058-1064`,
     `:1512-1524`) [disco]: o rail some em silêncio naquela escrita.
   - **Mitigação:** must-fix 8.
7. **R2-DO7 — MEDIUM — W3 — colisão fora do mapa e teto de paths.**
   - **Divergência:** o AMEND-1 §4.1/§21 põe o verificador no manifesto ADR-192
     (`gate-scripts-manifest.txt`). O plano o lista como livre, «manifesto ADR-192: não», e a linha do
     manifesto no mapa de colisões (`:230`) não inclui a W3 [disco].
   - **Teto de paths:** a W0.6 acrescenta um auxiliar JS do sigstore e, provavelmente, a declaração no
     `SBOM.md`. O pacote 1 passa de 8 paths: AMEND-1, `check_pair_rail.py`, verificador `.py`, auxiliar
     `.js`, testes, T-8, manifesto ADR-192, `SBOM.md` e, na opção (b) do must-fix 6, um lockfile.
   - **Mitigação:** must-fix 9.
8. **R2-DO8 — MEDIUM — W2 — o plano diverge do AMEND-4 em quatro pontos.**
   - **W2.2-bis:** o plano diz «timeout de 5 s menos margem» (`:574`); o AMEND-4 usa `T_min` = 3 s.
   - **W2.3:** o plano diz «pela compactação OU pelo dono na saída» (`:583`); o AMEND-4 §4.3 deixa só a
     compactação.
   - **W2.4:** no plano, o GC fica no pacote, com Check `-k gc` (`:597`). No AMEND-4 §4.5, ele é
     CONDICIONAL. Com a guarda de seletor vazio (`:637-640`), o Check da W2.4 sai 5 por construção.
   - **W2.5:** os mutantes do plano (`:609-611`) são de um GC que não existirá; os do AMEND-4 §6.2 são
     M-a..M-d.
   - **Mitigação:** must-fix 1.
9. **R2-DO9 — LOW — W3 — dependência de `node` e da biblioteca sigstore no verificador.**
   - **Opção (a), o módulo interno do npm:** não é API pública e muda de lugar num `brew upgrade` [W0.6].
     A falha é fail-closed (a adoção é recusada), então é perda de VIVACIDADE, não de segurança.
   - **Opção (b), sigstore fixado no staging:** puxa uma árvore de dependências (tuf-js e outras) que
     precisa de lockfile com integridade.
   - **Nas duas opções:**
     - `node` resolvido pelo PATH é o resíduo de mesmo UID (R-5);
     - a declaração «stdlib-only» do `CLAUDE.md` §3 e do `SBOM.md` (que cobre o runtime central) precisa
       nomear a exceção de ferramenta de mantenedor.
   - **Mitigação:** must-fix 6.

## Must-fix (blocking)

> Os itens valem POR ONDA. Os da W2 são condições de EXECUÇÃO: o CEO os aplica antes de abrir o pacote,
> sem nova rodada. Os da W3 entram no AMEND-1 e no plano antes da rodada 3.

### W2 (dono sugerido: CEO no texto; builder da W2 no código)

1. **[W2] Alinhar o plano ao AMEND-4** (R2-DO8):
   - W2.2-bis com `T_min` = menor timeout registrado (hoje 3 s) e o teste de deriva;
   - W2.3 só com a compactação (a remoção pelo dono fica como alternativa declarada);
   - W2.4 marcada CONDICIONAL, com o Check `-k gc` fora da lista de Checks da W2 até o GC voltar;
   - mutantes da W2.5 = M-a..M-d do AMEND-4 §6.2;
   - texto da W2.6 alinhado à decisão pendente 2.

   Sem isso, o Check da W2.4 é vermelho por construção e o rail audita dois textos contraditórios.
2. **[W2] Âncora do prazo = início do PROCESSO, não importação** (R2-1 do rascunho; R2-DO3).
   - **Como ler o início:**
     - No caminho Claude, o `_python-hook.sh` faz `exec` do Python (`:413`) [disco]: o PID e o instante de
       início são os do processo que o harness criou, e o tempo do wrapper fica incluído.
     - Esse instante sai do kernel, em stdlib: `sysctl` `kern.proc.pid` via `ctypes` no macOS; no Linux,
       `/proc/self/stat` mais `CLOCK_BOOTTIME`.
     - Fallback = importação, com o resíduo declarado.
   - **Alternativa equivalente:** censo AST com controle positivo exigindo, em todo hook registrado com
     timeout ≤ 10 s, o import de topo do `audit_emit` ou uma chamada de «armar prazo» no início do `main`.
     Essa variante toca hooks canônicos e pesa no teto de paths, por isso prefiro a primeira.
   - **Controle S1:** a célula de ENTREGA DE DECISÃO da W0.5 usa um guard sintético com IMPORT TARDIO
     depois de trabalho simulado, no molde do `check_canonical_edit.py`. Sem isso, o verde de S1 vale para
     a população errada.
3. **[W2] W0.5: dois acréscimos ao pré-registro.**
   - **(a) Intervalo medido desde o INÍCIO DO WRAPPER** até a âncora, não desde o início do interpretador.
     O `_python-hook.sh` procura o Python, faz hash do PATH com `shasum` e pode lançar `python3 -c` sem
     cache; o relógio do harness começa ali.
   - **(b) Vivacidade da perna 3 sob rajada:** contagem e idade dos spools órfãos com conteúdo ao fim da
     carga e depois de N emissores seguintes. Cada drain move ≤ `K_MAX` = 100 entradas
     (`spool_writer.py:53`), e com o diretório cheio cada drain lista ~0,2 s. É preciso mostrar que a
     perna 3 alcança a fila.
4. **[W2] T1 com limiar OPERACIONAL e a W2.6 como manutenção recorrente** (R2-DO4).
   - A H3 ganha um limiar que não é de segurança: com travas ≥ 100 mil (proposta), o check do `/ceo-boot`
     recomenda rodar a W2.6 de novo.
   - O plano declara que a W2.6 é RECORRENTE sob T1, com o custo operacional (fechar as sessões DESTE
     projeto a cada ~2–4 semanas de uso intenso).
   - O gatilho da T2 é pré-registrado: emissores na célula «~150 mil travas», ≥ 9 concorrentes, com
     `exit_deadline_skip` > 0 ou p95 de saída > o orçamento; ou a W2.6 precisar rodar mais de 1× por mês.
     A decisão sai da medição, não de opinião.

### W3 (dono sugerido: CEO no AMEND-1; builder da W3 e derivador do kit da W7)

5. **[W3 × W7] Rota 2 sem execução antes do oráculo e sem lançador** (R2-DO1).

   «Inverter OU declarar» (AMEND-1 §16 item 6, R-12) vira só **inverter**. Os derivadores do kit da
   1.4.3 trocam o `npx -y … --version` por:
   - materialização SEM execução: `npm install --prefix <OUT própria>` com `--ignore-scripts`, ambiente do
     npm montado do zero como na W0.6 (sem `.npmrc` do usuário, sem `npm_config_*`, registro fixo, cache
     novo) e a versão exata do manifesto;
   - oráculo sem flag sobre o lançador materializado;
   - shim que faz `exec` do **`path` verificado** que o oráculo devolve, como o hook já faz, e não do
     lançador;
   - só então o `--version`.

   A busca do lançador com `find` em `_npx/` some, porque o caminho fica determinístico.

   **Controle:** um lançador plantado diferente, num registro redirecionado pela configuração, NUNCA
   executa. Um espião prova zero execução antes do oráculo.
6. **[W3] Reescrever o AMEND-1 com a W0.6** (R2-DO2, R2-DO9).
    - **§4.1:** o verificador = orquestrador Python + auxiliar `node` para a assinatura. É exceção
      nomeada ao «stdlib-only», declarada no `SBOM.md` como ferramenta de mantenedor, fora do runtime
      central.
    - **V-5:** `sigstore.verify` com política de identidade (SAN do workflow e emissor do GitHub Actions)
      sobre o bundle que o PRÓPRIO verificador buscou, nos DOIS bundles. A falta de qualquer um é recusa
      do verificador (A-12).
    - **V-4:** sha512 do tarball = digest do `subject` do bundle VERIFICADO.
    - **V-3/V-5:** cache do npm e cache TUF NOVOS a cada execução, para que «sem rede» recuse.
    - **§4.4:** o host TUF entra como 2.º host declarado.
    - **Tetos:** os valores medidos na W0.6 (2× o maior).
    - **Achado lateral da W0.6:** declarar os outros executáveis do pacote de plataforma no §2.
    - **Escolha de procedência da biblioteca, com o custo escrito:**
      - (a) módulo interno do npm, com allowlist de versão e sha dos arquivos em constante canônica; uma
        atualização do npm vira recusa até a cerimônia;
      - (b) sigstore em versão exata, de lockfile com integridade, instalado no staging.

      **Recomendo (b),** porque desacopla do Homebrew e do npm e ancora a confiança numa constante
      canônica.
    - **Nas duas opções:** `node` resolvido por caminho absoluto, com versão mínima; versões do `node`, do
      npm e do sigstore, mais o digest da raiz TUF, gravados na linha do registro e no evento HMAC; e o
      auxiliar JS sob a MESMA cerimônia do verificador. Se só o `.py` estiver no ADR-192, a política de
      assinatura escapa da cerimônia.
7. **[W3] Promoção a partir dos bytes VERIFICADOS, nunca de busca nova no registro** (R2-DO5).
    - **Como:** a Fase 2 instala com `--offline` sobre o cache do staging que a Fase 1 acabou de
      verificar, ou mecanismo equivalente. O npm confere a integridade do tarball inteiro contra o
      packument já verificado, e assim os auxiliares (`rg`, `zsh`, `code-mode-host`) são os bytes
      atestados.
    - **Linha do registro:** grava o manifesto sha256 por membro do tarball de plataforma (44 membros
      regulares [W0.6]).
    - **Detecção posterior:** o `/ceo-boot` pode re-hashear os membros instalados FORA do hook (~333 MB,
      advisory; resíduo de mesmo UID).
    - **Efeito colateral:** acaba o download duplo da Fase 1 (V-3 pelo npm e V-4 pelo `urllib`).
8. **[W3] Promoção com quiesce** (R2-DO6).
    - Antes do `npm i -g`, o verificador recusa se houver processo executando o payload ou os auxiliares
      do prefixo global, conferido por `lsof` ou `ps` sobre o caminho do payload, nunca por `pgrep -f`
      (lição registrada).
    - O plano declara a promoção como janela curta de manutenção (as rodadas de rail param), no molde das
      «rodadas manuais congeladas» do plano B.
9. **[W3] Reconciliar o manifesto ADR-192 e os paths** (R2-DO7).
    - O plano e o AMEND-1 dizem a MESMA coisa sobre o verificador e o auxiliar JS. Recomendo os dois
      dentro do ADR-192.
    - O mapa de colisões ganha a W3 (pacote do verificador) na linha do `gate-scripts-manifest.txt`,
      «nunca em paralelo» com a W7, a W7b, a W10 e a W5c.
    - O pacote 1 é recontado e dividido se passar de 8 paths:
      - 1a: verificador + auxiliar + lockfile + testes + `SBOM.md` + manifesto ADR-192;
      - 1b: AMEND-1 + `check_pair_rail.py` + testes do hook + T-8.
    - O oráculo `--is-canonical` roda no auxiliar JS na abertura.
10. **[W3] Rollback sem rede, ou a dependência declarada.**
    - Hoje o rollback é reinstalar uma versão registrada (AMEND-1 §14), o que precisa de rede, porque a
      Fase 1 usa caches descartáveis.
    - **Opção recomendada:** reter o cache verificado das 2 últimas versões promovidas (~150 MB cada,
      endereçado por integridade, no diretório do registro). Assim o rollback é a mesma rota de promoção
      do must-fix 7, offline.
    - **Senão:** declarar R-16 «rollback exige rede; sem rede, o rail bloqueia até haver rede».
    - Em qualquer caso, a versão do MANIFESTO é o rollback final sempre válido (H-01) e a sua via de
      instalação offline também deve ser declarada.

### Transversal

11. **[Transversal]** Liberação por onda: ATENDIDA. Fica só o registro de que a W2 libera sem a W3: o
    `consensus.md` da rodada 2 registra o PROCEED da W2 separado.

## Nice-to-have (advisory)

1. **[W2.6] Prova positiva de «nenhum emissor vivo deste projeto».** Recusar a execução inteira se algum
   spool ativo ou `.draining.*` tiver PID vivo. É barato e fica dentro do predicado. Complementa o
   «mtime < 10 min»: uma trava aberta e um `flock` não mudam o mtime.
2. **[W2, G1] Cadência dos gatilhos.** «3 medições diárias seguidas» vira «3 execuções do check em dias
   DISTINTOS e consecutivos de uso». O check do boot roda por sessão, não por dia.
3. **[W2, opção H do rascunho] Fechar o stdout antes do drain** vira célula da W0.5. Se o harness entregar
   a decisão no EOF do stdout, essa é uma cura independente da calibração do prazo.
4. **[W3, §14] Comando único `--quarantine --rollback-to <v>`.** Hoje quarentenar a versão INSTALADA
   bloqueia todas as escritas L3+ até a reinstalação manual.
5. **[W3, rota 2] Sondar as flags do argv da W3 também na versão do MANIFESTO** (0.156.1), que o corte usa.
   O argv fixo (modelo, esforço, `--ignore-user-config`) tem de existir nela, senão o re-pass falha.
6. **[W3, §8.C R-04] Nota de operador.** Com o global auto-pinado, o `pair-rail-gate.sh --phase 6`
   reprova POR DESENHO. A saúde diária é a CLI com a flag; um vermelho esperado não pode ser lido como
   incidente.

## Unseen by the original plan

1. **O shim da rota 2 executa o lançador, não o payload verificado** (`run-ga-repass.sh:295-306`), com a
   configuração do npm do usuário herdada (`:266`). O ADR-182 fechou esse buraco só no hook.
2. **O import tardio do `audit_emit` é o padrão dos guards** (`check_canonical_edit.py:658`, `:725`,
   `:1429`; `check_skill_reference_read.py:155`). A âncora na importação não é caso raro.
3. **Sob T1, o estoque de travas volta à célula «~150 mil» em semanas.** A W2.6 deixa de ser única.
4. **A promoção por busca nova no registro não cobre os auxiliares executáveis** que a W0.6 achou no
   pacote.
5. **Promover com uma rodada em voo** gera desvio de versão binário/auxiliar, que degrada para advisory.
6. **A divergência ADR-192 entre o plano e o AMEND-1** cria uma colisão sem linha no mapa.

## What I would NOT change

- **W2:**
  - nenhum `unlink` de `*.lock` em hook (T1), com a T2 condicional por medição;
  - o journal vazio removido SÓ pela compactação, sob a própria trava (o único produtor de 0 byte);
  - o INV-NP por CONJUNTO;
  - `truly_lost` declarado morto e substituído por G1–G6 com controle positivo;
  - o mínimo GLOBAL de timeout (3 s) como base do prazo, por ser conservador e testável contra os settings;
  - «PID vivo ⇒ pula só a FAMÍLIA» na W2.6. Recusar a execução inteira faria o script nunca rodar: as
    famílias ocupam ~76% do espaço de PIDs. Com as sessões deste projeto fechadas, um PID vivo é de
    processo alheio, que não abre este state dir (por projeto desde o PLAN-182 W1). Isso, mais o
    «mtime < 10 min ⇒ recusa tudo», é suficiente.
- **W3:**
  - a carência de 48 h com a regra «a estável elegível mais nova, ≤ `latest`» (a minha objeção da rodada
    1 era à combinação com «== `latest`», que caiu);
  - registro fora de `state/` e da árvore;
  - CLI só-manifesto por padrão, com `pin_source`;
  - matriz A/H/C/R pré-registrada;
  - verificador fora de qualquer guard;
  - o `/ceo-boot` sem disparar o verificador;
  - a faixa intocada;
  - a trilha de release ancorada no manifesto;
  - a W3.6 logo depois do LAND.

## Avaliação dos meus must-fix da rodada 1

| MF (r1) | onda | estado | evidência |
|---|---|---|---|
| 1 — cura na origem no lugar da relocação | W2 | **atendido (journals); travas refutadas, aceito** | AMEND-4 §4.3 (remoção sob a trava do journal), §4.4 (T1); minha premissa refutada (§2.4 do rascunho) |
| 2 — caminho rápido só com o próprio estado; união reescrita | W2 | **atendido** | AMEND-4 §4.1 (`stat` + `_OWN_DRAIN_PENDING`, zero `listdir`), §3.2–3.3; plano W2.2 |
| 3 — transição sem perda, se a relocação ficasse | W2 | **prejudicado (a relocação saiu)** | AMEND-4 §4.6 (nenhum caminho muda) |
| 4 — GC de carona, com teto | W2 | **parcial** | AMEND-4 §4.5 o torna condicional e preserva as condições; o plano W2.4 ainda o põe no pacote, com o Check `-k gc` vermelho por construção → must-fix 1 |
| 5 — observabilidade pelo resultado | W2 | **atendido** | AMEND-4 §9 (`stat` limitado a 2.000, check fora de hook); plano W2.4-bis |
| 6 — AMEND-4 próprio, limiar, gatilhos ligados | W2 | **atendido (limiar como o consenso §2(d))** | AMEND-4 §6.3 (H1 fluxo, H2 teto), §8.2 G1–G6 com controle positivo, §8.3 |
| 7 — W0.5 mede latência antes e depois | W2 | **parcial** | AMEND-4 §6.4 (2³ + extras); faltam o intervalo desde o wrapper e a vivacidade da perna 3 → must-fix 3 |
| 8 — corrida do `audit_log.py` antes ou junto | W2 | **atendido no desenho; vaga do Owner** | AMEND-4 §7, `sign_precondition`; plano W2.0 |
| 9 — adoção em duas fases, fora do hook | W3 | **parcial** | AMEND-1 §4.2–4.3, I3, H-12; mas a promoção re-busca no registro e não há quiesce → must-fix 7, 8 |
| 10 — registro e leitores | W3 | **atendido (melhorado)** | AMEND-1 §9–§10 (fora de `state/`, I7) |
| 11 — CLI só-manifesto por padrão | W3 | **atendido** | AMEND-1 §8.C C-01/C-02, R-04; §10 |
| 12 — sonda e canário bloqueantes | W3 | **atendido** | V-8, V-9, A-19, A-20, §17 |
| 13 — rollback e quarentena nomeados | W3 | **parcial** | §14 + §17; o rollback depende de rede, sem declaração → must-fix 10 |
| 14 — elegibilidade | W3 | **atendido (48 h + a minha regra de escolha)** | §5; consenso §2(a) |
| 15 — rota 2 herdada; W3.6 não espera a W7 | W3 | **parcial** | §16 e plano W3.6 aceitam; mas a ordem M4 fica «inverter OU declarar» e o shim executa o lançador → must-fix 5 |
| 16 — mesmo argv nas duas trilhas + Q11 no re-pass | W3 | **atendido** | AMEND-1 §12; plano W3.6, condição 5 |
| 17 — dois eixos; id no instrumento de aposentadoria | W3 | **atendido (par = decisão 5)** | §12, R-4 |
| 18 — chamadores fora do hook | W3 | **atendido** | §13, R-9 |
| 22 — veredito por onda | transv. | **atendido** | consenso `wave_verdicts`; plano «Approach» |

**Esforço revisado (ADR-081, estimado):**

| onda | estimativa | composição |
|---|---|---|
| W2 | 1,0–1,8 M tokens, 1–2 sessões | Âncora pelo kernel (~50–100 linhas no `spool_writer.py`) + os acréscimos da W0.5; a W2.0 continua à parte (150–300k + ~50k) |
| W3 | 1,6–2,8 M tokens, 3–4 sessões | Pacotes 1a, 1b e 2, mais o de kernel do evento; os must-fix 5–10 somam ~200–400k |
| W7 | +100–150k tokens | Para a rota 2 reescrita |

**Regra de parada:** a W3 vai à rodada 3, a última. Se os must-fix 5–9 não entrarem no AMEND-1 até lá, o
impasse vai ao Owner por múltipla escolha, sem NO-GO: nenhum P0, e o plano não tem afirmação falsa.
Quem tem afirmação falsa é o rascunho (§4.1 e §4.4), e isso se corrige na rodada 3.
