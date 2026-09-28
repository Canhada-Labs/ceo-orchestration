# pin-0156-approved — sentinel do re-pin do codex CLI 0.155.0 → 0.156.1

Plan: PLAN-193
Wave: W2 — re-pin codex-cli 0.155.0 → 0.156.1
Anchor-SHA: (preenchido pelo OWNER-PIN-SIGN.sh no momento da assinatura)
Data: (preenchida pelo OWNER-PIN-SIGN.sh no momento da assinatura)

## Ratificação (Owner, 2026-09-22 e 2026-09-23)

Pedido registrado verbatim no `PLAN-193` §Context (S357): «[…] e ajusta os
pontos emergenciasi pra gente atualizar esse modelo e tbm a ultima versao do
codex, para os usuarios terem acesso rapido. precisamos evoluir.» Escopo
escolhido na mesma sessão: «Modelo + Codex + via expressa». Este pack é o W2
daquele plano e cobre só o Codex.

Em 2026-09-23 (S357), o Owner instalou globalmente o codex-cli 0.156.1 — o
payload global confere byte a byte com o tarball do registry (seção «Evidência
dos digests»). Antes dessa instalação, o W2 estava escrito para o 0.156.0 num
rascunho do plano que nunca foi commitado; este pack foi montado primeiro
para o 0.156.0 (nunca assinado) e remontado para o 0.156.1, a versão
instalada e a `latest` do npm na medição da seção «Evidência dos digests».

A OQ-4 do plano (re-pin e wave-opus55 no mesmo sentinel ou em duas
cerimônias) foi registrada aberta, com o padrão do CEO de duas cerimônias;
este pack é a cerimônia própria do re-pin, e assiná-lo resolve a OQ-4 nesse
sentido. O motivo que a OQ-4 dava naquele rascunho não commitado
(2026-09-22) — o `npm i -g` imediatamente antes do SIGN — deixou de valer: o
Owner instalou o 0.156.1 antes de o pack ser remontado.

Medido em 2026-09-23, com o codex-cli 0.156.1 instalado globalmente e cópias
do registry (0.156.1 e 0.155.0) baixadas por `npm pack` para o diretório
temporário da sessão, sem instalar:

    check_pair_rail.py --verify-codex-pin
    manifesto VIVO x 0.156.1 instalado
      -> {"status": "mismatch", "detail": "payload_sha256_mismatch"}   rc=1
    manifesto VIVO x 0.156.1 do registry
      -> {"status": "mismatch", "detail": "payload_sha256_mismatch"}   rc=1
    manifesto NOVO (deste pack) x 0.156.1 instalado
      -> {"status": "verified", "detail": "ok", ...}                   rc=0
    manifesto NOVO x 0.156.1 do registry
      -> {"status": "verified", "detail": "ok", ...}                   rc=0
    manifesto NOVO x 0.155.0 do registry
      -> {"status": "mismatch", "detail": "payload_sha256_mismatch"}   rc=1
    manifesto VIVO x 0.155.0 do registry
      -> {"status": "verified", "detail": "ok", ...}                   rc=0
    manifesto da montagem para 0.156.0 x 0.156.1 instalado
      -> {"status": "mismatch", "detail": "payload_sha256_mismatch"}   rc=1

Cada célula foi medida de dois jeitos, com o mesmo resultado: pelas costuras
de teste do próprio verificador (`CEO_PAIR_RAIL_TEST_MODE=1` +
`CEO_PAIR_RAIL_PIN_MANIFEST`) e SEM costura (`CLAUDE_PROJECT_DIR` apontando
para um diretório cujo `.claude/governance/` contém o manifesto da célula). As
cópias do registry estavam em layouts npm com a mesma forma do global
(launcher `bin/codex.js` → payload em
`node_modules/@openai/codex-darwin-arm64/`). Ou seja: com o 0.156.1 instalado,
o manifesto vivo fecha o pair-rail (fail-CLOSED), e este manifesto o reabre.

## Scope

- `.claude/governance/codex-cli-pin.txt` — range `>=0.128.0,<0.156.0` →
  `>=0.128.0,<0.157.0` (limite inferior INALTERADO), com o motivo, a decisão
  sobre o corpus e a consequência declarados num parágrafo novo do cabeçalho.
- `.claude/governance/codex-cli-pin-manifest.json` — `package_version`
  0.156.1, `npm_integrity` do artefato de PLATAFORMA e `sha256` do payload
  `aarch64-apple-darwin`, regenerados do tarball real do registry.

Nada além desses dois arquivos canônicos, deste sentinel e da sua assinatura
entra no commit da cerimônia. O script recusa rodar com qualquer variável git
herdada que o próprio git declara local ao repositório
(`git rev-parse --local-env-vars`: diretório, árvore, índice, objetos e config
por ambiente), roda as próprias operações git com os hooks do git e o
fsmonitor desligados (`core.hooksPath=/dev/null`, `core.fsmonitor=false`),
confere antes de assinar que a árvore de trabalho não difere do HEAD
(`git diff` contra o HEAD sobre um índice temporário lido dele, sem confiar nos
bits assume-unchanged/skip-worktree do índice de quem rodou), congela cópias
dos bytes
verificados e assinados, monta a árvore do commit a partir delas por plumbing
(índice temporário, blobs gravados sem filtros), confere essa árvore contra o
escopo exato e em bytes ANTES de o `main` avançar — e ele só avança por
compare-and-swap sobre o HEAD pré-cerimônia —, e depois confere de novo o
escopo do commit e que a árvore de trabalho bate com ele.

## Bytes que esta assinatura cobre

O script recusa aplicar se qualquer um destes não bater (guard de deriva):

    vivo   codex-cli-pin.txt                 c7c7e87fe679432677d5ff21522ccb34e6a8e6b1d468c8c12064bdb2a642f595
    vivo   codex-cli-pin-manifest.json       697dc026e339a01682b72005ff4f6eed441ae462a843efa45d6fa0d2bfe66daf
    novo   codex-cli-pin.txt.new             11514263cc7c219ca0d40ff8bc294f2d69cd5c837e08f80d1e10e0e73148a6f8
    novo   codex-cli-pin-manifest.json.new   1828a56abf1acec1dadb6484aa271d263faefafe8827a75a4177f778facc933a

Os dois «vivo» são os bytes do HEAD em que o pack foi montado (última mudança
de ambos: o re-pin anterior, `7d807f4c`). O `.new` do pin é o arquivo vivo
com a última linha (o range antigo) trocada por uma linha em branco, um
parágrafo novo e o range novo; o `.new` do manifesto é o vivo com três
valores trocados. O range novo é `>=0.128.0,<0.157.0`.

## Evidência dos digests (reproduzível; medida em 2026-09-23)

    npm view @openai/codex dist-tags.latest
      -> 0.156.1

    npm view @openai/codex time --json | grep -E '"0\.156\.1(-darwin-arm64)?"'
      -> "0.156.1": "2026-09-23T02:45:25.210Z"
         "0.156.1-darwin-arm64": "2026-09-23T02:50:04.460Z"

    npm view @openai/codex@0.156.1 optionalDependencies
      -> "@openai/codex-darwin-arm64": "npm:@openai/codex@0.156.1-darwin-arm64"
         (mesmo nome de pacote de plataforma que o pack de 0.155.0 usou)

    npm view @openai/codex@0.156.1-darwin-arm64 dist.integrity
      -> sha512-Jg6wbdV+wmMZczhwE74GSxOYEZlViKXn6KyCw/yfrz3PAKFD14xljuPopmdhWC1+8IKU2WdN5fdmXNPt2q4HPA==

    npm pack @openai/codex@0.156.1-darwin-arm64
    openssl dgst -sha512 -binary openai-codex-0.156.1-darwin-arm64.tgz | base64
      -> Jg6wbdV+wmMZczhwE74GSxOYEZlViKXn6KyCw/yfrz3PAKFD14xljuPopmdhWC1+8IKU2WdN5fdmXNPt2q4HPA==
         (o tarball baixado confere com o `dist.integrity` do registry)

    tar xzf openai-codex-0.156.1-darwin-arm64.tgz
    shasum -a 256 package/vendor/aarch64-apple-darwin/bin/codex
      -> 0196e89fe5a7598f816ee54232c3d7c26d75e502ab5cfe2c9240e81d90f7255a

    shasum -a 256 <payload do codex global instalado>
      -> 0196e89fe5a7598f816ee54232c3d7c26d75e502ab5cfe2c9240e81d90f7255a
         (`cmp`: byte a byte igual ao do tarball)

Binário de 238.138.912 bytes; tarball de 131.652.985 bytes. Os 44 arquivos do
pacote de plataforma instalado são byte a byte iguais aos do tarball. Para
registro, o `dist.integrity` do pacote PRINCIPAL de 0.156.1 é
`sha512-nI1iVl/n2SO2lSvlwEsJx63zdSI4C4Me2gR7AG0OWMJiGSakz2tY2hx43E39Zq5aEoeB5bZjJXzp5Sqhog6vyA==`
(não é o que se grava: o ADR-182 §5 passo 2 manda o de plataforma, como no
pack de 0.155.0). O 0.156.1 global foi instalado pelo Owner; este pack não
instalou nada nem alterou ferramenta nenhuma da máquina, e o script recusa
assinar se o payload instalado não tiver o sha256 acima (conferido por hash,
sem executar o binário).

## Superfície medida (0.155.0 × 0.156.0 × 0.156.1)

Os três payloads nativos, cada um conferido por sha256 antes de rodar (0.155.0
e 0.156.1 do registry em 2026-09-23; 0.156.0 baixado do registry em
2026-09-22):

    codex --version            codex-cli 0.155.0 / 0.156.0 / 0.156.1
    codex exec --help          byte a byte idêntico nos três  (sha256 0e82cfde…509e)
    codex exec review --help   byte a byte idêntico nos três  (sha256 24118986…d392)
    codex --help               0.156.1 = 0.156.0; contra 0.155.0 só acrescenta `--no-daemon`

Mais: o launcher `bin/codex.js` do pacote principal é byte a byte idêntico nas
três versões e no instalado, e o tarball de plataforma do 0.156.1 tem o mesmo
conjunto de 44 caminhos de arquivo do 0.155.0.

Fontes, `rust-v0.155.0` → `rust-v0.156.0` (crate `codex-rs/exec`, medido em
2026-09-22 e de novo em 2026-09-23 pela GitHub API): mesmo conjunto de
arquivos; `cli.rs` e `main.rs` idênticos; fora de testes mudam cinco
arquivos. A mudança de FORMA de saída está confinada aos itens de web search
do stream `codex exec --json` (`exec_events.rs` e o processador JSONL; PR
#46319: ações mapeadas explicitamente e campo opcional `results`); o
processador de saída humana passa dois argumentos — o cwd e as raízes do
workspace — com outro TIPO (daí a dependência nova no `Cargo.toml` do crate,
`codex-utils-path-uri`); e o `lib.rs` passa ao servidor
`turn_trigger: "exec"` e `disabled_plugin_ids: None`. O `exec` sobe um
app-server EM PROCESSO
(`InProcessAppServerClient::start`), nenhum arquivo-fonte (não-teste) do crate
nem o seu `Cargo.toml` cita o daemon, e o CLI de topo despacha `exec` direto
para `codex_exec::run_main` — a lógica de reuso do servidor compartilhado e o
`--no-daemon` (PR #46088) estão no CLI de topo e na TUI.

Fontes, `rust-v0.156.0` → `rust-v0.156.1` (medido em 2026-09-23 pela GitHub
API; release `rust-v0.156.1` com `prerelease: false`): as duas tags saem da
mesma base; a 0.156.0 acrescenta a ela só a versão do workspace em
`codex-rs/Cargo.toml`, e a 0.156.1, o backport do PR #47332 (que as notas da
release chamam de «[hotfix 0.156.0]», #47405) e a própria versão. A árvore
git de `codex-rs/exec` é a MESMA nas duas tags, assim como as dos crates de
sandbox, `execpolicy`, `app-server` e `protocol`; fora de testes mudam só a
versão do workspace, o catálogo de modelos embutido
(`models-manager/models.json`) e dois arquivos-fonte da TUI. No catálogo:
entram `gpt-6-sol` e `gpt-6-luna`; `gpt-6-astra` segue com prioridade 1 e muda
só a descrição; as cinco entradas `gpt-5.x` ganham ou trocam o ponteiro
`upgrade` (para `gpt-6-sol`/`gpt-6-luna`), e quatro delas (todas menos a
`gpt-5.4`) trocam também a descrição — por exemplo, a da `gpt-5.5` passa de
«Frontier model for complex coding, research, and real-world work.» a
«Legacy coding model.». O rail vivo não passa `--model`
(`codex_cli_shape.DEFAULT_MODEL = None`: o modelo é o que o próprio codex
resolve pela configuração e pela conta). Pela
mensagem do commit upstream e pelos snapshots de cenário do `core` que ele
atualiza, o catálogo também alimenta a descrição das ferramentas de sub-agente
(`namespace/collaboration`) enviadas ao modelo; não foi medido aqui se, com o
catálogo remoto que o codex busca em tempo de execução, o texto de fato enviado
num turno do rail muda — a consequência declarada abaixo cobre os dois casos.

Motivo a favor, das notas do upstream (não medido aqui): a 0.156.0 fecha
brechas de isolamento do sandbox, entre elas escrita através de descritor
somente-leitura no Seatbelt do macOS (PR #46500) — o rail roda o codex com
`--sandbox read-only` no macOS. A 0.156.1 sai da mesma base que a 0.156.0, e
no ramo da 0.156.0 nada além da versão muda sobre essa base (medido acima).

## Protocolo (ADR-111 §2; ADR-182 §5)

Alargar o limite superior NÃO dispara re-run da Phase 4-bis por si: a regra
de reabertura do ADR-111 §2 (repetida no ADR-182 §5 passo 5) exige um desvio
MEDIDO de catch_rate > 5 pp no corpus travado. Nenhuma medição de corpus foi
tomada para este bump, então o gatilho fica NÃO AVALIADO — ausência de
medição, não resultado. O rótulo `§pin-update-protocol` que os parágrafos
anteriores do `codex-cli-pin.txt` citam não nomeia cabeçalho nenhum do
ADR-111; a regra a que se referem é esta do §2.

Forma widen-upper-only, e SÓ depois da tag `v1.4.1` (o script confere que a
tag existe, é ancestral do HEAD e é o mesmo objeto no remoto). Motivo
mecânico: o step 15 do `release.yml` confere o `codex_cli` do veredito contra
o range e o `codex_payload_sha256` contra o manifesto da árvore TAGUEADA, e
`codex-cli-pin.txt` entra no `inputs_hash` do veredito — um re-pin antes da tag
quebraria o veredito do GA, produzido no 0.155.0.

EXCEÇÃO DECLARADA à doutrina da S355, que o próprio `codex-cli-pin.txt`
registra («every Codex upgrade requires this re-pin BEFORE any release cut»):
o Owner instalou o 0.156.1 globalmente em 2026-09-23, antes do corte do GA da
v1.4.1, então, para esse corte, a letra da regra não é cumprida. O que
continua valendo: o validador que o step 15 roda só aceita o veredito do GA se
ele DECLARAR um `codex_cli` dentro do range da árvore tagueada e o sha256 do
payload que o manifesto dela pina (o do 0.155.0) — conferência da declaração,
não hash do binário que produziu o veredito —; então, antes de estes bytes
entrarem, nenhum veredito que declare o 0.156.1 valida. O modo opcional do
step 15 (`CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`, variável do repositório desligada
em 2026-09-23) vai além de tolerar a validação reprovada — também pula um
arquivo de veredito ausente e desliga o vínculo com o parent-SHA —, e o gate
de delta+ancestralidade que vem depois dele falha fechado nesse modo.
O parágrafo novo do `codex-cli-pin.txt` declara a mesma exceção.

O passo 4 do ADR-182 §5 (`--verify-codex-pin` com saída 0 e
`pair-rail-gate.sh --phase 6`) é executado pelo script depois de aplicar e
antes de commitar, com o verificador ancorado na raiz do checkout e sem
costuras de teste; qualquer reprovação restaura a árvore. A bateria de gates
roda com ambiente de allowlist (identidade do usuário, locale, diretório
temporário, resolução do Python e do codex) e `CLAUDE_PROJECT_DIR` fixado na
raiz: variável herdada fora dessa lista não chega a nenhum gate da bateria. A
phase 6 e o verificador rodam com o ambiente do Owner menos as costuras de
teste, porque a phase 6 precisa da rota de autenticação do codex; o override
de rotação de chave do próprio gate (`CEO_CODEX_KEY_ROTATION_OVERRIDE`), se
presente, NÃO é removido — é anunciado no começo e registrado na mensagem do
commit, e a verificação do pin (Gate 4) não depende dele. As rotas de
autenticação que a phase 6 exige (Gates 1 e 2: `OPENAI_API_KEY` com a
cadência de rotação de 90 dias de `docs/rotation-log.md`, ou a sessão em
`~/.codex/auth.json`) são conferidas antes do pinentry, pela mesma regra do
gate e sem executar o codex; a phase 6 depois de aplicar segue sendo a
autoridade.

A assinatura só é aceita de chave que passe nas duas pernas de signatário do
guard canônico, com as mesmas funções: fingerprint em
`.claude/sentinel-signers.txt` (`gpg_verify.verify_detached`) e, havendo o
registro do ADR-121, chave válida nele (`sentinel_signers.is_valid_signer`;
registro ilegível cai só na perna legada, como o guard antes da GENESIS). O
script escolhe a chave por esse critério antes do pinentry e confere a
assinatura produzida de novo, pelo mesmo critério.

## Decisão sobre o corpus (Phase 4-bis) e o checklist do ADR-161

ADIADOS — o corpus como nos re-pins de S352 e S356; o checklist como
declarado no re-pin de S356 (que registrou o de S352 como a mesma postura) —,
com o motivo mecânico e as mudanças que poderiam derrubar o adiamento
conferidos:

1. O re-run não é executável nesta árvore: o executor do corpus no código
   vivo (`.claude/scripts/run-promotion-gate.py`) aponta por padrão para
   `.claude/plans/PLAN-081/corpus/locked/`, caminho que não existe no
   checkout nem no histórico deste repositório, e a revisão por fixture
   (`review_fixture`) é stub — devolve ADVISORY sem invocar o codex.
2. O rail vivo monta o `codex exec` com `-o` e SEM `--json`
   (`codex_cli_shape.build_verdict_argv`); o único parser do stream `--json`
   na árvore rastreada fora de `.claude/plans/`
   (`parse_usage_from_codex_stdout`, caminho de promoção) não tem chamador
   fora de testes (busca textual em 2026-09-23). No código rastreado fora de
   `.claude/plans/`, os demais chamadores de `codex exec` leem o arquivo `-o`,
   o stdout em texto, ou não leem a saída. Os procedimentos de live-fire do
   ADR-161 (em `.claude/plans/PLAN-155/`) LEEM o stream `--json`, mas itens
   que não são de web search — o único tipo que a mudança toca — e ficam
   adiados com o checklist. A mudança de forma do `exec` de 0.155.0 para
   0.156.0 (seção «Superfície medida») não tem leitor no código vivo, e de
   0.156.0 para 0.156.1 o crate do `exec` não muda.
3. O checklist do ADR-161 re-certifica o Codex como HOST de hooks; o que força
   este re-pin é o Codex como REVISOR do rail. As fixtures do adaptador são
   payloads de hook (não eventos do `exec`) gravadas sob `codex-cli 0.139.0`,
   que segue DENTRO do range; o teste de acoplamento fixture↔pin roda na
   bateria desta cerimônia. CONSEQUÊNCIA DECLARADA do adiamento: o aviso de
   version skew do harness de Codex do instalador (`scripts/_codex_harness.sh`)
   lê este mesmo range, então alargá-lo admite o 0.156.x como dentro do range
   para o Codex como host de hooks, com a evidência de hooks ainda no 0.139.0 —
   uma re-certificação que este adiamento dispensa de propósito (todo
   alargamento desde que esse leitor entrou, em 2026-07-10, teve o mesmo
   efeito).
4. A sonda local T2 (`test_codex_templates.py`, que executa o binário real
   depois da verificação) roda na bateria e tem de constar PASSED: pulada,
   o script aborta. Ela e o gate da phase 6 executam o payload VERIFICADO
   pelo caminho que o verificador resolveu, como o hook do rail.

O re-record das fixtures e o checklist completo ficam para a wave de
substrato, como declarado no re-pin de S356.

## Consequência DECLARADA

Isto troca o INSTRUMENTO do rail. Medições feitas antes e depois deste commit
NÃO são comparáveis. A fronteira fica registrada em vez de silenciosa.

## Janela de rail fechado

Enquanto o 0.156.1 estiver instalado e o manifesto vivo for o de 0.155.0, o
binário instalado não bate com o manifesto e o pair-rail fica fail-CLOSED
(medido em 2026-09-23, primeira linha da tabela acima); este script fecha a
janela ao aplicar os dois canônicos. Se o script abortar ANTES de o `main`
avançar — por falha ou por INT, TERM ou HUP —, a árvore volta ao manifesto de
0.155.0 e o rail segue fechado até rodá-lo de novo. O avanço do `main`, o
desarme da restauração e a sincronização do índice correm com INT, TERM e HUP
ignorados; uma falha depois do avanço para com «NÃO faça push» e o comando
para desfazer só o commit. Um SIGKILL ou a queda da máquina não rodam
restauração; o diretório de backup que o script imprime ao começar fica na
pasta temporária, que um reboot pode apagar — mas os originais sempre voltam
do git, porque o P0 exige a árvore igual ao HEAD: `git checkout HEAD --` nos
dois canônicos e no sentinel, e remover o `.asc` não rastreado.

## Residual

1. Só o payload `aarch64-apple-darwin` é pinado (a plataforma do Owner). As
   outras plataformas do `optionalDependencies` seguem sem digest — mesma
   postura das gerações anteriores, não regressão.
2. Dentro do tarball pinado, só `vendor/<triple>/bin/codex` tem digest: todo
   outro executável que o tarball carrega sob `vendor/<triple>/` e que o
   payload venha a executar roda sem pin. O conjunto de caminhos é o mesmo do
   0.155.0 — não é regressão, e a medição não o fecha.
3. O launcher `bin/codex.js` do pacote principal não tem digest no manifesto.
   O hook do rail e esta cerimônia executam o payload VERIFICADO pelo caminho
   resolvido; o `pair-rail-gate.sh --phase 6` rodado FORA desta cerimônia e o
   `codex` interativo do Owner entram pelo launcher do PATH, que, trocado,
   executaria outro binário sem que o verificador visse. Mesma postura desde o
   manifesto do ADR-182, não regressão deste pack.
4. O pin atesta os bytes do payload, não o processo que atende o turno. Hoje o
   `exec` roda em processo; se uma versão futura fizer o `exec` reusar o
   servidor compartilhado (pacote instalado à parte), o artefato verificado
   deixa de ser o que executa — conferir a cada re-pin, como feito aqui.
5. A cadência medida do Codex é de cerca de um minor por semana, e o patch
   pode vir horas depois (datas do npm: 0.155.0 em 17/09, 0.155.1 em 18/09,
   0.156.0 em 22/09 às 19:55Z, 0.156.1 em 23/09 às 02:45Z). Com pin de
   versão exata, toda atualização global fecha o rail até o re-pin seguinte —
   este pack foi remontado uma vez por isso. A cura estrutural (gerar este pack
   a partir de um número de versão) é a W5 do PLAN-193 e NÃO está neste pack.
