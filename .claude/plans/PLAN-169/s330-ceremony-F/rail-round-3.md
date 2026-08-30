# Pacote F — rail codex rodada 3 (shadow-F curada da r2, 2026-08-30 ~14:44 -03)

Rail-Verdict: CHANGES-REQUESTED (1 P1 + 4 P2, os cinco reais, os cinco curados)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh`. Modelo `gpt-5.6-sol`, esforço xhigh. Saída bruta:
`<scratchpad efd20343>/rail/r3.txt`. Wrapper: **TREE INTACT**.

## Achados

- **[P1] `--write` alcançável com um `--spec` EXTERNO** —
  `gen-settings-user-template.py:960-962`. `check_canonical_edit` é registrado
  para `Edit|Write|MultiEdit`, **não para `Bash`**, então um gerador invocado
  pelo shell escrevendo num path canônico não é visto por ele. **REAL.**
- **[P2-a] Campos comportamentais em `annotation_overrides`** — `:546-550`. Só
  `command` era recusado; `timeout`, `type` e `prompt` passavam. `timeout` **é**
  comportamento. **REAL.**
- **[P2-b] Chaves top-level desconhecidas** — `:342-344`. Um typo
  (`env_override`) era aceito, round-tripped para `_derivation`, e então
  IGNORADO — a derivação usava o default correto e o `--check` ficava verde.
  **REAL.**
- **[P2-c] Escopo de evento no oráculo de install** —
  `test_install_user_skips_governance_hooks.py:75-78`. O helper descartava
  `event` e ignorava o bucket pendente. **REAL, latente** (o spec vivo tem 0
  exclusões qualificadas) — e latente é a razão de curar agora.
- **[P2-d] Exclusões sobrepostas** — `:368-375`. Uma exclusão nua mais uma
  qualificada para o MESMO hook passavam, porque as chaves de tupla diferem.
  **REAL.**

## Curas

**P1 — o que é desta wave, e o que não é.** A CLASSE precede a wave:
`generate-adr-index.py --write` reescreve o canônico `.claude/adr/README.md`
exatamente do mesmo jeito, e `build-plugin.py --write-manifests` também. Curar
um de três seria teatro. O que a wave INTRODUZIU foi o `--spec <path>`: uma rota
para um documento **não-revisado, fora da árvore**, dirigir aquela escrita. Essa
rota fecha — `--write` recusa spec de fora do repositório, com **rc 1** (recusa
de POLÍTICA), nunca rc 2 (INFRA). `--check` com spec externo segue permitido:
ler uma proposta e reportar o diff não escreve nada. O residual fica **declarado**.

**P2-a/P2-b/P2-d** — vocabulários fechados: `ANNOTATION_FIELDS`
(`statusMessage`, `_comment`), `SPEC_KEYS` (16 chaves), e detecção de
sobreposição nua↔qualificada nos DOIS buckets.

**P2-c** — o helper passa a devolver `(bare, scoped)`, lê o bucket pendente, e o
teste afirma por evento: o registro excluído some daquele evento **e os outros
sobrevivem** (asserção positiva — sem ela, um gerador que derrubasse ambos
passaria nessa metade). O parsing virou função pura para que o ramo scoped, que
o spec real ainda não alcança, seja exercitável.

## O incidente: o controle vermelho corrompeu o artefato

Registrado porque a lição é maior que o susto.

A primeira versão de `WriteRefusesAnOutOfTreeSpec` invocava `--write` contra o
**repositório real**. Ela era segura *apenas porque a cura que ela testa estava
presente*. No instante em que o controle vermelho removeu essa cura — para
provar que o teste sabia falhar — a escrita passou e **reescreveu o
`settings.user.json` shipado** com o `_minimal_spec()` do teste: 47 registros,
`criterion` = "test fixture criterion", zero exclusões. E o `--check` ficava
**rc 0**, porque o arquivo batia com o spec falso que ele mesmo passou a
carregar.

Recuperado do `F-wip.patch` commitado (o snapshot do writer), com as curas de
spec re-aplicadas e verificação byte a byte: 30 registros, 17 exclusões, 5
`blocking_inclusions`, 38.178 B.

**A cura é estrutural, não um cuidado:** os testes de `--write` rodam contra uma
árvore SINTÉTICA (`_synth_root`), com o spec deliberadamente fora dela; ganharam
um controle positivo (spec DENTRO da árvore ⇒ escreve, rc 0) e a asserção de que
o arquivo **não existe** após a recusa — a recusa acontece antes de qualquer
escrita. E o controle vermelho foi **refeito**, agora comparando o sha256 do
template antes e depois: **byte-idêntico**.

Regra que fica: *um teste cuja segurança depende do código que ele testa não é
um teste.* Qualquer caso que invoque um caminho de ESCRITA roda em árvore
descartável, sempre.

## Verificação

- 13 testes novos (`SpecVocabulariesAreClosed` 7, `WriteRefusesAnOutOfTreeSpec` 3,
  `TestExclusionParsingKeepsTheEvent` 4 — no arquivo de install).
- **Controle vermelho** com o gerador pré-r3: **5 de 9 vermelhos**, e o template
  **byte-idêntico** antes e depois.
- Bateria da cerimônia **239 → 252**; arquivo nuclear **87 → 98**.
- `gen --check` rc 0; ratchet rc 0; `check-claude-md-claims` rc 0; roster 30/47.
- Dois testes pré-existentes precisaram de reconciliação, não de relaxamento:
  a mensagem didática de `top_level_keep` passou a rodar ANTES do vocabulário
  fechado (quem está na grafia antiga merece a frase que explica, não um
  "unknown key"), e o teste da r1 que usava `hook.timeout` migrou para
  `statusMessage` — a propriedade sob teste é a mesma, o campo é que deixou de
  ser anotação.

## Disposição

Sombra CURADA. Rodada 4 sobre ela.
