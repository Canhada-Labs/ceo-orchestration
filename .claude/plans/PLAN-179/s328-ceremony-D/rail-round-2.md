# Pair-rail — PACOTE D (PLAN-179 W2+W4), rodada 2

**Instrumento:** `codex exec review --uncommitted` (codex-cli 0.147.0), clone
novo do HEAD `560dad0` com o pack **já curado pela rodada 1** aplicado pelo
MANIFESTO + os materiais de cerimônia.

**Resultado:** `rc=0`, veredito **REJECT** — 3 P1 + 1 P2.
Rail-Verdict: REJECT
**Artefato bruto:** `<scratchpad>/pkgD-rail-2.txt` (2.588 bytes).

Leitura honesta do movimento: 9 achados → 4. Nenhum dos 4 é reincidência da
rodada 1 — são superfícies que a rodada 1 não tocou, e **dois deles são dos
MEUS materiais de cerimônia**, não do payload. O rail cross-vendor está
fazendo exatamente o que justifica a sua existência: mudando a pergunta.

---

## P1-1 — o SIGN deixava assinar um pacote REPROVADO — **CURADO**

> `OWNER-W179-W24-SIGN.sh:191-198` — o gate só checa que existe pelo menos um
> artefato de rail. O único artefato existente é o `rail-round-1.md`, cujo
> veredito é **REJECT**, e ainda assim a assinatura era permitida. Isso
> contorna o contrato de revisão cross-LLM e a própria exigência da cerimônia
> de iterar até APPROVE.

**VERIFICADO — verdadeiro, e é o achado mais sério da rodada.** O meu gate
contava ARQUIVOS. Contar arquivos responde "houve rail?"; o contrato pergunta
"o rail FECHOU?". São perguntas diferentes, e a minha media a errada — a
classe "instrumento verde cuja pergunta envelheceu", cometida por mim, no
script cuja função é impedir precisamente esse tipo de passagem.

**CURA:** o registro de cada rodada passa a DECLARAR o veredito numa linha
`Rail-Verdict: APPROVE|REJECT|UNAVAILABLE`, e o SIGN:

1. ordena os registros pelo **número** da rodada, não pela ordem do glob
   (`rail-round-10.md` vem antes de `rail-round-9.md` em ASCII, e é a ÚLTIMA
   rodada que decide);
2. lê o veredito da última e **exige `APPROVE`**;
3. trata `REJECT` e `UNAVAILABLE` como abortos com mensagens distintas e
   acionáveis;
4. **campo ausente é ABORT**, nunca "assume que passou" — fail-closed em
   input, como manda o `CLAUDE.md §4`;
5. nome de arquivo fora do padrão `rail-round-<N>.md` também aborta, em vez
   de ser ignorado silenciosamente pelo parser.

---

## P1-2 — a raiz do repositório era o `cwd` do evento — **CURADO**

> `check_ledger_checkpoint.py:1081-1083` — quando o `cwd` segue um
> `CwdChanged` para um subdiretório, aquele diretório é tratado como raiz. O
> git continua devolvendo caminhos relativos à RAIZ, mas a varredura de ACs e
> a inspeção do ledger olham `<cwd>/.claude/plans`, e o estado de observação é
> escrito em `<cwd>/.claude/state`.

**VERIFICADO — verdadeiro, com três consequências distintas**, todas
reproduzidas: commits com escopo por AC classificados fora de escopo; um
ledger EXISTENTE reportado como ausente; e o contador de observação
fragmentado em diretórios aninhados que nem sequer são gitignored.

**CURA:** `_resolve_repo_root(start, deadline)` resolve `git rev-parse
--show-toplevel` **antes** de qualquer path ser derivado. Fail-OPEN por
desenho — este hook não é matcher de segurança, e sem git a rota `no_repo`
já reporta a situação honestamente.

**CONTROLE POSITIVO (provado vermelho→verde), 2 testes:**

```
AssertionError: 'ledger_absent_from_plan' != 'ledger_missing'
AssertionError: True is not false : observation state fragmented into a nested directory
```

O primeiro é a **assinatura exata do defeito**: `ledger_absent_from_plan` é o
que se obtém quando a busca aconteceu sob o subdiretório;
`ledger_missing` (encontrado, não atualizado) é o valor correto. O teste
discrimina entre os dois em vez de só exigir "não vazio".

---

## P2 — commits prefixados por ambiente sumiam — **CURADO**

> `check_ledger_checkpoint.py:452-455` — em `GIT_EDITOR=true git commit -m x`
> ou `env FOO=1 git commit -m x`, o token de atribuição/wrapper limpa
> `at_command_position` e o `git` seguinte nunca é reconhecido. O commit não
> recebe advisory NEM evento de skip: sai do universo observado.

**VERIFICADO — verdadeiro, e a gravidade é maior do que P2 sugere.** Este rail
tem uma invariante declarada: *"Omissão é uma medição, não silêncio"* — todo
commit não-advertido emite um `ledger_checkpoint_skipped` com razão de enum
fechado. Um commit prefixado por ambiente violava a invariante: silêncio
total. E `GIT_EDITOR=true git commit` é forma de shell absolutamente comum.

**CURA:** a posição de comando sobrevive a atribuições `NAME=value`
(`_ENV_ASSIGN_RE`) e a wrappers finos (`_CMD_WRAPPERS = {env, command,
nohup, stdbuf}`). O conjunto de wrappers é deliberadamente CURTO e o
comentário diz por quê: `sudo`/`xargs` ficam de fora porque alargar o
conjunto troca um falso negativo por um falso positivo, e o rail é advisory
nos dois casos.

**CONTROLE POSITIVO (provado vermelho→verde):**

```
AssertionError: 0 != 1 : the commit vanished from the observed universe:
GIT_EDITOR=true git commit -m "feat: work"
```

Mais um **controle na direção oposta**: `GIT_EDITOR=true echo hello` continua
totalmente silencioso — a cura não pode transformar uma atribuição qualquer
em gatilho.

---

## P1-3 — identidade pessoal em artefatos que serão commitados — **CURADO**

> `s328-ceremony-D/README-D.md:27` — as instruções expõem um nome de usuário
> real e um caminho de checkout específico da máquina; a mesma identidade
> aparece repetidamente em `land-sim.log`. Além de publicar detalhes locais,
> os comandos copy-paste falham para qualquer checkout em outro lugar.

**VERIFICADO — verdadeiro, e é regressão minha contra uma regra explícita do
repo** (`CLAUDE.md §4`, "No contamination"). A instrução da minha tarefa dizia
"paths absolutos" para o Owner conseguir copiar e colar; eu implementei isso
da forma errada — **hardcoding** a identidade — quando o precedente do repo já
mostrava a forma certa: o `OWNER-S327b-SIGN.sh` computa `$ROOT` em tempo de
execução e IMPRIME o caminho absoluto na saída, sem nunca gravá-lo no arquivo.

Vale notar que o `check_contamination.py` **não teria pego**: a árvore de
planos inteira está isenta pelo glob `.claude/plans/*` do `_ALLOWLIST_GLOBS`
(o fnmatch atravessa `/` ali). Mais um caso de gate cuja pergunta não cobre o
sítio — o rail cobriu.

**CURA:**
- `README-D.md` ganhou um **passo zero** (`cd ~/canhada-labs/ceo-orchestration`,
  com a nota de que qualquer checkout serve) e os três comandos passaram a ser
  **relativos**. O copy-paste continua funcionando para um operador leigo, e o
  arquivo não carrega mais identidade. Os scripts resolvem a raiz sozinhos a
  partir do próprio `BASH_SOURCE` e imprimem o comando seguinte pronto.
- `land-sim.log`: 9 ocorrências de caminho pessoal substituídas por `<repo>` /
  `<home>`, e o slug path-based (`-Users-<user>-...`, que carrega o username
  com `/` → `-`) substituído por `<slug-do-clone>`. Varredura final por
  `joaocanhada` nos meus materiais: **0 ocorrências**.

---

## Resumo da rodada 2

| # | sev | superfície | disposição |
|---|---|---|---|
| P1-1 SIGN aceita rail REJECT | P1 | **cerimônia (minha)** | **curado** — contrato `Rail-Verdict:` fail-closed |
| P1-2 raiz do repo = `cwd` | P1 | payload | **curado** + 2 controles positivos |
| P1-3 identidade pessoal commitada | P1 | **cerimônia (minha)** | **curado** — paths relativos + log escovado |
| P2 commit prefixado por env some | P2 | payload | **curado** + controle positivo + controle inverso |

**4 de 4 curados.** Dois eram dos meus próprios materiais — o registro fica
como está, sem suavização: o script cuja função é impedir assinatura indevida
tinha um gate que contava arquivos em vez de ler o veredito, e o README que eu
escrevi para o Owner publicava o nome de usuário dele num repositório público.
