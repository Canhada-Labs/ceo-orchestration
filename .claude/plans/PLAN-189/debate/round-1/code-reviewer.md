---
round: 1
archetype: Staff Code Reviewer
skill: code-review-checklist
agent_persona: Code Reviewer (Staff, merge VETO holder)
generated_at: 2026-09-16T00:50:00Z
reviewed_artifacts:
  proposal: .claude/plans/PLAN-189/debate/round-1/proposal.md
  payloads_pinned_sha256:
    ADR-140-AMEND-1-cure-the-class.md.new: 211865255ec15845cb4aea691ba6685588950f9b245b6e1730ece53be874478a
    PROTOCOL.md.new: 27a21e05c103e0898803d9cdbe86cdb0136e056c381b692a3207547cae3471fe
    README.md.new: 05b6ee7820f0c9e62eef7d216a0c5ed7efaff1a01fae850d2513c7143c5a8930
    protocol-section.md: c3bb09dc9fcb76caa8b1207f053b070514c551c2e64835312db0d60ed4a1e565
  base_pinned: PROTOCOL.md 16a619d0077bb785ba9e02d8290514850410c5c55f5ac906dbb5fe754997f74f (bate com w0/payloads/BASE.sha256)
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- A W0 põe no PROTOCOL.md a regra que ataca a causa MEDIDA das cerimônias
  longas (cura por enumeração). A espinha está certa: nada no texto reduz
  detecção — verifiquei os 3 itens adversarialmente e não achei caso em que
  uma cura legítima fique proibida ou um achado deixe de ser registrado.
- Forte: definição operável de classe (propriedade OU superfície, julgado
  pelo autor POR ESCRITO), janela «same ceremony» cobrindo achados irmãos na
  mesma rodada, escopo mínimo de 3 paths, ADR-AMEND pareado com enforcement
  declarado, MINOR bump correto. Payloads batem byte a byte com o texto
  criticado (verifiquei por continência, não por resumo).
- Fraco: o texto ASSINADO carrega dois claims factuais que o disco não
  sustenta como escritos — a enumeração parentética do precedente r22
  diverge do registro real, e os números do ADR §2 («sources on the
  record») não têm fonte re-contável em nenhum arquivo versionado. Num repo
  cuja marca é auditabilidade, isso é exatamente o defeito que os re-passes
  do GA transformaram em NO-GO por TEXTO.

## Risks

- **R-CR1 — HIGH — precedente enumerado diverge do registro que cita.**
  Texto assinável: «five rounds on one basename sanitizer (spaces, hyphens,
  concatenation, limits)». Registro real
  (`.claude/plans/PLAN-179/s335-ceremony-179close/rail-round-22.md`, achado 1):
  «5ª rodada da MESMA classe (r15 espaços → r19 hífens → r20 camel/minúscula
  → r21 run-19 → r22 run-14-que-o-validador-permite)». «concatenation» não
  existe no registro; «camel/minúscula» ficou de fora; são 5 rodadas para 4
  rótulos. Qualquer auditor que abrir o rail-round-22.md vê a divergência no
  texto canônico permanente. Lição já paga (S351, GA r1/r2/r4): enumerar
  sítios em material assinado não converge — declarar a classe pela FORMA.
  Mitigação: remover o parêntese ou copiar a cadeia exata do registro.
- **R-CR2 — HIGH — números do ADR §2 sem fonte re-contável em disco.**
  O ADR-140-AMEND-1 §2 afirma «measured, sources on the record» e cita
  r1-r3 93 %, r4-r7 93 %, r8+ 91 %, 178 REAL/VERIFICADO vs 13
  REFUTADO/PUSHBACK. Verifiquei: esses números não existem em nenhum arquivo
  versionado fora do triângulo plano/proposal/payload, nem nas duas memórias
  citadas (`reference-rail-configuration-evidence-s352` traz evidência
  externa — o único «91» lá é o 76,91 % de Choi et al.). Os dados primários
  (rail-round-*.md do PLAN-179) existem, mas a CONTAGEM e o método não estão
  registrados — o claim não é re-executável. Regra da casa: claim MEDIDA
  precisa de data + substrato. Mitigação: must-fix 2.
- **R-CR3 — MEDIUM — item 3 promete granularidade que a operação não tem.**
  «no further round opens on that class»: rodada de rail/debate abre sobre
  um CANDIDATO, não sobre uma classe. O mecanismo real está no ADR §3 («the
  lander treats a record without a structural cure or a declared acceptance
  as a blocking finding» — regra de processo hoje; W2/W3 tornam mecânico),
  mas o leitor do PROTOCOL.md não vê nada disso — e PROTOCOL.md é o arquivo
  que os agentes leem no Gate 1; o ADR não é. Responde à pergunta 3: o par
  texto+ADR é honesto; o texto sozinho sobre-promete uma frase.
- **R-CR4 — MEDIUM — pack montado em paralelo ao round + pin de base
  incompleto.** `PROTOCOL.md.new` mudou de forma entre minhas duas leituras
  na mesma revisão (diff `448a449,484` → `445a446,471`+`446a473,482`;
  conteúdo final verificado idêntico por continência). `BASE.sha256` pina só
  PROTOCOL.md; `.claude/adr/README.md` (destino pré-existente, auto-gerado,
  contador 198→199) não tem base pinada — um land livre que adicione um ADR
  antes da assinatura deixa o `README.md.new` STALE em silêncio. Lição S328:
  o baseline de um pack à espera de assinatura é o hash do vivo; o land de A
  invalidou o pack D duas vezes. Mitigação: must-fix 4 + consensus pina os
  sha256 acima.
- **R-CR5 — LOW — «no round ceiling» pode ser lido como revogação implícita
  de R2 v2.1.** R2 («teto por classe», Owner S347/S348) é regra de operação
  ratificada e não vive no PROTOCOL.md — não há autocontradição interna. Mas
  um leitor futuro pode tomar o blockquote por revogação. Responde à
  pergunta 4: R1 (zero codex em land livre) e R3 (>20 registros) não
  conflitam; com a W0 valendo, R2 vira segunda linha de defesa quase
  redundante — coexiste, mas merece 1 frase ou decisão explícita do Owner.
- **R-CR6 — LOW — espelho pt-BR diverge mais uma seção.**
  `PROTOCOL.pt-BR.md:408` tem «## Receiving review»; a W0 insere a seção só
  no inglês. Política declarada no cabeçalho cobre (English wins, last sync
  2026-06-11), e o ADR §4 já declara o não-update — falta só o Sync Impact
  Report do commit listar o espelho como intocado-por-política.

## Must-fix (blocking)

1. **Exatificar ou des-enumerar o precedente r22 no texto do PROTOCOL.md.**
   Ou o parêntese reproduz a cadeia exata do rail-round-22.md (espaços →
   hífens → camel/minúscula → run-length ×2), ou cai — «five rounds on one
   basename sanitizer, closed only when the surface was removed» já carrega
   toda a doutrina. Custo: ~2-3k tokens (editar payload + proposal + re-diff),
   mesma sessão.
2. **Dar substrato re-contável aos números do ADR §2.** Commitar a análise
   que produziu 93 %/93 %/91 % e 178/13 como artefato do plano (ex.:
   `.claude/plans/PLAN-189/w0/evidence-round-validity.md` com método,
   data, e a contagem por rodada apontando os rail-round-*.md de origem) OU
   reescrever §2 para afirmar apenas o que o disco sustenta (o
   rail-round-22.md sustenta sozinho o precedente central). «Sources on the
   record» só pode ficar se o record existir. Custo: ~4-6k tokens se a
   análise da lane Codex ainda estiver recuperável nesta sessão; senão,
   reescrever §2 custa ~2k.
3. **Alinhar o item 3 com o mecanismo real.** Trocar «and no further round
   opens on that class until the record carries one of the two» por
   formulação que nomeie quem bloqueia (o lander/fechamento da cerimônia,
   como o ADR §3 já descreve) — ou acrescentar ao blockquote meia-frase de
   enforcement-status («Process rule today; PLAN-189 W2/W3 make it
   mechanical»). Precedente da casa: o spawn-protocol do CLAUDE.md distingue
   o que o gate «mechanically BLOCKS today» do que é doutrina. Custo: ~1-2k
   tokens.
4. **Pinar TODAS as bases pré-existentes em `BASE.sha256`** (PROTOCOL.md E
   `.claude/adr/README.md`) e regenerar `README.md.new` via
   `generate-adr-index.py` na hora da cerimônia, não à mão — o
   `validate.yml:134` roda `--check` (hoje verde com 198 ADRs; qualquer ADR
   novo entre agora e a assinatura invalida o payload em silêncio). Custo:
   ~1k tokens no script de cerimônia.
5. **Bateria da cerimônia.** O `OWNER-189-W0-SIGN.sh` citado no frontmatter
   do ADR ainda não existe. Quando nascer: `check-ceremony-script.py` na
   bateria (lição S352 — main vermelho por pular exatamente isso),
   `generate-adr-index.py --check` pós-aplicação, governance COMPLETO (não
   `--fast`), e `cmp` do bloco aplicado contra `protocol-section.md`. Custo:
   dentro dos ~15-25k tokens já esperados para o script; total W0 ≤ 1 sessão
   de CEO + external_wait (janela de assinatura do Owner).

## Nice-to-have (advisory)

1. Uma frase registrando a coexistência com R2 v2.1 (teto por classe) — ou
   levar ao Owner a decisão de aposentá-la quando a W0 entrar (é dele, não
   nossa).
2. Uma frase dando ao revisor o direito de contestar a classificação: «a
   reviewer may raise misclassification of a class as a finding against the
   record». Fecha a porta «tudo é outra classe» da pergunta 2 sem tirar o
   julgamento do autor.
3. Sync Impact Report do commit lista `PROTOCOL.pt-BR.md` como
   intocado-por-política (English wins).
4. Quando o follow-up do skill `receiving-review` (ADR §4) abrir, que ganhe
   nome no padrão `PLAN-189-FOLLOWUP-<slug>` (PLAN-SCHEMA §1.4), não fique
   como menção solta.

## Unseen by the original plan

1. **Dois achados da mesma classe na MESMA rodada** contam como 1.ª e 2.ª
   ocorrência simultâneas — «same ceremony» cobre, e o efeito (cura
   estrutural exigida já na primeira cura quando o revisor entrega dois
   exemplos) é desejável. Nem o plano nem a proposal discutem o caso; vale
   um exemplo no registro-modelo para ninguém «resolver» relaxando a leitura.
2. **«CI» como origem de achado** no blockquote: a segunda falha do MESMO
   gate numa cerimônia (ex.: flake) passa a exigir cura estrutural ou
   aceitação nomeada — consequência forte e provavelmente intencional
   (flakes deixam de ser re-tentados ad infinitum), mas não declarada. Uma
   linha no ADR evita a surpresa.
3. **Higiene do round:** os payloads derivados foram (re)escritos DURANTE a
   crítica. Não é violação (o objeto criticado é o texto da proposal, e
   verifiquei convergência byte a byte no estado final), mas o consensus
   deve pinar por sha256 o que cada crítico viu — esta crítica pina no
   frontmatter.

## What I would NOT change

- **A definição de classe** (propriedade OU superfície, julgado pelo autor,
  escrito no registro). Operável, auditável, e qualquer taxonomia fechada
  mataria a regra em burocracia. O julgamento visível é contestável — é o
  suficiente.
- **A janela «same ceremony»** para a 2.ª ocorrência (não «same round»).
- **O escopo mínimo da assinatura** (3 paths, W0 sozinha — decisão 6 do
  Owner, verificada verbatim em
  `PLAN-186/debate/owner-decisions-S353.md`).
- **O par texto+ADR-AMEND com `ACCEPTED`-at-land** e ratificação pelo
  `.asc` — precedente ADR-194; o `numbering_note` e o modelo de enforcement
  espelham o ADR-140 base corretamente.
- **MINOR bump**: aditivo, não toca Plan→Debate→Execute, vetos nem 3-strike
  (`docs/PROTOCOL-SEMVER.md` tabela). Emenda pareada presente por
  construção.
- **A posição da inserção**: verifiquei no payload — seção contida byte a
  byte, ordem Receiving review < Cure discipline < 3-Strike policy, delta de
  1.963 bytes, nenhuma outra mudança no arquivo.
- **A frase «Enumerating instances is not a cure; it is how a class stays
  open»** — é a tese inteira em uma linha; não diluir.

## Answers to the six questions (free-form)

1. **Reduz detecção?** Não encontrei caso. O item 2 não proíbe cura alguma —
   exige cura melhor OU aceitação escrita; a rota de escape («why removal is
   not possible» + risco nomeado) mantém legítima qualquer cura pontual
   inevitável. O item 3 bloqueia fechamento/gasto de rodada, nunca o
   registro de um achado: um achado novo da classe vira violação contra o
   REGISTRO, que é blocking — detecção preservada.
2. **«Mesma classe» é operável?** Sim, com a mitigação do nice-to-have 2. O
   risco «tudo é outra classe» é real mas auto-limitado: a classificação é
   escrita, datada e contestável; o precedente r22 (espaços/hífens/case/
   limites = UMA classe) é o exemplo normativo que calibra a régua.
3. **Item 3 promete mecanismo inexistente?** Em parte — ver R-CR3/must-fix 3.
   O ADR é honesto; o texto do protocolo sozinho não.
4. **Interação com v2.1:** R1 e R3 sem conflito. R2 (teto por classe)
   coexiste com tensão de leitura — ver R-CR5/nice-to-have 1.
5. **Sync Impact desta assinatura:** nenhum artefato a jusante PRECISA mudar
   além dos 3 do escopo. `CLAUDE.md` §4 já carrega a linha S352 (vira
   referência — correto não editar: cache-stable, closeout-only);
   PLAN-SCHEMA/DEBATE-SCHEMA sem mudança obrigatória (não existe schema de
   rail-round record em nenhum dos dois — verifiquei por grep; a linha
   `Class:` nasce definida pelo próprio PROTOCOL.md, e o DEBATE-SCHEMA §4
   permite seções livres); skill `receiving-review` é follow-up nomeado;
   `docs/HONEST-LIMITATIONS.md` intocado (a regra não altera as limitações
   do rail). O espelho pt-BR entra no relatório como intocado-por-política.
6. **Estimativas (ADR-081):** must-fix 1-3 ≈ 4-8k tokens, 0,1 sessão;
   must-fix 4-5 dentro do custo já planejado do script de cerimônia
   (~15-25k tokens). Round 2 do debate, se o CEO re-passar o texto após as
   curas: ~50-70k tokens, 0,3 sessão. Total W0: ≤ 1 sessão de CEO.
   External_wait (único prazo humano): a janela de assinatura do Owner.
   Nenhuma «semana» recebida de fonte externa havia a converter.

## Verification log (evidence)

- Seção proposta == `protocol-section.md` payload: diff byte a byte, idêntico.
- Seção contida em `PROTOCOL.md.new`: True; ausente do vivo: True; ordem
  correta: True; delta 1.963 bytes; nenhum outro hunk.
- `BASE.sha256` == sha256 do PROTOCOL.md vivo hoje: confere (16a619d0…).
- `rail-round-22.md` do PLAN-179: cadeia real da classe difere da paráfrase
  assinável (R-CR1); confirma «5.ª rodada» e morte por remoção do canal.
- Decisões 6/7/8 do Owner: verbatim em `owner-decisions-S353.md`, batem com
  a proposal.
- `generate-adr-index.py --check`: VERDE hoje (198); wired em
  `.github/workflows/validate.yml:134`.
- Frontmatter `adr_id:` no payload: padrão dos AMENDs existentes
  (ADR-110-AMEND-1 idem); o gerador deriva id do filename e lê
  `title:`/`status:` — payload compatível.
- Números 93/93/91 e 178/13: ausentes de todo arquivo versionado fora de
  plano/proposal/payload e das memórias citadas (R-CR2).
- Oráculo `--is-canonical` para este arquivo: `0` (não-canônico) antes da
  escrita.
