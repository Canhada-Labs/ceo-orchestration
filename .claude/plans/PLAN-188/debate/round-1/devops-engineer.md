---
round: 1
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
agent_persona: (crítico de gates/CI/mecânica de cerimônia; perfil da linha do SKILL MAP)
generated_at: 2026-09-06T00:00:00Z
---

## Verdict

ADJUST — 4 itens BLOCKING (R-DO1, R-DO2, R-DO3, R-DO4).

## Summary (≤ 3 bullets)

- O corte «UM toolkit + manifesto por pacote» é o certo: as 7 classes da tabela são classes de CLONE, e clone não se fecha com nota, fecha-se com dono único. As 9 invariantes são falsificáveis quase todas.
- **Onde é forte:** invariante 2 (trailer gerado do CONJUNTO), 4 (baseline só pelo finalize) e 6 (ligar `NEW_SHA` ao índice aprovado) atacam exatamente os defeitos que a S345 pagou; o plano recusa inventar número (OQ-4) e declara os 6 limites do próprio instrumento (OQ-5).
- **Onde é fraco:** o endereço. Levar os scripts de `.claude/plans/**/*.sh` para `.claude/scripts/ceremony/` os tira do ÚNICO gate que hoje lê scripts de cerimônia, e o plano não cita nem o lint nem o gerador de cerimônia que já existe. Dois ACs (3 e 4) não conseguem ficar vermelhos como estão escritos.

## Risks

**R-DO1 — BLOCKING (P1) — O endereço proposto tira os scripts do gate de cerimônia: falso-verde por construção.**
`check-ceremony-script.py:62-68` descobre candidatos SÓ em `DISCOVERY_ROOTS = [".claude/plans", ".claude/scripts/local/historical"]` mais `EXPLICIT_FILES = [".claude/scripts/local/generate-ceremony.sh"]`. O workflow que o executa (`.github/workflows/ceremony-lint.yml:5-17`) dispara só em `.claude/plans/**/*.sh` e nesses 3 arquivos explícitos. O toolkit vive em `.claude/scripts/ceremony/` (PLAN-188:104-106) ⇒ **nenhuma das classes BLOCKING R1 (proveniência), R2 (`|| true` na linha de gpg/push/tag), R3 (`grep … | tail` em VERDICT), R4 (`git add` de diretório), R8 (exec-bit 100755) roda sobre o script que passa a ser O gate da assinatura**. É a classe já paga neste repo («mover artefato p/ subdiretório pode tirá-lo do gate»). AC-1 checa só `bash -n` + `shellcheck`, que não cobrem nenhuma delas.
*Mitigação:* a W0 entrega, no MESMO patch, `DISCOVERY_ROOTS += ".claude/scripts/ceremony"` + `paths:` do `ceremony-lint.yml`, com controle VERMELHO (plantar `gpg … || true` em `sign.sh` e exigir BLOCK) — e uma 10.ª invariante «todo script do toolkit é descoberto pelo lint», provada pela saída de `check-ceremony-script.py --list`.

**R-DO2 — BLOCKING (P1) — Já existe um dono para «não escrever cerimônia à mão», e o plano não o reconcilia.**
`.claude/scripts/local/generate-ceremony.sh:2-7` declara-se «Replaces hand-writing OWNER-CEREMONY.sh from scratch each time» (PLAN-073 §2), com guards G1-G6 pré-emissão (`:17-30`: paths batendo `_CANONICAL_GUARDS`, sentinel parseável por `check_canonical_edit.py::_sentinel_grants_path`, `bash -n`). Ele é membro EXPLÍCITO do lint e gatilho do workflow. PLAN-188 §Approach propõe a SEGUNDA resposta à mesma pergunta e não o cita em lugar nenhum; a W2 diz «remoção dos clones» sem dizer se o gerador é aposentado, vira emissor de `ceremony.toml`, ou fica como terceira rota. É a forma exata dos D1-D4 (S322-S327): a ORIGEM tinha dono, a ROTA não.
*Mitigação:* uma linha de decisão no §Approach (aposentar / absorver / conviver) + AC que prove mecanicamente qual dos dois emite a cerimônia; se conviverem, G1-G6 e as 9 invariantes precisam ser o MESMO código.

**R-DO3 — BLOCKING (P1) — A linha de base do AC-4 não é reproduzível e o parâmetro que muda o veredito é literal.**
`measure-rail-classes-v2.py:32` fixa `SINCE = 2026-09-04 20:00` e `:123` filtra `os.path.getmtime(f) >= SINCE`: o conjunto medido depende de **mtime**, não de conteúdo. O corpus vive fora do repo e o próprio plano admite (PLAN-188:54-56) que a cifra «viaja com a sua apuração, não com um comando reproduzível num checkout». Logo o «era 23,1 %» do AC-4 (:176-181) não pode ser re-derivado, e qualquer `cp`/`rsync` dos pacotes muda o conjunto. `--pack-dir` é obrigatório (`:104-113`, recusa nomeada — bom), mas `SINCE` não tem flag: é um default que decide o veredito.
*Mitigação:* `SINCE` vira argumento obrigatório; o AC-4 pina o corpus por manifesto sha256 dos registros (as duas medições, base e follow-up, citam o manifesto); e o AC declara qual binário — resolver a OQ-5 ANTES da W0, porque o limite (vi) (`PATH_RE`, `:33`, `tests` fora das raízes) classifica achados de `tests/` como `ceremony`, inflando justo a fração comparada.

**R-DO4 — BLOCKING (P1) — O Check do AC-3 nasce verde e não pode ficar vermelho.**
AC-3 (:172-175) checa que «`git ls-files` não lista nenhum `OWNER-*-{SIGN,LAND}.sh` para os 6 pacotes». Os 6 pacotes são untracked e fora do repo (:54-56) ⇒ `git ls-files` retorna vazio para eles HOJE, antes de qualquer trabalho. E no repo há **46** arquivos rastreados casando `OWNER-*(SIGN|LAND).sh` (`git ls-files | grep -c 'OWNER-.*\(SIGN\|LAND\).sh'` = 46, de PLAN-166/167/168/…), que o AC não distingue. Sem um mapa pacote → conjunto de paths, o AC é vácuo nos dois sentidos: não prova migração e pode acusar cerimônias históricas.
*Mitigação:* o AC lista os paths concretos por pacote (derivados, não digitados) e traz controle positivo: um clone deliberadamente mantido faz o Check ficar VERMELHO.

**R-DO5 — P2 — Nenhum workflow/step executa o runner das 9 invariantes.**
AC-1 (:162-167) exige «9/9 VERMELHO-antes / VERDE-depois», mas a tabela de Items dá à W0 o gate «livre» e nenhum job de CI. O `shellcheck` sim é automático — `validate.yml:341-359` roda `find .claude/scripts .claude/hooks -name '*.sh'` — mas com `-S warning`; o AC diz só «shellcheck», então local e CI podem discordar. O runner de controles, sem step, vira instrumento de mão e morre em silêncio (classe «instrumento verde cuja pergunta envelheceu»).
*Mitigação:* nomear o workflow e o step que rodam o runner (o `ceremony-lint.yml` é o hospedeiro natural, já com `timeout-minutes: 5`), medir o custo antes de escolher, e fixar `-S warning` no texto do AC-1.

**R-DO6 — P2 — Membresia no manifesto ADR-192 não decidida (e o bootstrap dela).**
`.claude/governance/gate-scripts-manifest.txt` tem 9 linhas pinando por sha256 os scripts de gate (`verify-counts.sh`, `validate-governance.sh`, `_release_tag_guard.py`, …). O toolkit passa a ser O gate da assinatura do Owner e o plano não diz se entra. Se entrar, toda edição do toolkit vira cerimônia — e a primeira cerimônia do toolkit é feita pelo próprio toolkit (bootstrap circular que o plano precisa declarar; hoje só há a nota «a última assinatura à moda antiga», :144-145).

**R-DO7 — P2 — OQ-3 é um bloqueio de desenho parado nas Open questions.**
O §Approach já congela o formato como TOML (:108-117) e a invariante 5 exige regenerar e comparar, mas «COMO ler o `ceremony.toml` a partir do bash» segue aberto (:200-201). Um parser TOML caseiro em shell torna o manifesto uma ENTRADA não confiável parseada pela camada mais fraca — e a doutrina do repo é fail-CLOSED em entrada (CLAUDE.md §4). Chave desconhecida, chave duplicada, array multilinha, valor com `#` ⇒ recusa NOMEADA, nunca leitura parcial.
*Mitigação:* emitir o manifesto em JSON e ler por `python3 -c` (stdlib já é requisito), ou gerar um fragmento `.sh` a partir do TOML por derivador Python; e o conjunto de recusas vira invariante com controle vermelho.

**R-DO8 — P3 — A invariante 3 embute um literal de máquina dentro do guard que proíbe literais de máquina.**
O único allow do guard de path absoluto é o glob de self-test `claude-501/*/scratchpad` (:121-123) — um uid de máquina escrito no código do gate. Ele envelhece em outra máquina (o guard vira ruído ou o self-test some) e é justamente a classe «path pessoal em material assinado».
*Mitigação:* o allow vem do manifesto ou de `TMPDIR`/`--self-test-root`; o auto-escaneio prova que o allow não pode ser alargado sem aparecer no diff.

**R-DO9 — P3 — Colisão de nome com uma exclusão morta do CI.**
`validate.yml:354` exclui `.claude/scripts/owner-ceremony/archive/*`, diretório que **não existe** (`ls` falha). O nome proposto `.claude/scripts/ceremony/` fica a um passo dessa exclusão morta; qualquer renomeio futuro para `owner-ceremony/` cairia num buraco de shellcheck sem ninguém notar.
*Mitigação:* a W0 remove a exclusão morta no mesmo patch, ou o plano fixa o nome final com o motivo escrito.

## Falta antes da W0 (OQs para o Owner ratificar)

- **OQ-6** — descoberta + gatilho do `ceremony-lint` para a nova raiz (R-DO1). Sem isso a W0 não deve começar.
- **OQ-7** — destino do `generate-ceremony.sh` (R-DO2).
- **OQ-8** — o toolkit entra no manifesto ADR-192? Quem assina a primeira versão dele? (R-DO6)
- **OQ-9** — formato/leitor do manifesto + conjunto de recusas de parse (R-DO7, hoje OQ-3).
- **OQ-10** — mapa pacote → paths do AC-3 e pinagem por conteúdo do corpus do AC-4 (R-DO3, R-DO4); e a decisão da OQ-5 (corrigir o classificador e re-medir × congelar) antes de o AC-4 virar critério.
- **OQ-11** — qual workflow/step roda o runner das 9 invariantes, com custo medido (R-DO5).
