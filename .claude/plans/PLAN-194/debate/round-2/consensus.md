---
plan: PLAN-194
round: 2
rounds_synthesized: [round-1, round-2]
scope: "W2 e W3 (a W5c saiu PROCEED na rodada 1)"
critics: [Critic-A, Critic-B, Critic-C]
agents_considered: [Critic-A, Critic-B, Critic-C]
verdicts: [ADJUST, ADJUST, ADJUST]
vetoes: "Critic-B — W2: RETIRADO, condicionado a MF-R2-W2-1..4 no texto do ADR-055-AMEND-4 e do plano antes do pacote de ADR, com a W2.0 landada antes do SIGN da W2; W3: LEVANTADO até MF-R2-W3-1..8 no ADR-182-AMEND-1 revisado e a escolha do Owner entre os empacotamentos (i) e (ii) do sigstore. Se o Owner escolher «confiança no registro», o VETO segue levantado e a W3 vai ao Owner (ESCALATE)"
wave_verdicts:
  W2: PROCEED
  W3: RUN-ANOTHER-ROUND
  W5c: "PROCEED (rodada 1, inalterado)"
round_verdict: RUN-ANOTHER-ROUND
next_round: "rodada 3 — a ÚLTIMA pela regra de parada pré-registrada; só a W3"
design_coherent:
  W2: true
  W3: false
  W5c: true
consensus_adjustments: 52
decisions_revised_in_plan: "pendente — esta síntese NÃO edita o plano nem os rascunhos; o CEO aplica a lista «Plan adjustments» (os itens da W2 sem nova rodada; os da W3 antes da rodada 3)"
synthesized_at: 2026-10-02T03:29:49Z
synthesized_by: CEO (síntese delegada, S361)
synthesized_from: "texto anonimizado das três críticas da rodada 2 (cópias fora do repositório, no scratchpad da sessão); consenso da rodada 1; rascunhos PROPOSED do ADR-182-AMEND-1 e do ADR-055-AMEND-4; PLAN-194 no commit 11c71a42; seção W0.6 do LEDGER e o relatório completo da W0.6 (fora do repositório). Limitações declaradas: o mapa de anonimização foi lido só para o estado do VETO, mas também lista os arquétipos; os rascunhos e o plano citam achados por arquétipo. Cada decisão abaixo se apoia em fato conferido no disco ou medido, não em quem o afirmou."
---

# Consenso — PLAN-194, debate L3 único, rodada 2 (W2 e W3)

> **O que este veredito certifica.** `design-coherent` (DEBATE-SCHEMA §13.1) certifica só a coerência
> interna do desenho entre as perspectivas forçadas do MESMO modelo. Não autoriza publicar. Publicar
> continua exigindo a cascata V0 → V1 → V2 (rail do Codex) → V3 (GPG do Owner).
>
> **Repositório público.** Só classes de defeito e ids de lane; nenhum caminho da pasta privada do Owner;
> nenhuma receita de contorno de guarda.

## 0. Verificação das afirmações (antes de consolidar)

O sintetizador conferiu no disco (HEAD `11c71a42`; o arquivo do plano é idêntico ao do commit) e por
medição só-leitura as afirmações em que as decisões se apoiam.

| afirmação | onde | resultado |
|---|---|---|
| A rota 2 do re-pass EXECUTA antes de verificar | `PLAN-193/repass-ga/run-ga-repass.sh`: o `npx -y "$CODEX_PKG" --version` (só o cache é trocado; nada de `.npmrc` vazio nem `--ignore-scripts`) vem antes do oráculo `--verify-codex-pin "$CODEX_LAUNCHER"` | confere |
| O shim da rota 2 executa o LANÇADOR, não o payload verificado | o mesmo arquivo: o shim faz `exec "$CODEX_LAUNCHER"`, mesmo tendo o oráculo devolvido o `path` verificado | confere |
| A âncora no import do `spool_writer` nasce tarde nos guards críticos | `check_canonical_edit.py`: nas primeiras 80 linhas só há imports da stdlib, mais `gpg_verify` e `sentinel_signers` (`:63`, `:73`), e nenhum dos dois importa `audit_emit` no topo; `audit_emit` só entra DENTRO de função (`:658`, `:725`, `:1429`, `:1448`, `:1460`). `check_agent_spawn.py:52-62` importa `contract`, `adapters.claude`, `team`, `redact` e `subagent_dispatch`, e nenhum deles importa `audit_emit`/`spool_writer` no topo (conferido um nível) | confere |
| O wrapper mantém o PID do processo | `_python-hook.sh:413`: `exec "$FOUND_PY" "$HOOK_SCRIPT" "$@"` ⇒ o instante de início do processo no kernel inclui o tempo do wrapper | confere |
| O `atexit` roda ANTES do flush do stdout | **medido** (CPython 3.9.6 do sistema): processo-filho com stdout em pipe, um `print` do JSON de decisão e um `atexit` de 1,5 s ⇒ o 1.º byte só chega ao leitor em **1,52 s**, junto da saída do processo | confere: com stdout em pipe, a decisão de um hook que não chama `flush` só sai DEPOIS da drenagem de saída |
| Perda real de `agent_spawn` sem gatilho | `audit_log.py:1324-1328`: num `FileLockTimeout` a linha vai só para o breadcrumb `lock timeout (stale?) would-log=` | confere |
| O `npm audit signatures` dá falso verde; o `sigstore.verify` com política serve | relatório da W0.6 §2: V-T2/V-R1 (payload adulterado ⇒ exit 0), V-P3 (atestado removido ⇒ exit 0), V-N1/V-N3 (cache quente sem rede ⇒ exit 0), S-11 (atestado de OUTRO repositório, sem política ⇒ VERIFIED); S-02..S-12 com política: verde só no íntegro | confere |
| Literais da identidade e ids imutáveis | W0.6 §4: SAN `https://github.com/openai/codex/.github/workflows/rust-release.yml@refs/tags/rust-v<X.Y.Z>`; emissor `https://token.actions.githubusercontent.com`; id do repositório `965415649`; id do dono `14957082` | confere |
| 2.º host, alias de plataforma, executáveis irmãos e tetos | W0.6 §3, §5, §6: cache TUF em `tuf-repo-cdn.sigstore.dev`; `@openai/codex-darwin-arm64` é ALIAS (404 como pacote); executáveis fora do sha pinado (`bin/codex-code-mode-host`, `codex-path/rg`, `codex-voice-host`, `zsh`, dylibs); tetos 2× o maior medido | confere |
| O plano chama o verificador de «livre» e a linha do manifesto ADR-192 no mapa não cita a W3 | plano `:848` («0, livre»); mapa de colisões `:230` (W7, W7b, W10, W5c) | confere ⇒ diverge do AMEND-1 §4.1 |
| O registro não tem guarda contra escrita do próprio agente | AMEND-1 R-5 diz «a conferir». O sandbox está `enabled: false` (`.claude/settings.json:8`). A busca rápida do sintetizador não achou guarda dedicada à família do log de auditoria em `check_*.py` | **inconclusivo** (a conferir no pacote 1b, ajuste 41) |

**Não refeitos pelo sintetizador** (aceitos como medição ou inferência de crítico, com a etiqueta deles):

- o `-k gc` casando o NOME do módulo (Critic-A mediu, e é a semântica documentada do `pytest -k`);
- `pid`/`wall_ns` sobrevivendo no log canônico, 50 de 50 (Critic-A);
- o ritmo de ~15,8 mil travas por dia e o retorno a ~150 mil em 3 a 4 semanas (inferências do rascunho e
  do Critic-C).

## 1. Vereditos por onda e estado do VETO

| onda | veredito | VETO (Critic-B) | o que libera / o que falta |
|---|---|---|---|
| **W2** | **PROCEED** (`design-coherent`) — os três críticos | **RETIRADO**, condicionado a MF-R2-W2-1..4 | A W2 **libera sem esperar a W3**. As condições do VETO e os must-fix de execução (lista §3(a)) são aplicados pelo CEO no plano e no AMEND-4 SEM nova rodada; quem confere a aplicação é o rail do pacote (V2). O SIGN da W2 continua depois do LAND da W2.0 (cura da condição 67; vaga = decisão pendente 1) e na vaga da W2 (depois da W7a do PLAN-183). |
| **W3** | **RUN-ANOTHER-ROUND** — os três críticos | **LEVANTADO** | A W0.6 mudou a arquitetura da decisão de confiança, e o rascunho é anterior a ela. A rodada 3 exige o AMEND-1 revisado (lista §3(b)) e a escolha do Owner entre os empacotamentos (i) e (ii) (decisão 3). Nenhum P0; nenhuma afirmação FALSA no PLANO (as duas falsas estão no RASCUNHO: §4.1 «stdlib-only» e §4.4 «MESMO host»). |
| **W5c** | PROCEED (rodada 1) | RETIRADO (rodada 1) | inalterada; fora do escopo da rodada 2 |

**Veredito da rodada: RUN-ANOTHER-ROUND**, só para a W3. A rodada 3 é a **ÚLTIMA** pela regra de parada
pré-registrada (no máximo 3 rodadas; NO-GO só por P0 ou afirmação FALSA no plano). Se ela não fechar, o
impasse vai ao Owner por múltipla escolha.

Se o Owner escolher «confiança no registro» na decisão 3, a W3 vai direto ao Owner (ESCALATE), sem
rodada 3.

**Nota de processo (DEBATE-SCHEMA §12.3).** A W2 convergiu por VEREDITO na rodada 2. O portão M1 do
Red Team é do orquestrador e dispara por convergência de Jaccard dos conjuntos de risco entre rodadas,
que aqui mudaram quase por inteiro. O sintetizador não o calculou, porque o script pode gravar evento.
O CEO decide se o roda antes de marcar a W2. A checagem externa da verdade do desenho da W2 continua
sendo o rail V2.

## 2. Divergências resolvidas

Regra: o portador de VETO (Critic-B) prevalece no domínio do VETO, salvo evidência no disco que o
refute.

### W2

**(a) Âncora do prazo de saída (R2-1).**
- **Critic-A:** a âncora no import basta, com o resíduo declarado, mais um censo AST como nice-to-have.
- **Critic-B (VETO):** o import NÃO basta; vale a mais cedo entre o import e um marco de início do
  processo.
- **Critic-C:** início do PROCESSO lido do kernel (stdlib, `ctypes`/`sysctl` no macOS e `/proc/self/stat`
  no Linux), com o import como fallback; o censo AST fica como alternativa.
- **Evidência:** o disco CONFIRMA o Critic-B, porque o import do `audit_emit` é tardio exatamente nos
  guards mais críticos (§0).
- **Decisão:** o Critic-B prevalece, com o mecanismo do Critic-C, que é um marco de início do processo e
  não toca os hooks canônicos. Âncora = `min(instante do import, início do processo no kernel)`. Valor
  inválido, ausente ou no futuro ⇒ vale o do import, com o resíduo declarado. Assim o erro só vai para
  «menos tempo». O controle S1 usa um guard sintético com import TARDIO depois de trabalho simulado, no
  molde do `check_canonical_edit.py`. O censo AST com «armar o prazo no `main`» fica como alternativa
  só se a leitura do kernel não for viável, porque toca hooks canônicos e pesa no teto de paths.

**(b) Observabilidade da trava canônica presa (R2-4).**
- **Critic-B (VETO):** sinal em ≤ T, pré-registrado (proposta ≤ 1 h), sem volume por saída, com controle
  positivo. Motivo: o spool é PRÉ-cadeia, e o tempo fora da cadeia é janela de adulteração sem elo
  quebrado.
- **Critic-A:** a contenção fica invisível depois da cura; quer a taxa de `exit_deadline_skip` na W0.5 e
  o G6.
- **Critic-C:** limiar operacional das travas.
- **Decisão:** convergem; o Critic-B fixa o requisito. Exemplo de mecanismo, a cargo do builder: no salto
  por prazo, UM `stat` do log canônico; se o log não avança há mais que T, sai um breadcrumb `STARVED` com
  gate e taxa limitada, no formato que `ceo-diagnose.py`/`status.py` já contam. Isso não contradiz o C17
  da rodada 1: é breadcrumb, não evento por arquivo, e não toca o `audit_emit.py`.

**(c) Instrumento ligado de perda real (R2-3).**
- **Critic-A e Critic-B:** o G6 entra NA W2.
- **Critic-B:** mais o **G7**, contagem datada de `would-log` (`audit_log.py:1324-1328`) com controle
  positivo.
- **Decisão:** entram os dois, como verificador só-leitura fora de hook, rodado no pós-LAND e no nightly.
  `record_id` em `.malformed.*`, `.quarantined.*` ou `.test-origin.*` conta como quarentenado, não como
  perdido.

**(d) W2.6 com PID vivo.**
- **Plano:** «recusa». **AMEND-4 §5.2:** «PID vivo ⇒ pula a família; mtime < 10 min ⇒ recusa a execução».
- **Critic-B e Critic-C** aceitam o AMEND-4. O Critic-C acrescenta: spool ativo ou `.draining.*` com PID
  vivo ⇒ recusa a execução inteira (prova positiva de emissor vivo deste projeto, porque trava aberta e
  `flock` não mudam o mtime).
- **Decisão:** texto do AMEND-4 + o acréscimo do Critic-C. A pré-condição continua sendo decisão do Owner
  (decisão 2).

**(e) A W2.6 sob a regra de travas T1.**
- **Critic-C:** o estoque de travas volta à célula «~150 mil» em semanas, então a W2.6 é RECORRENTE. Quer
  limiar operacional (≥ 100 mil ⇒ o `/ceo-boot` recomenda rodar de novo) e gatilho numérico da T2
  pré-registrado.
- Os outros críticos não divergem. O Critic-A pede o esperado por célula sob T1 e o gatilho da T2 escrito
  ANTES de rodar.
- **Decisão:** aceito. A recorrência é custo operacional do Owner (decisão 2).

**(f) Drain oportunista ANTES da decisão (só o Critic-A).**
- É a mesma classe («trabalho longo dentro de guard vira allow»), antes do stdout: o drain oportunista
  lista o diretório e pode esperar nas travas por PID.
- **Decisão:** mantido como célula da W0.5, com regra pré-registrada: se o tempo entre a decisão e o
  stdout escrito passar da margem, a mesma regra de prazo vale para o drain oportunista, no pacote da W2.

**(g) Entrega da decisão e flush do stdout.**
- **Fato medido (§0):** com stdout em pipe, a decisão só sai depois do `atexit`.
- Três críticos convergem em medir a semântica do harness: Critic-A MF-4 (calibração com o harness
  REAL), Critic-B NTH 1 (`flush` antes da drenagem) e Critic-C NTH 3 (fechar o stdout antes).
- **Decisão:**
  - o auxiliar de saída faz `sys.stdout.flush()` e `sys.stderr.flush()` ANTES da drenagem. É barato e
    não substitui o prazo;
  - a W0.5 ganha a célula de calibração: 2 chamadas `claude -p`, CC congelado, hook sintético que
    imprime BLOCK e atrasa a saída além do timeout, contra o mesmo hook saindo rápido, com e sem o
    `flush`;
  - sem a calibração, S1 é declarado no material assinado como prova contra um MODELO do harness.

### W3

**(h) Empacotamento do sigstore.**
- **Critic-B (VETO):** prefere (ii), `sigstore` em versão exata com lockfile de toda a árvore sob o
  manifesto ADR-192, `npm ci --ignore-scripts` em staging novo.
- **Critic-C:** recomenda o mesmo, a opção (b).
- **Critic-A:** neutro, desde que a versão e a integridade sejam FIXAS.
- **Decisão:** o Owner escolhe (decisão 3); recomendação do CEO: **(ii)**. Motivo: o código que toma a
  decisão criptográfica fica governado pelo repositório, e não pelo npm do Homebrew. A (i) quebra num
  upgrade do npm; é fail-closed, então perde vivacidade, não segurança.

**(i) O ramo «dependência recusada» da decisão 3.**
- **Critic-A:** pré-registrar os dois ramos; recusada ⇒ A-15 aceita e DECLARADA.
- **Critic-B (VETO):** «confiança no registro» deixou de ser resíduo aceitável, porque a W0.6 mediu um
  mecanismo que a dispensa (S-02..S-12); escolhê-la mantém o VETO e vira ESCALATE.
- **Decisão:** o Critic-B prevalece; a W0.6 é a evidência A FAVOR dele. O AMEND-1 pré-registra os testes
  só do ramo escolhido, (i) ou (ii). O ramo recusado aparece como rota de ESCALATE, citando a W0.6 (o
  comando do npm não detecta a A-15).

**(j) Promoção (Fase 2).**
- **Critic-B (VETO):** conferir a ÁRVORE instalada inteira contra o manifesto de membros do tarball
  verificado, OU instalar a partir dos bytes verificados.
- **Critic-C:** instalar a partir dos bytes verificados, com `--offline` sobre o cache do staging, e
  gravar o manifesto por membro.
- **Decisão:** os DOIS. O mecanismo é o do Critic-C, com prova de zero busca no registro: a Fase 2 roda
  sob proxy morto. O P-01 é o do Critic-B: árvore inteira, lançador e plataforma, por nome, tamanho e
  sha256, sem executável extra. Custo: uma passada de hash (~333 MB), fora de hook.

**(k) Rota 2 do corte.**
- O AMEND-1 diz «inverter OU declarar» (R-12). O Critic-B (VETO) e o Critic-C exigem inverter.
- **Decisão:** inverter, como pré-condição da W3.6. Com a W3.6 antes do corte, a rota 2 vira o caminho
  PADRÃO de todo corte, na sessão em que o GPG do Owner está desbloqueado.

**(l) Rollback sem rede (só o Critic-C).**
- Reter o cache verificado das 2 últimas versões, ou declarar.
- **Decisão do CEO:** declarar o R-16 agora («rollback exige rede; sem rede, o rail bloqueia até haver
  rede»; a via de instalação da versão do manifesto também depende de rede). O cache retido vira
  follow-up. Isso cumpre o «ou» do próprio crítico.

**(m) Check da CLI na W3.1 (Critic-A).**
- A flag vale para o Check de sucesso e para a W3.6.
- O Check da W3.1 cobre o período ATÉ o LAND (0.156.1, só-manifesto) e fica sem flag, com o escopo
  escrito no item.

## 3. As duas listas de must-fix que restam

### (a) W2 — condições do VETO e must-fix de execução

O CEO aplica estes itens no plano e no ADR-055-AMEND-4, sem nova rodada. Os quatro primeiros são as
condições do VETO.

1. **MF-R2-W2-1 (VETO):** trava canônica presa vira sinal em ≤ T (≤ 1 h, pré-registrado), sem volume
   por saída, com controle positivo: um portador externo segura a trava por T e o sinal aparece; um
   vermelho prova que o G3 de 24 h sozinho não basta (§2(b)).
2. **MF-R2-W2-2 (VETO):** âncora do prazo = `min(import, início do processo no kernel)`, com fallback
   declarado. O S1 usa um guard sintético com import tardio (§2(a)).
3. **MF-R2-W2-3 (VETO):** G6 (perda real, só-leitura, fora de hook, pós-LAND e nightly, quarentenado ≠
   perdido) e G7 (`would-log` datado), os dois com controle positivo, entram NA W2 (§2(c)).
4. **MF-R2-W2-4 (VETO):** reconciliar o plano com o AMEND-4. Onde divergirem, vale o rascunho:
   - W2.2-bis com `T_min` = menor timeout registrado (3 s hoje) e teste de deriva;
   - W2.3 só pela compactação;
   - W2.4 CONDICIONAL, fora do pacote base, e o Check `-k gc` sai;
   - mutantes da W2.5 = M-a..M-d;
   - predicado da W2.6 conforme §2(d);
   - célula (c) da W2.2 = «auxiliar de saída chamado no atexit E no sinal».
5. **Seletores:** o módulo de teste é renomeado para um nome que não contenha nenhum seletor (ex.:
   `test_spool_state_amend4.py`). A guarda de seletor afirma que cada `-k` casa SÓ os testes do próprio
   item, e o Check da W2.4-bis ganha um seletor dos testes novos (hoje é verde com os 120 existentes).
6. **Check de sucesso da W2 reescrito (Critic-A MF-2):**
   - o teto de 1.000 conta só journals; as travas vão à parte, sem limiar de segurança;
   - o H1 com |D| é um script que lê `pid`/`wall_ns`, com `|D|_min` ≥ 200 pré-registrado (abaixo dele,
     reprova);
   - o carimbo do LAND sai do commit, em ISO validado; marcador literal ⇒ saída ≠ 0;
   - o braço de timeouts passa a se chamar «guarda de regressão»;
   - as regex são o texto do AMEND-4 §4.7 (`fullmatch` + `re.ASCII`);
   - «decisão perdida» lê o veredito gravado pela W0.5, ou o texto sai.
7. **Check da W2.0:** aponta o teste de barreira por node id e o censo AST. O LEDGER guarda a execução
   VERMELHA no HEAD antes do patch (comando + sha).
8. **`flush` antes da drenagem e calibração com o harness real** (§2(g)).
9. **Estatística e esperado por célula sob T1 (Critic-A MF-5, Critic-C MF-4):**
   - medir primeiro a taxa p̂ de perda de decisão no HEAD; escolher N com 3/N ≤ p̂/10;
   - p95 só com N ≥ 100 (senão p90);
   - sem spool: razão p95 cheio/vazio ≤ 1,2;
   - com spool e ~150 mil travas: decisão entregue e prazo respeitado, razão NÃO exigida;
   - gatilho numérico da T2 escrito ANTES de rodar: na célula «~150 mil travas» com ≥ 9 concorrentes,
     `exit_deadline_skip` > 0 ou p95 de saída acima do orçamento; ou W2.6 mais de 1× por mês.
10. **Célula da W0.5 para o drain oportunista ANTES da decisão**, com a regra pré-registrada (§2(f)).
11. **W0.5 mede mais duas coisas (Critic-C MF-3):** o intervalo desde o INÍCIO DO WRAPPER até a âncora; e
    a vivacidade da perna 3 sob rajada (contagem e idade dos spools órfãos com conteúdo depois da carga e
    depois de N emissores; `K_MAX` = 100).
12. **Composição da cadeia no estresse (Critic-A MF-7):** N ≥ 1.000 elos, com ≥ 100 `agent_spawn`, ≥ 100
    lotes de drain (`_drain_epoch`), ≥ 50 transições ADJACENTES entre classes e ≥ 1 rotação no meio.
13. **Guardas mecânicas (Critic-A MF-9):**
    - inode de cada `*.lock` estável do 1.º ao último uso no estresse;
    - censo dos abridores de `audit-pending.*` como teste;
    - células do sinalizador: o próprio `.draining` consumido por OUTRO drainer; spool próprio em
      quarentena ⇒ uma tentativa só; SIGTERM honra o caminho rápido e o prazo;
    - `_OWN_DRAIN_PENDING` fail-safe: liga antes do rename, desliga só depois da remoção confirmada, com
      teste de exceção no meio (Critic-B NTH 2).
14. **T1 operacional (Critic-C MF-4, Critic-A MF-8):**
    - o check do `/ceo-boot` conta as travas, e ≥ 100 mil ⇒ recomenda a W2.6;
    - conta spool órfão com conteúdo de QUALQUER idade, como taxa;
    - escreve no máximo uma linha por execução;
    - a W2.6 é declarada RECORRENTE sob T1;
    - o G1 ganha controle positivo também para o H1 e cadência de «3 execuções em dias DISTINTOS e
      consecutivos de uso» (Critic-C NTH 2).
15. **Valores pré-registrados (R2-5, aceitos pelos três):**
    - ε = 0,01, só com `|D|_min` e o vermelho do H1 MEDIDO no HEAD (esperado F ≥ 0,9);
    - `EXIT_MARGIN_S` = 1,0 s e prazo de 2,0 s, como valores INICIAIS;
    - regra: margem ≥ p99 medido × 1,5; se não couber, encolhe o PRAZO, nunca a margem. A medição é
      declarada como da máquina do Owner, porque a CI é mais lenta;
    - limite de 2.000 `stat` no check;
    - Linux de vida longa como gatilho da T2.
16. **R2-7:** o slug do ADR fica, por anti-churn; os três críticos são neutros. Entram o teste dourado dos
    construtores de caminho (byte a byte contra o HEAD) e a asserção, no estresse, de que journals COM
    conteúdo foram produzidos antes do drain (Critic-A NTH 2 e 3).

### (b) W3 — o que o AMEND-1 revisado e o plano precisam conter para a rodada 3

1. **V-5 = `sigstore.verify` COM política** (MF-R2-W3-1):
   - `certificateIdentityURI` exato = SAN do `rust-release.yml` com a tag `rust-v<X.Y.Z>` da versão BASE;
   - `certificateIssuer` exato = `https://token.actions.githubusercontent.com`;
   - `certificateOIDs` com os ids imutáveis do repositório (`965415649`) e do dono (`14957082`);
   - sobre os bundles que o PRÓPRIO verificador buscou;
   - literais em constantes canônicas com teste;
   - nunca `npm audit signatures`.
2. **Os DOIS bundles (lançador e plataforma) exigidos pelo verificador:** a A-12 passa a ser dele (V-P3).
3. **A-14 e A-15 viram RECUSA:** sai «aceita e declarada» do AMEND-1 e da W3.4 do plano.
4. **Vínculo:** sha512 do tarball baixado = digest do `subject` do bundle VERIFICADO, lido dos MESMOS
   bytes passados ao verificador; o `dist.integrity` vira só cruzamento (MF-R2-W3-3).
5. **Caches do npm e do TUF NOVOS a cada execução**, com asserção de vazio no início; o cache quente vira
   célula (V-N1, V-N3).
6. **Lista FECHADA de hosts:** o registro e `tuf-repo-cdn.sigstore.dev`. A A-03 e o §4.4 («MESMO host»)
   são corrigidos.
7. **Tetos medidos:** packument ~33,6 MB; atestado ~30,3 KB; tarball comprimido ~268,6 MB; membro
   `bin/codex` ~483,1 MB; descomprimido total ~666 MB.
8. **§4.1 reescrito:**
   - orquestrador Python + auxiliar `node` para a assinatura, como exceção NOMEADA ao «stdlib-only»;
   - `node` por caminho absoluto, com versão mínima;
   - versões de `node`, npm e sigstore, sha do lockfile (ou do módulo) e digest da raiz TUF na linha do
     registro e no evento HMAC (`signature_mode`);
   - trocar o verificador é «instrumento mudou»;
   - `verifier_sha256` e o sha do lockfile no conjunto permitido do H-07 (Critic-B NTH 6).
9. **Empacotamento conforme a decisão 3:**
   - (ii): `sigstore` em versão exata, lockfile de integridade de toda a árvore sob o ADR-192,
     `npm ci --ignore-scripts` em staging novo e ambiente npm montado do zero;
   - (i): módulo interno do npm com lista canônica de versões e shas de arquivo, e recusa fora dela;
   - os testes do ramo escolhido ficam pré-registrados (§2(h), §2(i)).
10. **Células novas da fronteira do verificador**, todas recusa (1), nunca INFRA (Critic-A MF-11):
    - `node` ausente;
    - sigstore ausente, movido ou com versão ≠ a fixada;
    - saída não-JSON;
    - código ≠ 0;
    - tempo excedido;
    - chamada SEM política (mutante: S-11 vira VERIFIED ⇒ o teste fica vermelho);
    - cache quente.
11. **Duas camadas de teste, com o lugar pré-registrado (Critic-A MF-12):**
    - camada 1, no CI: stub do subprocesso, que prova a FIAÇÃO fail-closed;
    - camada 2, criptografia REAL e offline: bundles reais da 0.156.1 e da 0.160.0 (~15 KB cada), raiz de
      confiança fixada, mutantes S-03..S-09, S-11 e S-12; verde só no íntegro com a política certa. Roda
      no CI com `node` e sigstore fixos, ou na bateria do LAND com SKIP = falha;
    - fixture sintética só nas células de forma (A-05, A-16, A-17).
12. **Guarda de rede dos FILHOS (Critic-A MF-13):** proxy morto em `HTTPS_PROXY`/`HTTP_PROXY` e
    `NO_PROXY` vazio, com controle POSITIVO de que um fetch do `node` filho falha. Se o ambiente não
    prender o filho, o builder troca o mecanismo, mantendo o controle positivo. A guarda de socket do
    Python continua para o hook (H-12).
13. **Promoção a partir dos bytes VERIFICADOS + P-01 da árvore inteira** (§2(j); MF-R2-W3-4):
    - o registro grava o manifesto sha256 por membro;
    - §2 e R-6: o hook confere só o `bin/codex` a cada invocação; os irmãos são conferidos na promoção; a
      troca deles em tempo de execução é resíduo de mesmo UID;
    - um teste documenta esse resíduo (Critic-A NTH 4).
14. **Quiesce na promoção (Critic-C MF-8):** recusa se algum processo executar o payload ou os auxiliares
    do prefixo global, conferido por `lsof`/`ps` sobre o caminho, nunca `pgrep -f`. A promoção é
    declarada janela curta de manutenção, com as rodadas de rail paradas.
15. **Rota 2 INVERTIDA no kit da 1.4.3 (MF-R2-W3-6; Critic-C MF-5), pré-condição da W3.6:**
    - materializar sem executar: `npm install --prefix <OUT>`, `--ignore-scripts`, ambiente npm do zero,
      registro fixo, cache novo, versão exata do manifesto;
    - oráculo sem flag;
    - shim com `exec` do `path` VERIFICADO;
    - só então o `--version`;
    - controle: lançador plantado num registro redirecionado NUNCA executa, e um espião prova zero
      execução antes do oráculo;
    - o R-12 sai dos resíduos;
    - o argv fixo (modelo, esforço, `--ignore-user-config`) é sondado também na 0.156.1 do manifesto
      (Critic-C NTH 5).
16. **Registro protegido contra escrita do PRÓPRIO agente (MF-R2-W3-5):**
    - Edit, Write e Bash, inclusive acréscimo por redirecionamento;
    - controle positivo: escrita no formato do agente ⇒ BLOCK;
    - o «a conferir» do R-5 é resolvido no pacote. Se não houver guarda dedicada à família do log (§0,
      inconclusivo), o pacote cria a guarda do registro e registra a lacuna da família do log como item
      próprio.
17. **`SBOM.md` (MF-R2-W3-7):**
    - declara a dependência de tempo de operação (`node` + sigstore-js, versão e integridade) como
      ferramenta de mantenedor, fora do runtime dos hooks;
    - o «stdlib-only» fica escopado ao runtime dos hooks, no MESMO pacote;
    - o `CLAUDE.md` §3 só muda no fechamento, dentro da poda (risco 9).
18. **Manifesto ADR-192 e paths (MF-R2-W3-8; Critic-C MF-9):**
    - verificador `.py`, auxiliar JS e lockfile DENTRO do manifesto;
    - linha do `gate-scripts-manifest.txt` no mapa: + W3 (pacote 1a), «nunca em paralelo» com W7, W7b,
      W10 e W5c;
    - pacote 1 dividido em 1a (verificador + auxiliar + lockfile + testes + `SBOM.md` + manifesto) e 1b
      (AMEND-1 + `check_pair_rail.py` + testes do hook + T-8 + guarda do registro, se couber);
    - ordem: 1b antes de 1a, porque o verificador reaproveita funções e constantes do núcleo (AMEND-1
      §4.1);
    - oráculo `--is-canonical` no auxiliar JS na abertura.
19. **Checks da CLI (Critic-A MF-14):**
    - o Check de sucesso e o da W3.6 usam `--verify-codex-pin --allow-auto-pin` e afirmam
      `pin_source == "registry"` para versão FORA do manifesto;
    - um literal só, o do código (`registry`);
    - o Check da W3.1 fica sem flag, com escopo «até o LAND» escrito (§2(m)).
20. **Censo das células (Critic-A MF-15):**
    - arquivo de teste do verificador nomeado AGORA e posto no Check da W3.4;
    - um teste-censo liga cada id (A-01..A-24, P-01..P-02, H-01..H-12, C-01..C-02, R-01..R-04 e as
      novas) a ≥ 1 teste;
    - W3.3 e W3.4 com seletores distintos, que não sejam substring do nome do módulo (`pin`, `auto`,
      `rail`, `pair` e `check` casam `test_check_pair_rail_auto_pin.py`).
21. **Rollback:** R-16 declarado (§2(l)).
22. **Fiação e higiene do hook:**
    - `_emit_audit()` ligado ao `emit_generic` no pacote 1b (achado do AMEND-1, confirmado);
    - o sumidouro de teste honrado só no modo de teste (Critic-B NTH 5);
    - a mensagem do Gate 4 da fase 6 nomeia a rota 2 quando o global está auto-pinado, com nota de
      operador (Critic-B NTH 7; Critic-C NTH 6);
    - canário sobre diff SINTÉTICO fixo (Critic-B NTH 8);
    - política de nova tentativa do canário pré-registrada (Critic-A NTH 5).
23. **As decisões 3 a 6 escritas no AMEND-1 assim que saírem;** a decisão 3 do plano reescrita (§6).

## 4. Consensus findings (2+ críticos)

1. **R2-C1 — A W2 está `design-coherent`.** Os três críticos. O que resta é prova, texto e
   observabilidade, não desenho. → §3(a).
2. **R2-C2 — Plano e AMEND-4 divergem em W2.2-bis, W2.3, W2.4, W2.5 e W2.6, e o Check da W2.4 é
   vermelho ou vácuo por construção.** Os três. MEDIUM. → §3(a) itens 4 e 5.
3. **R2-C3 — A âncora no import é tardia nos guards reais.** Critic-B e Critic-C; o Critic-A aceita o
   resíduo. HIGH. Disco confirma (§0). → §2(a).
4. **R2-C4 — Depois da cura, a contenção e o travamento ficam invisíveis.** Critic-A (R-QA2-5), Critic-B
   (R2-SEC5), Critic-C (limiar operacional). MEDIUM-HIGH. → §2(b).
5. **R2-C5 — O G6 entra na W2.** Critic-A e Critic-B. → §2(c).
6. **R2-C6 — Sob T1, a célula «~150 mil travas» é o regime permanente.** Critic-A (R-QA2-3, razão
   vermelha por construção) e Critic-C (R2-DO4). → §2(e), §3(a) item 9.
7. **R2-C7 — A semântica do harness diante do prazo não foi medida.** Critic-A MF-4, Critic-B NTH 1/Unseen
   1, Critic-C NTH 3; ordem do `atexit` medida (§0). → §2(g).
8. **R2-C8 — O AMEND-1 contradiz a W0.6** («stdlib-only», «MESMO host», `dist.integrity` cru, A-15
   «declarada», A-12 delegada ao npm). Os três. HIGH. → §3(b) itens 1 a 8.
9. **R2-C9 — A promoção reabre a janela registro → disco para os executáveis irmãos.** Critic-B
   (R2-SEC2) e Critic-C (R2-DO5). HIGH. → §2(j).
10. **R2-C10 — A rota 2 do corte executa antes de verificar e roda o lançador.** Critic-B (R2-SEC3) e
    Critic-C (R2-DO1). HIGH. → §2(k).
11. **R2-C11 — A decisão 3 do plano, como está escrita, induz à variante mais fraca.** Critic-A MF-16 e
    Critic-B R2-SEC1. HIGH. → §6, decisão 3.
12. **R2-C12 — A W3 precisa de declaração no `SBOM.md` e de reconciliação com o ADR-192.** Critic-B
    (MF-R2-W3-7/8) e Critic-C (R2-DO7, R2-DO9). → §3(b) itens 17 e 18.
13. **R2-C13 — Checks da W3 vácuos ou vermelhos depois da W3.6**, e literal `registro`/`registry`
    divergente. Critic-A; o Critic-C tem a nota do Gate 4. → §3(b) item 19.

## 5. Single-agent insights kept / rejected or deferred

**Mantidos:**

- **Critic-B:** MF-R2-W2-1..4 e MF-R2-W3-1..8 (VETO). O R-1 e o R-12 recusados como resíduo. Os NTH 2,
  5, 6, 7 e 8.
- **Critic-A:**
  - os Checks vácuos (`-k gc` casa o módulo; `'2' < '<'` no `awk`; W2.0 e W2.4-bis verdes hoje);
  - as duas camadas de teste da criptografia;
  - a guarda de rede dos filhos;
  - o censo das células;
  - o drain oportunista pré-decisão;
  - a composição da cadeia;
  - as guardas de inode e do censo dos abridores.
- **Critic-C:**
  - âncora pelo kernel;
  - quiesce;
  - W2.6 recorrente com limiar operacional;
  - sondar o argv também na 0.156.1;
  - o intervalo desde o wrapper e a vivacidade da perna 3 na W0.5.

**Rejeitados ou adiados:**

- **Critic-A, R2-1 «import basta, com resíduo»:** REJEITADO (o VETO prevalece; disco, §0). O censo AST
  dele fica como fallback do §2(a).
- **Critic-A MF-16, ramo «dependência recusada ⇒ A-15 aceita e declarada»:** REJEITADO como desenho; vira
  rota de ESCALATE (§2(i)).
- **Critic-C MF-10, cache verificado retido para rollback offline:** ADIADO a follow-up; o R-16 é
  declarado (§2(l)).
- **Critic-C MF-2, alternativa do censo AST com «armar no `main`»:** mantida só como fallback (toca hooks
  canônicos).
- **Critic-C NTH 4 (`--quarantine --rollback-to`) e Critic-A NTH 6 (lint geral de seletores):** ADIADOS.
  O lint vale como regra de texto no plano (§3(a) item 5).
- **R2-7 (trocar o slug do ADR):** NÃO adotado (anti-churn; os três são neutros).

## 6. Decisões pendentes do Owner (atualizadas pela rodada 2)

1. **Vaga da cura da condição 67 (W2.0).** Agora é o ÚNICO pré-requisito do Owner para o SIGN da W2, que
   saiu PROCEED. **Recomendação (inalterada):** pacote canônico PRÓPRIO, landado antes do SIGN da W2, como
   1.º pacote na vaga da W2 ou na primeira vaga que abrir antes. A aposentadoria da condição 67 vai no
   `CHANGELOG.md` do corte.
2. **Pré-condição e RECORRÊNCIA da W2.6.** **Recomendação:**
   - trocar «todas as sessões do Claude fechadas» por «todas as sessões DESTE projeto fechadas»;
   - predicado do AMEND-4: PID vivo ⇒ pula a família; mtime < 10 min ⇒ recusa a execução; spool ativo
     ou `.draining.*` com PID vivo ⇒ recusa a execução;
   - aceitar que, sob a regra T1, a W2.6 é manutenção RECORRENTE, a cada ~2 a 4 semanas de uso intenso,
     quando o `/ceo-boot` acusar ≥ 100 mil travas;
   - rodar a 1.ª já.
   Se a W2.6 precisar rodar mais de 1× por mês, isso é gatilho da T2 (pacote de kernel próprio).
3. **(REESCRITA) Empacotamento do verificador de assinatura da W3.** A W0.6 mostrou que o comando
   `npm audit signatures` NÃO serve (falso verde com payload adulterado, atestado removido, atestado de
   outro repositório e cache quente). Mostrou também que a biblioteca `sigstore` chamada COM política de
   identidade SERVE: verde só no íntegro; recusa toda adulteração e toda identidade divergente. A
   escolha agora é o EMPACOTAMENTO:
   - **(i)** o módulo interno do npm, com lista canônica de versões permitidas e shas de arquivo, e recusa
     fora dela. Não é API pública; muda de lugar ou de versão num upgrade do npm do Homebrew; a falha é
     fail-closed, então perde vivacidade, não segurança;
   - **(ii)** `sigstore` em versão exata, com lockfile de integridade de toda a árvore sob o manifesto
     ADR-192, instalado com `npm ci --ignore-scripts` em staging novo. É código de terceiro, mas
     governado pelo repositório.

   Nos dois casos o verificador passa a depender de `node`, e o `SBOM.md` declara isso.
   **Recomendação: (ii)**, a preferida do portador do VETO e de outro crítico. Escolher «confiança no
   registro» mantém o VETO levantado e vira **ESCALATE**: a W3 vai ao Owner por múltipla escolha, sem
   rodada 3.
4. **Sentinela de qualidade.** **Recomendação (inalterada):** (ii) a W3 landa SEM sentinela, declarada.
   Os três críticos aceitam o R-2 declarado; o gatilho do ADR-111 §2 fica preservado como NÃO AVALIÁVEL
   até haver corpus.
5. **Modelo e esforço fixos no argv do rail.** **Recomendação:** `gpt-6-astra` + `xhigh`, condicionado ao
   re-teste da Q11. Acréscimos da rodada 2:
   - o par e as flags (`--ignore-user-config` incluída) precisam existir também na 0.156.1, que o corte
     usa;
   - na mesma decisão, se os adopters herdam o par fixo ou mantêm o padrão da conta.
6. **Evidência da aceitação automática.** **Recomendação (inalterada):** evento na cadeia HMAC. O
   Critic-B só aceita «evidência só no registro» por decisão escrita do Owner (R-3).
7. **Para ciência, sem decisão:**
   - a W3 cresce para 1,6 a 2,8 M tokens em 3 a 4 sessões (pacotes 1b, 1a e 2, mais o de kernel do
     evento), e a W3.6 (Codex atualizado) depende de todos eles e da rota 2 invertida no kit;
   - cada promoção é uma janela curta de manutenção, com as rodadas de rail paradas (quiesce);
   - a calibração da W2 custa 2 chamadas `claude -p` na vez da W2 (freio Q1);
   - o rollback da W3 exige rede (R-16).

## 7. Plan adjustments

O CEO aplica estas edições. Itens 1 a 22 (plano e AMEND-4, W2) sem nova rodada; itens 23 a 52 (plano e
AMEND-1, W3) antes da rodada 3.

**PLAN-194 — transversal e W2**

1. *Frontmatter `budget_tokens`:* W2 de 1,0 a 1,8 M; W3 de 1,6 a 2,8 M em 3 a 4 sessões (1b, 1a, 2 + kernel); W7 +100 a 150k (rota 2 invertida); rodada 3 com 150 a 300k.
2. *Frontmatter `external_wait`:* W2.6 recorrente (operação do Owner, decisão 2); janela de manutenção de cada promoção da W3.
3. *Approach item 4 e «Cláusula de bloqueio»:* W2 PROCEED na rodada 2 (VETO retirado com condições), liberada do portão do debate; W3 BLOQUEADA até a rodada 3, a ÚLTIMA.
4. *W2, parágrafo «BLOQUEADA»:* reescrever como «LIBERADA pelo PROCEED da rodada 2», com MF-R2-W2-1..4, a W2.0 antes do SIGN e a vaga inalterada.
5. *W2, «Paths»:* módulo de teste renomeado sem seletor como substring (ex.: `test_spool_state_amend4.py`); W2.4 fora do pacote base.
6. *W2.0:* Check por node id do teste de barreira + o censo AST; LEDGER com a execução VERMELHA antes do patch.
7. *W2.2:* célula (c) = auxiliar de saída no atexit E no sinal; `flush` de stdout e stderr antes da drenagem; células do sinalizador e `_OWN_DRAIN_PENDING` fail-safe (§3(a) item 13).
8. *W2.2-bis:* `T_min` = menor timeout registrado (3 s) com teste de deriva; âncora = `min(import, início do processo)`; controle S1 com import tardio; sinal de travamento ≤ T (MF-R2-W2-1).
9. *W2.3:* só pela compactação; a remoção pelo dono sai.
10. *W2.4:* marcada CONDICIONAL (volta só como pacote próprio, com as condições do AMEND-4 §4.5); o Check sai.
11. *W2.4-bis:* seletor dos testes novos; G6, G7, spool órfão de qualquer idade como taxa; travas ≥ 100 mil ⇒ recomenda a W2.6; no máximo uma linha por execução.
12. *W2.5:* mutantes M-a..M-d; composição da cadeia; guarda de inode estável; teste-censo dos abridores.
13. *W2.6:* predicado do AMEND-4 + a recusa por spool/`.draining.*` com PID vivo; RECORRENTE sob T1; pré-condição pela decisão 2.
14. *W0.5:* acrescentar ao pré-registro o que pede o §3(a) itens 8 a 11 e 15.
15. *W2, «Seletores dos Checks»:* cada seletor casa SÓ os testes do item; nenhum seletor é substring do nome do módulo.
16. *W2, «Controle vermelho→verde»:* razão ≤ 1,2 só nas células sem spool; células com spool = decisão entregue + prazo respeitado; sem calibração, S1 declarado como prova contra modelo.
17. *«Success criteria», braço da W2:* reescrita do §3(a) item 6.

**ADR-055-AMEND-4 (rascunho → texto do pacote de ADR)**

18. *§4.1 e §4.2:* auxiliar de saída com `flush` antes da drenagem; âncora `min(import, kernel)` com fallback e resíduo; sinal `STARVED` ≤ T com controle positivo; `_OWN_DRAIN_PENDING` fail-safe.
19. *§6.1, §6.2 e §6.4:* calibração com o harness real; S1 com import tardio; estatística; esperado por célula sob T1; células pré-decisão, do wrapper e da perna 3; composição da cadeia; guardas de inode e de censo; gatilho numérico da T2.
20. *§6.3, §8.2 e §9:* H1 com `|D|_min` ≥ 200; H3 com limiar operacional de 100 mil; G6 ATIVO; G7 novo; G2 vira «guarda de regressão»; G1 com controle positivo do H1 e cadência por dias distintos.
21. *§5.2:* recusa da execução por spool ativo ou `.draining.*` com PID vivo.
22. *§11, §13 e §14:* R2-1..R2-7 respondidos e fechados; resíduo da âncora reduzido; W2.6 recorrente; status «`design-coherent` na rodada 2, VETO retirado com condições».

**PLAN-194 — W3**

23. *W3, parágrafo «BLOQUEADA»:* rodada 3 = a ÚLTIMA, só para a W3; «confiança no registro» ⇒ ESCALATE.
24. *W3, resposta da pergunta 2:* reescrita com a W0.6 (o comando do npm não serve; `sigstore.verify` com política serve; A-14/A-15 recusam; empacotamento = decisão 3).
25. *W3, «Identidade do construtor»:* literais medidos, ids imutáveis, âncora no `subject` do bundle verificado (`dist.integrity` só cruzamento).
26. *W3, «CLI e consumidores»:* literal `registry`; nota de operador do Gate 4 da fase 6.
27. *W3, «Paths»:* pacotes 1b → 1a → 2 + kernel; verificador, auxiliar JS e lockfile sob o ADR-192 (não «livre»); `SBOM.md`; guarda do registro; recontagem ≤ 8 paths por pacote.
28. *W3.1:* escopo «até o LAND» escrito no item; Check sem flag.
29. *W3.3:* argv também sondado na 0.156.1; canário com diff sintético; política de nova tentativa pré-registrada.
30. *W3.4:* tirar «senão ACEITA e DECLARADA»; células de fronteira; duas camadas de teste; guarda de rede dos filhos; teste-censo; Check com o arquivo de teste do verificador e seletores distintos.
31. *W3.6:* novas pré-condições: rota 2 invertida, quiesce, promoção pelos bytes verificados com P-01 da árvore inteira; Check com `--allow-auto-pin` e `pin_source == "registry"`.
32. *W3, «Declarar no material assinado»:* executáveis irmãos; R-16; dependência de `node` + sigstore; janela de promoção.
33. *W7, «Pré-condições do corte»:* rota 2 invertida nos dois derivadores do kit (materializar sem executar, ambiente npm do zero, `--ignore-scripts`, shim no `path` verificado), com o controle do §3(b) item 15.
34. *Mapa de colisões:* linha do `gate-scripts-manifest.txt` + W3 (pacote 1a); linha nova do `SBOM.md` se outra onda o tocar (conferir).
35. *«Paths × oráculo»:* auxiliar JS, lockfile, `SBOM.md` e guarda do registro, com o oráculo rodado na abertura.
36. *«Decisões pendentes do Owner»:* aplicar o §6 (a decisão 3 reescrita; a 2, a 5 e a 7 atualizadas).
37. *«Riscos»:* risco 4 com a rota 2 executando antes de verificar até a inversão e os irmãos fora do pin; risco novo «decisão sai só depois do `atexit`» (medido), mitigado por `flush` + prazo.
38. *«Session history»:* S361, rodada 2 (W2 PROCEED; W3 para a rodada 3).
39. *«Unidades que ganharam dono» / poda do `CLAUDE.md`:* registrar que o §3 («stdlib-only») muda no fechamento junto do `SBOM.md`, dentro da folga de 87 bytes (risco 9).

**ADR-182-AMEND-1 (rascunho revisado, entrada da rodada 3)**

40. *§2 e R-6:* escopo honesto com os executáveis irmãos (conferidos na promoção; troca em tempo de execução = mesmo UID).
41. *§4.1:* orquestrador Python + auxiliar `node`; exceção nomeada ao «stdlib-only»; auxiliar e lockfile sob o ADR-192; `node` por caminho absoluto com versão mínima; guarda do registro (MF-R2-W3-5).
42. *§4.2 (V-3, V-4, V-5):* `sigstore.verify` com política, os dois bundles, vínculo ao `subject` verificado pelos mesmos bytes, caches novos com asserção.
43. *§4.3:* promoção pelos bytes verificados, sob proxy morto; P-01 da árvore inteira; quiesce; manifesto por membro na linha do registro.
44. *§4.4:* lista fechada de hosts (registro + CDN do TUF); tetos medidos.
45. *§6:* literais da W0.6 e ids imutáveis como constantes com teste.
46. *§8:* A-03, A-12, A-14 e A-15 reescritas; células de fronteira novas; P-01 ampliado; H-07 com o sha do verificador e do lockfile.
47. *§9 e §11:* campos da linha e do evento (`signature_mode`, versões de `node`/npm/sigstore, sha do lockfile ou do módulo, digest da raiz TUF, manifesto por membro).
48. *§10 e §8.C:* literal `registry`; mensagem do Gate 4 nomeando a rota 2.
49. *§11:* `_emit_audit()` ligado ao `emit_generic` no pacote 1b; sumidouro de teste só no modo de teste.
50. *§14 e §16:* R-16 (rollback exige rede); rota 2 INVERTIDA como pré-condição da W3.6, com shim no `path` verificado.
51. *§17:* duas camadas de teste; guarda de rede dos filhos; teste-censo; mutante «sem política».
52. *§19 e §21:* o R-1 sai (vira decisão de empacotamento; «confiança no registro» ⇒ ESCALATE); o R-12 sai; entra o R-16; o R-5 fica resolvido para o agente pela guarda; pacotes 1b → 1a → 2 + kernel, com `SBOM.md` e o manifesto ADR-192.

## 8. Round verdict

**RUN-ANOTHER-ROUND** — só a W3, na rodada 3, a ÚLTIMA.

- **W2: PROCEED** (`design-coherent`; VETO retirado com condições). Libera sem esperar a W3.
- **W5c:** PROCEED (rodada 1).

**Entrada da rodada 3:**

- este consenso;
- o plano com os ajustes 23 a 39;
- o AMEND-1 revisado (ajustes 40 a 52);
- a decisão 3 do Owner, se já tiver saído.

Os mesmos três críticos julgam só a W3, e cada crítica registra o id servido.

**Retirada do VETO da W3:**

- MF-R2-W3-1 a MF-R2-W3-8 no AMEND-1 revisado;
- empacotamento (i) ou (ii) escolhido pelo Owner.

Se o Owner escolher «confiança no registro» ⇒ ESCALATE, sem rodada 3.

**Regra de parada:** impasse depois da rodada 3 ⇒ Owner por múltipla escolha. NO-GO só por P0 ou
afirmação FALSA no plano. Nenhuma rodada do Codex acima de 80% do semanal (Q2).
