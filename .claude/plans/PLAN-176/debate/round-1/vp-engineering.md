---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — o arquétipo não tem bloco de persona em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-06T04:10:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O arquivo que o brief chama `PLAN-176.md` **não existe**; o plano vive em
  `.claude/plans/PLAN-176-model-currency-refresh.md` (161 linhas). Verifiquei o
  núcleo do desenho em disco: **o split T/P é SÓLIDO por construção** —
  `.claude/governance/*.json` casa `_CANONICAL_GUARDS`
  (`check_canonical_edit.py:234`) e `.claude/data/**` não casa padrão nenhum
  dos 72. A premissa central do §1/§2 é verdadeira, e é o melhor pedaço do plano.
- **Onde é forte:** a cerimônia é preservada por PATH, não por convenção; os
  kill criteria incluem controle de falso-NEGATIVO (fixture injetada), que é a
  metade que quase todo plano esquece; a fase-2 (auto-merge) está explicitamente
  fora e gated em ADR.
- **Onde é fraco:** (a) o **enforcer** do split nasce FORA da cerimônia que ele
  protege; (b) a W1 propõe injetar REDE no único instrumento cujo desenho de
  segurança é «zero side effects, argv hardcoded» (achado Codex R2 P0); (c) o
  ADR-114 citado como controle de egress **não cobre a forma de egress da W1**;
  (d) o plano tem **zero linhas `Check:`** e zero checkboxes — o gate mecânico da
  `PLAN-SCHEMA.md` §13, que se aplica a ele, é vacuamente verde.

## Risks

**R-VP1 — CRITICAL — O lint que sustenta o split T/P é editável SEM cerimônia.**
Rodei a lista de guards contra os entregáveis do W0: `models-registry.json` →
CANONICAL (`.claude/governance/*.json`), `_lib/model_registry.py` → CANONICAL
(`.claude/hooks/*.py`), mas **`check-model-literals.py` → LIVRE** (nenhum dos 72
padrões casa `.claude/scripts/check-*.py`; os únicos scripts guardados são
nominais — `lessons.py`, `prune-lessons.py`, `lesson-restore.py`,
`lesson_ranker.py`, `check_canonical_edit.py:130-133`). O plano protege a camada
T e deixa **o guarda da fronteira T/P desprotegido**: um agente enfraquece o
ratchet, e o `models-registry.json` continua sentinel-gated protegendo um
perímetro que ninguém mais vigia. Este repo já pagou exatamente isto e já tem a
cura: `verify-counts.sh` virou membro do manifesto ADR-192
(`.claude/governance/gate-scripts-manifest.txt`, 9 membros hoje).
*Mitigação:* `check-model-literals.py` entra em
`.claude/governance/gate-scripts-manifest.txt` **no MESMO patch do W0** (o
manifesto é `.claude/governance/*.txt` ⇒ canonical, logo o bump viaja na mesma
assinatura). Sem isso o split é uma porta blindada num batente de papelão.

**R-VP2 — CRITICAL — A W1 injeta rede no instrumento projetado para não ter nenhuma.**
`check-substrate-watch.py` (path REAL: `.claude/scripts/check-substrate-watch.py`
— o plano não o localiza) documenta o oposto do que a W1 quer:
«Probing is OPT-IN (`--probe-installed`): by default the checker does NOT run any
version command (**zero side effects**, suitable for the read-only nightly agent)»
e «the argv is hardcoded in `_PROBE_ARGV` … **the ledger can NEVER supply a
command (Codex R2 P0)**» (`:27-32`). `grep -nE "urllib|requests|http|urlopen"`
sobre o arquivo retorna **zero**. A W1 diz «este plano APENAS estende
`check-substrate-watch.py` com o probe upstream faltante» (§2 W1, linhas 66-68):
isso transforma um script *local, opt-in, sem side effects* no **primeiro
consumidor de rede** do repo, herdando o ledger como superfície de entrada. O
achado R2 P0 que endureceu esse arquivo existe justamente porque o ledger não
pode virar canal de comando.
*Mitigação:* o fetcher com rede é um **módulo NOVO e separado**
(`.claude/scripts/fetch-model-feeds.py`), sem import do substrate-watch; o
substrate-watch continua no-network e apenas **lê** o ledger que o fetcher
escreve. Estender vs. adjacente não é gosto: é a diferença entre preservar e
destruir a propriedade «zero side effects» que um rail já certificou.

**R-VP3 — CRITICAL — O ADR-114 não é o controle de egress desta wave (categoria errada).**
O §2 W1 declara «Revisão ADR-114 no debate de abertura» e o brief o chama de
«redactor». Lido em disco, o ADR-114 é *Codex MCP egress redaction symmetry*:
seu objeto são os **prompts que o framework envia ao Codex** contendo «source
code fragments, evidence quotes, secrets … (audit-log HMAC keys, sentinel signer
fingerprints)» (`ADR-114:20-24`), wired em `codex_invoke.py:invoke_codex()` e
`check_pair_rail.py:325-363`. A W1, pela sua PRÓPRIA garantia (linhas 73-78), é
«GET-only, SEM body, SEM query params …, SEM headers customizados». **Uma
requisição sem body e sem headers não tem o que redigir.** As duas afirmações não
podem ser ambas load-bearing: ou o redactor é inaplicável (e a W1 está sem
controle de egress declarado), ou a garantia GET-only é falsa. Como está, o plano
cita um controle que não toca a superfície.
*Mitigação:* nomear o controle REAL da W1 — que é de **ingress**, não egress
(allowlist de host/path, sem redirect cross-host, cap de tamanho/timeout, digest
sha256, parse fail-closed — tudo já escrito nas linhas 69-73) — e remover o
ADR-114 da W1. Se algum dado local passar a sair, aí sim o ADR-114 volta, e a
garantia «NADA do repo sai» cai junto.

**R-VP4 — HIGH — O plano está sujeito ao gate §13 e o evade por FORMATAÇÃO.**
`PLAN-SCHEMA.md` §13.4: o gate vale para `created: >= 2026-06-12` **e** `status ∈
{draft, reviewed, executing}`. PLAN-176 tem `created: 2026-08-11` e
`status: reviewed` (`:5,7`) ⇒ **está dentro**. Medido no arquivo:
`grep -cE '(^|[^\w])Check:\s*\S'` = **0** e `grep -cE '^\s*- \[[ x]\]'` = **0**.
Zero checkboxes = zero unidades de execução enforced = **gate vacuamente verde**.
Os ACs da §3b («AC: relatório lista os 3 CLIs…», «AC: nunca bloqueia») são prosa
sem comando; nenhum deles pode ficar VERMELHO por máquina. É a bandeira vermelha
literal do meu escopo: um AC cujo Check não pode reprovar.
*Mitigação:* converter §3b em checkboxes sob um heading `## Waves` (§13.3 exige
título começando com `wave`/`items`/`progress log`/`sprint plan`) com uma linha
`Check:` por unidade, ou `Check: none (doc-only)` explícito. Enquanto forem
parágrafos, a §3b declara intenção, não aceite.

**R-VP5 — HIGH — O oráculo do W0 nasce VERMELHO no HEAD, e o plano não pré-registra isso.**
O W0 promete o oracle «`replacements ⊆ valid_override_ids`» (`:47-48,62`). Medido:
`model-deprecations.json` recomenda `['claude-haiku-4-5-20251001',
'claude-mythos-5', 'claude-opus-4-8-fast', 'claude-opus-5', 'claude-sonnet-5',
'gpt-5.6-sol']`, enquanto `_VALID_MODELS`
(`.claude/hooks/_lib/codex_cli_shape.py:97-105`) é `('gpt-5.5', 'gpt-5',
'gpt-5-mini', 'gpt-5-codex', 'o3', 'o3-mini', 'o4-mini')`. `gpt-5.6-sol` **não
está lá** — e o CLI que roda hoje (GPT-6 Astra) tampouco. O oráculo, escrito como
está, reprova no minuto em que existir. Um W0 que lande vermelho por desenho
precisa do padrão que este repo já tem: um conjunto EXATO de REDs esperados
(`ownership-expected-reds.txt` + `ownership-nightly-gate.sh`, que falha em
QUALQUER diferença).
*Mitigação:* ou o W0 cura os literais como parte do escopo (aí não é mais «sem
rede + 8 paths»), ou publica `models-expected-reds.txt` com os ids exatos e a
causa de cada um. «Verde na chegada» não é opção; escolher entre as duas é
decisão do Owner, não do executor.

**R-VP6 — HIGH — `env` na cadeia de precedência é um canal de override não autenticado ACIMA da camada auditada.**
§1: «Precedência: **caller > env > preference > default do schema**» (`:44-45`).
`env` vence o arquivo que passa por PR auditado. O plano não nomeia quais
variáveis, nem um prefixo, nem quem as valida, nem se a camada T é servida pelo
mesmo resolvedor. Este repo mediu duas vezes, na S345, que env é superfície de
bypass real: os dois bypasses de autenticação dos gates da W4b foram
`argparse.py` em `sys.path[0]` e **`BASH_ENV`** (CLAUDE.md §5), e a S321/S322
gastou uma wave neutralizando `CLAUDE_PROJECT_DIR_NATIVE` no import
(`WHOLE_DIR_OVERRIDE_CARRIERS`). Um resolvedor de modelo com `env` acima de
`preference` e sem allowlist reintroduz a classe.
*Mitigação:* nomear o conjunto FECHADO de variáveis lidas (prefixo único), fazer
o resolvedor **recusar servir chaves da camada T por env** (T só por id concreto
no call-site) e registrar cada override por env num evento de auditoria. Se a
precedência ficar como está, o ADR-149-A2 declara explicitamente que env é um
canal confiável — e assume o custo.

**R-VP7 — HIGH — «Fail-closed p/ default» é DEGRADAÇÃO SILENCIOSA, não fail-closed.**
§1 diz que valores P fora do schema são «fail-closed p/ **default**» (`:44-45`) e
§1 também diz «TTL vencido = advisory» (`:45`). Ambas as regras terminam no mesmo
lugar: o sistema **continua rodando com outro modelo** e nada fica vermelho. Como
`.claude/data/**` não é sentinel-gated (medido: NO MATCH nos 72 padrões) e a
rotina da W1 escreve ali via PR, um valor P errado/hostil que passe no merge
produz **downgrade de modelo em silêncio** — a classe «instrumento verde cuja
PERGUNTA envelheceu» que o índice de memória lista nominalmente. O §3 gateia o CI
apenas contra PR que **toca o arquivo T**; não há gate declarado que valide os
VALORES de P contra o schema T **no CI**.
*Mitigação:* separar os dois desfechos — schema-inválido é **erro alto** (CI
vermelho no PR + breadcrumb em runtime), TTL vencido é advisory. E adicionar ao
§3 o gate que falta: CI valida `models-preference.json` contra o schema em T a
cada PR, com controle positivo (valor fora do schema ⇒ vermelho provado).

**R-VP8 — MEDIUM — Os kill criteria não têm dono, contador nem arquivo de estado.**
§3 lista sete gatilhos, e **nenhum** nomeia o instrumento que os mede:
«>2 falsos-positivos/mês ⇒ desativa auto-abertura» (quem conta? onde fica o
contador?); «3 falhas consecutivas de um vendor ⇒ lane desabilitada» (qual
arquivo guarda o streak, e quem o zera?); «fixture de lançamento conhecido
injetado ⇒ a rotina TEM de detectá-lo» (mensal — disparado por quê? o nightly
citado na mesma linha é outro job). Um kill criterion sem contador persistido e
sem dono é uma intenção: na hora do incidente ninguém sabe se o limiar foi
cruzado. Contraste com o padrão que funciona neste repo: `ownership-nightly-gate.sh`
compara um conjunto EXATO contra um arquivo rastreado.
*Mitigação:* cada gatilho ganha (a) um arquivo de estado rastreado, (b) o comando
que o lê, (c) quem desativa a lane — no texto do plano, antes do W1.

**R-VP9 — MEDIUM — A garantia de egress cobre a W1 e cala sobre a W2, que é a wave que de fato envia dados.**
A frase «NADA do repo (nem números de versão locais) sai em requisição alguma»
(`:75-77`) está no bloco da W1. Mas a W2 «abre PR» carregando «o
relatório+digests como evidência» (`:82-83`) — isto é, uma requisição **POST com
body contendo conteúdo derivado do repo**, para um serviço externo, feita por uma
rotina cloud. Não é necessariamente errado (é o próprio repo do Owner), mas o
plano apresenta uma garantia absoluta de egress cujo escopo real é uma wave só,
sem dizê-lo. Um leitor futuro cita a frase e conclui coisa falsa sobre a W2.
*Mitigação:* escopar a frase («na COLETA de feeds da W1…») e declarar em uma
linha o egress da W2: destino, o que vai no body, e que o relatório passa por um
redactor antes de virar corpo de PR (aqui, sim, o ADR-114 é o precedente certo).

**R-VP10 — MEDIUM — Duas tabelas de modelo no MESMO diretório, e o plano não diz qual vence.**
O W0 quer criar `.claude/data/models-preference.json`. Já existe
`.claude/data/canonical_models.json` — e ele está **vencido**: seu campo de
staleness marca `2026-09-01` (hoje é 06/09) e `'opus-5'/'sonnet-5'` não aparecem
no arquivo (medido por leitura do JSON). O próprio §4 do plano previu isto
(«`canonical_models.json` sem gen-5 e expirando 01/09», `:155-156`), mas o §2 W0
não diz se o arquivo novo **substitui**, **absorve** ou **convive** com ele. É a
forma exata dos defeitos D1–D4 da S322–S327 registrada no CLAUDE.md §5: a ORIGEM
ganha dono, a ROTA não — e um segundo leitor resolve pela fonte velha.
*Mitigação:* o W0 declara o destino de `canonical_models.json` (migrado e
apagado, ou explicitamente fora da classe com o motivo) e o lint do W0 trata um
segundo arquivo de modelos em `.claude/data/` como VERMELHO.

**R-VP11 — MEDIUM — `trig_014Y…` é uma figura sem fonte, e a rotina «irmã» talvez não exista.**
`:106-107` ancora o AC da W1 em «rotina registrada (RemoteTrigger, irmã da
substrate-watch `trig_014Y…`)». O id está **truncado com reticências** no texto do
plano e não aparece em nenhum arquivo rastreado (`git ls-files | grep -i
substrate` devolve só planos, o checker, o JSON e docs). Um AC cujo antecedente é
um id irrecuperável não é verificável por quem executar a wave daqui a um mês.
*Mitigação:* o id completo entra no plano, ou o AC passa a referenciar a
CONFIGURAÇÃO da rotina (nome + cron + repositório) em vez de um handle opaco.

**R-VP12 — LOW — O W0, como especificado, é um pacote canônico no limite do modelo v2.**
Classifiquei os prováveis paths do W0 contra os guards: `models-registry.json`,
`_lib/model_registry.py`, o teste do resolver, `validate.yml`, o ADR-149 e o
`gate-scripts-manifest.txt` são **canônicos** (6); `models-preference.json`,
`check-model-literals.py` e seu teste são livres (3). Nove paths, seis exigindo
UMA assinatura GPG — acima do teto de 8 paths do modelo de operação v2 e, na
noite corrente, sem assinatura possível.
*Mitigação:* cortar o W0 em **W0a** (registry T + resolver + teste + ADR-149-A2 —
canônico, uma assinatura) e **W0b** (preference P + lint + teste + bump do
manifesto), com o W0b consumindo o W0a. O lint sem o registry não tem o que
validar, então a ordem é forçada e não há ambiguidade.

## Must-fix (blocking)

1. **Pôr `check-model-literals.py` no manifesto ADR-192 no mesmo patch do W0
   (R-VP1).** O enforcer da fronteira T/P não pode ser a única peça do desenho
   editável sem cerimônia.
2. **Tirar a rede de dentro do `check-substrate-watch.py` (R-VP2).** Fetcher novo
   e separado; o substrate-watch permanece no-network e só LÊ o ledger. A
   propriedade «zero side effects / argv hardcoded» foi certificada por um rail
   (Codex R2 P0) e não se revoga de passagem.
3. **Trocar o ADR-114 pelo controle real da W1 (R-VP3).** Nomear os controles de
   INGRESS já escritos e remover a citação do redactor de egress, que não tem o
   que redigir numa requisição sem body e sem headers.
4. **Converter os ACs da §3b em checkboxes com linha `Check:` (R-VP4).** O plano
   está dentro do gate §13 da `PLAN-SCHEMA.md` e hoje passa por não ter unidades.
5. **Resolver o oráculo que nasce vermelho (R-VP5):** ou curar os literais dentro
   do W0, ou publicar o conjunto EXATO de REDs esperados, no molde de
   `ownership-expected-reds.txt`. Decisão do Owner.
6. **Fechar a cadeia de precedência (R-VP6):** conjunto fechado de variáveis de
   env, recusa de servir a camada T por env, e evento de auditoria por override.

## Nice-to-have (advisory)

1. Separar «schema-inválido = vermelho alto» de «TTL vencido = advisory»
   (R-VP7), e gatear os VALORES de P no CI com controle positivo.
2. Dar a cada kill criterion um arquivo de estado, um comando e um dono (R-VP8).
3. Escopar a frase de egress à W1 e declarar em uma linha o egress da W2
   (R-VP9).
4. Declarar o destino de `canonical_models.json` (R-VP10) — hoje vencido em
   01/09 e sem gen-5.
5. Completar ou substituir o id `trig_014Y…` (R-VP11).
6. Cortar o W0 em W0a (canônico) e W0b (livre) para caber no modelo v2 (R-VP12).
7. Corrigir os dois paths errados do próprio texto: o plano se refere a
   `check-substrate-watch.py` sem diretório (é `.claude/scripts/`), e o brief da
   sessão aponta `PLAN-176.md`, que não existe.

## Unseen by the original plan

1. **O guarda da fronteira fica fora da cerimônia que protege.** O plano
   verificou (corretamente) que T é gated e P não é, mas não perguntou se o LINT
   é gated. Não é.
2. **`check-substrate-watch.py` foi endurecido contra exatamente o que a W1 quer
   fazer com ele** — o comentário `:27-32` é a memória de um achado P0 de rail.
3. **O ADR-114 é sobre prompts para o Codex, não sobre fetch HTTP.** A citação
   sobrevive há 4 revisões (r4/r5) sem ninguém abrir o ADR.
4. **O oráculo `replacements ⊆ valid_override_ids` reprova no HEAD** —
   `gpt-5.6-sol` não está em `_VALID_MODELS`, e o CLI que roda hoje (GPT-6 Astra)
   tampouco. O plano trata o oráculo como neutro.
5. **`canonical_models.json` já venceu** (staleness `2026-09-01`, hoje 06/09) e
   mora no diretório onde o W0 quer criar a camada P.
6. **Zero checkboxes ⇒ o gate §13 é vacuamente verde**, num plano que ele
   deveria cobrir por `created` e `status`.
7. **`env` vence `preference`** — a única perna da precedência que ninguém
   assina e ninguém audita.
8. **`task-route.py:511-551` ainda roteia VETO holders para `claude-opus-4-8` /
   `claude-sonnet-4-6`** — o item do anexo §4 continua vivo e não tem AC em
   nenhuma wave deste plano.

## What I would NOT change

- **O split T/P por PATH.** Verifiquei os dois lados contra os 72 padrões de
  `_CANONICAL_GUARDS`: T casa, P não casa. «Preserva a cerimônia POR CONSTRUÇÃO»
  é uma afirmação **verdadeira e mecanicamente checável** — o oposto do padrão
  de plano que promete disciplina. Não trocar por convenção nem por um flag.
- **O controle de falso-NEGATIVO mensal** (fixture de lançamento conhecido
  injetada). É a metade que quase todo desenho de detector esquece, e sem ela
  «nenhum lançamento detectado» e «detector morto» são indistinguíveis.
- **Fase 2 (auto-merge) FORA, gated em ADR próprio.** A wave que escreve sozinha
  é categoricamente diferente da que propõe; manter a fronteira.
- **A recusa de double-booking com o substrate-watch** (nenhum fetcher paralelo
  de CLI). O instinto está certo — é a implementação (R-VP2) que precisa mudar,
  não a regra.
- **`W1-W3` só abrem com o W0 landado.** A dependência dura, corrigida no r4 de
  «pendurada» para explícita, é o sequenciamento certo: sem registry não há o que
  a rotina proponha.
- **A obrigatoriedade do `/debate` L3 na abertura por causa do egress.** É a
  razão desta rodada existir e ela se pagou: três dos seis blocking acima só
  aparecem quando alguém abre os arquivos citados.
