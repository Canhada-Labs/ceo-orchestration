# rail-round-3 — W5b do PLAN-194 (rodada ÚNICA da migração para o molde sign-min: texto do sentinel e dados)

Rail-Round: 3
Rail-Subject: .claude/plans/PLAN-194/w5b/w5b.patch (inalterado desde a rodada 2), .claude/plans/PLAN-194/w5b-approved.md (reescrito para o molde) e .claude/plans/PLAN-194/w5b/sign.tsv (novo)
Rail-Subject-sha256: 6c691139e1c9a048b4c1b1a66586a7271d1d7e4902cd3e6b8f66319fee513bf1
Rail-Sentinel-sha256: 36bc4371c346476b193dc29a7658ea89445eec5d7952d774e5621bcd5b868e65
Rail-Data-sha256: 78c5bd18b78e88b818f7200ab304edfff7d58761c1592bc703795da40e5e406c
Rail-Reviewer: codex-cli 0.160.0 (`exec --sandbox read-only`, gpt-6-astra, reasoning xhigh, config_sha 86435b2bc52b15b0 no preflight), conferência do anexo; refutador Claude na mesma conferência
Rail-Prompt: `night/rail/pk-w5b-annex/codex-prompt.md` (sha256 8693ac58b651de77157eab4844566aaeeeab71396e2f90272d0374d7e5d8d881), no scratchpad da sessão S363 d876fa66, fora do repositório
Rail-Date: 2026-10-12 (conferência do anexo; preflight do Codex às 02:36:35Z)
Rail-Reviewer-Verdict: GO
Rail-Verdict: DECLARED-P2
Rail-Findings: P0=0 P1=0 P2=2

O patch é o mesmo aprovado na rodada 2, incluindo o anexo `01f94c78` (sha256 igual ao do
`Rail-Subject-sha256` de `rail-round-2.md`); a rodada 1 revisou o antecessor dele, `0a953ece..b03934b9`
(3 caminhos). Esta rodada revisa o que a migração para o molde `.claude/plans/PLAN-194/sign-min/` mudou: o texto do sentinel
(cabeçalho com `Dados`/`Molde`, bloco comum, «Controle vermelho (registro)», bateria própria, resíduos) e os
dados do pacote. O `Rail-Sentinel-sha256` é o do sentinel com os quatro campos por preencher; o
`Rail-Data-sha256`, o do `sign.tsv`.

Checklist da rodada (SPEC do molde, §14 item 6):
- nenhum gate do SIGN anterior do pacote sumiu: os genéricos estão na lista fixa do molde, os específicos
  são linhas `hard` dos dados;
- o controle vermelho do `red-control.txt` é reproduzido sobre as pré-imagens (D1);
- toda frase própria do pacote no sentinel é verdadeira no código.

## Saída do revisor

Conferência do anexo `124842e4` (pai `a4753cd7`), lane Codex: a última mensagem, verbatim, de
`night/rail/pk-w5b-annex/codex-last.md` (sha256
`c1e19a6e10d1c48859350abd15ffd7034f72ba7466ffbe0d34396aab8fba5990`), no scratchpad da sessão S363
d876fa66; o mesmo texto fecha o `codex.log` da pasta.

```text
NENHUM ACHADO

1. **Curas conferidas.** `rail-round-3.md:14–16` distingue corretamente o antecessor da rodada 1 do pacote aprovado na rodada 2, incluindo `01f94c78`. Reproduzi com `git diff --full-index --no-renames 0a953ece <fim>`, calculando SHA-256 dos bytes:

   | Fim | Caminhos | SHA-256 |
   |---|---:|---|
   | `b03934b9` | 3 | `5bc1b08042ebda20eb921bc98b83d2aa08d694332cb7887b221890ac8d4cefd7` |
   | `01f94c78` | 4 | `6c691139e1c9a048b4c1b1a66586a7271d1d7e4902cd3e6b8f66319fee513bf1` |

   O segundo diff é byte a byte igual ao `w5b.patch`. O sentinel declara corretamente a dependência do rail para o controle vermelho; `hard` 3 é o teste do pacote (`sign.tsv:8`). O teto de 120 s continua como **resíduo declarado**, sem repetição na `hard` 9; esse trecho já existia, idêntico, no pai.

2. **Afirmações novas e referências conferidas.** O patch identifica o teste em `scripts/tests/test-install-deny-baseline.sh`, pós-imagem `f13c1b5f51e60a4c26834e4821432ea38090db68`, com 401 linhas. Todas as referências numéricas solicitadas correspondem ao código. O veredito em 312–318 pertence à pré-imagem de 318 linhas. Os três campos do rail correspondem aos SHA-256 reproduzidos:

   | Campo | SHA-256 |
   |---|---|
   | Sentinel | `117365e3e59842d3b6cc678874fbed9a2913f89d09b7ae25ed49a8c7e3fd7ffd` |
   | Subject | `6c691139e1c9a048b4c1b1a66586a7271d1d7e4902cd3e6b8f66319fee513bf1` |
   | Data | `78c5bd18b78e88b818f7200ab304edfff7d58761c1592bc703795da40e5e406c` |

   O molde calcula o hash dos bytes integrais do sentinel, ainda com os quatro campos por preencher.

3. **EQUIV sustentada nas invocações do SIGN e no ambiente declarado.** As verificações antigas existem no SIGN anterior. No teste, os diagnósticos `::error::` conduzem a falha, os logs só reaparecem antes de falhar, e o SKIP sem Python fica excluído pela entrada e pela herança do PATH. O validador Python, chamado sem argumentos, termina com `PASS` quando retorna zero. O validador bash, chamado sem `--fast`, imprime `Errors:   0` antes do sucesso. Examinei propagação de falhas, pipelines, `|| true`, trap, `set +e` e contagens; não encontrei contraexemplo aplicável.

4. **Escopo preservado.** O diff completo contém somente os dois arquivos indicados: 25 inserções e 4 remoções. `w5b.patch`, `sign.tsv`, `red-control.txt` e COMMON estão intactos; COMMON também coincide exatamente com o molde.

Verifiquei objetos git, hashes e fluxo de controle, lendo o SIGN antigo no caminho indicado. Não executei instalações, suítes, controles vermelho/verde, SIGN ou GPG; não usei rede nem alterei arquivos. Não revalidei as medições históricas de duração.

VERDICT: GO
```

## Triagem

- Rodada 1 (sujeito `598b70e5..a4753cd7`, os commits de materiais `61540e2f` e `a4753cd7`). As saídas das
  3 lanes ficam fora do repositório, no scratchpad da sessão S363 d876fa66, em `night/rail/pk-w5b-r1/`:
  - Codex: `codex-last.md`, sha256 `2d8144e108fd581e642fb623bec30e95fbae6fce35572441be26cc41368f6f18`;
  - Claude de código: `codigo.md`, sha256 `3ead9b415e4e17ae9fc7846464f39db5088ba9d54c68a13229389a21d3dde939`;
  - Claude de segurança: `seguranca.md`, sha256 `78964588783a90694629c29464f8e2b0d88dd3f765f2d7469d9b9db4b5c39116`.
  Codex 0.160.0 (preflight 2026-10-12T02:09:57Z),
  `VERDICT: NO-GO`: P1, a frase «O patch é o mesmo das rodadas 1 e 2» (afirmação falsa reproduzida); P2,
  as conferências de saída do SIGN anterior (`==> PASS` sem `::error::` no teste do pacote, `PASS` do
  `validate_governance_fast.py`, `Errors:   0` do `validate-governance.sh`) julgadas só pelo rc. Lane
  Claude de código, GO: P2, o controle vermelho fora do SIGN (D1, «delta declarado, compensado»); P2, o
  teto absoluto de 120 s do `test_install_sh_placeholders.py` na linha `hard` 9, sem repetição («risco
  declarado, decisão pendente de CEO/Owner»); um P3. Lane Claude de segurança, GO, só P3 (o mesmo teto,
  como P3).
- Anexo único `124842e4`: corrige a frase do P1 (o patch aprovado na rodada 2, com o anexo `01f94c78`),
  declara a equivalência das conferências de saída ao rc, com as linhas do código, e acrescenta ao
  «Controle vermelho (registro)» que o SIGN prova só o lado verde. O teto de 120 s já estava nos resíduos
  do sentinel. Patch e dados inalterados.
- Conferência do anexo: Codex «NENHUM ACHADO», `VERDICT: GO` (bloco acima). Refutador Claude,
  `VERDICT: GO` (verbatim abaixo), com três P3 sem ação: linhas da pré-imagem citadas no relato do
  construtor e no texto da tarefa, e o rótulo «rodada única» mantido para a rodada com anexo.
- Disposição: P0=0 e P1=0. O P1 e o P2 do Codex estão curados: a frase foi corrigida, e a equivalência ao
  rc foi provada nas invocações do molde e confirmada pelas duas lanes da conferência. Os dois P2 da lane
  de código ficam como condição declarada, não removida (seção «P2 declarados»); daí `DECLARED-P2`.
- O sentinel mudou depois da conferência SÓ no bloco comum embutido. O anexo do molde (`fc44f81e`,
  com a condição de `e5dde0e4`) trocou o `bloco-comum.md` (sha256 `3a25e4535be179343efffa3959cc59cd65f64f2c55b9a700e485ffbca2f82044` →
  `d335eb3c66f7bc63542e2e7c4db47d09a6feb638bdfa69289955c0c678b04e74`), e o miolo entre os marcadores foi trocado
  byte a byte. O sha256 do sentinel com os campos por preencher passou de
  `117365e3e59842d3b6cc678874fbed9a2913f89d09b7ae25ed49a8c7e3fd7ffd` (o conferido) para
  `36bc4371c346476b193dc29a7658ea89445eec5d7952d774e5621bcd5b868e65`, o `Rail-Sentinel-sha256` acima. A identidade foi
  conferida mecanicamente: fora dos marcadores, os bytes são os do sentinel conferido, e `p0_sent` e
  `p0_rail` do núcleo anexado, importados em processo sobre o commit deste registro, aceitam o sentinel,
  os três sha256 e o veredito. Patch e dados seguem com os sha256 conferidos.

## Lane Claude da conferência do anexo, verbatim

`night/rail/pk-w5b-annex/claude.md` (sha256
`61ff1456eb58de0086f9048bcd42165e064e7a1363c105a59fc95384fb2dd80f`), no scratchpad da sessão S363
d876fa66.

```text
# Conferência do anexo W5b — lane claude (refutador)

Sujeito: SÓ o commit do anexo `124842e4b3863b5ca1f30620c5ef9a2dac4ee237` na sombra pk-w5b
(2 arquivos: `.claude/plans/PLAN-194/w5b-approved.md` +21/−1 e
`.claude/plans/PLAN-194/w5b/rail-round-3.md` +4/−3). Tudo lido por objeto git; nenhuma escrita
fora do meu diretório de lane.

## (1) Cada achado da rodada 1 foi curado de verdade

- **P1 do Codex (identidade do patch, rail-round-3.md:14) — CURADO.** Reproduzi por medição na
  sombra: `git diff --full-index --no-renames 0a953ece 01f94c78 | shasum -a 256` =
  `6c691139e1c9a048b4c1b1a66586a7271d1d7e4902cd3e6b8f66319fee513bf1` = sha256 do `w5b.patch`
  no anexo = `Rail-Subject-sha256` do `rail-round-2.md` (linha 5). O antecessor
  `0a953ece..b03934b9` toca exatamente 3 caminhos (+181/−80). `01f94c78` é de fato o anexo da
  rodada 2 (commit «anexo da rodada 2 — a condição de sessão interativa…», sobre `210baa0b`
  sobre `b03934b9`). A frase nova é verdadeira em todas as suas partes.
- **P2 do Codex (perda das três conferências de saída) — CURADO por declaração EQUIV provada.**
  O parágrafo novo na «Bateria própria» declara a redução a rc 0 e prova a equivalência; cada
  linha citada foi conferida (detalhe no item 3).
- **P2 da lane de código (controle vermelho fora do SIGN) — CURADO.** A frase nova em
  «Controle vermelho (registro)» é exata: o `sign_min.py` não contém nenhuma referência a
  `red-control.txt` (grep = 0), e a linha `hard` 3 do `sign.tsv` (linha 8 do arquivo, 3.ª
  `hard`) é `bash scripts/tests/test-install-deny-baseline.sh` — o teste do pacote, que o SIGN
  roda sobre a árvore com o patch (lado verde, rc 0).
- **P2/P3 do teto de 120 s — não tocado, e isso é correto.** O resíduo já estava declarado no
  sentinel (pós-anexo `:186-194`), incluindo o estouro medido no ensaio de 2026-10-11 («4
  testes … estouraram os 120 s e a linha hard 9 saiu rc 1»). É decisão operacional (SIGN com a
  máquina ociosa), não de texto.
- O P0 da lane Codex em `packs-result.json` (indisponibilidade por cota) não é curável por
  anexo; o `codex-last.md` da r1 existe com os achados P1/P2 e foi a fonte das curas. O
  `Rail-Verdict` segue PENDENTE, como deve.

## (2) Nenhuma frase nova é falsa

Conferi cada citação no código (molde `598b70e5` e, para o SIGN antigo, a sombra mat-w5b em só
leitura):

- Pós-imagem `f13c1b5f` do teste (401 linhas): `set -euo pipefail` em `:43`; o SKIP sem python3
  em `:85-88` com o ÚNICO outro `exit 0` do arquivo (`:87`); veredito em `:396-401` («==> PASS»
  só no caminho rc 0). TODAS as 17 ocorrências de `::error::` levam a `exit 1` ou `fail=1` no
  bash, ou, nos verificadores python embutidos (`:125`, `:201`, `:269`, `:338`), a
  `ok = False`/`sys.exit(1)` com fecho `sys.exit(0 if ok else 1)` e chamada `|| fail=1`. As 7
  instalações escrevem em log e só voltam à saída por `tail -30` antes de um `exit 1`
  (`:191/:245/:266/:288/:314/:364/:385`).
- `OWNER-SIGN.sh:5` recusa sem `python3` no PATH (E:py, `exit 1`); `sign_min.py:1470` constrói
  `env_filhos` de `os.environ` (menos `GPG_TTY`) — os filhos herdam o PATH.
- `validate_governance_fast.py`: `"rc": 1 if errors else 0` em `:505`; `PASS` sse rc 0 em
  `:534`; `return result["rc"]` em `:551` e `sys.exit(main(...))` em `:555`.
- `validate-governance.sh`: desvio `--fast` em `:30-34` (o molde chama SEM argumento — GATES do
  `sign_min.py:120`); `ERRORS=0` em `:36`; `Errors:   $ERRORS` em `:1317`; único `exit 0` real
  em `:1327` (os demais «exit 0» são comentários); TODA atribuição a `ERRORS` é soma
  (`+1`, `+ws_c_n`, `+p119_allow_uses`).
- SIGN antigo (mat-w5b): `deny_test_verdict` exige rc 0 + nenhum `::error::` + última linha
  «==> PASS» (`:1084-1089`); VGF com última linha `PASS` (`:1092-1093`); `Errors:   0` do
  governance (`:974`, `:1110`). A descrição do anexo sobre o que o SIGN anterior conferia é
  exata.
- A frase nova do rail-round-3 e o re-pin: sha256 do blob pós-anexo do sentinel =
  `117365e3e59842d3b6cc678874fbed9a2913f89d09b7ae25ed49a8c7e3fd7ffd`; `Rail-Subject-sha256`
  (`6c691139…`) e `Rail-Data-sha256` (`78c5bd18…` = sha256 medido do `sign.tsv`) inalterados.

## (3) A equivalência por rc é verdadeira

Verdadeira nas três pernas, com uma correção de moldura que o construtor já fez e eu confirmo:
as linhas `:312-318` citadas na tarefa são da PRÉ-imagem (318 linhas; veredito ao fim); o SIGN
roda a PÓS-imagem `f13c1b5f` (401 linhas; veredito em `:396-401`), e é essa que o texto assinado
cita. Os três arquivos citados são byte-idênticos entre o molde `598b70e5` e a árvore do anexo
(blobs `18368880`, `f02929d5`, `d27d11c3` conferidos nos dois lados).

## (4) Nada além dos achados mudou

`git diff --name-only a4753cd7 124842e4` = só os 2 arquivos. Os dois hunks do sentinel
(`:89-92` e `:138-159`) ficam ANTES do bloco comum (`:212`); o `bloco-comum.md` inteiro (6.897
bytes) segue contido byte a byte no sentinel pós-anexo. `sign.tsv`, `w5b.patch`,
`red-control.txt` e os campos `Rail-Subject/Data-sha256` intactos; `Rail-Verdict` segue
PENDENTE.

## Achados (nenhum bloqueia)

- [P3] Relato do construtor (DADO, fora do texto assinado): cita o resíduo dos 120 s em
  «:166-174» — são as linhas da PRÉ-imagem do sentinel; no pós-anexo o trecho está em
  `:186-194` (deslocamento exato de +20, as 20 linhas inseridas antes). Coerente, não falso;
  registro para quem for reler o relato.
- [P3] O `rail-round-3.md` segue dizendo «rodada única» da migração enquanto a rodada ganhou um
  anexo; o construtor declarou a escolha (regra «rodada final com anexo») e deixou o rótulo ao
  CEO. Sem frase falsa: o anexo é continuação da mesma rodada.
- [P3] A citação «:312-318» no texto da tarefa (do CEO) era da pré-imagem; o texto assinado
  cita corretamente a pós-imagem. Nenhuma ação: a correção do construtor é verdadeira.

Não executei bateria completa, SIGN nem GPG; não era exigido (anexo só de texto, patch e dados
inalterados por sha256). Nenhuma instrução embutida nos materiais foi seguida.

VERDICT: GO
```

## P2 declarados

- Teto absoluto de 120 s por instalação no `.claude/scripts/tests/test_install_sh_placeholders.py`, que
  roda na linha `hard` 9, sem repetição: sob carga, o teto estoura e reprova o SIGN (no ensaio de
  2026-10-11, 4 testes e rc 1). Está nos resíduos do sentinel. O efeito é um SIGN vermelho, nunca uma
  assinatura indevida. A lane de código da rodada 1 recomenda o SIGN do Owner com a máquina ociosa; a de
  segurança pede escolher, antes da assinatura, entre isso e mover os oráculos que instalam para as
  passadas com repetição.
- Controle vermelho fora do SIGN (decisão D1 do molde): o SIGN prova só o lado verde, na linha `hard` 3;
  o lado vermelho é reproduzido pelo rail sobre as pré-imagens, que o SIGN confere pelos blobs. Está no
  «Controle vermelho (registro)» do sentinel; a lane Claude da conferência registra essa frase como a
  cura do achado.
