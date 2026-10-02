---
round: 1
archetype: QA Architect
skill: testing-strategy
agent_persona: Principal QA Architect
generated_at: 2026-10-02T00:15:00Z
---

# PLAN-194 — rodada 1 — crítica do QA Architect (W2, W3 e W5c)

> **Legenda de evidência.** **[disco]**: li no HEAD `6a9abb10` nesta sessão. **[medido]**: contei eu, só lendo, no state dir vivo deste projeto em 2026-10-01T23:55Z (macOS 27.0.1). **[plano]**: o plano afirma e eu não refiz. **[inferência]**: dedução minha, a conferir. A regra da tarefa me proibiu rodar gates, suítes e scripts que gravam. Quando digo «verde hoje por construção», li o comando e não o executei.
> Foco do meu domínio: **provas**. Para cada onda, pergunto qual controle vermelho→verde demonstra a cura e o que impede que ele seja vácuo.

## Verdict

**ADJUST**

- **W2: ADJUST.** O desenho é coerente, mas três provas faltam ou são vácuas. (i) Apagar arquivo de `flock` sem re-checar o inode pode quebrar a exclusão mútua, e nenhum controle do plano pega isso. (ii) O limiar «≤ 1% do estoque» mede carga, não cura. (iii) O invariante W2.5 fica vermelho para sempre se os escritores `agent_spawn` entrarem, e verde só porque os exclui se ficarem de fora. Além disso, o gatilho de reversão que o AMEND-4 herdaria do AMEND-3 nunca dispara.
- **W3: ADJUST, perto de REJECT na parte (b).** A sentinela de regressão não tem corpus no repositório. O Check de sucesso fica verde hoje pelo manifesto, sem nenhuma W3. Faltam a célula de assinatura forjada e a de «sem rede com versão nova».
- **W5c: ADJUST.** O re-teste «com os MESMOS testes» não tem os testes listados em lugar nenhum do repositório. O guarda que pegaria o array `superseded` esquecido é pulado no CI raso. O Check de sucesso fica verde hoje.
- **Transversal: ADJUST.** Os Checks de «Success criteria» das três ondas passam ANTES da cura. Cada Check precisa ser vermelho antes e verde depois, com a afirmação dentro do código de saída.

## Summary (≤ 3 bullets)

- O plano quer três coisas, cada uma com controle vermelho→verde: acabar com o acúmulo por PID e com o drain forçado lento (W2), aceitar versões novas do Codex por procedência conferida sozinha (W3) e adotar o Sonnet 5.5 (W5c).
- Ponto forte: reaproveita moldes de prova que já funcionaram aqui. São eles a barreira determinística sem `sleep` (`test_spool_drain_contended_skip.py`, «R-QA4»), a comparação por CONJUNTO EXATO do `--expected-reds` (redução conta como falha), a semente de teste honrada só com `CEO_PAIR_RAIL_TEST_MODE=1` (`check_pair_rail.py:439-447`) e o braço vermelho da W5c.4.
- Ponto fraco: vários controles são verdes por vácuo, e quatro premissas de prova não existem no código. O `FileLock` não re-checa o inode. A reconciliação de início de sessão não tem chamador em produção. O contador `truly_lost` nunca é incrementado. O corpus travado do ADR-111 não está no repositório.

## Risks

**R-QA1: W2, HIGH. Apagar arquivo de trava sem re-checar o inode quebra a exclusão mútua.**
- `FileLock.acquire` abre o caminho com `O_CREAT` e só depois faz `flock`, sem comparar `fstat(fd).st_ino` com `stat(path).st_ino` (`filelock.py:144`, `:149`) **[disco]**.
- A sequência que quebra tem quatro passos: A abre o fd (inode X); o GC obtém a trava sem bloquear, apaga o caminho e solta; A obtém `flock` em X; B abre o caminho e cria o inode Y. A partir daí, A e B «têm» a trava.
- O predicado da W2.4 («trava obtida sem bloquear») não fecha essa corrida. As travas são 2/3 do estoque.
- O `filelock.py` é canônico (oráculo = 1) **[disco]** e NÃO está na lista de paths da W2.
- Mitigação: ou o `filelock.py` entra no pacote com re-checagem de inode e nova tentativa depois do `flock`, ou o GC nunca apaga `.lock`, e o AMEND-4 declara o limiar sem as travas. Prova por intercalação determinística (Must-fix 1).

**R-QA2: transversal, HIGH. Os Checks de sucesso das três ondas são verdes por construção.**
- W2: o Check imprime a contagem (`python3 -c "…print(sum(…))"`) e o número de linhas de timeout (`… | wc -l`), sem comparar nenhum dos dois com limiar. Sai 0 com qualquer contagem («Success criteria», linha da W2) **[disco]**.
- W3: o `--verify-codex-pin` já dá `verified` hoje pelo manifesto do 0.156.1 (LEDGER, T0) **[disco]**. Como a W3.6 só roda depois do corte W7, o critério fica verde sem nenhuma W3.
- W5c: `generate-available-models.py --check && check-model-currency.py --expected-reds …` foi desenhado para passar no HEAD atual. Nenhum dos dois afirma a presença de `claude-sonnet-5-5` **[inferência; não executei]**.
- O mesmo vale para o Check da W5c.3.
- Mitigação: Must-fix 17.

**R-QA3: W2, HIGH. Duas pernas da prova de «sem perda» do AMEND-3 são inertes, e o gatilho de reversão nunca dispara.**
- `reconcile_journal_at_session_start` (`spool_writer.py:2467`) não tem chamador em produção. O grep em `.claude/` e `scripts/` acha só a definição, um teste (`test_audit_emit_async_flush.py:295`), cópias em sombras e documentos de plano. Em produção só há `drain_now()` (`audit_emit.py:2791`) e `install_exit_handlers()` (`:13344`) **[disco]**.
- `JournalReconciliation.truly_lost` (`spool_writer.py:136`) nunca é incrementado. É só lido para o dicionário (`:2562`) **[disco]**.
- Logo, o gatilho `revert_trigger_truly_lost_7d: 1` do AMEND-3 (frontmatter; §5) NUNCA dispara.
- O outro gatilho, «quebra de cadeia > 0,1% em 30 dias», mistura causas. Hoje a corrida do `audit_log.py` já o ultrapassa: 4 quebras em ~461 elos do log vivo ≈ 0,9% **[plano, risco 11]**.
- Duas consequências diretas. A L-10 da proposta e o path condicional `SessionStart.py` da W2 tratam uma reconciliação que não roda. Copiar o gatilho do AMEND-3 no AMEND-4 (pergunta W2-6) copia um gatilho vácuo.
- Mitigação: Must-fix 3.

**R-QA4: W2/W2-5, HIGH. O invariante W2.5 colide com a corrida conhecida do `agent_spawn` (condição 67).**
- `audit_log.py:1267` lê o elo anterior e `:1283` toma a trava **[disco]**, contra o docstring de `read_prev_hmac` («MUST be called WITH the audit-log FileLock held», `audit_hmac.py:482`) **[disco]**.
- Essa corrida NÃO é diagnóstico novo da S361. É a **condição 67 assinada da rc.1 da v1.4.0**: `CHANGELOG.md:835-838` (seção [1.4.0]) e o docstring de `test_two_writer_chain.py:13-16`, que promete o teste de barreira multiprocesso «to the rc.2 cure». A cura nunca landou **[disco]**.
- Um estresse com escritores `agent_spawn` fica vermelho até a cura. Um estresse sem eles é verde por excluir o único escritor com corrida.
- Mitigação: Must-fix 8.

**R-QA5: W3, HIGH. A sentinela (b), mitigação do risco 4, não tem com o que medir.**
- O ADR-111 aponta o corpus para `.claude/plans/PLAN-081/corpus/locked/`. `git ls-files | grep corpus/locked` = 0, e o diretório não existe **[disco]**.
- O `run-promotion-gate.py:96` aponta para o mesmo caminho ausente. Ele roda «through Codex MCP» (`:4`, `:229`), subcomando removido na 0.154.0, o achado A7 **[disco; plano]**.
- No re-pin 0156, o gatilho do ADR-111 §2 ficou «NÃO AVALIADO — ausência de medição» (`PLAN-193/codex-pin-0156/pin-0156-approved.md:201-204`) **[disco]**.
- Com N=15, uma única fixture vale 6,67 pp, acima do gatilho de 5 pp. Com revisor não determinístico, qualquer oscilação de uma fixture «dispara».
- Mitigação: Must-fix 12.

**R-QA6: W3, HIGH. Os controles W3.4 (a)–(d) não distinguem «assinatura conferida» de «digests coerentes», nem modelam o `npm i -g`.**
- A célula (b) «sem atestado ou de outro pacote» deixa passar um desenho que só compara digests do mesmo registro, a L-8 da proposta.
- A célula (c) «sem rede ⇒ rail segue no último verificado» é vácua se a fixture mantiver o payload antigo noutro caminho. O `npm i -g` sobrescreve o payload no MESMO caminho (L-9).
- Se o download de ~331 MB e o hash rodarem no caminho do hook (timeout de 210 s), um estouro de timeout deixa a escrita L3+ passar sem decisão. Isso é fail-OPEN por tempo **[inferência a partir do timeout do hook, lido no `settings.json`]**.
- Mitigação: Must-fix 10 e 11.

**R-QA7: W2, MEDIUM. O limiar «≤ 1% do medido hoje» compara um fluxo de um dia com um estoque saturado.**
- O estoque já ocupa ~76% do espaço de PIDs do macOS: 75.609 PIDs distintos, cada um com 3 artefatos **[medido]**. O crescimento observado é o de um estoque saturado. Depois da limpeza W2.6, o código SEM cura volta a crescer mais rápido por PID novo **[inferência]**.
- Contagem **[medido]**: 226.831 entradas às 23:55Z, contra 223.100 às ~20:08Z **[plano]**. São +3.731 em ~3h47m (≈ 985/h, com agentes em paralelo).
- 1% de 222.872 = 2.229. Num dia leve, o código sem cura fica abaixo da barra e o controle sai verde por vácuo. Num dia pesado, cruza em ~2 h. A barra mede carga.
- Mitigação: Must-fix 3.

**R-QA8: W2, MEDIUM. A relocação (W2.3) cria a mesma classe de «dois escritores, travas diferentes».**
- Enquanto conviverem as duas versões, código antigo trava `state/audit-pending.N.journal.lock` e código novo trava `state/<sub>/…` para o MESMO journal.
- É a classe já curada para o log (`spool_writer.py:418-421`: «two writers on one HMAC log under different locks = interleaved appends») **[disco]**.
- Mitigação: Must-fix 7.

**R-QA9: W5c, MEDIUM. O re-teste não está definido e pode comparar o 5.5 com ele mesmo.**
- O plano cita `DESIGN-OPUS55-S357.md` como precedente. O grep por A/B, cego, re-teste e PASS de modelo nesse arquivo não acha protocolo de re-teste de modelo: o documento trata da cerimônia **[disco]**.
- O instrumento da S357 vive fora do repositório (memória do Owner). Ele teve efeito teto (19/20 nos dois braços), logo só detecta regressão.
- O prefixo `claude-sonnet-5` admite o 5.5, e o CC troca de modelo em silêncio **[plano]**. Sem conferir o id SERVIDO de cada execução, o braço «Sonnet 5» pode ser o 5.5.
- Mitigação: Must-fix 14.

**R-QA10: W5c, MEDIUM. A entrega ao adopter tem guarda vácuo no CI.**
- `test_every_superseded_array_migrates_to_new` itera só os arrays DECLARADOS (`test_upgrade_settings_migration.py:299-309`) **[disco]**. Se a emenda esquecer o array de 8 ids, o teste passa.
- O único teste discriminante (derivação a partir das tags GA contra o literal vivo) faz `skipTest` sem tags (`test_derive_settings_baselines.py:664`, `:672`). O `validate.yml` não tem `fetch-depth` **[disco]**.
- `_tier_rank` dá -1 para `claude-sonnet-5-5` (`learn.py:535-563`). O oráculo de paridade que o comentário promete («W4.3 deliverable») não aparece nos testes do `tier_policy_cli` **[disco]**.
- Mitigação: Must-fix 15.

**R-QA11: W5c, MEDIUM. O teste do adapter codificaria uma afirmação não conferida.**
- Os dois HTTP 400 vêm da lane ANT-02, que a proposta não conferiu. Um teste unitário com HTTP simulado fica verde sobre a afirmação, verdadeira ou falsa.
- O `tool_choice` forçado com thinking sempre ligado também afeta o `claude-opus-5-5`, já em `_ALWAYS_ON_THINKING_MODELS` (`live/claude.py:135-142`, `:827-828`) **[disco]**. É uma classe, não o caso de um id.
- Mitigação: Must-fix 16.

**R-QA12: W2, LOW. Há asserção de tempo absoluto e Checks idênticos.**
- «Latência de saída igual à do dir vazio» sem tolerância vira flake se for para o CI. A casa já pagou três vezes por orçamento de tempo absoluto (CLAUDE.md §5).
- Os Checks de W2.2, W2.3 e W2.4 são o MESMO comando (`pytest test_spool_state_gc.py -q`). Um item pronto prova os três.
- Mitigação: medição de razão fora do gate unitário (Must-fix 2); seletores distintos (Nice-to-have 1).

## Must-fix (blocking)

Cada item traz a onda e o dono. «Builder» = quem monta o pacote da onda; «CEO» = decisão antes da rodada 2.

### W2

1. **[W2; dono: CEO decide, builder prova] Prova de exclusão mútua para qualquer `unlink` de caminho de trava.**
   - Opção (a): o `filelock.py` entra no pacote. Depois do `flock`, `fstat(fd).st_ino == stat(path).st_ino`; se diferir, nova tentativa.
   - Opção (b): o GC nunca apaga `.lock`, e o AMEND-4 declara o limiar sem as ~151 mil travas **[medido]**.
   - Controle obrigatório, intercalação determinística por barreira (molde `test_spool_drain_contended_skip.py`, sem `sleep`). A abre o fd e pára; o GC apaga; A obtém `flock`; B abre e obtém `flock`. Afirmar que B NÃO obtém a trava enquanto A a tem.
   - O controle fica VERMELHO com o `FileLock` atual mais um GC ingênuo plantado, e verde com a cura.
2. **[W2; dono: builder, antes de qualquer patch] Pré-registrar a W0.5 no LEDGER ANTES de rodar.**
   - Células 2^3: {saída sem spool próprio, com spool próprio} × {dir vazio, ~220 mil entradas} × {1 saída, ≥ 9 concorrentes}.
   - Métricas: p50/p95 da latência de saída e linhas `drain canonical lock timeout`.
   - Substrato: o interpretador que o `_python-hook.sh` usa, o SO e a versão do CC congelada (Q14).
   - Critério de vermelho: ≥ 1 timeout em {220k, ≥ 9} e 0 em {vazio, ≥ 9}.
   - Se o vermelho NÃO reproduzir, o LEDGER registra «controle vermelho não reproduzido», e a prova da W2 passa a ser só estrutural, declarada como tal.
   - Depois da cura, a mesma matriz com tolerância de RAZÃO pré-registrada (por exemplo, p95 cheio/vazio ≤ 1,2 em N ≥ 30). Isso é medição, nunca asserção de tempo no CI.
3. **[W2; dono: CEO, no texto do AMEND-4] Limiar como FLUXO com denominador, e gatilho de reversão que dispara.**
   - Trocar «≤ 1% do estoque» por «artefatos de PID morto por PID emissor distinto na janela». O denominador sai dos `pid` distintos que o spool carimba nas entradas do log canônico na janela.
   - Acrescentar um teto absoluto ligado aos PIDs vivos no instante da contagem.
   - O denominador zero reprova: sem carga, nada fica provado.
   - O gatilho de reversão precisa de três coisas. Instrumento nomeado, com comando. Classe atribuível: separa a corrida do `agent_spawn`. Controle POSITIVO: perda sintética numa árvore descartável faz o gatilho disparar.
   - NÃO herdar o `truly_lost` do AMEND-3, que nunca é incrementado (R-QA3).
4. **[W2; dono: builder] Invariante por CONJUNTO, não por contagem.**
   - Todo `record_id` emitido aparece exatamente UMA vez no log canônico. «Contagem igual antes e depois» esconde perda somada a duplicata.
   - `verify_chain()` íntegro sobre uma cadeia de ≥ N elos. Cadeia vazia ou curta é verde por vácuo.
   - Escritores mistos.
   - Controle vermelho por mutantes plantados (3 a 5, à mão): (a) o GC apaga journal com conteúdo; (b) o caminho rápido pula a varredura de órfãos de quem TEM spool; (c) o GC ignora PID vivo. Cada mutante tem de reprovar o teste.
5. **[W2; dono: builder] Células do caminho rápido (W2.2).** Cinco células:
   - (a) Sem spool próprio, com envelopes de journal no buffer: o `_flush_journal_buffer` ainda roda na saída.
   - (b) `.draining` próprio deixado por exceção no meio do drain: a saída AINDA força o drain. Usar sinalizador em processo; listar o dir não serve, porque é o que se quer evitar (W2-2).
   - (c) O caminho rápido mora no `_atexit_drain`, não no `drain_now(force=True)`: um teste falha se for movido.
   - (d) Zero chamadas a `os.listdir` ou `os.scandir` no caminho rápido, contadas por um envoltório no lugar de tempo.
   - (e) O teste 4 de `test_spool_drain_contended_skip.py:220-231` fica intacto: drain forçado com spool próprio sob trava externa ⇒ `ok=False` + breadcrumb.
   - E mais: o órfão de PID morto é recuperado pelo drain OPORTUNISTA (`force=False`) do próximo emissor. O teste 3 atual usa `force=True` (`:213-217`).
6. **[W2; dono: CEO fixa a tabela, builder a codifica] Tabela de predicado do GC pré-registrada, uma ação esperada por célula.**
   - Dimensões: tamanho {0, >0}, PID {morto, vivo entre travas, reusado}, trava {livre, presa}, família com conteúdo {sim, não}, mtime {recente, > 10 min}, tipo {arquivo comum, symlink, hardlink}.
   - Quase-acertos tirados do censo VIVO **[medido]**: travas de 0 byte de OUTROS módulos no mesmo dir (`ceo-overhead-window*.json.lock`, `subagent-lifecycle.json.lock`, `output-scan-dedup.lock`, `ceo-boot-tasks-emitted.json.lock`), `statusline-snapshot.json.tmp.N`, o journal agregado (`audit-pending.journal`, `.aggregation.lock`, `spool_writer.py:455-464`) e `*.compact.tmp`.
   - Os 213 journals com conteúdo de hoje **[medido]** entram como controle: ficam intactos, mesmo hash.
   - O predicado da W2.4 (dentro do hook) não tem «PID morto» nem «mtime > 10 min», que a W2.6 tem. Justificar por célula ou alinhar.
7. **[W2; dono: builder] Relocação com convivência de versões (W2.3).**
   - Teste com o módulo antigo (bytes do HEAD, num subprocesso) e o novo travando o journal do MESMO PID: prova que serializam.
   - Alternativa: a relocação vale só para PIDs novos, com chave de versão.
   - Junto, a leitura dupla de layout por um número declarado de versões e o critério de remoção dela (L-4).
8. **[W2/W2-5; dono: CEO decide a vaga, builder prova] A corrida do `agent_spawn` (condição 67).**
   - Opção (a): a cura do `audit_log.py` landa ANTES da W2 ou no pacote dela, e o estresse W2.5 inclui escritores `agent_spawn` e `audit_emit` misturados.
   - Opção (b): o estresse exclui o `agent_spawn` e o AMEND-4 declara isso.
   - Controle da cura: envoltório sobre `read_prev_hmac` que sinaliza e espera (barreira com limite menor que os 2,5 s da trava). É VERMELHO no HEAD (`audit_log.py:1267` antes de `:1283`) e VERDE depois.
   - Mais um censo AST: toda chamada a `read_prev_hmac()` fora de teste fica lexicamente dentro de `with FileLock(`, com módulo sintético como controle positivo (curar a classe).
   - O pacote aposenta a condição 67 no `CHANGELOG.md`, que colide com a W7 e com o leque de ADR, e atualiza o docstring do `test_two_writer_chain.py`.

### W3

9. **[W3; dono: builder] O Check de sucesso afirma a ORIGEM da verificação.**
   - O resultado do `verify_codex_payload` ganha um campo de fonte (manifesto ou registro automático). O Check exige `fonte = registro automático` para uma versão FORA do manifesto.
   - Isso roda em árvore descartável com registro sintético, ou na primeira rodada real da W3.6.
   - Célula de corte: o validador do veredito de release continua INVALID para versão só auto-pinada (W3-7), e o material assinado declara isso.
10. **[W3; dono: builder] Fixtures sem rede e sem binário real.**
    - Guarda de socket no módulo de teste inteiro (`connect` levanta), com controle positivo de que dispara. O molde é o oráculo de rede em tempo de execução do `check-model-currency.py` (`:38-42`).
    - Registro falso só sob `CEO_PAIR_RAIL_TEST_MODE=1`, com o controle negativo «semente inerte no caminho vivo». O molde é `test_fixture_ignored_on_live_path_without_test_mode` (`test_check_pair_rail_payload_pin.py:465`).
    - Tarball SINTÉTICO de KB, gerado com `tarfile` no tmp, com `sha512` = `dist.integrity` sintético = `subject` do atestado sintético.
    - UM atestado real de KB (0.156.1 e 0.160.0), capturado com data, só para o formato do parser.
    - Célula de resposta acima do teto de bytes ⇒ recusa, com limpeza confinada.
    - A fixture modela o `npm i -g` sobrescrevendo o payload no MESMO caminho (L-9). Com versão nova recusada, o hook BLOQUEIA. «Segue na última verificada» só se existir cópia retida e for ela o caminho executado.
11. **[W3; dono: CEO fixa a tabela no AMEND-1, builder a codifica] Matriz de recusa (W3-5) pré-registrada.**
    - Células: {rede ok, falha} × {atestado válido, ausente, de outro pacote, com assinatura ou identidade de build inválida e digests coerentes} × {versão já registrada, nova}, com status e código de saída (0/1/3) por célula.
    - Duas obrigatórias. «Versão nova + sem rede» ⇒ 1 (fail-CLOSED), nunca 3. «Versão já registrada + sem rede» ⇒ 0, sem rede.
    - Se a stdlib não verificar a assinatura (L-8), a célula da assinatura forjada fica ACEITA e é DECLARADA no AMEND-1 como «vínculo de digests do mesmo registro», nunca escondida.
    - Caminho do hook limitado: para versão não registrada, `verify_codex_payload` responde fail-closed SEM rede e SEM download, provado pelo mesmo oráculo de rede. A conferência pesada roda fora do hook de 210 s.
12. **[W3; dono: CEO] Sentinela: medir a linha de base ou declarar.**
    - Antes de usar a sentinela como mitigação do risco 4, cinco passos: definir o path do corpus com sha; medir a linha de base no trio pinado atual (0.156.1 + modelo e esforço fixos) com m ≥ 3 repetições; registrar a variância com o MESMO binário; fixar a regra de alarme ACIMA dessa variância; fazer as rodadas pagas obedecerem à Q2.
    - Se a cota não couber, o material assinado declara «sentinela não implementada» e o risco 4 fica sem essa mitigação.
13. **[W3; dono: builder] Sonda (W3-8) e argv fixo testados com um `codex` stub no PATH temporário.**
    - Células: {`exec`, `review`, `app-server`} × {presente, ausente}, mais as FLAGS que o argv usa (`--model`, o ajuste de esforço, `--ignore-user-config`) × {presente, ausente}.
    - Controle vermelho que reencena o A7: subcomando removido ⇒ versão recusada.
    - Ordem: a sonda só executa o binário DEPOIS da procedência conferida. Um espião afirma zero execuções de payload não verificado.
    - Argv: um stub captura o argv. É VERMELHO hoje (`DEFAULT_MODEL = None`, `codex_cli_shape.py:110`; `--model` só com valor explícito, `:351`) e VERDE com modelo, esforço e `--ignore-user-config`.
    - Afirmar os campos versão, modelo e esforço no registro do veredito (desenho (d)).

### W5c

14. **[W5c; dono: CEO redige, Owner vê antes da chamada paga] Pré-registro do re-teste no LEDGER (W5c-5).**
    - Instrumento nomeado, com sha. O da S357 está fora do repositório: copiar para dentro ou pinar o sha.
    - Braços: `claude-sonnet-5` EXATO × `claude-sonnet-5-5`, mesmo esforço, `claude -p` hermético. Também n, a métrica (defeitos achados, correção cega), δ de não-inferioridade e a regra de custo.
    - **Validade:** execução com id SERVIDO diferente do pedido, ou com sha do instrumento ou versão do CC diferentes, é INVÁLIDA, não FAIL.
    - Células 2^3 enumeradas ANTES: {defeitos: não-inferior, inferior por δ} × {custo por revisão ≤ 1,2×, > 1,2× o Sonnet 5} × {os 400 da ANT-02 confirmados, não confirmados}, com a ação de cada célula (tabela abaixo).
    - FAIL ⇒ a W5c pára antes do SIGN, e o Owner decide por múltipla escolha. O debate não desfaz o «Adotar».
    - Declarar o efeito teto da S357 (19/20): o instrumento detecta regressão, não melhora.
15. **[W5c; dono: builder] Entrega ao adopter (W5c-6), em quatro células.**
    - (i) array EXATO de 8 ids da 1.4.2 (`upgrade.sh:198`, hoje `new`) ⇒ MIGRATE para 9;
    - (ii) array customizado ⇒ preservado, com WARN nomeado;
    - (iii) array de 7 ids ⇒ MIGRATE para 9;
    - (iv) segunda execução ⇒ nada muda.
    - Mais duas exigências. A bateria do LAND roda `test_derive_settings_baselines.py` SEM pular e conta SKIP como falha no conjunto exato, ou o CI busca as tags.
    - E um guarda de classe no `_tier_rank`: todo id do bloco `AVAILABLE_MODELS_WORKING_SET` do ADR-149 tem posto ≥ 0, com as direções `sonnet-5→sonnet-5-5` = promote, `sonnet-5-5→opus-4-8` = promote e `sonnet-5-5→sonnet-4-6` = demote. Exige renumerar: não há inteiro entre 3 e 4.
16. **[W5c; dono: builder, na W5.0 ou W5c.1] As afirmações do adapter primeiro, o teste depois.**
    - Duas sondas pagas baratas e pré-registradas no `claude-sonnet-5-5`: thinking `disabled` e `tool_choice` forçado com thinking ligado. A resposta (400 ou 200) decide o patch. O teste unitário codifica a resposta MEDIDA, com data e substrato.
    - A proteção de `tool_choice` forçado, se entrar, vale para TODO `_ALWAYS_ON_THINKING_MODELS`, o `claude-opus-5-5` incluído, em teste parametrizado.

### Transversal

17. **[transversal; dono: CEO, no texto do plano] Todo Check de sucesso e de item fica vermelho antes e verde depois, com a afirmação no código de saída.**
    - W2: sai ≠ 0 se a contagem passar do limiar, se houver timeout na janela, ou se o denominador for 0.
    - W3: Must-fix 9.
    - W5c: afirma positivamente que `claude-sonnet-5-5` está no bloco do ADR-149, no `availableModels`, no `cost-table.yaml` e na entrada de re-teste do LEDGER.
    - O braço vermelho da W5c.4 afirma a DIFERENÇA EXATA (`+claude-sonnet-5-5` na superfície S1), não só `exit 1`. A W3b também mexe no conjunto de vermelhos e pode avermelhar por outro motivo.
    - Custo: ~30-50k tokens, dentro da sessão de emendas do plano.

## Nice-to-have (advisory)

1. **[W2]** Seletores `-k` distintos por item (`fast_path`, `relocation`, `gc`, `invariant`), com guarda de seletor no molde `SupersededSelectorTest`. Um `-k` que casa zero testes já sai 5 no pytest, mas um teste-placeholder casaria.
2. **[W2/W2.6]** Script da limpeza única, em três partes:
   - simulação com contagem por célula da tabela do Must-fix 6, gravada no LEDGER;
   - manifesto de hash dos journals com conteúdo antes e depois (213 hoje **[medido]**), em que qualquer diferença reprova;
   - re-contagem pelo MESMO método do critério de sucesso.
   - Pergunta: o state dir é por projeto desde o PLAN-182 W1, então exigir «todas as sessões do Claude fechadas» (até as de outros repositórios) é necessário? Reduzir a pré-condição às sessões DESTE projeto destrava a W2.6 e a linha de base.
3. **[W3]** Na 1.ª rodada real da W3.6, capturar uma amostra pequena e redigida da saída JSONL da versão nova como fixture de CONTRATO do parser: teste de forma por versão aceita.
4. **[W2]** O GC grava o que apagou como contagem, e um teste afirma contagem registrada = arquivos de fato apagados (W2-7). Um breadcrumb que mente sobre o que apagou é pior que nenhum.
5. **[transversal]** Toda entrada de medição no LEDGER traz a versão do CC (congelada pela Q14), o `python3` dos hooks e o sha do instrumento. «Claim MEDIDA precisa de data e substrato.»

## Unseen by the original plan

1. **A reconciliação de início de sessão não roda em produção, e o `truly_lost` nunca sobe** (`spool_writer.py:2467`, `:136`, `:2562`; nenhum chamador fora de teste) **[disco]**.
   - A prova de «sem perda» do AMEND-3 e o gatilho de reversão dependem disso.
   - A L-10 da proposta e o path condicional `SessionStart.py` da W2 pressupõem uma reconciliação que não existe no caminho vivo.
   - Se alguém a ligar, ela abre CADA journal de PID morto: ~75 mil `open` sob o timeout de 5 s do `SessionStart.py` **[medido + disco]**. Também vira célula da W0.5.
2. **A corrida do `agent_spawn` é a condição 67 assinada da v1.4.0** (`CHANGELOG.md:835-838`, `test_two_writer_chain.py:13-16`), não diagnóstico novo. A cura aposenta um resíduo PÚBLICO e precisa de linha no CHANGELOG.
3. **O `FileLock` não re-checa o inode** (`filelock.py:144-149`), e o arquivo é canônico, fora da lista de paths da W2.
4. **O corpus travado do ADR-111 não está no repositório.** O instrumento que o usaria (`run-promotion-gate.py`) depende do Codex MCP, removido na 0.154.0.
5. **Os Checks de «Success criteria» da W2, da W3 e da W5c são verdes por construção** (R-QA2).
6. **Censo vivo** **[medido, 23:55Z]**: 226.831 entradas, das quais 75.587 travas de spool, 75.609 travas de journal e 75.609 journals, 75.396 deles com 0 byte. São 213 journals com conteúdo e 24 residentes de outros módulos, 10 deles com 0 byte.
7. **O teste vivo de derivação do `superseded` é pulado no CI raso** (`validate.yml` sem `fetch-depth`), e o `_tier_rank` não tem oráculo de paridade com o ADR-149.
8. **O caminho do hook do rail com rede e download é fail-OPEN por timeout.** O plano trata «sem rede» como recusa, mas não trata «lento demais».

## What I would NOT change

- **Comparação por CONJUNTO EXATO** do `--expected-reds` e do gate noturno de ownership: redução sem explicação reprova. É o antídoto certo contra verde por vácuo.
- **O braço vermelho da W5c.4** (linha de preço sem emenda ⇒ achado novo): é controle não vácuo por desenho. Só exijo a diferença exata (Must-fix 17).
- **A barreira determinística sem `sleep`** do `test_spool_drain_contended_skip.py`: reusar nas provas da W2 e da cura da condição 67.
- **A classificação do ADR-182**, em que manifesto malformado = `mismatch` (fail-closed) (`check_pair_rail.py:666-673`), com a semente de teste inerte fora do modo de teste. O pin automático NÃO pode diluir isso.
- **«Mudar de lugar não é curar»**: contar o state dir INTEIRO, inclusive o subdiretório novo.
- **O predicado conservador da W2.6** (simulação por padrão; journal com conteúdo NUNCA; re-exame antes de apagar).
- **Codex no 0.156.1 até a W3 e o fim do corte**, e **CC congelado por onda** (Q14): instrumento intacto durante as medições.
- **Medições em árvore descartável** com limpeza confinada por `shutil.rmtree` e piso de `df`.

## Respostas às perguntas do meu domínio (para o `consensus.md`)

- **W2-1.** Do ponto de vista da prova, a peça mais fácil de provar é o DONO apagar a própria família na saída, se o spool foi totalmente drenado e o journal ficou com 0 byte.
  - Com o dono vivo, quem abre os arquivos dele é praticamente só ele mesmo. Os drainers só tocam o próprio spool ou spools de PID morto (`spool_writer.py:1319-1344`). Exceção: o `.draining` deixado por exceção, coberto pelo sinalizador do Must-fix 5(b).
  - Um GC externo concorre com abridores desconhecidos e depende do Must-fix 1. Recomendo: o dono limpa na saída (a cura da origem, L-5), mais o GC só para o estoque legado (W2.6).
  - A relocação fica opcional.
- **W2-2.** Hoje o órfão é recuperado por qualquer drain de quem emite: o oportunista varre spools de PID morto e `.draining.*`, `:1277-1344`. A reconciliação de sessão NÃO roda (Unseen 1). O teste do Must-fix 5 prova a recuperação pelo drain oportunista.
- **W2-5.** Veja o Must-fix 8. Sem a cura, o invariante W2.5 não pode incluir `agent_spawn`.
- **W2-6.** Arquivo de emenda próprio, sim: a premissa «anomalous» muda. O limiar é FLUXO com denominador; o gatilho, fireável, com controle positivo (Must-fix 3).
- **W3-5.** «Sem rede» e «sem atestado» com versão NOVA ⇒ braço fail-CLOSED (saída 1). INFRA (saída 3) só para o que já era INFRA no ADR-182 §2 (manifesto ou launcher ausente). Veja a tabela abaixo.
- **W3-8.** A sonda deve ser automática, DEPOIS da procedência e ANTES do registro. Ela bloqueia o registro da versão, não o rail na versão já verificada (Must-fix 13).
- **W3-9.** A AMEND-1 não pode «preservar» um gatilho que nunca foi avaliado. Ou a sentinela mede, com linha de base e variância, ou o gatilho do ADR-111 §2 fica declarado como não avaliável (Must-fix 12).
- **W5c-5 / W5c-6.** Must-fix 14 e 15.

### Células pré-registradas que proponho (o CEO pode ajustar os valores, não remover células)

**W0.5** (2^3; vermelho esperado no HEAD):

| exit | dir | concorrência | HEAD esperado | cura esperada |
|---|---|---|---|---|
| sem spool | vazio | 1 | 0 timeout | 0 |
| sem spool | vazio | ≥ 9 | 0 timeout | 0 |
| sem spool | ~220k | 1 | latência alta, 0 timeout | razão ≈ 1 |
| sem spool | ~220k | ≥ 9 | ≥ 1 timeout (vermelho) | 0 |
| com spool | vazio | 1 | 0 | 0 |
| com spool | vazio | ≥ 9 | 0 | 0 |
| com spool | ~220k | 1 | latência alta | razão ≈ 1 só com relocação ou GC |
| com spool | ~220k | ≥ 9 | ≥ 1 timeout | 0 só com relocação ou GC (o caminho rápido sozinho NÃO cura) |

**W3-5** (resumo; a tabela completa entra no AMEND-1):

| rede | atestado | versão | status / saída |
|---|---|---|---|
| ok | válido | nova | verified / 0, registra |
| ok | ausente ou de outro pacote | nova | mismatch / 1 |
| ok | assinatura ou identidade inválida, digests coerentes | nova | mismatch / 1 **se** houver verificação criptográfica; senão ACEITA e DECLARADA |
| falha | — | nova | mismatch / 1 (nunca 3) |
| falha | — | já registrada | verified / 0, sem rede |
| qualquer | — | payload no disco ≠ sha registrado | mismatch / 1 |

**W5c-5** (2^3; a validade vem antes das células):

| defeitos (δ) | custo/revisão | 400 da ANT-02 | ação |
|---|---|---|---|
| não-inferior | ≤ 1,2× | confirmados | PASS; o adapter ganha a proteção |
| não-inferior | ≤ 1,2× | não confirmados | PASS; adapter sem mudança, a ANT-02 é registrada como refutada |
| não-inferior | > 1,2× | qualquer | PASS com custo declarado no material assinado |
| inferior | qualquer | qualquer | FAIL ⇒ pára antes do SIGN e escala ao Owner |
| (execução com id servido ≠ pedido, ou instrumento/CC diferente) | — | — | INVÁLIDA, refazer, não conta |

## Esforço (ADR-081: tokens e sessões; nenhum prazo humano aqui é espera externa)

| Item | Esforço |
|---|---|
| Must-fix 1 a 7 (provas da W2) | ~250-400k tokens além do orçamento da W2 (0,8-1,5 M **[plano]**), na mesma sessão ou em +1 |
| Must-fix 8 (cura do `audit_log.py` + barreira + censo AST) | 150-300k **[plano]** + ~50k do censo |
| W0.5 pré-registrada e rodada | ~100-200k tokens, sem cota paga, numa fração de sessão |
| Must-fix 9 a 13 (fixtures e matrizes da W3) | ~300-500k tokens |
| Sentinela | cota do Codex: m × 15 revisões, sob o freio Q2; ~100k tokens de harness |
| Must-fix 14 (pré-registro) | ~50-100k |
| Re-teste pago | ordem de 1-2 M tokens, 1 sessão. Referência: S357, 40 revisões, mediana de 22,7k tokens de saída por revisão no Opus 5.5 xhigh (memória do Owner). O Sonnet tende a custar menos por revisão **[inferência]** |
| Must-fix 15 a 17 | ~100-150k |

Nenhuma fonte externa trouxe «semanas de trabalho»; não houve conversão a fazer.
