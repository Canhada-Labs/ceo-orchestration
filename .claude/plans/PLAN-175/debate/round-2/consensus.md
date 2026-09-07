---
plan: PLAN-175
round: 2
rounds_synthesized: [round-1, round-2]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "§2.1 perna 0 — a elegibilidade como escrita zera o conjunto de candidatas (medido: core=42, candidatas=0); a perna muda de ARQUITETURA (exclusão por canal-sem-instrumento REALMENTE usado, ou MANTER-override restrito ao Gate 2 + piso de VETO), nunca ganha mais uma exceção"
  - "§2.1 perna 1 — `min_window_coverage_days = 90` contra os 16,6 dias do §4:182 devolve RECUSA para toda skill; o número volta ao Owner com a razão, e o §8:467 deixa de registrar C1 («janela de 90 dias inexistente») como CURADO pela própria guarda de 90 dias"
  - "§2 saídas — a regra declara sua posição sobre ledger não-íntegro: `chain_status: NOT INTACT` é RECUSA, ou o plano registra o risco aceito por escrito (o leitor nomeado no §1 reporta `hmac_mismatch` hoje)"
  - "§4.4 (plan:282-285) — a premissa «o CLAUDE.md deste projeto manda operar em português» é FALSA no HEAD; ou vira fração MEDIDA de consultas pt na janela, ou desce de «regressão medida» para hipótese, e a AC-1.4 acompanha"
  - "§5 W2 + §1 passo 5 — ordem das ondas: W4 (contagem derivada) precede W2, ou a AC-2.2 é reescrita para o patch de arquivamento carregar as superfícies derivadas; e a W2 ganha decomposição (1 SKILL.md + 8 documentos de produto + possivelmente `verify-counts.sh` = ~10 caminhos em DOIS regimes de cerimônia, contra o teto de 8)"
  - "§5 W0/W1 + §6:445-446 — AC-0.6 edita `.claude/hooks/_lib/rag_router.py`, que o oráculo responde CANÔNICO (1): ou o rótulo «pacote LIVRE» cai, ou a AC-0.6/AC-1.6 saem da primeira sessão"
  - "§5 AC-3.3 — o `Check:` não exercita perna nenhuma: `smoke-install.sh` não parseia argv (`:17 TARGET=\"${1:-}\"`, `:34 --profile core,frontend` fixo), então a AC-3.3 roda a MESMA suíte da AC-3.2 e ainda faria `mkdir` de um diretório `--profile` na raiz"
  - "§5 AC-1.4 — o `Check:` (`grep -n` sem `-r` sobre `.claude/plans/PLAN-175/decisions/`, diretório inexistente) responde «não» para sempre; o gate que segura a Fase 1 precisa de caminho de registro, dono, conjunto fechado e critério de morte"
  - "§5 AC-0.5/AC-1.3 — a sonda `p1/probe-retrieval-language-gap.py` tem ZERO parsing de argv: os flags `--require-mode`/`--pairs`/`--json` são engolidos e os Checks ficam VERDES sobre a sonda NÃO corrigida"
  - "§5 AC-1.1, AC-2.2, AC-2.3, AC-4.1, AC-4.4 (e AC-0.1, AC-1.3) — invocações nuas sem asserção: ficam vermelhas por crash, nunca por resposta errada (a classe C6 que o round 1 curou); a AC-2.3 usa o comando IDÊNTICO ao da AC-2.2, sem discriminar «restaurou» de «nunca arquivou»"
  - "§5 AC-4.2 — asserta a COR do gate embora `rule_matches_by_doc` exista (`verify-counts.sh:789,795`, exportado no `--json` em `:1258`)"
  - "§9 — o volume do orçamento é refutado pelo instrumento que o próprio §9 imprime (320-960 turnos de subagente orçados contra 49.965 medidos na MESMA janela de 3 dias); o `assento` medido é Fable 5.1, não o Opus 5 declarado no `tier_mix_estimate`; as figuras ganham âncora de data e o espalhamento de 51,7% diz qual termo carrega"
  - "§Progress log:528 — a linha «PENDENTE de ratificação do Owner» do `external_wait: none` está envelhecida (ratificado 2026-09-06 23:5x); um campo que decide sequenciamento não pode ter duas leituras"
  - "§5 AC-1.7 — «re-medição aos 30 dias» dentro de um plano cujo frontmatter diz `external_wait: none` e `eta_calendar: mesmo-dia a D+1` e cujo §6:431 jura não haver segundo lugar afirmando espera"
synthesized_at: 2026-09-07T00:35:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-175 — consenso do round 2

Três críticos, três `ADJUST`, 13 achados marcados bloqueantes somados. Nenhum
pediu `REJECT`. Este round é **coerência de DESENHO** sobre a versão reescrita
em `35aa149`: certifica coerência interna do TEXTO, nunca verdade externa, e
não autoriza nada — o flip para `executing` é decisão do Owner (item 4.10).

**O que a revisão realmente curou** (verificado, e registrado antes das
críticas para não enterrar o crédito): a perna 0 de elegibilidade existe
(§2.1), o controle de não-autofagia é AC bloqueante com controle POSITIVO ao
lado (AC-0.2/AC-0.3, e a AC-0.3 asserta código de saída ≠ 0 — não é invocação
nua), o leitor da telemetria está nomeado com invocação completa (§1 passo 1),
o alvo `42 → ~25` saiu da regra, e 25 ACs carregam `Check:`. Reproduzi o censo
do §4.7 (10 arquivos com o literal `166 skills`, 8 deles documentos de produto)
e confirmei que a AC-0.6 pode ficar VERMELHA hoje: o literal
`PLAN-097-FOLLOWUP-rag-router-wireup` está vivo em
`.claude/hooks/_lib/rag_router.py:32`.

**O que este round descobriu:** as DUAS pernas NOVAS que a revisão adicionou
para curar o round 1 quebram o experimento por construção. Essa é a segunda
rodada consecutiva em que a regra de poda cai — e a regra de parada
pré-registrada da própria W0 («se o controle não ficar verde em duas rodadas, a
regra muda de ARQUITETURA em vez de ganhar mais uma exceção») é exatamente o
gatilho que se aplica aqui.

---

## Consensus findings (2+ críticos, cada um verificado em disco)

### C1 — P1 — o `Check:` da AC-3.3 é inerte: as duas pernas do teste-mestre medem a mesma coisa (Critic-A R-VP1, Critic-B F6, Critic-C R-QA4)

Verificado em `scripts/tests/smoke-install.sh`: `:17` é `TARGET="${1:-}"` (o
primeiro posicional é o diretório-alvo), `:25` faz `mkdir -p "$TARGET"`, `:34`
chama o installer com `--profile core,frontend` **fixo**; `:311`, `:398` e
`:453` fixam `--profile core`. Não há `case`/`shift`/parser de flags no arquivo.

Consequências, todas mecânicas: (a) `bash scripts/tests/smoke-install.sh
--profile core,<domínio>` NÃO passa perfil nenhum ao installer — a AC-3.3 roda
byte-a-byte a mesma suíte da AC-3.2; (b) a perna que o C5 do round 1 mandou
testar — o caminho que lê `.claude/skills/domains/<parte>`, o que o P3 remove —
nunca é exercida por AC nenhuma; (c) o comando ainda criaria um diretório
literalmente chamado `--profile` na árvore. O plano chama a AC-3.3 de «a que de
fato regride» (`:406`): hoje ela não regride nada.

### C2 — P1 — `min_window_coverage_days = 90` devolve RECUSA para tudo e re-impõe o calendário que o §0 declara caído (Critic-B F1, Critic-C R-QA2)

Verificado: a guarda está em `:119-120`; a cobertura medida da família de
auditoria está em `:182` — **16,6 dias**. `16,6 < 90` ⇒ pela tabela do §2.2 a
saída é `RECUSA` para toda skill, e só deixaria de ser por volta de
2026-11-19. Isso colide frontalmente com `external_wait: none` (`:16`) e
`eta_calendar: "mesmo-dia a D+1"` (`:17`).

O sintoma de desenho mais grave é o efeito sobre os CONTROLES, e ele é da
classe canônica «controle que reproduz a APARÊNCIA e não o MECANISMO»: com
`RECUSA` dominante, a AC-0.2 (que exige `MANTER`) fica inalcançável, e a AC-0.3
— o controle positivo, que exige saída ≠ 0 com a perna 0 DESLIGADA — fica verde
**pela guarda de denominador**, não pela remoção da proteção que ela pretende
falsificar. O mesmo vale para a AC-0.4 (`--force-empty-telemetry`), que deixa
de discriminar do run normal.

Verificado também o auto-fechamento: `:467` registra o consenso C1 do round 1
(«janela de 90 dias inexistente») como CURADO por «guarda
`min_window_coverage_days` no §2.1» — isto é, a cura declarada do achado «a
janela de 90 dias não existe» é uma guarda de 90 dias.

### C3 — P1 — o `Check:` da AC-1.4 nunca pode ficar verde, e ele é o gate da Fase 1 (Critic-A R-VP4, Critic-B F11, Critic-C R-QA5)

Verificado em duas pernas: `ls .claude/plans/PLAN-175/` devolve apenas `debate`
e `p1` — não existe `decisions/`; e `grep -n` **sem `-r`** sobre um diretório
não casa nada por construção. Executado: `grep -n "decisao-b"
.claude/plans/PLAN-175/decisions/` ⇒ `No such file or directory`, rc=2. A
AC-1.4 é `[P0]` e é o item que segura a Fase 1 (`:374`); um gate cujo
verificador responde «não» para sempre não é gate, é bloqueio.

### C4 — P2 — Checks que imprimem sem asserir reintroduzem a classe C6 que o round 1 curou (Critic-A R-VP6, Critic-C R-QA8)

Verificado por leitura dos `Check:`: AC-0.1 (`:350`), AC-1.1 (`:369`), AC-1.3
(`:373`), AC-1.6 (`:381`), AC-2.1 (`:389`), AC-2.2 (`:391`), AC-2.3 (`:393`),
AC-4.1 (`:418`) e AC-4.4 (`:424`) são invocações que saem 0 sempre que a
ferramenta funciona — ficam vermelhas por CRASH, nunca por resposta errada. O
contraste está no mesmo arquivo e prova que o autor sabe fazer: a AC-0.3
(`:354`) asserta «sai com código diferente de 0» e a AC-0.4 (`:356`) asserta o
literal `"verdict": "RECUSA"`.

Caso particular nomeado pelo Critic-C e confirmado: a AC-2.3 («restauração
testada») usa o comando IDÊNTICO ao da AC-2.2 (`bash
.claude/scripts/local/verify-counts.sh`), sem nada que distinga «arquivou e
restaurou» de «nunca arquivou» — as duas metades do teste de restauração são o
mesmo verde. O controle numérico «166 → 165» está enunciado em prosa e ausente
do comando.

### C5 — P3 — `external_wait` ratificado no mundo, `PENDENTE` no texto (Critic-A R-VP7, Critic-B F12)

Verificado: `:16` diz `external_wait: none`; `:431` afirma «não há segundo lugar
no corpo que afirme espera»; `:528` ainda diz «**PENDENTE de ratificação do
Owner**». A ratificação ocorreu em 2026-09-06 23:5x. Um campo que decide
sequenciamento com duas leituras no mesmo arquivo é defeito de coerência,
mesmo sendo cura de uma linha.

---

## Single-agent insights kept (verificados por mim; entram como must-fix)

### K-A — P1 — a perna 0 zera o conjunto de candidatas: `ARQUIVAR` é inalcançável e a W2 abre vazia (Critic-C R-QA1)

**Reproduzi independentemente.** Censo por limite de palavra do nome de cada
skill core sobre a união de `CLAUDE.md` + `.claude/team.md` +
`.claude/frontend-team.md` + `.claude/commands/*.md` + `.claude/agents/*.md` —
os quatro canais que o §2.1 declara excludentes:

```
core= 42
named_by_perna0= 42
candidates_after_perna0= 0
not_named= []
```

Nenhuma skill core sobrevive à perna 0. Logo o veredito `ARQUIVAR` é
inalcançável por construção, a lista da AC-2.1 é vazia, e a W2 — **o único
pacote canônico do plano, o que pede assinatura do Owner** — não tem entrada.
Guardo este como o achado mais consequente do round: ele não é um `Check:`
errado, é o experimento central sem sujeito. É de um crítico só, e por isso o
verifiquei antes de promovê-lo; a evidência acima é minha, não dele.

Vale registrar a simetria: a perna 0 foi adicionada para curar K1 do round 1 (a
regra arquivava `ceo-orchestration`). Ela cura — e leva junto as outras 41. A
cura da cura não é mais uma exceção: é trocar a arquitetura da perna (por
exemplo, excluir só o canal que é comprovadamente ALCANÇADO sem instrumento, ou
transformar a perna num `MANTER`-override restrito ao Gate 2 e ao piso de VETO,
que é exatamente o conjunto que a AC-0.2 protege).

### K-B — P1 — W0/W1 são declarados «pacote LIVRE», mas a AC-0.6 edita caminho CANÔNICO (Critic-C R-QA3)

Verificado com o oráculo: `python3 .claude/hooks/check_canonical_edit.py
--is-canonical .claude/hooks/_lib/rag_router.py` ⇒ `1` (canônico). O literal que
a AC-0.6 manda remover está nesse arquivo (`:32`). O §6 (`:445-446`) afirma «Só
W0, W1 e W4 são pacotes integralmente livres». As duas afirmações não coexistem:
ou o rótulo da W0 cai, ou a AC-0.6 sai da primeira sessão. Isso importa duplo
sob a regra da noite: um pacote canônico consome assinatura e teto de rodadas.

### K-C — P1 — a premissa que PROÍBE a Fase 1 é falsa no HEAD (Critic-A R-VP2)

Verificado: `grep -rniE "portugu" CLAUDE.md PROTOCOL.md .claude/team.md
.claude/frontend-team.md .claude/skills/core/ceo-orchestration/SKILL.md`
devolve **exatamente uma linha** — `PROTOCOL.md:3`, um ponteiro para o espelho
pt-BR que declara o inglês como fonte de verdade. `CLAUDE.md`: zero ocorrências.

O plano afirma em `:282-284` que «o `CLAUDE.md` deste projeto manda operar em
português», e é essa frase que converte uma tabela N=8 em «**regressão
medida**» e proíbe ligar a Fase 1 (`:284-285`). A tabela N=8 em si está
honestamente rotulada como limite (o round 1 pediu isso e foi atendido); o
defeito é a premissa que a promove a proibição.

### K-D — P1 — `verify-counts` é BIDIRECIONAL: a AC-2.2 é vermelha por construção na ordem declarada (Critic-A R-VP3)

Verificado em `.claude/scripts/local/verify-counts.sh:25-27` («The check is
BIDIRECTIONAL (a doc number that disagrees with live fails) and CROSS-FILE») e
`:31` (`skills (total) … exact (166)`). Censo reproduzido: 10 arquivos fora de
`.claude/plans/` carregam o literal, 8 deles documentos de produto
(`CHANGELOG.md`, `README.md`, `README.pt-BR.md`, `CLAUDE.md`,
`docs/GUIA-COMPLETO.md`, `docs/GUIA-COMPLETO.pt-BR.md`, `docs/FAQ.md`,
`npm/README.md`).

Arquivar UMA skill move o vivo de 166 para 165 e derruba os 8 documentos. O
`Check:` da AC-2.2 é `bash verify-counts.sh` — vermelho no instante em que a
AC-2.2 faz o que promete. A W4, que é a onda que deriva as contagens, é a
ÚLTIMA no §5 e o passo 5 no §1. **W4 é pré-requisito da W2, e a ordem declarada
é a inversa.**

### K-E — P1 — a telemetria de todo o §4 vem de uma cadeia que o leitor NOMEADO reporta como não-íntegra (Critic-B F4)

Rodei a invocação que o §1 nomeia:

```
python3 .claude/scripts/skill-health.py --include-rotated --since all --json
⇒ "chain_status": "NOT INTACT: status=tamper reason=hmac_mismatch — treat this
   report's telemetry as potentially tampered (advisory only; ...)"
```

O plano nunca cita o estado da cadeia, e a decisão que sai dessa evidência
(`ARQUIVAR`) é edição canônica com assinatura. A regra tem três saídas e uma
delas já é `RECUSA` por amostra insuficiente; a coerência pede que ela declare
sua posição sobre amostra **não-íntegra** — seja `RECUSA`, seja risco aceito por
escrito. Não estou afirmando adulteração: estou registrando que o instrumento
que o plano elegeu se auto-declara não confiável e o plano não responde.

### K-F — P2 — a sonda não parseia argv: AC-0.5 e AC-1.3 podem ficar VERDES sobre a sonda NÃO corrigida (Critic-C R-QA7)

Verificado: `grep -cE 'argv|argparse|require-mode|--pairs'
.claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py` ⇒ `0`. Os Checks
passam `--require-mode tfidf`, `--pairs 30` e `--json` a um script que os
ignora em silêncio. É a classe que o próprio §4.4 invoca («o instrumento exige
o mesmo escrutínio adversarial que o sujeito») aplicada ao plano: os ACs que
mandam corrigir a sonda são verificados por comandos que a sonda ANTIGA também
satisfaz.

### K-G — P2 — o orçamento é refutado pelo instrumento que o próprio §9 imprime (Critic-B F2, F3)

Rodei `python3 .claude/scripts/ceo-cost.py --since 3d --source transcripts
--format json`:

```
assento   usd=659.23   turns=1833    usd/turn=0.3596
subagent  usd=8745.84  turns=49965   usd/turn=0.1750
TOTAL=9405.08
```

O preço unitário do plano **reproduz** (US$ 0,1753 declarado × US$ 0,1750
medido) — crédito onde é devido, o K6 do round 1 foi atendido na metade textual.
O volume não: o §9 orça 8 rodadas × 40–120 turnos = **320–960 turnos** de
subagente, enquanto o MESMO instrumento na MESMA janela de 3 dias mede **49.965**.
Preço vindo da janela e volume ignorando a janela, sem justificativa escrita, é
incoerência interna — não estou afirmando que o plano custará US$ 9.400.

F3 confirmado por identidade exata: `by_role/assento` tem
`cache_read_tokens = 986490190`, o mesmo valor de `by_dimension/claude-fable-5-1`
— o «assento» medido é um assento Fable 5.1, enquanto o `tier_mix_estimate`
(`:14`) declara «assento Opus 5». A conversão nunca é declarada.

### K-H — P2 — a AC-4.2 volta a asserir a COR do gate, embora o instrumento exista (Critic-C R-QA6)

Verificado: `rule_matches_by_doc` é construído em `verify-counts.sh:789,795` e
exportado no `--json` em `:1258`. O `Check:` da AC-4.2 é `bash verify-counts.sh`
mais uma comparação **em prosa**. A AC-4.2 é literalmente o item que promete
«asserta a CONTAGEM de sítios CASADOS, não a cor do gate» — e o faz em texto.

### K-I — P2 — o teto de 8 caminhos morde a W2, e a W2 não tem decomposição (Critic-A R-VP5)

Verificado: o §3 (`:172-176`) diz que o teto morde o P3; o §6 (`:440-446`)
admite que a W2 pode ter de editar `verify-counts.sh`, membro do manifesto do
ADR-192. Somando o mínimo real: 1 `SKILL.md` canônico + 8 documentos de produto
(censo acima) + possivelmente `verify-counts.sh` = ~10 caminhos, em DOIS regimes
de cerimônia. A W3 ganhou decomposição explícita («um pacote por vez», `:399`);
a W2 não ganhou nenhuma.

### K-J — P1 — a AC-1.7 é uma espera de calendário de 30 dias dentro de um plano que jura não ter espera (Critic-B F10)

Verificado: `:380` («a re-medição aos 30 dias é publicada… A Fase 1 não fecha no
baseline») contra `:16` (`external_wait: none`), `:17` (`eta_calendar:
"mesmo-dia a D+1"`) e `:431` («não há segundo lugar no corpo que afirme
espera»). O §6 afirma a ausência de um segundo lugar que existe 51 linhas acima
dele. Não peço remover a re-medição — peço que o frontmatter a reconheça ou que
a Fase 1 declare que fecha no baseline.

---

## Single-agent insights rejected / deferred (com minha verificação)

- **F5 «`--include-rotated` é inerte» — DEFERIDO como nota de uma linha.**
  Verifiquei: `rotated_siblings_present: false` no HEAD, então hoje o flag não
  casa nada. Mas a frase do §1 é sobre a SEMÂNTICA do leitor (sem o flag ele vê
  só o arquivo vivo), que continua verdadeira e é a razão de manter o flag
  quando houver rotação. Não é defeito de modelo; vale a nota «inerte no HEAD».
- **F5 (metade dos números) + F9 «figuras não reproduzíveis» — FUNDIDOS num
  must-fix P3, não bloqueante.** Confirmei a deriva (hoje mediu assento 659,23 e
  mix 92,50/7,01/0,49 contra 655,23 e 92,57/6,97/0,45 no plano; o §4 já andou de
  141.988/109/0,257 para números novos). A cura é âncora de data explícita nas
  figuras do §9 — o §4 já faz isso e serve de molde. É higiene, não modelo.
- **F7 «minutos de CI/e2e e rodadas de cerimônia fora do orçamento» —
  DEFERIDO.** A convenção do repositório para `budget_usd_estimate` é gasto de
  modelo; nenhum plano do corpus precifica minutos de runner. Vale uma frase de
  ESCOPO no §9 («este número não inclui minutos de CI nem rodadas de
  cerimônia»), não um recálculo.
- **F8 «espalhamento declarado e não propagado» — REBAIXADO a P3.** O §9 de fato
  declara 51,7% de espalhamento e depois usa o ponto ~97k. Mas a faixa publicada
  620–950k já carrega incerteza pelo termo de TRABALHO (60k–140k). A cura é
  dizer QUAL termo carrega o espalhamento, não alargar a faixa para 428k–1,15M.
- **F11 (metade) «a AC-1.2 já está verde hoje» — REJEITADO como defeito.**
  Verifiquei: o grep da perna 1 devolve rc=1 sem saída no HEAD. Isso é o estado
  CORRETO depois de a revisão curar o K3 — a AC é uma invariante («nenhuma forma
  maior-ou-igual sobrevive»), e invariante nasce verde. **Fica** a outra metade,
  como P3: o padrão não cobre `>=0,10` sem espaço nem a grafia com ponto
  decimal.
- **R-QA9 «plano L3 sem ADR novo nomeado» — DEFERIDO para AC, não bloqueante.**
  O `CLAUDE.md` §4 exige ADR para escolha arquitetural cross-cutting, e o
  destino do arquivo morto fora de `.claude/skills/` qualifica. Mas o ADR é
  artefato de EXECUÇÃO: a cura coerente é uma AC nomeando-o na W2, não reabrir o
  modelo agora.

---

## Plan adjustments (must-fix numerado)

Bloqueantes (o plano não abre round 3 nem flipa sem eles):

1. **§2.1 perna 0** — trocar a ARQUITETURA da elegibilidade (medido:
   candidatas = 0). Sem isso `ARQUIVAR` é inalcançável e a W2 não tem entrada.
2. **§2.1 perna 1 + §8:467** — resolver `min_window_coverage_days = 90` contra
   os 16,6 dias medidos; parar de registrar C1 como curado pela guarda de 90
   dias.
3. **§2.2** — declarar a posição da regra sobre `chain_status: NOT INTACT`
   (`RECUSA`, ou risco aceito por escrito).
4. **§4.4 (`:282-285`)** — remover ou MEDIR a premissa «o `CLAUDE.md` manda
   operar em português»; a proibição da Fase 1 depende dela.
5. **§5 AC-3.3** — `Check:` que exerça o caminho de perfil por domínio (nova AC
   na W3 que ensine `smoke-install.sh` a receber perfil, ou outro comando).
6. **§5 AC-1.4** — `Check:` executável: caminho do registro, dono, conjunto
   fechado e critério de morte; `grep -rn` (com `-r`).
7. **§5 W2 + §1 passo 5** — W4 antes da W2, ou AC-2.2 reescrita; e decompor a
   W2 para caber no teto de 8 caminhos.
8. **§5 W0/W1 + §6:445-446** — reconciliar o rótulo «LIVRE» com a AC-0.6, que
   edita caminho canônico.

Não bloqueantes, mas o texto absorve na mesma revisão:

9. **§5 AC-0.5/AC-1.3** — Checks que discriminem a sonda corrigida da antiga
   (asserção sobre a saída, não flags que a sonda ignora).
10. **§5 AC-1.1, AC-0.1, AC-1.6, AC-2.1, AC-2.2, AC-2.3, AC-4.1, AC-4.4** — cada
    `Check:` ganha metade vermelha; a AC-2.3 ganha discriminante contra a AC-2.2.
11. **§5 AC-4.2** — asserir `rule_matches_by_doc` (`verify-counts.sh:789,795`,
    exportado em `:1258`), não a cor.
12. **§9** — reconciliar volume com a janela; declarar a conversão
    Fable 5.1 → Opus 5 do `assento`; ancorar as figuras por data; dizer qual
    termo carrega o espalhamento; nota de escopo (CI/cerimônia fora).
13. **§Progress log:528 e §5 AC-1.7** — apagar o «PENDENTE» já ratificado;
    reconciliar a re-medição aos 30 dias com `external_wait: none`.

---

## Round verdict

**ESCALATE-TO-OWNER.**

O rótulo `design-coherent` **NÃO** é registrado: os três críticos terminaram em
`ADJUST` e os oito itens bloqueantes acima estão abertos.

Escolhi escalar em vez de `RUN-ANOTHER-ROUND` por três razões verificadas:

1. **O experimento central não tem sujeito.** Com a perna 0 como escrita, o
   conjunto de candidatas é vazio (medido, reproduzido por mim) e a W2 — único
   pacote canônico — abre sem entrada. Nenhuma reescrita de `Check:` resolve
   isso; é decisão de arquitetura.
2. **A regra de parada do próprio plano dispara.** A W0 pré-registra: «se o
   controle de não-autofagia não ficar verde em duas rodadas, a regra muda de
   arquitetura em vez de ganhar mais uma exceção». Round 1: a regra arquivava
   `ceo-orchestration`. Round 2: a cura zera todas as candidatas e a guarda de
   denominador deixa o controle positivo verde pelo motivo errado. São as duas
   rodadas.
3. **Quatro perguntas não têm dono abaixo do Owner** — um round 3 as
   re-derivaria sem poder respondê-las.

Perguntas abertas para o Owner (as três primeiras bloqueiam qualquer round 3):

- **OQ-1** — com a perna 0 zerando as candidatas: a W2 ainda existe? Se sim, sob
  que critério (a consolidação do §2.3, que tem critério próprio, em vez da
  telemetria)?
- **OQ-2** — `min_window_coverage_days`: qual número, com a razão? Ou a guarda
  passa a ser «cobertura declarada do histórico atribuível», e aí
  `external_wait: none` sobrevive?
- **OQ-3** — a poda pode decidir sobre ledger com `chain_status` não íntegro? Se
  não, a regra devolve `RECUSA` nesse estado.
- **OQ-4** — decisão (b) de idioma: conjunto fechado, dono, critério de morte e
  o CAMINHO do registro (a AC-1.4 não pode existir sem isso). Depende de OQ-5.
- **OQ-5** — a premissa de uso em português vira fração MEDIDA na janela, ou
  desce de «regressão medida» para hipótese?
- **OQ-6** — W0/W1 aceitam duas assinaturas a mais (AC-0.6 é canônica), ou a
  AC-0.6/AC-1.6 saem da primeira sessão?
- **OQ-7** — quem entrega a perna de perfil do harness de instalação: a W3 deste
  plano, ou o PLAN-171?

`status:` permanece `reviewed`. Este documento é registro de debate — não
autoriza execução, não flipa status e não substitui o pair-rail.
