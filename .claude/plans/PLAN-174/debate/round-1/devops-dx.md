---
round: 1
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
agent_persona: DevOps Engineer (Principal)
generated_at: 2026-08-20T00:00:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- W1-W2 mina uma hipótese REAL: verifiquei diretamente os 27 patches em
  `.claude/plans/PLAN-166/repass-rc3-scripts/` e as 6 classes citadas
  aparecem de fato, com linhas concretas (ex.: `rc engolido` em
  `diff-cures-round10.patch:1294-1296`; `|| true` mascarando falha em
  `diff-cures-round10.patch:97,227,843`; `tail -1` em VERDICT em
  `diff-cures-round10.patch:97,133-143`; guard de `git add` de diretório
  em `diff-cures-round10.patch:355,384,439,926-931`; symlink em
  `diff-cures-round10.patch:154,172-176,318,382`). A tese não é
  especulação — é um catálogo extraível hoje.
- Onde é fraco: a palavra "pre-commit" no AC do W2 não tem referente
  mecânico neste repo (não há git hook nativo — `.git/hooks/` só tem
  `.sample`; o próprio ADR-143 documenta que "nosso pre-commit
  governance é um hook PreToolUse do Claude Code"), e o glob
  `.claude/plans/*/OWNER-*.sh` tem lacunas DEMONSTRÁVEIS contra a
  população real de scripts já landados no repo.
- Onde é forte: os guard-rails do §2b (positive control, zero
  falso-positivo em históricos, fallback "W1/W2 valem sozinhos" no §3)
  já dão a estrutura certa para consertar os dois pontos acima sem
  reabrir o plano.

## Risks

1. **R-DX1 — "pre-commit" é ambíguo e a resolução muda o custo real.**
   Severidade: HIGH.
   Se "pre-commit" significa um NOVO hook PreToolUse registrado em
   `.claude/settings.json`, o arquivo cai em `.claude/hooks/*.py` —
   que é canonical-guarded (`_CANONICAL_GUARDS` em
   `check_canonical_edit.py:139`) e portanto landa por cerimônia
   Owner-GPG completa (sentinel + anchor-sha + dois rails de signer),
   não por commit direto. Se ao invés disso "pre-commit" significa
   "script que o Owner roda manualmente antes de commitar", ele não
   está WIRED a nada e o AC "roda em pre-commit E CI" fica falso por
   metade. Nenhuma das duas leituras está escrita no plano.
   Mitigação: o plano precisa dizer explicitamente qual das duas é, e
   se for a primeira, o budget de W2 precisa somar o custo de
   cerimônia (não é grátis — ver ADR-143, ADR-186).

2. **R-DX2 — `.claude/scripts/local/` está documentado como
   NUNCA-CI.** Severidade: HIGH.
   O README de `.claude/scripts/local/` diz literalmente: "Scripts
   that run on the Owner's machine only, **never as part of CI** or
   adopter installs." Se o lint do W2 for depositado ali (que é o
   local não-canônico, editável sem cerimônia — a leitura óbvia da
   pergunta 1 da proposta), ele estruturalmente NÃO PODE satisfazer a
   metade "roda em CI" do AC, por convenção já em vigor neste repo.
   Mitigação: a cópia CI-facing tem de morar em `.claude/scripts/`
   top-level (com testes, como `check-contamination.sh` e
   `verify-counts.sh`) e ser chamada de `validate.yml` no mesmo padrão
   já usado (`bash .claude/scripts/check-contamination.sh`,
   `.github/workflows/validate.yml:192`).

3. **R-DX3 — o glob `.claude/plans/*/OWNER-*.sh` já erra contra a
   população real, hoje.** Severidade: HIGH.
   Levantei os scripts OWNER-* efetivamente rastreados no repo:
   14 arquivos sob `.claude/plans/PLAN-{158,166,167,168,169,179,180}/`
   batem no glob (incluindo maiúsculo `OWNER-*.sh`), MAS:
   - `.claude/plans/PLAN-158/owner-ga-ceremony.sh` e
     `owner-rc-ceremony.sh` são **minúsculos** — em runner Linux (CI é
     case-sensitive) o glob `OWNER-*.sh` não casa; em macOS local
     (case-insensitive por padrão) casaria — um gap dev/CI clássico.
   - `.claude/plans/PLAN-160/land-plan160.sh` e
     `PLAN-161/land-plan161.sh` são scripts de corte da MESMA classe
     funcional (bash de cerimônia one-shot) mas sem prefixo `OWNER-` —
     o glob nunca os vê.
   - `scripts/local/historical/OWNER-CEREMONY-PLAN-094-WAVE-A.sh` e
     `OWNER-CEREMONY-S82-V1120.sh` estão fora de `.claude/plans/*/` —
     o glob nunca os vê.
   - `~/canhada-labs/OWNER-RATIFY-S302.sh` (citado na memória do
     projeto, S315) está fora do repo inteiramente — nenhum gate
     local/CI pode vê-lo, por construção.
   Consequência prática: o AC "zero falso-positivo sobre históricos"
   fica fácil de satisfazer pelo motivo ERRADO — o glob simplesmente
   não enxerga boa parte do universo real, então "zero FP" pode
   significar "zero cobertura" em vez de "zero violação".
   Mitigação: no W1, rodar a extração do catálogo contra a população
   REAL (`find . -iname 'owner-*.sh' -o -iname 'land-plan*.sh'`, não
   só o glob do plano) e declarar as 4 classes de gap acima como
   residual NOMEADO — exatamente como o CLAUDE.md §5 já faz para
   outros gates deste repo, não deixar implícito.

4. **R-DX4 — sobreposição não resolvida com PLAN-183 A2.**
   Severidade: MEDIUM.
   `PLAN-183-adopter-fitness.md` linha 51 nomeia A2 como "Steps do
   template de CI que só rodam no repo do framework" — DEFEITO VIVO,
   alvo do PLAN-183 W2. Conferi `templates/.github/workflows/
   validate.yml.template`: não tem NENHUM guard de auto-detecção
   "estou no repo do framework". Se o W2 deste plano adicionar um step
   de lint em `.github/workflows/validate.yml` (vivo) sem espelhar em
   `templates/.github/workflows/validate.yml.template` (ou sem um
   guard de auto-detecção), ele fabrica uma instância NOVA da classe
   A2 antes do PLAN-183 W2 sequer começar — e o waiver S316 já
   sequencia 174 W1-W2 ANTES de 182/183.
   Mitigação: ver Must-fix #4.

## Must-fix (blocking)

1. Resolver R-DX1: o plano precisa declarar, por escrito, se o
   "pre-commit" do AC W2 é (a) um hook PreToolUse novo em
   `.claude/hooks/` (custo = cerimônia canonical-edit completa,
   somado ao budget) ou (b) um script não-wired que o Owner roda
   manualmente (e nesse caso o AC não pode dizer "roda em pre-commit"
   sem qualificar "roda quando invocado manualmente"). As duas leituras
   têm custo e garantia MUITO diferentes — a proposta não pode deixar
   isso para a implementação decidir sozinha.
2. Resolver R-DX2: a cópia CI-facing do lint W2 vai para
   `.claude/scripts/` (top-level, testada), NÃO para
   `.claude/scripts/local/` — que é documentado como nunca-CI pelo
   próprio README do diretório. Se a leitura (a) do Must-fix 1 for a
   escolhida, o hook em `.claude/hooks/` e o script CI em
   `.claude/scripts/` compartilham a MESMA lógica de detecção de
   classe (uma lib importada por ambos), para não duplicar (e
   divergir) as 6 regras.
3. Resolver R-DX3: o W1 mede a extração contra a população REAL de
   scripts de cerimônia (não só o glob citado na proposta), e o
   catálogo nomeia explicitamente os casos fora do glob (minúsculo,
   sem prefixo OWNER-, fora de `.claude/plans/`, fora do repo) como
   residual conhecido — do jeito que este repo já documenta residuais
   em outros gates fail-closed.
4. Resolver R-DX4: OU (a) landar o step de CI do W2 simultaneamente
   no workflow vivo e no template, atrás de um guard de
   auto-detecção "é o repo do framework" (mesma classe de guard que
   `check-contamination.sh` já teria que resolver para o PLAN-183),
   OU (b) escopar W2 para hook/pre-commit apenas nesta rodada e
   DEFERIR o wiring de CI até o PLAN-183 W2 landar seu próprio gate de
   drift template-vs-vivo — reaproveitando esse gate em vez de
   competir com ele. Recomendo (b): mais barato, e o próprio §3 do
   plano já aceita "W1/W2 valem sozinhos" sem a metade CI.
5. **Escape hatch nomeado para o gate fail-closed do W2.** O plano não
   tem rota de recuperação para um falso positivo do lint bloqueando
   um corte real sob pressão de horário (o cenário mais provável, dado
   o histórico de cortes de madrugada citado no próprio plano). Seguir
   o padrão já estabelecido neste repo (CLAUDE.md §4, o par
   fail-open-infra / fail-closed-input com rota de recuperação
   nomeada, ex. `CEO_SENTINEL_UNLOCK` do ADR-186): um env var
   específico + razão OBRIGATORIAMENTE logada no audit trail, nunca um
   `|| true` silencioso — que seria irônico, dado que é exatamente uma
   das 6 classes que o lint está caçando.

## Nice-to-have (advisory)

1. Para os casos-vermelho do CI (AC do W2), usar excertos REAIS
   (redigidos) dos rounds que já achei — ex. o padrão `tail -1` de
   `diff-cures-round10.patch:97` ou o guard de `git add` de
   `diff-cures-round10.patch:355` — em vez de reproduções sintéticas
   minimalistas. Reproduções minimalistas historicamente sub-
   especificam a forma real do bug neste repo (a lição de "5 de 5
   números derivados por grep estavam errados" se aplica aqui: um
   caso-vermelho fabricado à mão tende a testar a forma que o autor
   IMAGINOU, não a forma que apareceu de verdade).
2. Metodologia de extração do W1 mais barata que ler os ~53K linhas
   dos 27 patches manualmente: sweep por `grep -l` das 6 assinaturas
   conhecidas (`|| true`, `tail -1`, `rc=`, `git add` sem `--`,
   `symlink`/`-L`, ausência de `comm`/set-diff) para localizar
   candidatos, leitura pontual só dos hits — é como fiz a verificação
   acima e cobriu as 6 classes com ~6 chamadas de `grep`. Deixar isso
   como o método documentado no catálogo, não uma leitura linear.
3. `SCRIPTS-MANIFEST.sha256` já existe no diretório de evidência —
   reusar esse padrão de manifesto pinado para o baseline de waiver do
   Must-fix/Q2 (ver resposta à questão 2 abaixo), em vez de inventar
   um formato novo.

## Unseen by the original plan

1. O custo de cerimônia para adicionar um novo arquivo canonical-
   guarded (`.claude/hooks/*.py`) não está no budget de 100-150k para
   W1-W2 se a leitura (a) do Must-fix 1 for a escolhida — cerimônias
   Owner-GPG deste porte historicamente rodam de 1 a várias rodadas de
   pair-rail (ex.: o próprio PLAN-166 repass teve 27 rounds até GO).
   Se o hook realmente precisar de sentinel + dois rails de signer, o
   budget de sessões (3-5) fica otimista.
2. `.claude/scripts/local/generate-ceremony.sh` (o gerador que o W3
   deste MESMO plano vai estender) já teria a lógica de "quais paths
   são canonical" via `--canonical-paths` validado contra
   `check_canonical_edit.py::_CANONICAL_GUARDS`. O W2 deveria, no
   mínimo, deixar registrado que o lint de classes e o gerador do W3
   vão eventualmente precisar compartilhar a MESMA fonte de verdade
   sobre "o que é um script de cerimônia válido" — hoje são dois
   sistemas paralelos (glob do lint vs. flags do gerador) que podem
   divergir silenciosamente quando W3 chegar.
3. `actionlint.yml` já estabelece, NESTE repo, o precedente de um lint
   "advisory / continue-on-error" para achados estilísticos versus um
   lint hard-fail em `validate.yml` para achados que a governança trata
   como reais. As 6 classes do W1 são histórico de VERDICT: NO-GO real
   (não estilo) — o plano deveria citar esse precedente explicitamente
   para justificar por que o W2 vai no padrão hard-fail de
   `validate.yml`, não no padrão advisory de `actionlint.yml`. Hoje
   isso fica implícito.

## What I would NOT change

1. O guard-rail do §3 ("nenhuma mudança no CONTEÚDO das garantias de
   cerimônia") está certo e não precisa de ajuste — mantém o lint como
   camada de detecção, não como substituto do sentinel/anchor-sha/dois-
   rails-de-signer.
2. O fallback explícito "W1/W2 valem sozinhos" (§3) é a decisão certa
   de design — dá ao W2 uma saída limpa sem depender do gerador (W3) ou
   do piloto (W4), que é exatamente o que sustenta minha recomendação
   de adiar a metade CI do W2 (Must-fix 4b) sem invalidar o resto do
   plano.
3. A escolha de extrair o catálogo de ROUNDS REAIS (PLAN-166) em vez de
   uma lista de antipadrões genéricos de bash está certa — verifiquei
   que as 6 classes citadas são reais e specíficas deste histórico, não
   uma lista de shellcheck genérica reembalada.

## Respostas às 4 questões abertas da proposta

1. **Layout**: catálogo em `.claude/plans/PLAN-174/catalog.md` está
   correto e segue a convenção de material-irmão em `PLAN-NNN/`. Para o
   lint: a cópia CI-facing vai em `.claude/scripts/` (testada,
   invocada de `validate.yml` no padrão já usado por
   `check-contamination.sh`/`verify-counts.sh`) — NÃO em
   `.claude/scripts/local/`, que o próprio README declara "never as
   part of CI". Se além disso for necessário feedback em tempo de
   autoria (o "pre-commit" real deste repo, via PreToolUse hook), essa
   segunda cópia vai em `.claude/hooks/` e herda o custo de cerimônia
   canonical-guarded — orçar esse custo separadamente (ver Must-fix 1).
2. **Fail-closed vs baseline**: baseline PINADA por entrada individual
   (arquivo + linha + classe + justificativa de 1 linha), no molde do
   `SCRIPTS-MANIFEST.sha256` que já existe no corpus de evidência —
   nunca um exclude por diretório/glob (o `repass-rc3-scripts/` é
   exatamente o corpus que o W1 está minerando; excluir o diretório
   inteiro esconderia violação real futura ali também). O lint diffa
   contra esse conjunto pinado: violação NOVA em arquivo antigo = 
   vermelho; violação já catalogada = grandfathered e visível no
   relatório, nunca silenciosa.
3. **Fronteira W2/CI**: SIM, cruza com PLAN-183 A2 diretamente — ver
   R-DX4. Recomendo escopar o W2 desta rodada para hook/pre-commit
   apenas e diferir o wiring em `.github/workflows/` até o PLAN-183 W2
   landar seu gate de drift template-vs-vivo, reaproveitando-o em vez
   de abrir uma segunda frente que o PLAN-183 teria que descobrir e
   corrigir depois.
4. **Escopo do glob**: NÃO cobre — confirmado empiricamente contra os
   16 scripts OWNER-*/land-plan* já rastreados no repo (2 minúsculos,
   2 sem prefixo OWNER-, 2 fora de `.claude/plans/*/`) mais o caso já
   citado na proposta (`~/canhada-labs/` fora do repo). O catálogo do
   W1 deve declarar essas 4 lacunas como residual nomeado, não deixar
   a leitura de "zero falso-positivo" mascarar zero-cobertura.

## Estimativa de esforço (ADR-081 — tokens + sessões)

- W1 (catálogo): 60-90k tokens, 1 sessão — a extração por sweep de
  `grep` (não leitura linear dos 53K linhas) é o método barato; o custo
  principal é achar e citar exemplo real por classe + escrever
  caso-vermelho executável para cada uma.
- W2, leitura (b) só-hook-de-autoria (sem cerimônia canonical):
  40-70k tokens, 1 sessão.
- W2, leitura (a) com hook novo em `.claude/hooks/*.py` (custo de
  cerimônia canonical-edit incluído — sentinel + pair-rail no hook):
  90-160k tokens adicionais, 1-2 sessões adicionais — ESTE custo não
  está refletido no budget atual de 100-150k para W1+W2 combinados.
  Se a leitura (a) for a escolhida, o budget total de W1-W2 precisa
  subir para ~150-250k / 2-3 sessões, não 100-150k / implícito em 1.
- `external_wait`: nenhum novo além do já registrado no plano (waiver
  S316); todo o trabalho acima é tempo de agente, sem espera externa.
