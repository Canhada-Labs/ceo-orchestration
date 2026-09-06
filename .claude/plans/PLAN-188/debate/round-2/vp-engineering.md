---
round: 2
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — o arquétipo não tem bloco de persona em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-06T03:40:00Z
---

## Verdict

ADJUST — **4 bloqueantes** (R-VP1, R-VP2, R-VP3, R-VP4).

## Summary (≤ 3 bullets)

- Os 15 must-fix do round 1: **12 fechados, 2 parcialmente, 1 fechado no texto
  mas com a cura apontando para um mecanismo que não faz o que o plano diz**
  (C1 — o lint de cerimônia é `.sh`-only e condicionado por CONTEÚDO, então o
  `read_manifest.py` fica fora das cinco classes bloqueantes e o controle
  positivo do AC-1 não discrimina). Tabela item-a-item na §1.
- Os quatro novos bloqueantes são todos da MESMA forma que o round 1 já
  nomeou — «Check que não pode ficar vermelho» e «duas seções que se leem como
  regras diferentes» —, mas em sítios que o round 1 não olhou: AC-2, a divisão
  W0a/W0b, e a OQ-7 travando o leitor que a W0 entrega.
- A tese continua certa e o plano melhorou muito. O que falta é pequeno em
  linhas e grande em consequência: sem R-VP1 e R-VP4 a W0 landa verde sem
  provar nada.

## 1. Os 15 must-fix do round 1 (`round-1/consensus.md:6-21`)

| # | item | veredito | evidência |
|---|---|---|---|
| 1 | endereço = decisão de gate, 2 sítios no mesmo patch | **parcial** | plano :126-133 entrega 3 sítios + o 4.º em :320-323; mas ver R-VP1 |
| 2 | contradição «W0 livre» × cerimônia | fechado | :291-301 («a W0 é CANÔNICA») + :352-358 |
| 3 | `scope_generated_from` sem comando | **parcial** | :177-190 dá dois braços; mas ver R-VP4 |
| 4 | formato antes da W0 (TOML impossível) | fechado | :142-175; reproduzi `python3 -V`=3.9.6, `import tomllib`=ModuleNotFoundError |
| 5 | AC-1 reduzido ao falsificável | **parcial** | :369-373 lista 1,3,4,5,10; ver R-VP3 |
| 6 | AC-3 com mapa + controle positivo | fechado | :486-503 |
| 7 | AC-4 pinado/parâmetros/morte | fechado | :510-584; sha256 confere: `shasum -a 256 .claude/plans/PLAN-188/measure-rail-classes-v2.py` = `d2234bd…181062` |
| 8 | invariante de signatário | fechado | :270-281; reproduzi 33 e 48 |
| 9 | rail pinado por digest; inv. 9 reescrita | fechado | :224-230, :260-269 (ADVISORY, K5) |
| 10 | W1/W2 declaram o corte v2 | fechado | :374-389, :401-407, :410-416 |
| 11 | reconciliação `generate-ceremony.sh` | fechado | :192-220; consumidores vivos verificados (`test_generate_ceremony.sh:21`, `PLAN-174:98`) |
| 12 | AC de membresia ADR-192 | fechado | AC-6 :590-599; manifesto tem 9 membros, confirmado |
| 13 | custódia dos clones assinados | fechado | :417-425; `check_contamination.py:299-301` e `:321-326` conferem |
| 14 | `depends_on` + file assignment/AC/commit por item | fechado | frontmatter :7; PLAN-186 é `executing` (`.claude/plans/PLAN-186-orchestrator-operating-model.md:4`) |
| 15 | OQ-6..OQ-9 | fechado | :667-711 |

## 2. Riscos

### R-VP1 — BLOQUEANTE (P1) — a cura do C1 não alcança o arquivo que mais importa, e o controle positivo do AC-1 não discrimina

`check-ceremony-script.py:127-151`: `discover()` só considera nomes que terminam
em `.sh` (`:137-138`) e só aceita um `.sh` cujo corpo case **SHEBANG_RE E**
`CEREMONY_OPS_RE` (`:146`), com `CEREMONY_OPS_RE` = `gpg|git tag|gh release|npm
publish|sentinel|approved\.md|VERDICT` (`:71-73`). Consequências, contra o texto
do plano :121-124 («o script que passa a SER o gate da assinatura nasce isento
das cinco classes BLOQUEANTES»):

1. `.claude/scripts/ceremony/read_manifest.py` — o parser fail-CLOSED no ponto
   exato onde o Owner assina, entrega da W0 (:359-360) — **nunca é descoberto**,
   pondo-se `DISCOVERY_ROOTS` o que se puser. Nenhuma das cinco regras
   bloqueantes o cobre, hoje ou depois.
2. `lib.sh` e `controls/inv3_abs_path.sh`, `controls/inv4_baseline.sh`,
   `controls/run.sh` só são descobertos se os BYTES deles contiverem um dos sete
   tokens. Descoberta condicionada a conteúdo é a mesma classe «falso-verde por
   endereço» que o C1 fechou, um nível abaixo.
3. O controle positivo que o AC-1 exige (`:460-461`: «um script do toolkit com
   `|| true` numa linha de `gpg` REPROVA na regra R2») **fornece ele próprio o
   token `gpg` que torna o arquivo descoberto**. Ele passaria mesmo que a
   entrada em `DISCOVERY_ROOTS` estivesse errada para todos os arquivos REAIS do
   toolkit: é um Check que não pode ficar vermelho pela razão que alega medir.

Cura mínima: (a) a W0 declara como o lint passa a ver `.py` de cerimônia, ou
escreve que `read_manifest.py` fica fora e nomeia o gate que o cobre; (b) o
controle positivo do AC-1 usa um arquivo do toolkit **sem** token de
`CEREMONY_OPS_RE` (prova a descoberta) além do controle de R2 (prova a regra).

### R-VP2 — BLOQUEANTE (P1) — a divisão W0a/W0b deixa `lib.sh` em nenhuma das duas

§Items W0 lista como arquivos «`lib.sh`, `read_manifest.py`, e UM arquivo de
controle por invariante … mais o runner» + os três de gate (:359-368). A divisão
declarada em :383-386 é **W0a** = «manifesto + leitor + os TRÊS arquivos de gate
= 5 paths» e **W0b** = «os seis arquivos de controle». Somando: 5 + 6 = 11 ✓,
mas o conjunto não bate — `lib.sh` não aparece em nenhuma das duas, e «manifesto»
nomeia um arquivo que a W0 não entrega (o `ceremony.tsv` é da W1, :397). Como o
AC-1 da W0 é definido como «o subconjunto que **`lib.sh`** falsifica SOZINHO»
(:451-452, :369-370), a subwave que carrega os controles (W0b) ficaria sem a
biblioteca que eles chamam. Duas seções que se leem como regras diferentes.

### R-VP3 — BLOQUEANTE (P1) — três dos cinco controles da W0 são definidos em termos de `finalize.sh`/`sign.sh`, que são da W1

O plano justifica o subconjunto {1,3,4,5,10} com «todas predicados sobre
ARQUIVOS» (:370-371). O texto das próprias invariantes diz outra coisa:
invariante 1 — registros «PINADOS por sha256 **gravado pelo `finalize`**»
(:225-226); invariante 4 — «escritos SÓ pelo finalize; **`sign.sh`** regenera e
compara» (:241-242); invariante 5, braço (b) — «o **`finalize.sh`** grava o
arquivo de escopo … e o **`sign.sh`** compara» (:246-248). Ambos são entrega da
W1 (:395-397). É literalmente o argumento com que o C6 tirou 2/6/7/8 da W0
(«controle sem o objeto que ele falsifica é verde vacuoso», :371-373), aplicado
a 1/4/5 e não visto. O plano pode salvá-los, mas só declarando o que hoje não
declara: que `lib.sh` contém os PREDICADOS e que `sign.sh`/`finalize.sh` são
apenas chamadores — hoje o file assignment da W0 não diz o que `lib.sh` contém.

### R-VP4 — BLOQUEANTE (P1) — a OQ-7 esconde uma decisão que o leitor da W0 precisa ter tomado

O esquema do manifesto congela a chave `scope_generated_from` (:166) e o leitor
nasce com «chave desconhecida» na lista de RECUSAS NOMEADAS (:170-171). A OQ-7
(:689-696) deixa em aberto se a chave existe («se `scope_generated_from` é chave
OPCIONAL»). As duas leituras são incompatíveis num leitor fail-closed entregue
pela W0: com a chave no esquema, um pacote sem derivador `--describe` é recusado;
sem ela, um pacote que a traga é recusado como chave desconhecida. A tarefa deste
round manda não re-litigar OQs — este não é o mérito da OQ-7, é o
SEQUENCIAMENTO: como a OQ-3 antes dela, a OQ-7 tem de ser pré-condição da W0 ou
o esquema tem de declarar a chave como opcional-por-construção.

### R-VP5 — P2 — o Check do AC-2 é a vacuidade do C2, no AC que gateia a W1

AC-2 (:471-474): «o commit landado do piloto não referencia nenhum
`OWNER-*-{SIGN,LAND}.sh` próprio». Reproduzi o mesmo comando que o AC-3 usa para
se declarar inobservável: `git ls-files | grep -icE 'w4b|w5a|w1a|w6a'` = **0**, e
o plano diz que os pacotes ficam FORA do repo (:58-60, :492). O commit landado de
um pacote fora da árvore nunca referencia os scripts dele — a resposta é «não
referencia» ANTES do trabalho e continua «não referencia» se o piloto tiver usado
um clone. O round 1 curou isso no AC-3 (mapa + controle positivo, :495-503) e não
olhou o AC-2. Cura: o AC-2 herda o controle positivo do AC-3 (plantar um
`OWNER-*-SIGN.sh` no diretório do piloto ⇒ VERMELHO).

### R-VP6 — P2 — o alargamento da R8 contradiz a razão escrita no código e não tem contrato de invocação

`check-ceremony-script.py:192-194` documenta a razão do escopo atual: «R8 só na
superfície de binding assinado (`.claude/plans/`): exec-bit em ferramenta de
`scripts/local/` é legítimo (invocada diretamente)». Medido: o gerador que o
toolkit ABSORVE é rastreado `100755` (`git ls-files -s
.claude/scripts/local/generate-ceremony.sh`). O plano alarga a R8 ao toolkit
(:129-133) e exige controle positivo de reprovação por exec-bit (:134-136), sem
dizer em nenhum lugar como o Owner invoca `sign.sh`/`land.sh`. Se for `./sign.sh`,
o próprio toolkit shipado nasce VERMELHO na regra que a W0 acabou de alargar.
Uma linha resolve: «o toolkit é invocado por `bash <path>`; exec-bit é recusa».

### R-VP7 — P2 — o AC-1 produz evidência que ninguém executa, e a OQ-9 não pode ficar para depois da W0

O AC-1 exige que «o runner de controles imprime 5/5 VERMELHO-antes /
VERDE-depois» (:457-459), e a OQ-9 (:704-711) deixa em aberto quem o executa. O
repo já pagou essa classe e a escreveu no próprio workflow:
`.github/workflows/smoke-install.yml:20-21` («a red gate nobody runs — an unwired
test is the same as no test») e `:36-38`. Sem um sítio de execução decidido no
patch da W0, a evidência do AC-1 é uma execução manual de uma noite, e os
controles apodrecem exatamente como o `test-manifest-delivery-route.sh` apodreceu
até a S327. Não peço a decisão de custo — peço que a W0 nomeie o evento.

### R-VP8 — P3 — citações de esquema sem o path que resolve no HEAD

O plano cita `PLAN-SCHEMA.md:441` (:348) e `PLAN-SCHEMA.md:462-470` (:20). O
arquivo não existe na raiz: `git ls-files | grep -i plan-schema` =
`.claude/plans/PLAN-SCHEMA.md` (o CONTEÚDO das duas faixas confere ali —
`:441` é o item «`## Items` … each with file assignment, acceptance criteria, and
commit message hint»; `:462-470` é «§7 The `id` and `depends_on` graph»). É a
convenção do `CLAUDE.md` §4, mas num plano que exige de terceiros «toda citação
resolve no HEAD» o custo de escrever o path é zero.

## 3. O que falta antes de executar (ratificação do Owner)

1. **OQ-7 antes da W0** (R-VP4) — é a única OQ que trava um artefato da W0.
2. OQ-9 reduzida a «qual evento» antes da W0 (R-VP7); o custo pode vir depois.
3. OQ-3 já resolvida no texto; OQ-1/OQ-2/OQ-4/OQ-5/OQ-6/OQ-8 não bloqueiam a W0
   (a OQ-5 bloqueia só o AC-4 virar critério, e o plano já escreve isso em
   :507-509).

## 4. Verdict

**ADJUST — 4 bloqueantes** (R-VP1, R-VP2, R-VP3, R-VP4). Nenhum deles pede
arquitetura nova: três são de TEXTO (o conjunto de arquivos das subwaves, o que
`lib.sh` contém, a chave opcional) e um é de MECANISMO com cura de duas linhas
(descoberta `.py` + controle positivo que discrimine). Com eles fechados eu
concedo `design-coherent` para a W0 e a W1; a W2 e a W3 já estão coerentes o
bastante para serem escritas quando a sua vez chegar.
