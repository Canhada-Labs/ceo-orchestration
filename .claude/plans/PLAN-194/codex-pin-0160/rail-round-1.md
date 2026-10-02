# rail-round-1 — re-pin do Codex 0.156.1 → 0.160.0 (PLAN-194, pack `codex-pin-0160`)

Rail-Round: 1
Rail-Subject: .claude/plans/PLAN-194/codex-pin-0160/ (os seis arquivos do pack)
Rail-Subject-Commit: 5572996d5f93af03cacab8cb3cf9e295433862d6
Rail-Subject-sha256:
    OWNER-PIN-SIGN.sh                 d875dc5dc007de406a973b7c82eba9b04dac67c026a1396858eca492a7d5f07a
    README.md                         2635c3e23f30945308b94abcd65854ad0ee9464152d8ec0dd96f1d75ccb13fdb
    codex-cli-pin-manifest.json.new   e356c3611bf9754f9e313ec644463d7bd765c9ab04ff52ea9569bb5c0b9b92dc
    codex-cli-pin.txt.new             cb532824ecabd8357d55799a90306dc2e326a7081a937e892df2454856264269
    pin-0160-approved.md              9eada2d8d1a8b3c334cc6f63fd28317b3430239a51636add9b8ce22fac8a9e0a
    rehearse-pin-0160.sh              20b51008add8c3e3ce20b067599a4adc1b253be367a9c8b9d951990cb241fd62
    (trilha do rail, no mesmo commit, fora do sujeito)
    rail-prompt.md                    8853868f1bf84f02808f91e9a324f4c034e9e01e9a73039a06ac4de79aee4fd1
    rail-record-template.md           58393a4c25027e84e00f23b28c62965608ef0d56570e6c2b2491c1fc05c1b085
Rail-Reviewer: codex-cli 0.156.1 (global, `--verify-codex-pin` = verified, conferido pelo CEO antes da rodada), exec read-only; servidos (cabeçalho da sessão do revisor): modelo gpt-6-astra, esforço xhigh
Rail-Codex-Config-sha256: 232b5bede4e1cb36c103046a2aedbb075dac6255c080b789bcb027bcc423a53a
Rail-Prompt: .claude/plans/PLAN-194/codex-pin-0160/rail-prompt.md
Rail-Rehearsal: PASS — rehearse-pin-0160.sh em 2026-10-02 sobre estes seis arquivos, 93 PASS / 0 FAIL
Rail-Reviewer-Verdict: GO
Rail-Verdict: DECLARED-P2
Rail-Findings: P0=0 P1=0 P2=2

Regra de parada (pré-registrada no rail-prompt): no máximo 3 rodadas, a 3.ª final com anexo. Esta é a
rodada 1 de 3, e a série FECHA nela: veredito agregado GO, sem mudança no sujeito (os seis arquivos
seguem nos bytes do commit acima; nada foi regenerado nem editado depois da rodada).

Cópia das saídas: as três lanes estão abaixo byte a byte, cada uma num bloco verbatim. Nenhuma linha
delas começava com três crases (mesmo indentada), então nenhuma troca de marcador foi feita. Os três
arquivos de origem terminavam sem quebra de linha final; a única adição é essa quebra, para a cerca de
fechamento ficar na sua própria linha. Nenhum caminho local aparecia nas três saídas (nada redigido). A
linha `VERDICT:` conferida é a do Codex (seção seguinte); as das lanes Claude entram na triagem.

## Saída do revisor

```text
NENHUM ACHADO

VERDICT: GO
```

## Saída das lanes Claude (verbatim)

Refutador Claude, lente especificação e afirmações (R-RP-A):

```text
TAREFA R-RP-A — refutador Claude, RODADA 1, lente ESPECIFICAÇÃO E AFIRMAÇÕES. Sujeito: commit 5572996d (pai cd5b90c7 = origin/main) na sombra fd10, diretório .claude/plans/PLAN-194/codex-pin-0160/.

PRÉ-CONDIÇÕES CONFERIDAS (recalculadas por mim, não aceitas do relato):
- sha256 dos 8 arquivos na sombra = subject-sha256.txt, 8/8 iguais; commit 5572996d com pai cd5b90c7 confirmado; ~/.codex/config.toml = 232b5be… ; codex global = codex-cli 0.156.1.

VERIFICAÇÕES QUE PASSARAM (prova resumida):
1. Bloco «Bytes que esta assinatura cobre»: os 4 sha batem — BASE_PIN 11514263…/BASE_MAN 1828a56… recalculados de git show cd5b90c7 dos 2 canônicos; SRC_PIN cb532824…/SRC_MAN e356c36… recalculados dos .new. Continuidade de cadeia: SRC_* do molde 0156 = BASE_* deste pack.
2. Manifesto .new = vivo com EXATAMENTE 3 valores trocados (package_version, npm_integrity de plataforma, sha256 do payload). Pin .new = vivo com prefixo intacto (diff só em 147c147,196), parágrafo novo 100% comentários «#» (+1 linha em branco), faixa >=0.128.0,<0.161.0 como ÚLTIMA linha (compatível com o leitor last-non-comment do _codex_harness.sh:43-49) — só o teto alarga.
3. OWNER-PIN-SIGN.sh vs molde 0156 (sha do molde confere: 09ec1cf8…): diff de 107 linhas, TODAS nas 3 zonas declaradas (cabeçalho, bloco de constantes, guard TODO(owner)). Constantes batem com sentinel e registry; GA_TAG=v1.4.2; guards :338-342 fazem exatamente o que o sentinel afirma (tag existe, ancestral do HEAD, mesmo objeto no remoto — conferi: v1.4.2 local=remoto 900b219b, nenhuma v1.4.3*).
4. Guard de pendência: grep 'TODO(owner)' sobre pin-0160-approved.md + codex-cli-pin.txt.new sai VAZIO (rc=1); sem caractere de controle, sem CR. Outra rota do marcador: não há — o gerador só o escreve nas seções humanas (preenchidas) e na nota (:1548-1550, reescrita); o README/script carregam o literal mas o guard só varre $SENT e $SRC_PIN. Confirmei em re-pin-codex.py:1548-1550 que a nota GERADA cita o TODO_MARK por extenso — o item 4 do residual é verdadeiro e a reescrita («guard de pendência») preserva o sentido.
5. Registry (npm view, 02/10): latest=0.160.0; time 0.160.0=2026-10-01T20:26:19.286Z; nenhuma 0.160.x estável depois (só win32 do próprio 0.160.0 e alphas); alpha=0.162.0-alpha.7; integrity de PLATAFORMA sha512-aefV6cq… bate; integrity do PRINCIPAL sha512-kEtVGzjRAYAM… bate (declarado como «não é o que se grava» ✓). Payload re-hasheado por mim do prefixo mantido da FD-02: 112fae7a…, 241555024 bytes ✓. Runbook D-1/D-2/D-3/D-20 e PLAN-194:1219-1249 conferem a Ratificação frase a frase (Plano B ATIVADO verbatim; decisão 3 NÃO tomada; W3.1 :1090; app regravou config em 2026-10-01 :885-886/:1177).
6. Afirmações sobre código: release.yml :693-702/:760-762 (faixa + manifesto + inputs_hash com os 2 arquivos) ✓; ADR-111 §2 «>5pp catch_rate shift» ✓ e «pin-update-protocol» com 0 ocorrências no ADR-111 e 4 no pin vivo ✓; run-promotion-gate.py:96 DEFAULT_CORPUS_DIR=PLAN-081/corpus/locked AUSENTE do checkout ✓, stub por fixture :277-321 ✓; build_verdict_argv docstring «-o only, NO --json» ✓; parse_usage_from_codex_stdout sem chamador fora de testes ✓; _codex_harness.sh CODEX_VERIFIED_VERSION=0.139.0 ✓; re-pin-codex.py :893-906 hash do membro EM MEMÓRIA (tf.extractfile + hashlib, sem extrair a disco) ✓. Doutrina S355 no pin herdado :83-84; contraste com a exceção do 0156 (:100-103) correto. rehearse-pin-0160.sh difere do molde SÓ no cabeçalho (45 linhas, todas comentário). Mensagem de commit herdada (:553-577) relida linha a linha contra ESTE re-pin: nenhuma frase falsa (a frase «npm pack + shasum sobre o binário extraído» está coberta pelo residual item 3 e pela sonda, que extraiu e hasheou de verdade). FD-02 corrobora cada medição do bloco «Medido em 2026-10-02» (mismatch, argvs, controles negativos rc=2, T2 PASSED, canários com servidos gpt-6-astra/xhigh).

ACHADOS:

- [P1] pin-0160-approved.md:194 — «Defeito do gerador …, reportado para cura no gerador»: a afirmação de reporte NÃO tem objeto rastreável no repo. Prova: grep no PLAN-194 vivo (main até 9a458f19), em .claude/plans/PLAN-194/LEDGER.md e por FOLLOWUPs — zero registros da classe («a nota que o gerador escreve contém o marcador que o guard que ele injeta recusa»); o único texto que a descreve é o próprio pack (sentinel item 4 + rail-prompt «Achado já conhecido»), o que é circular. A tarefa desta lente perguntava explicitamente se «a cura de classe do gerador» está como follow-up: NÃO está. Consequência pela forma: o gerador REGENERA a nota com o TODO_MARK a cada pack (re-pin-codex.py:1548-1550, _inherited_prose_notes), logo o PRÓXIMO re-pin reintroduz o defeito e exige a mesma edição à mão — sem item de trabalho, o conhecimento vive só nesta série de rail. Não é P0 porque a falha é fail-CLOSED e visível (o guard aborta o run real, não assina em silêncio). CURA (fora do pack, sem regenerar): landar ANTES da sentada de sábado um registro rastreável — linha no PLAN-194/LEDGER.md ou follow-up nomeado no PLAN-194 («cura de classe: _inherited_prose_notes não escrever no sentinel o marcador que o guard injetado recusa, com teste vermelho→verde no gerador»). A frase do sentinel está em seção humana e fica verdadeira assim que o registro landar; alternativa mínima é reescrever a frase da seção humana para apontar o registro.

- [P2] pin-0160-approved.md:142-144 — motivo (2) do adiamento do ADR-161: «a sonda mediu o ARGV do rail na 0.160.0 (aceito pelo parser), não a forma da SAÍDA do exec». A FD-02 TAMBÉM validou a saída no caminho feliz: dois canários reais rc=0 com out-file JSON conferido (hook: findings/summary/verdict PASS; CEO: verdict ok sob --output-schema) — e o próprio sentinel os registra nas linhas 50-52. Há leitura defensável (saída = forma do STREAM stdout, que o motivo (1) contextualiza e que não foi sondada; o canário validou só o arquivo -o), mas na forma atual a frase subdeclara a medição e tensiona com a seção «Medido em 2026-10-02». CURA (seção humana, sem regenerar): precisar a frase — p.ex. «mediu o argv e um canário de caminho feliz da saída em arquivo; a forma do stream de saída do exec e a diferença de fonte entre 0.156.1 e 0.160.0 não foram medidas». Opcional: pode ser DECLARED-P2.

Nota de triagem (não é achado): o rail-prompt declara «os seis arquivos do pack» como sujeito; o commit tem 8 (os 6 + rail-prompt.md + rail-record-template.md, que são a trilha do rail, coerente com README:16 e PLAN-194:343). Li os 2 extras; nada neles contradiz o pack.

VERDICT: GO-WITH-CONDITIONS
```

Refutador Claude, lente segurança, supply-chain e cerimônia (R-RP-B):

```text
R-RP-B (refutador Claude, lente segurança/supply-chain/cerimônia) — RODADA 1 do rail do re-pin 0.156.1 → 0.160.0. Sujeito: commit 5572996d, .claude/plans/PLAN-194/codex-pin-0160/. Sha256 dos 6 arquivos conferidos contra subject-sha256.txt (batem todos); árvore do pack limpa na sombra.

## O que foi verificado e PASSOU (com prova)

1. PROVENIÊNCIA DOS DIGESTS — reproduzida por download independente do registry (diretório próprio no scratchpad, npm pack --ignore-scripts, binário jamais executado, diretório removido ao fim por shutil.rmtree):
   - time["0.160.0"] = 2026-10-01T20:26:19.286Z; dist-tags.latest = 0.160.0; nenhuma 0.160.x estável posterior; 0.162.0 existe só como alpha (0.162.0-alpha.1..7) — as frases do sentinel (pin-0160-approved.md:13-17) são verdadeiras hoje.
   - dist.integrity do artefato de PLATAFORMA @openai/codex@0.160.0-darwin-arm64 = sha512-aefV6cqZA2REZgR//4McyXlp7zLcTti4CI2v3j9IVgNndPBv2kCeNEcz07qeelXcwOdSFPUKb6roA48vZmDgrQ== e o sha512 que EU calculei do tarball baixado (134311083 bytes, igual ao declarado) é IDÊNTICO.
   - membro package/vendor/aarch64-apple-darwin/bin/codex: 241555024 bytes, sha256 = 112fae7a5a1223e673c8a1791d32338f37df8b527ff1159bb8adac6c4dbf1b4b — reproduzido exato.
   - dist.integrity do pacote PRINCIPAL = sha512-kEtVGzjRAY… distinto, como o sentinel declara (linha 100).
   - Resposta à pergunta (1) da tarefa: o sha256 do payload e o integrity sha512 NÃO vêm de canais independentes do fornecedor — ambos derivam do registry npmjs (metadata JSON + tarball CDN), consistentes entre si; a independência que existe é TEMPORAL/por-obtenção (sonda instalada + npm pack do gerador + minha reprodução agora, três downloads que convergem no mesmo valor). Ver P2-1 abaixo.

2. OS QUATRO SHA DO BLOCO «Bytes que esta assinatura cobre» batem: BASE_PIN 11514263… e BASE_MAN 1828a56a… = canônicos vivos no HEAD da sombra (medido); SRC_PIN cb532824… e SRC_MAN e356c361… = os .new (medido). Manifesto .new = vivo com EXATAMENTE 3 valores trocados (diff em bytes). Pin .new = prefixo intacto + parágrafo novo só de comentários + faixa >=0.128.0,<0.161.0 (só o teto alarga; piso inalterado).

3. OWNER-PIN-SIGN.sh (fail-closed, TOCTOU, segredos):
   - Diff contra o molde 0156 (sha256 do molde conferido = 09ec1cf8…): 128 linhas, esgotadas em exatamente 3 blocos — cabeçalho, constantes, guard. Corpo byte a byte o do molde. Constantes batem com sentinel e com o registry; GA_TAG=v1.4.2 (tag existe, é ancestral do HEAD, nenhuma v1.4.3*).
   - Fail-closed em todo caminho sondado: set -euo pipefail; env git herdado = recusa (linhas 41-48); argumento desconhecido = recusa (60-64); GPG/chave fora do allowlist → pick_sign_key die ANTES do pinentry (372); árvore suja por porcelain E por conteúdo contra índice temporário do HEAD (319-326, cobre assume-unchanged/skip-worktree); BASE_* divergente = die com ordem de remontar (350-351); .new divergente do declarado = die (355-356); binário instalado conferido por hash sem executar, exigindo mismatch EXATO {sha256=NEW, expected=OLD} (363-369).
   - TOCTOU verificar→aplicar nos canônicos: NÃO HÁ. Os .new são CONGELADOS em cópia (354) e o sha é medido NA CÓPIA (355-356); o apply (420-421), a re-conferência (422-423) e os blobs do commit (515-516, blob_is 531-532) saem todos da mesma cópia congelada; main avança por compare-and-swap (595-596) com INT/TERM/HUP ignorados na seção crítica (592).
   - «Override de kernel»: NÃO EXISTE no script (grep unlock/sota/kernel vazio nos dois scripts) — e não é necessário: a cerimônia roda fora do harness; o que há é hooks git desligados via GIT_CONFIG_* (54-56), escopo de processo documentado, NÃO herdado pela bateria (clean_env usa env -i com allowlist que não inclui GIT_CONFIG_*).
   - Segredos: nenhum caminho imprime OPENAI_API_KEY — só o COMPRIMENTO dela em mensagem de die (306); fingerprints e GPG_TTY não são segredos. Nada loga token.

4. GUARD DE PENDÊNCIA (pergunta 3): grep 'TODO(owner)' sobre sentinel + os dois .new = vazio; sem caracteres de controle nos 3 assináveis. Nenhuma OUTRA rota do marcador: o passo 1 só grava Anchor-SHA/Data por regex ancorada; o rehearse só REMOVE uma linha de digest em cópia clonada (rehearse-pin-0160.sh:449-450); o README contém o marcador mas não é lido pelo guard nem é texto assinável. Item 4 do residual é VERDADEIRO. O rehearse difere do molde só no cabeçalho (hunks 2-39 apenas).

5. FAIXA + PIN (pergunta 4), lido check_pair_rail.py: o verificador compara o sha256 do payload RESOLVIDO contra o entry do triple no manifesto (verify_codex_payload, 729-741); versão NUNCA relaxa o sha. Uma 0.160.x futura com outro payload ⇒ payload_sha256_mismatch ⇒ rc 1 ⇒ fail-CLOSED (CLI 2520-2524). Manifesto PRESENTE-mas-malformado ⇒ mismatch fail-closed (666-673); ausente ⇒ infra rc 3, que a cerimônia também recusa (367). Seams só sob CEO_PAIR_RAIL_TEST_MODE=1 e nunca relaxam o sha; a cerimônia roda com SEAM_UNSET explícito. A faixa é só version-gate do step 15, exatamente como o texto assinável declara.

6. RESIDUAL DO SENTINEL (pergunta 5): o item 1 nomeia os executáveis irmãos pela forma — e o tarball REAL confirma que existem (codex-code-mode-host 65 MB, codex-voice-host, rg, zsh, ~30 dylibs — todos fora do sha); a troca de INSTRUMENTO está declarada com o servido medido (gpt-6-astra, xhigh) no sentinel E no parágrafo do .new do pin. Claims de código verificadas: build_verdict_argv sem --json no rail vivo (codex_cli_shape.py:137,367-370); parse_usage_from_codex_stdout sem chamador fora de testes (só definição em adapters/codex.py:1026); step 15 confere codex_cli vs range + codex_payload_sha256 vs manifesto (validate-pair-rail-verdict.py:600-624, release.yml:760-763) e codex-cli-pin.txt ENTRA no inputs_hash (pair-rail-inputs-hash-manifest.txt); _codex_harness.sh lê a faixa com evidência fixada em 0.139.0 (linhas 43-49); ADR-111 não tem cabeçalho «pin-update-protocol»; PLAN-081/corpus/locked/ ausente do checkout. A mensagem de commit herdada relida contra ESTE re-pin: nenhuma frase falsa (a nuance «npm pack + shasum sobre o binário extraído» é coberta pelo residual item 3, e minha reprodução POR EXTRAÇÃO deu o mesmo valor).

## Achados

- [P2] OWNER-PIN-SIGN.sh:455-493 (corpo HERDADO do molde assinado; não-regressão): janela hash→exec no payload — o sha é medido em 455 e a phase 6/sonda T2 executam depois via symlink que re-resolve o caminho; um escritor same-UID pode trocar os bytes na janela. Mitigantes: o Gate 4 da phase 6 re-hasheia internamente; same-UID é limite PERMANENTE declarado do threat model (CLAUDE.md §5); bash sem openat («o check e o ato são UMA syscall?» — não). Cura: nenhuma neste pack (regenerar não muda o corpo do molde); registro para a wave do gerador/W3.

## Classe no gerador (seção separada — não decide o veredito)

- [P2] .claude/scripts/re-pin-codex.py: o artefato de plataforma TEM attestation SLSA provenance v1 + signatures no registry (dist.attestations medido na minha reprodução: registry.npmjs.org/-/npm/v1/attestations/@openai%2fcodex@0.160.0-darwin-arm64) e NENHUMA peça do pack/gerador a confere — toda a proveniência deriva de um único canal (registry npmjs). Nenhuma frase do sujeito fica falsa (o sentinel não alega independência de canais). Cura: no GERADOR, conferir a attestation (npm audit signatures ou fetch do endpoint) e registrar o resultado no sentinel gerado; fora deste pack.
- (Nota, sem severidade: a cura da classe do marcador TODO(owner) no gerador — nota que cita o marcador que o próprio guard recusa — já está declarada no item 4 do residual e confere.)

VERDICT: GO
```

## Triagem

- Codex 0.156.1 (read-only): «NENHUM ACHADO», VERDICT: GO.
- Lane Claude de segurança (R-RP-B): VERDICT: GO. Dois P2, ambos na classe do GERADOR ou do corpo
  herdado do molde, nenhum curável neste pack sem trocar o molde:
  - P2 `OWNER-PIN-SIGN.sh:455-493` — janela entre o hash do payload e a execução (phase 6 e sonda T2)
    para um escritor de mesmo UID. Corpo HERDADO byte a byte do molde 0156 já assinado (não regressão);
    o Gate 4 da phase 6 re-hasheia; mesmo UID é limite PERMANENTE declarado do threat model. DECLARADO
    (abaixo).
  - P2 de CLASSE no gerador (`.claude/scripts/re-pin-codex.py`, fora do sujeito): a attestation SLSA do
    artefato de plataforma existe no registry e nenhuma peça do pack ou do gerador a confere. Nenhuma
    frase do sujeito fica falsa (o sentinel não alega canais independentes). Não decide o veredito e não
    conta em Rail-Findings; vai para o follow-up do gerador.
- Lane Claude de especificação e afirmações (R-RP-A): VERDICT: GO-WITH-CONDITIONS.
  - P1 `pin-0160-approved.md:194` — «reportado para cura no gerador» não tinha registro rastreável no
    repositório. DECISÃO DO CEO: a cura fica FORA do pack, sem regenerar nem editar o sentinel — o
    follow-up `.claude/plans/PLAN-194-FOLLOWUP-repin-generator-hardening.md`, com os itens do gerador,
    foi landado no main antes deste registro; ver o `git log` do arquivo. Com ele no main, a frase do
    sentinel é verdadeira. Resolvido; não conta em Rail-Findings.
  - P2 `pin-0160-approved.md:142-144` — o motivo (2) do adiamento do ADR-161 subdeclara a sonda: a
    FD-02 também validou o arquivo `-o` de dois canários no caminho feliz. DECISÃO DO CEO: DECLARED-P2,
    sem mudar o sujeito (leitura defensável: a forma do STREAM de saída do `exec` não foi medida).
    DECLARADO (abaixo).
  - Nota da lane (não é achado): o commit traz oito arquivos, os seis do sujeito mais `rail-prompt.md`
    e `rail-record-template.md` (trilha do rail); lidos, nada neles contradiz o pack.
- Agregado: P0=0, P1=0 em aberto (o único P1 resolvido pelo follow-up landado), 2 P2 declarados no
  sujeito, 1 P2 de classe fora do sujeito. Rail-Verdict DECLARED-P2 com o revisor em GO: veredito
  agregado GO, série encerrada na rodada 1.

## P2 declarados

- `pin-0160-approved.md:142-144` — o motivo (2) do adiamento do ADR-161 diz que a sonda mediu o argv
  do rail, não a forma da SAÍDA do `exec`; a sonda também conferiu o arquivo `-o` de dois canários no
  caminho feliz (registrados no próprio sentinel, seção «Ratificação»). O que NÃO foi medido é a forma
  do stream de saída do `exec` e a diferença de fonte entre 0.156.1 e 0.160.0.
- `OWNER-PIN-SIGN.sh:455-493` (corpo herdado do molde 0156) — entre o hash do payload verificado e a
  execução dele pela phase 6 e pela sonda T2, um processo de mesmo UID pode trocar os bytes; o Gate 4
  da phase 6 re-hasheia, e mesmo UID é limite permanente declarado. Mesma postura do pack 0156, não
  regressão; cura, se houver, é da wave do gerador ou da W3.
