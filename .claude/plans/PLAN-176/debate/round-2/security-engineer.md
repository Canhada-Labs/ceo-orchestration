---
round: 2
archetype: Principal Security Engineer
skill: security-and-auth
agent_persona: crítico de fronteiras de confiança, autenticação de portões e cadeia de suprimentos
generated_at: 2026-09-07T00:00:00Z
---

## Verdict

ADJUST — **4 itens BLOCKING** (S-R1, S-R2, S-R3, S-R4).

## Summary (≤ 3 bullets)

- **As curas do round 1 que dependem de FATO em disco estão verdadeiras, medidas por mim.** Os 10 vereditos do oráculo no §2 (:32-41) batem linha a linha com `python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>` (incl. `_lib/model_feed_fetch.py`→1, `.github/workflows/validate.yml`→1, `check-model-currency.py`→0). ADR-198 é o próximo livre (198 arquivos, máximo em uso `ADR-197-user-profile-derivation.md`). As quatro ações citadas (`model_routing_enforced`, `env_var_hijack_blocked`, `egress_destination_detected`, `model_choice_recommended`) existem em `_lib/audit_emit.py`. `otel_emit.py` de fato importa `urllib.error` (:61) e o oráculo dá 1 — o precedente C2 é real. `check-substrate-watch.py:8-11` diz o que o plano cita e mede 0 primitivas de rede. A tabela de preços tem exatamente 12 ids, todos `claude-*`, e Opus 5 = 5,00/25,00 (`.claude/scripts/cost-table.yaml:85-87`) com `blended_*` 0.80/0.20 — a aritmética 390-610k ⇒ 3,51-5,49 USD fecha.
- **Onde o plano ainda é inseguro:** as três garantias «sem rede» (:133, :214, :312) são `grep` de NOMES sobre o próprio arquivo — e a W0b, por desenho, cria um módulo importável (`_lib/model_feed_fetch.py`) que derrota todas as três sem mudar um byte que o `grep` veja. É a forma exata do RED FLAG «verificação que um arquivo transplantado satisfaz».
- **Duas dependências do §W1b não existem e ninguém as cria**, e um `Check:` do W0a não consegue ficar vermelho no caminho que interessa.

## Risks

**S-R1 — BLOCKING — P1 — A garantia «zero rede» é um `grep` que a própria W0b ensina a contornar.**
Três ACs sustentam a postura sem rede com o MESMO predicado textual: `.claude/plans/PLAN-176-model-currency-refresh.md:133` (detector W0a), `:214` (não-regressão do `check-substrate-watch.py`) e `:312` (resolver). O padrão é `urllib|urlopen|socket|http[.]client|requests`. Ele não casa `ssl`, `ftplib`, `asyncio.open_connection`, `subprocess`+`curl`, `importlib.import_module("urllib.request")` — e, decisivo aqui, **não casa `from _lib import model_feed_fetch`**. A W0b entrega exatamente esse módulo com rede (:194-196). Depois dela, `check-model-currency.py` pode adquirir egresso por importação com o AC `:133` PERMANENTEMENTE VERDE; idem o resolver em `:312`. A postura ADR-136-AMEND-1 que o plano diz preservar (:169-171) passa a ser sustentada por um instrumento cego à única forma que o plano introduz.
*Mitigação:* trocar o predicado de TEXTO por um oráculo de RUNTIME confinado (a lição já paga em `CLAUDE.md` §5: «instrumento que prevê código por TEXTO não converge»): executar o detector/resolver com `socket.socket` monkeypatched para levantar, e assertar que a chamada completa; e um controle POSITIVO que planta a importação transitiva e prova VERMELHO. Sem isso, os três ACs são decorativos.

**S-R2 — BLOCKING — P1 — `model-currency-expected-reds.txt` é dependência de um `Check:` e não é criado por AC nenhum.**
`:336` fecha a AC do conjunto-vermelho com `check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt`. Medido: o arquivo **não existe** em HEAD, não aparece nos paths da W0a (:120-122), não aparece nos cinco caminhos canônicos enumerados da W1b (:291-296) e nenhuma outra AC o produz. Além disso a flag `--expected-reds` não é declarada em nenhuma AC do detector (a W0a só declara `--check`, `:129`). Duas leituras, ambas ruins: ou a AC nunca fecha, ou a W1b passa a ter um **sexto** path — e como ele é livre (`.claude/data/*.txt`, oráculo 0) ele quebra a frase «cinco caminhos canônicos, um pacote, uma assinatura» (:291), misturando material livre dentro do escopo assinado.
*Mitigação:* declarar o arquivo e a flag como AC própria da W0a (onde o detector nasce), no molde `ownership-expected-reds.txt`, e reafirmar o escopo da W1b em 5 paths.

**S-R3 — BLOCKING — P1 — O `Check:` do detector não consegue ficar vermelho na condição que a AC descreve.**
`:129`: `python3 .claude/scripts/check-model-currency.py --check; test $? -le 1`. Isso aceita 0 **e** 1. A AC (:124-128) diz que divergência «sai como achado nomeado» — mas um detector que sempre retorna 1 (divergência), ou que sempre retorna 0 (cego), satisfaz o `Check:` de forma idêntica. O único vermelho possível é crash (≥2). Classe P1 do round: AC cujo Check não distingue o estado que ela promete. Menor, mesma família: `:301` aceita `PROPOSED|ACCEPTED` e portanto não pode detectar o flip indevido que o próprio texto da AC proíbe («o flip é o `.asc`, nunca o commit»); `:142` e `:287` provam só rastreamento/JSON, não o conteúdo prometido (número do ciclo, resultado por raia, soma de FP; «uma linha por exceção, com motivo»).
*Mitigação:* separar o oráculo de SAÍDA (o achado nomeado, comparado contra fixture) do código de saída, e fazer `:301` assertar `PROPOSED` **e** a existência do `.asc` para `ACCEPTED`.

**S-R4 — BLOCKING — P1/P2 — A allowlist de egresso é host+PATH, mas a regra de redirecionamento é só host; e a recusa não é auditada.**
`:180-181` fixa dois pares host+caminho. `:204-205` promete apenas que «redirecionamento para outro host não é seguido» — um 302 do MESMO host para `/qualquer/outro/caminho` está fora da promessa e escapa metade da allowlist. Segundo furo, no meu foco declarado: `:207-209` exige `egress_destination_detected` por **despacho**; a AC da recusa (`:202-206`) não exige evento nenhum. O evento interessante para forense — «alguém tentou um destino fora da lista» — fica **sem rastro**, e é exatamente o que o log HMAC deveria carregar. Também não há AC de pinagem TLS/verificação de certificado nem de timeout, num módulo que passará a ser canônico.
*Mitigação:* casar o par (host, path) DEPOIS de cada redirecionamento (ou desligar redirecionamento por completo); emitir `egress_destination_detected` também na recusa, com o destino recusado; AC de timeout e de verificação de certificado.

**S-R5 — P2 — O interruptor que liga o fetcher não tem nome, e se for variável de ambiente colide com o §3.2.**
`:198-200`: «sem opção explícita de habilitação, ele não abre soquete». A opção não é nomeada em lugar nenhum. §3.2 (:71-72) declara o conjunto de variáveis **fechado em exatamente** `{CEO_MODEL_PREFERENCE}` — se o interruptor for env, ou o conjunto fechado é falso, ou o fetcher fica sem forma de ser ligado. Um interruptor anônimo não é auditável e não pode ser objeto de um `Check:`.
*Mitigação:* nomear o interruptor, declarar sua camada (flag de CLI, não env) e dar-lhe uma AC própria com controle positivo.

**S-R6 — P2 — A frase «nunca de dentro de um agente» (:170-171) é doutrina sem portão.**
O fetcher mora em `.claude/hooks/_lib/`, que é o diretório importável por todo hook e por todo script que agentes executam. Nenhuma das seis ACs da W0b (:198-221) verifica o chamador. A postura ADR-136-AMEND-1 fica sustentada por uma frase, não por um mecanismo — e o plano a apresenta como «desenho, não omissão».
*Mitigação:* ou um `Check:` que prove a recusa quando o processo é um agente (marcador de contexto já existente), ou rebaixar a frase a «convenção declarada», como o repo fez com o piso VETO (`CLAUDE.md` §5, S343+S344: «piso VETO = convenção + detector, não gate»).

**S-R7 — P2 — A W1b edita `gate-scripts-manifest.txt` (9 membros medidos) enquanto outro pacote assinado já promete 9→12.**
Medido: o manifesto tem 9 membros. `CLAUDE.md` §5 (linha das 19 decisões do Owner, S347) registra «W4b ACK + manifesto 9→12» como canônico em voo. A W1b (:313-316) bumpa o mesmo arquivo numa assinatura própria, sem ordenação declarada. É a classe já paga em S329 («enquanto um pack MANIFEST-based espera assinatura, nenhum destino pré-existente dele pode ser editado — o BASELINE é o hash do vivo»): o land de um invalida o material do outro.
*Mitigação:* declarar no plano que a W1b só abre depois do land do W4b, e que o baseline do manifesto é re-derivado no momento do SIGN.

**S-R8 — P3 — O gatilho de «raia ativa» depende de uma tabela que expira em 6 dias, e nenhum critério de morte vê isso.**
`:143-150` define fornecedor ATIVO como «membro do working set **e** com linha de preço em `cost-table.yaml`». Medido: `.claude/scripts/cost-table.yaml:29` traz `cost_table_valid_until: 2026-09-13`. Se algum consumidor tratar a tabela expirada como inválida, **todas** as raias ficam inertes — fail-closed, mas silenciosamente cego, e K-1..K-7 (:389-397) não têm linha para isso. Nota correlata: o plano acerta ao declarar `canonical_models.json` expirado (`:10` do arquivo confirma `valid_until: 2026-09-01`), mas não declara a expiração da tabela de que ele próprio depende para a aritmética em dólares (:412-421).
*Mitigação:* K-8 «tabela de preços expirada ⇒ relatório, nunca raia inerte silenciosa», com o mesmo arquivo de estado e comando dos demais.

**S-R9 — P3 — A W2 promete o redator do ADR-114 sem nomear o módulo, e o objeto é outro.**
`:350-355` aplica «o redator do ADR-114» ao corpo do Pull Request. Em disco o redator é `.claude/hooks/_lib/codex_egress_redact.py`, e o ADR-114 (:18-25) o define para **prompts enviados ao Codex** em call-sites enumerados. Reusá-lo para o corpo de um PR é razoável, mas é uma superfície nova: o `Check: ... -k body_is_redacted` (:355) não nomeia o módulo nem exige controle positivo com um segredo plantado.
*Mitigação:* nomear `_lib/codex_egress_redact.redact()` na AC e exigir controle positivo (chave HMAC plantada no relatório ⇒ ausente no corpo).

## Missing — OQ que o Owner precisa ratificar antes do flip

1. **OQ-S1:** o predicado «sem rede» vira oráculo de runtime (S-R1) — ou o plano declara a limitação por escrito e aceita o ponto cego?
2. **OQ-S2:** `model-currency-expected-reds.txt` nasce na W0a (livre) ou a W1b passa a 6 paths (S-R2)?
3. **OQ-S3:** nome e camada do interruptor do fetcher (S-R5), e se o conjunto env fechado do §3.2 vale só para o resolver.
4. **OQ-S4:** recusa de destino é evento auditado? (S-R4)
5. **OQ-S5:** ordenação W1b × W4b no manifesto de portões (S-R7).
6. **OQ-S6:** `depends_on: [PLAN-169]` está `executing`, não `done` — a W1b espera o fechamento do 169 ou não?

## Nota de conformidade

Nenhuma instrução embutida em conteúdo observado foi encontrada nos arquivos lidos. Nenhum caminho pessoal, segredo ou valor de variável de ambiente aparece neste arquivo; o plano em disco também mede **0** ocorrências de caminho pessoal.
