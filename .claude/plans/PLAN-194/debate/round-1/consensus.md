---
plan: PLAN-194
round: 1
rounds_synthesized: [round-1]
critics: [Critic-A, Critic-B, Critic-C]
agents_considered: [Critic-A, Critic-B, Critic-C]
verdicts: [ADJUST, ADJUST, ADJUST]
vetoes: "Critic-B — LEVANTADO em W2 (integridade do audit-log, ADR-052; veto_floor herdado do ADR-055-AMEND-3) e em W3 (cadeia de suprimento, T-8); RETIRADO em W5c, condicionado a MF-W5c-1 e MF-W5c-2 na emenda 4 do ADR-149"
wave_verdicts:
  W2: RUN-ANOTHER-ROUND
  W3: RUN-ANOTHER-ROUND
  W5c: PROCEED
round_verdict: RUN-ANOTHER-ROUND
design_coherent:
  W2: false
  W3: false
  W5c: true
consensus_adjustments: 48
decisions_revised_in_plan: "pendente — esta síntese NÃO edita o plano; o CEO aplica a lista «Plan adjustments» antes da rodada 2"
synthesized_at: 2026-10-02T00:26:38Z
synthesized_by: CEO (síntese delegada, S361)
synthesized_from: "texto anonimizado das três críticas (cópias fora do repositório, no scratchpad da sessão); proposta da rodada 1; plano no HEAD 6a9abb10 com as emendas não commitadas da S361. Limitações declaradas: (1) o mapa de anonimização foi lido só para saber o estado do VETO, mas ele também lista os arquétipos; (2) o texto não commitado do risco 11 do plano nomeia o arquétipo de um achado. Cada decisão abaixo se apoia em fato conferido no disco, não em quem o afirmou."
---

# Consenso — PLAN-194, debate L3 único, rodada 1 (W2, W3, W5c)

> **O que este veredito certifica.** `design-coherent` (DEBATE-SCHEMA §13.1) certifica só a coerência
> interna do desenho entre perspectivas forçadas do MESMO modelo. Não autoriza publicar. Publicar
> continua exigindo a cascata V0 → V1 → V2 (rail do Codex) → V3 (GPG do Owner).
>
> **Repositório público.** Classes de defeito e ids de lane apenas; nenhum caminho da pasta privada do
> Owner; nenhuma receita de contorno de guarda.

## 0. Verificação das afirmações (antes de consolidar)

O sintetizador conferiu no disco (HEAD `6a9abb10`) as afirmações que sustentam as decisões. Todas as
listadas abaixo conferem; duas premissas de crítico NÃO conferem e estão marcadas.

| afirmação | onde | resultado |
|---|---|---|
| `FileLock.acquire` abre com `O_CREAT` e faz `flock` sem comparar inode | `.claude/hooks/_lib/filelock.py:144-149`; `grep st_ino\|fstat` = 0 | confere |
| `reconcile_journal_at_session_start` sem chamador em produção | só a definição (`spool_writer.py:2467`), um teste (`test_audit_emit_async_flush.py`) e um script histórico de cerimônia | confere |
| `truly_lost` nunca é incrementado | só `spool_writer.py:136` (default) e `:2562` (leitura) | confere ⇒ o gatilho `revert_trigger_truly_lost_7d` do AMEND-3 nunca dispara |
| O `SessionStart` drena à força | `SessionStart.py` não tem `drain` nem `spool`; os `drain_now(force=True)` vivos são `:2581` (atexit) e `:2610` (sinal); `:2539` está dentro da reconciliação morta | **NÃO confere** (premissa de MF-W2-5 e do frontmatter do AMEND-3) |
| A varredura de órfãos roda também no drain oportunista | `_phase2_sweep_and_rename` dentro do `with FileLock(..., timeout=canonical_timeout)` de `drain_now` (`spool_writer.py:2366-2371`) | confere ⇒ a perna 3 é o drain do próximo emissor que ganhar a trava |
| A compactação reescreve o journal com 0 byte e nunca o remove; o flush reabre pelo caminho, sob a trava do journal, com `O_CREAT` | `spool_writer.py:2276-2297`; `:956-962` | confere |
| Outro processo pode tomar a trava do journal de um PID VIVO | fase 1 recupera `.draining.*` «owned by a dead PID (or even a live one)» (`:1277-1316`) e a compactação do PID drenado trava o journal dele (`:2276`) | confere ⇒ **NÃO confere** a premissa «enquanto o PID vive, nenhum drainer toca os arquivos dele» |
| Abridores dos caminhos de trava por PID | 4 sítios: `:958` (flush), `:1002` (append), `:1374` (rename da fase 2), `:2276` (compactação) | confere (censo pequeno, mecanizável) |
| Corrida do `agent_spawn` = condição 67 assinada da v1.4.0-rc.1 | `audit_log.py:1265-1276` (HMAC fora da trava) e `:1283` (trava); `CHANGELOG.md:835-838`; `test_two_writer_chain.py:13-16` | confere |
| INFRA no hook = rail some em silêncio (allow) | `check_pair_rail.py:783-786` (`None`) e `:1512-1524` (`CodexUnavailable` ⇒ `systemMessage` «fail-OPEN advisory») | confere |
| Ação fora de `_KNOWN_ACTIONS` vira breadcrumb | `audit_emit.py:5260-5262`; `pair_rail_codex_pin_mismatch` tem 0 ocorrências no `audit_emit.py` (`check_pair_rail.py:1204`) | confere |
| Timeout do hook do rail; hook `Stop` que executa `codex` | `.claude/settings.json:285` (210 s); `:636-645` (`codex_review_user_code.py`, auto por opt-in) | confere |
| Rota 2 do runner do re-pass (npx em cache próprio) | `PLAN-193/repass-ga/run-ga-repass.sh:242-306` e `repass-rc1/run-rc1-repass.sh:214-251`: rota 1 só se o payload global confere E a versão é a pinada; rota 2 morre se a versão do npx ≠ manifesto, verifica pelo mesmo oráculo e põe um shim no PATH | confere |
| O corte já rodou pela rota 2 | `PLAN-192/repass-ga/PROVENANCE-ga.md:6` «rota do codex: npx (cache proprio)», 0.155.0 (GA 1.4.1) | confere |
| O envelope lê o Codex da PROVENANCE, nunca da máquina | `PLAN-193/gen-envelope-ga.py:213-243`; `OWNER-GA-CUT.sh:1679`, `OWNER-RC1-CUT.sh:1218`; nenhum dos dois chama `pair-rail-gate.sh` | confere |
| `parse_semver` do validador casa por prefixo | `.github/scripts/validate-pair-rail-verdict.py:355-359` (`re.match`) | confere |
| Corpus travado do ADR-111 ausente | `git ls-files \| grep -c corpus/locked` = 0; `.claude/plans/PLAN-081/corpus` não existe | confere |
| Precedente wave-opus55 com 76 paths | `PLAN-193/wave-opus55/WOPUS55.patch`: 76 `diff --git`, inclusive `scripts/install.sh`, o baseline do censo do instalador, `audit_log.py`, `settings.user.json`, `_lib/test_isolation.py`, `upgrade.sh`, `validate-governance.sh` e o manifesto ADR-192 | confere |
| Guarda da migração do adopter pula em clone raso | `test_derive_settings_baselines.py:664`, `:672` (`skipTest`); `validate.yml` sem `fetch-depth`; `derive-settings-baselines` ausente de `.github/` e do `validate-governance.sh` | confere |
| `_tier_rank` sem o Sonnet 5.5 | `tier_policy_cli/learn.py:535-563`: `claude-sonnet-5` = 3, `claude-opus-4-8` = 4 ⇒ `claude-sonnet-5-5` = -1, e não há inteiro livre entre 3 e 4 | confere |

**Medições do sintetizador (só leitura).**

- **Cadência do npm**, 2026-10-02T00:20Z, `npm view @openai/codex time` com cache próprio descartável:
  23 estáveis desde 2026-08-25, 22 intervalos, **mediana de 22,0 h**, 13 de 22 abaixo de 24 h e 16 de 22
  abaixo de 48 h. Confirma a medição de um crítico (que deu mediana de 22,5 h). `latest` = 0.160.0
  (publicada 2026-10-01T20:26:19Z); `alpha` = 0.162.0-alpha.1. As dist-tags trazem
  `release-0.159.0-alpha.12.1-alpha-darwin-arm64` → `0.159.0-alpha.12.1-darwin-arm64`, a armadilha de
  gramática apontada na crítica: alpha com sufixo de plataforma.
- **Erros do drain**, 2026-10-02T00:25Z: o `audit-log.errors` tem **30.258** linhas, **30.068** delas
  `drain canonical lock timeout`. Eram 25.589 linhas às ~20:08Z (plano), ou seja, cerca de 1.100 por hora.
  Os críticos contaram 226.831 e 226.811 entradas no state dir às 23:55Z e às 00:00Z.

## 1. Vereditos por onda e estado do VETO

| onda | veredito da rodada | VETO (Critic-B) | por quê |
|---|---|---|---|
| **W2** | **RUN-ANOTHER-ROUND** | LEVANTADO | O desenho muda de forma: a W2.3 sai, entra o prazo na saída e vale a regra de travas da §2(b). O ADR-055-AMEND-4 ainda não existe nem em rascunho. A cura do `agent_spawn` é pré-condição e espera a vaga, que o Owner decide. |
| **W3** | **RUN-ANOTHER-ROUND** | LEVANTADO | Faltam a matriz de recusa no ADR-182-AMEND-1 (rascunho PROPOSED) e o verificador fora do hook. Três decisões condicionais do Owner (§«Decisões pendentes») entram por escrito no AMEND-1. |
| **W5c** | **PROCEED** (`design-coherent`) | RETIRADO, com condições | Os críticos não divergem: formato da Amendment 2, pacote derivado por script, cláusula `superseded`. Os must-fix são pré-requisitos de execução e valem para a onda (Q3: «os must-fix valem por onda»). Ver ajustes 35 a 40. |

**Veredito da rodada: RUN-ANOTHER-ROUND**, com a rodada 2 restrita à W2 e à W3. A W5c sai do portão do
debate, mas a posição na fila não muda (depois da W2, Q7/OQ-11; primeira a sair se a cota apertar). A
rodada 2 só reabre a W5c se um crítico mostrar que os ajustes 35 a 40 foram aplicados de forma diferente
do texto aqui.

## 2. Divergências resolvidas (regra: o portador de VETO prevalece no domínio do VETO, salvo evidência no disco que o refute)

### (a) Carência para aceitar versão nova do Codex — W3-4

- **Posições.** Critic-B (VETO): ≥ 48 h contadas da publicação NO REGISTRO, em constante canônica; `latest`
  é necessária e nunca prova; `deprecated` recusada; nunca abaixo do piso do manifesto. Critic-C: ≥ 24 h,
  escolhendo a estável mais nova com idade ≥ carência e ≤ `latest`, e nunca «== `latest`», porque pela
  cadência medida «== latest + 48 h» deixaria o pin parado em ~73% dos dias.
- **Evidência.** A cadência foi re-medida e confere (§0). Ela prova o CUSTO da combinação «== `latest`»,
  mas não prova que 48 h deixa de proteger: ninguém mediu a latência de detecção de uma versão maliciosa
  com procedência válida, que é o risco que a carência cobre. Nada no disco refuta o Critic-B.
- **Decisão.** **Carência de 48 h** (Critic-B prevalece), contada no relógio do registro, em constante
  canônica com teste. A **regra de escolha é a do Critic-C**: a candidata é a estável mais nova com idade
  ≥ 48 h, ≤ `latest`, sem `deprecated` e ≥ piso do manifesto. Nunca «== `latest`». A `latest` fica como teto:
  o «necessária» do Critic-B passa a valer como «a `latest` atual é estável e ≥ candidata».
- **Efeito.** Sempre existe versão elegível, e o pin anda uns 2 dias atrás da `latest`, sem cerimônia. Em
  2026-10-02T00:20Z: 0.160.0 (~4 h) e 0.159.3 (~25 h) ainda não eram elegíveis; a 0.159.2 (~48,3 h) era.
- **Gramática estrita (MF-W3-4).** Base estável `X.Y.Z` mais o sufixo EXATO do triple da plataforma.
  Qualquer outro pré-release é recusado.
- A espera de 48 h é `external_wait` (relógio do npm).

### (b) Apagar arquivos de trava (`*.lock`) — W2-1, W2-4

- **Posições.** Critic-B (VETO): nenhum hook apaga `*.lock`, salvo se TODOS os adquirentes passarem a
  re-checar o inode (`filelock.py`, kernel). A cura vai na origem. Critic-A: ou o `filelock.py` ganha a
  re-checagem no pacote, ou o GC nunca apaga `.lock`; nos dois casos, com controle de intercalação
  determinística. Critic-C: o dono apaga o próprio journal e as DUAS travas como último passo da saída, e
  o GC de PID morto vai de carona no drain, com o reuso de PID declarado como resíduo.
- **Evidência.** O `FileLock` não re-checa o inode (§0). A premissa do Critic-C, «nenhum drainer toca os
  arquivos de um PID vivo», é FALSA para o caso `.draining.*` (§0). Nada refuta o Critic-B; o disco o
  reforça.
- **Decisão (o Critic-B prevalece).**
  - Na W2, **nenhum hook faz `unlink` de caminho `*.lock`**.
  - **Journals:** cura na origem. O journal vazio é removido sob a PRÓPRIA trava do journal, pela
    compactação no lugar de reescrever 0 byte, ou pelo dono na saída quando o spool está todo drenado, o
    journal tem 0 byte e o buffer está vazio. Isso é seguro para o ARQUIVO do journal, porque o flush
    reabre pelo caminho, sob a mesma trava (§0).
  - **Travas:** a direção padrão para a rodada 2 é **L1**. As travas ficam; o estoque é limpo pela W2.6;
    a contagem é reportada à parte e fica limitada pelo espaço de PIDs.
  - A proposta do Critic-C de o dono apagar as próprias travas vai à rodada 2 só com quatro coisas: o
    censo mecânico dos 4 abridores (§0) como guarda, o sinalizador em processo do próprio `.draining`, o
    controle de intercalação do Critic-A (vermelho com remoção ingênua, verde com a cura) e o novo
    julgamento do Critic-B.
  - **L2**, a re-checagem de inode no `filelock.py`, só entra como pacote de kernel PRÓPRIO e condicional:
    se a W0.5 depois da cura mostrar que só a listagem das travas ainda estoura o prazo do drain forçado.
  - **L3**, a relocação das travas, sai (ver C14).
  - Na W2.6, que roda com todas as sessões do projeto fechadas, apagar travas é seguro, porque não
    existe nenhum adquirente vivo.

### (c) A W3.6 (atualizar o Codex) espera o corte W7? — W3-7, L-7

- **Posições.** Critic-B (MF-W3-11): na 1.4.3, a W3.6 vem DEPOIS da W7, e a faixa não muda. Critic-C
  (MF-15): o runner do re-pass já resolve o Codex do MANIFESTO por npx, em cache próprio, quando o
  global é outra versão (rota 2), então a W3.6 não precisa esperar.
- **Evidência no disco.** Confere inteira (§0): as rotas 1 e 2, a igualdade de versão, a verificação pelo
  mesmo oráculo, o shim, o uso real no GA 1.4.1 e o envelope que lê a PROVENANCE e nunca a máquina. A
  âncora que o Critic-B protege continua intacta pela rota 2: o manifesto assinado da árvore tagueada, o
  validador sem mudança e a faixa sem mudança.
- **Decisão.** O disco refuta a NECESSIDADE de «W3.6 depois da W7». **A W3.6 roda logo depois do LAND da
  W3**, como o Owner quer: o Codex atualizado o quanto antes, pela W3. O resto do MF-W3-11 fica (faixa
  intacta na W3; T-8 atualizado no mesmo pacote).
- **Condições da W3.6 antes do corte:**
  1. o `derive-kit-143.py` e o `derive-ga-kit-143.py` herdam a rota 2, a igualdade de versão, a
     verificação pelo manifesto e o shim. Controle: kit com global ≠ manifesto ⇒ a PROVENANCE registra a
     versão do manifesto e a rota 2;
  2. a CLI `--verify-codex-pin` fica só-manifesto por padrão (Critic-C), e o registro só vale com flag
     explícita;
  3. o registro nunca é lido pelo validador, pelo `gen-envelope-ga.py` nem pelo kit (Critic-B);
  4. o pré-voo do corte declara a rede, os ~331 MB, o piso de `df` e a limpeza confinada do `.npx-cache`;
  5. o argv do runner fica alinhado à base da W3, e o pré-voo da Q11 vale também no re-pass da rc e do GA
     (Critic-C, MF-16);
  6. antes da W3.6 landam o detector de deriva lendo o registro e o pacote do evento de aceitação (ver (e)),
     ou a decisão escrita do Owner.
- **Resíduo declarado.** O corte depende da rede e de a 0.156.1 seguir baixável no registro.

### (d) Limiar de sucesso da W2 — W2-6

- **Posições.** Critic-C: absoluto, ≤ 1.000 arquivos nos 3 padrões depois de 24 h, com as sessões do
  projeto paradas. Critic-A: FLUXO com denominador (artefatos de PID morto por PID emissor distinto na
  janela), com teto absoluto e denominador zero reprovando. Critic-B: para a segurança decidem a decisão
  de guard entregue, a não-perda e zero quebra de cadeia atribuível; a contagem é higiene.
- **Decisão.** O domínio do VETO cobre os critérios de SEGURANÇA, que passam a ser os critérios que
  BARRAM:
  1. o controle de entrega de decisão (MF-W2-3) passa de vermelho a verde;
  2. o invariante por conjunto fica verde (todo `record_id` exatamente uma vez);
  3. `verify_chain()` fica íntegro sob estresse com escritores `agent_spawn`, depois da cura da condição
     67.

  `truly_lost` não serve: está morto (§0). Para a HIGIENE, o critério primário é o fluxo do Critic-A, por
  padrão (journals e, se houver remoção de trava, travas). Ele não fica verde por vácuo num dia leve e não
  envelhece com o estoque. O teto absoluto do Critic-C vira limite secundário de sanidade. Denominador zero
  reprova. O Check sai ≠ 0 acima do limiar (ajuste 41).

### (e) Observabilidade sem tocar `audit_emit.py` × evento de aceitação na cadeia HMAC — W2-7, W3

- **W2.** Os três concordam: nenhum evento por arquivo e nenhum toque no `audit_emit.py`. Um evento
  emitido por processo sem spool recriaria os 3 arquivos (Critic-C). A W2 se observa pelo RESULTADO:
  check advisory no `/ceo-boot` (contagem de 0 byte e idade do `.draining.*` mais velho), breadcrumb só
  quando o teto estourar e contagens da W2.6 no LEDGER.
- **W3 (o Critic-B prevalece).** Cada aceitação automática SUBSTITUI uma assinatura humana. Por isso ela
  vira **evento durável na cadeia HMAC**, como ação registrada em `_KNOWN_ACTIONS`, com versão, triple,
  sha256 do payload, `integrity`, digest do atestado e identidade. Hoje uma ação desconhecida vira
  breadcrumb (§0). O veículo é o do Critic-C: UM pacote de kernel de registro de ações, que também promove
  o `pair_rail_codex_pin_mismatch`. Ele vai em série com a W1a do PLAN-195 (`audit_emit.py`) e landa ANTES
  da W3.6. O precedente do AMEND-3, de preferir breadcrumb para não tocar o kernel, não se aplica, porque
  ali não se substituía assinatura. A alternativa (evidência só no registro) só entra por decisão
  ESCRITA do Owner, como resíduo no AMEND-1.

### L-1 e L-2

- **L-1:** liberação POR ONDA, como pedem os três críticos. Uma onda que volta não segura as outras.
- **L-2:** a rodada 2 mantém os mesmos 3 críticos (DEBATE-SCHEMA §2). Não entra crítico de FinOps: a W5c
  já saiu, e a escolha de modelo e esforço do revisor (W3-10) é adoção por geração, decidida pelo Owner.
- **Regra de processo (aviso do Critic-B):** cada crítica registra o id SERVIDO. Crítica com VETO cujo
  modelo servido esteja fora do piso VETO não conta.

## 3. Consensus findings (2+ críticos)

1. **C1: verificação de procedência dentro do hook PreToolUse vira fail-OPEN por timeout.** Critic-A,
   Critic-B, Critic-C. CRITICAL. O hook tem timeout de 210 s e a verificação baixa ~331 MB. Mitigação: o
   verificador roda em processo próprio, fora de qualquer guard. O hook só faz hash e consulta local, nunca
   usa rede, e sha desconhecido ⇒ bloqueio. → W3 (desenho (a)), ajuste 21.
2. **C2: «sem rede», «sem atestado» e tudo o que for «binário presente, mas não verificado» são
   fail-CLOSED, nunca INFRA.** Critic-A (matriz), Critic-B (MF-W3-1), Critic-C (o hook bloqueia sha
   desconhecido). CRITICAL. No hook, INFRA não executa o binário: tira a revisão em silêncio (§0).
   «O rail segue na última verificada» só vale com cópia retida, que é a promoção em duas fases do
   Critic-C. Fora dela, a frase vira «bloqueia até verificar ou reinstalar a versão verificada». → W3,
   pergunta 5, W3.4, ajustes 21 e 25.
3. **C3: a stdlib não verifica assinatura; coerência de digests não é autenticidade.** Critic-A,
   Critic-B, Critic-C. HIGH. Nada de cripto escrita à mão, e nada de chamar «assinatura conferida» à
   comparação de dois campos da mesma resposta. Medir o verificador do próprio npm num projeto-rascunho
   (W0.6); senão, decisão escrita do Owner. → W0, W3, pergunta 2, decisão pendente 3.
4. **C4: a sonda executa o binário.** Critic-A, Critic-B, Critic-C. HIGH. Ordem obrigatória: verificar →
   sondar → aceitar. A sonda (subcomandos e FLAGS dos chamadores) e o canário funcional bloqueiam o
   registro. Um espião prova zero execução de payload não verificado. → W3.3, ajuste 24.
5. **C5: o registro é uma 2.ª fonte de verdade.** Critic-B, Critic-C. HIGH. Ele mora fora da árvore git.
   Lêem-no só o núcleo do hook e a CLI; o passo 15, o `gen-envelope-ga.py` e o kit nunca. A CLI fica
   só-manifesto por padrão, com `verified` × `verified_auto`. Vale só para este repositório. O resíduo de
   mesmo UID é declarado. → W3, pergunta 1, ajuste 31.
6. **C6: modelo e esforço fixos no argv, em dois eixos.** Critic-A (stub de argv), Critic-B, Critic-C.
   MEDIUM. O binário é automático. Modelo e esforço ficam em constante canônica, e uma cerimônia por
   GERAÇÃO é aceitável e desejável. `--ignore-user-config` entra se a sonda confirmar a flag, com medição de
   que `memories` não carrega. Cada rodada registra versão, sha, modelo pedido e servido, e esforço. →
   W3-10, ajuste 32, decisão pendente 5.
7. **C7: a faixa do `codex-cli-pin.txt` fica intocada na W3, e os cortes seguem ancorados no manifesto.**
   Critic-A, Critic-B, Critic-C. → W3-3, ajuste 25.
8. **C8: chamadores fora do hook.** Critic-B, Critic-C. MEDIUM. Os livres (`codex_invoke.py`,
   `run-promotion-gate.py`) passam pelo núcleo. Os canônicos (`codex_review_user_code.py`, que é
   AUTOMÁTICO no opt-in, e `council-audit.js`) e o daemon `app-server` ficam declarados, com o estado do
   opt-in. → W3-6, ajuste 28.
9. **C9: a corrida do `agent_spawn` (condição 67) contamina a prova da W2.** Critic-A, Critic-B,
   Critic-C. HIGH. A cura landa antes da W2 ou dentro dela, e o estresse inclui escritores
   `agent_spawn`. Excluí-los e declarar a exclusão NÃO basta (VETO). → W2.5, risco 11, decisão pendente 1.
10. **C10: apagar caminho de trava quebra a exclusão mútua.** Critic-A, Critic-B. HIGH. Resolvido em
    §2(b). → W2.3/W2.4, ajustes 12 e 13.
11. **C11: o gatilho de reversão do AMEND-3 está morto.** Critic-A, Critic-C; o Critic-B acrescenta que o
    gatilho de taxa de quebra de cadeia não dá para avaliar. HIGH. O AMEND-4 não herda o `truly_lost` e
    declara que a reconciliação não roda em produção. Os gatilhos ficam em instrumentos LIGADOS, com
    controle positivo. → ajuste 19.
12. **C12: cura na origem dos journals vazios.** Critic-A, Critic-B, Critic-C. → W2-1, ajuste 12.
13. **C13: o caminho rápido confere só o próprio estado.** Critic-A, Critic-B, Critic-C. Um `stat` do
    próprio spool e um sinalizador em processo para o próprio `.draining` ou drain falho. O flush do buffer
    do journal continua. Órfãos ficam com a perna 3, que é o drain do próximo emissor; NÃO há perna de
    `SessionStart` (§0). → W2.2, ajuste 10.
14. **C14: a relocação (W2.3) cria «duas travas para o mesmo recurso» durante a convivência de
    versões.** Critic-A, Critic-B, Critic-C. MEDIUM. A W2.3 sai. → ajuste 12.
15. **C15: a W0.5 é pré-registrada e mede latência, entrega de decisão e timeouts, sem asserção de tempo
    absoluto no CI.** Critic-A (2^3 células), Critic-B (entrega de decisão), Critic-C (p50/p95). →
    ajuste 6.
16. **C16: o ADR-055-AMEND-4 vai em arquivo próprio, porque a premissa «anômalo» muda.** Os três. →
    ajuste 19.
17. **C17: a W2 se observa pelo resultado, sem evento por arquivo e sem `audit_emit.py`.** Os três. →
    §2(e), ajuste 20.
18. **C18: a pré-condição da W2.6 pode encolher para as sessões DESTE projeto.** Critic-A, Critic-C. O
    state dir é por projeto (W1 do PLAN-182). → decisão pendente 2.
19. **C19: a W5c fica no formato da Amendment 2**: só o working set, com piso VETO, fallback e pin
    intocados. Critic-B, Critic-C. → ajuste 35.
20. **C20: a entrega ao adopter pode falhar em silêncio.** Critic-A, Critic-B, Critic-C. MEDIUM. O
    `superseded` precisa do array de 8 ids da 1.4.2; a derivação pula em clone raso; `_tier_rank` dá -1
    para o 5.5. → ajuste 36.
21. **C21: veredito por onda (L-1).** Os três. → §2, §1.

## 4. Single-agent insights kept

1. **Critic-B — prazo na drenagem forçada de saída, derivado do orçamento do hook, com controle de ENTREGA
   DE DECISÃO (MF-W2-3).** Domínio do VETO. É a cura da CLASSE «trabalho longo dentro de guard vira
   allow»: vale para qualquer causa de lentidão. Estourado o prazo, o spool fica para a perna 3, e isso
   deixa de ser «anômalo»; é a emenda semântica do AMEND-4. → ajuste 11.
2. **Critic-B — identidade do construtor fixada (MF-W3-4).** Repositório, caminho do workflow, ref da tag
   amarrada à versão, `predicateType` SLSA v1 e `subject` = purl do pacote de PLATAFORMA, com digest =
   `dist.integrity`. A chave de aceitação é o sha256 do ÚNICO membro regular no caminho exato do tarball,
   lido em fluxo: sem extrair, sem link, sem nome duplicado. → ajuste 30.
3. **Critic-B — registro FORA de `state/`** (alcance do GC da W2), com modos 0700/0600, só-acréscimo e a
   evidência completa (MF-W3-5). Vence a proposta do Critic-C (registro no state dir) no domínio do VETO.
   → ajuste 31.
4. **Critic-B — `.npmrc` e `npm_config_*` podem redirecionar a raiz de confiança, e falha de TLS é
   fail-closed** (Unseen 8). Mais: o registro não vira atalho por mtime ou tamanho que dispense o hash a
   cada invocação (Unseen 10). → ajustes 7 e 31.
5. **Critic-B — o T-8 do `docs/CROSS-LLM-THREAT-MODEL.md` é atualizado no MESMO pacote**, porque a âncora
   de confiança do hook muda (MF-W3-11, parte mantida). Oráculo 0. → ajuste 28.
6. **Critic-B — escopo honesto:** o pin protege a identidade e a integridade do REVISOR cujo veredito o
   framework registra, não a máquina (Unseen 11). → ajuste 27.
7. **Critic-B — endurecimento do script da W2.6** (MF-W2-6): resolvedor `runtime_paths`, recusa de
   symlink, `unlink` relativo ao descritor do diretório, reexame imediato, simulação por padrão e contagem
   pelo mesmo método do critério. → ajuste 15.
8. **Critic-C — CLI só-manifesto por padrão (MF-11),** com `pin_source` no JSON e controle «kit com
   binário só auto-registrado falha no pré-voo, antes de qualquer rodada paga». → ajuste 31.
9. **Critic-C — adoção em duas fases com prefixo de staging (MF-9)**, que torna verdade «segue na última
   verificada» quando o Owner usa a rota do verificador. → ajuste 21.
10. **Critic-C — rollback e quarentena nomeados e testados (MF-13),** com contagem diária de
    `pair_rail_codex_unavailable` por versão no boot. → ajuste 25.
11. **Critic-C — mesmo argv do revisor nas duas trilhas (MF-16)**: o kit do corte herda a base da W3, ou
    declara a divergência. → ajuste 42.
12. **Critic-C — o detector de deriva lê o registro antes da W3.6 (NTH 2)**, senão vira alarme perpétuo
    recomendando o re-pin que o Owner recusou. → ajuste 26.
13. **Critic-C — censo da W5c contra o precedente de 76 paths, com novas linhas no mapa de colisões, e a
    W5c landando por ÚLTIMO no núcleo (MF-19, MF-21).** → ajustes 4 e 37.
14. **Critic-C — custo medido de uma varredura própria** (`os.scandir` com `stat` levou 50,7 s): nenhuma
    varredura do diretório inteiro dentro de hook. → ajuste 13.
15. **Critic-C — adoção sob demanda ou no máximo 1× por semana (NTH 3)**, coerente com o freio Q2. →
    ajuste 29.
16. **Critic-C — limite do `parse_semver` (NTH 7)**, que é conferido (§0). O passo 15 não garante «só
    estável»; quem garante é o sha do manifesto. Declarar no AMEND-1. → ajuste 27.
17. **Critic-A — os Checks de «Success criteria» são verdes por construção** (R-QA2): cada um precisa ser
    vermelho antes e verde depois, com a afirmação dentro do código de saída (MF-17). → ajuste 41.
18. **Critic-A — invariante por CONJUNTO, `verify_chain()` sobre ≥ N elos, escritores mistos e 3 a 5
    mutantes plantados (MF-4).** → ajuste 14.
19. **Critic-A — tabela pré-registrada do predicado, com quase-acertos tirados do censo vivo** (travas de
    outros módulos, `*.compact.tmp`, journal agregado) e os journals com conteúdo como controle (MF-6). →
    ajuste 13.
20. **Critic-A — censo AST: toda chamada a `read_prev_hmac()` fora de teste fica dentro de `with
    FileLock(`, com controle positivo** (MF-8; «cure a classe»). → decisão pendente 1, ajuste 9.
21. **Critic-A — fixtures da W3 sem rede**: guarda de socket com controle positivo, registro falso só sob
    `CEO_PAIR_RAIL_TEST_MODE=1`, tarball sintético e o `npm i -g` modelado no MESMO caminho (MF-10). →
    ajuste 25.
22. **Critic-A — pré-registro do re-teste da W5c com regras de VALIDADE** (id servido ≠ pedido ⇒
    INVÁLIDA) e o efeito teto declarado (MF-14). → ajuste 38.
23. **Critic-A — afirmações do adapter primeiro, teste depois:** duas sondas pagas baratas, e a proteção
    de `tool_choice` forçado vale para a CLASSE `_ALWAYS_ON_THINKING_MODELS`, `claude-opus-5-5` incluído
    (MF-16). → ajuste 39.
24. **Critic-A — guarda de classe no `_tier_rank`**, com renumeração e direções (MF-15). → ajuste 36.
25. **Critic-A — substrato em toda entrada de medição do LEDGER** (versão do CC, `python3` dos hooks, sha
    do instrumento — NTH 5). → ajuste 6.

## 5. Single-agent insights rejected / deferred

1. **Critic-C, MF-1 — o dono apaga as próprias TRAVAS na saída:** ADIADO para a rodada 2, sob a regra da
   §2(b). Premissa refutada no caso `.draining.*` (§0). A apagar o próprio journal vazio fica aceita
   (C12).
2. **Critic-C, MF-4 — GC de travas de PID morto dentro do hook, com o reuso de PID declarado:**
   REJEITADO. O VETO prevalece, e o `FileLock` não re-checa o inode. Na W2.6, com as sessões fechadas,
   continua valendo.
3. **Critic-C, MF-14 — carência de 24 h:** REJEITADO em favor de 48 h (§2(a)). A regra de escolha dele
   (a estável elegível mais nova, ≤ `latest`) foi ACEITA.
4. **Critic-C, MF-6 — limiar absoluto como critério primário:** REBAIXADO a teto secundário (§2(d)).
5. **Critic-B, MF-W3-11 — «a W3.6 depois da W7»:** REFUTADO pelo disco (§2(c)). O resto do item fica.
6. **Critic-B, MF-W2-5 e W2-2 — «órfão recuperado pelo drain do próximo `SessionStart`»:** premissa
   REFUTADA (§0). O teste de estresse fica, com a recuperação pelo drain do próximo emissor (oportunista
   ou forçado).
7. **Critic-B, W3-9 — o corpus da sentinela é o corpus travado do ADR-111:** premissa REFUTADA (o corpus
   não está no repositório). Vai ao Owner (decisão pendente 4). O gatilho do ADR-111 §2 fica PRESERVADO,
   mas declarado NÃO AVALIÁVEL até existir corpus com sha e linha de base (Critic-A, MF-12).
8. **Critic-A, MF-1 opção (a) — re-checagem de inode no `filelock.py` dentro da W2:** ADIADO a pacote de
   kernel próprio e condicional (L2, §2(b)).
9. **Critic-A, MF-7 — teste de convivência da relocação:** PREJUDICADO, porque a W2.3 sai. Fica só a
   regra de versões mistas do AMEND-4.
10. **Critic-B, nice-to-have 1** (o kit re-pina o manifesto por script nos cortes futuros), **2** (lista
    de revogação assinada), **3** (cópia endereçada por conteúdo do último payload; pede ADR próprio) e
    **4** (pin automático para adopters): ADIADOS a follow-ups, fora da 1.4.3.
11. **Critic-B, nice-to-have 6** (prazo na reconciliação de início de sessão): PREJUDICADO, porque o
    código está morto. Ligar a reconciliação também fica FORA da W2, porque abriria ~75 mil journals sob o
    timeout de 5 s do `SessionStart` (Critic-A). Os 214 journals com conteúdo ficam declarados como
    forense-only.
12. **Critic-A, nice-to-have 3** (contrato JSONL por versão): ADIADO para a 1.ª rodada real da W3.6.
13. **Critic-C, nice-to-have 6** (reaproveitar o `_cacache` do npm): ADIADO ao builder, com a parte
    criptográfica sob revisão do portador do VETO.
14. **Critic-C, nice-to-have 8** (o L3 `adopt-model.py` antes da W5c): mantido como PREFERÊNCIA, não como
    pré-condição. Se o L3 não estiver pronto, clona-se o derivador da wave-opus55.

## 6. Respostas às perguntas da proposta

| id | resposta | fonte |
|---|---|---|
| W2-1 | Criar menos (caminho rápido) + apagar o journal vazio NA ORIGEM sob a própria trava. Travas: L1 por padrão (§2(b)). Relocação: sai | C12, C14, §2(b) |
| W2-2 | O caminho rápido usa só o próprio PID, sem listar. Órfãos: perna 3 (drain do próximo emissor, `spool_writer.py:2366-2371`). Não existe perna de `SessionStart` | C13, §0 |
| W2-3 | Sem layout novo. O AMEND-4 traz a regra de versões mistas: LAND com as sessões do projeto fechadas, declarado, e adopter via `upgrade.sh` com sessão aberta declarado | C14, ajuste 19 |
| W2-4 | Nenhuma varredura própria no hook. Se sobrar GC de journal de PID morto: de carona na listagem da fase 2, depois de soltar a trava canônica, com teto (≤ 200 arquivos e ≤ 50 ms, a confirmar na W0.5), regex ancorada, lista do que nunca se apaga e reexame sob trava. Nenhum `*.lock` | ajuste 13 |
| W2-5 | A cura landa ANTES do SIGN da W2 (pacote próprio, recomendado) ou dentro dela. O estresse inclui `agent_spawn`. O VETO fica levantado até lá | C9, decisão 1 |
| W2-6 | Arquivo próprio. O limiar segue §2(d). Os gatilhos de reversão ficam em instrumentos ligados, com controle positivo | C11, C16 |
| W2-7 | Pelo resultado (`/ceo-boot`, LEDGER). Sem `audit_emit.py` | §2(e) |
| W3-1 | Diretório resolvido por `runtime_paths`, FORA de `state/` e da árvore git; só-acréscimo; leitores: núcleo do hook e CLI; só este repositório; resíduo de mesmo UID declarado | C5, Critic-B |
| W3-2 | Inviável só com stdlib. Medir o verificador sigstore do npm num projeto-rascunho (W0.6). Senão, a «confiança no registro» vai como decisão escrita do Owner. O vínculo atestado → tarball → payload sai da stdlib (`urllib` com TLS verificado, `tarfile` em fluxo, `hashlib`). O download nunca roda no hook | C3, decisão 3 |
| W3-3 | A faixa fica `>=0.128.0,<0.157.0`. O corte declara o 0.156.1. O limite do `parse_semver` é declarado | C7 |
| W3-4 | 48 h no relógio do registro; a estável elegível mais nova, ≤ `latest`; nunca «== latest»; gramática estrita | §2(a) |
| W3-5 | Todo «presente, mas não verificado» ⇒ SECURITY, saída 1 e bloqueio. INFRA (3) só no que já era INFRA no ADR-182 §2. Falha de rede é falha do VERIFICADOR (versão não registrada), nunca INFRA do hook | C2 |
| W3-6 | Livres pelo núcleo; canônicos e daemon declarados, com o estado do opt-in | C8 |
| W3-7 | O corte já é independente do global (rota 2). A W3.6 vai logo após o LAND da W3, com as condições de §2(c) | §2(c) |
| W3-8 | Automática, dentro do verificador, depois da procedência e antes do registro; bloqueante; inclui as FLAGS e o canário funcional | C4 |
| W3-9 | O gatilho do ADR-111 §2 fica preservado e declarado não avaliável até haver corpus. A sentinela vai ao Owner | decisão 4 |
| W3-10 | Dois eixos; constante canônica; `--ignore-user-config` se a sonda confirmar; o id fixado entra no `model-deprecations.json` | C6, decisão 5 |
| W5c-1 | Formato A2, só ele; `_ROUTING_TABLE` intocado | C19 |
| W5c-2 | Decidido pelo CEO, com critério pré-registrado: os exemplos da skill seguem com o alias `sonnet`. Fixar o id recria churn a cada geração. A tabela de roteamento (`SKILL.md:109-123`, que cita `claude-sonnet-4-6`) é corrigida no pacote. Se a W5.0 medir alias → `claude-sonnet-5-5` em 3/3 sondas (id servido conferido, CC congelado), a tabela cita «alias `sonnet` = `claude-sonnet-5-5` no CC ≥ 2.1.284, medido em <data>»; senão, cita só o alias e declara | CEO |
| W5c-3 | Medir primeiro (duas sondas pagas, pré-registradas); o teste codifica a resposta MEDIDA; proteção para a classe inteira | Critic-A, MF-16 |
| W5c-4 | Nenhum fato antecipa a W5c. Ela landa por ÚLTIMO no núcleo, re-derivada sobre o HEAD. Se não estiver landada quando começar a derivação do kit da W7, vai para depois do GA | Critic-C, MF-21 |
| W5c-5 | Tabela de células do Critic-A, com validade antes das células. FAIL ⇒ pára antes do SIGN e o Owner decide por múltipla escolha; o debate não desfaz o «Adotar» | Critic-A, MF-14 |
| W5c-6 | Sim: as duas cláusulas da A2.2 (itens 5 e 6) repetidas; o array de 8 ids da 1.4.2 vai para `superseded`; o `new` acrescenta o 5.5 no FIM | C20 |
| L-3 | Sem efeito: o debate NÃO recusou o pin automático | — |
| L-6 | Primeiro pronto, primeiro a landar; um por fechamento; nenhum pacote de ADR em voo entre o início da derivação do kit da W7 e a publicação do GA | Critic-C, NTH 4 |
| L-7, L-9 | L-7 cai (§2(c)). L-9: promoção em duas fases + bloqueio no hook | §2(c), C2 |
| L-10 | Prejudicada: a listagem de `:2480` está em código morto | §0 |

## 7. Plan adjustments (o CEO aplica no PLAN-194 antes da rodada 2; esta síntese não edita o plano)

**Cabeçalho, regra de WIP e Approach**

1. *Frontmatter `budget_tokens`/`budget_sessions`:* W2 de 0,9 a 1,7 M (prazo na saída + provas); pacote da cura do `agent_spawn` de 150 a 300k + ~50k do censo AST; W3 de 1,3 a 2,5 M em 2 a 3 sessões, em 2 pacotes de ≤ 8 paths, mais o pacote de kernel de registro de ações (100 a 200k + 1 cerimônia de kernel) e a W0.6; W5c com +100 a 200k para o censo contra o precedente.
2. *Frontmatter `external_wait`:* o Codex fica no 0.156.1 até o LAND da W3 (sai «e até o fim do corte W7»); carência de 48 h no relógio do npm; pré-condição da W2.6 conforme a decisão pendente 2.
3. *Approach, item 4, e «Cláusula de bloqueio»:* liberação POR ONDA (L-1). A W5c está liberada pelo PROCEED da rodada 1, com os must-fix valendo para ela. W2 e W3 seguem BLOQUEADAS até a rodada 2.
4. *Mapa de colisões:* novas linhas: (a) `audit_emit.py` × pacote de kernel de registro de ações da W3 × W1a do PLAN-195, hoje CERTA para a W3, em série; (b) `audit_log.py` × cura do `agent_spawn` × W5c (o precedente o tocou), com a cura primeiro; (c) `scripts/install.sh` e baseline do censo do instalador × W5c, que entra na fila depois da W5b e da W1a/W1b do PLAN-183; (d) `templates/settings/settings.user.json` × W6 × W5c; (e) `_lib/test_isolation.py` × W5c; (f) `docs/CROSS-LLM-THREAT-MODEL.md` × W3 × W0 do PLAN-195 (risco 9); (g) `check-substrate-drift.py` × L1 × W3, com a leitura do registro dentro da L1 ou logo depois; (h) `ceo-boot.py` × L2 × W2 (check advisory), um pacote só; (i) `_lib/filelock.py` (kernel) só se a L2 for escolhida.
5. *Paths × oráculo:* acrescentar `.claude/hooks/audit_log.py` (1), `.claude/hooks/tests/test_two_writer_chain.py` (0), `.claude/hooks/_lib/filelock.py` (1, condicional), o verificador novo da W3 (nome proposto `.claude/scripts/codex-auto-pin-verify.py`, livre: rodar o oráculo), `docs/CROSS-LLM-THREAT-MODEL.md` (0), `.claude/scripts/derive-settings-baselines.py` (0, bateria da W5c) e `.claude/scripts/check-installer-write-safety.py` (0, bateria da W5c). Tirar `SessionStart.py` da W2: não há drain nem reconciliação nele.

**W0**

6. *W0.5:* pré-registro no LEDGER ANTES de rodar, com as 8 células do Critic-A, mais p50/p95 da latência de saída, entrega de decisão de um guard BLOCK, linhas de timeout e uma célula «estoque só de travas (~150 mil)». Substrato congelado (versão do CC, `python3` dos hooks, sha do instrumento). Critério de vermelho escrito antes. Vermelho não reproduzido ⇒ «prova só estrutural», declarada. Depois da cura, a mesma matriz com tolerância de RAZÃO (p95 cheio/vazio ≤ 1,2 com N ≥ 30) e o `SPOOL_LOCK_TIMEOUT` re-medido.
7. *W0.6 nova (W3, sem cota paga):* o verificador sigstore do npm num projeto-rascunho (`npm i --prefix`, nunca `-g`), com registro fixo, sem `.npmrc` do usuário e com `npm_config_*` limpos. Vermelho = tarball adulterado; verde = pacote de plataforma íntegro. Diretório próprio, piso de `df`, ~331 MB e limpeza confinada.

**W2**

8. *W2, «Objetivo» e «Por que importa»:* o risco de segurança é a DECISÃO DE GUARD PERDIDA por latência de saída; a contagem é higiene. O Goal passa a dizer: «sem acúmulo de journals e sem decisão perdida; travas limitadas e limpas pela W2.6» (salvo L2).
9. *W2, «Paths» e dependências:* a cura do `agent_spawn` (`audit_log.py` + teste de barreira multiprocesso, vermelho no HEAD + censo AST de `read_prev_hmac()` + docstring do `test_two_writer_chain.py`) é PRÉ-CONDIÇÃO do SIGN da W2. Vaga: decisão pendente 1. A linha que aposenta a condição 67 vai no `CHANGELOG.md` do corte W7, não no pacote da cura.
10. *W2.2:* um `stat` do próprio spool e um sinalizador em processo (o próprio `.draining` ou drain falho); o flush do buffer do journal continua; zero `listdir`/`scandir`, contados por envoltório. As 5 células do Critic-A, mais a recuperação de órfão pelo drain OPORTUNISTA do próximo emissor. O teste 4 de `test_spool_drain_contended_skip.py` fica intacto.
11. *W2.2-bis, nova (MF-W2-3):* prazo na drenagem forçada de saída, derivado do orçamento do hook (timeout de 5 s menos margem). Estourado o prazo, o spool fica para a perna 3, sem ser «anômalo». Controle de entrega de decisão: vermelho na W0.5, verde depois da cura.
12. *W2.3:* REMOVIDA (relocação). No lugar: «journal vazio removido na origem, sob a própria trava» + a regra de travas da §2(b). L1 é o padrão; a remoção pelo dono vai à rodada 2 com o censo dos 4 abridores, o sinalizador e o controle de intercalação; L2 só como pacote de kernel condicional.
13. *W2.4:* nenhum `unlink` de `*.lock` em hook; nenhuma varredura própria. O GC que sobrar segue W2-4 (§6). A tabela do predicado é pré-registrada (Critic-A, MF-6), com a lista do que NUNCA se apaga (Critic-B, MF-W2-4) e o porquê de cada diferença em relação ao predicado da W2.6.
14. *W2.5:* invariante por conjunto (`record_id` exatamente uma vez); `verify_chain()` sobre ≥ N elos; escritores mistos: `agent_spawn` (depois da cura), `audit_emit`, drainers oportunistas e forçados, saídas pelo caminho rápido, kill -9 no meio do drain e reuso de PID; 3 a 5 mutantes plantados, cada um reprovando.
15. *W2.6:* script com o endurecimento do Critic-B (MF-W2-6), mais a simulação com contagem por célula, o manifesto de hash dos journals com conteúdo antes e depois (qualquer diferença reprova) e a re-contagem pelo mesmo método. Pré-condição conforme a decisão pendente 2. A W2.6 pode apagar travas, porque não há adquirente vivo.
16. *W2, «Controle vermelho→verde»:* trocar «latência igual à do dir vazio» pela razão medida FORA do CI (ajuste 6) e pelo controle de entrega de decisão. Nenhuma asserção de tempo absoluto em teste do CI.
17. *Checks W2.2/W2.4/W2.5:* seletores `-k` distintos (`fast_path`, `deadline`, `origin`, `gc`, `invariant`), com guarda de seletor que casa zero.
18. *W2.1/W3.2:* rascunhos do `ADR-055-AMEND-4` e do `ADR-182-AMEND-1` em PROPOSED como entrada da rodada 2, em `.claude/plans/PLAN-194/debate/round-2/` (oráculo 0). O arquivo canônico nasce só no pacote de ADR (Q5).
19. *Conteúdo exigido do AMEND-4:*
    - a união de não-perda reescrita (perna 2 só para quem tem spool; perna 3 = drain do próximo emissor; sem perna de `SessionStart`);
    - o prazo da saída;
    - a regra de versões mistas;
    - regex ANCORADAS, com PID só de dígitos;
    - a lista do que nunca se apaga;
    - o caminho de reversão;
    - gatilhos em instrumentos ligados, com controle positivo de perda sintética: resíduo acima do limiar em 3 medições diárias; linha de timeout depois do LAND sob a carga da W0.5; `.draining.*` com mais de 24 h; decisão perdida no controle; quebra de cadeia atribuível à W2 depois da cura;
    - declarado: `truly_lost` morto, reconciliação fora de produção e 214 journals forense-only.
20. *W2-7:* observabilidade pelo `/ceo-boot` (check advisory: contagem de 0 byte nos padrões e idade do `.draining.*` mais velho), dentro do pacote da L2; breadcrumb com taxa limitada só quando o teto estourar; teste afirmando contagem registrada = arquivos apagados.

**W3**

21. *W3, «Desenho decidido» (a), reescrito:*
    - o verificador roda em processo PRÓPRIO, fora de qualquer guard, em duas fases: staging em prefixo próprio → procedência → sonda + canário → registro → promoção ao global com a MESMA versão e o MESMO sha;
    - o hook só faz hash e consulta local, nunca usa rede;
    - sha fora do manifesto e do registro ⇒ bloqueio, nomeando o verificador.
22. *W3, «Perguntas de desenho» 1 a 7 (+ 8 a 10):* trocar o texto em aberto pelas respostas da §6. A pergunta 5 passa a dizer «bloqueia até verificar ou reinstalar a versão verificada».
23. *W3.1:* «Codex no 0.156.1, sem `npm update -g`, até o LAND da W3»; depois disso, só pelo procedimento da W3.6 (instalar a versão ELEGÍVEL, nunca a `latest` crua).
24. *W3.3:* sonda (subcomandos e a união das FLAGS dos chamadores) e canário funcional (`exec` mínimo com o argv REAL sobre diff fixo, devolvendo JSON de veredito), automáticos e bloqueantes, depois da procedência e antes do registro. Testes com `codex` stub no PATH temporário e espião de zero execução de payload não verificado.
25. *W3.4, controles reescritos:*
    - a matriz {rede ok/falha} × {atestado válido/ausente/de outro pacote/identidade inválida com digests coerentes} × {versão registrada/nova}, com status e saída por célula;
    - guarda de socket com controle positivo, tarball sintético e 1 atestado real de KB só para o formato;
    - resposta acima do teto ⇒ recusa; o `npm i -g` modelado no mesmo caminho;
    - quarentena ⇒ `mismatch`; reinstalar a anterior ⇒ `verified` offline;
    - CLI sem flag ⇒ só-manifesto;
    - a célula (d) da faixa vira: «o validador do veredito segue INVALID para versão só auto-pinada».
26. *W3.6:* logo depois do LAND da W3, e não mais depois da W7. Antes dela: o pacote de kernel do evento (ou a decisão escrita do Owner); o detector de deriva lendo o registro; os derivadores do kit da W7 herdando a rota 2. A 1.ª rodada real: `verified_auto` + evento na cadeia + `session_meta` com versão, originador e 0 sessões «guardian».
27. *W3, «Declarar no material assinado»:* acrescentar o resíduo de mesmo UID do registro; o escopo (identidade do revisor, não proteção da máquina); a «confiança no registro», se a decisão 3 for por ela; a sentinela não implementada, se a decisão 4 for (ii); o hook `Stop` automático no opt-in; o `council-audit.js`; o daemon; o limite do `parse_semver`; adopters seguem em INFRA aberto.
28. *W3, «Paths»:* dois pacotes. (1) AMEND-1 + `check_pair_rail.py` + verificador + teste(s) + `docs/CROSS-LLM-THREAT-MODEL.md` (T-8). (2) `codex_cli_shape.py` (argv fixo e o id em `_VALID_MODELS`, depois da W3b) + `codex_invoke.py` + `run-promotion-gate.py` pelo núcleo. `codex-cli-pin.txt` FORA. O pacote de kernel do `audit_emit.py` é à parte.
29. *W3, elegibilidade:* constante canônica de 48 h com teste; a estável elegível mais nova; ≤ `latest`; sem `deprecated`; ≥ piso do manifesto; gramática estrita (§2(a)). Adoção sob demanda ou ≤ 1× por semana, sob o freio Q2.
30. *W3, identidade do construtor:* as constantes da §4, item 2.
31. *W3, registro e CLI:* local, modos, leitores e só-acréscimo conforme C5 e §4, item 3. `--verify-codex-pin` só-manifesto por padrão; aceitação pelo registro só com flag explícita; `pin_source`/`verified_auto` no JSON. Contrato de cada consumidor (hook, Gate 4 do `pair-rail-gate.sh`, `run-ga-repass.sh`, release) escrito no AMEND-1. Sem atalho por mtime ou tamanho.
32. *W3, «Base do argv fixo»:* dois eixos (C6); registro por rodada de versão, sha, modelo pedido e servido, e esforço; o id fixado no `model-deprecations.json`; id indisponível ⇒ contagem diária no boot, nunca silêncio.
33. *W3-9, sentinela:* conforme a decisão pendente 4. O AMEND-1 preserva o gatilho do ADR-111 §2 como NÃO AVALIÁVEL até existir corpus com sha e linha de base (m ≥ 3, variância medida com o mesmo binário).
34. *Risco 4:* reescrever as mitigações (verificador fora do hook, sonda e canário bloqueantes, carência de 48 h, identidade fixada, quarentena, evento durável) e o estado da sentinela. O corte segue pela rota 2.

**W5c (PROCEED; must-fix que valem para a onda)**

35. *W5c, texto da emenda 4:* formato A2; `claude-sonnet-5-5` fora do piso VETO, do pin de sessão e de `.claude/agents/*.md` (A1.1 reafirmada), com controle de igualdade de bytes do conjunto elegível a VETO antes e depois (Critic-B, MF-W5c-1).
36. *W5c, entrega ao adopter:*
    - o array de 8 ids da 1.4.2 vai para `superseded`; o `new` acrescenta o 5.5 no FIM, com casamento byte a byte;
    - 4 células: o array exato ⇒ MIGRATE; o customizado ⇒ PRESERVED com WARN; o de 7 ids ⇒ MIGRATE; a 2.ª execução ⇒ nada muda;
    - `derive-settings-baselines.py --check` na bateria, num clone com TODAS as tags GA, e SKIP conta como falha;
    - `_tier_rank` renumerado (`sonnet-5→sonnet-5-5` promote; `sonnet-5-5→opus-4-8` promote; `sonnet-5-5→sonnet-4-6` demote), com guarda de classe contra o bloco do ADR-149.
37. *W5c, censo e ordem:* censo da abertura contra o `WOPUS55.patch` (76 paths), com as linhas novas do ajuste 4; `check-installer-write-safety.py` na bateria; a W5c landa por ÚLTIMO no núcleo, re-derivada sobre o HEAD; linha de corte da W5c-4.
38. *W5c.1:* pré-registro com a tabela do Critic-A:
    - instrumento com sha (copiar o da S357 para dentro ou pinar o sha);
    - braços `claude-sonnet-5` EXATO × `claude-sonnet-5-5`;
    - n, métrica, δ e regra de custo;
    - validade antes das células;
    - efeito teto declarado.
39. *W5c-3, adapter:* duas sondas pagas pré-registradas (thinking `disabled`; `tool_choice` forçado com thinking ligado) na W5.0 ou na W5c.1. O teste codifica a resposta medida, com data e substrato; proteção parametrizada sobre `_ALWAYS_ON_THINKING_MODELS`.
40. *W5c-2, skill:* critério da §6.

**Transversal**

41. *«Success criteria»:*
    - todo Check fica vermelho antes e verde depois, com a afirmação no código de saída;
    - W2: sai ≠ 0 acima do limiar, com timeout ou decisão perdida na janela, ou com denominador zero, pelos critérios de §2(d);
    - W3: exige `pin_source = registro` para uma versão FORA do manifesto;
    - W5c: afirma `claude-sonnet-5-5` no bloco do ADR-149, no `availableModels`, no `cost-table.yaml` e na entrada do re-teste no LEDGER;
    - o braço vermelho da W5c.4 afirma a DIFERENÇA EXATA (`+claude-sonnet-5-5` na S1).
42. *W7, «Pré-condições do corte»:*
    - o Codex global pode diferir do manifesto;
    - os derivadores do kit herdam a rota 2 com controle;
    - o pré-voo declara a rede, os ~331 MB e o piso de `df`;
    - o argv do runner fica alinhado à base da W3 (ou a divergência é declarada);
    - o pré-voo da Q11 vale no re-pass da rc e do GA;
    - linha de corte da W5c;
    - nenhum pacote de ADR em voo durante o kit (L-6).
43. *W5.1:* se a W3.6 rodou antes do corte, o `codex_cli` do refresh é a versão global auto-pinada, e não o 0.156.1.
44. *«How to continue»:* `codex --version` = 0.156.1 até o LAND da W3; depois, a versão elegível registrada.
45. *Risco 11:* números de 2026-10-02T00:25Z (§0); o gatilho de reversão do AMEND-3 está morto; a condição 67 (já no texto).
46. *Risco novo:* «trabalho longo dentro de guard vira allow por timeout», classe comum à W2 (listagem) e à W3 (download). Mitigação: prazo na saída e verificador fora do hook.
47. *«Fora do escopo» / backlog:* os nice-to-have 1 a 4 do Critic-B; a ligação da reconciliação de início de sessão; a L2, se não for escolhida; a sentinela, se a decisão 4 for (ii).
48. *«Decisões do Owner»/«Open questions»:* registrar as decisões pendentes abaixo, cada uma com a recomendação, e a regra de parada do debate (≤ 3 rodadas; NO-GO só por P0 ou afirmação FALSA; impasse ⇒ Owner por múltipla escolha).

## 8. Decisões pendentes do Owner (com a recomendação do CEO)

1. **Vaga da cura da corrida do `agent_spawn` (condição 67; risco 11, unidade 4).** O VETO da W2 fica
   levantado até ela landar. **Recomendação:** pacote canônico PRÓPRIO, landado ANTES do SIGN da W2: o
   primeiro pacote na vaga da W2, ou a primeira vaga que abrir antes. Raio menor e rail independente;
   150 a 300k tokens + ~50k do censo AST, 0 a 1 sessão. A aposentadoria da condição 67 vai no
   `CHANGELOG.md` do corte. Alternativa: dentro da W2, com +2 paths.
2. **Pré-condição da limpeza única W2.6.** **Recomendação:** trocar «todas as sessões do Claude fechadas»
   por «todas as sessões DESTE projeto fechadas», porque o state dir é por projeto desde a W1 do PLAN-182.
   O script recusa se achar arquivo da família com PID vivo ou mtime < 10 min. E rodar já: o
   `audit-log.errors` subiu de 25.589 para 30.258 linhas entre ~20:08Z e 00:25Z, com 30.068 timeouts.
3. **Assinatura do atestado (W3-2), só se a medição W0.6 reprovar o verificador do npm.**
   **Recomendação:** aceitar por escrito «confiança no registro via TLS + vínculo de digests + identidade
   do construtor fixada», como resíduo NOMEADO no AMEND-1 e no material assinado. Recusar devolve o plano
   B (re-pin manual), que o Owner já recusou.
4. **Sentinela de qualidade (desenho (b) da W3).** O corpus travado do ADR-111 não está no repositório.
   **Recomendação:** (ii) a W3 landa SEM sentinela, declarada, e a sonda e o canário bloqueantes cobrem a
   classe A7. A sentinela vira follow-up quando houver corpus com sha e linha de base (m ≥ 3) sob o freio
   Q2. Alternativa (i): construir o corpus e a linha de base antes da W3 (cota do Codex m × N revisões +
   ~100k tokens).
5. **Modelo e esforço fixos no argv do rail (W3-10).** **Recomendação:** `gpt-6-astra` + `xhigh`, o par
   em uso de fato, condicionado ao re-teste da Q11. O id entra em `_VALID_MODELS` no pacote da W3, depois
   da W3b. Trocar de modelo passa a ser cerimônia por GERAÇÃO.
6. **Evidência da aceitação automática (só se o Owner quiser evitar o pacote de kernel).** O padrão do
   debate é o evento na cadeia HMAC (§2(e)). **Recomendação:** manter o evento. A alternativa (evidência
   só no registro) exige o resíduo escrito no AMEND-1.
7. **Para ciência, sem decisão:**
   - a carência é de 48 h, então o pin anda ~2 dias atrás da `latest`, sem cerimônia;
   - a W3.6 roda logo depois do LAND da W3, e o corte segue pela rota 2, como o Owner pediu;
   - a W5c saiu do portão do debate, mas a posição na fila não muda.

## 9. Round verdict

**RUN-ANOTHER-ROUND.**

- **W2:** RUN-ANOTHER-ROUND (VETO levantado).
- **W3:** RUN-ANOTHER-ROUND (VETO levantado).
- **W5c:** PROCEED (`design-coherent`; VETO retirado com as condições dos ajustes 35 e 36).

**Entrada da rodada 2:**

- este consenso;
- o plano com os ajustes 1 a 48 aplicados;
- os rascunhos PROPOSED do `ADR-055-AMEND-4` e do `ADR-182-AMEND-1` (ajuste 18);
- as decisões do Owner que já tiverem saído.

Os mesmos três críticos julgam só a W2 e a W3 (a W5c só se houver desvio de texto), e cada crítica
registra o id servido.

**Retirada do VETO na rodada 2:**

- **W2:** MF-W2-1 a MF-W2-6 no AMEND-4 e no plano, com a cura do `agent_spawn` landada antes do SIGN ou
  dentro do pacote.
- **W3:** MF-W3-1 a MF-W3-11 no AMEND-1, já com as correções das §2(a) e §2(c), e as decisões 3 a 6
  escritas.

**Regra de parada (pré-registrada):** no máximo 3 rodadas; NO-GO só por P0 ou afirmação FALSA no plano;
impasse depois da 3.ª rodada ⇒ Owner por múltipla escolha. Nenhuma rodada do Codex acima de 80% do
semanal (Q2).
