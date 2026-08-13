---
plan: PLAN-177
round: 1
role: VP Engineering
skill: architecture-decisions
created_at: 2026-08-13
---

# VP Engineering — round 1, PLAN-177 (rc.4)

## Verdict

**ADJUST.** Sem VETO. A arquitetura do plano está certa nas três decisões
que importam (fronteira W0/W1, escopo mínimo, gerador compartilhado). Os
seis Must-fix abaixo são pontuais e todos verificados no disco. Um deles
(MF-2) invalida uma justificativa que o plano usa como mecanismo; outro
(MF-5) inverte a ordem do W2 de um jeito que faria o próprio guard matar
a tag. Nenhum é motivo para redesenhar o plano.

## Summary

O plano acerta o corte principal: os dois validadores do P1-4 **não** são
canônicos (confirmei que `.github/scripts/validate-pair-rail-verdict.py`
e `.claude/scripts/local/_release_tag_guard.py` não aparecem em
`_CANONICAL_GUARDS`), então tratá-los como W0 livre e concentrar tudo
que é canônico num pack único é o corte de menor custo de cerimônia — a
assinatura é custo **por cerimônia**, não por arquivo.

O que o plano ainda não viu é que os **dois pontos de inserção do P1-4
não são redundantes**: eles têm perfis de falha diferentes. O step 15
carrega `continue-on-error: ${{ vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL ==
'1' }}` (`.github/workflows/release.yml:689`) — com a variável em `1`, o
gate no validador é ignorado inteiro, qualquer que seja o exit code. Quem
fecha nesse modo é o step seguinte, "Verify verdict delta + ancestry
(fail-closed)", que aborta explicitamente com
`CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` (`release.yml:786-790`) e chama
`_release_tag_guard.py delta` (`release.yml:855-856`). Ou seja: **o gate
que realmente barra é o do tag guard**; o do validador é defesa em
profundidade. Isso precisa estar escrito nos dois arquivos, senão a
próxima "simplificação" remove a cópia errada e reabre o P1-4 pela
terceira vez.

Blast radius: L2. Reversibilidade: ALTA (nenhuma decisão irreversível —
o único ponto sem volta é o `npm publish`, e todas as curas *aumentam* a
distância até ele). Regra dos 10x: o gate de decisão é O(1) sobre um
campo escalar; escala sem reescrita.

## Risks

- **R-a — crash-como-infra (fail-open real).** Em
  `validate-pair-rail-verdict.py:110-114`, uma linha `verdict:` sem valor
  vira `out["verdict"] = {}`. O gate proposto (`verdict.get("verdict",
  "").strip()`) levanta `AttributeError` sobre um dict ⇒ traceback ⇒
  exit 1 ⇒ **indistinguível de `EXIT_INFRA_ERROR`**, que é exatamente o
  código que `CEO_PAIR_RAIL_VERDICT_OPTIONAL` tolera. No tag guard,
  `_parse_verdict:219-221` mapeia o mesmo shape para `[]`. Os dois gates
  precisam de `isinstance(..., str)` **antes** do compare, com o não-str
  caindo em `VERDICT_INVALID` / `E_DECISION`, nunca em infra. Um envelope
  com `verdict:` vazio é hoje a rota mais barata para o cenário do P1-4.
- **R-b — a rc.4 vai ser cortada com um `GO`.** O caminho feliz não
  exercita o gate. Foi assim que a cura anterior do P1-4 (só no
  `OWNER-GA-CUT.sh`) sobreviveu a um re-pass inteiro. O controle positivo
  do AC-1 é o que fecha isso; ele não é "nice-to-have", é o único
  exercício do ramo vermelho que vai existir.
- **R-c — remover uma allowlist de arquivo inteiro expõe tudo o mais que
  ela mascarava** (detalhe em MF-3).
- **R-d — censo R-4 confirmado por mim:** 11 envelopes vivos, 9 com
  `verdict: GO` e 2 com `GO-WITH-CONDITIONS` (rc.2 e rc.3), campo sempre
  presente e sempre em coluna 0. O gate não quebra nenhum histórico. O
  template (`pair-rail-verdict-template.md:13`) traz
  `verdict: GO | NO-GO | GO-WITH-CONDITIONS` e é **corretamente**
  rejeitado pela igualdade exata — vale um caso de teste explícito, é o
  literal mais provável de vazar para um envelope real.

## Must-fix

**MF-1 — OQ-1: `E_DECISION = 13` novo, sim; e o assert que o plano cita
já está desatualizado.**
Decisão: **código novo**. O cabeçalho do módulo diz por que
(`_release_tag_guard.py:51-53`: "Exit codes are distinct so the failure
MODE is testable, not just the failure"). `E_VERDICT = 10` significa
"verdict unusable (missing file/field, wildcard, wrong tag, bad parent)"
(`:57`) — uma falha **estrutural**. Um `NO-GO` não é um envelope
inutilizável: é bem-formado, corretamente pinado, e diz não. As
remediações são **opostas** (re-autorar o envelope × consertar o produto
e re-revisar), e colapsar as duas num código só apaga essa diferença no
log de release. O precedente é interno e consistente: `E_VACUOUS = 11` e
`E_PARENT_NOT_ANCESTOR = 12` foram esculpidos do mesmo balde `E_VERDICT`
por essa mesma razão.
**Mas:** o assert que o plano invoca como fundamento —
`test_release_workflow_asserts.py:1001-1013` — enumera os códigos **à
mão** e já está desatualizado: a lista termina em `E_VACUOUS` e **não
contém `E_PARENT_NOT_ANCESTOR`**. Acrescentar `E_DECISION` sem consertar
isso deixa o código novo fora do assert de distinção. Cura de duas
linhas: derivar a lista do módulo (`[v for k, v in vars(mod).items() if
k.startswith("E_")]`).
No validador do CI, **reusar `EXIT_VERDICT_INVALID = 3`** está certo e
não é incoerência: introduzir um 4º código lá obrigaria a rotear o novo
código em `release.yml` (KERNEL, canônico, fora do escopo). A assimetria
`3` no validador × `13` no guard é uma decisão, não um descuido — escreva
isso no plano.

**MF-2 — "entry órfã = MANDATORY-FIRE" é FALSO para esta entrada.**
A tupla `^\.gitignore$` (`scripts/tests/_parity_classify.py:123-132`)
está em **`ACCEPTED`** (lista aberta em `:90`), não em **`KNOWN_OPEN`**
(`:159-165`, hoje vazia). O docstring do módulo é explícito nos dois
sentidos: `:56-58` "KNOWN_OPEN entries are MANDATORY-FIRE. An entry that
matches nothing is FATAL"; `:59-60` "**ACCEPTED entries that turn out
IDENTICAL emit a WARNING** (stale declaration, harmless)". O código
confirma: `stale_ledger` (KNOWN_OPEN) vira `FATAL [ledger-rot]`
(`:507-521`), enquanto `stale_accepted` imprime `WARNING` (`:523-534`) e
não entra em `fatal_blocks` (`:475-499`).
Consequência: se a cura landar e a tupla ficar, o gate emite um aviso e
**o CI fica verde**. É literalmente a 17ª instância da classe que este
plano existe para não cometer, dentro da justificativa do próprio plano.
Duas rotas, ambas aceitáveis: (a) mover a tupla para `KNOWN_OPEN` com
`unblocked_by` no commit **anterior** à cura — aí o mecanismo passa a
forçar a deleção de verdade; ou (b) manter a remoção no commit da cura e
**trocar a justificativa** por AC-3 (que já exige o e2e verde sem a
allowlist). O que não pode continuar é o plano afirmar um mecanismo que
não existe.

**MF-3 — a allowlist mascara o ARQUIVO inteiro, não o bloco.**
`^\.gitignore$` cobre qualquer divergência daquele arquivo. E
`$TARGET/.gitignore` tem **dois** escritores em `install.sh`:
`install_mcp_secrets_dir` (`:1797-1815`, linha `state/mcp_client_secrets/`)
e `install_posture_state_ignores` (`:1830-1857`). `upgrade.sh` não entrega
**nenhum** dos dois (grep por `gitignore` em `scripts/upgrade.sh`: zero
ocorrências). Verifiquei que o bloco do mcp é byte-idêntico entre `v1.2.0`
e HEAD (mesmo comentário `# PLAN-019 P2-SEC-H: MCP shared-secret store
(never commit)`), então o fixture v1.2.0 converge e o e2e não vai ficar
vermelho por isso — **mas a classe não fecha**: um adopter pré-v1.2.0
continua sem o entry do mcp para sempre, e o fixture está pinado em
v1.2.0, então o gate é estruturalmente cego a essa metade.
Como o W1 já vai abrir `upgrade.sh` para adicionar um passo de entrega de
`.gitignore`, entregar **os dois blocos pelo mesmo gerador** custa ~6
linhas e fecha a causa raiz ("upgrade não tem passo de append"). Se a
decisão for não fazer agora, o gap do mcp entra em `KNOWN_OPEN` com
`unblocked_by` — silêncio, não.

**MF-4 — `"npm"` em `SCAN_ROOTS` desce no bundle espelhado.**
`scan_live_surfaces` (`.claude/scripts/tests/test_release_bump_sites.py:1160-1185`)
faz `base.rglob("*")` filtrando apenas `__pycache__` (`:1170-1172`). E
`pytest.ini:68-72` documenta que `npm/.claude/{hooks,scripts}` **espelha
a árvore canônica, incluindo os `tests/`**, durante o staging. Com `"npm"`
como raiz, o censo de "superfícies vivas" passa a contar um **espelho**
como superfície viva, e o teste novo de "semver nu em `npm/*.md`" colheria
`npm/.claude/**/*.md` (skills, ADRs, planos) — vermelho por forma, não por
defeito. `SCAN_ROOTS` já aceita **arquivos** (`"RELEASE.md"` é um, tratado
em `:1170` via `base.is_file()`): use `"npm/INTEGRITY.md"` e
`"npm/README.md"` explícitos.

**MF-5 — OQ-4: a ordem do W2 está invertida e o guard mataria a tag.**
Dois asserts que li fixam a ordem. Primeiro,
`_release_tag_guard.py:369-383` rejeita qualquer entrada de allowlist que
não seja o verdito ou evidência sob `.claude/plans/` — com a mensagem
literal "Allowlisting a version site, a workflow or any code path turns
this assert into permission to land unreviewed work on the tag". Segundo,
`:529-542` (`E_VACUOUS`) exige que o verdito esteja **dentro** do delta.
Logo o parent revisado tem de ser o commit que **já contém curas + bump**,
com o verdito sendo o único arquivo depois dele. A sequência escrita no
plano ("1. Re-pass Codex contra as curas → 2. `bump --rc 4` → verdito")
coloca o bump **depois** do parent revisado ⇒ delta com superfícies de
bump ⇒ `E_DELTA = 6`.
Segundo motivo, mesmo desfecho: R-1 está certo, `.github/scripts/validate-pair-rail-verdict.py`
é a linha 35 do `pair-rail-inputs-hash-manifest.txt` (e
`_release_tag_guard.py` de fato não está lá) — então o `inputs_hash`
declarado no envelope só bate no step 15 se o verdito foi gerado contra a
árvore **já curada**. Reescrever W2.1/W2.2 como: curas + bump landam →
re-pass revisa ESSE SHA → verdito (único arquivo do delta) → push → CI →
preflight → tag.

**MF-6 — OQ-3: o gate "Where enforced ⇒ step existe" não testa a
propriedade que quebrou.**
Ele acopla dois textos livres editados por humanos (prosa markdown ×
`name:` de step YAML). Isso falha nos dois sentidos: fica **vermelho**
quando alguém renomeia um step correto, e fica **verde** para uma promessa
nova escrita sem o prefixo "Where enforced" — que é exatamente o modo como
o P1-3 nasceu. O `INTEGRITY.md` não mentiu sobre o *nome* de um step; ele
afirmou uma garantia para a qual **não existe mecanismo nenhum**.
Duas alternativas, ambas cabem no W0 (superfícies livres):
- **Preferida** — inverter a direção: `INTEGRITY.md` declara seus
  controles num bloco fenced legível por máquina (`control:`, `status:
  enforced|deferred`, `evidence: <workflow>#<step name>`), e o teste
  assere (i) todo controle `enforced` nomeia um step que existe e (ii)
  **nenhuma frase de enforcement vive fora do bloco declarado**. O (ii) é
  o que faz uma promessa nova falhar em vez de passar em silêncio.
- **Mínima**, se (i)+(ii) não couber: gate **negativo** — nenhuma
  ocorrência do vocabulário de enforcement ("enforced today", "every tag
  publish records", "is verified") fora da seção declarada como deferred.
  Regex estrito sobre UM arquivo, robusto, com controle positivo.
Do jeito que está especificado hoje, eu não deixaria embarcar.

## Nice-to-have

- Um comentário de 3 linhas em cada validador dizendo qual dos dois é o
  fail-closed real sob `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` (ver Summary).
  Sem isso, a próxima limpeza remove o gate certo.
- Caso de teste com o literal do template
  (`GO | NO-GO | GO-WITH-CONDITIONS`) como vermelho explícito.
- No `E_DECISION`, imprimir o valor observado **entre aspas** e truncado
  — um `verdict: GO ` com espaço à direita é o falso-vermelho mais
  provável, e a mensagem tem de deixar isso óbvio em 1 segundo.

## Unseen

- **U-1 — o assert de exit codes já é um instrumento verde com pergunta
  velha.** `test_release_workflow_asserts.py:1001-1013` não cobre
  `E_PARENT_NOT_ANCESTOR` (12). O plano cita esse assert como *garantia*
  de que códigos novos são vigiados; ele parou de vigiar em 12. Derivar a
  lista de `vars(mod)` fecha a classe, não só a instância.
- **U-2 — a assimetria GA-CUT × envelope não é bug, mas não está escrita
  em lugar nenhum.** `OWNER-GA-CUT.sh:376-391` exige `"VERDICT: GO"`
  exato sobre a **saída bruta** do rail, e o comentário explica por quê:
  um `GO-WITH-CONDITIONS` carrega condição NOVA que o envelope
  pré-escrito não contém. O gate novo aceita `GO-WITH-CONDITIONS` no
  **envelope**. São dois objetos diferentes e as duas regras estão certas
  — mas sem uma frase declarando isso, o próximo revisor "unifica" e
  quebra um dos dois lados. Custo: 3 linhas de comentário em cada ponta.
- **U-3 — a classe do P1-3 é maior que os irmãos que o plano listou.** O
  defeito não é "`INTEGRITY.md` mentiu"; é "documento público afirma
  controle sem gate". O plano já achou 3 irmãos (`SHA256SUMS.txt`,
  `SUPPORT.md`, `install-npm.sh`) — o que ninguém varreu foi o mesmo
  vocabulário em `README.md`, `npm/README.md`, `SECURITY.md` e `docs/`.
  Uma varredura por vocabulário (não por arquivo) custa minutos agora e
  evita que o próximo re-pass ache o quinto irmão. Se não couber na rc.4,
  registre como item nomeado do trem v1.4.0 — não como "já corrigimos as
  promessas".
- **U-4 — o que importa na entrega do `.gitignore` é a idempotência, não
  o byte-a-byte.** O `.gitignore` do adopter é append-only e **do
  adopter**: ele pode já ter adicionado `.claude/state/` à mão, com outro
  comentário. `install.sh:1846` protege isso com `grep -Fxq` **por
  linha**, não por bloco. O gerador do W1 tem de preservar esse predicado
  por-linha; se ele testar presença do bloco inteiro, todo `upgrade` que
  rodar duas vezes num adopter que editou o comentário duplica o bloco. O
  plano fala em "saída byte-idêntica" (que é sobre o parity gate); a
  propriedade que o adopter sente é outra.
- **U-5 — nada garante que a rc.4 exercite o ramo vermelho.** Ver R-b. O
  AC-1 cobre na suíte; vale também um smoke manual documentado no runbook
  do corte (flipar o envelope para `NO-GO` numa cópia e ver o guard
  matar), porque foi a ausência exata desse exercício que deixou a cura
  anterior passar por completa.

## What I would NOT change

- **A fronteira W0/W1.** Está correta e é o corte de menor custo:
  nenhum dos dois validadores do P1-4 é canônico, e cerimônia é custo
  por-cerimônia. **OQ-2: incluir `scripts/install-npm.sh:182-184` no pack
  W1** — 3 linhas dentro de um escopo que já vai ser assinado, contra
  levar uma claim falsa *conhecida* para o próximo re-pass, onde ela custa
  uma rodada inteira. A assimetria de custo decide sozinha.
- **O escopo mínimo e o que ficou de fora.** Rota (i) do P1-3, node24,
  patch de perf e o wiring da suíte morta: cada um toca KERNEL
  (`validate.yml`) ou o caminho de publish sob hold. Confirmei R-3 — o
  `pytest.ini` (`testpaths`, `:38-44`) realmente não lista
  `.github/scripts/tests`, então a suíte é morta e wirá-la é mudança de
  KERNEL. Fora da rc.4 é a chamada certa. Rota (ii) é a resposta honesta,
  não o atalho.
- **Não unificar a semântica com o `OWNER-GA-CUT.sh`.** Ver U-2: são
  superfícies diferentes, e a mais estrita está no lugar mais
  irreversível. Coexistir é o desenho certo.
- **A doutrina do gerador compartilhado para o P1-1 não é
  over-engineering.** O argumento "são 3 linhas" é exatamente o que se
  dizia do pointer do PROTOCOL.md, e o INV-4/PLAN-168 é precedente do
  MESMO repo com a MESMA causa: duas cópias do mesmo texto. O custo é uma
  função; o retorno é que o parity gate passa a comparar uma origem só.
  **Mas ela só se paga se o gerador for dono de todos os blocos
  marker-guarded do `.gitignore`** (MF-3) — dono de um só, é cerimônia sem
  a propriedade.
- **`release.sh` não muda.** Confirmei `:622-631`: `tag()` já invoca
  `ancestry` e `delta` com `|| die`, incondicionalmente para RC e stable.
  Qualquer exit≠0 novo do guard já mata a tag. Tocar ali só adicionaria
  uma segunda opinião sobre a mesma decisão.
- **Não adicionar `npm/INTEGRITY.md` como site de bump.** A doutrina do
  módulo (writer sem oráculo = dead rule) está certa: texto
  version-neutral + scanner é a resposta com menos partes móveis.
