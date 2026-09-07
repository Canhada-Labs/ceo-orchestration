---
plan: PLAN-176
round: 3
rounds_synthesized: [round-1, round-2, round-3]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "§3.4 (:270-292) — a regra publicada de número de ADR é NÃO-IDEMPOTENTE e a sua saída é FALSA em HEAD: re-rodada agora ela elege 179, não 180, porque o próprio texto landado menciona ADR-180. A regra tem de excluir o arquivo do plano da varredura, ou a saída tem de ser declarada como medida ANTES do land (com a data), nunca como reproduzível hoje"
  - "§Waves W0b (:496, :534-537) — a AC `refused_destination_emits_event` exige um campo `decision` que o allowlist fechado do próprio action não carrega (`_lib/audit_emit.py:8480-8488`); a degradação da rodada 2 alcançou 2 dos 3 sítios da mesma página. A recusa tem de ser distinguível por um campo que EXISTE (o enum fechado de `egress_class`) ou a AC diz explicitamente que recusa e sucesso gravam evento indistinguível — e isso vira linha da OQ-2"
  - "§4 (:364-370, :839) — a única AC que exercita `--state --json` enumera SETE critérios enquanto a tabela publica NOVE (:844-852); os dois de fora são K-8 e K-9, criados por esta mesma cura para enxergar a rotina morta. O nome da AC e o texto passam a NOVE, e o número deixa de ser digitado: o teste deriva a lista das linhas `^| K-` do §4"
  - "§Waves W0a (:376-408) — o conjunto VERMELHO de 4 identificadores contradiz a AC vizinha `active_lanes_is_anthropic_only`: `gpt-5.6-sol` é justificado «fora de `_VALID_MODELS`», constante que não existe em código vivo em HEAD (só em `PLAN-142/staging/` e na prosa). Com a raia OpenAI INERTE por construção, o conjunto exato + anti-encolhimento nasce VERMELHO. O conjunto vira 3 identificadores Anthropic, ou a 4.ª linha ganha causa que sobrevive à definição de raia ativa"
  - "§Waves W0a (:385-399) — o arquivo `.claude/data/model-currency-expected-reds.txt` copia o MOLDE de `scripts/tests/ownership-expected-reds.txt` sem copiar a âncora que o torna portão: o molde é membro do `gate-scripts-manifest.txt` (linha 6), o análogo deste plano não entra em manifesto nenhum. Ou o arquivo entra no manifesto (o que o move para a perna canônica), ou a AC declara que o portão é autenticado só pela revisão do Pull Request"
  - "frontmatter (:15) — `external_wait: none` é falso: a W1c só abre depois do land do pack `w4b-ci-matrix` (:678) e a W3b espera o item (iv) do PLAN-169, `status: executing` (:90). O campo passa a nomear as duas esperas; e `eta_calendar: mesmo-dia a D+1` (:16) não cabe em quatro pernas canônicas sob a regra do Owner «WIP canônico ≤ 3 de dia»"
  - "§7 (:915-923) — «o valor em dólares é TETO» é falso como bound: `claude-fable-5` e `claude-fable-5-1` são membros do `AVAILABLE_MODELS_WORKING_SET` do ADR-149 a 10,00/50,00 ⇒ 18,00 por milhão, 2× os 9,00 usados. O número é defensável SOB O PIN `claude-opus-5`; a palavra «teto» sai, ou o teto é recalculado sobre o conjunto de trabalho"
  - "§Waves W0b (:453-458, :512-517) — o interruptor do módulo com rede é declarado como bandeira de linha de comando enquanto o módulo mora em `_lib/` importável: `argv` não alcança um importador, e a AC `disabled_by_default_opens_no_socket` fica verde nas duas arquiteturas. A AC tem de exercer o caminho de IMPORTAÇÃO (chamar a função pública do módulo sem passar a bandeira) além do caminho de `__main__`"
  - "§Waves W3a (:767-800) — o cache buscado na rede é lido pelo `/ceo-boot` sem AC de cerca (a W2a tem `untrusted_feed_is_fenced`, a W3a não tem nenhuma) e «não rastreado» é afirmação sem linha de `.gitignore` (medido: `.gitignore` só cita `.claude/data/federation/peers.yaml`, :197), contra a ordem obrigatória `git add -A` do `CLAUDE.md` §4"
  - "§3.3 (:333-336) — três autoridades do detector são citadas por nome nu (`cost-table.yaml`, `model-deprecations.json`, `settings.json`) enquanto todas as outras carregam caminho; duas são ambíguas em disco (o segundo tem cópia viva em `npm/.claude/scripts/`; o terceiro tem três superfícies, uma delas o perfil `user` DERIVADO de `templates/settings/settings.user.json`, ADR-197)"
  - "§Waves W1c (:678-681) + §4 (:845) — a espera da W1c no `w4b-ci-matrix` não tem dono, perna de relógio nem critério de desistência, e é ela sozinha que fia o instrumento de K-2 (:704-708: «sem isto, K-2 é declaração e não catraca»). Ganha linha própria na tabela §5b: rota barata = K-2 declarado como dívida; rota cara = re-priorizar a fila canônica"
  - "§Waves W1a/W1c (:144, :561-566 × :694-697) — o lint é declarado «Pull Request livre» em duas seções e a W1c o inscreve no `gate-scripts-manifest.txt`; a partir daí toda edição dele passa pela cerimônia (`CLAUDE.md` §5, S326). O custo de cerimônia futura fica declarado, hoje só o do resolver está"
  - "§7 (:919-923) — a faixa 9,84-13,85 não se reproduz da faixa publicada no cabeçalho (1,09M × 9,00 = 9,81; 1,54M × 9,00 = 13,86): os extremos vêm de 1,094/1,538, que o cabeçalho não carrega. Figura DIGITADA, contra a promessa do parágrafo vizinho (:913)"
  - "§6 (:869-874) — a expiração de `cost-table.yaml` (`:29`, 2026-09-13, seis dias) é nomeada só pela perna de «raia ativa»/K-8; a perna do próprio ORÇAMENTO (todo dólar do §7 sai dessa tabela, e a linha do Sonnet 5 já é declarada stale pelo ADR-149:285-290) não é nomeada"
  - "§4 (:844-852) + frontmatter (:16) — com a cadência declarada de 1 ciclo/24 h (:121-129) nenhum critério de qualidade dispara dentro do `eta_calendar`: K-1 pede 8 ciclos, K-5 4 ciclos, K-3/K-9 96 h ⇒ piso de 8 dias. A janela de OBSERVAÇÃO passa a ser orçada separadamente da janela de CONSTRUÇÃO"
synthesized_at: 2026-09-07T01:20:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-176 — consenso do round 3

Três críticos, três `ADJUST`, **11 itens bloqueantes somados (4 + 4 + 3)**.
Nenhum pediu `REJECT`. Toda claim abaixo foi re-verificada por mim em disco,
em HEAD, antes de virar ajuste. O plano não contém caminho pessoal absoluto
(varredura pelo prefixo de diretório de usuário = **0** ocorrências).

**O que o round 3 CONFIRMA — a revisão `5fcf861` fez o trabalho grosso.**
Re-verifiquei, e os três críticos re-verificaram independentemente:

- **15 dos 16 must-fix do round 2 estão cumpridos.** O ADR foi renumerado, a
  W1b foi re-cortada em W1b + W1c com `Paths:` igual às tags, o registro T
  ganhou AC, os dois `Check:` vacuosos viraram comandos cujo vermelho é a
  condição descrita, as garantias «sem rede» viraram oráculo de RUNTIME com
  ponto cego declarado (:409+), as promessas de auditoria foram degradadas aos
  allowlists fechados, o arquivo de vermelhos nasce na W0a, a W3 virou W3a/W3b
  com alvos reais, a cadência ganhou perna de relógio, e a aritmética de
  orçamento fecha nas duas derivações (510-760k + 6-8 × 97.292 = 1,094-1,538M;
  9,00/M no teto e 7,29/M na mista).
- **A tese central segue mecânica.** Os vereditos do oráculo `--is-canonical`
  do §2 reproduzem; o manifesto tem 9 membros; `pytest.ini` coleta os três
  diretórios de teste; `F = 97.292` está em `CLAUDE.md:97`.

**E o que o round 3 descobre é UMA classe, não onze defeitos.** Onze dos itens
abaixo têm a mesma assinatura: *a cura da rodada 2 foi aplicada ao sítio que o
crítico nomeou e não ao seu irmão*. A degradação de auditoria alcançou 2 de 3
sítios da mesma página; o corte de ondas criou W1c mas não atualizou
`external_wait`; a tabela de morte ganhou K-8 e K-9 mas a AC que a lê continua
dizendo SETE; o arquivo de vermelhos copiou o molde e não a âncora que o torna
portão. A contagem de bloqueantes não convergiu entre as rodadas (12 → 11) —
a CLASSE mudou, o volume não. Pela doutrina desta casa («classe repetindo ⇒
trocar a arquitetura da cura»), a cura do round 3 não é editar onze parágrafos:
é **derivar mecanicamente o conjunto de sítios afetados antes de escrever cada
cura** — exatamente o que o §3.4 já faz para o número do ADR e o que a W3 do
PLAN-186 fez para os sítios do piso VETO.

## Consensus findings (2+ agents flagged)

### C1 — BLOQUEANTE — a AC lê SETE critérios de morte, a tabela publica NOVE (Critic-A R-VP4, Critic-C R-FIN1)

Medido por mim: `grep -c '^| K-'` sobre o plano = **9** (`:844-852`, K-1..K-9),
e a AC que exercita `--state --json` diz «serve os **SETE** critérios» (`:364`),
«o teste enumera os sete» (`:366`) e carrega o nome
`state_json_serves_all_seven_death_criteria` (`:370`, repetido em `:839`). Os
dois de fora são **K-8** («zero raias ativas») e **K-9** («rotina parada»,
`:852`, pelo próprio texto «a única perna que enxerga a rotina morta») — os
dois que a cura do round 2 criou para tornar a morte visível. A caixa fica
VERDE sem provar o que a cura inventou: é a classe «instrumento verde cuja
PERGUNTA envelheceu», já paga duas vezes neste repositório.

**Severidade acordada:** BLOQUEANTE. **Mitigação:** o número sai do texto — a
AC assere que a saída de `--state --json` serve **todos** os critérios lidos
das linhas `^| K-` do §4, com controle positivo (uma linha K nova sem campo
correspondente deixa a caixa VERMELHA). **Landa em:** §4 (:364-370), :839.

### C2 — BLOQUEANTE — a AC de recusa de egresso exige um campo que o allowlist fechado não carrega (Critic-A R-VP2, Critic-B S2)

Medido por mim em `.claude/hooks/_lib/audit_emit.py:8480-8488`:
`_EGRESS_DESTINATION_DETECTED_ALLOWLIST = {action, session_id, project,
egress_class, destination, ts, event_schema, tokens_in, tokens_out,
tokens_total, hmac, hmac_error}` — teste de pertinência de `"decision"`
retorna **False**. O plano CITA esse mesmo frozenset corretamente em `:487-490`
e três linhas abaixo (`:496`) escreve «o que a cadeia carrega é host +
`egress_class` + **a decisão**»; a AC `refused_destination_emits_event`
(`:534-537`) exige «o host recusado **e a decisão**». Consequência forense
verificável: recusa e sucesso no MESMO host gravam evento byte-idêntico — e o
`302` same-host que a AC vizinha `allowlist_matches_host_and_path_including_redirect`
nomeia como ameaça fica invisível na cadeia HMAC.

Critic-B mediu o irmão: `env_var_hijack_blocked` nunca carrega nome/valor da
variável e coage `hijack_class` fora do enum para `parse_failure`. A cura do
round 2 alcançou **2 dos 3-4 eventos que o plano emite** — foi aplicada às
seções que o crítico do round 2 nomeou, não ao conjunto derivado das ações.

**Severidade acordada:** BLOQUEANTE. **Mitigação:** o censo das ações que o
plano EMITE é derivado mecanicamente e cada uma é confrontada com o seu
allowlist; a recusa passa a ser distinguível por campo que EXISTE (valor
próprio do enum fechado de `egress_class`, ou action distinta já na taxonomia),
ou a AC declara em letra que recusa e sucesso são indistinguíveis na cadeia —
e essa indistinguibilidade vira linha da **OQ-2**, que sobe de preço.
**Landa em:** §3.1, §3.3, W0b (:496, :534-537), §5b OQ-2.

### C3 — BLOQUEANTE — `external_wait: none` é falso e o calendário não cabe (Critic-A R-VP6, Critic-C R-FIN2)

Medido: o cabeçalho declara `external_wait: none` (`:15`), enquanto o corpo diz
«**A W1c só abre depois do land do `w4b-ci-matrix`**» (`:678`) e «**Só a W3b
espera o item (iv)**» do PLAN-169 (`:90`), cujo `status: executing` eu confirmei
em `PLAN-169-closure-and-cross-session-evolution.md:4`. A autoridade da espera
confere: `PLAN-186/debate/owner-decisions-S347.md:55` fixa a prioridade de WIP
canônico W1 → W6a → W4b sob teto de 3 por dia, o que põe o `w4b-ci-matrix` em
terceiro. O manifesto vivo tem **9** membros (medido), o pack o levará a 12.

Duas consequências, uma de cada crítico, ambas verificadas. (i) `eta_calendar:
mesmo-dia a D+1` (`:16`) não cabe em quatro pernas canônicas (W1b, W1c, W3b,
mais a cerimônia contada em `:903-907`) sob «≤ 3 canônicos de dia». (ii) A
espera da W1c é a única dependência fora da autoridade do CEO cujo NÃO-desfecho
apaga silenciosamente um critério de morte: `:704-708` diz literalmente «sem
isto, K-2 é declaração e não catraca», e `:845` marca K-2 como «fiado pela W1c».

**Severidade acordada:** BLOQUEANTE. **Mitigação:** `external_wait` nomeia as
duas esperas; `eta_calendar` passa a ser derivado do número de assinaturas sob
o teto de WIP; e a espera da W1c ganha linha na tabela §5b com rota barata
(K-2 registrado como dívida declarada, no molde do ADR-190) e rota cara
(re-priorizar a fila canônica) — **nomeada, não decidida por esta rodada**.
**Landa em:** frontmatter (:15-16), §Waves W1c (:678-681), §5b (linha nova).

### C4 — BLOQUEANTE — o portão do conjunto VERMELHO não é portão, e o seu conteúdo nasce vermelho (Critic-A R-VP3, Critic-B S1)

Dois mecanismos independentes sobre o mesmo artefato, os dois verificados.

**Conteúdo (Critic-A).** O conjunto publicado de 4 identificadores (`:380-383`)
justifica `gpt-5.6-sol` como «fora de `_VALID_MODELS`». Medido:
`grep -rn 'VALID_MODELS' --exclude-dir=.git .` casa **apenas**
`.claude/plans/PLAN-142/staging/codex_cli_shape.py`, prosa de planos e este
próprio plano; `.claude/hooks/_lib/adapters/codex.py` dá **0**. A constante não
existe em código vivo em HEAD. E a AC vizinha `active_lanes_is_anthropic_only`
(`:400-408`) declara a raia OpenAI **INERTE por construção** (a tabela de preços
tem 12 identificadores, todos `claude-*` — reproduzi). Um conjunto exato com
anti-encolhimento (`:392-399`, «falha em QUALQUER diferença — inclusive
encolhimento») cuja 4.ª linha só é derivável numa raia que nunca abre nasce
VERMELHO no dia um.

**Autenticação (Critic-B).** O plano copia o molde
`scripts/tests/ownership-expected-reds.txt` sem copiar a âncora que o torna
portão: medido, esse molde é o membro da **linha 6** de
`.claude/governance/gate-scripts-manifest.txt`; o análogo deste plano
(`.claude/data/model-currency-expected-reds.txt`) não entra em manifesto nenhum,
e a única AC de manifesto do plano (`:694-697`, W1c) inscreve só o lint. Apagar
uma linha do arquivo torna o «conjunto exato» verde por construção.

**Severidade acordada:** BLOQUEANTE. **Mitigação:** o conjunto passa a três
identificadores Anthropic (ou a 4.ª linha ganha causa que sobreviva à definição
de raia ativa), e o plano ESCOLHE explicitamente entre inscrever o arquivo no
manifesto — o que o move para a perna canônica e muda o corte de ondas — ou
declarar em letra que o portão é autenticado apenas pela revisão do Pull
Request, no molde honesto do `OWN-` do PLAN-167.
**Landa em:** §Waves W0a (:376-399), §5b (efeito sobre a OQ-3).

### C5 — ADVISORY — a definição de «raia ativa» torna o fornecedor do trilho permanentemente invisível (Critic-A R-VP3, Critic-C R-FIN7)

Os dois nomeiam o mesmo fato, e eu o reproduzi: `cost-table.yaml` tem 12
identificadores, todos `claude-*`; «raia ativa» exige membro do conjunto de
trabalho do ADR-149 **e** linha de preço. Logo a única raia que abre é a
Anthropic — e a única deriva de currency que este repositório já MEDIU está do
outro lado (o §8 do próprio plano, `:989-990`, inventaria a forma do revisor
externo congelada em 0.139 contra binário 0.144.6). Não invalida o fail-closed,
que está correto; é ROI que precisa estar escrito, senão o plano promete
«currency» e entrega currency de um fornecedor. **Landa em:** §2 ou §8, uma
frase; não bloqueia onda.

## Single-agent insights kept

1. **K1 (Critic-A, R-VP1) — BLOQUEANTE: a regra de número de ADR é
   não-idempotente e a sua saída é FALSA em HEAD.** Rodei o snippet do próprio
   plano (`:270-285`) em HEAD e obtive: `livres 22` (bate com o publicado),
   `zero 12 [68,166,167,168,169,170,171,172,176,177,178,179]`, `max 179`. O
   plano publica «13 com zero menção […,179,180]; escolhido **180**» (`:290-292`).
   O delta é exatamente 180 — o texto landado passou a mencionar o número que
   ele elege, e a regra que se apresenta como reproduzível refuta o próprio
   resultado na segunda execução. A AC de reserva (`:632`) usa outra regra
   (colisão de arquivo + reserva em `.claude/plans`, excluindo `PLAN-176`) e
   fica VERDE, então nenhum portão vê a contradição. **Cura:** a derivação
   exclui o arquivo do plano da varredura (o mesmo `grep -v` que a AC já faz),
   ou a saída é datada e declarada como medida ANTES do land. Uma linha.
2. **K2 (Critic-C, R-FIN3) — BLOQUEANTE: «o valor em dólares é TETO» é falso
   como bound.** Verificado em disco: `claude-fable-5` (`cost-table.yaml:65-69`)
   e `claude-fable-5-1` (`:70-74`) custam 10,00/50,00 e são membros do
   `AVAILABLE_MODELS_WORKING_SET` do ADR-149 (`:80-96`), cuja semântica é
   explícita — «the set of model ids the harness **may select on ANY surface**»
   (`:107-110`). Aplicando as mesmas quotas 0,80/0,20 do plano dá 18,00 por
   milhão, **2×** os 9,00 usados; o teto real sobre o conjunto de trabalho é
   19,7-27,7 USD, e o piso re-pago sozinho (10,5-14,0 USD) já excede o teto
   publicado. O número é correto e defensável SOB O PIN
   (`.claude/settings.json` fixa `claude-opus-5`), que é como o plano deve
   escrevê-lo. **Cura:** trocar «teto» por «estimativa sob o pin», ou publicar
   o teto sobre o conjunto de trabalho. Duas linhas.
3. **K3 (Critic-B, S3) — BLOQUEANTE: o interruptor do módulo com rede não tem
   camada de aplicação declarada.** Verificado: `:453-455` declara a defesa
   REAL como «sem a bandeira, **nenhum chamador** (agente ou não) abre soquete»
   e `:456-458` define o interruptor como **bandeira de linha de comando**; o
   módulo mora em `.claude/hooks/_lib/model_feed_fetch.py`, importável. Uma
   bandeira parseada em `__main__` não é vista por `from _lib import
   model_feed_fetch`, que é exatamente o caminho que a AC vizinha
   `substrate_watch_no_network_runtime_oracle` (`:544-551`) diz que o `grep`
   antigo era cego a. A AC `disabled_by_default_opens_no_socket` (`:512-517`)
   fica verde nas duas arquiteturas. **Cura:** a AC exerce o caminho de
   IMPORTAÇÃO — chamar a função pública sem passar o parâmetro de habilitação,
   com `socket.socket` substituído por uma função que levanta — além do
   caminho de `__main__`. Uma caixa.
4. **K4 (Critic-B, S4) — BLOQUEANTE: o cache de rede chega ao contexto do CEO
   sem cerca e sem linha de `.gitignore`.** Verificado nas duas pernas: as
   quatro caixas da W3a (`:776-800`) não têm nenhuma AC de cercar/truncar
   conteúdo externo, enquanto a W2a tem `untrusted_feed_is_fenced` (`:741-744`);
   e `grep -n '.claude/data' .gitignore` dá **uma** linha, `:197`
   `.claude/data/federation/peers.yaml` — «não rastreado» (`:770-772`) é
   afirmação sem mecanismo, contra a ordem obrigatória `git add -A` do
   `CLAUDE.md` §4. **Cura:** AC de cerca na W3a (o conteúdo do cache é dado de
   fonte externa lido para dentro do prompt do CEO) + linha de `.gitignore`
   entregue na mesma onda, com AC que a assere.
5. **K5 (Critic-A, R-VP7) — as autoridades do detector citadas por nome nu.**
   Verificado: `:333-336` nomeia `cost-table.yaml`, `model-deprecations.json` e
   `settings.json` sem caminho, enquanto toda outra autoridade do plano carrega
   um. Duas são ambíguas em disco: `model-deprecations.json` existe em
   `.claude/scripts/` **e** em `npm/.claude/scripts/`; e há três superfícies de
   settings vivas — `.claude/settings.json`, `.claude/settings.local.json` e o
   perfil `user` DERIVADO em `templates/settings/settings.user.json` (ADR-197,
   wave-s330-F). É a FORMA dos defeitos D1-D4 da S322-S327: a origem tem dono,
   a ROTA não. Advisory, cura de três palavras por linha.
6. **K6 (Critic-B, S5) — o lint deixa de ser «livre» ao entrar no manifesto.**
   Verificado: `:144` e `:561-566` o declaram «Pull Request livre» e `:694-697`
   o inscreve no `gate-scripts-manifest.txt`; a partir daí toda edição dele
   passa pela cerimônia (`CLAUDE.md` §5, lição S326, paga com `verify-counts.sh`).
   O plano declara o custo de cerimônia só para o resolver. Advisory: uma
   frase no §Riscos.
7. **K7 (Critic-C, R-FIN6) — nenhum critério de qualidade dispara dentro do
   `eta_calendar`.** Verificado: cadência de 1 ciclo/24 h (`:121-129`), K-1 pede
   8 ciclos (`:844`), K-5 a cada 4 ciclos (`:848`), K-3 e K-9 96 h (`:846`,
   `:852`) ⇒ piso de 8 dias de OBSERVAÇÃO contra `eta_calendar: mesmo-dia a
   D+1`. O critério está corretamente pré-registrado antes do primeiro número —
   o que falta é orçar a janela de observação separadamente da de construção.
   Um plano fechado em D+1 tem n=1 ciclo, que não separa «detector funciona» de
   «detector sempre verde». Advisory com consequência: o §4 ganha a data em que
   os critérios passam a ser LEGÍVEIS.
8. **K8 (Critic-C, R-FIN5) — a expiração da tabela de preços não é nomeada
   pela perna do orçamento.** Verificado: `cost-table.yaml:29`
   `cost_table_valid_until: 2026-09-13` (seis dias), `:34` `last_verified_at:
   2026-06-15`, e o ADR-149:285-290 declara as linhas-cartaz do Sonnet 5 «stale
   from today» — e o Sonnet 5 é insumo dos 7,29/M da derivação mista. O plano
   nomeia a expiração em §6 apenas pela perna de raia ativa/K-8. Advisory: uma
   frase no §7.
9. **K9 (Critic-C, R-FIN4) — a quota do revisor externo não está precificada.**
   Verificado por aritmética do próprio plano (`:903-907`): quatro pernas
   canônicas × 2 rodadas de trilho = 8 invocações contra uma quota separada,
   com dois modos de falha já medidos neste repositório («at capacity», «usage
   limit»). Custo zero e disponibilidade não modelada para o item que decide o
   calendário de metade do plano. Advisory: entra no §Riscos como risco de
   DISPONIBILIDADE (adia onda canônica), não como dólar.
10. **K10 (Critic-C, R-FIN8) — o multiplicador de sessões é 51-54 % do envelope
    e continua digitado.** Verificado: `budget_sessions: 6-8` (`:11`), piso
    584-778k contra total 1,094-1,538M, e o próprio plano escreve a cura sem
    executá-la (`:909-914`: «`F` não é um ponto, é uma banda… deve gerar a faixa
    em vez de digitá-la», instrumento rastreado em
    `.claude/plans/PLAN-179/w0/gateboot_repay.py`). Com 8 ondas e 4 cerimônias
    em 6-8 sessões não há folga para uma rodada de trilho vermelha. Advisory
    com prazo: a próxima revisão gera a faixa pelo instrumento.
11. **K11 (Critic-C, R-FIN9) — a faixa em dólares não se reproduz da faixa de
    tokens publicada.** Verificado: 1,09 × 9,00 = 9,81 e 1,54 × 9,00 = 13,86,
    contra os 9,84-13,85 do texto (`:919-923`), que derivam de 1,094/1,538 —
    números que o cabeçalho (`:10`) não carrega. É figura digitada, o defeito
    que o parágrafo vizinho (`:913`) promete não repetir. P3, cura de uma linha:
    o cabeçalho carrega os extremos que a derivação usa.

## Single-agent insights rejected / deferred

1. **REBAIXADO de bloqueante a advisory — R-VP5 (as tags da W2a nomeiam
   caminhos fora da linha `Paths:`).** A medição do crítico está certa (as 5
   caixas dão `[.claude/data/models-preference.json]`,
   `[.claude/governance/models-registry.json]` e três sem segmento de caminho,
   contra `Paths (2)` em `:721-723`), mas a divergência é **declarada no
   parágrafo imediatamente acima**, `:716-719`: «os dois arquivos de camada
   citados nas tags abaixo … aqui são **alvo de controle**, não caminho
   editado». Divergência explicada não é a mesma classe que divergência
   silenciosa — que foi o que justificou re-cortar a W1b. E o próprio crítico
   confirma que não é violação do PLAN-SCHEMA (§13.2 enforce cobertura de
   `Check:`, não a tripla da tag). **Mantido como advisory:** vale usar uma
   grafia distinta para «alvo de controle» vs «caminho editado», para que a
   regra de leitura do `:295-307` seja mecanicamente aplicável.
2. **REBAIXADO a P3 — R-VP8 (a AC do ADR ancora na gramática minoritária
   `status:`).** Medi: em `.claude/adr/`, **8** arquivos casam
   `^status: PROPOSED$` e **85** casam `^status: ACCEPTED$`, contra **86** que
   usam a grafia capitalizada/bullet `Status`. A caixa (`:632`) portanto **não
   nasce vermelha** — os moldes recentes (ADR-195, ADR-196) usam a grafia que
   ela exige, e o ADR-180 será escrito por este plano. É fragilidade real da
   classe que a S333 já pagou (o leitor de `Status` teve de aprender bullet e
   negrito), não defeito. **Deferido:** o plano cita o molde exato pelo nome,
   uma linha; a cura estrutural pertence ao `FU-ADR-GRAMMAR`, já aberto.
3. **DEFERIDO — S6 (o conjunto de cabeçalhos da requisição não é fechado por
   AC).** Verificado: as 8 caixas da W0b (`:512-559`) cobrem allowlist,
   redirecionamento, tempo-limite, certificado, evento e forma da resposta —
   nenhuma sobre cabeçalhos. É superfície real (`User-Agent`/`Cookie`
   derivados do ambiente), mas de um só crítico, sem colisão com outra AC e
   curável na própria onda. Entra como caixa P1 da W0b se sobrar orçamento;
   não bloqueia.
4. **NÃO DECIDIDO por desenho — as três OQ do §5b (`:947-949`).** OQ-1 (número
   do ADR: 180 por regra × arbitrar 198), OQ-2 (forense de auditoria: degradação
   barata × emenda canônica a `_lib/audit_emit.py`, oráculo = 1, +1 caminho e
   +1 assinatura) e OQ-3 (corte da W1b: duas assinaturas × pacote único de 8
   caminhos). Confirmei que a rota barata está executada em cada uma e que
   **nenhuma bloqueia onda**. Registro apenas o efeito das descobertas desta
   rodada sobre o PREÇO delas: C2 encarece a rota barata da OQ-2 (sem emenda,
   uma AC precisa ser **reescrita**, não só degradada — e Critic-B tem razão em
   pedir que a OQ-2 cubra extensão de ENUM, não só de allowlist); e C4 toca a
   OQ-3, porque inscrever o arquivo de vermelhos no manifesto mudaria o corte.
   **A decisão continua sendo do Owner.**
5. **NÃO DECIDIDO — a OQ-4 nova proposta por Critic-A e a OQ-A/OQ-B de
   Critic-C.** As três são bem formadas e eu as verifiquei, mas são perguntas
   ao Owner, não curas do sintetizador. Entram no §5b como LINHAS (rota barata
   × rota cara × preço), sem resposta: a espera da W1c (C3), o teto sob o pin
   × sobre o conjunto de trabalho (K2), e as 8 rodadas de trilho contra quota
   externa (K9).
6. **NÃO VERIFICÁVEL por ausência de artefato — 8 dos 10 caminhos do §2 não
   existem em HEAD.** Critic-C o registra e o próprio plano o declara
   (`:129-131`). Todos os vereditos de oráculo sobre eles são previsões de
   PADRÃO de caminho, não medições de arquivo. Não é defeito — é o limite que
   o plano já escreveu; fica como instrução de re-medição no land.

## Plan adjustments

| § do plano | mudança |
|---|---|
| frontmatter (:15-16) | `external_wait` nomeia as duas esperas (land do `w4b-ci-matrix` para a W1c; item (iv) do PLAN-169 para a W3b); `eta_calendar` derivado do número de assinaturas sob o teto «WIP canônico ≤ 3 de dia»; `budget_tokens` carrega os extremos que a derivação do §7 usa |
| §3.4 (:270-292) | a derivação exclui o arquivo do próprio plano da varredura (ou a saída é datada como medida ANTES do land); o texto deixa de apresentar como reproduzível hoje um resultado que a 2.ª execução refuta |
| §3.3 (:333-336) | as três autoridades ganham caminho; a ambiguidade de `model-deprecations.json` (2 cópias) e de `settings.json` (3 superfícies, uma DERIVADA) é resolvida por nome de arquivo completo |
| §Waves W0a (:364-370, :839) | a AC de `--state --json` passa a NOVE e o número deixa de ser digitado: a lista sai das linhas `^| K-` do §4, com controle positivo |
| §Waves W0a (:376-399) | o conjunto VERMELHO fica coerente com `active_lanes_is_anthropic_only` (3 identificadores, ou 4.ª linha com causa que sobrevive); e o plano ESCOLHE entre inscrever `.claude/data/model-currency-expected-reds.txt` no manifesto ou declarar que o portão é autenticado só pela revisão |
| §Waves W0b (:453-458, :512-517) | a AC do interruptor exerce o caminho de IMPORTAÇÃO além do de `__main__` |
| §Waves W0b (:496, :534-537) | censo mecânico das ações que o plano EMITE × os seus allowlists; a recusa passa a ser distinguível por campo existente, ou a indistinguibilidade é declarada em letra e sobe para a OQ-2 |
| §Waves W1c (:678-681) | a espera ganha dono, perna de relógio e critério de desistência; K-2 aparece como dívida declarada enquanto ela durar |
| §Waves W2a (:716-723) | grafia distinta para «alvo de controle» × «caminho editado», para que a regra de leitura do :295-307 seja mecanicamente aplicável |
| §Waves W3a (:767-800) | AC de cerca sobre o conteúdo do cache lido para dentro do contexto do CEO + linha de `.gitignore` entregue e asserida na mesma onda |
| §4 (:844-852) | a janela de OBSERVAÇÃO é orçada separadamente da de construção: a data em que K-1/K-3/K-5/K-9 passam a ser legíveis fica escrita |
| §6 / §7 (:869-874, :915-923) | «teto» vira «estimativa sob o pin `claude-opus-5`» (ou o teto é recalculado a 18,00/M sobre o conjunto de trabalho do ADR-149); a expiração da tabela de preços é nomeada também pela perna do orçamento; a faixa em dólares reproduz a faixa de tokens do cabeçalho |
| §5b (linhas novas) | +3 linhas ABERTAS (espera da W1c; teto sob o pin × sobre o conjunto de trabalho; quota do revisor externo nas 8 rodadas de trilho), cada uma com rota barata, rota cara e preço — **nenhuma decidida aqui** |
| §Riscos | +custo de cerimônia futura do lint (membro do manifesto após a W1c); +quota do revisor externo como risco de DISPONIBILIDADE; +ROI declarado da raia única ativa |
| Progress log | entrada «round 3 sintetizado» |

## Round verdict

**RUN-ANOTHER-ROUND**

Regra aplicada: risco levantado por 2+ críticos ⇒ o plano MUDA (quatro
bloqueantes, C1-C4, mais um advisory C5, todos re-verificados por mim em
disco); risco de um só crítico ⇒ decisão escrita do sintetizador (11 mantidos
com verificação, 6 rejeitados, rebaixados ou deferidos com razão).

**Por que não PROCEED.** Há sete itens bloqueantes vivos com `file:line`
verificado — C1 (`:364-370` × `:844-852`), C2 (`:496`, `:534-537` ×
`audit_emit.py:8480-8488`), C3 (`:15` × `:678`, `:90`), C4 (`:380-383` ×
`:400-408`, e `:385-399` × `gate-scripts-manifest.txt:6`), K1 (`:290-292`),
K2 (`:915-923`), K3 (`:453-458` × `:512-517`) e K4 (`:770-772` × `.gitignore`).
A regra desta rodada é literal: PROCEED só com zero bloqueantes. O rótulo
**design-coherent NÃO é registrado** — o round terminou com 11 itens
bloqueantes somados nas três críticas.

**Por que não ESCALATE-TO-OWNER.** Nenhum dos oito exige decisão do Owner:
todos são curáveis por reescrita de texto dentro da autoridade do CEO, e as
três OQ do §5b (mais as três linhas novas que esta rodada propõe) continuam
ABERTAS por desenho, com a rota barata executada — nenhuma bloqueia onda. O
flip de `status` continua sendo do Owner (4.10); o plano permanece `reviewed`.

**Nota de método para quem abrir a rodada 4 — e para quem decidir não abrir.**
A contagem de bloqueantes não convergiu (12 no round 2, 11 no round 3): a
CLASSE mudou, o volume não. Onze dos itens desta rodada são o mesmo defeito —
*cura aplicada ao sítio nomeado, não ao seu irmão*. Uma rodada 4 que revise o
TEXTO curado item a item reproduzirá a série. A cura de arquitetura, e é ela
que recomendo ao CEO antes de qualquer rodada nova, é derivar mecanicamente o
conjunto de sítios afetados por cada cura antes de escrevê-la — o censo que o
§3.4 já faz para números de ADR, que a W3 do PLAN-186 fez para os sítios do
piso VETO, e que Critic-B formulou exatamente: *o censo é sobre as ações que o
plano EMITE, derivado mecanicamente, não sobre as seções que o crítico
mencionou*. Sob a doutrina de teto de rodadas por classe, absorver os 15
ajustes com censo mecânico e fechar a série é uma escolha legítima do CEO; o
que não é legítimo é declarar `design-coherent` sobre o texto atual.
