---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (none — profile synthesized from the team.md skill-map row)
generated_at: 2026-08-20T17:47:46Z
---

## Verdict

ADJUST — a tese está certa e a evidência a sustenta, mas o **instrumento
proposto para a W2 está errado por construção** e a taxonomia da W1
descreve a minoria dos achados. Executar como escrito gasta o orçamento
na classe menos frequente e deixa a mais cara intocada.

## Summary (≤ 3 bullets)

- O plano quer trocar revisão de 42KB de bash descartável por revisão de
  input declarativo + gerador amortizado. A direção é correta e a W4 tem
  critério de falha honesto (`§3`: se não reduzir ≥40%, reportar NEGATIVO
  e manter W1/W2).
- **Forte:** o corpus é real, on-disk e reproduzível (27 rodadas de
  veredito em `repass-rc3-scripts/`), e a doutrina de não mexer no
  CONTEÚDO das garantias (`§3`) protege a fronteira que importa.
- **Fraco:** medi as 27 rodadas achado a achado — as 6 classes nomeadas
  cobrem **~28 de ~83 achados (~34%)**, não 40-50%, e a classe DOMINANTE
  (~15 achados: *binding de evidência por NOME em vez de CONTEÚDO*) não
  está na lista e **não é detectável por lint sintático**. Pior: o
  catálogo da W1 já existe em prosa, não-enforçado, desde abril.

## Risks

**R-VP1 — CRITICAL — A W1 vai reescrever um catálogo que já existe, sem
saber que existe.**
`docs/OWNER-CEREMONY-CONTRACT.md` (227 linhas, Sessão 75, 2026-04-29)
já é o contrato do que todo `OWNER-*.sh` DEVE fazer, e nasceu da mesma
classe (Codex Finding 10: "fail-open misadvertised as fail-closed"). Ele
já manda: fail-closed por padrão (§1), sem passes silenciosos (§4),
idempotência/resume (§5 + contrato v2), rollback transacional; e já
nomeia como anti-padrão `|| true` em bloco que enforça e `set +e` sem
restaurar. **Todas essas regras escritas foram violadas no trem rc.3.**
`grep -rln "OWNER-CEREMONY-CONTRACT"` sobre `*.py`/`*.sh`/`*.yml` =
**zero arquivos**. É a classe-assinatura deste repo: contrato verde
porque ninguém o executa.
*Mitigação:* redefinir o entregável da W1 como **DELTA** — quais itens
do contrato existente não têm enforcement, e quais classes o contrato
ainda não nomeia. O catálogo novo referencia o contrato; não o duplica.
Se duplicar, o repo passa a ter duas fontes de verdade divergentes sobre
cerimônia, que é exatamente a lição `cura no corpo ≠ cura nas
REFERÊNCIAS` em forma nova.

**R-VP2 — HIGH — A W2 propõe escrever um lint novo quando o lint que
falta já está instalado e apenas não enxerga o alvo.**
`.github/workflows/validate.yml:306-310` roda shellcheck sobre
`find .claude/scripts .claude/hooks -name '*.sh'`. Os scripts de
cerimônia moram em `.claude/plans/PLAN-NNN/OWNER-*.sh` — **fora das duas
raízes**. Nenhum dos 6 scripts do trem v1.3.0 foi visto pelo shellcheck,
nunca. (Detalhe revelador: a exclusão `-not -path
'.claude/scripts/owner-ceremony/archive/*'` aponta para um diretório que
**não existe** — alguém já assumiu que cerimônia moraria em escopo
coberto.) Isto é literalmente
`feedback-guard-green-because-files-are-untracked`: o guard nunca
respondeu "ele vê o meu alvo?".
*Mitigação:* a W2 começa por **estender o escopo**, não por escrever
código. Ver M-2 para o desenho e o controle positivo que já rodei.

**R-VP3 — HIGH — O AC "zero falso-positivo sobre históricos" é onde o
orçamento morre, e ele conflita com fail-closed.**
São 16 `OWNER-*.sh` vivos em 7 planos + 2 em `scripts/local/historical/`.
Exigir zero-FP fail-closed sobre todos força ou regras fracas demais para
pegar as classes, ou uma rodada de waivers por arquivo. Já medi o
tamanho do problema: com `--enable=all` o shellcheck emite **422 SC2250 +
91 SC2292** só nos 3 scripts do round 5 — ruído que mata qualquer gate.
*Mitigação:* separar os dois papéis. **Bloqueante** (fail-closed, zero-FP
exigido) só para as classes com detecção exata e consequência P0.
**Advisory** (nunca bloqueia, imprime checklist) para as classes que
over-firam. Baseline pinada por sha256 de arquivo, com data de expiração
e um teste que falha se a baseline crescer — nunca waiver por nome de
arquivo sem prazo.

**R-VP4 — HIGH — A `§2` não menciona o defeito mais caro do trem: o loop
de fechamento da própria revisão.**
Rounds 12 e 25 (ambos P0/P1) acharam o mesmo: a rodada de revisão dos
scripts entra no conjunto que os templates ASSINADOS da cerimônia
enumeram. Somar ao `MANIFEST-cures.sha256` quebra set-equality no delta
guard depois do commit 2; não somar faz o G0 rejeitar; regenerar os
templates cria mais uma versão não-revisada e mais uma rodada — laço
infinito. A cura que o próprio reviewer propôs no round 25 é
**estrutural**: evidência de revisão de cerimônia em diretório
independentemente pinado, FORA do delta manifest da release.
*Mitigação:* isto é requisito de DESENHO do gerador (W3) e nenhum lint o
alcança. Registrar agora como AC da W3 no plano, enquanto a memória do
trem está fresca. Se ficar para a W3 sem estar escrito, ele é reinventado
no primeiro corte da v1.4.0.

**R-VP5 — MEDIUM — O template canônico do contrato é ele próprio gerador
de uma das 6 classes.**
O contrato prescreve `set -u; set -o pipefail` (sem `-e`). No trem real:
`repass-ga/run-ga-repass.sh:15` usa `set -uo pipefail` → gerou os achados
fail-open dos rounds 6, 7, 13, 19 e 25; `OWNER-RC3-CUT.sh:29` usa
`set -euo pipefail` → gerou o **P0 do round 28** (`_grv_rc=$?`
inalcançável porque o `errexit` mata o script antes). **As duas metades da
mesma cerimônia escolheram disciplinas opostas de erro e as duas
escolhas produziram defeito.** A classe verdadeira não é "`|| true`
mascarando falha"; é "não existe disciplina única de propagação de erro,
e o contrato não decide".
*Mitigação:* ADR curto que fixa UMA disciplina para cerimônia e nomeia o
idioma obrigatório para capturar rc esperado-não-zero (o `if`-wrapper ou
o `set +e` escopado com restore imediato). O lint enforça a decisão do
ADR; sem ADR, o lint não tem o que enforçar.

**R-VP6 — MEDIUM — A baseline de rounds da W4 não é derivável do disco.**
O plano fixa 38 rounds / 31 em scripts. Contagem comportamental:
**44** arquivos de veredito em 6 diretórios `repass-*` — 27 em
`repass-rc3-scripts/`, 7 em `repass-rc3-cures/`, 5 em `repass-r2/`, 2 em
`repass-ga/`, 2 em `repass-ga-rc2-NOGO/`, 1 em `repass-r1/`. A RAZÃO se
sustenta (27/34 ≈ 79% vs os 82% alegados), o denominador não. O critério
de sucesso da W4 (`≥40%`) divide por esse número.
*Mitigação:* congelar a baseline como **contagem derivada de um comando
citado no plano**, com o comando no próprio AC. Não é da W1, mas a W1 é
onde o corpus é aberto — o custo marginal é ~zero agora e alto depois.

**R-VP7 — LOW — A classe de exec-bit já reincidiu DEPOIS do trem que
originou o plano.**
Rounds 8, 9 e 12 acharam "modo git fora do binding assinado". Em S314 os
fix-forwards `6f7f20e` e `45c75e3` existiram exatamente para zerar exec
bits (755→644) pós-land. A classe não é histórica; é ativa.
*Mitigação:* é a candidata mais barata a regra **bloqueante** da W2 —
detecção exata, consequência real, zero ambiguidade.

## Must-fix (blocking)

1. **W1 vira DELTA, não catálogo novo.** Primeiro entregável: mapa
   `regra escrita em docs/OWNER-CEREMONY-CONTRACT.md → tem enforcement?
   (arquivo:linha | NENHUM)`. Só depois as classes que o contrato não
   nomeia. AC adicional: o catálogo não redefine nenhuma regra que o
   contrato já define; referencia. (R-VP1)

2. **Censo do instrumento existente ANTES de escrever lint, com o
   controle positivo que já rodei.** Reconstruí as versões do round 5 a
   partir de `payload-cures-round5.redacted.txt` (as ceremony files vêm
   como diffs vs `/dev/null`, então o texto integral está lá) e medi:
   - `shellcheck -S warning` (o ajuste EXATO do CI hoje): **1 achado**
     nos 3 scripts somados. Inútil para esta classe.
   - `shellcheck --enable=check-extra-masked-returns -S style`: SC2312
     acusa `run-ga-repass.sh:26` —
     `[ -z "$(git -C "$WT" status --porcelain)" ]` — que é **exatamente
     o P1 que o round 17 achou** ("failed `git status` com stdout vazio é
     lido como worktree limpa"). Um achado que custou uma rodada Codex
     inteira **doze rodadas depois** era mecanicamente detectável na
     rodada 5, por ferramenta de prateleira, com uma flag.
   A W2 portanto é, na ordem: (a) estender o `find` do
   `validate.yml:306` para cobrir `.claude/plans/*/OWNER-*.sh` e remover
   a exclusão vacuosa de `owner-ceremony/archive/`; (b) habilitar
   **cirurgicamente** as optional checks que mapeiam para as classes
   (`check-extra-masked-returns` para rc-engolido; `SC2154` para o P0 do
   round 21, `NID` usado sem atribuição sob `set -u`); (c) só então
   escrever Python para as 2-3 classes que o shellcheck não expressa
   (set-equality de manifesto, `git add` de diretório, variável de guarda
   atribuída e nunca lida). **Nunca `--enable=all`** — 422 SC2250 + 91
   SC2292 nos 3 scripts. (R-VP2, R-VP3)

3. **Separar bloqueante de advisory no desenho, não na operação.** Duas
   listas explícitas no catálogo da W1, cada classe marcada
   `BLOCKING | ADVISORY` com justificativa. O AC de zero-FP vale só para
   a lista BLOCKING. A lista ADVISORY tem AC oposto e honesto: taxa de
   disparo medida sobre os históricos, publicada no catálogo (SC2312
   dispara 18× nos 3 scripts do round 5 contra ~7 ocorrências reais da
   classe — ~2,5× de over-fire; isso é checklist de revisor, não gate).
   (R-VP3)

4. **Registrar o loop de fechamento como AC da W3 agora.** Uma linha na
   `§2` do plano: a cerimônia gerada deve emitir a evidência de revisão
   dos PRÓPRIOS scripts em diretório pinado independentemente, fora do
   delta manifest da release. Citar rounds 12 e 25 como origem. Não é
   trabalho da W1/W2 — é escrituração de 5 minutos que impede
   reinvenção. (R-VP4)

5. **ADR de disciplina de erro em cerimônia, antes do lint.** Fixar `-e`
   sim ou não, e o idioma obrigatório de captura de rc esperado.
   Justificativa gravada: `run-ga-repass.sh` (sem `-e`) e
   `OWNER-RC3-CUT.sh` (com `-e`) produziram defeitos opostos no mesmo
   trem. Sem essa decisão, as regras "`|| true`" e "rc engolido" do
   catálogo são incoerentes entre si. (R-VP5)

## Nice-to-have (advisory)

1. Reconciliar as **três declarações de localização divergentes** num
   único lugar: o contrato diz `OWNER-*.sh` (raiz do repo) ou
   `.claude/scripts/owner-ceremony/`; o `validate.yml` exclui
   `.claude/scripts/owner-ceremony/archive/*`; a realidade é
   `.claude/plans/PLAN-NNN/OWNER-*.sh` (16 arquivos, 7 planos) mais
   `scripts/local/historical/` (2). Enquanto as três discordarem,
   qualquer glob novo herda o mesmo ponto cego.
2. Publicar no catálogo a tabela **classe → nº de achados → rounds** que
   sustenta a priorização. Hoje a ordem das 6 classes na `§2` não
   corresponde à frequência; `grep|tail -1` em VERDICT aparece **uma
   única vez** (round 11) e está listada como classe de destaque.
3. Adicionar ao catálogo a classe **"cura decorativa"** (round 24:
   `BASE_TAG_OBJ`/`BASE_TAG_COMMIT` declarados nas linhas 22-23 e nunca
   verificados nem usados — a cura do round 23 foi aplicada ao corpo e
   nunca ligada). É puramente sintática, barata de detectar
   (atribuída-e-nunca-lida) e é a forma mecânica da lição-mãe do repo.
4. Congelar o corpus da W1 por sha256 antes da extração. Já existe
   `SCRIPTS-MANIFEST.sha256` no diretório — usar, e citar o hash no
   catálogo, para que a extração seja re-executável contra o mesmo input.

## Unseen by the original plan

1. **A classe dominante não está na lista.** *Binding de evidência /
   receipt por NOME ou por chave fraca, em vez de por CONTEÚDO* —
   ~15 achados (rounds 5, 6, 8, 9, 16, 18, 19×2, 20, 21, 22, 23, 24,
   27×2, 29), mais que qualquer classe nomeada. Formas: provenance não
   pina o manifesto do pack; arquivos de cerimônia aceitos por pathname
   sem sha; receipt de workflow selecionado só por `headSha`; `BASE_TAG`
   simbólico nunca vinculado a objeto. **Nenhum lint sintático pega
   isto** — exige conhecer o modelo de confiança. O lugar da cura é o
   TEMPLATE (a cerimônia gerada pina por conteúdo por construção), não a
   regra de lint. Se a W1 não a nomear, a W3 nasce sem o requisito e o
   piloto da W4 repete a classe.
2. **Segunda e terceira não-nomeadas, também estruturais:** estado remoto
   (tag/release) consultado tarde, parcialmente, ou por chave fraca
   (~9 achados: rounds 12, 13, 14, 20, 21, 24, 27, 29, 30); e
   resumabilidade/artefato órfão/tri-estado (~9: rounds 5×2, 6, 7, 11,
   12, 14, 20, 22) — esta última já é o item 5 do contrato existente,
   escrito e não enforçado.
3. **Ordem de irreversibilidade** (~5 achados: rounds 14, 15, 25, 26,
   27): o artefato público existe antes da verificação final. A cura que
   os reviewers convergiram é de desenho — criar release como draft e
   des-draftar só após o receipt. É propriedade do template, não regra de
   lint, e o plano não a menciona.
4. **Predicado sobre conjunto fechado incompleto** (~4: rounds 11, 12,
   14, 19): `isPrerelease` sem `isDraft`; só a conclusão literal
   `failure` tratada; CI aceito sem exigir `completed` + zero pendentes.
   O repo **já tem essa lição na memória**
   (`feedback-closed-sets-must-be-derived-not-recalled`: derive do enum
   da autoridade, nunca de cabeça) e ela não chegou ao catálogo.
5. **Modo declarado ≠ comportamento** — `MONITOR_ONLY` anunciado como
   read-only e não sendo (rounds 20, 29, 30: **três rodadas seguidas**,
   cada uma achando uma superfície nova do mesmo engano). É a classe mais
   reincidente por rodada consecutiva do trem inteiro e não está na
   lista das 6.
6. **A `§2b` exige "equivalência de GARANTIAS, não bytes" para a W3 mas
   não diz quem enumera as garantias.** O contrato existente é o
   candidato natural a essa enumeração — mais um motivo para a W1 partir
   dele. Sem lista canônica de garantias, "equivalência" é inverificável
   e o golden test da W3 vira vacuous gate.

## What I would NOT change

1. **O critério de falha da `§3`.** "Se o piloto não reduzir ≥40%,
   reportar NEGATIVO e manter template+lint" é honesto e raro — preserva
   o valor de W1/W2 independentemente da hipótese central. Não trocar por
   uma métrica que sempre passa.
2. **A doutrina de não tocar no CONTEÚDO das garantias.** Sentinel,
   anchor-sha, dois rails de signer, `scope=∅` antes do commit ficam como
   estão. É a fronteira que separa "baratear a revisão" de "afrouxar a
   cerimônia", e o plano a desenha no lugar certo.
3. **O piloto SHADOW da `§2b`** (trem 1 gerado em dry-run PARALELO ao
   manual que executa de verdade; manual canônico até dois trens verdes;
   fallback antes da fronteira irreversível). Dado que a classe
   "irreversibilidade fora de ordem" produziu 5 achados neste corpus,
   este desenho está calibrado com a evidência. Não encurtar para um
   único trem.
4. **Extrair de rodadas REAIS em vez de escrever classes de cabeça.** O
   corpus on-disk é o ativo mais valioso do plano — foi ele que me
   permitiu falsificar o próprio número do plano. Manter o AC de "exemplo
   REAL citado (round/arquivo)" por classe, sem exceção.
5. **Métrica primária em rounds, horas como secundária** (`§4`). Rounds
   são contáveis a partir do disco; horas de reviewer não são
   reproduzíveis. A escolha está certa.

---

## Respostas às 4 questões abertas

**1. Layout de entrega.** Catálogo em `.claude/plans/PLAN-174/catalog.md`
está certo (é evidência de plano, não superfície canônica). O lint **não**
deve nascer em `.claude/scripts/local/`: o diretório está dentro do escopo
do shellcheck do CI (que varre `.claude/scripts` inteiro), mas `local/` é
o balde de ferramentas de operador e o lint é gate de CI. Recomendo
`.claude/scripts/check-ceremony-script.py` com testes em
`.claude/scripts/tests/`, seguindo os guards existentes. **Mas a decisão
de layout mais importante é outra:** os alvos estão em
`.claude/plans/*/OWNER-*.sh` enquanto contrato e workflow apontam para
`.claude/scripts/owner-ceremony/`. Reconciliar isso é pré-requisito do
wire — senão o lint novo nasce com o mesmo ponto cego do shellcheck. O
wire de CI é um step novo no `validate.yml` (job `Governance, health,
contamination, shellcheck` — o step de shellcheck já está lá, na linha
296); pre-commit não existe hoje (`.git/hooks/` está vazio, só samples),
então "roda em pre-commit" precisa antes de um mecanismo de pre-commit —
tratar como item próprio, não como pressuposto.

**2. Fail-closed vs baseline.** Nem waiver por arquivo nem baseline
solta. Três camadas: (a) classes **BLOCKING** — detecção exata,
consequência P0 — fail-closed sem exceção, e se um histórico viola, é
violação real e o histórico é curado ou o arquivo é movido para
`historical/` explicitamente fora do escopo; (b) classes **ADVISORY** —
imprimem, nunca bloqueiam, taxa de disparo publicada; (c) **baseline
pinada por sha256 do arquivo**, com teste que falha se a baseline
CRESCER. Baseline que só encolhe é dívida com juros declarados; waiver
por nome de arquivo é dívida invisível. O AC de zero-FP aplica-se
exclusivamente a (a).

**3. Fronteira W2/CI vs PLAN-183 W2.** Não colidem hoje, e a razão
importa. O PLAN-183 cobre os **templates de workflow entregues ao
adopter** (o censo dele achou zero referência aos dois templates em
qualquer teste); a W2 daqui toca o `validate.yml` **vivo deste repo**.
Arquivos distintos, problemas distintos. A colisão nasce se alguém
decidir templatizar o lint de cerimônia para adopters — o que **não**
recomendo: cerimônia de release com pinentry, dois rails de signer e
delta guard é superfície deste projeto, não do adopter. Registrar essa
não-templatização como decisão explícita evita que o PLAN-183 herde o
lint sem querer.

**4. Escopo do glob.** `.claude/plans/*/OWNER-*.sh` cobre **16** arquivos
em 7 planos (166, 167, 168, 169, 179, 180) — é o glob que corresponde à
realidade. O que ele **não** cobre e apareceu no corpus:
`repass-ga/run-ga-repass.sh` (não casa `OWNER-*` e concentrou ~1/3 dos
achados dos rounds que li — 6, 7, 13, 17, 19, 22, 23, 24, 25, 26);
`scripts/local/historical/OWNER-CEREMONY-*.sh` (2 arquivos);
`.claude/scripts/local/generate-ceremony.sh` (o gerador da W3, que
precisa se auto-linter); e os scripts que moram fora do repo em
`~/canhada-labs/` (`OWNER-RATIFY-S302.sh`), que **nenhum gate alcança** —
esses precisam de política, não de glob: ou entram no repo sob o gate, ou
são declarados fora de escopo por escrito. Recomendo o critério ser
**runner de cerimônia**, não prefixo de nome: qualquer `.sh` sob
`.claude/plans/` mais o gerador, mais `historical/` em modo advisory.

## Estimativa de esforço (ADR-081 — tokens + sessões)

- **W1 re-escopada** (delta contra o contrato existente + tabela
  classe→frequência→rounds a partir dos 27 vereditos + as 5 classes
  não-nomeadas): **50-80k tokens, 1 sessão**. O corpus já está aberto e
  classificado neste documento; a extração é redação, não descoberta.
- **W2 na ordem que recomendo** (extensão de escopo do shellcheck +
  enable cirúrgico + complemento Python para 2-3 classes + controles
  positivos): **60-100k tokens, 1 sessão**.
- **W2 como escrito no plano** (lint Python do zero, ≥6 classes, caso
  vermelho por classe, zero-FP sobre ~18 históricos): **140-220k tokens,
  2 sessões** — acima do envelope de 100-150k firmado para W1-W2. O custo
  esconde-se no AC de zero-FP sobre históricos, não nas regras.
- **ADR de disciplina de erro** (M-5): **15-25k tokens**, cabe dentro da
  sessão da W1.

Ou seja: W1+W2 na ordem recomendada cabe em **110-180k / 2 sessões**,
dentro do envelope firmado. Na ordem do plano, estoura.

Sem `external_wait` novo: nada aqui depende de espera humana ou de
terceiro. O único prazo de calendário que permanece é o já declarado no
frontmatter do plano (D-2 do corte v1.4.0-rc.1), que é external wait
legítimo por ser janela de release.
