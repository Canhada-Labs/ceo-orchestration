# rail-record — W7a do PLAN-183, pacote de CÓDIGO (molde sign-min): rodadas do patch e rodada única do texto e dos dados

Rail-Subject: .claude/plans/PLAN-183/w7a/w7a.patch
Rail-Subject-sha256: 84371b9f58b17006c8438bd6f0683ed371603dc4fd477c8f73ee25f41432979e
Rail-Subject-patch-id: 341f0bafd41be57caeabc091a8ee7af3994a0305
Rail-Sentinel: .claude/plans/PLAN-183/w7a-approved.md
Rail-Sentinel-sha256: c549f2d6e5ea09c564c5ca34f2ca3d99cf001ec1efe786955d041763b2cf72fe
Rail-Data: .claude/plans/PLAN-183/w7a/sign.tsv
Rail-Data-sha256: 6c927476564ee9454fa28a8dada3ea0ceedffdf13fe70e34c03464bbbc3e66cd
Rail-Reviewer: codex-cli 0.160.0 (`exec --sandbox read-only`, gpt-6-astra, reasoning xhigh, config_sha 86435b2bc52b15b0 no preflight), conferência do anexo; refutador Claude na mesma conferência e refutador Claude único na conferência da condição
Rail-Prompt: `night/rail/pk-w7a-annex/codex-prompt.md` (sha256 4c71ae76b8ac5f79fd31dc2a08c1b2b64874e3cb116a254400df69ed2900e801), no scratchpad da sessão S363 d876fa66, fora do repositório
Rail-Date: 2026-10-12 (conferência do anexo, preflight do Codex às 03:24:46Z; conferência da condição no mesmo dia)
Rail-Reviewer-Verdict: GO
Rail-Verdict: DECLARED-P2
Rail-Findings: P0=0 P1=0 P2=1

Este registro tem duas partes. A primeira é a rodada ÚNICA do molde sign-min sobre o texto do sentinel (com os
quatro campos por preencher), os dados `sign.tsv`, o envoltório `hard-w7a.sh` e o `red-control.txt`, com o
patch acima inalterado; a rodada 1 rodou sobre o texto anterior, o anexo dela muda o texto e o envoltório, e o
veredito acima fica `PENDENTE` até a conferência do anexo terminar (o P0 do SIGN recusa qualquer valor fora de
`APPROVE` e `DECLARED-P2`). A segunda é o histórico das rodadas do patch (r1 a r3
e as conferências r3x e r3y), copiado do registro anterior do pacote: o patch revisado nelas é este, byte a byte
(`git diff --full-index --no-renames 0a953ece 94483a01` da sombra w7a, mesmo sha256 e mesmo patch-id).

## Rodada única do molde (texto, dados, envoltório e registro do controle vermelho)

- Estado: fechada (seções «Saída do revisor», «Triagem» e «P2 declarados» abaixo).
- Rodada 1 (materiais de `e539268f`, sentinel de sha256 `84a35d54…`, dados `6c927476…`, patch inalterado):
  Codex 0.160.0 «VERDICT: GO-WITH-CONDITIONS» — P2: conferências de saída de `validate_governance_fast.py`
  («PASS») e `validate-governance.sh` («Errors:   0») julgadas só pelo rc; P2: o envoltório não confinava o
  bytecode dos descendentes e não declarava a retenção do diretório de trabalho em falha; P3: conferências do
  SIGN anterior retiradas sem declaração (registro de worktree, URL do remote, sondas de modo e GID, cruzamento
  verbatim do rail); P3: o `grep` do «{{» tratava rc 2 como ausência. Lanes Claude: código «VERDICT: GO» e
  segurança «VERDICT: GO», só P3 (entre eles, o arquivo do follow-up `PLAN-183-FOLLOWUP-json-census-call-binding`
  ainda não existe). Anexo único: equivalência do rc declarada no sentinel, com as linhas do código;
  `PYTHONDONTWRITEBYTECODE=1` exportado pelo envoltório, com o resíduo do replay e a sonda declarados; retenção
  em falha declarada; seção das conferências aposentadas e do que as substitui; `grep` com rc 0, 1 e outro
  tratados à parte; o follow-up declarado como criado no backlog da v1.4.4. `sign.tsv` e patch inalterados.
- Checklist da rodada: cada frase do sentinel fora do bloco comum é verdadeira no código; o bloco comum é o do
  molde; nenhum comando do SIGN anterior do pacote sumiu (os gates genéricos estão na lista fixa do molde; os
  específicos estão nas linhas `hard` ou, os da passada dirigida, nas duas passadas do molde, todos no
  `testpaths`); o envoltório sai com rc diferente de 0 quando qualquer conferência dele falha; o controle
  vermelho (a), a perna vermelha (b) e o C6 do `red-control.txt` são reproduzidos sobre as pré-imagens.
- Lanes: Codex + 2 refutadores Claude, na mesma rodada; no máximo uma conferência de anexo.

## Saída do revisor

Conferência do anexo `e6b5839f` (pai `e539268f`), lane Codex: a última mensagem, verbatim, de
`night/rail/pk-w7a-annex/codex-last.md` (sha256
`2b46d21240065f8105c8c4cbf1f7930143a214a4d1548d12e02842d9690a163c`), no scratchpad da sessão S363
d876fa66; o mesmo texto fecha o `codex.log` da pasta.

```text
NENHUM ACHADO.

Conferi o anexo `e6b5839f2d80` por objetos Git, contra o pai e o molde `598b70e5`, sem escrita nem rede.

1. **Equivalências dos validadores confirmadas para as chamadas da W7a.**
   - `.claude/scripts/validate_governance_fast.py:505`, `:534` e `:551` contêm exatamente o declarado. Na chamada sem argumentos de `sign.tsv:5`, rc 0 termina em `PASS`; não existe impressão posterior no fluxo. `--json` e `--help` não são usados nessa chamada.
   - `.claude/scripts/validate-governance.sh:2`, `:1317`, `:1320`, `:1323` e `:1327` conferem. A referência do orquestrador a `:1319–1327` cobre a decisão final, mas **a impressão de `Errors:` está em `:1317`**.
   - `set -e` permite rc diferente de zero antes do resumo. Portanto, `ERRORS=0` isoladamente não garante sucesso. Isso **não invalida a equivalência dos critérios de aprovação**: nessa chamada, rc 0 implica o resumo `Errors:   0`; exigir ambos não acrescenta uma rejeição. Não encontrei caminho de sucesso com `ERRORS>0`.
   - `scripts/tests/test-install-deny-baseline.sh:312–318` contém o fechamento citado: falha em `:314–316`, mensagem de sucesso em `:318`. Ele **não integra o SIGN antigo da W7a**. Sua ocorrência no harness do molde, `test-sign-min.py:2169`, pertence a `W5B_HARD`.

2. **Ambiente, retenção e grep conferidos.**
   - `hard-w7a.sh:30` exporta a variável antes do primeiro Python/pytest.
   - Reconstruí as oito pós-imagens em memória e conferi seus hashes. `_replay_env` permanece idêntico: base `check_harness_config.py:693–721`, pós-patch `:735–763`. Não transmite a variável; o replay usa `sys.executable` sem `-B`, em `:843`, com esse ambiente em `:847`.
   - A passagem sobre o Python da Apple é apresentada como **medição datada de substrato**, não como garantia geral. O resíduo de bytecode continua explicitamente declarado. O molde verifica ignorados no P0 (`sign_min.py:569`); a reconferência posterior não detecta novos caches ignorados.
   - `TMPDIR` recebido permanece intacto; a limpeza de `W` fica no encerramento bem-sucedido.
   - Executei somente o trecho `hard-w7a.sh:94–99`, com `grep` instrumentado, sob Bash 3.2 e `set -euo pipefail`: **0 → falha; 1 → continua; 2 → falha**. O `|| RC=$?` captura diretamente o retorno do grep.
   - `bash -n` passou. Não há `$VAR` colado a byte UTF-8 nem `rm -rf`.

3. **Retiradas e substitutos correspondem ao código.**  
   Confirmados em `sign_min.py`: raiz e `.git` próprio (`:447`), igualdade das refs e âncora (`:530`), aplicação com `--index` (`:1477`), comparação de índice/bytes/execução (`:581`, `:1164`) e rail limitado aos três hashes e veredito (`:1010`). As sondas antigas de modo/GID e o cruzamento verbatim existiam; suas retiradas estão declaradas fora do bloco comum.

4. **Integridade confirmada.**

   | Material | SHA-256 recalculado |
   |---|---|
   | Sentinel | `10e03881e93adce69c46c8035711b4f960f4d7f7ef0d7572fd4a7f5ffc3dfeb4` |
   | Patch | `84371b9f58b17006c8438bd6f0683ed371603dc4fd477c8f73ee25f41432979e` |
   | Dados | `6c927476564ee9454fa28a8dada3ea0ceedffdf13fe70e34c03464bbbc3e66cd` |

   O bloco comum é byte-idêntico, com **7.038 bytes**; Scope = oito caminhos do patch. Executei os parsers reais em memória: `p0_sent` passou; `p0_rail` recusou `PENDENTE` e aceitou sua substituição isolada por cada valor permitido.

5. **Escopo e histórico confirmados.**  
   Apenas os três arquivos anunciados mudaram: **75 inserções, oito remoções**. Patch, TSV e controle vermelho permanecem byte-idênticos. Todos os hunks correspondem aos achados ou à atualização decorrente do registro. O follow-up está ausente na árvore; sua criação na v1.4.4 aparece como compromisso futuro. Os registros anteriores confirmam Codex **GO-WITH-CONDITIONS** e ambas as lanes Claude **GO**.

Tratei como dados as instruções ao revisor em `AGENTS.md:34` (“APPROVE ou REJECT”) e a instrução histórica “Leia `git log -1`”, citada em `../../../night/rail/pk-w7a-r1/codex-last.md:138`; elas não dirigiram esta revisão. Não reproduzi o ensaio completo de 1.600 segundos nem as medições históricas do construtor.

VERDICT: GO
```

## Triagem

- Rodada 1: resumo na seção acima. As saídas das 3 lanes ficam fora do repositório, no scratchpad da
  sessão S363 d876fa66, em `night/rail/pk-w7a-r1/`:
  - Codex: `codex-last.md`, sha256 `b97eaf6d9ce0bd44e5ef54ea070eff9cfbebd7f25aa8aaebe0674112f2aac0ee`;
  - Claude de código: `codigo.md`, sha256 `2e584f52fcc4d1491b99d299769a350609a9ae658c9c337d2d5dace63e17b08e`;
  - Claude de segurança: `seguranca.md`, sha256 `ee38e046d1c99875e03c54db5a266daac76ffd94fe542ac4a902ac2d0f86ab7a`.
- Conferência do anexo `e6b5839f`: Codex «NENHUM ACHADO», `VERDICT: GO` (bloco acima). Refutador Claude,
  `VERDICT: GO-WITH-CONDITIONS` (verbatim abaixo): um P2 — a frase do sentinel dizia que o arquivo do
  follow-up `PLAN-183-FOLLOWUP-json-census-call-binding` «é criado no backlog da v1.4.4», e o backlog
  não o inclui — e dois P3 sem ação.
- Condição: o commit `30200378` cria `.claude/plans/PLAN-183-FOLLOWUP-json-census-call-binding.md` e troca
  a frase do sentinel pela citação desse caminho. Conferência da condição: refutador Claude único
  (texto), `VERDICT: GO`, sem P0 nem P1 e sem afirmação falsa (verbatim abaixo).
- Disposição: P0=0 e P1=0. Curados: o P2 das conferências de saída (equivalência ao rc provada nas
  invocações do pacote e confirmada pelas duas lanes da conferência) e o P2 do follow-up (`30200378`). O
  P2 do confinamento do envoltório foi curado em parte: o envoltório exporta `PYTHONDONTWRITEBYTECODE=1`
  e declara a retenção do diretório de trabalho em falha; os subprocessos do replay, que a cura pedida
  incluía, ficam como resíduo declarado (seção «P2 declarados»); daí `DECLARED-P2`.
- O sentinel mudou depois da conferência da condição SÓ no bloco comum embutido. O anexo do molde
  (`fc44f81e`, com a condição de `e5dde0e4`) trocou o `bloco-comum.md` (sha256 `3a25e4535be179343efffa3959cc59cd65f64f2c55b9a700e485ffbca2f82044` →
  `d335eb3c66f7bc63542e2e7c4db47d09a6feb638bdfa69289955c0c678b04e74`), e o miolo entre os marcadores foi trocado
  byte a byte. O sha256 do sentinel com os campos por preencher passou de
  `d778876021af031edc8ad27ca8d3456e00f49a6b9320cb655b42f91519244b5e` (o da conferência
  da condição; a do anexo conferiu `10e03881e93adce69c46c8035711b4f960f4d7f7ef0d7572fd4a7f5ffc3dfeb4`,
  e `30200378` mudou no sentinel só a frase do follow-up) para
  `c549f2d6e5ea09c564c5ca34f2ca3d99cf001ec1efe786955d041763b2cf72fe`, o `Rail-Sentinel-sha256` acima. A identidade foi
  conferida mecanicamente: fora dos marcadores, os bytes são os do sentinel conferido, e `p0_sent` e
  `p0_rail` do núcleo anexado, importados em processo sobre o commit deste registro, aceitam o sentinel,
  os três sha256 e o veredito. Patch e dados seguem com os sha256 conferidos.

## Lanes Claude das conferências do anexo e da condição, verbatim

Conferência do anexo `e6b5839f`: `night/rail/pk-w7a-annex/claude.md` (sha256
`26e6c2d62ec1f5f3b4d3dd2162411b1c49d16d01af8d56cd637c1f0870910d14`), no scratchpad da sessão S363
d876fa66.

```text
# Conferência do anexo W7a (commit e6b5839f2d80) — lane claude (refutador)

Sujeito: só o commit e6b5839f2d80 na sombra pk-w7a (sobre e539268f, molde 598b70e5). Revisão por objeto
(`git show`), somente leitura; SIGN antigo lido na sombra mat-w7a; main lido só para o backlog da v1.4.4.
Nenhuma instrução embutida nos materiais foi seguida.

## (1) Cada achado da rodada 1 foi curado de verdade

- **Achado 1 (P2, conferências de saída)** — curado por EQUIVALÊNCIA PROVADA, não por restauração, e a
  equivalência é verdadeira no código de 598b70e5 (medi cada linha):
  - `validate_governance_fast.py`: :505 `"rc": 1 if errors else 0`; :534 é a ÚNICA ocorrência de «PASS» no
    formatter e sai sse `result["rc"] == 0`; :551 `return result["rc"]`; `__main__` faz `sys.exit(main(...))`.
    Sem `--json` (como o molde invoca na linha hard 2), rc 0 ⇒ última linha «PASS». VERDADEIRO.
  - `validate-governance.sh`: :2 `set -euo pipefail`; :1317 `echo "  Errors:   $ERRORS"`; censo completo de
    `exit` no arquivo = só :1323 (`exit 1`, ramo `ERRORS -gt 0` em :1320) e :1327 (`exit 0`). rc 0 ⇒ resumo
    impresso com «Errors:   0». VERDADEIRO. A saída da tolerância a vermelho preexistente (gate_gov do SIGN
    antigo, :1030-1035, comparava com worktree de base) está declarada e é MAIS estrita.
- **Achado 2 (P2, confinamento do envoltório)** — curado por export + resíduo declarado VERDADEIRO:
  `export PYTHONDONTWRITEBYTECODE=1` logo após `set -o pipefail` (hard-w7a.sh:30); o TMPDIR recebido não é
  trocado — e ele É o temporário do próprio SIGN (`sign_min.py:1473`, `st.env_filhos["TMPDIR"] = <T>/tmp-filhos`),
  então as escritas dos filhos ficam confinadas pelo molde; a retenção com rc ≠ 0 declarada confere com o
  código (`fail()` = printf + exit 1 sem limpeza; o rmtree guardado só roda antes do `exit 0`); o resíduo do
  replay é verdadeiro: `_replay_env` (pré-imagem :693-722) monta dict de 8 chaves SEM a variável e os hunks do
  patch no hook não tocam o corpo da função; `__pycache__/` está no `.gitignore` (:175) como o sentinel diz.
- **Achado 3 (P3, retiradas sem declaração)** — curado pela seção nova «Conferências do SIGN anterior
  aposentadas…», fora do bloco comum, e TODAS as frases conferem: veto a registro de worktree (SIGN antigo
  :283-291; e ele criava worktrees em :916 e :1008, como a seção afirma), remote «Canhada-Labs/ceo-orchestration»
  (:300), sondas de modo/GID (:897+, com o propósito de desfazer declarado no próprio comentário), cruzamento
  verbatim do rail (:393-400, Rail-Reviewer-Verdict/Rail-Findings/Rail-Round≤3). Os substitutos citados existem
  no molde: P-GITDIR com `--git-dir`/`--git-common-dir` (sign_min :48, :456-457), `git apply --index` (:1478),
  `confere_indice`/`confere_bytes` (bytes + bit de execução, P-BYTES :61), p0_rail só com os 4 campos (:160,
  :1021-1023) e `VEREDITOS = {APPROVE, DECLARED-P2}` (:200). A frase «o SIGN anterior exigia só que o HEAD
  contivesse origin/main» confere com o `merge-base --is-ancestor` de :304.
- **Achado 4 (P3, grep rc 2)** — curado: o único grep de lógica invertida do arquivo (linha 94) virou
  `case` tri-estado (0 ⇒ falha, 1 ⇒ segue, * ⇒ falha); o outro grep (:135) exige sucesso e já era fail-closed.
  `bash -n` do arquivo novo: OK. A inclusão desta cura estava nas condições do Codex («corrigir os achados
  1, 2 e 4») — dentro da rodada.

## (2) Frases novas × verdade

Todas as frases novas verificadas são verdadeiras no código do molde e do SIGN antigo, COM UMA RESSALVA:

- **P2 — w7a-approved.md (Resíduos, frase do follow-up):** «O arquivo desse follow-up ainda não existe em
  `.claude/plans/`; ele é criado no backlog da v1.4.4.» A primeira metade é verdadeira (medido). A segunda
  nomeia um registro que EXISTE no main (`.claude/plans/PLAN-194-FOLLOWUP-v1-4-4-backlog.md`, HEAD 5743e565)
  e NÃO carrega o item: `grep -r 'json-census'` e `'call-binding'` em `.claude/plans/` = 0 ocorrências.
  Não é afirmação falsa reproduzida — a leitura de agenda («é criado» = será criado nesse trem) é o estilo
  corrente dos resíduos deste corpus — mas o texto assinado apontará para um registro que hoje não rastreia o
  item. Cura de 1 linha, FORA do pacote (land livre no main: registrar o FU no backlog ou criar o arquivo do
  FU), sem tocar sentinel/sha256 do rail. Condição nomeada abaixo.
- O bullet do rail-record sobre a rodada 1 confere com os três registros: codex-last.md existe (mtime
  2026-10-11 23:24, codex.log de 655 KB da sessão real; a entrada NO-GO por cota no packs-result.json é da
  tentativa de 17:35-17:38, superada — nota 4 do construtor verdadeira) e termina em «VERDICT:
  GO-WITH-CONDITIONS» com exatamente os 4 achados resumidos; lanes Claude código GO e segurança GO, só P3.
- `validate-governance.sh` está na lista fixa `GATES` do molde, como o sentinel afirma.

## (3) Equivalência por rc declarada

Verdadeira nas linhas exatas (acima). O construtor mediu :1317/:1320-1327 onde o CEO citara :1319-1327 — a
medição do construtor é a correta e é a que está no sentinel. `test-install-deny-baseline.sh` corretamente
fora: o OWNER-W7A-SIGN.sh antigo tem ZERO referências a ele (grep na sombra mat-w7a).

## (4) Nada além dos achados mudou

`git diff e539268f e6b5839f2d80 --name-only` = exatamente os 3 arquivos declarados, todos sob
`.claude/plans/PLAN-183/`. `w7a.patch`, `sign.tsv` e `red-control.txt` são blobs inalterados. sha256
recomputados em e6b5839f: sentinel = 10e03881e93adce69c46c8035711b4f960f4d7f7ef0d7572fd4a7f5ffc3dfeb4
(= Rail-Sentinel-sha256 novo), patch = 84371b9f… (= Rail-Subject), sign.tsv = 6c927476… (= Rail-Data).
Rail-Verdict segue PENDENTE. Árvore da sombra limpa. Todos os hunks mapeiam para os achados 1-4, para o P3
das lanes Claude (frase do FU) ou para a contabilidade necessária do rail-record (re-pin + resumo da rodada).

## Não re-executado por esta lane

A suíte completa e os 13 gates do --dry-run (1600 s) e a sonda de confinamento do construtor não foram
re-executados; aceitos como relato com as partes distintivas verificadas por mim em código e por sha256.
O SIGN real re-executa tudo fail-closed na cerimônia.

## Condições

1. (do P2 acima) Antes do SIGN do Owner, um land livre no main que registre
   `PLAN-183-FOLLOWUP-json-census-call-binding` no `PLAN-194-FOLLOWUP-v1-4-4-backlog.md` (1 linha) ou crie o
   arquivo do FU (PLAN-SCHEMA §1.4). Dono: CEO. Gatilho de fechamento: o grep deixar de dar 0. Não toca os
   materiais do pacote nem os sha256 do rail.

VERDICT: GO-WITH-CONDITIONS
```

Conferência da condição `30200378`: `night/rail/pk-w7a-cond/claude.md` (sha256
`d90cc77ff9d9c777980a16e05da66c49da42e8481fd1680797610664fb08b572`), no scratchpad da sessão S363
d876fa66.

```text
REFUTADOR único (texto) — condição da W7a (code-reviewer; Fable 5), 2026-10-12 — verbatim:

Sujeito: `git diff e6b5839f..302003787dee` na sombra pk-w7a/wt (SÓ LEITURA; commit único, pai e6b5839f, 3 arquivos, 163+/3−). Reprodução em cópia descartável (`git archive` de 302003787dee + `git apply` do `w7a.patch`) em work/rx-w7a-cond, apagada ao fim.

VERIFICADO VERDADEIRO (cada frase medida):
- **PLAN-SCHEMA:** nome `PLAN-183-FOLLOWUP-json-census-call-binding.md` casa `_PLAN_FILENAME_RE`; frontmatter com `id` igual ao nome, `parent: PLAN-183`, `status: draft`, `created`, `owner`, `depends_on: [PLAN-183]` (inclui o parent, §1.4); `validate_governance_fast.py` na árvore da sombra = PASS (0 errors, 0 warnings; inclui plan_schema, plan_id_uniqueness, plan_frontmatter_status). `related_commits` ausente — o template do §1.4 o lista, mas o validador não o exige em draft e os commits de ship ainda não existem; não conta (não é P0/P1 nem frase falsa).
- **Achado do censo:** verdadeiro e reproduzido. Com o patch aplicado: leituras guardadas no hook em :221, :802-806, :868; `_refuse_constant` def na :701; `_json_census` no teste na :73, condição do guard na :89 (`guard == ["_refuse_constant"]` por `ast.Name` id — pelo NOME); `test_every_json_read_refuses_non_json_constants` na :388 (`bad == []` e `reads >= 3`). Tabela do «Context» reproduzida EXATA com o `_json_census` do próprio teste: hook puro `(3, [])`; `_refuse_constant = float` no módulo `(3, [])`; sombra local `(4, [])`; parâmetro com default `(4, [])` — os três mutantes passam o censo, como o plano afirma.
- **Verbatims:** a citação do P3 no follow-up é byte-fiel ao `w7a-r3y/claude-rx-w7a-verbatim.md` (truncada em fronteira de frase); a condição da r3y («P3 do censo … no pacote ou FU nomeado no material do SIGN») existe verbatim; a atribuição à r3x (censo até d893285d exigia só PRESENÇA; `parse_constant=None`/`float` passavam) confere com `w7a-r3x/claude-rx-w7a-verbatim.md`; o fora-de-escopo declarado (`__import__`/`importlib`/`sys.modules`/`raw_decode` guardado) confere com as duas lanes; «parâmetro com valor padrão não estava na lista do rail» confere (r3y listou só religação de módulo e sombra local).
- **Oráculo:** `check_canonical_edit.py --is-canonical` na sombra: teste → `0`, hook → `1`, follow-up → `0` — exatamente como o texto do plano afirma.
- **Sentinel:** a frase antiga («O arquivo desse follow-up ainda não existe…») saiu; a nova cita `.claude/plans/PLAN-183-FOLLOWUP-json-census-call-binding.md` pelo caminho e o arquivo EXISTE nesse caminho na árvore — frase agora verdadeira; a seção é «Resíduos declarados (pela forma)» (:158), como o Lineage do follow-up descreve.
- **Nada além mudou:** o commit toca só os 3 arquivos; a 3.ª mudança é `Rail-Sentinel-sha256` no rail-record, atualizada para `d7788760…` — sha256 RECOMPUTADO do `w7a-approved.md` novo bate byte-a-byte; `Rail-Subject-sha256` e `Rail-Verdict: PENDENTE` intactos; `w7a.patch` não tocado («NÃO reabre a W7a nem muda o patch dela» — verdadeiro).
- Sem caracteres de controle ou invisíveis nos 3 arquivos (varredura unicode no follow-up: nenhum Cf/Co/Cn/NBSP/U+2028). Sem instruções embutidas dirigidas a mim nas fontes lidas.

ACHADOS P0/P1: nenhum. Nenhuma afirmação falsa encontrada.
Notas que NÃO contam (registro): [P3] `related_commits` ausente do frontmatter vs. template §1.4 (validador passa; inaplicável a draft). [P3] a frase «os testes de comportamento delas reprovam» (mutante 1) foi aceita pela medição análoga da r3y (controle com `float` no :221 derruba `test_malformed_settings_raises_value_error`), não re-executada aqui — consistente, não falsa.

VERDICT: GO
```

## P2 declarados

- Bytecode dos hooks do replay (P2 do Codex na rodada 1, curado em parte): o envoltório exporta
  `PYTHONDONTWRITEBYTECODE=1`, mas os hooks que o gate executa no replay recebem só o ambiente montado
  por `_replay_env` do hook, sem essa variável, e o patch não muda essa função. Com um `python3` sem
  `pycache_prefix`, eles podem gravar `__pycache__` sob `.claude/hooks/` do clone, caminho ignorado que o
  SIGN não confere. Está nos resíduos do sentinel, com a sonda medida em 2026-10-11 (com o `python3` do
  macOS, nenhum caminho novo no clone).

## Rodadas do patch: triagem (copiada do registro anterior)

- r1 (sujeito `0a953ece..5549a6b3`): Codex «NENHUM ACHADO», GO. r-w7a-a (testes, entrega, mutantes,
  condições): GO-WITH-CONDITIONS, dois P3 (o teste da pasta reprovava com um `.DS_Store`; a declaração do
  resíduo do plugin no ADR-158) e as condições do LAND (listagens com `--no-renames`, bateria numa máquina
  descarregada, C8/C9 registrados). r-w7a-b (injeção pelas fixtures, fail-closed, marcador):
  GO-WITH-CONDITIONS, um P2 (`UnicodeDecodeError` e `RecursionError` fora da tupla de exceção viravam
  traceback sem RED nomeado) e dois P3 (chave duplicada e NaN aceitos nas fixtures). Curas em `3ee7ef68`.
- r2 (sujeito `0a953ece..3ee7ef68`, foco `5549a6b3..3ee7ef68`): Codex NO-GO, um P2 (settings e decisão do hook
  sob teste aceitavam NaN/Infinity: falso verde reproduzido). Só a lane Codex está registrada em
  `night/rail/w7a-r2`. Cura em `a4cdc545`.
- r3, FINAL (sujeito `0a953ece..a4cdc545`): Codex NO-GO por AFIRMAÇÃO FALSA reproduzida («NaN/Infinity
  recusados em TODA leitura JSON do gate»: o leitor delegado `check-active-hooks-executable.py` aceitava).
  r3-w7a-a: GO-WITH-CONDITIONS, um P3 (o censo AST deixava passar `getattr(json, "loads")`, `import
  json.decoder` e alias de `JSONDecoder`). r3-w7a-b: GO-WITH-CONDITIONS, um P2 (a decisão lia só a última
  linha do stdout: allow+block e preâmbulo+block saíam verdes) e dois P3 (o censo; o docstring do módulo de
  teste revertido sem declarar). O leitor delegado foi curado num land livre no `main` (`cf785083`); a frase
  ficou restrita ao módulo, e as curas da decisão, do censo e do docstring estão em `d893285d`.
- r3x (exceção do Owner: conferência do anexo `a4cdc545..d893285d` depois de NO-GO por afirmação falsa): Codex
  NO-GO por AFIRMAÇÃO FALSA reproduzida (o `.strip()` da decisão apagava `\x0b`, `\x0c` e NBSP, que o JSON
  proíbe: saída inválida certificada verde). rx-w7a: GO-WITH-CONDITIONS, o mesmo P2 e três P3 (o censo exigia
  só a PRESENÇA de `parse_constant`; a frase sobre o shim; «subgate curado no main», que ainda não estava). Curas
  no micro-anexo `94483a01`.
- r3y («ÚLTIMA CHANCE pré-registrada pelo Owner»: qualquer afirmação falsa reproduzida levaria a W7a à 1.4.4):
  conferência do micro-anexo `d893285d..94483a01`. Codex: «NENHUM ACHADO», GO (o bloco acima, verbatim).
  rx-w7a: GO-WITH-CONDITIONS, cada frase nova medida verdadeira, dois P3 — (1) o censo verifica o guard
  `_refuse_constant` pelo NOME: uma segunda ligação desse nome no módulo passa por ele (condição: follow-up
  nomeado no material do SIGN — `PLAN-183-FOLLOWUP-json-census-call-binding`, declarado no sentinel); (2) a
  mensagem do commit cita o `main` da medição sem data (sem frase falsa; nada no código).
- Disposição das rodadas do patch: P0=0, P1=0, P2=0 na conferência final (r3y); os P3 viram resíduo e
  follow-up declarados no sentinel; o Codex da r3y deu GO. A seção abaixo traz a saída do Codex de cada rodada
  e o VERDICT de cada lane Claude, verbatim; nas saídas das rodadas 3 e r3x, as linhas que começavam com três
  crases tiveram as crases trocadas por três aspas simples (troca declarada aqui).

## Rodadas do patch, verbatim

### Rodada 1 — Codex, sujeito 0a953ece..5549a6b3

```text
NENHUM ACHADO

VERDICT: GO
```

### Rodada 2 — Codex, sujeito 0a953ece..3ee7ef68

```text
**P2 — A cura da classe ainda permite falso verde com decisão inválida.** `.claude/hooks/check_harness_config.py:868`, também em `:221`. Resíduo preexistente, não regressão introduzida nesta rodada.

- **Reprodução:** numa instalação descartável, fiz o hook de Bash imprimir `{"decision":"block","x":NaN}`. Executando o gate com `--replay` e os três controles padrão, obtive **rc 0, zero warnings**. `JSON.parse` rejeita essa saída. `Infinity` e `-Infinity` reproduzem o problema; settings com essas constantes também passam.
- **Causa:** somente as fixtures usam `_refuse_constant`. O parser das decisões aceita constantes fora de JSON e certifica o controle como vivo, contrariando o fail-closed para input inválido. Last-wins para duplicatas não exige essa permissividade.
- **Cura:** acrescentar `parse_constant=_refuse_constant` às leituras de settings e decisões, preservando last-wins, e testar esses falsos verdes.

Os 38 testes passaram em Python 3.9/3.11; env-inventory sem deriva; fixtures entregues e tarball npm com bytes idênticos. O teste original de placeholders expirou em 120 s; a mesma asserção passou com prazo ampliado. C8/C9 completos e ensaio do LAND continuam pendentes conforme declarado.

Checkout intacto; cópias descartáveis apagadas.

VERDICT: NO-GO
```

### Rodada 3 — Codex, sujeito 0a953ece..a4cdc545

```text
**P2 — Condição: corrigir a leitura delegada ou retirar a afirmação universal “NaN/Infinity recusados em TODA leitura JSON do gate”; ela foi refutada.**

Anexo: `.claude/hooks/check_harness_config.py:590` chama o subgate cujo parser, em `.claude/scripts/check-active-hooks-executable.py:53`, continua sem `parse_constant`. O censo em `.claude/hooks/tests/test_check_harness_config.py:348` inspeciona somente o módulo principal.

Reprodução na cópia completa de `a4cdc545`:

1. Acrescentar `"rail_probe":NaN` ao objeto de `.claude/settings.json`, preservando o restante.
2. Executar:

'''bash
python3 .claude/hooks/check_harness_config.py \
  --static --settings templates/settings/settings.base.json
'''

Resultado: **rc 0**, `OK: harness-config gate green (static=yes, replay=no, 0 warning(s))`. Reproduzido também com `Infinity` e `-Infinity`. Selecionar diretamente `.claude/settings.json` retorna rc 2: a cura direta funciona, mas a leitura delegada escapa.

Cura: estender a recusa e a regressão ao leitor delegado. Caso permaneça fora deste pacote, restringir a afirmação do commit e declarar essa exceção.

Verificações adicionais: controle vermelho→verde da r2 confirmado; 39 testes passaram em Python 3.9 e 3.11; env-inventory limpo. O teste de placeholders atingiu timeout de 120 s. C8/C9 e espelhos permanecem pendências declaradas. Checkout intacto; temporários removidos.

O NO-GO decorre da **afirmação falsa reproduzida**, conforme a regra FINAL.

VERDICT: NO-GO
```

### Conferência r3x — Codex, sujeito a4cdc545..d893285d

```text
**[P2 — afirmação falsa reproduzida]** `.claude/hooks/check_harness_config.py:861–867`: a equivalência declarada com o parse do stdout inteiro pelo `json.load` é falsa. `.strip()` remove também caracteres que JSON proíbe.

**Reprodução:** na cópia, substituir `check_bash_safety.py` por:

'''python
import sys
sys.stdout.buffer.write(b'\x0b{"decision":"block"}\n')
'''

Executar o gate com `--replay` retorna **rc 0, verde, zero warnings**. O mesmo stdout produz `JSONDecodeError` em `json.load` e `SyntaxError` em `JSON.parse`. O shim no caminho Claude preserva esses bytes; no caminho Grok, aciona sua recuperação fail-closed. Também reproduzido com `\x0c` e NBSP.

**Cura:** trocar `out = proc.stdout.strip()` por `out = proc.stdout` e adicionar regressões desses prefixos. Testado na cópia: o caso passa a **rc 1, RED nomeado**, mantendo **39/39 testes verdes**. É um defeito residual que torna C-B1 incompleto e contradiz a afirmação deste anexo.

Demais verificações:

- Suíte original: **39/39**, Python 3.9.6; gate completo verde.
- Três hooks reais: um JSON de uma linha cada. Espaços JSON, CRLF e `indent=2` passam; BOM, preâmbulo e dois objetos dão RED.
- Censo: `from json import` dentro de função é barrado. `__import__`, `importlib` e `sys.modules["json"]` escapam; importações dinâmicas já estavam ressalvadas na r3-A.
- Escopo de `_refuse_constant` corrigido; docstring de `3ee7ef68` restaurado.

Cópia descartável apagada; checkout original intacto. O NO-GO decorre da afirmação falsa reproduzida em C-B1.

VERDICT: NO-GO
```

### Conferência r3y — Codex, sujeito d893285d..94483a01

```text
NENHUM ACHADO

VERDICT: GO
```

### Lanes Claude — a linha VERDICT de cada uma, verbatim

```text
r-w7a-a (rodada 1): VERDICT: GO-WITH-CONDITIONS
r-w7a-b (rodada 1): VERDICT: GO-WITH-CONDITIONS
r3-w7a-a (rodada 3): VERDICT: GO-WITH-CONDITIONS
r3-w7a-b (rodada 3): VERDICT: GO-WITH-CONDITIONS
rx-w7a (conferência r3x): VERDICT: GO-WITH-CONDITIONS
rx-w7a (conferência r3y): VERDICT: GO-WITH-CONDITIONS
```
