---
plan: PLAN-188
round: 4
rounds_synthesized: [round-4]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "§Acceptance criteria AC-4, cabeçalho (:1114-1116) × Check passo (2) (:1202-1204) — o AC nomeia DUAS bases para a mesma comparação; o cabeçalho ainda ancora em `s345-rail-classes.txt`, que o Check proíbe com todas as letras. A Meta < 5 % (:1243) herda a base proibida."
  - "§Acceptance criteria AC-3, pré-condição (:1088-1096) e §Waves W1 (:846-849, :855-856) / W2x (:883) — o MAPA das seis chaves é lido pelos `Check:` do AC-2 (:1066) e do AC-3 (:1097) e não tem PATH em file assignment nenhum."
  - "§Waves W3, file assignment (:919-933) — a wave cria um ADR e não leva `CLAUDE.md` (superfície GERADA que conta ADRs, hoje 198/198 rc 0), que é Gate-1 cache-stable por §0."
  - "§Approach controles POSITIVOS (b) e (c) (:249-252, :986-989) — definidos sobre «um script do toolkit» sem LUGAR declarado; rastreados sob o toolkit root eles produzem BLOCKING e derrubam o gate fail-closed do `ceremony-lint`."
  - "§Approach recusas do leitor (:397-401) × AC-1 piso (:973-975) × W0b (:820-822) — as 7 RECUSAS NOMEADAS prometem «cada uma com controle vermelho» e nenhuma está no piso de 7 nem entre os 6 arquivos de controle."
  - "§Acceptance criteria AC-5 (:1245-1249) × §Waves W3 (:934-937) × §Success criteria (:1494) — o AC tem duas cláusulas, `Check:` para uma só, e a segunda está escrita como «não pertence a wave nenhuma»."
  - "§Open questions OQ-9 (:1418-1447) × §Riscos quarto sítio (:654-658) × AC-1 (:1053-1055) — duas ternas (i)/(ii)/(iii) distintas, rótulos colididos por numeral nu no MESMO bloco (:1427 × :1447), e um AC que afirma ser UMA pergunta."
  - "§Riscos instrumento de EVENTO (:635-639) e AC-1 quarto controle (:998-1004) — o casador prescrito (`fnmatch`, itens ENTRE ASPAS) é mais permissivo que o filtro `paths:` que ele modela e cego a listas não citadas; o precedente nomeado (:1167-1174) usa igualdade exata."
  - "§Waves W0, corte v2 (:773-775, :782-784) × W0a/W0b/W0c (:797-802, :820-823) — o total publicado «15 paths» é inalcançável pelas próprias subwaves (máximo 14), e «cada um desses é um path a mais» contradiz «ou o workflow barato que o substitua»."
  - "§Acceptance criteria AC-1, Check (:960) e piso (:977-979) — `bash -n` sem executor nomeado, e o membro `.py` do toolkit sem nenhum julgamento de sintaxe/import em CI; o `N/N` é derivado pela lista que o próprio runner enumera."
  - "§Approach decisão (c) (:236-238) × AC-6 (:1281-1289) — a R8 alargada ao toolkit root torna um exec-bit acidental um BLOCKING cuja única rota de escape passa a exigir bump ASSINADO; o custo de recuperação não está escrito."
  - "§Acceptance criteria AC-1, cláusula Falha (:1016) — sobrevive um controle de EVENTO cujo único instrumento nomeado se declara limitado ao PREDICADO."
synthesized_at: 2026-09-07T01:10:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-188 — consenso do round 4

Três críticos, três `ADJUST`, 4 + 2 + 3 itens declarados bloqueantes. Nenhum
pediu `REJECT`. Este round é uma checagem de COERÊNCIA INTERNA do texto do plano
curado em `952c27d`; não certifica verdade externa e não autoriza wave nenhuma.
Toda claim abaixo foi re-verificada em disco (árvore viva, HEAD `5fcf861`) antes
de virar ajuste.

**O que os três confirmaram primeiro, e eu reproduzi:** os **14 must-fix do
round 3 estão absorvidos**. Spot-check próprio, com sítio: M1/M2 — a frase «o
passo devolve rc 1 (medido no HEAD)» tem **0** ocorrências no plano e
`:155-165` publica a razão nova (`SC1071` permanente), coerente com
`ceremony-lint.yml:72` (ADVISORY), `:75` (`continue-on-error`), `:77`
(`set -uo pipefail`, sem `-e`) e `:81-82` (`|| true`); M2 — a cláusula de FALHA
perdeu o job `shellcheck-ceremony` (`:1018-1021`); M3 — o AC-6 ganhou «ONDE cada
vermelho é observável» (`:1271-1289`); M4 — a W3 perdeu o rótulo `docs`
(`:899-900`); M5/M12 — a W0a é **7 paths** com as duas suítes que o
`pytest.ini:41` coleta (`:797-816`); M6 — o controle POSITIVO sintético entrou
(`:1219-1228`), e `grep -c "scripts/ceremony" s345-rail-classes.txt` = **0**
reproduz o motivo; M8 — o piso é **7** vermelhos com id por controle
(`:973-975`); M9 — a exceção da invariante 9 está no cabeçalho (`:949-953`);
M10 — `cohort-records.sha256` e `rail-classes-rebased.txt` entraram no file
assignment da W3 (`:925-932`); M11 — a consequência de sequência do `harness.sh`
está DENTRO do braço (iii) (`:1428-1436`), sem decidir a OQ-9; M13 — os DOIS
consumidores do `--list` estão nomeados e `:39` é declarado não-consumidor
(`:1010-1014`); M14 — o mecanismo do censo é o filtro `is_tracked` de
`check-ceremony-script.py:329-330` (`:309-310`), verificado no código.
**A classe do round 3 está fechada.**

O que sobra é uma classe NOVA, nomeada pelos três com instâncias diferentes:
**artefato ou rótulo que um `Check:` CONSOME e que nenhuma wave DECLARA.**

## Consensus findings (2+ agents flagged)

### C1 — BLOQUEANTE — o AC-4 nomeia DUAS bases para a mesma comparação (Critic-B, Critic-C)

Verificado em disco. O cabeçalho do AC-4 (`:1114-1116`) ancora a medição «contra
a base congelada de 23,1 % (`.claude/plans/PLAN-188/s345-rail-classes.txt`)»; o
passo (2) do `Check:` do MESMO AC (`:1202-1204`) manda comparar contra
`.claude/plans/PLAN-188/rail-classes-rebased.txt`, «**nunca** contra
`s345-rail-classes.txt`, que é a base da regra ANTIGA». A `Meta: < 5 %`
(`:1243`) foi escrita contra a base que o próprio Check proíbe.

A cura M10 do round 3 acrescentou o artefato novo e não emendou o cabeçalho nem
a Meta. Agravante medido por Critic-C e reproduzido: o plano exige que a base
re-medida bata **classe a classe** com a congelada (`:1163-1165`) e o corpus
congelado tem **0** ocorrências de `scripts/ceremony` — logo as duas bases têm
figuras IDÊNTICAS por construção sobre esse corpus, e um leitor não consegue
saber, pelo texto, qual número a Meta persegue.

**Severidade acordada:** BLOQUEANTE. **Ajuste:** o cabeçalho e a Meta passam a
citar `rail-classes-rebased.txt`; `s345-rail-classes.txt` fica nomeado só no seu
papel (base da regra ANTIGA e input do controle de mudança-só-de-CLI).

### C2 — BLOQUEANTE — o instrumento dos controles de EVENTO pode nascer verde sem provar o gatilho (Critic-A, Critic-C)

Dois mecanismos independentes contra o MESMO instrumento — o caso novo em
`.claude/scripts/tests/test_release_workflow_asserts.py` que reusa
`_workflow_paths_lists` (`:635-639`, `:998-1004`). Ambos verificados:

(a) **O casador é mais permissivo que o filtro que ele modela.** O plano
prescreve `fnmatch`; medido, `fnmatch.fnmatch('.claude/scripts/ceremony/controls/run.sh',
'.claude/scripts/ceremony/*')` = `True`, enquanto o `*` do filtro `paths:` do
GitHub não atravessa `/`. No layout que a W0b entrega — `controls/` (`:820-822`)
— um wave que escreva `/*` passa no teste e o PR real não dispara. O precedente
nomeado pelo próprio plano (`test_ownership_paths_present_in_both_filters`,
`:1169-1176`) usa `assertIn` **exato**, sem glob nenhum; e `grep -c fnmatch`
naquele arquivo = **0** — o casador não existe hoje, é entrega da wave. Precisão
que registro: os sítios do plano que já escrevem o glob usam `**` (`:651`,
`:668`), forma em que os dois casadores concordam no contra-exemplo — o defeito
é que o instrumento não obriga essa forma.

(b) **O extrator é cego a listas não citadas.** O docstring de
`_workflow_paths_lists` (`:1095-1101`) diz «Collects quoted `- "..."` items»;
os `paths:` do `.github/workflows/ceremony-lint.yml` estão entre aspas hoje
(`:6-11`, `:13-18`), então o caso funciona para ele — mas o workflow do QUARTO
SÍTIO é criado pela wave, e um `paths:` sem aspas devolve lista VAZIA, contra a
qual o casador não tem o que falhar. E o leitor `self._smoke()` do precedente lê
OUTRO workflow.

**Severidade acordada:** BLOQUEANTE (é o instrumento de que dependem o quarto
controle do AC-1 e os controles de evento do quarto sítio). **Ajuste:** o
instrumento nasce com (i) casador cuja semântica de `*` NÃO atravessa `/`
(ou a exigência escrita de que o glob entregue seja `**`), (ii) asserção de
lista NÃO-VAZIA para cada workflow lido, e (iii) o controle vermelho já previsto
(remover a entrada nova) rodando sobre AMBOS os workflows.

### C3 — BLOQUEANTE — a classe: artefato que um `Check:` consome e que nenhuma wave declara (Critic-A, Critic-B, Critic-C)

Três instâncias distintas, uma por crítico, mesma forma — e é a forma do M10 do
round 3, em sítios novos. Cada uma verificada por mim, em disco:

**(a) O MAPA das seis chaves (Critic-A).** O `Check:` (a) do AC-2 (`:1066`) e o
`Check:` (a) do AC-3 (`:1097`) leem «o MAPA das seis chaves»; `:1088-1096`
manda a W1 escrever a linha de W6a e `:883` põe «a linha do MAPA» em cada
subwave `W2x`. Mas o file assignment da W1 (`:846-849`) e o seu corte v2
(`:855-856`) são EXATAMENTE 6 paths sem o mapa, e
`grep -nEi 'map\.tsv|MAP\.md|ceremony-map|packs-map'` no plano não devolve nada.
Sem arquivo, o controle POSITIVO obrigatório dos dois ACs (`:1070-1073`,
`:1100-1104`) não tem sobre o que rodar. Precisão: os seis diretórios vivem fora
do repo (`<PK>`), o que explica não haver path RASTREADO — mas o mapa em si
continua sem endereço em wave nenhuma, e é ele que o Check abre.

**(b) A superfície GERADA que conta ADRs (Critic-B).** A W3 cria
`.claude/adr/ADR-2xx-shared-ceremony-toolkit.md` (`:919-920`) e o seu file
assignment (`:919-933`) não inclui `CLAUDE.md`. Medido no HEAD: `CLAUDE.md:54`
afirma «**198 ADRs**», `ls .claude/adr/ADR-*.md | wc -l` = **198**, e
`check-claude-md-claims.py:139-146` (check «ADR count», `claim_regex`
`\b(\d+)\s+ADRs\b`, `tolerance=0`) sai rc 0 hoje. No instante em que a wave
escreve o ADR, o gate de corpus acende sobre a árvore staged — e `CLAUDE.md` é
Gate-1 **cache-stable, editável só em closeout** por `CLAUDE.md` §0.

**(c) Os controles POSITIVOS (b) e (c) do lint (Critic-C).** `:249-252` e
`:986-989` definem «um script do toolkit com `|| true` numa linha de `gpg`» e
«um script do toolkit com exec-bit no índice» sem LUGAR declarado. Rastreados no
endereço real, com o predicado novo de descoberta incondicional, produzem
BLOCKING — `check-ceremony-script.py:329` é
`if n_block and not waived and is_tracked` — e o job de `ceremony-lint.yml:36-42`
é fail-CLOSED (`exit "$rc"`). Medido hoje `blocking_unwaived` = 0; a única cura
seria um append no `ceremony-lint-waivers.json`, que é exatamente a rota de
escape que o AC-6 do plano denuncia. O precedente da casa para isso é árvore
descartável (`test_check_ceremony_script.py:35-44`, `--root <tmp>`).

**Severidade acordada:** BLOQUEANTE nas três instâncias. **Ajuste:** cada
artefato ganha wave, path (ou endereço `<PK>` declarado) e, no caso (c), a
exigência escrita de árvore DESCARTÁVEL — nenhum controle positivo do lint é
shipado rastreado sob o toolkit root.

## Single-agent insights kept (verified on disk)

- **S1 — BLOQUEANTE (Critic-A) — o AC-5 tem duas cláusulas e `Check:` para uma
  só.** `:1245-1247` exige «ADR próprio ACEITO» **E** «ADR-010 emendado»; o
  `Check:` de `:1248-1249` só testa a primeira. E `:934-937` escreve, com todas
  as letras, que «a emenda ao ADR-010 NÃO é agendada aqui … a emenda não
  pertence a wave nenhuma» enquanto a OQ-1 estiver aberta — enquanto `:940` dá
  «Aceite: AC-4 … e AC-5» à W3 e o §Success criteria (`:1494`) exige «AC-1 a
  AC-6 marcados». **Não decido a OQ-1:** o ajuste é escrever o `Check:` da
  segunda cláusula e marcar a cláusula como CONDICIONAL à wave que a OQ-1
  fixar, para que o Success criteria não exija o inexigível. Mantido.
- **S2 — BLOQUEANTE (Critic-A) — a OQ-9 carrega DUAS ternas com rótulos
  colididos.** Terna A (onde mora o quarto sítio) em `:654-658`; terna B (quem
  executa o runner) em `:1424-1428`. Dentro do MESMO bloco da OQ-9, `:1427` usa
  «(iii) execução local exigida pelo `harness.sh`» e `:1447` usa «a opção (iii)»
  para o step REPLICADO num workflow barato — dois referentes, um rótulo. E o
  AC-1 (`:1053-1055`) afirma que a OQ-9 foi «reduzida a UMA pergunta», contra
  `:1418-1420` («quem EXECUTA … e, agora, onde mora o QUARTO sítio») e `:1439`
  («passa a decidir junto o CUSTO do quarto sítio»). Verifiquei também o fato de
  kernel que a terna B carrega: `check_arbitration_kernel.py:144` lista
  `.github/workflows/validate.yml`. **Não decido a OQ-9** — o ajuste é de
  ROTULAGEM: as duas perguntas ganham letras próprias (`OQ-9a` sítio /
  `OQ-9b` executor) e o AC-1 para de chamá-la de uma. Um Owner que responda
  «(iii)» hoje não sabe a que respondeu. Mantido.
- **S3 — BLOQUEANTE (Critic-B) — as 7 RECUSAS NOMEADAS do leitor prometem
  controle vermelho e não têm nenhum.** `:397-401` lista as sete (chave
  desconhecida, chave duplicada, obrigatória ausente, valor multi-linha, `TAB`
  em valor, path absoluto em `paths`, `CRLF`) «cada uma com controle vermelho».
  O piso do AC-1 (`:973-975`) enumera exatamente sete ids —
  `inv1`, `inv3a`, `inv3b`, `inv3c`, `inv4`, `inv5`, `inv10` — e **nenhum** é do
  leitor; a W0b (`:820-822`) entrega 6 arquivos, nenhum do `read_manifest.py`.
  O runner imprime 7/7 VERDE com o parser fail-CLOSED do ponto onde o Owner
  assina sem um único controle. Agravante verificado: `pytest.ini:38-46` não
  lista `.claude/scripts/ceremony` — o leitor `.py` não é coletado por nenhuma
  suíte de CI. Mantido.
- **S4 (Critic-A) — o corte v2 da W0 publica um total que as subwaves não podem
  produzir.** `:773-775` («cada um desses é um path a mais») e `:782-784`
  («13 … 14 … **15** quando entram dois») contra `:797-802`, que define o quarto
  sítio como UM slot («`smoke-install.yml` **OU** o workflow barato que o
  substitua»), e `:822-823` («W0c = 0 ou 1 path»): máximo 7 + 6 + 1 = **14**.
  Aritmética de escopo, não mudança de modelo. Mantido.
- **S5 (Critic-B) — o `bash -n` do AC-1 não tem executor, e o membro `.py` do
  toolkit não tem sintaxe/import em CI nenhuma.** `:960` exige `bash -n` +
  `shellcheck`; só o segundo é declarado automático (`:1049-1052`), via
  `validate.yml:341-359` — verificado recursivo, com única exclusão
  `owner-ceremony/archive/*` em `:354`, e restrito a `-name '*.sh'`.
  `grep -rn 'bash -n' .github/workflows/*.yml` = **vazio**. Somado ao
  `pytest.ini` sem `.claude/scripts/ceremony`, o `read_manifest.py` — o leitor
  fail-closed do ponto de assinatura — não é compilado, importado nem
  shellcheckado por nada. Mantido.
- **S6 (Critic-B) — a R8 alargada + AC-6 tornam um exec-bit acidental reparável
  só por cerimônia.** Verificado: `check-ceremony-script.py:192-194` restringe a
  R8 hoje a `.claude/plans/`; a decisão (c) do plano a alarga ao toolkit root
  (`:236-238`), e `CLAUDE.md` §4 registra que o exec-bit volta no primeiro
  `git add -A`. Com os arquivos do lint dentro do manifesto ADR-192 (AC-6), a
  rota de escape passa a exigir bump ASSINADO. O AC-6 escreve o custo do append
  de waiver (`:1281-1289`), não o do exec-bit. Mantido como custo a escrever.
- **S7 (Critic-C) — o `N/N` é derivado pela lista que o próprio runner
  enumera.** `:977-979` («o runner imprime `N/N` derivado da lista de ids que
  ele mesmo enumera») contra `:973-975` (os sete ids). Um runner que perca o
  `inv3b` imprime `6/6` e passa. O conjunto autoritativo tem de ser o do AC,
  comparado como CONJUNTO nos DOIS sentidos. Mantido.
- **S8 (Critic-C) — a cláusula Falha do AC-1 ainda promete um EVENTO sem
  observador.** `:1016` mantém «um PR do toolkit que não dispare o
  `ceremony-lint.yml`» enquanto `:1002-1004` declara que o instrumento prova o
  PREDICADO, não o motor de eventos. É o resíduo da classe que o M2 fechou para
  o job `shellcheck-ceremony`. Mantido (o ajuste é uma frase, não uma wave).
- **S9 (Critic-C) — o chaveiro GPG descartável é entrega sem dono.** `:769-771`
  e `:1051-1052` atribuem o chaveiro à OQ-9, que decide QUEM executa e ONDE mora
  o quarto sítio; semear chaveiro é ENTREGA, necessária nos três braços. Mantido
  como item a nomear numa wave, sem decidir a OQ-9.
- **S10 (Critic-A) — o placeholder `ADR-2xx` no file assignment da W3.**
  Verificado: `:919-920` declara `.claude/adr/ADR-2xx-shared-ceremony-toolkit.md`
  e `:934-937` deixa o número com a OQ-1; medido, o maior ADR do HEAD é o
  **ADR-197** (198 arquivos), confirmando `:906`. Mantido com escopo
  ESTREITADO: a gramática de `CLAUDE.md` §4 governa a declaração de um SPAWN
  (ADR-191), não a lista `Arquivos:` de uma wave — o ajuste é escrever que a W3
  não pode ser DESPACHADA enquanto o placeholder estiver de pé, não renumerar o
  ADR (isso decidiria a OQ-1).
- **S11 (Critic-B) — o vermelho (ii) do AC-6 depende de DUAS entregas em waves
  diferentes.** `:1272-1280` atribui a ligação ao quarto sítio («é ELE que liga
  o append de waiver ao `shasum -c`»); verificado, `smoke-install.yml:355-360`
  confere apenas MEMBROS do manifesto, e a metade da MEMBRESIA é a própria AC-6
  (W1). O round 3 (M7) escreveu essa metade no §Riscos; o AC não a repete.
  Mantido como precisão de uma frase.

## Single-agent insights rejected / deferred

- **REJEITADO na leitura forte — «o placeholder `ADR-2xx` é declaração viciada
  pelo ADR-191» (Critic-A, R-VP5).** O fato é verdadeiro, a moldura não: a regra
  «globs/placeholders taint the whole declaration» de `CLAUDE.md` §4 é do
  protocolo de SPAWN, e uma wave de plano não é um spawn. Reaproveitado em S10
  na forma estreitada (não despachar com placeholder).
- **DEFERIDO — a opção (iv) da OQ-9 («aceitar a latência da nightly, sem sítio
  novo»).** Já está registrada no plano como recomendação (`:1449-1456`) por
  decisão do round 3; numerá-la seria chegar perto de decidir uma OQ que o Owner
  mantém aberta. Sem mudança.
- **NÃO DECIDIDO, por desenho — OQ-1, OQ-2, OQ-4, OQ-5, OQ-6, OQ-8, e as
  pré-condições OQ-7 e OQ-9.** Os três críticos as listaram como faltantes; as
  três listas coincidem. Nenhum dos 12 must-fix abaixo decide qualquer uma
  delas: M2 e M7 escrevem CONSEQUÊNCIA e ROTULAGEM para o Owner escolher com
  elas à vista, que é o mesmo tratamento que o M11 do round 3 recebeu.

## Plan adjustments (must-fix — o texto do plano tem de absorver)

1. **[BLOQUEANTE]** `:1114-1116` + `:1243` — o cabeçalho e a `Meta` do AC-4
   passam a citar `rail-classes-rebased.txt`, a base que o `Check:` (`:1202-1204`)
   exige; `s345-rail-classes.txt` fica só no papel de base da regra ANTIGA.
2. **[BLOQUEANTE]** `:1245-1249` + `:934-937` + `:1494` — o AC-5 ganha `Check:`
   para a segunda cláusula (emenda ao ADR-010) **e** a marca de que ela é
   CONDICIONAL à wave que a OQ-1 fixar, de modo que o §Success criteria pare de
   exigir uma cláusula que nenhuma wave entrega. **Não decidir a OQ-1.**
3. **[BLOQUEANTE]** `:1088-1096` + `:846-849` + `:883` — o MAPA das seis chaves
   ganha ENDEREÇO declarado (path rastreado, ou endereço `<PK>` escrito com a
   mesma clareza do §Context) e a wave que o CRIA; sem isso os controles
   positivos obrigatórios do AC-2 (`:1070-1073`) e do AC-3 (`:1100-1104`) não
   têm objeto.
4. **[BLOQUEANTE]** `:919-933` — `CLAUDE.md` entra no file assignment da W3
   (ou a wave declara como concilia a contagem), porque
   `check-claude-md-claims.py:139-146` tem `tolerance=0` sobre «198 ADRs»
   (`CLAUDE.md:54`; disco 198) e o ADR novo acende o gate na árvore staged; e o
   parágrafo registra que `CLAUDE.md` é Gate-1 cache-stable/closeout-only
   (`CLAUDE.md` §0), o que faz dessa edição uma decisão, não uma carona.
5. **[BLOQUEANTE]** `:249-252` + `:986-989` — os controles POSITIVOS (b) e (c)
   ganham LUGAR escrito: árvore DESCARTÁVEL no molde de
   `test_check_ceremony_script.py:35-44` (`--root <tmp>`). Nenhum controle
   positivo do lint é shipado RASTREADO sob o toolkit root — `:329` de
   `check-ceremony-script.py` e o `exit "$rc"` de `ceremony-lint.yml:36-42`
   fariam dele um BLOCKING cuja única cura é o append de waiver que o AC-6
   denuncia.
6. **[BLOQUEANTE]** `:397-401` + `:973-975` + `:820-822` — resolver a promessa
   das 7 RECUSAS: ou elas entram no piso do AC-1 com id próprio e arquivo de
   controle na W0b (e o piso deixa de ser 7), ou `:397-401` para de prometer
   «cada uma com controle vermelho» e escreve o que de fato é entregue.
   Registrar no mesmo parágrafo que `pytest.ini:38-46` não coleta
   `.claude/scripts/ceremony`.
7. **[BLOQUEANTE]** `:654-658` × `:1424-1428` × `:1427` × `:1447` × `:1053-1055`
   — as DUAS perguntas da OQ-9 ganham rótulos disjuntos (`OQ-9a` = onde mora o
   quarto sítio; `OQ-9b` = quem executa o runner), nenhum numeral nu `(i)/(ii)/(iii)`
   é reusado no mesmo bloco para ternas diferentes, e o AC-1 para de afirmar
   «reduzida a UMA pergunta». **Não decidir a OQ-9.**
8. **[BLOQUEANTE]** `:635-639` + `:998-1004` — o instrumento dos controles de
   EVENTO nasce com casador cujo `*` NÃO atravessa `/` (ou com a exigência
   escrita de que o glob entregue seja `**`), com asserção de lista NÃO-VAZIA
   por workflow lido (`_workflow_paths_lists` só coleta itens ENTRE ASPAS,
   `:1095-1101`) e com o controle vermelho rodando sobre os DOIS workflows.
   Citar que o precedente (`:1169-1176`) usa igualdade exata, não glob.
9. `:773-775` + `:782-784` — corrigir a aritmética do corte v2: o máximo
   alcançável por W0a (7) + W0b (6) + W0c (0 ou 1) é **14**; e desfazer «cada um
   desses é um path a mais» contra «ou o workflow barato que o substitua»
   (`:800`), que é substituição, não adição.
10. `:960` + `:1049-1052` — nomear o executor do `bash -n` e escrever que o
    membro `.py` do toolkit não tem, hoje, sintaxe/import em CI nenhuma
    (`validate.yml:341-359` é `-name '*.sh'`; `pytest.ini:38-46` não cobre o
    diretório), ou entregar a cobertura no mesmo patch.
11. `:977-979` — o conjunto autoritativo de ids é o do AC (`:973-975`),
    comparado como CONJUNTO nos dois sentidos; um `N/N` derivado pela própria
    enumeração do runner passa com um id perdido.
12. `:1016` — a cláusula Falha do AC-1 para de prometer um EVENTO que o
    instrumento nomeado declara não observar (`:1002-1004`), ou nomeia o
    observador; e `:236-238` + `:1281-1289` escrevem o custo de recuperação do
    exec-bit acidental sob a R8 alargada, ao lado do custo do append de waiver
    que já está lá. Nomear numa wave o chaveiro GPG descartável (`:769-771`),
    que é entrega nos três braços da OQ-9.

## Round verdict

**RUN-ANOTHER-ROUND.**

Oito itens bloqueantes sobrevivem à verificação em disco (M1–M8), dos quais dois
foram levantados por dois críticos (C1, C2) e um pelos três, em instâncias
diferentes da mesma forma (C3). A regra do round é explícita: `PROCEED` só com
zero itens bloqueantes.

O rótulo **design-coherent NÃO é registrado neste round** — ele se registra
apenas quando o round ITSELF termina com zero bloqueantes nas três críticas, e
aqui foram 4 + 2 + 3.

Não é `ESCALATE-TO-OWNER`: nenhum dos doze must-fix decide uma das OQ abertas
(OQ-1, OQ-2, OQ-4, OQ-5, OQ-6, OQ-8) nem as pré-condições OQ-7/OQ-9. M2 e M7
escrevem, respectivamente, a CONDICIONALIDADE e a ROTULAGEM que fazem as duas
perguntas ficarem legíveis para quem vai respondê-las — o mesmo tratamento que o
M11 do round 3 já recebeu e que o Owner ratificou ao manter as OQs abertas.

Nenhum dos ajustes reescreve o MODELO do plano: os doze corrigem uma AFIRMAÇÃO,
uma CONTAGEM, um ESCOPO DE ARQUIVO ou um RÓTULO. As dez invariantes, o corte de
waves (W0a/W0b/W0c, W1, W2a..W2e, W3) e as decisões (a)–(d) do §Approach seguem
intactos. A classe que este round abre e fecha é uma só: **artefato ou rótulo
que um `Check:` CONSOME e que nenhuma wave DECLARA** — sucessora direta da classe
do round 3 («controle de aceite cuja metade vermelha não é alcançável»), agora
do lado do OBJETO em vez do lado do EVENTO.

Zero codex nesta rodada (regra R1 do Owner: um pacote de docs/plano não recebe
rodada de rail). Nenhum arquivo da árvore viva foi tocado por esta síntese.
