---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (none — perfil sintetizado da linha do skill-map; não há persona em team.md nem agents/ para este papel)
generated_at: 2026-09-16T00:45:00Z
plan: PLAN-189
scope_reviewed: "W0 — o texto REAL: w0/payloads/protocol-section.md (byte-igual ao bloco da proposal.md, verificado), w0/payloads/ADR-140-AMEND-1-cure-the-class.md.new e o derivador w0/derive-p189-w0.py (3.ª lane)"
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano põe em `PROTOCOL.md` uma regra que o repo já paga por não ter (r22 do
  179close: 5 rodadas da mesma classe até a troca de arquitetura). A tese é
  correta, a decisão de assinatura pequena (Owner, decisão 6) é correta, e o
  status `ACCEPTED`-no-land do ADR com `authorization` apontando o sentinel é a
  forma certa (precedente ADR-164-AMEND-1). Nada aqui reduz detecção.
- O escopo declarado (3 paths) é INSUFICIENTE para o land sair verde: o par
  `PROTOCOL.md ↔ PROTOCOL.pt-BR.md` é registrado em
  `.claude/scripts/translations-pairs.yaml` e o job BLOQUEANTE
  `structural-parity` exige igualdade de contagem de headings (hoje 52 = 52,
  `drift: false`); a W0 acrescenta um H2 só ao lado inglês. E o novo arquivo de
  ADR faz `check-claude-md-claims.py` (CI, `validate.yml:82-85`) e
  `verify-counts.sh` (chamado pelo PRÓPRIO molde, `OWNER-PIN-SIGN.sh:95`)
  reprovarem contra o «198 ADRs» de `CLAUDE.md:54`. O SIGN abortaria no
  próprio gate.
- O texto tem três buracos de desenho que o rail vai achar por leitura: o item
  3 promete um mecanismo que não existe e fala em «rodada sobre uma classe»
  (rodadas são por candidato); a «aceitação de risco nomeada» não diz quem
  aceita nem o que ela faz com a 3.ª ocorrência; e a palavra «classe» já é
  usada com OUTRO sentido na regra R2 ratificada (classe de ARTEFATO), com «no
  round ceiling» contradizendo R2/R3 e os caps da DEBATE-SCHEMA §12.1.

## Risks

- **R-VP1** — Severity: CRITICAL — O job `structural-parity` de
  `.github/workflows/translations-drift.yml` (sem `continue-on-error`, dispara em
  push para `main` quando `PROTOCOL.md` muda) roda
  `.claude/scripts/check_translations_drift.py`, cuja regra em
  `check_translations_drift.py:100-104` exige `src_headings == mir_headings`. Medido
  na árvore viva: EN 52 headings / 10 fences / 597 linhas, PT-BR 52 / 10 / 596,
  `drift: false`. A W0 leva o EN a 53 ⇒ main VERMELHO no primeiro push. O ADR §4
  ainda justifica não tocar o espelho com «already out of sync since 2026-06-11»
  — falso como justificativa: os dois arquivos foram tocados pela última vez no
  MESMO commit (`9777a8d`, 2026-06-29) e o checker os dá em paridade hoje.
  Mitigação: `PROTOCOL.pt-BR.md` (oráculo `--is-canonical` = 0, livre) entra no
  escopo da W0 com a seção traduzida; a âncora `\n---\n\n## 3-Strike policy\n` é
  ÚNICA também no espelho (medido: 1), logo o mesmo `_derive` serve com um
  segundo payload; a bateria do SIGN roda `check_translations_drift.py --json`
  sobre a árvore aplicada. Delta de linhas fica em ~6 % (≤ 10 %).
- **R-VP2** — Severity: HIGH — `check-claude-md-claims.py` conta
  `.claude/adr/ADR-*.md` (198 hoje, AMENDs incluídos) contra a regex
  `\b(\d+)\s+ADRs\b` em `CLAUDE.md:54`; `verify-counts.sh:196` deriva o mesmo
  número e o molde da cerimônia (`codex-pin/OWNER-PIN-SIGN.sh:95`) o executa
  ANTES de assinar. Com o ADR novo, 199 ≠ 198 ⇒ o SIGN morre no próprio gate e,
  se passasse, a CI cai. Precedente: os lands de ADR-197 (`303ae55`) e ADR-196
  (`cc00235`) editaram `CLAUDE.md` no MESMO commit assinado. Mitigação:
  `CLAUDE.md` (oráculo 0) entra no escopo com a troca «198» → «199», feita pelo
  derivador. Cuidado medido: `CLAUDE.md` tem 39.982 bytes, 18 abaixo do limite de
  40.000 do governance COMPLETO — a edição tem de ser byte-neutra (3 dígitos →
  3 dígitos); a ideia de a linha S352 «virar referência» NÃO cabe nesta
  assinatura sem encurtar outra coisa.
- **R-VP3** — Severity: HIGH — O item 3 do texto («no further round opens on
  that class until…») lê-se como mecanismo e é semanticamente torto: rodadas
  abrem sobre um CANDIDATO, não sobre uma classe. Hoje nenhum hook lê o registro
  da rodada; o único gate mecânico com essa forma no repo é a condição de
  LANÇADOR da R2 («verificado pelo lançador antes de abrir a rodada N+1»,
  `PLAN-186-orchestrator-operating-model.md:288-292`). E a parentética da
  pergunta 3 («W2/W3 tornam mecânico») também não se sustenta: W2 é telemetria
  (torna a 2.ª ocorrência OBSERVÁVEL), W3 é salvaguarda do relato — nenhuma das
  duas impede uma rodada de abrir. Mitigação: reescrever como obrigação de quem
  abre a rodada («the CEO/lander MUST NOT open round N+1 of that ceremony while
  the record shows a second occurrence with neither…») e acrescentar UMA linha
  de nível de enforcement, como o ADR-140 faz («checklist-enforced; lander
  condition; no blocking hook; W2 makes it observable»); corrigir o §3 do ADR.
- **R-VP4** — Severity: HIGH — «named risk acceptance» não diz QUEM aceita nem o
  que a aceitação FAZ com a instância seguinte. Sem acceptor, o autor aceita o
  próprio risco (o repo já pagou esta classe: «agente NÃO alarga a própria
  allowlist», «GPG válida NÃO é autorização mecânica»). Sem efeito definido, a
  3.ª ocorrência ou continua bloqueando (a cerimônia gira igual, agora com
  «aceito» no registro) ou deixa de ser registrada — e isso é redução de
  detecção pela porta dos fundos, exatamente o que o texto jura não fazer.
  Mitigação (texto): a aceitação é ESCRITA pelo autor e RATIFICADA pelo Owner na
  assinatura da cerimônia (o registro está no escopo assinado); até lá é
  PROPOSTA e a cerimônia pode seguir com ela no registro; instâncias
  posteriores da classe aceita continuam REGISTRADAS sob a aceitação (detecção
  intacta), não bloqueiam por si, e uma instância P0 ou o Owner REABRE a
  aceitação (precedente: gatilho de reabertura observável do ADR-089-AMEND-1).
  Quando a remoção da superfície exige paths FORA do escopo assinado
  (`touched ⊆ scope`), a aceitação é interina e NOMEIA o follow-up que remove.
- **R-VP5** — Severity: MEDIUM — Colisão de vocabulário e contradição com regra
  ratificada: na R2 (Owner, S348) «classe» é classe de ARTEFATO (prosa/docs 1,
  material 1, instrumento 2, canônico 2 rodadas); na W0 é classe de ACHADO. E o
  texto assinado diz «no round ceiling» enquanto R2 é um teto por classe de
  artefato, R3 rescinde acima de 20 rodadas e a DEBATE-SCHEMA §12.1 tem
  `--max-rounds 5` (default) e cap duro 10. Um `PROTOCOL.md` assinado que nega
  a existência de tetos ratificados é auto-contraditório no dependent-set.
  Mitigação: usar «finding class» (ou «defect class») em todo o texto; trocar
  «It reduces no detection: no round ceiling…» por «This section introduces no
  ceiling, no filter and no severity waiver of its own; the spend stops of the
  operating model (R2, R3) and the debate caps (DEBATE-SCHEMA §12.1) are
  unchanged» — e o ADR nomeia a R3 como a gêmea de nível de pack («a classe só
  volta com ARQUITETURA diferente», `PLAN-186…:293-297`) para não haver duas
  regras sem dono para um defeito (espírito da R6).
- **R-VP6** — Severity: MEDIUM — O parágrafo de precedentes no `PROTOCOL.md` é
  um ímã de NO-GO por TEXTO (lição do GA v1.4.0: 3 rodadas por enumeração de
  sítios em material assinado). Medido contra o disco: (a) «`_sanitize_memory_basename`
  byte-identical between the r6 and r15 candidates» não tem NENHUM artefato na
  árvore — a cerimônia guarda só o `W179CLOSE.patch` final e os candidatos
  viveram em scratchpad; os registros r6 (cinco P2, nenhum sobre charset de
  basename) e r15 (P1 «Preâmbulo de papel atravessava até o systemMessage») não
  sustentam a claim por leitura; (b) a enumeração «(spaces, hyphens,
  concatenation, limits)» não bate com o registro real
  (`s335-ceremony-179close/rail-round-22.md:11-24`: «r15 espaços → r19 hífens →
  r20 camel/minúscula → r21 run-19 → r22 run-14»); (c) «closed only when the
  surface was removed» ao lado do nome da função sugere que a função saiu — ela
  EXISTE em `.claude/hooks/SessionEnd.py:656` e é chamada em `:958`; o que saiu
  foi o canal de nomes do systemMessage; (d) `PROTOCOL.md` hoje não cita
  nenhum nome de função (grep vazio) e é entregue a adopters que não podem
  verificar nada disso. Mitigação: `PROTOCOL.md` fica com UMA frase-ponteiro
  («Precedent and evidence: ADR-140-AMEND-1 §2»); o ADR §2.2 cita a cadeia do
  r22 VERBATIM do registro em disco, diz que o sanitizer permanece como gate
  interno testado, e ou anexa artefato para a byte-identidade r6/r15 ou a
  rotula como «medida na S352 sobre sombras não retidas» — ou a retira.
- **R-VP7** — Severity: MEDIUM — Escopo «in the same ceremony» é estreito demais
  sob o modelo v2.1 e diverge da regra já em vigor. Sob R2 um pack canônico tem
  2 rodadas: a janela para uma «segunda ocorrência na mesma cerimônia» é de uma
  rodada. Onde as classes voltam HOJE é entre packs: rescisão por R3 e
  sucessor re-arquitetado (`w4b-ci-matrix` → `w4b-gates-v2`), e a série r1/r2/r4
  do GA (mesma condição 63 por três textos). E a linha do `CLAUDE.md` §4 e a
  memória S352 dizem «2.ª ocorrência ⇒ cura estrutural» SEM limite de cerimônia
  — dois textos, dois escopos. Mitigação: definir «ceremony» no texto como a
  linhagem de UMA assinatura (todas as rodadas e packs, inclusive sucessores
  após rescisão, rumo ao mesmo sentinel); declarar que a recorrência entre
  assinaturas fica para a identidade persistente de achado da W2; manter a
  linha do `CLAUDE.md` como superset dogfood (não editar agora — ver R-VP2).
- **R-VP8** — Severity: LOW — Derivador (3.ª lane): em `--apply`, `proto.write_text(out)`
  acontece ANTES de `if adr_dst.exists(): return 2` ⇒ recusa deixa a árvore
  meio-aplicada (classe já curada no installer pelo PLAN-185: «pré-voa TODOS os
  destinos antes da primeira escrita» — 2.ª ocorrência da classe no repo, o que
  a própria W0 diz exigir cura estrutural); `--check-only` não verifica ausência
  do ADR nem `generate-adr-index.py --check`; `README.md.new` (39.791 bytes)
  não é produto de `--write` (que só emite `PROTOCOL.md.new` + `BASE.sha256`) e
  por isso envelhece à parte; escrita não atômica. Mitigação: pré-voo completo
  antes da 1.ª escrita, `--check-only` completo (ADR ausente, README em sincronia,
  paridade pt-BR, claims), `--write` deriva TODOS os payloads, tmp + rename.
- **R-VP9** — Severity: LOW — `check_protocol_semver_cascade.py` sonda
  `contains:Critical Rules` (`:219-221`) com `needle in text` case-sensitive
  (`:153-158`); `CLAUDE.md` tem ZERO ocorrências de «Critical Rules» (o heading é
  «## 4. Critical rules (dogfood mode)», `:80`); o teste usa fixture, não o repo.
  O Sync Impact Report da máquina vai dizer `CLAUDE.md Critical Rules:
  MISSING/DRIFT` na edição da W0 — advisory, fail-open, pré-existente.
  Mitigação: registrar no ADR §5 como falso DRIFT esperado e NÃO curar durante a
  cerimônia (allowlist do veredito é fechada); follow-up livre no probe
  (oráculo antes).

## Must-fix (blocking)

1. **Espelho pt-BR no escopo** (R-VP1): `PROTOCOL.pt-BR.md` recebe a mesma
   seção traduzida, via segundo payload do derivador (mesma âncora, única nos
   dois arquivos); a bateria do SIGN executa
   `python3 .claude/scripts/check_translations_drift.py --json` e exige
   `"drift": false`; o §4 do ADR troca a frase falsa sobre o espelho pelo fato
   (paridade estrutural BLOQUEANTE, espelho atualizado na mesma assinatura).
2. **Contagem de ADRs no escopo** (R-VP2): `CLAUDE.md:54` «198 ADRs» → «199 ADRs»
   pelo derivador, byte-neutro; bateria do SIGN roda
   `check-claude-md-claims.py` e `verify-counts.sh --no-tests` sobre a árvore
   APLICADA (ordem do `CLAUDE.md` §4: gate de corpus DEPOIS da última edição,
   sobre o staged). Escopo passa a 5 paths (dentro do teto v2 de ≤ 8).
3. **Item 3 honesto** (R-VP3): reescrever como obrigação de quem abre a rodada
   N+1, em MUST NOT, e acrescentar a linha de enforcement («checklist-enforced
   + lander condition; no blocking hook; W2 makes second occurrences observable
   in telemetry»); corrigir o §3 do ADR (W2/W3 não «tornam mecânico»; o gate
   mecânico é condição de lançador, mesma forma da R2, e nasce no toolkit do
   PLAN-188 — follow-up nomeado no §6).
4. **Semântica da aceitação** (R-VP4): no texto — autor escreve, Owner ratifica na
   assinatura (até lá PROPOSTA, cerimônia pode seguir); instâncias posteriores
   continuam registradas sob a aceitação; P0 ou Owner reabre; se a remoção
   exige paths fora do escopo assinado, a aceitação é interina e nomeia o
   follow-up. Sem isso, a «aceitação» é a saída barata que o plano diz não
   existir.
5. **Vocabulário e tetos** (R-VP5, R-VP7): «finding class» em todo o texto;
   substituir «no round ceiling» pela forma «introduces none of its own; R2/R3
   and DEBATE-SCHEMA §12.1 unchanged»; definir «ceremony» como linhagem de uma
   assinatura (sucessores após rescisão incluídos); disputa de classe pelo
   revisor conta como MESMA classe até o Owner decidir (fail-closed, na direção
   das guardas de input do repo); o ADR nomeia a R3 como a gêmea de nível de
   pack.
6. **Precedentes e claims do ADR** (R-VP6 + higiene): `PROTOCOL.md` fica com a
   frase-ponteiro; ADR §2.2 cita o `rail-round-22.md` verbatim e a permanência
   do sanitizer; byte-identidade r6/r15 com artefato, rotulada como sombra não
   retida, ou removida; §3 remove «already followed in the S353 night packs»
   (não verificável agora) ou aponta os registros; `debate_record`,
   `accepted_at` e `decided_by` são preenchidos NO SIGN a partir do resultado
   real do debate (hoje descrevem um `consensus.md` que ainda não existe); a
   linha da tabela §5 sobre `DEBATE-SCHEMA.md` diz ONDE vive a linha `Class:`
   de um achado de debate (`round-N/consensus.md`, aditivo sob §12.9) — o texto
   do PROTOCOL diz aplicar-se a «debate», a tabela diz que não há onde escrever.

## Nice-to-have (advisory)

1. Derivador (R-VP8): pré-voo de todos os destinos antes da primeira escrita;
   `--check-only` completo (ADR ausente, `generate-adr-index.py --check`,
   paridade, claims); `--write` emite também `README.md.new` via `--print`;
   tmp + rename. Uma rodada das lanes do lander sobre o derivador (R1: zero
   codex em instrumento).
2. Gramática mínima para a linha de classe, para ser greppável e consumível pela
   W2: `Class: property|surface — <nome curto>`; a «violação visível» vira
   `grep -c '^Class:'` contra o número de achados do registro.
3. Molde do prompt do rail (toolkit PLAN-188): pedir ao revisor que NOMEIE a
   classe que vê e DISPUTE a do autor quando divergir — o lado revisor da regra
   não cabe no `PROTOCOL.md` e sem ele a mitigação da pergunta 2 fica só no
   autor. Follow-up nomeado no ADR §6.
4. Ensaio do SIGN com os oráculos da CI que LEEM os arquivos patchados
   (`check_translations_drift.py`, `check-claude-md-claims.py`,
   `generate-adr-index.py --check`) — é a primeira edição de `PROTOCOL.md` na
   história pública (1 commit em 843; `9777a8d`), o caminho nunca foi exercido
   aqui («LAND verde ≠ CI verde»).
5. Probe do `check_protocol_semver_cascade.py` case-insensitive ou âncora em
   regex (R-VP9) — land livre, oráculo antes; fora desta assinatura.
6. Manter a rota SP-NNN para `receiving-review/SKILL.md` (oráculo 1) como já
   declarado no §4 do ADR; sem mudança.

## Unseen by the original plan

1. O par `PROTOCOL.md ↔ PROTOCOL.pt-BR.md` sob paridade ESTRUTURAL bloqueante
   (`translations-pairs.yaml` + `translations-drift.yml` job `structural-parity`);
   nem o plano nem a proposta o mencionam, e o ADR o descarta com uma premissa
   falsa.
2. Os dois gates de contagem de ADRs (`check-claude-md-claims.py` na CI e
   `verify-counts.sh` no molde do SIGN) e o teto de 40.000 bytes do `CLAUDE.md`
   (39.982 hoje) — o land de 3 paths aborta no próprio molde.
3. `PROTOCOL.md` nunca foi editado no repo público: o «Enforcement commit
   `a2986b8`» do ADR-140 não resolve aqui; o caminho semver-hook + paridade +
   contagem + ponteiro dos adopters roda pela primeira vez junto.
4. «classe» já tem dono na R2 (classe de artefato) e a R3 já é «cure a classe»
   ao nível de pack; o texto cria uma segunda regra com a mesma palavra e outro
   sentido sem dizê-lo.
5. Sob R2 (2 rodadas por pack canônico) a «segunda ocorrência na mesma
   cerimônia» tem janela de uma rodada; a recorrência que dói agora é entre
   packs/sucessores e entre assinaturas — fora do alcance do texto até a W2.
6. O probe case-sensitive do hook de cascata gera um `MISSING/DRIFT` falso em
   toda edição de `PROTOCOL.md` neste repo.
7. `_sanitize_memory_basename` continua no código; a frase do precedente
   convida à leitura oposta.

## What I would NOT change

1. **W0 sozinha, assinatura pequena** (Owner, decisão 6): mesmo com 5 paths fica
   dentro do teto v2 (≤ 8 paths, ≤ 400 linhas) e é a wave que corta horas.
2. **Definição «propriedade OU superfície, julgado pelo autor»** (decisão 7):
   operável, desde que a disputa do revisor tenha default fail-closed (MF-5).
   Não estreitar para «só propriedade».
3. **Nenhum teto, filtro ou dispensa por severidade** introduzidos pela W0 — os
   dados do corpus (validade 93/93/91 % por faixa de rodada) sustentam; só a
   REDAÇÃO precisa deixar de negar os tetos ratificados que existem.
4. **`status: ACCEPTED` no land com `authorization` = sentinel + `.asc`**
   (precedente ADR-164-AMEND-1): evita a degradação `PROPOSED > 30d` do
   `check-staleness.py:293` e uma segunda assinatura só para virar o status.
5. **AMEND-1 do ADR-140 e inserção logo após §Receiving review**: é a casa certa
   (lado de receber → lado de curar), mesmo modelo de enforcement.
6. **Derivador com `BASE.sha256` e recusa por seção já presente**: a forma
   correta contra baseline envelhecido e dupla aplicação — só completar, não
   trocar.
7. **Skill `receiving-review` fora desta assinatura** (rota SP-NNN).

## Respostas às 6 perguntas da proposta

1. **Reduz detecção?** O texto em si, não. Dois pontos podem reduzir por
   leitura: a «aceitação» sem efeito definido sobre a 3.ª ocorrência (MF-4) e a
   parada do item 3 lida como «a classe deixa de ser revisada» (MF-3). Com as
   duas curas de redação, zero redução; nenhuma cura legítima fica proibida — a
   troca de arquitetura fora do escopo assinado vira aceitação interina +
   follow-up, não um exemplo a mais.
2. **«Mesma classe» é operável?** Sim, por causa da linha `Class:` na 1.ª
   ocorrência (a 2.ª vira comparação contra registro, não julgamento
   retrospectivo). A porta «tudo é outra classe» fecha com o default de
   disputa fail-closed e com o revisor nomeando a classe que vê (toolkit).
3. **Item 3 promete mecanismo?** Sim — e W2/W3 também não o entregam. Redação
   honesta: obrigação de quem abre a rodada + linha de enforcement + gate
   mecânico nomeado como condição de lançador (forma da R2) no toolkit.
4. **v2.1:** R1 sem conflito (W0 governa a cura; R1, os bytes que vão a codex).
   R2: colisão de palavra + «no round ceiling» contradiz — MF-5. R3: é a gêmea
   de pack; nomear. Efeito colateral: sob R2 a janela intra-cerimônia é curta;
   a linhagem (sucessores) tem de contar.
5. **Sync Impact obrigatório NESTA assinatura:** `PROTOCOL.pt-BR.md` (paridade
   bloqueante) e `CLAUDE.md:54` (contagem, byte-neutro). NÃO mudar:
   `DEBATE-SCHEMA.md` (aditivo, §12.9 tolera a linha `Class:` em
   `consensus.md`; só o ADR precisa dizer isso), `PLAN-SCHEMA.md`,
   `docs/HONEST-LIMITATIONS.md` (grep: nenhuma claim sobre rodadas ou tetos;
   só as linhas 88-120 do pair-rail cross-vendor), `docs/PROTOCOL-SEMVER.md`,
   `receiving-review/SKILL.md` (SP-NNN). Esperado e não-curável agora: o
   `MISSING/DRIFT` falso do item [1] do hook de cascata.
6. **Estimativas** — abaixo.

## Estimativas (ADR-081)

| Item | budget_tokens | budget_sessions | context_risk | external_wait |
|---|---|---|---|---|
| MF-1 espelho pt-BR + 2.º payload + paridade na bateria | 20-35k | 0 extra (na sessão que prepara o SIGN) | low | none |
| MF-2 contagem `CLAUDE.md` byte-neutra + gates na bateria | 5-10k | 0 extra | low | none |
| MF-3 + MF-4 + MF-5 redação do texto assinado | 15-25k | 0 extra | low | none |
| MF-6 precedentes → ADR + higiene de claims | 8-15k | 0 extra | low | none |
| Rail sobre os bytes canônicos re-derivados (R2: ≤ 2 rodadas) | 30-60k | 0-1 | medium | assinatura do Owner (manhã) |
| **W0 total re-trabalhada** | **80-145k** | **1** | **medium** | **Owner GPG** |
| NH-1 derivador (pré-voo, `--check-only` completo) | 10-20k | 0 extra | low | none |
| NH-3 molde do prompt do rail (toolkit PLAN-188) | 60-120k | 1-2 | high (toca o toolkit em construção) | none |
| NH-5 probe do hook de cascata (livre) | 5-10k | 1 | low | none |
| SP-NNN `receiving-review` | 20-40k | 1 | low | none |
