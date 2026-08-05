---
round: 3
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (team.md é o template do framework — linha de arquétipo apenas; esperado em dogfood)
generated_at: 2026-08-05T00:00:00Z
verifies: texto FINAL pós-17-rounds; round-2 must-fix 1-7
---

## Verdict

**ADJUST** — o texto final é coerente e executável (verifiquei 12
afirmações factuais novas contra a árvore; **todas verdadeiras**, incluindo
a aritmética do r13 — `pytest --collect-only` no escopo documentado devolve
**14172** exatos), e os 7 must-fixes do round 2 estão fechados; mas a
composição de dois fixes corretos (r3 "verdito commitado antes da tag" +
r15 "preflight restaurado no GA") os colocou na **ordem errada**, deixando
a tag GA apontar para um commit cujo CI nunca foi verificado — a mesma
classe que §Riscos declara estar fechando.

## Summary (≤ 3 bullets)

- **Os 17 rounds NÃO produziram contradição arquitetural.** Cruzei as
  quatro OQs entre si e contra os §W0/§W1/§W2/§ACs: o predicado de 4
  oráculos, a semântica de candidato do poll, a condicionalidade por
  entrega real do FMS e o assert de delta ancorado no `parent_sha` são
  mutuamente consistentes. As correções são cumulativas, não conflitantes —
  a trajetória registrada em §W0.2 (mesmo-commit r2 → allowlist r4 →
  provenance r10 → parent_sha r11 → conjunto fechado r14 → server-side r15)
  é uma cadeia de refinamento, não de remendos que se anulam.
- **A qualidade de verificação subiu de forma mensurável.** Achados que o
  debate inteiro não pegou e o codex pegou: `GH_TOKEN` ausente (fail-closed
  que quebraria TODA release), `fetch-depth: 1` (o pin `v1.2.0` não resolve
  em CI — confirmei em `smoke-install.yml:53`), `--no-replay` pulando a
  leitura de ceremony (confirmei `upgrade.sh:292-295` + o gate `REPLAY -eq
  1` em `:681`), o loop eterno do update-checker (confirmei: ele sobe a
  árvore procurando `VERSION` da raiz e lê em `:103`). Nenhum deles é
  cosmético.
- **O que ainda quebra:** a ordem `bump → preflight → verdito-commit → tag`
  em §W2.2 e §W2.4 (R3-VP1); mais três imprecisões de censo/escopo que a
  própria doutrina do plano condena (lista recitada em vez de derivada;
  métrica adjacente deixada sem regra; edição de arquivo Gate-1 sem
  reconhecer a disciplina de cache).

## Risks

**R3-VP1 — HIGH — `preflight` roda ANTES do commit do verdito; a tag cai num commit não verificado por ele.**
§W2 fixa a sequência por tag como "re-pass → verdito → **commitar** →
**push origin main** → tag". Mas §W2.2 e §W2.4 ordenam
`bump → preflight → verdito assinado+commitado+pushado → tag`. O
`preflight` afirma `HEAD == origin/main` e "all workflows for HEAD green
(Validate success)" — e então o commit do verdito é criado **depois**,
mudando HEAD. `tag()` só checa ancestralidade + VERSION + árvore limpa.
Logo o commit efetivamente taggeado **nunca passou pelo preflight**. É a
forma exata do bug F2 que o plano acabou de fechar (commit criado após o
preflight que `tag()` assina), só que agora o commit é o do verdito em vez
do bump. O r15 acertou o DIAGNÓSTICO ("o hold de 24h pode ter mudado
main/CI") e errou a POSIÇÃO.
*Residual real:* limitado — `release.yml` refaz os gates sobre a árvore da
tag e, com F1, o npm não publica; o dano é tag desperdiçada + delete/re-tag,
não publicação ruim. Mas §Riscos vende "o gate de ancestralidade em `tag()`
e o `await-release-gate` fecham as duas pernas", e esta perna fica meio
aberta.
*Mitigação (uma linha, estritamente melhor):* reordenar para
**verdito assinado+commitado → push origin main → CI verde no commit do
verdito → `preflight`(`--rc N`/`--stable`) → tag → push da tag**. Verifiquei
a compatibilidade: após commitar+pushar o verdito a árvore está limpa
(`preflight` exige `git status --porcelain` vazio ✅), `HEAD == origin/main`
passa a valer para o commit taggeado ✅, a tag continua livre ✅, e o assert
de delta `parent_sha→HEAD ⊆ allowlist` continua válido porque **nenhum
commit nasce depois do preflight**. Com F2 no-op provado, `bump` antes ou
depois é indiferente no GA.

**R3-VP2 — MEDIUM — o censo recitado em §W0.3 está incompleto, na frase que manda não recitar.**
§W0.3 diz que `docs/README.md` "sozinho carrega SETE stale
(151/53/44/22/171/67/~670 vs 166/57/46/27/188/68/~730, verificado)". Conferi
o arquivo: são **pelo menos nove métricas em doze ocorrências**. Faltam na
lista: `:79` "**44** distinct scripts (**46** event registrations)" — o 46
também está stale (vivo = 48) — e `:83` "**~12.000** collected cases"; e as
prosas de `:85-86` repetem 53, 44 e 46 FORA da tabela (os `TABLE_RULES`
casam célula de rótulo, então prosa não é alcançada por eles). §W1.5 já
prescreve o método certo — "censo = rodar o gate, não recitar sites" — e
§W0.3 também pede "censo COMPLETO"; a lista entre parênteses é justamente o
artefato que a regra proíbe, e ela erra.
*Mitigação:* apagar a enumeração ou marcá-la NÃO-EXAUSTIVA ("≥7; a fonte é
o gate"). Consequência se ficar: `docs/README.md` entra em `DOCS`
incompleto → `verify-counts` vermelho → **W0 bloqueia o próprio preflight
da rc.2**, que é exatamente o risco que o parágrafo tenta evitar.

**R3-VP3 — MEDIUM — ativar `approx` deixa uma métrica adjacente órfã, com divergência VIVA entre dois docs vigiados.**
Confirmei a aritmética do r13: coleta no escopo documentado = **14172**;
banda ±5% = **[13463, 14881]**; `~13,000` e `~13k` = 13000 → **abaixo do
piso**, logo `CLAUDE.md:73`, `README.md:60,187` e `docs/ARCHITECTURE.md:74`
realmente falhariam — a exigência do plano está certa. Mas a mesma linha
carrega uma segunda métrica **sem regra nenhuma**: contagem de ARQUIVOS de
teste. Vivo = **730**. `CLAUDE.md:73` diz "~730" (certo);
`docs/ARCHITECTURE.md:73` diz "| Test files | ~720 |" e a prosa de `:84`
diz "roughly 720" (stale) — dois docs vigiados discordando hoje, invisíveis
ao gate. E a prosa de `ARCHITECTURE:85` ("It is not 13,000 hand-written…")
fica factualmente errada assim que `:74` subir.
*Mitigação:* (i) incluir `ARCHITECTURE:73,84,85` no passe de refresh de
§W0.3 (o plano lista só `:74`); (ii) criar a métrica `test_files` — a
derivação já está escrita na própria célula Notes do `ARCHITECTURE:73`
(`git ls-files '*test_*.py' '*_test.py' | wc -l`), custo quase zero — ou
registrar a omissão DELIBERADAMENTE, nunca por silêncio.

**R3-VP4 — LOW — §W0.3 exige editar `CLAUDE.md`, que a §0 do próprio `CLAUDE.md` declara cache-stable.**
`CLAUDE.md:73` precisa subir de `~13,000` para dentro da banda. Mas
`CLAUDE.md` §0 ("Cache discipline") diz: os arquivos de Gate-1 — `CLAUDE.md`
incluído — "Do **not** edit them mid-session — only at an explicit
closeout." O plano não reconhece a regra em lugar nenhum.
*Mitigação:* uma frase em §W0.3 dizendo que a edição de `CLAUDE.md` é
agendada para o closeout da sessão de W0 (ou que o custo de re-boot do cache
é aceito explicitamente). Não muda o trabalho; muda o plano parar de violar
uma regra escrita sem dizer que está.

**R3-VP5 — LOW — o bloco `Scope:` da cerimônia virou grande demais para ser escrito à mão.**
O commit de W1 carrega agora: 7 superfícies canônicas + `ADR-155-AMEND-1`
(confirmei que `.claude/adr/ADR-*.md` É canonical,
`check_canonical_edit.py:178` — o plano acerta ao pôr o ADR na cerimônia) +
o refresh 188→189 em TODOS os sites alcançados pelos matchers de ADR
(§W1.5) + fiação de testes + arquivos livres. E `touched−scope=∅` é sobre o
commit inteiro (a §W1 já diz isso corretamente). Um `Scope:` de ~20 linhas
escrito de memória é a `feedback-closed-sets-must-be-derived-not-recalled`
aplicada ao artefato ASSINADO — e reescrever `approved.md` obriga a
re-assinar.
*Mitigação:* gerar o bloco `Scope:` mecanicamente a partir de
`git status --porcelain` da árvore staged, e conferir `touched−scope=∅`
ANTES de pedir a assinatura, não depois.

**R3-VP6 — LOW — duas imprecisões de citação que custam tempo na execução.**
(i) §OQ-3 cita `check-framework-updates.sh:82-103` sem caminho; o arquivo
está em **`.claude/scripts/`**, não em `scripts/` (todas as outras citações
do plano carregam o path). (ii) §W1 diz "a cerimônia inclui a rota de
kernel-override" sem nomear o slug. Verifiquei que não há pré-registro —
`CEO_KERNEL_OVERRIDE` aceita qualquer `[A-Za-z0-9._-]{1,120}` e o ACK é o
literal `I-ACCEPT` (`check_arbitration_kernel.py:380-394`) — então não é
bloqueio; mas os precedentes do repo usam slug nomeado por plano, e uma
cerimônia auditável deve fixar o seu no texto (ex.:
`PLAN-166-W1-RELEASE-YML-AWAIT-GATE`).

## Must-fix (blocking)

1. **Reordenar §W2.2 e §W2.4** para verdito-commit → push main → CI verde →
   `preflight` → tag (R3-VP1). É a última instância da classe "preflight
   valida uma árvore que não é a taggeada" — e o plano só pode declarar a
   perna fechada em §Riscos depois disso.
2. **Apagar (ou marcar como não-exaustiva) a lista `151/53/44/22/171/67/~670`
   em §W0.3** (R3-VP2), mantendo a instrução de derivar do gate. Como está,
   o número "SETE" é falso e o doc entraria em `DOCS` incompleto,
   avermelhando W0.
3. **Estender o passe de §W0.3 a `docs/ARCHITECTURE.md:73,84,85`** e decidir
   explicitamente sobre a métrica `test_files` — criar a regra ou registrar
   a omissão (R3-VP3). Hoje há divergência VIVA 720 vs 730 entre dois docs
   vigiados.
4. **Reconhecer a disciplina de cache do Gate-1 para a edição de
   `CLAUDE.md:73`** (R3-VP4): uma frase dizendo quando a edição acontece.
5. **Dizer que o `Scope:` do sentinel é GERADO da árvore staged**, não
   redigido (R3-VP5).

## Nice-to-have (advisory)

1. Corrigir o path de `check-framework-updates.sh` e nomear o slug de
   kernel-override (R3-VP6).
2. §W2.4: com a reordenação do must-fix 1, vale afirmar no checklist que
   `preflight --stable` roda sobre EXATAMENTE o commit que será taggeado —
   a frase é o que impede a próxima pessoa de "otimizar" a ordem de volta
   (mesmo raciocínio que o plano já aplica ao `already_published` em §OQ-1).
3. §Deferred: o item "família script livre que decide gate de release" agora
   tem um terceiro membro nomeável — `verify-counts.sh` ganha o `approx`
   nesta release e passa a decidir bloqueio de preflight sobre uma banda.
   Registrar o membro novo junto com os dois já listados.
4. §W1.5 fala em "atualizar o valor no `verify-counts.sh` (tolerance=0)".
   Vale explicitar que isso é o **derivado** de ADRs, não uma constante
   digitada — senão a frase se lê como "hardcode 189".

## Unseen by the original plan

1. **A ordem preflight-vs-verdito** (R3-VP1). Não era visível nos rounds 1-2
   porque `preflight --stable` só entrou no r15 e a exigência de commitar o
   verdito antes da tag só entrou no r3 — os dois fixes são corretos
   isolados e incompatíveis na ordem em que foram compostos. É o único
   defeito que encontrei atribuível à **composição** dos 17 rounds, e não a
   um round individual.
2. **`docs/README.md:79` carrega `46 event registrations`** (vivo = 48) e
   **`:83` carrega `~670 test files`** (vivo = 730) — nenhum dos dois está
   na lista do r6, e ambos entram em vigor no instante em que o doc entra em
   `DOCS`. Verificado linha a linha.
3. **A métrica `test_files` não existe no gate** e os dois docs que a citam
   já divergem (R3-VP3). O plano cria maquinaria nova (`approx`) para a
   métrica vizinha na MESMA linha de tabela e passa ao lado desta.
4. **`ARCHITECTURE:85` é prosa que cita o número cru `13,000`** dentro de um
   parágrafo explicativo ("It is not 13,000 hand-written…"). Não é um claim
   de contagem no sentido do gate, mas fica FALSO quando `:74` subir para
   ~14k. Refresh de número tem cauda de prosa; o plano trata as tabelas e
   esquece as caudas — foi exatamente assim que o `README.pt-BR.md:60` e o
   `docs/README.md:85-86` viraram findings.

## What I would NOT change

1. **A cerimônia única com as 7 superfícies + kernel-override.** Verifiquei
   as duas classificações novas: `.github/workflows/release.yml` é entrada
   EXATA de `_KERNEL_PATHS` (`check_arbitration_kernel.py:134`) e
   `.claude/adr/ADR-*.md` é canonical (`check_canonical_edit.py:178`). A
   §W1 está certa e a nota "dois conceitos distintos" (superfícies que
   exigem sentinel × bloco `Scope:`) fechou exatamente o meu Unseen 3 do
   round 2.
2. **A semântica de candidato do poll (r14/r16).** "Runs não-candidatos são
   IGNORADOS, nunca BLOCK" é a diferença entre um gate que funciona e um que
   perde a corrida contra a própria presença na lista de runs do SHA. E o
   fixture GRANT obrigatório é a defesa contra a implementação
   sempre-BLOCK — controle positivo no lugar certo.
3. **A condicionalidade por ENTREGA REAL, não por ceremony (r17).** É mais
   forte do que o gate de ceremony que eu pedi no round 1: `install_one` é
   skip-if-exists, então ceremony sozinha ainda inventariaria o `SPEC/v1`
   PRÓPRIO de um adopter maintainer como framework-owned, com
   `uninstall.sh` podendo deletá-lo. Correto, e o fixture de SPEC
   pré-existente é o teste certo.
4. **O marcador como arquivo RASTREADO (r6, Forma A).** A versão
   "gerada-só-no-destino" tornava as duas proteções inalcançáveis no
   checkout de release. Rastreado, o 12º site do bump e o assert
   incondicional no `release.yml` são reais. Não voltar atrás.
5. **`check_tier_a_npm_version_match` NÃO adotar o marcador.** Em árvore de
   adopter o `package.json` da raiz é o do APP; comparar marcador do
   framework com versão do app seria false-red permanente. É a mesma
   assimetria raiz-vs-namespace que motivou não tocar o `VERSION` — bem
   aplicada de novo.
6. **O predicado de 4 oráculos e o `--restamp` excluindo o fast-path (r14).**
   Sem a exclusão, `--restamp` seria letra morta no cenário que o justifica.
   Boa pegada.
7. **A decisão registrada em §W0.5 refutando o P1 do r3.** Excluir os
   arquivos de bump do inputs-manifest É deliberado — incluí-los quebraria a
   reprodutibilidade do replay. O plano refuta com razão e pina a exclusão
   por TESTE em vez de mudar o manifest (sem entrada nova no escopo da
   cerimônia). É C4 aplicado a um achado do próprio revisor.
8. **`budget_sessions: 3-4` e a estrutura W0-pesado / W1-canônico.** Com a
   autoria dos testes em §W0.6 (meu must-fix 5 do round 2, aplicado), a
   distribuição está certa: o material experimental fica em superfície livre
   e a cerimônia recebe só o que exige assinatura.

---

## Verificação factual do texto novo (C4 — 12 afirmações checadas contra a árvore)

| Afirmação do plano | Onde verifiquei | Resultado |
|---|---|---|
| `release.yml:659` valida verdito POR TAG na árvore taggeada | `VERDICT_FILE=".claude/governance/pair-rail-verdict-${GITHUB_REF_NAME}.md"`, hard-block por default | ✅ |
| `release.yml` é entrada exata de `_KERNEL_PATHS` | `check_arbitration_kernel.py:134` | ✅ |
| `.claude/governance/*.txt` é canonical (erratum do consensus r1) | `check_canonical_edit.py:232` | ✅ |
| `smoke-install.yml` usa `fetch-depth: 1` (pin v1.2.0 não resolve) | `smoke-install.yml:53` | ✅ |
| `--no-replay` pula a leitura de ceremony | `upgrade.sh:292-295` (`REPLAY=0`) + `:681` (bloco inteiro sob `REPLAY -eq 1`) | ✅ |
| `manifest-set` emite `PROTOCOL.md` incondicionalmente | `_framework_manifest_set.sh:97` | ✅ |
| `doctor.sh` chama `_framework_manifest_files` sem contexto de ceremony | `doctor.sh:618` (source em `:186-188`) | ✅ |
| update-checker resolve o `VERSION` da RAIZ → loop `behind-minor` | sobe a árvore procurando `VERSION` (`:82-96`), lê em `:103` | ✅ (path é `.claude/scripts/`, não `scripts/`) |
| coleta no escopo documentado = 14.172 | `python3 -m pytest --collect-only -q` (Makefile `test-collect`, sem path → `pytest.ini`) | ✅ **14172** exato |
| banda ±5% reprova `~13k`/`~13,000` | 14172×0.95 = 13463,4 > 13000 | ✅ |
| `DERIVED_TESTS` usa população diferente | `verify-counts.sh:160` usa `pytest --collect-only -q .claude/` | ✅ (populações distintas) |
| ADR count 188 → 189 com o AMEND | `ls .claude/adr/ADR-*.md` = 188; `ADR-*-AMEND-*.md` casa o glob | ✅ |

### Round-2 must-fix — todos fechados

| # (round 2) | Onde fecha | Status |
|---|---|---|
| 1. `npm-trusted-publisher.txt` no escopo | §W1 cabeçalho (com erratum nomeado) | ✅ |
| 2. 4º oráculo no predicado | §OQ-2 1º bullet | ✅ (com o racional que eu dei) |
| 3. `INSTALL.md:627` com AC + wave | §W0.4 ("AQUI em W0; sem condicional") + AC-6 | ✅ |
| 4. Banda declarada | §W0.3 + AC-5 (`approx`, ±5%, justificada) | ✅ |
| 5. Autoria dos testes em W0 | §W0.6 | ✅ |
| 6. Endereço dos testes | §W0.6 "Endereços" | ✅ |
| 7. Grep de superfícies vivas + evidência imutável | AC-6 | ✅ |

### Veredito sobre a pergunta do round 3

**Coerente: sim.** Cruzei OQ-1×OQ-2 (candidato do poll × no-op do bump ×
delta ancorado no `parent_sha`), OQ-2×OQ-3 (marcador como 12º site do bump ×
`VERSION_SITES` × assert incondicional no `release.yml`), OQ-3×OQ-4
(condicionalidade por entrega real × fixture de 2º upgrade × ceremony no
doctor) e §W1×§W0 (o que exige sentinel × o que é livre). Não achei
contradição entre as decisões.

**Executável: sim, com a reordenação.** O escopo é grande mas está
corretamente estratificado — o experimental em W0 livre, o assinado em W1.
O único item que eu não deixaria passar para execução como está é a
sequência de §W2, porque é a parte do plano que efetivamente CORTA a
release, e ela ainda contém a forma do defeito que o plano existe para
fechar.
