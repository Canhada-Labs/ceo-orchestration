---
round: 1
archetype: Principal Security Engineer
skill: security-and-auth
agent_persona: (crítico de trust boundaries, autenticação de gates e supply chain; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-06T02:40:00Z
---

## Verdict

ADJUST — 5 itens BLOQUEANTES.

## Summary (≤ 3 bullets)

- O corte «um toolkit + manifesto» está certo: as 7 classes da tabela são reais e o custo de cada clone é uma assinatura sobre conteúdo errado. As invariantes 1, 2, 4, 5 e 6 são exatamente as certas.
- **Onde é fraco (a tese deste crítico):** o plano endurece o CONTEÚDO que o Owner assina e não endurece o GATE que decide. Verificado em disco: `.claude/scripts/ceremony/sign.sh` responde **0** ao oráculo de canonicalidade — hoje e depois da W1 —, o manifesto nomeia um COMANDO que o gate executa, os registros de rail entram por NOME sem digest, e as 9 invariantes omitem o único controle que 33 dos 48 scripts clonados já implementam (allowlist de signatário).
- Consequência: sem os 5 must-fix, o toolkit troca sete defeitos distribuídos por UM alvo central de alto valor, editável por qualquer agente e sem assinatura própria.

## Risks

**R-SEC1 — P1 — O gate da assinatura nasce fora de qualquer gate, e as duas seções do plano discordam sobre isso.**
Medido: `python3 .claude/hooks/check_canonical_edit.py --is-canonical .claude/scripts/ceremony/sign.sh` → `0`, contra `1` para um hook. A lista `_CANONICAL_GUARDS` (`.claude/hooks/check_canonical_edit.py:115-215`) é ESTÁTICA por path: nomeia `.claude/scripts/lessons.py`, `prune-lessons.py`, `lesson-restore.py`, `lesson_ranker.py` — nenhum prefixo `.claude/scripts/ceremony/`. Logo a nota do gate da W0 (linha 155, «oráculo 0 **até serem referenciados por SIGN**») é FALSA no HEAD: ser referenciado por um SIGN não muda a lista, e o oráculo segue 0 para sempre. E a linha 145 diz «o toolkit landa por cerimônia própria (a última assinatura à moda antiga)» enquanto a linha 155 põe a W0 — que entrega `lib.sh`, onde as 9 invariantes moram — como pacote **livre**. As duas seções não podem estar certas ao mesmo tempo. Somado ao fato registrado em memória de que Bash/python contornam o hook de `Edit`, o resultado é: o programa que autentica a assinatura do Owner é o único artefato de governança sem autenticação.
*Mitigação:* `.claude/scripts/ceremony/*` entra em `_CANONICAL_GUARDS` **no mesmo patch que cria o diretório**, com controle vermelho (oráculo responde 1); a W0 deixa de ser livre — ou entrega apenas os controles, com `lib.sh` na W1 canônica.

**R-SEC2 — P1 — O manifesto é executado, e o formato escolhido não tem parser no runtime declarado.**
`scope_generated_from = "apply-w6a.py --describe"` (linha 116): uma STRING vinda de um arquivo por pacote — não rastreado, escrito pelo builder — que o `sign.sh` executa para imprimir o escopo que o Owner assina. Nada no §Approach pina o derivador por sha256, então «o escopo é gerado, nunca digitado» garante que o texto veio de um programa, não QUE programa. Duas consequências: escopo forjado (o derivador mente sobre os paths) e execução arbitrária dentro da cerimônia. Agrava: a OQ-3 pergunta como ler TOML do bash, mas o problema é anterior — medido na máquina do Owner, `python3 -V` = **3.9.6** e `import tomllib` → `ModuleNotFoundError`. O CLAUDE.md §4 fixa stdlib-only e Python ≥ 3.9; `tomllib` só existe em 3.11+. Sem parser, sobra parsing ad-hoc por regex/`eval` no shell — a superfície clássica de path confusion no exato ponto onde o Owner digita a passphrase.
*Mitigação:* trocar TOML por JSON (stdlib em 3.9) ou por `chave<TAB>valor` lido com `while IFS=` sem `eval`; o manifesto declara `derivator_path` + `derivator_sha256` e o gate recusa se o sha não bater; a invocação é argv fixo (`python3 <derivator> --describe`), nunca uma string de comando do manifesto.

**R-SEC3 — P1 — «Registro de rail» é prosa; o gate autentica um arquivo, não uma rodada.**
A invariante 1 fecha o CONJUNTO (disco vs lista) — correto e necessário —, mas `rail_records` (linha 114) lista NOMES sem digest, e o predicado é «lê exatamente `Rail-Verdict: APPROVE`». Quem escreve o registro é o próprio builder do pacote; um `APPROVE` datilografado é indistinguível de um retorno do rail. A invariante 9 tenta cobrir isso com `VERDICT:` próprio, `tokens used` inédito e âncoras — três campos de PROSA no MESMO arquivo, todos forjáveis por quem forja o veredito. Regra da casa aplicável (memória S345): «veredito de rail vale só para o SUJEITO revisado» — e nada aqui liga o registro ao sujeito por bytes.
*Mitigação:* o registro é a saída CAPTURADA do CLI (stdout+rc), o `sign.sh` recusa registro sem o cabeçalho de modelo do próprio CLI, e o `finalize.sh` — nunca o autor — grava `record_sha256` no manifesto; qualquer edição posterior ao registro faz o SIGN recusar. Sem isso a invariante 1 fecha a lista e deixa o conteúdo aberto.

**R-SEC4 — P1 — As 9 invariantes omitem a autenticação do SIGNATÁRIO, que 33 dos 48 scripts clonados já fazem.**
Medido: `grep -l "sentinel-signers" .claude/plans/*/OWNER-*.sh | wc -l` = **33**, contra 48 scripts `OWNER-*{SIGN,LAND}*.sh` rastreados; exemplo `PLAN-182/OWNER-S326-LAND.sh:144` (`SIGNERS=".claude/sentinel-signers.txt"`), arquivo que existe no HEAD e é consultado também pelo hook (`check_canonical_edit.py:70,95`). A lista de 9 invariantes é apresentada como o conjunto do que o toolkit garante; uma migração que a tome como especificação **remove** de 33 pacotes o controle que distingue «assinatura GPG válida» de «assinatura do Owner» — a lição já paga e registrada em memória («assinatura GPG válida NÃO é autorização mecânica»).
*Mitigação:* antes da W0, INVENTÁRIO MECÂNICO dos controles presentes nos 48 clones (um censo, não uma lista de memória — a classe «planos são confiáveis sobre a FORMA, não sobre MECÂNICA escrita de memória»); toda invariante ausente do toolkit vira item nomeado, e a verificação de signatário vira a invariante 10 com controle vermelho.

**R-SEC5 — P1 — O Check do AC-3 já está VERDE hoje, antes de qualquer trabalho.**
`git ls-files | grep -EI 'OWNER-.*(W4B|w4b|W5A|w5a|W1A|w1a|SF|WR)'` retorna **vazio** no HEAD: os 6 pacotes citados vivem fora do repositório (área de trabalho da noite, como o próprio plano admite nas linhas 54-56). O critério «`git ls-files` não lista nenhum `OWNER-*-{SIGN,LAND}.sh` para os 6 pacotes» não pode ficar vermelho — nem antes, nem depois, nem se a migração falhar. (Existem 48 desses scripts rastreados, todos de OUTROS planos, fora do escopo declarado do AC.)
*Mitigação:* o AC-3 mede sobre a árvore dos pacotes (`<PK>`), não sobre `git ls-files`, e o Check nomeia o comando com o diretório como parâmetro; ou o escopo passa a ser «nenhum pacote NOVO nasce com script próprio», verificável por um gate no derivador.

**R-SEC6 — P2 — ADR-192 é citado como leitura e não aparece em nenhum AC.**
O cabeçalho (linha 24) cita «ADR-192 (manifesto de scripts de gate)»; `.claude/governance/gate-scripts-manifest.txt` existe e pina 9 scripts por sha256. Um `sign.sh`/`land.sh` compartilhado é, por definição, um script de gate — e nenhum dos 5 ACs pede sua entrada no manifesto. Sem isso o toolkit fica fora do único mecanismo que detecta edição de gate por hash.
*Mitigação:* AC novo: os 5 scripts entram no `gate-scripts-manifest.txt` no mesmo patch, com o controle vermelho (byte alterado ⇒ gate reprova).

**R-SEC7 — P2 — O guard de path absoluto é uma SEGUNDA superfície decidindo o mesmo fato, e nasce com uma isenção por NOME.**
Já existe `check_contamination.py`, e ele **isenta a árvore de planos por atacado**: `_ALLOWLIST_GLOBS` inclui `".claude/plans/*"` (`:238-247`, com a nota de que `fnmatch` cruza `/`) e `"OWNER-*.sh"` (`:292`), com uma única exceção negativa por BASENAME (`_NEVER_ALLOWLISTED_BASENAMES` = `LEDGER.md`, `LEDGER-ARCHIVE.md`, `:330-353`). Isso explica por que o hit de `w4b` passou — e o plano não reconcilia as duas superfícies (a forma exata dos defeitos D1–D4: a ORIGEM tinha dono, a ROTA não). Pior, a isenção proposta na invariante 3 (`claude-501/*/scratchpad`, linha 126) é uma exceção por NOME que codifica um UID: qualquer material sob um scratchpad passa, e o padrão envelhece no dia em que o UID mudar. Colateral da migração: ao sair de `OWNER-*.sh` para `.claude/scripts/ceremony/*`, os scripts SAEM de uma zona isenta — bom —, mas a isenção por nome continua viva para o próximo clone que alguém batize `OWNER-*.sh`.
*Mitigação:* o guard novo CHAMA `check_contamination.py` (um leitor a mais, não uma segunda regra); a exceção do self-test é por marcador explícito no arquivo de controle, não por regex de path; e a W2 propõe a poda de `OWNER-*.sh` da allowlist de contaminação assim que os clones saírem.

**R-SEC8 — P2 — O AC-4 é medido por um instrumento sem gate, e sua evidência exige um path pessoal.**
`.claude/plans/PLAN-188/measure-rail-classes-v2.py` responde **0** ao oráculo (está sob `.claude/plans/`, isento também da contaminação) e não tem sha pinado em lugar nenhum: o critério de sucesso do plano é editável pela parte medida. Some-se o limite (v) que a própria OQ-5 verifica em disco — `nh = sum(high.values()) or 1` (`:147-148`) imprime `total=1` quando não há achado alto — e um pacote silencioso vira 100 % de uma classe. E o Check pede `--pack-dir <árvore dos pacotes>`: essa árvore fica sob `<PK>`, fora do checkout, então a linha de evidência do AC-4 tende a carregar um path absoluto pessoal para dentro do plano — a classe que a invariante 3 existe para fechar.
*Mitigação:* pinar o sha256 do instrumento no plano (e no manifesto ADR-192 se ele passar a decidir um AC); o Check cita `CEO_RAIL_PACK_DIR` (o instrumento já aceita, `:29`) e a evidência usa `<PK>`, nunca o path literal.

**R-SEC9 — P2 — «Remoção dos clones» (W2) apaga a cadeia de custódia de assinaturas passadas.**
A allowlist de contaminação preserva `scripts/local/historical/*` e `archive/*` com a razão escrita: «retained for chain-of-custody. Never re-executed» (`check_contamination.py:271-272,294-298`). Apagar um `OWNER-*-LAND.sh` já executado remove a única prova do que o Owner rodou naquela assinatura.
*Mitigação:* mover para `archive/` (ou `scripts/local/historical/`), nunca `git rm`; o AC-3 fala em «não referenciado por pacote novo», não em «deixar de existir».

**R-SEC10 — P3 — Nenhuma invariante cobre o que o `land.sh` EMPURRA além do commit.**
A invariante 6 pina parent, paths, blobs, modos, mensagem, tree e o `NEW_SHA` do push — bom. Fora do conjunto: refs além de `HEAD` (tags), hooks locais (`core.hooksPath`) e o remoto de destino. Um `push` pinado ao sha mas para um remoto trocado ainda entrega o conteúdo assinado ao lugar errado.
*Mitigação:* o `land.sh` fixa `remote` + `refspec` no manifesto e recusa qualquer outro; recusa também `core.hooksPath` divergente.

## Must-fix (blocking)

1. **Canonicalizar o toolkit no mesmo patch que o cria (R-SEC1)** e resolver a contradição linha 145 × linha 155: `lib.sh` não pode nascer em pacote livre.
2. **Manifesto sem execução de string e com parser existente (R-SEC2):** JSON/TSV lido sem `eval`, derivador pinado por sha256, argv fixo. `tomllib` não existe em 3.9.
3. **Registro de rail autenticado por bytes (R-SEC3):** saída capturada do CLI + `record_sha256` gravado pelo finalize; `APPROVE` em prosa deixa de bastar.
4. **Censo mecânico dos controles dos 48 clones antes da W0 (R-SEC4)**, com a verificação de signatário (`sentinel-signers.txt`, presente em 33 deles) promovida a invariante com controle vermelho.
5. **Reescrever o Check do AC-3 (R-SEC5):** hoje ele está verde no HEAD e não pode ficar vermelho.

## Nice-to-have (advisory)

1. Entrada dos 5 scripts no `gate-scripts-manifest.txt` como AC próprio (R-SEC6).
2. Guard de path absoluto como LEITOR de `check_contamination.py`, isenção por marcador e não por regex de UID (R-SEC7).
3. Sha do instrumento de medição pinado; evidência do AC-4 por `CEO_RAIL_PACK_DIR` (R-SEC8).
4. Clones arquivados, nunca removidos (R-SEC9).
5. `remote`+`refspec` no manifesto (R-SEC10).

## OQs que o Owner precisa ratificar antes da W0

- **OQ-A** — Formato e parser do manifesto (JSON stdlib × TSV), dado que `tomllib` não existe no runtime declarado.
- **OQ-B** — O que é pinado por digest: derivador, registros de rail, instrumento de medição — e quem grava (só o finalize).
- **OQ-C** — `.claude/scripts/ceremony/*` entra em `_CANONICAL_GUARDS` e no manifesto ADR-192? (define se a W0 é livre ou canônica).
- **OQ-D** — Destino dos clones: arquivo com custódia × remoção.
- **OQ-E** — Poda das isenções por NOME (`OWNER-*.sh`, `.claude/plans/*`) na contaminação, e a forma da exceção do self-test.
- (mantidas as OQ-2/OQ-4/OQ-5 do plano; a OQ-1 já foi resolvida pelo CEO.)

## Unseen by the original plan

1. O oráculo de canonicalidade responde **0** para o próprio gate — e continuará respondendo, porque a lista é estática por path.
2. `check_contamination.py` **isenta `.claude/plans/*` por atacado** e `OWNER-*.sh` por nome: é a razão de fundo pela qual a classe «path pessoal em material assinado» sobreviveu.
3. 33 dos 48 scripts clonados verificam a allowlist de signatário; nenhuma das 9 invariantes menciona isso.
4. `tomllib` não existe no Python do repositório nem no da máquina do Owner (3.9.6 medido).
5. O `--pack-dir` do AC-4 aponta para fora do checkout: a evidência do critério de sucesso nasce carregando um path pessoal.
6. ADR-192 é citado no cabeçalho e ausente de todos os ACs.

## What I would NOT change

- **A invariante 1 (gate das DUAS famílias, com registro em disco fora da lista ⇒ recusa nomeada).** Fechar o conjunto nos dois sentidos é o desenho certo; o que falta é digest, não outra regra.
- **A invariante 2 (trailer GERADO do conjunto, comparado nos dois sentidos).** É a cura da classe «teto ≠ conjunto».
- **A invariante 4 (baseline só pelo finalize) e a 5 (escopo gerado, nunca digitado).** São exatamente a forma que impede o Owner de assinar um escopo menor que o diff.
- **A invariante 8 (harness NUNCA planta `APPROVE`).** Verde de harness lido como evidência de rail é a pior das sete classes; manter literal.
- **O nível L3 e a exigência de debate antes de qualquer wave.** Um gate de assinatura merece isso.
- **A honestidade da OQ-5** — seis limites do instrumento verificados no código, com linha citada. Não «reconciliar» isso para cima.
