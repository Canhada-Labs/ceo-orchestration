# PLAN-194 — LEDGER, arquivo das seções fechadas (S361–S362)

Seções movidas do `.claude/plans/PLAN-194/LEDGER.md` em 2026-10-03 (S362), VERBATIM e na ordem em que
estavam no commit `904bdd94`. Tudo abaixo da linha horizontal é byte a byte o trecho removido do
LEDGER. O LEDGER guarda um ponteiro de uma linha por seção, com o sha256 deste arquivo. Este arquivo é
LIVRE (oráculo de canonicidade = 0) e não recebe entradas novas.

---

## W0.2 — manifesto do setup-python (controle vermelho da W1)

- 2026-10-01 (S361): no `versions-manifest.json` do ramo `main` de `actions/python-versions`, o
  Python 3.9 NÃO tem nenhum build linux para Ubuntu 26.04 (só até 24.04); 3.10 e 3.14 têm.
- ARQUIVADA em 2026-10-02 (S362), depois do LAND da W1 (`c54934d8`); o texto acima é o integral.

## W0.1 — Docker `ubuntu:26.04` (parcial)

- ARQUIVADA em 2026-10-02 (S362), depois do LAND da W1 (`c54934d8`), cujo sentinel assinado
  (`wave-w1-approved.md`, seção «Evidência») cita este registro. O título fica, para a âncora não
  mudar. Texto integral (substrato, itens (a) a (d), ferramenta e limpeza): `git show
  97a78fce:.claude/plans/PLAN-194/LEDGER.md`, linhas 52 a 198.
  verifier: `git show 97a78fce:.claude/plans/PLAN-194/LEDGER.md | sed -n '52p' | grep -q '^## W0.1 '` exit=0
- Resumo: medido de 2026-10-01T20:41Z a 2026-10-02T03:30Z (S361), colima aarch64 com 4 CPU e 6 GiB;
  `ubuntu:26.04` = `sha256:da6fc2be547864451aa253836dd926da33623312df4a9a243e35dc877c378a78` («Ubuntu
  26.04.1 LTS»), `python3` 3.14.4 na imagem.
  - (a) Template do adopter ativado e executado: 10/10 steps `run:` verdes no 26.04 e no 24.04 ⇒ W1.4
    sem mudança.
  - (b) Job `validate` antes do `setup-python`: só o step dos `import yaml` depende do sistema (PyYAML
    ausente) ⇒ W1.2.
  - (c) Suíte da matriz no 3.14: falhas contidas na linha de base 3.12, todas da classe «orçamento de
    tempo absoluto» ⇒ nada atribuível ao 3.14 nem ao 26.04.
  - (d) Censo: 21 workflows em `ubuntu-latest` (28 jobs) e 6 jobs `Ceo`; nenhum marcado como quebrando
    ⇒ W1.5 sem pacote. Não medidos: os dois jobs do `npm-publish.yml` e o TLC do `formal-verify.yml`.

## W3b.3 — verificação em fonte primária (ids da OpenAI)

- 2026-10-02 ~00:30Z (S361), fonte: página oficial de deprecações da OpenAI
  (`https://platform.openai.com/docs/deprecations`, que redireciona com 301 para
  `https://developers.openai.com/api/docs/deprecations`), lida por WebFetch (extração por modelo
  auxiliar; as linhas abaixo foram pedidas verbatim):
  - seção «2026-06-11: GPT-5 and o3 model deprecations»: desligamento em **Dec 11, 2026** de
    `gpt-5-2025-08-07`, `gpt-5-mini-2025-08-07`, `gpt-5-nano-2025-08-07`, `gpt-5-pro-2025-10-06`,
    `o3-2025-04-16` e `o3-pro-2025-06-10` (substitutos `gpt-5.6-sol`/`-terra`/`-luna`);
  - seção «2026-04-22: Legacy GPT model snapshots (July 2026 shutdown)»: desligamento em
    **July 23, 2026** (já passado) de `gpt-5-codex`, `gpt-5-chat-latest`, `gpt-5.1-codex`,
    `gpt-5.1-codex-max`, `gpt-5.1-codex-mini`, `gpt-5.2-codex`, `gpt-5.1-chat-latest` e
    `o3-deep-research-2025-06-26`;
  - **`gpt-5.5` NÃO aparece na página** ⇒ a aposentadoria em 2026-10-14 NÃO se confirma; pelo texto
    da W3b.3 o item fecha sem a linha no `model-deprecations.json` (Check: none, resultado aqui).
  - `o3-mini`: uma primeira extração resumida citou «October 23, 2026», mas a extração verbatim não
    trouxe linha de `o3-mini` ⇒ NÃO confirmado; re-conferir à mão antes da W3b.1.
- Consequência para a W3b (achado do builder da W3b.0 + esta leitura): com a cura do detector, uma
  variante só casa se o ledger a listar; `gpt-5-codex` (desligado em 2026-07-23) e os demais ids da
  seção de julho precisam entrar no `model-deprecations.json` para não ficarem escondidos (hoje o
  `gpt-5-codex` aparece em `codex_invoke.py` e `codex_phase_gate.py`). Entra no refresh do ledger
  junto da W3b.3 (mesmo arquivo; a regra INERT do `check-model-currency.py:64`, opção A do builder,
  vai no mesmo land).
- 2026-10-02T00:55Z (S361), re-conferência pedida acima («re-conferir à mão antes da W3b.1»), feita
  pelo builder da W3b.1 sobre o HTML CRU da mesma página (`curl -sSL
  https://developers.openai.com/api/docs/deprecations`, 482.750 bytes, sha256
  `d7f797e77e57c9b05c6b2e569499a60ece6a6917c934cdb779c4149a631d552d`; texto extraído por script,
  sem modelo auxiliar). A página tem DUAS seções com data 2026-04-22: a de julho (lida acima) e
  «2026-04-22: Legacy GPT model snapshots», SEM o parêntese, cujas linhas têm desligamento em
  **October 23, 2026** — 12 snapshots na tabela principal e 5 modelos com ajuste fino. Entre elas:
  - `o3-mini-2025-01-31 | o3-mini`, substituto `gpt-5.6-sol` ⇒ `o3-mini` CONFIRMADO (supera a linha
    «NÃO confirmado» acima; a primeira extração resumida acertou a data);
  - `o4-mini-2025-04-16 | o4-mini`, substituto `gpt-5.6-terra` ⇒ `o4-mini` também se aposenta (não
    estava na leitura de 2026-10-02 ~00:30Z).
  - `gpt-5.5` segue AUSENTE da página (0 ocorrências no HTML cru).
- Consequência (land livre, antes do SIGN da W3b.1): `o3-mini` e `o4-mini` ganham linha no
  `model-deprecations.json` (substituto `gpt-5.6-sol` pela política de alvo único do `_meta`; a
  página dá `gpt-5.6-terra` para o `o4-mini`, registrado na nota da linha), e o mapa de dívida
  `W3B1_DECLARED_DEBT` cresce de 12 para 14 acertos (os dois em `codex_cli_shape.py`). As outras 15
  linhas da seção de outubro (`gpt-3.5-turbo*`, `gpt-4*`, `o1*`, `gpt-image-1`, ajuste fino) e as 6
  linhas da seção de julho que o ledger não tem (`computer-use-preview*`, as duas `*-search-preview`,
  `gpt-audio-mini-*`, `gpt-realtime-mini-*`, `o4-mini-deep-research*`) NÃO entram: medido com um
  ledger de sonda contendo todas elas, nenhuma tem referência viva (não-INERT) nesta árvore
  (`check-model-deprecations.py --ledger <sonda> --json --today 2026-10-13` = só os 14 acertos acima).
  Ficam como backlog declarado (refresh completo do ledger da OpenAI, com substitutos por faixa
  depois que a W3b.1 põe a família `gpt-5.6-*` em `_VALID_MODELS`). A linha `o3-deep-research-2025-06-26`
  do ledger diz que nenhum alias sem data foi inferido, mas a página lista `o3-deep-research` como
  alias — mesmo backlog.

## W0.6 — verificador de procedência do Codex (S361, 2026-10-02)

- Medição completa (comandos, versões, células, saídas): fora do repositório, no checkpoint
  `s361-packs/b11-w06/W0.6-medicao.md` da sessão S361 (npm 11.16.0; `sigstore` 4.1.1 interno do npm;
  versões 0.160.0 e 0.156.1 do Codex; registro oficial e CDN do TUF do Sigstore).
- `npm audit signatures` NÃO serve para a W3: verifica só o que o REGISTRO declara (assinatura do
  registro e bundle do atestado), não os bytes locais, não fixa identidade, não exige o atestado e fica
  verde sem rede com cache quente. Células medidas: payload adulterado instalado ⇒ exit 0 «verified»;
  atestado removido ⇒ exit 0; atestado de outro repositório ⇒ verde.
- O `sigstore` interno do npm chamado com política de identidade (`certificateIdentityURI` +
  `certificateIssuer`) + vínculo em stdlib (sha512 do tarball = `subject` do atestado; sha256 do
  `bin/codex` lido em fluxo) dá verde no íntegro e vermelho em toda adulteração e identidade divergente.
  Decisão de desenho pendente do Owner: módulo interno do npm vs. `sigstore` fixado no staging.
- Identidade literal do construtor (0.160.0 e 0.156.1): repositório `https://github.com/openai/codex`,
  workflow `.github/workflows/rust-release.yml`, ref `refs/tags/rust-v<X.Y.Z>`, emissor OIDC
  `https://token.actions.githubusercontent.com`, `predicateType` `https://slsa.dev/provenance/v1`,
  purl de plataforma `pkg:npm/%40openai/codex@<X.Y.Z>-darwin-arm64`.
- Tamanhos 0.160.0: tarball de plataforma 134.311.083 bytes (332.972.398 descomprimido; `bin/codex`
  241.555.024). O pacote de plataforma traz outros executáveis fora do sha256 pinado (`rg`, `zsh`,
  `codex-voice-host`, dylibs) — entra no «escopo honesto» do ADR-182-AMEND-1.
- Controle: o sha256 do `bin/codex` da 0.156.1 lido do tarball = o do manifesto assinado (`0196e89f…`).

## Arquivo (S362, 2026-10-02)

- T0 (topo): CONGELADO no lugar, sem edição. `debate/round-1/security-engineer.md:263` cita
  `LEDGER.md:16-18`, `debate/round-1/qa-architect.md:40` cita «LEDGER, T0», e os registros de debate
  não se editam. A última frase do T0 está superada pela seção RP.
- W0.2 e W0.1: arquivadas nas próprias seções, com os títulos mantidos (âncoras estáveis). O texto
  integral da W0.1 está no histórico do git, preso ao `97a78fce` do `main`.
- O `LEDGER-ARCHIVE.md` da convenção do hook de checkpoint não foi criado nesta rodada; o histórico do
  git faz o papel de arquivo.
