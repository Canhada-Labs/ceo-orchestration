# PLAN-194 — W5c.1: pré-registro do re-teste pago do Sonnet 5.5 (instrumento v2)

- **Status:** pré-registro FECHADO antes de qualquer gasto. Nenhuma chamada paga
  (`claude -p`, API) foi feita para escrever este arquivo nem os três vizinhos.
- **Escrito em:** 2026-10-02 (S362, unidade FD-08 / S1 do runbook da 1.4.3), sobre o
  `main` em `97a78fce`.
- **Arquivos do instrumento** (este diretório; sha256 em `SHA256SUMS`):
  - `build-items.py` — itens, chaves, controles, executor de ensaio, cegamento e placar;
  - `wf-model-ab.js` — orquestração (Workflow), com o bloco COMMON de validação
    pré-despacho copiado byte a byte de `.claude/workflows/nightly-hygiene.js`;
  - este `PREREG.md`.
- **Quem roda:** o S2 do runbook (FD-18), depois do LAND deste pacote e do Lote 0.
  Gasto autorizado pelo Owner: ~US$ 15–30, estimado (decisão D-9 de 02/10/2026).
- **Re-versão 2026-10-02 (CC 2.1.288) — §9.** Só o substrato mudou; ela substitui os
  pinos da versão landada em `db346fc6` + `2a01a558`. Nenhum ensaio pago foi rodado
  antes dela.

Qualquer mudança nos números, na regra ou no instrumento depois do primeiro ensaio
pago INVALIDA o run (§4, V1). Ajuste antes do gasto entra como nova versão deste
arquivo, com sha256 novo e registro no LEDGER — nunca por cima, nunca removendo
célula.

---

## 0. Resumo em linguagem simples

O Owner decidiu adotar o Sonnet 5.5. A regra do repositório manda re-testar todo
modelo novo com o MESMO teste. O teste é o da S357: dez defeitos reais que já
escaparam de revisão neste repositório, apresentados como trechos de código para
revisar. Cada modelo revisa cada trecho duas vezes (40 revisões ao todo), na mesma
configuração de esforço. Um avaliador que não sabe qual modelo escreveu cada
resposta confere se o defeito foi achado. Um programa, e não um agente, aplica a
regra fixada aqui e diz o resultado:

- **PASS** — o Sonnet 5.5 acha os defeitos pelo menos tão bem quanto o Sonnet 5,
  com folga de 2 em 20; segue para o SIGN da W5c (com o custo declarado, se passar
  de 1,2×);
- **FAIL** — ele acha 3 ou mais a menos em 20; a W5c para antes do SIGN e sai pela
  linha de corte;
- **INVÁLIDO / INCONCLUSIVO** — a medição não serviu (modelo trocado em silêncio,
  versão do Claude Code mudou, ensaios demais perdidos, avaliador reprovado no
  controle); refaz, nunca vira PASS.

O teste já bateu no teto na S357 (19 de 20 achados): ele detecta piora, não melhora.

---

## 1. Pergunta e decisão alimentada

**Pergunta.** Na mesma configuração que o repositório usaria (`--effort xhigh`,
`claude -p` hermético, revisão de trecho de código em rodada única), o
`claude-sonnet-5-5` acha os defeitos reais do instrumento pelo menos tão bem quanto
o `claude-sonnet-5`, e a que custo relativo?

**Decisão.** W5c do PLAN-194 (adoção do `claude-sonnet-5-5` no conjunto de trabalho,
emenda 4 do ADR-149, formato da Amendment 2). O debate L3 da W5c fechou com PROCEED
na rodada 1 (ajuste 38: pré-registro com validade antes das células e efeito teto
declarado; ajuste 39: as sondas do adapter). Pela decisão D-10 (02/10/2026), o
adapter da `ANT-02` fica fora da 1.4.3: a dimensão `ANT-02` desta medição é
«não medida» (§5).

**Por que xhigh.** É o nível do braço de referência da S357, o padrão do Claude Code
para os modelos que o suportam e o nível que um agente `sonnet` herda numa sessão
em ultracode (decisão do Owner na S357: ultracode/xhigh padrão). Os dois braços
usam o MESMO rótulo; a documentação diz que o Sonnet 5.5 recalibrou os níveis
(§8, resíduo R5).

---

## 2. Instrumento: origem, o que mudou e por quê

**Origem pinada (dados, conferidos em 02/10/2026):**

| artefato | sha256 |
|---|---|
| `~/ceo-owner-tools/s357/workflows/wf-effort-ab.js` (instrumento S357) | `c57102c33a7d66210cbf0465d3f999a01b3e39c691febb624237c51ee8449128` |
| `~/ceo-owner-tools/s357/results/effort-ab.json` (itens e resultado S357) | `b01d4e3982266d09aa17120f87c8001e19e2221521483313777fdb0219a8f101` |

`build-items.py --check` confere o sha256 do JSON de origem e, item a item, os
campos `fix_commit` (prefixo), `file` e `defect_class` contra a tabela embutida,
quando o JSON está no disco; na ausência dele, usa a tabela embutida e diz isso.

**Por que «v2».** Os arquivos `prompt.txt` e `key.json` da S357 viviam no scratchpad
de uma sessão que não existe mais. O instrumento S357 não pode ser reproduzido
byte a byte; o que se preserva é o MESMO conjunto de defeitos, a mesma forma de
tarefa (trecho ≤ 220 linhas com a numeração original, pedido de revisão neutro,
texto final idêntico) e a mesma receita hermética. A comparação da W5c.1 é
INTERNA: Sonnet 5 × Sonnet 5.5 sobre os mesmos itens v2. Os números da S357 (Opus
5.5) não são linha de base.

**Mudanças em relação à S357, cada uma com o motivo:**

| # | S357 | v2 | motivo |
|---|---|---|---|
| M1 | braços = esforço (xhigh × max), modelo fixo | braços = modelos (`claude-sonnet-5` × `claude-sonnet-5-5`), esforço fixo `xhigh` | é a pergunta da W5c |
| M2 | itens cortados por um agente | itens reconstruídos por código determinístico (7 por `git cat-file blob <pai-do-fix>:<arquivo>`; D02 da cópia staged; D04 da pós-imagem de arquivo novo dentro de um patch; D06 da base + hunks de um patch, aplicação estrita sem fuzz) | reprodutível e pinado por sha256 (§3) |
| M3 | ferramentas padrão do CLI (o sujeito tentava usar ferramentas e era negado: `permission_denials` > 0 em 35 dos 40 ensaios) | `--tools ""`, `--permission-mode manual`, `--no-session-persistence` | desde o CC 2.1.284 uma sessão sem `defaultMode` nasce em `auto`, que pode APROVAR leituras; sem ferramentas, o sujeito responde só do trecho (o efeito que a S357 tinha na prática) e não alcança chaves no disco |
| M4 | `--mcp-config '{}'` e `CLAUDE_CONFIG_DIR` descartável no texto | `--mcp-config '{"mcpServers":{}}'`; sem `CLAUDE_CONFIG_DIR` | os dois desvios que a própria S357 aplicou e registrou (CLI 2.1.280 recusa `'{}'`; `CLAUDE_CONFIG_DIR` descartável dá «Not logged in») |
| M5 | teto US$ 4 por ensaio; 900 s | teto US$ 2 por ensaio (preço do Sonnet); relógio 540 s por ensaio; 3 tentativas por etiqueta; teto do run US$ 40 (equivalente de API, tentativas incluídas) | gasto autorizado ~US$ 15–30; o comando do agente tem limite de 600 s |
| M6 | ABBA com o mesmo braço abrindo sempre | ABBA por item, braço de abertura alternando com a paridade do item (D01 abre com o Sonnet 5, D02 com o Sonnet 5.5, ...) | balanceia efeito de ordem |
| M7 | um avaliador para 40 respostas (o lote chegou truncado em 2) | um avaliador por item, com 1 controle do avaliador por item; rótulos opacos derivados de um sal escolhido no lançamento; nomes de modelo redigidos | cegueira e controle vermelho do avaliador (§4, V5) |
| M8 | agente de veredito aplicava a regra | `build-items.py --score` aplica a regra; o agente só roda o comando | regra pré-registrada aplicada por código |
| M9 | validade: id servido conferido | id servido conferido com a regra V2 (inclui chave extra de modelo auxiliar) e versão do CC + sha do instrumento em CADA registro (re-versão do §9: + sha256 do binário do CC) | ajuste 38 do debate |

O que NÃO muda: o texto final do pedido de revisão (copiado da S357), o limite de
220 linhas por trecho, `--output-format json`, `--setting-sources ""`,
`--strict-mcp-config`, a remoção das variáveis `CLAUDE_CODE_*` com
`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` religada depois, o diretório de trabalho
descartável fora do repositório e «nunca repetir um ensaio pago válido».

**sha256 do instrumento v2** (os mesmos de `SHA256SUMS`):

| arquivo | sha256 |
|---|---|
| `build-items.py` | `4af593df9dd69bcda57189e6d0c1f54abc76f78d08b4f87a6b5e6422135a40ae` |
| `wf-model-ab.js` | `8aac6e3ef6167e6cc9a6204e6446360c42eac601265aa2a1663a15d1c2b7872d` |

---

## 3. Itens, chaves e controles (fixados antes do gasto)

Digest do manifesto (o `--build` do S2 tem de imprimir exatamente este valor; o
`wf-model-ab.js` o carrega como `EXPECTED_DIGEST`; re-versão do §9):
`0ce3c825ec19870bad3fe581024ff489f82635dc24f2f769de8448ffb9d7d6b9`

| item | defeito-chave (classe) | fix | receita da fonte | linhas-chave | controle |
|---|---|---|---|---|---|
| D01 | âncora do fechamento do bloco yaml | `94a4f589` | blob `cd98b14f:.github/scripts/validate-pair-rail-verdict.py` | 128 | negativo |
| D02 | escrita que segue symlink em caminho temporário previsível (TOCTOU) | `3a83b765` | blob `88e56dee:` cópia staged do `audit_emit.py` (PLAN-179) | 8580, 8582, 8584 | positivo |
| D03 | injeção no programa do `sed` + redirecionamento que trunca | `cc002351` | blob `00f56df5:scripts/install.sh` | 479, 1643 | negativo |
| D04 | época NaN/infinita/futura passa pelo TTL | `18505706` | pós-imagem de `launch_ledger.py` em `62ad94c7:.claude/plans/PLAN-190/w1/p190-w1.patch` | 443, 446 | positivo |
| D05 | escrita curta do `os.write` ignorada | `47870320` | blob `38eb917c:.claude/scripts/ceo-launches.py` | 120 | negativo |
| D06 | variável herdada do ambiente apagada pelo trap de saída | `3c155edf` | base `b0e992f3:scripts/install.sh` + hunks do `install.sh` em `6f9fafbf:.claude/plans/PLAN-185/s329-ceremony-C/C.patch` | 780 | positivo |
| D07 | retorno antecipado pula a checagem de arquivo já rastreado | `cd1cec1c` | blob `94a4f589:scripts/_framework_manifest_set.sh` | 989 | negativo |
| D08 | para no primeiro candidato canônico em vez de checar todos | `43bb1268` | blob `8c7877aa:.claude/hooks/check_canonical_edit.py` | 1370, 1372 | positivo |
| D09 | `--since=168h` mal interpretado em silêncio pelo git | `9af6114f` | blob `843eb577:.claude/scripts/persona_demand_scan.py` | 208 | negativo |
| D10 | `str.splitlines()` divide em separadores não-LF | `cd98b14f` | blob `0272508d:.claude/scripts/local/_release_tag_guard.py` | 223, 319 | positivo |

sha256 por item (`source` = arquivo reconstruído; `prompt` = o que o sujeito recebe;
`key` = a chave de correção; `control` = a resposta de controle do avaliador). São
os valores da tabela `EXPECTED` de `build-items.py`, que o `--build` e o `--check`
exigem:

| item | source | prompt | key | control |
|---|---|---|---|---|
| D01 | `22671e953161a1ccc6a680f9d08bb2d9b00f960a85f2c112e91ae8072ea39494` | `c735c79c1bca8d5bcf3643b293496dbb2b0a0fff088dbafc1629629c394425e3` | `3fa57134547406fc3063e5215ae13b142d7b158dd84ad11cf45e139900ce2ad3` | `0b5935f5cf91f05f35a49fd6c068793a1f044f959776830ebe16128e9e5c2a3c` |
| D02 | `3715d1540f75906a4b4f49717553367f2001e91b03160c822afbffe883e9421c` | `346f5de0c045e4dd8f43e677eb12c26559cfa264e4733895ba1428e9020c02e6` | `dd45b26a03df2f54bbd0ec99327ff4c1185af700f916f32199b94c9b3e2fb280` | `a0a50d2a05469cd93c77cd9493cfb2eff86490603079a463c18012bbeebe4dcb` |
| D03 | `2e405fc29e5dff33fb21e8880c8f25ce9b36e36fec5becdb39cf80e384447651` | `b12f671d85b99dbd9a608d1c8a213dfe6eaa7bfacd95f73d304443f4a68b4601` | `c03ddaee3c47f55be654b0e830b29ef6619e72e90e253d0638d3e5cc11852aba` | `9743faabd17d96ac4c8fcc6301d75e37c62891d87784a7db84f6e4658d6b2268` |
| D04 | `2731e3a991f4748beeca328b6744827d99c101d9a63cfd189db123f0adb8f8f9` | `622a07ea2548b1bd9ead553e26f45d8a535338d7baadbdadf686c9830d12f714` | `b2b7aed3f899bf7f38eaa1a3f0a09945e8b91676451c6b3dc43cf9b271989351` | `18a6a8057fb1eabcb145bedb2b89c053c396259a19326423cab546a397a03f11` |
| D05 | `8ef72ab914ba84198b942b2c6759df3b2d4e86b85b3bdcbbbe30e3f9774bc2e3` | `c352733b133c7ebea52b8d28c5bad6bc228689561de3f4491cdb7710bb168178` | `3c4c387e46ffbf3a572b7a48a8bcb103e8073e4ddcc3ea39252a2dd8d37eebce` | `618a34d379ea4aaa9247f0e50c8aa6f4d7fef962e680907bcd384e9ec986bac0` |
| D06 | `1a9c99943e90ca89093b7b5f379ab2a07b903b5d2373978b8de872a7568d8e0a` | `179e9041d52f0129f6e96e80071c0f70d556ea4126fb84bb20678a53bb2c8d7e` | `a31d72988af1d1554652d573ced01a1e4626dec2e93914f935f168a3302464b0` | `00dbc2f0153d489be74494508b24bdcbec0cacb2ad62ecd6c0bb691607320b85` |
| D07 | `b64812281fe6fd053bf719b63ec56d1695fe34700f71226f39425b8648ed72c0` | `0908bb5f78a21d9e71208655edb3e1c2411f9067bd728947a2d7d83a75b74b3a` | `fe72f8fe9884eaedac4980c746d9c492ff414f9ddf0d2b0bdaa8ffccb5bfcdbf` | `149c8c559712cabf613292792a1ca9898d1ebd65af78c0a6754f9a571480467d` |
| D08 | `16b86af5d5061afbf972e23891ab400177806c7831a91ec731254cf318bbd7e9` | `89ef9b989abc8f9f1415e5c45fb3f7d2f7d5fb87cf7bd78a9fca58b6655c7536` | `47bf2f648d99423d9bef836e2a18e34ef0886199fa049c23045dd6545870b945` | `dbc86d4f00bbe5fc0b6388ebf88b701548f19876def0c6549722528847439805` |
| D09 | `c382461d8ef845e4ba0efac9695b51f56121a4588037be08cee073682cc98474` | `a60320904cec9f2b5cf5531d44a91727aec06166b10384009030f320ac09e086` | `5ea38879b44ba235e47a58308670d3d38a1d394724d111ca0e7d8a0ba3266689` | `1ec96879bcdce7a1dfc2a3d7b67afc0e559f2b3ed73a6bdf8f4931087e2699a1` |
| D10 | `5b677ff583371200d81223e90ae0ad4dad1fdfd423bbe9995c3d0517e42896c1` | `e1ab810b3203980cd3f93db1957e733971b767b940ab73cb7695e5cf461ba2f4` | `bebc96d6eac74cdd16dd991b8eb0dbd07a8af50d94a4735e22999e42d0391082` | `f6c51e5ea04d949581cbda439f2aac17ea9696d9bdcbb307ac7c7c4424cc7bc1` |

As 10 fontes foram conferidas contra uma reconstrução independente feita à mão
(`git show <pai>:<arquivo>`, extração por `sed` da pós-imagem do D04 e `git apply`
do D06): os 10 sha256 batem.

**Chave.** Cada `keys/<ID>.json` traz o defeito, as linhas-chave (resolvidas por
âncora literal no arquivo reconstruído e conferidas DENTRO do recorte), a correção
mínima, o defeito secundário (quando há), e os critérios `found_if` / `partial_if`.
`found` exige o defeito-chave; o secundário sozinho vale no máximo `partial`.

**Controle do avaliador.** Por item, uma resposta sintética entra no lote cego com
rótulo igual ao das respostas reais: nos itens pares é POSITIVA (a chave na voz de
um revisor; nota esperada `yes`), nos ímpares é NEGATIVA (dois achados plausíveis
que não são o defeito-chave nem o secundário; nota esperada `no`). Ela pega o
avaliador que diz sempre «sim» ou sempre «não»; não pega viés sutil (§8, R3).

---

## 4. Execução e validade (a validade vem ANTES das células)

**Plano.** 10 itens × 2 braços × 2 repetições = **40 ensaios**, etiquetas `t01`–`t40`
(`build-items.py --plan`), ordem ABBA por item com o braço de abertura alternado
(§2, M6), em dois lotes paralelos (D01–D05 e D06–D10). Primeiro uma passada
completa; depois, só para as etiquetas sem ensaio válido, novas tentativas até 3
por etiqueta (as novas tentativas quebram a ordem ABBA de relógio, como na S357 —
declarado).

**Ensaio.** `build-items.py --trial OUT --item <ID> --model <id> --rep <n> --tag tNN`:
confere o plano, o sha256 do prompt, a versão do CC e o sha256 do binário que
`claude` resolve; roda, num diretório descartável fora do repositório, sem as
variáveis `CLAUDE_CODE_*`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL` e
`ANTHROPIC_DEFAULT_*_MODEL`, e com `DISABLE_AUTOUPDATER=1` (§9):

```
claude -p <prompt> --model <id> --effort xhigh --output-format json --setting-sources "" \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' --tools "" --permission-mode manual \
  --no-session-persistence --max-budget-usd 2
```

e grava o registro (`runs/tNN.json`), a saída crua, o stderr e o texto da resposta.

**Regras de validade (na ordem):**

| # | escopo | condição | consequência |
|---|---|---|---|
| V0 | run | o pré-voo falha: `SHA256SUMS` não confere, `build-items.py --substrate` ≠ `2.1.288 (Claude Code)` com binário `bbe93063…d750`, flag ausente no `--help`, plano ≠ t01–t40, digest do `--build` ≠ §3 | **INVÁLIDO** antes de qualquer gasto |
| V1 | run | algum registro com versão do CC ≠ 2.1.288, sha256 do binário ≠ `bbe93063…d750`, sha256 do `build-items.py` diferente do atual, esforço ≠ xhigh, fora do plano, ou de autoteste | **INVÁLIDO**: nada conta; refaz do zero com este mesmo pré-registro |
| V2 | ensaio | id SERVIDO ≠ id PEDIDO: as chaves de `modelUsage`, sem o sufixo `[1m]`, têm de ser exatamente `{id pedido}` (uma chave extra, de qualquer modelo, também invalida) | ensaio **inválido**, não conta, refeito (até 3 tentativas) |
| V3 | ensaio | status ≠ sucesso (erro, estouro do teto de US$ 2, relógio de 540 s) ou sem texto de resposta | ensaio **vazio** |
| V4 | braço | 5 ou mais dos 20 ensaios de um braço sem nota válida (vazio, inválido, ou sem nota do avaliador) | **INCONCLUSIVO** |
| V5 | avaliador | o controle de um item recebe a nota errada | 1 nova passada de avaliação SÓ desse item (agente novo); se errar de novo: **INCONCLUSIVO** |
| V6 | gasto | soma ≥ US$ 40 (equivalente de API, tentativas incluídas) | o executor recusa novos ensaios; o que faltar conta como vazio (pode levar a V4) |

**Recusa do modelo.** Uma recusa do PRÓPRIO modelo pedido (id servido = pedido)
é comportamento do modelo: o ensaio é válido, recebe nota normal (em geral `no`) e é
contado à parte (`refusals`). Uma recusa seguida de troca silenciosa de modelo cai
na V2; se isso levar à V4, o INCONCLUSIVO é reportado ao Owner com a causa
(recusas do braço), nunca convertido em PASS.

**Substrato a registrar no LEDGER (toda entrada da medição):** versão do Claude Code
(`2.1.288`) e o sha256 do binário (`bbe93063f7a0879a1021b2891e5c9354e5b3b98433e32efe6750f7710afed750`,
conferido em cada ensaio); sistema (macOS / Darwin 27.0.0); `python3`
(3.9.6 nesta máquina em 02/10) e `git` (2.54.0); o sha256 de `SHA256SUMS` e dos três
arquivos; o digest do manifesto (§3); os ids servidos por braço; o modelo da sessão
que rodou os avaliadores; a data; se havia `ANTHROPIC_API_KEY` no ambiente (só
sim/não, nunca o valor — o registro do ensaio guarda esse booleano).

---

## 5. Métrica, δ, regra de custo e células

**Métrica.** Por braço, `taxa = achados / válidos`, onde `achado` = nota `yes` do
avaliador cego (`partial` não conta; é reportado à parte, junto com os falsos
positivos e as recusas). Sem vazios, `válidos = 20`.

**δ de não-inferioridade = 10 pontos percentuais (= 2 de 20).** Não-inferior ⇔
`taxa(5.5) ≥ taxa(5) − 0,10`; o código usa a forma inteira
`100·d₅.₅·n₅ ≥ 100·d₅·n₅.₅ − 10·n₅·n₅.₅`. Sem vazios: 18 × 16 é não-inferior;
18 × 15 é inferior.

**Regra de custo = 1,2×.** `C = mediana(custo por revisão válida do 5.5) /
mediana(custo por revisão válida do 5)`. Custo = tokens do `modelUsage` × tabela
FIXA igual nos dois braços (US$ 2 entrada, 10 saída, 0,20 leitura de cache, 2,50
escrita de cache, por milhão de tokens; preço público dos dois modelos). UMA fonte
para TODOS os ensaios válidos dos dois braços: tokens, se todos os trouxerem; senão
`total_cost_usd`, se todos forem positivos; valor ausente, zero ou fonte mista ⇒
INCONCLUSIVO (um zero faria um braço parecer barato por engano). A fonte usada sai
em `score.json` (`cost_source`). Como o preço por token é o mesmo, `C` mede a
diferença de consumo. Barato ⇔ `C ≤ 1,2`.

**`ANT-02`.** Os dois HTTP 400 do adapter (`thinking` `disabled`; `tool_choice`
forçado com `thinking` ligado) NÃO são medidos neste run (D-10: fora da 1.4.3). A
documentação do skill `claude-api` empacotado no CC 2.1.287 (cache de 25/09/2026)
descreve os dois 400 para o Sonnet 5.5 — isso é documentação lida, não medição; o
resíduo é declarado no material do corte.

**Células (2³, enumeradas antes, nenhuma removida).** Dimensões: defeitos
{não-inferior, inferior por δ} × custo {≤ 1,2×, > 1,2×} × `ANT-02` {400
confirmados, não confirmados}. Neste run a terceira dimensão vale «não medida», então
as quatro células com `ANT-02` medida são INALCANÇÁVEIS e ficam registradas para
uma medição futura:

| célula | defeitos | custo | `ANT-02` | ação |
|---|---|---|---|---|
| A1 | não-inferior | ≤ 1,2× | confirmados | (inalcançável neste run) PASS; o adapter ganha a proteção |
| A2 | não-inferior | ≤ 1,2× | não confirmados | (inalcançável) PASS; adapter sem mudança, `ANT-02` registrada como refutada |
| A3 | não-inferior | > 1,2× | confirmados | (inalcançável) PASS com o custo declarado; o adapter ganha a proteção |
| A4 | não-inferior | > 1,2× | não confirmados | (inalcançável) PASS com o custo declarado; `ANT-02` refutada |
| A5 | inferior | ≤ 1,2× | confirmados | (inalcançável) FAIL |
| A6 | inferior | ≤ 1,2× | não confirmados | (inalcançável) FAIL |
| A7 | inferior | > 1,2× | confirmados | (inalcançável) FAIL |
| A8 | inferior | > 1,2× | não confirmados | (inalcançável) FAIL |
| **C1** | não-inferior | ≤ 1,2× | **não medida** | **PASS** — segue para o SIGN; adapter sem mudança; `ANT-02` resíduo declarado |
| **C2** | não-inferior | > 1,2× | **não medida** | **PASS com custo declarado** no material assinado (valor de `C`); `ANT-02` resíduo declarado |
| **C3** | inferior | ≤ 1,2× | **não medida** | **FAIL** — pára antes do SIGN; o Owner decide por múltipla escolha (o debate não desfaz o «Adotar»); pelo runbook, a W5c sai pela linha de corte |
| **C4** | inferior | > 1,2× | **não medida** | **FAIL** — idem C3 |

Fora das células (vêm ANTES delas): **INVÁLIDO** (V0, V1) e **INCONCLUSIVO** (V4,
V5, custo sem fonte única e positiva). Nenhum dos dois é verde: a W5c não segue para o
SIGN sem PASS; o CEO refaz (mesmo pré-registro) ou leva ao Owner.

**Critério de vermelho.** O resultado é VERMELHO (FAIL) se, e só se, a validade está
satisfeita e `taxa(5.5) < taxa(5) − 0,10` (células C3/C4). O custo nunca produz
FAIL sozinho: acima de 1,2× ele é DECLARADO (C2). INVÁLIDO e INCONCLUSIVO não são
vermelho nem verde: são «não medido».

**Efeito teto e poder (declarados).** Na S357 o Opus 5.5 em xhigh achou 19 de 20:
o instrumento detecta PIORA, não melhora. Com 20 revisões por braço, o intervalo de
95% de uma diferença de taxas tem ordem de ±20 pontos; δ = 10 pontos é uma REGRA DE
DECISÃO para piora grosseira, não um teste estatístico de não-inferioridade. Se o
Sonnet 5 ficar baixo (por exemplo, abaixo de 10 em 20), o resultado vale do mesmo
jeito, com essa observação no LEDGER.

**Controles vermelho→verde do instrumento (já rodados, sem gasto).**
`build-items.py --check` roda o executor, o cegamento e o placar contra um `claude`
FALSO e exige, entre outros: id servido trocado ⇒ inválido; chave extra de modelo ⇒
inválido; variante `[1m]` ⇒ válido; 3 tentativas e esgota; estouro de orçamento ⇒
vazio; teto do run ⇒ recusa sem chamar o CLI; versão do CC diferente ⇒ recusa sem
chamar; binário com outro sha256 ⇒ recusa sem chamar, e registro com sha do binário
divergente ⇒ INVÁLIDO no placar; ambiente do sujeito com `DISABLE_AUTOUPDATER=1`;
prompt adulterado ⇒ recusa; resposta adulterada ⇒ o cegamento recusa;
ensaio válido nunca é repetido; respostas cegas sem nome de modelo; 18 × 16 ⇒ C1;
18 × 15 ⇒ C3; custo 1,3× ⇒ C2; sem tokens ⇒ custo por `total_cost_usd` em todos;
custo zero ⇒ INCONCLUSIVO; controle do avaliador errado ⇒ INCONCLUSIVO; 5
vazios num braço ⇒ INCONCLUSIVO e 4 ⇒ decide; registro de autoteste num run real ⇒
INVÁLIDO. Cada uma dessas afirmações foi provada vermelha por mutação do código
(o mutante correspondente faz o `--check` falhar) — registro no retorno da FD-08.

---

## 6. Registro no LEDGER depois do S2

Uma entrada datada na seção `## W5c.1` do `LEDGER.md` do PLAN-194 com: o veredito e
a célula; `taxa` e `válidos` por braço; `C`; partials, falsos positivos e recusas
por braço; vazios e inválidos por braço, com as causas; o sha256 de
`OUT/score.json`; o substrato do §4; os ids servidos; e qualquer desvio do
procedimento do §7, nomeado.

---

## 7. Como rodar (S2)

Pré-condições: este pacote landado; Lote 0 aplicado (Claude Code congelado em
2.1.288 com `DISABLE_AUTOUPDATER=1` no `env` do settings do usuário);
`python3 build-items.py --substrate` com rc 0 (versão e binário conferem) e
`python3 build-items.py --check` verde no
checkout que vai rodar.

1. Escolher um diretório de run FORA do repositório (no scratchpad da sessão) e um
   sal novo de 16 a 64 caracteres `[A-Za-z0-9]` (por exemplo, a saída de
   `python3 -c 'import secrets; print(secrets.token_hex(16))'`). O sal só aparece no
   lançamento e no retorno; nunca é commitado antes da avaliação.
2. Lançar o Workflow com `scriptPath` = `<checkout>/.claude/plans/PLAN-194/w5c1/wf-model-ab.js`
   e `args` = `{confirm_spend: true, run: "S2-<data>", out: "<diretório do run>",
   instrument_dir: "<checkout>/.claude/plans/PLAN-194/w5c1", blind_salt: "<sal>"}`.
3. Ao terminar, conferir `OUT/score.json` (o sha256 vem no retorno) e registrar no
   LEDGER (§6). Os registros `OUT/runs/*.json` são a evidência; o retorno do
   Workflow é conveniência.

Fases: Preflight (sem gasto) → Run (40 ensaios pagos, 2 lotes) → Blind → Grade
(10 avaliadores) → Score (com 1 passada extra de avaliação por item cujo controle
falhar).

---

## 8. Riscos e resíduos declarados

- **R1 — v2 ≠ S357.** Os recortes v2 são novos (determinísticos); os números da S357
  não são comparáveis aos deste run. O que se compara é Sonnet 5 × Sonnet 5.5.
- **R2 — chaves escritas por quem cortou os recortes.** Mitigação: critérios
  `found_if`/`partial_if` explícitos, escritos antes do gasto e pinados; refutador do
  rail R-1 antes do LAND.
- **R3 — avaliador do mesmo fornecedor e cegueira por regra.** O avaliador é um agente
  Claude com ferramentas: a cegueira vem dos rótulos opacos, da redação de nomes de
  modelo e da regra «não leia `runs/`»; um avaliador que a quebrasse poderia
  desanonimizar. O controle por item pega avaliador «sempre sim/sempre não», não viés
  sutil.
- **R4 — revisão de trecho em rodada única, sem ferramentas.** Mede revisão de código,
  não sessão agêntica longa (igual à S357).
- **R5 — níveis de esforço recalibrados no Sonnet 5.5.** O mesmo rótulo `xhigh` pode
  não significar a mesma profundidade; a pergunta é sobre a configuração que o
  repositório usaria, não sobre esforço equivalente.
- **R6 — cota e rede.** Dois lotes em paralelo na mesma conta podem dar 429 (a S357
  perdeu 10 tentativas por limite de sessão e 3 por queda de rede); as tentativas cobrem, e a V4 decide se não cobrirem.
  Valores em dólar são equivalentes de API; o limite real é a cota da assinatura.
- **R7 — Workflow com agentes que escrevem.** Os agentes escrevem SÓ no diretório do
  run, fora do repositório, e só pelos comandos do `build-items.py`; nenhuma escrita
  no repositório. O `wf-model-ab.js` valida a gramática reduzida do ADR-191 antes de
  cada despacho (bloco COMMON).
- **R8 — `ANT-02` não medida.** Resíduo declarado (D-10); as sondas pagas do adapter
  ficam para a 1.4.4.

---

## 9. Re-versão 2026-10-02 (CC 2.1.288)

**O que mudou: só o substrato.** Itens, recortes, prompts, controles, plano, δ, regra
de custo, regras de validade e células ficam como estavam. Os sha256 de `source`,
`prompt` e `control` dos 10 itens são os MESMOS da versão anterior; os prompts que o
sujeito recebe são byte a byte os mesmos. Mudaram:

| o quê | antes (landado em `db346fc6` + `2a01a558`) | agora |
|---|---|---|
| versão do Claude Code exigida | `2.1.287 (Claude Code)` | `2.1.288 (Claude Code)` |
| sha256 do binário | só registrado no LEDGER | PINADO e conferido em cada ensaio e no placar: `bbe93063f7a0879a1021b2891e5c9354e5b3b98433e32efe6750f7710afed750` (o realpath de `claude`; no 2.1.287 era `6eab8333fe2121553100d8f40bfada384a3e989b94f947e18ba6677a6fcb41ea`) |
| ambiente do sujeito | sem `DISABLE_AUTOUPDATER` | `DISABLE_AUTOUPDATER=1` no processo do `claude -p` (motivo abaixo, ponto 6) |
| pré-voo | `claude --version` | `build-items.py --substrate` (versão + sha256 do binário, rc 0 só se os dois conferem) |
| `INSTRUMENT_VERSION` | `w5c1-v2` | `w5c1-v2.1` (por isso só o sha256 das CHAVES muda: o campo `instrument` está nelas) |
| digest do manifesto | `5117525e78144e7fbc7388d668c4215a9c5ca8d82eca947423a4a621ad837d7f` | o do §3 |
| sha256 dos arquivos | `PREREG.md` `b54857fb…9703`, `build-items.py` `edd38a45…d63d`, `wf-model-ab.js` `a67e84be…bde7d1` (`SHA256SUMS` `d9f9dfc1…2579`) | os de `SHA256SUMS` |

**Por quê.** O Claude Code 2.1.287 se atualizou sozinho para o 2.1.288 em 2026-10-02
(binário novo gravado às 20:31:44Z) e o Owner decidiu ADOTAR o 2.1.288 e congelá-lo com
`DISABLE_AUTOUPDATER=1`. A versão anterior exigia exatamente o 2.1.287 e recusava
antes do gasto (fail-closed, como desenhado); o refutador do rail R-1 apontou isso.
Esta re-versão é o caminho que o próprio pré-registro prevê («ajuste antes do gasto
entra como nova versão»), não uma edição por cima: os valores antigos ficam
registrados na tabela acima e no histórico git.

**NENHUM ensaio pago foi rodado antes desta re-versão.** O S2 não começou; nenhum
`claude -p` foi chamado por este instrumento em nenhuma versão.

**Re-medição 2.1.287 × 2.1.288.** Fonte NORMATIVA (durável, versionada): a seção
«CC 2.1.288 — adoção e re-medição 287 × 288 (2026-10-02, S362)» do
`.claude/plans/PLAN-194/LEDGER.md`, landada no commit
`8e9f1115ae76e5ff74e868c5a7f156d47587c3de` (leitura do código minificado dos dois
binários; o único comando executado foi `--version`; itens (1) a (6)). Medição bruta da
sessão S362, NÃO versionada e só como rastro: `cc288.json`, sha256
`79228c6011de7da84099fe26a191d3569f0dc00866ac7ed7331c4c82cb2e235b` (não é copiado para o
repositório: carrega caminhos absolutos da máquina). Os itens do LEDGER, lidos contra o
que o instrumento usa:

| item do LEDGER | 287 × 288 | efeito no instrumento |
|---|---|---|
| (1) varredura `cleanupPeriodDays` | igual | nenhum: o instrumento grava fora de `~/.claude/projects/` e usa `--no-session-persistence` |
| (2) `workflowSizeGuideline` | igual (texto byte-idêntico) | nenhum: o workflow tem 15 despachos (até 26 com repasses de avaliação), no máximo 10 em paralelo; o guideline não é imposto |
| (3) loader de settings | igual | nenhum: o sujeito roda com `--setting-sources ""` |
| (4) watchdog do Workflow (600 s, pausado com ferramenta em voo) e concorrência | igual | nenhum: os comandos dos agentes têm limite de 600 s |
| (5) mudanças periféricas (`autoCompactWindow` por modelo, `/restart`, espera de quota do subagente de Workflow atrás de flag de servidor com padrão desligado) | só adições | nenhum na regra: nada toca `claude -p`, `--effort`, `availableModels`, a varredura ou o atualizador; uma espera de quota só atrasaria o run |
| (6) `DISABLE_AUTOUPDATER` | ainda desliga o atualizador, MAS não vale sob `--setting-sources` sem `user` | **afeta**: o sujeito roda com `--setting-sources ""`, então o congelamento do Owner não chegaria a ele. Cura nesta re-versão: o instrumento põe `DISABLE_AUTOUPDATER=1` no ambiente do próprio processo (a medição bruta lê o predicado em `process.env.DISABLE_AUTOUPDATER` nas duas versões). Uma troca de versão no meio do run seria pega de qualquer jeito (versão e binário conferidos antes de cada ensaio ⇒ V1), mas desperdiçaria gasto |

**`claude --help` do 2.1.288** (rodado em 2026-10-02, sem chamada à API): lista
`--tools` («Use "" to disable all tools»), `--permission-mode` com a escolha
`manual`, `--setting-sources`, `--strict-mcp-config`, `--mcp-config`,
`--max-budget-usd`, `--no-session-persistence`, `--output-format`, `--model` e
`--effort` com `xhigh`; `claude --version` = `2.1.288 (Claude Code)`; sha256 do
binário resolvido = `bbe93063…d750`, igual ao pino.

**Controles da re-versão (sem gasto).** `build-items.py --check` verde. Quatro
mutantes, cada um vermelho nomeado no `--check`: conferência do binário desligada no
ensaio (`cc-binary-refused`), conferência do binário desligada no placar
(`binary-pin-in-score`), `DISABLE_AUTOUPDATER` fora do ambiente do sujeito
(`child-env-disables-autoupdate`) e o pino de versão de volta ao 2.1.287 (o
autoteste aborta). A simulação do runtime do Workflow continua verde (17 despachos,
plano igual ao do Python) e recusa no pré-voo uma versão 2.1.287, um binário com
outro sha256 e um digest errado.

**Resíduo P3 declarado (refutador do rail R-1, re-versão `f8bf170c`): janela entre o
sha256 e a execução do binário.** O executor calcula o sha256 do `realpath` de `claude`
e, em seguida, executa `claude`; a conferência e a execução NÃO são uma syscall só. Uma
troca do symlink (ou do binário) nessa janela faria um ensaio rodar noutro binário com o
registro dizendo o pino. Uma troca que PERSISTE custa só gasto, nunca um PASS: a versão e
o binário são relidos antes de cada ensaio, o ensaio seguinte vira `instrument_error`, e o
placar exige TODOS os registros no pino de versão e de binário (V1 ⇒ run INVÁLIDO).
Precisão: só uma troca de ida e volta dentro da janela de um ÚNICO ensaio (milissegundos
entre o sha256 e a execução, desfeita antes da conferência seguinte) passaria sem
registro — isso exige ação deliberada sobre o symlink, não acontece por atualização com
o Claude Code congelado (Lote 0), e afetaria no máximo um dos 40 ensaios. Fechar a janela
pediria executar pelo descritor do arquivo conferido, o que o `claude` nativo não oferece.
