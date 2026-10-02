# pin-0160-approved — sentinel do re-pin do codex CLI 0.156.1 → 0.160.0

Plan: PLAN-194
Wave: re-pin codex-cli 0.156.1 → 0.160.0
Anchor-SHA: (preenchido pelo passo 1 do script de cerimônia)
Data: (preenchida pelo passo 1 do script de cerimônia)

## Ratificação (Owner, 2026-10-02)

Mandato do Owner no fechamento da S361 (2026-10-02, por volta de 14:50Z),
respondendo por múltipla escolha à decisão pendente 3 do PLAN-194: «Re-pin
manual agora», como «1.ª tarefa do próximo terminal». Na mesma data,
perguntado se a 0.160 era mesmo a última, o Owner aceitou a 0.160.0 «pra
assinar logo», com a sentada de assinatura marcada para o sábado
2026-10-03. Conferido no mesmo dia: a `latest` do npm é a 0.160.0
(publicada em 2026-10-01T20:26:19Z, seção «Evidência dos digests»), nenhuma
0.160.x saiu depois dela, e a 0.162.0 existe só como alpha.

O texto commitado que registra o mandato é o PLAN-194 no `cd5b90c7`
(«Plano B — re-pin manual pelo molde (ADR-182 §5; precedentes 0155 e 0156)
— ATIVADO para a 0.160.0 (decisão do Owner S362, 2026-10-02)»): a decisão 3
(como o pin automático é empacotado) NÃO foi tomada, a W3 (pin automático)
fica para DEPOIS da v1.4.3 e o VETO de Segurança sobre ela segue levantado.
Até a W3 landar, toda atualização do Codex passa por um pack gerado como
este, a partir do molde do pack mais novo
(`.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh`, com
`--ga-tag v1.4.2`).

Por que entra agora: é a 1.ª tarefa do trem da v1.4.3 por decisão do Owner,
e a doutrina da S355, registrada no próprio `codex-cli-pin.txt`, exige o
re-pin ANTES de qualquer corte de release. A regra operacional do Codex até
a W3 (W3.1 do PLAN-194) é ancorada nesta sentada: 0.156.1 até ela, 0.160.0
depois dela, nunca `npm update -g`.

Medido em 2026-10-02 (S362), com a 0.160.0 instalada num prefixo npm
descartável (`--ignore-scripts`) e, ANTES de executar qualquer binário
dela:

    shasum -a 256 do payload aarch64-apple-darwin instalado
      -> 112fae7a5a1223e673c8a1791d32338f37df8b527ff1159bb8adac6c4dbf1b4b
         (o mesmo valor que o gerador mediu no tarball do registry)
    check_pair_rail.py --verify-codex-pin  x  manifesto VIVO (0.156.1)
      -> {"status": "mismatch", "detail": "payload_sha256_mismatch"}

Depois, com o `CODEX_HOME` numa cópia temporária da configuração do Owner:
`--version` = `codex-cli 0.160.0`; o argv do hook do rail e o argv de
revisão do CEO aceitos pelo parser, com os dois controles negativos (valor
de sandbox inválido, flag desconhecida) recusados; `exec review --help`,
`app-server --help` e `execpolicy check` sem erro de parse; a sonda T2
(`test_codex_templates.py::TestExecpolicyRules::test_live_execpolicy_check`)
PASSED; e um veredito JSON válido de canário, com o modelo e o esforço
SERVIDOS registrados (seção «Protocolo, consequência e residual»).

## Scope

- `.claude/governance/codex-cli-pin.txt` — `<0.157.0` → `<0.161.0` (limite inferior INALTERADO em `>=0.128.0`), com o parágrafo datado do cabeçalho.
- `.claude/governance/codex-cli-pin-manifest.json` — `package_version` 0.160.0, `npm_integrity` do artefato de PLATAFORMA e `sha256` do payload `aarch64-apple-darwin`.

Nada além desses dois arquivos canônicos, deste sentinel e da sua
assinatura entra no commit da cerimônia.

## Bytes que esta assinatura cobre

    range novo                         >=0.128.0,<0.161.0
    .claude/governance/codex-cli-pin.txt vivo (sha256)   11514263cc7c219ca0d40ff8bc294f2d69cd5c837e08f80d1e10e0e73148a6f8
    .claude/governance/codex-cli-pin-manifest.json vivo (sha256)
                                       1828a56abf1acec1dadb6484aa271d263faefafe8827a75a4177f778facc933a
    codex-cli-pin.txt.new (sha256)          cb532824ecabd8357d55799a90306dc2e326a7081a937e892df2454856264269
    codex-cli-pin-manifest.json.new (sha256)
                                       e356c3611bf9754f9e313ec644463d7bd765c9ab04ff52ea9569bb5c0b9b92dc
    payload aarch64-apple-darwin (sha256)  112fae7a5a1223e673c8a1791d32338f37df8b527ff1159bb8adac6c4dbf1b4b
    npm_integrity (plataforma)         sha512-aefV6cqZA2REZgR//4McyXlp7zLcTti4CI2v3j9IVgNndPBv2kCeNEcz07qeelXcwOdSFPUKb6roA48vZmDgrQ==

Os dois `vivo` são os canônicos de quando o pack foi gerado; os dois `.new`
são os bytes que a cerimônia aplica.

## Evidência dos digests (medida por `.claude/scripts/re-pin-codex.py` em 2026-10-02)

Registry: `https://registry.npmjs.org/`, passado explicitamente a toda chamada do npm
(`--registry` e `--@openai:registry`: nenhum `.npmrc` escolhe outro).

    npm view @openai/codex@0.160.0 --json --registry=https://registry.npmjs.org/ --@openai:registry=https://registry.npmjs.org/
      -> time["0.160.0"] = 2026-10-01T20:26:19.286Z
      -> optionalDependencies["@openai/codex-darwin-arm64"] = npm:@openai/codex@0.160.0-darwin-arm64
    npm view @openai/codex@0.160.0-darwin-arm64 --json --registry=https://registry.npmjs.org/ --@openai:registry=https://registry.npmjs.org/
      -> dist.integrity = sha512-aefV6cqZA2REZgR//4McyXlp7zLcTti4CI2v3j9IVgNndPBv2kCeNEcz07qeelXcwOdSFPUKb6roA48vZmDgrQ==
      -> dist.tarball = https://registry.npmjs.org/@openai/codex/-/codex-0.160.0-darwin-arm64.tgz
    tarball openai-codex-0.160.0-darwin-arm64.tgz (134311083 bytes), baixado com npm pack num diretório temporário
      -> sha512 = sha512-aefV6cqZA2REZgR//4McyXlp7zLcTti4CI2v3j9IVgNndPBv2kCeNEcz07qeelXcwOdSFPUKb6roA48vZmDgrQ==  (confere com o dist.integrity)
    membro package/vendor/aarch64-apple-darwin/bin/codex (241555024 bytes)
      -> sha256 = 112fae7a5a1223e673c8a1791d32338f37df8b527ff1159bb8adac6c4dbf1b4b

Reprodução manual:

    npm pack @openai/codex@0.160.0-darwin-arm64 --registry=https://registry.npmjs.org/ --@openai:registry=https://registry.npmjs.org/
    openssl dgst -sha512 -binary openai-codex-0.160.0-darwin-arm64.tgz | base64
    tar xzf openai-codex-0.160.0-darwin-arm64.tgz package/vendor/aarch64-apple-darwin/bin/codex
    shasum -a 256 package/vendor/aarch64-apple-darwin/bin/codex

Para registro, o `dist.integrity` do pacote PRINCIPAL @openai/codex@0.160.0 é `sha512-kEtVGzjRAYAMOwJxN39bGcna7LT3IDQgq64NNJ/dDTfu4OzZaocJcyNb5/gGJ/IVF/Vj7oK7E2m3nmTan7lpjg==` — não é o
que se grava (ADR-182 §5 passo 2).

Conferência opcional antes da cerimônia, com a versão já instalada:
`python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"`
deve trazer `"sha256": "112fae7a5a1223e673c8a1791d32338f37df8b527ff1159bb8adac6c4dbf1b4b"` (o `status` ainda é `mismatch`
contra o pin vigente).

## Protocolo, consequência e residual

**Janela de release.** Fora de qualquer janela de release aberta: o GA
v1.4.2 foi cortado em 2026-09-30 e não existe tag `v1.4.3*`, nem local nem
no remoto (conferido em 2026-10-02). O script só roda depois da tag
`v1.4.2` (`GA_TAG`): ela tem de existir, ser ancestral do HEAD e ser o
mesmo objeto no remoto. Forma widen-upper-only: só o TETO da faixa alarga
(`<0.157.0` → `<0.161.0`); o piso fica em `>=0.128.0`. Motivo mecânico, o
mesmo do pack anterior: o step 15 do `release.yml` confere o `codex_cli` do
veredito contra a faixa e o `codex_payload_sha256` contra o manifesto da
árvore TAGUEADA, e o `codex-cli-pin.txt` entra no `inputs_hash` do
veredito. Diferente do pack 0156, aqui NÃO há exceção à doutrina da S355:
este re-pin entra antes do próximo corte (a rc.1 da v1.4.3), e nenhum
veredito que declare o 0.160.0 valida antes destes bytes.

**ADR-111 §2 (Phase 4-bis): NÃO avaliável.** A regra de reabertura do
corpus (ADR-111 §2, repetida no ADR-182 §5 passo 5) exige um desvio MEDIDO
de catch_rate > 5 pp no corpus travado. Nenhuma medição de corpus existe
para este bump, e o re-run não é executável nesta árvore: o executor
(`.claude/scripts/run-promotion-gate.py`) aponta por padrão para
`.claude/plans/PLAN-081/corpus/locked/`, ausente do checkout, e a revisão
por fixture é stub. O gatilho fica NÃO AVALIADO — ausência de medição, não
aprovação. O rótulo `§pin-update-protocol` que parágrafos antigos do
`codex-cli-pin.txt` citam não nomeia cabeçalho do ADR-111; a regra é a do
§2.

**ADR-161: checklist ADIADO**, para a wave de substrato, na mesma postura
dos re-pins da S352, da S356 e da S357. O checklist re-certifica o Codex
como HOST de hooks; o que força este re-pin é o Codex como REVISOR do
rail. Motivos, conferidos em 2026-10-02: (1) o rail vivo monta o
`codex exec` com `-o` e SEM `--json` (`codex_cli_shape.build_verdict_argv`),
e o único parser do stream `--json` fora de `.claude/plans/`
(`parse_usage_from_codex_stdout`) segue sem chamador fora de testes; (2) a
sonda mediu o ARGV do rail na 0.160.0 (aceito pelo parser), não a forma da
SAÍDA do `exec` — a diferença de fonte do `exec` entre 0.156.1 e 0.160.0
NÃO foi medida; (3) a sonda T2 roda na bateria do passo 5 e tem de constar
PASSED, senão o script aborta. CONSEQUÊNCIA DECLARADA do adiamento, pela
forma: todo leitor que usa esta faixa como gate de VERSÃO, e não o
manifesto, passa a admitir 0.160.x a partir deste commit — entre eles o
aviso de version skew do harness de Codex do instalador
(`scripts/_codex_harness.sh`), cuja evidência de hooks segue certificada no
0.139.0. Todo alargamento desde que esse leitor entrou teve o mesmo efeito.

**Consequência DECLARADA: troca de INSTRUMENTO.** O revisor do rail passa a
ser o binário 0.160.0. Medições do rail antes e depois deste commit NÃO são
comparáveis, e a 1.ª rodada de rail no 0.160.0 é re-teste. O que o revisor
SERVE é escolhido pela configuração do Codex do Owner, não por este pin:
medido em 2026-10-02 pela sonda (cópia dessa configuração num `CODEX_HOME`
temporário) como modelo `gpt-6-astra` com esforço de raciocínio `xhigh`.
Mudar essa configuração muda o instrumento sem tocar nestes bytes — o
PLAN-194 registra um caso (o app do Owner regravou o arquivo em
2026-10-01). O sha256 da configuração é registrado a cada rodada de rail,
fora deste sentinel.

**Janela de rail fechado.** Entre o `npm i -g @openai/codex@0.160.0` e o
commit desta cerimônia, o binário instalado não bate com o manifesto vivo
(0.156.1) e o pair-rail fica fail-CLOSED; o script fecha a janela ao
aplicar os dois canônicos, e a sentada roda com as rodadas de rail paradas.
Se o script abortar ANTES de o `main` avançar, a árvore volta ao manifesto
de 0.156.1 e o rail segue fechado até rodá-lo de novo, ou até reinstalar a
0.156.1 (o manifesto vivo ainda é o dela) e conferir `verified`.

**Residual, declarado pela forma.**

1. O pin atesta UM executável: o payload `aarch64-apple-darwin` no caminho
   do manifesto. Todo outro executável fica fora do sha — os executáveis
   irmãos que o tarball de plataforma carrega ao lado dele, os payloads das
   outras plataformas do npm e o launcher do pacote principal
   (`bin/codex.js`). Mesma postura de todas as gerações anteriores, não
   regressão deste pack.
2. O pin atesta os bytes do payload, não o processo que atende o turno:
   todo processo que o payload delega ou reaproveita fora do próprio
   binário (o daemon `app-server`, por exemplo) roda fora do pin.
3. Pack GERADO, não montado à mão: fora do bloco de constantes, do guard e
   do cabeçalho, o corpo do script é o do molde 0156, byte a byte (nota do
   gerador abaixo). A mensagem de commit herdada foi relida contra ESTE
   re-pin em 2026-10-02; nenhuma frase ficou falsa. A frase «npm pack +
   shasum sobre o binário extraído» descreve o método manual: o gerador
   faz o sha256 do membro em memória, sem extrair para o disco; o valor é o
   mesmo (seção «Reprodução manual») e o shasum do binário extraído pela
   instalação da sonda deu o mesmo valor.
4. Uma edição à mão na nota do gerador abaixo: o nome do guard foi reescrito
   sem o marcador literal de pendência. O guard do script procura esse
   marcador no sentinel INTEIRO, e a nota gerada o citava por extenso — com
   ela intacta, o run real recusaria mesmo com as duas seções humanas
   escritas. Defeito do gerador (a nota que ele escreve contém o marcador
   que o guard que ele injeta recusa), reportado para cura no gerador; o
   sentido da nota não muda.

Residual declarado pelo gerador: o caminho do payload (`@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex`)
é COPIADO do manifesto vivo; o gerador só confere que o tarball novo tem
um membro regular ali. Que o launcher da versão nova (`bin/codex.js` do
pacote principal) ainda execute esse caminho NÃO é conferido — ponto
cego compartilhado com `--verify-codex-pin`, que faz hash do mesmo
caminho do manifesto.

Texto herdado sem conferência: fora do bloco de constantes, do guard
de pendência e do cabeçalho, o corpo do script é o do molde, byte a byte —
inclusive a prosa da mensagem de commit (as linhas `printf`). O gerador só
confere nela os literais de versão, hex e SRI; uma frase verdadeira apenas
para o re-pin do molde passa inalterada. Leia a mensagem de commit do script
contra ESTE re-pin antes de assinar.
