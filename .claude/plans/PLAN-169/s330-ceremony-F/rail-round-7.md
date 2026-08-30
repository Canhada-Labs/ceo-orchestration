# Pacote F — rail codex rodada 7 (shadow-F curada da r6, 2026-08-30 ~18:46 -03)

Rail-Verdict: CHANGES-REQUESTED (0 P1, 2 P2 — um curado, **um é decisão do Owner**)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh`. Modelo `gpt-5.6-sol`, esforço xhigh. Saída bruta:
`<scratchpad efd20343>/rail/r7.txt`. Wrapper: **TREE INTACT**.

## 🔴 DECISÃO PENDENTE DO OWNER — o pacote não é assinável sem ela

**[P2-a] O guard do scratchpad casa por SUFIXO, e a wave o liga para o adopter.**
`templates/settings/settings.user.json:283`.

O revisor levantou `check_scratchpad_access.py` na rodada 2 e voltou a ele agora,
com um argumento mais forte — e ele está certo:

* `_tokens_target_scratchpad()` aceita **qualquer caminho** que termine em
  `scratchpad.py` (`check_scratchpad_access.py:96-120`; o comentário do módulo
  diz que a folga é deliberada, «para as fixtures de teste viverem em qualquer
  caminho absoluto»);
* logo, um adopter `--ceremony user` com plano resolvível que rode
  `python3 /qualquer/lugar/scratchpad.py --plan PLAN-999` **leva bloqueio** de um
  guard que existe para proteger o CLI do framework;
* a cura da rodada 6 (empacotar o `scratchpad.py` no plugin) fecha a
  incoerência «guard sem sujeito», mas **não estreita o matcher** — o falso
  positivo continua.

E ele bate no critério que o próprio spec declara: *fica de fora todo hook que
bloqueia uma chamada de ferramenta **sem deixar ao adopter uma rota praticável***.
Para o CLI do framework existe rota (rodar sem `--plan`, impressa na própria
mensagem). Para um script alheio homônimo **não existe rota nenhuma** — o
adopter não tem como saber por que foi bloqueado.

**As duas saídas honestas, e por que eu não escolhi sozinho:**

| opção | o que muda | custo |
|---|---|---|
| **(a) EXCLUIR** `check_scratchpad_access.py` do perfil user | uma linha no `_derivation.exclude_hooks` (classe `M`, razão = falso positivo sem rota) + a entrada sai de `blocking_inclusions`; roster **30 → 29** | reverte um veredito «INCLUIR por mérito» que a classificação S330 produziu e que a OQ-E5 ratificou |
| **(b) ESTREITAR o matcher** no `check_scratchpad_access.py` | o guard passa a casar só o caminho do CLI do framework/plugin | acrescenta um arquivo **fora** do FILE ASSIGNMENT desta wave, e o hook tem testes próprios que assumem a folga de caminho |

**Recomendação: (a).** O critério da wave é o que decide, e ele é explícito
sobre «rota praticável». A classificação chegou ao «INCLUIR» pelo critério
ANTIGO («bloqueia edição ou exige GPG/sentinel»), que o próprio documento
substituiu — é a mesma defasagem entre lista e regra que a rodada 2 achou, um
nível abaixo. (b) é defensável, mas alarga o escopo de uma cerimônia já grande
na última hora.

Isto **não** foi executado: mudar um veredito ratificado é chamada do Owner.

## Achado curado

- **[P2-b] Alvo malformado sob `--check --spec` não respeitava o contrato de
  exit** — `gen-settings-user-template.py:1214`. Com `--spec`, o `read_spec()`
  não parseia o TARGET, então essa é a primeira leitura dele: UTF-8 inválido
  escapava como traceback, e JSON inválido era reportado como **DRIFT** —
  nomeando o problema errado e mandando o leitor ao `--write` em vez de à
  corrupção. **REAL, curado:** os dois saem `RC_INFRA == 2` com mensagem
  nomeando o arquivo. Guard novo com controle nas duas formas.

Bateria **266 → 267**.

## Disposição

O pacote está completo e verificado **exceto por uma decisão**. O SIGN exige
`Rail-Verdict: APPROVE` no último registro, então ele **recusa** este pacote por
desenho — corretamente. Depois da decisão do Owner: aplicar (a) ou (b), rodar
uma rodada final, e só então o pacote fica assinável.
