---
round: 2
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: DevOps & Platform Engineer (Principal)
generated_at: 2026-09-06T06:05:00Z
---

## Verdict

ADJUST — **3 bloqueantes** (R-DO1, R-DO2, R-DO3).

Nota de forma: o alvo indicado na tarefa (`.claude/plans/PLAN-188.md`) NÃO existe no
HEAD; o arquivo revisado é `.claude/plans/PLAN-188-shared-ceremony-toolkit.md`
(landado em `fad3d02`, 751 linhas). Foi esse que critiquei.

## Sumário

- Os 15 must-fix do round 1 estão TODOS endereçados no texto (mapa item-a-item ao
  final). Nenhum é «não fechado» por omissão. O que a revisão introduziu foi
  **mecanismo novo não verificado**: a cura do C1 escolheu o sítio certo
  (`DISCOVERY_ROOTS`) mas ignorou que a descoberta do lint é **por CONTEÚDO**, não
  por endereço — e o controle positivo que o plano escolheu é exatamente o caso
  que passa pelo filtro, enquanto os arquivos em risco não passam.
- Duas classes que este repo já pagou reaparecem: **valor esperado digitado sem
  verificador** (o sha256 do instrumento, AC-4) e **custo de CI afirmado sem
  medição** (o quarto sítio arrasta um job de `timeout-minutes: 150`).
- Três ACs continuam sem NINGUÉM que os execute: AC-1 (metade cara), AC-3
  (diretórios fora do repo) e o «dispara pelo `paths:`», que nenhum instrumento
  local pode falsificar.

---

## R-DO1 — P1 — A cura do C1 é de ENDEREÇO, e a descoberta do lint é de CONTEÚDO: metade do toolkit nasce invisível, e o controle positivo escolhido não reproduz o mecanismo

**Verificado no HEAD.** `.claude/scripts/check-ceremony-script.py:127-146`,
`discover()`:

```
137:                if not fn.endswith(".sh"):
138:                    continue
...
147:                if SHEBANG_RE.match(body) and CEREMONY_OPS_RE.search(body):
```

e `:71-73` `CEREMONY_OPS_RE = re.compile(r"\bgpg\b|git tag|gh release|npm publish|sentinel|approved\.md|VERDICT")`.

Consequências que o plano não escreve, sobre a SUA PRÓPRIA lista de arquivos da W0
(`:359-368`):

1. `.claude/scripts/ceremony/read_manifest.py` — **excluído pelo filtro `.sh`**
   (`:137`). É o leitor fail-CLOSED que o plano põe no ponto onde o Owner assina
   (`:151-153`, `:169-175`). Ele NUNCA será coberto pelo ceremony-lint, por
   nenhum dos quatro sítios. O plano afirma o contrário em `:126-127`
   («os TRÊS sítios que fazem o lint valer para o toolkit»).
2. `controls/inv3_abs_path.sh`, `controls/inv4_baseline.sh`, `controls/run.sh` —
   nada obriga esses corpos a conter `gpg|git tag|gh release|npm publish|sentinel|approved.md|VERDICT`.
   Um controle de path absoluto que roda `grep -R '^/'` casa ZERO tokens ⇒
   `discover()` não o devolve ⇒ **R1-R4 e R8 não se aplicam a ele**, com
   `DISCOVERY_ROOTS` já alargado. Falso-verde por CONTEÚDO, que sobrevive intacto
   à cura de endereço.
3. O controle positivo que o plano escolhe (`:134-136`, AC-1 `:460-462`) é
   «um script do toolkit com `|| true` numa linha de `gpg`». Uma linha de `gpg`
   satisfaz `CEREMONY_OPS_RE` — **o controle prova o ramo que já funcionaria** e é
   cego ao ramo que falha. É a lição «controle positivo reproduz o MECANISMO do
   detector, não a aparência».

**Ajuste exigido:** o AC-1 da W0 declara o CONJUNTO ESPERADO de arquivos
descobertos e compara com a saída real de `discover()` (igualdade de conjuntos,
nos dois sentidos) — não «o lint enxerga o toolkit»; a W0 decide, no mesmo patch,
uma de duas: (a) todo arquivo do toolkit carrega um token de `CEREMONY_OPS_RE`
por construção (frágil), ou (b) `discover()` ganha uma raiz com predicado
**por endereço** (todo `*.sh` sob `.claude/scripts/ceremony/` é candidato,
sem filtro de conteúdo); e o `read_manifest.py` recebe cobertura NOMEADA por
outro gate (o `.py` está fora do lint por construção).

## R-DO2 — P1 — Com a descoberta funcionando, R1 BLOQUEIA todo script do toolkit: o único caminho verde é uma isenção por arquivo — que anula a regra que o plano diz herdar

**Verificado.** `check-ceremony-script.py:167-169`:

```
    if PROVENANCE_MARK not in body and EXCEPTION_MARK not in body:
        findings.append({"rule": "R1", "sev": "BLOCKING", ...
```
com `:84-85` `PROVENANCE_MARK = "AUTO-GENERATED"` e
`EXCEPTION_MARK = "CEREMONY-LINT: handwritten-exception:"`.

O toolkit é, por tese do plano, **escrito à mão e compartilhado** — é o produtor,
não o produzido. Nenhum dos cinco scripts nem dos seis controles pode legitimamente
carregar `AUTO-GENERATED`. Logo, no instante em que a cura do R-DO1 fizer a
descoberta funcionar, **cada arquivo do toolkit sai R1 BLOCKING** e o único verde
disponível é escrever `CEREMONY-LINT: handwritten-exception:` em todos eles.

O plano vende o oposto em `:121-124` e `:129-133` («sem a qual o toolkit
descoberto herdaria QUATRO das cinco classes bloqueantes (R1-R4), não cinco»):
ele conta R1 como classe HERDADA, quando na prática R1 será **dispensada por
exceção em 100 % do toolkit**. Isso não é fatal — mas é uma afirmação do plano
que fica falsa na execução, e a decisão (a exceção é aceitável para o toolkit? com
que texto de razão? auditada por quem?) não está escrita em lugar nenhum.

**Ajuste exigido:** §Approach declara explicitamente que o toolkit é linted sob
`EXCEPTION_MARK`, com a razão que cada arquivo carrega; a contagem «QUATRO das
cinco» vira «TRÊS (R2-R4) + R8», ou a W0 entrega uma terceira via (marca de
proveniência própria para código de toolkit rastreado).

## R-DO3 — P1 — O quarto sítio (`smoke-install.yml`) arrasta um job de 150 minutos para um `shasum -c` de 2 segundos, e o plano não mede o custo — enquanto a OQ-9 se preocupa com a metade barata

**Verificado.** O step de integridade que o plano quer disparar está em
`.github/workflows/smoke-install.yml:355-360` (`shasum -a 256 -c` sobre o
manifesto). Ele vive dentro do **ÚNICO job** do workflow (`:192-193`,
`jobs: / smoke:`), cujo `timeout-minutes` é **150** (`:337`) — não 126, como
`CLAUDE.md` §5 ainda registra. Medições que o próprio repo carrega:
`adb6e84` 1h08 e `5930974` 58 min.

O plano manda acrescentar `.claude/scripts/ceremony/**` e
`.claude/governance/gate-scripts-manifest.txt` às DUAS listas `paths:`
(`:320-322`, `:678-681`, `:366-368`). Efeito real: **todo PR que toque um byte do
toolkit passa a rodar o install/upgrade e2e inteiro** (~1 h de runner) para
executar um `shasum -c` de segundos. O plano afirma o sítio com controle positivo
e **não cita nenhum número de custo** — enquanto a OQ-9 (`:704-711`) está aberta
justamente sobre runner-minutos da metade CARA do AC-1, e o `validate.yml:341-359`
já dá de graça a metade barata.

Isto é a marca «custo de CI afirmado sem medição». Também vale a nota do próprio
plano (K10, `:136-140`): `validate.yml:354` exclui
`.claude/scripts/owner-ceremony/archive/*`, diretório inexistente — a casa já
pagou por escolher endereço sem olhar o custo do gate.

**Ajuste exigido:** o plano nomeia o custo esperado (≈1 h de runner por PR do
toolkit, com as duas medições citadas) e decide entre (a) aceitar, (b) mover a
verificação de integridade para um job/workflow próprio com `paths:` do toolkit —
segundos em vez de uma hora —, ou (c) acrescentar o step ao `validate.yml`, que já
dispara amplamente. A OQ-9 passa a cobrir as DUAS metades, não só a cara.

## R-DO4 — P2 — Alargar a R8 ao toolkit torna não-executáveis os scripts que o Owner invoca à mão, contra a razão escrita no próprio checador

**Verificado.** `check-ceremony-script.py:192-194`:

```
    # R8 só na superfície de binding assinado (.claude/plans/): exec-bit
    # em ferramenta de scripts/local/ é legítimo (invocada diretamente).
    if git_mode == "100755" and rel.startswith(".claude/plans/"):
```
E de fato `git ls-files -s` dá **100755** para
`.claude/scripts/local/generate-ceremony.sh` e `.claude/scripts/local/verify-counts.sh`,
contra **100644** em `.claude/plans/PLAN-182/OWNER-S326-LAND.sh`.

O plano manda alargar a R8 ao toolkit (`:129-133`, `:366`) com controle positivo
«exec-bit no índice REPROVA» (`:135-136`). Consequência não escrita: `sign.sh`,
`land.sh`, `harness.sh` e `controls/run.sh` têm de shipar **100644** e ser
invocados como `bash <path>` — o oposto da razão que o próprio checador dá para a
isenção de `scripts/local/`. Some-se `CLAUDE.md` §4: tirar o exec-bit exige tirá-lo
do índice E do filesystem, senão um `git add -A` o traz de volta — ou seja, o
controle positivo do AC-1 vai reprovar sozinho no primeiro `git add -A` de quem
tiver rodado `chmod +x` para testar.

**Ajuste:** o plano declara o modo de invocação (`bash <path>`), fixa modo 100644
para todo o toolkit e nomeia a armadilha do `git add -A`; ou restringe a R8 aos
arquivos ASSINÁVEIS do toolkit e deixa o runner executável.

## R-DO5 — P2 — O digest do instrumento (AC-4) é um valor esperado DIGITADO num documento sem verificador

`:512-513` fixa o sha256 `d2234bdf…181062` de
`.claude/plans/PLAN-188/measure-rail-classes-v2.py`. **Confere hoje** (rodei
`shasum -a 256` sobre o path: bate byte a byte). O problema é de mecânica: o valor
mora no texto do plano, **nenhum gate o confere** — o instrumento não está no
manifesto ADR-192 (`grep -ve '^#' -e '^$'` dá os 9 membros; nenhum é ele), não está
em `_CANONICAL_GUARDS` e `verify-counts.sh` não olha para `.claude/plans/**`. E o
próprio plano manda EDITÁ-LO na W3 (`--since`, `--cohort`, raiz `ceremony/**` no
classificador, `:531-541`, `:571-576`). Um valor esperado escrito à mão que a wave
seguinte invalida por desenho é a classe «`EXPECTED_*` declarado à mão envelhece»
que a noite S329 já pagou.

**Ajuste:** o digest sai do texto e vira linha de manifesto verificada por
`shasum -c` (ADR-192 ou um manifesto próprio do PLAN-188), com o bump acontecendo
no MESMO patch que edita o binário — dois digests em arquivo, não dois digests em
prosa.

## R-DO6 — P2 — Três Checks não têm executor nomeado; dois deles nem sequer podem ficar vermelhos onde o CI roda

- **AC-1, metade cara** (`:457-459`, «o runner de controles imprime 5/5»): quem o
  roda está na OQ-9, ABERTA. Não é «flag só se a OQ esconde decisão necessária
  antes da W0» — é pior: é a decisão necessária para **fechar** a W0. O AC-1 é o
  aceite da W0.
- **AC-1 / AC-6, «dispara pelo `paths:`»** (`:462-463`, `:320-325`): nenhum
  instrumento local falsifica um filtro `paths:` de workflow — actionlint valida
  sintaxe, não roteamento. A única prova é um PR real que toque só um arquivo do
  toolkit e mostre o job executado. O plano deve escrever essa evidência como
  «URL de run + lista de steps executados», ou o Check prova um NOME (a linha no
  YAML) e não BYTES (o job que rodou).
- **AC-3** (`:486-503`): o mapa aponta para `<PK>/<dir do pacote>` e o próprio
  plano diz que os seis pacotes ficam FORA do repo (`:58-60`). Logo o Check e o
  seu controle positivo não rodam num checkout limpo nem em CI, e a árvore `<PK>`
  é a área de trabalho de uma noite — quando ela sumir, o AC-3 fica
  **irrodável**, não vermelho. O AC-4 ganhou critério de morte pré-registrado
  (`:577-582`); o AC-3 não tem nenhum.

**Ajuste:** cada um dos três nomeia executor (workflow+step, ou «harness local,
evidência colada no sentinel») e o AC-3 ganha critério de morte simétrico ao do
AC-4 («corpus indisponível ⇒ NÃO CONCLUSIVO, com o porquê escrito»).

## R-DO7 — P3 — O controle vermelho da invariante 10 exige chaveiro GPG, e nenhum runner o tem

A invariante 10 (`:270-281`) entra no subconjunto falsificável da W0 (`:369-371`,
AC-1 `:452-453`). O seu controle vermelho é «`.asc` de chave FORA da allowlist ⇒
recusa nomeada» (`:281`) — o que exige gerar um par GPG descartável e assinar um
fixture. `validate.yml` não instala nem semeia chaveiro em passo nenhum
(o único step de shell relevante é o shellcheck, `:341-359`). É um custo de
ambiente que a OQ-9 não enumera.

## R-DO8 — P3 — O escape do lint não é mencionado

`.claude/scripts/ceremony-lint-waivers.json` existe e isenta por sha256 de
CONTEÚDO (o próprio arquivo diz «re-arma sozinho em qualquer edicao»). O plano
nunca o cita. Não é defeito — é uma porta que o texto deveria fechar por escrito
(«nenhum arquivo do toolkit entra em waiver»), já que o toolkit vai ser o gate.

---

## Os 15 must-fix do round 1 — closed / partial / not closed

| # (consenso r1) | Estado | Evidência no arquivo revisado |
|---|---|---|
| endereço = decisão de gate, dois sítios no mesmo patch | **parcial** | `:112-140` fecha o endereço; a descoberta por CONTEÚDO fica aberta (R-DO1) |
| contradição «W0 livre» × cerimônia; razão falsa sai | **fechado** | `:291-301` — W0 é CANÔNICA, dois lands «à moda antiga»; oráculo medido por mim: `ceremony-lint.yml` = 1, `smoke-install.yml` = 1, `ceremony/sign.sh` = 0 |
| `scope_generated_from` / `--describe` | **fechado** | `:177-190` + inv. 5 `:245-250` (dois braços, verificação incondicional) |
| formato do manifesto antes da W0 | **fechado** | `:142-175` TSV + leitor Python; `tomllib` refutado |
| AC-1 reduzido ao falsificável por `lib.sh` | **fechado** | `:449-465` (1,3,4,5,10 na W0; 2,6,7,8 na W1) |
| AC-3 com mapa + controle positivo | **parcial** | `:486-503` tem os dois; sem executor e sem critério de morte (R-DO6) |
| AC-4 pinado / parâmetros / denominador / morte | **parcial** | `:504-584` completo em texto; digest sem verificador (R-DO5) |
| invariante 10 (signatário) | **fechado** | `:270-281`; recontei: 33 de 48, bate |
| registros de rail por sha256; inv. 9 | **fechado** | `:222-230`; inv. 9 ADVISORY `:260-269` conforme K5 |
| corte v2 na W1/W2; W2 em subwaves | **fechado** | `:374-389`, `:401-407`, `:410-416`; recontei PLAN-169 = 13 |
| reconciliação com `generate-ceremony.sh` | **fechado** | `:192-220`; consumidores conferidos (`test_generate_ceremony.sh:21`, `PLAN-174:98`) |
| AC próprio de membresia ADR-192 + bootstrap | **fechado** | AC-6 `:590-599`; bootstrap `:285-290`; manifesto = 9 membros, conferido |
| custódia dos clones assinados | **fechado** | `:418-425`; faixas de `check_contamination.py` conferidas em `:299-301` e `:321-326` |
| `depends_on` + Items no PLAN-SCHEMA | **fechado** | `:7`; `PLAN-186-orchestrator-operating-model.md` = `status: executing`; `PLAN-SCHEMA.md:441` confere |
| OQ-6..OQ-9 | **fechado** | `:667-711` |

Nenhum item «não fechado». Os três parciais são os P1/P2 acima.

## O que falta antes de executar (OQs que o Owner precisa ratificar)

1. **OQ-9 alargada** — quem roda o runner de controles E o custo do quarto sítio
   (R-DO3, R-DO6, R-DO7). É a única OQ que bloqueia o FECHAMENTO da W0.
2. **OQ-3 (resta a lista de recusas)** — não bloqueia; a decisão de formato já foi
   tomada.
3. OQ-1, OQ-2, OQ-4, OQ-5, OQ-6, OQ-7, OQ-8 — do Owner por desenho, nenhuma
   esconde decisão necessária ANTES de a W0 começar (a OQ-5 já está corretamente
   sequenciada como pré-condição do AC-4, não da W0).

## Verdict

**ADJUST — 3 bloqueantes** (R-DO1, R-DO2, R-DO3). Nenhum é fatal para a tese: o
toolkit compartilhado continua o corte certo, e a revisão do round 1 foi honesta
(15/15 endereçados, e vários com medição própria que reproduzi). O que os três
bloqueantes têm em comum é a mesma forma que este plano existe para acabar: **um
gate cuja PERGUNTA não é a que o mecanismo responde** — endereço onde o filtro é
conteúdo, «classe herdada» onde a regra será dispensada, e um sítio de `paths:`
escolhido sem olhar o job que ele acorda.
