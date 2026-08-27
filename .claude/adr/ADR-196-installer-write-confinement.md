---
adr_id: ADR-196
title: O destino de uma escrita do installer é respondido por UM predicado de confinamento na biblioteca — a política fica no chamador, e o valor de flag é validado no parse, não no sítio de escrita
status: PROPOSED
date: 2026-08-26
plan: PLAN-185 (W1+W2; F1 escrita fora do $TARGET via symlink/hardlink, F2 CODEOWNERS de 0 bytes)
proposed_by: CEO (S329 night-run — pacote de cerimônia C)
decided_by: Owner (PENDENTE — a assinatura GPG do sentinel da cerimônia C É a ratificação; o flip textual para ACCEPTED chega ao main por cerimônia própria, como o ADR-194 registrou)
risk_tier: A
debate_required: true
debate: ".claude/plans/PLAN-185/debate/round-1/consensus.md (round 1, PROCEED/design-coherent, 3× ADJUST, 0 REJECT, 0 VETO). C4 decidiu o predicado; C5 separou predicado de política; C6/C7 a gramática compartilhada; C9 a escrita atômica; C10 a proveniência; C14 o pré-voo."
numbering_note: "196 era o próximo livre medido no disco na S329 (ADR-000..ADR-195). Alocado NO MOMENTO da escrita, conforme a emenda 8.2 do ADR-195."
related_plans: [PLAN-185, PLAN-183, PLAN-167, PLAN-182]
related_adrs: [ADR-194, ADR-190, ADR-039, ADR-155]
---

# ADR-196 — Confinamento de escrita do installer

## Context

Os dois defeitos são MEDIDOS, não argumentados (PLAN-185 §1; reproduzidos na
S325 e de novo na S329, com bytes):

* **F1 — escrita fora do `$TARGET`.** Todo escritor de destino do `install.sh`
  decidia escrever testando EXISTÊNCIA, e `-e` **segue** symlink. Um link
  PENDENTE plantado no destino responde falso, o escritor toma o ramo "não há
  nada aqui" e o `cp`/`>` escreve ATRAVÉS do link: `rc 0`, log dizendo
  `COPIED:`, **536 bytes** fora do alvo. Link resolvido e ancestral symlink
  escapam igual; **hard link** escapa com todo teste de path passando, porque um
  segundo nome do mesmo inode não é um link que caminhada nenhuma encontre. A
  população não é um sítio: são **7 escritores** desguardados (consenso C2).
* **F2 — CODEOWNERS de 0 bytes.** `--github-owner` era interpolado cru num
  programa `sed`. Um valor com `/` encerra o comando cedo: o `sed` falha
  **depois** de o `>` já ter truncado o destino, e `.github/CODEOWNERS` sobrevive
  em 0 bytes — EXISTS-skipado para sempre, fora do snapshot de rollback (que
  cobre só `$TARGET/.claude`), e lido pelo GitHub como "sem donos".

A classe é a de D1–D4 do PLAN-183: **ramo local por omissão**. Cada sítio
respondia por conta própria "posso escrever aqui?", e sete nunca fizeram a
pergunta. O ADR-194 já fixou o princípio para a ORIGEM de uma entrega; faltava o
lado do DESTINO.

**Por que o censo inverteu a régua.** As três primeiras passadas do instrumento
da W0 enumeravam formas PERIGOSAS e, a cada rodada de pair-rail, a mesma classe
voltava — "forma não modelada ⇒ fail-open". Classe que regenera é arquitetura
errada: a 4ª passada enumera as formas PROVADAS seguras, cada uma com controle
positivo, e trata o resto como `indeterminado` — fail-closed por construção.

## Options considered

**(1) Guarda por sítio vs UM predicado compartilhado.** Sete guardas locais
seriam sete cópias a divergir — o mecanismo que produziu D1–D4 — e `upgrade.sh`
e `doctor.sh` precisam da MESMA resposta, que um helper privado do `install.sh`
não lhes daria. **Escolhido:** predicado na biblioteca que os três já carregam.

**(2) Escapar o `sed` vs eliminar a linguagem de substituição.** Escapar mantém
o valor DENTRO de um programa: "escapei todos os metacaracteres?" nunca fecha, e
a locale reabre a pergunta. **Escolhido:** remover os dois `sed`; o render usa
expansão de parâmetro do bash, cujo lado de substituição não tem caractere ativo
nenhum, mais um conjunto fechado validado no parse.

**(3) Recuperar o CODEOWNERS de 0 bytes por TAMANHO vs por EVIDÊNCIA.** 0 byte
não distingue "o `sed` abortou" de "o adopter esvaziou de propósito" — truncar
para zero é um modo real de DESLIGAR revisão obrigatória, e reescrever por
tamanho re-liga donos num repositório de terceiro (classe D4, que já custou uma
sessão). **Escolhido:** proveniência.

## Decision

> Âncoras conferidas no estado FINAL do patch. O **nome** é a referência
> estável; a linha é conveniência e apodrece — quatro destas mudaram dentro da
> própria sessão, quando o bloco de política subiu de lugar.

1. **Predicado único, na biblioteca.** `_wbm_dst_refuses <target_root>
   <rel_path>` (`scripts/_framework_manifest_set.sh:743`): `rc 0` = **recusar**,
   motivo em `_WBM_DST_REFUSE_WHY`; `rc 1` = confinado. Sem `echo`, sem `exit` —
   nome e polaridade espelham `_wbm_source_confined` (`:621`). Recusa: raiz ou
   relpath vazios; relpath não confinado (`_wbm_route_relpath_ok`, `:501`);
   **componente symlink, folha incluída** (`-L` é verdadeiro para link pendente,
   a forma cega ao `-e`); contenção física do ancestral existente mais profundo
   (`cd -P`/`pwd -P` — o piso bash 3.2 não tem `realpath`); folha de tipo não
   regular; e `nlink > 1` (`_wbm_nlink`, `:683`), que caminhada de path não vê.
2. **A POLÍTICA é do chamador.** `install_one` preserva o SKIP que os testes
   atuais fixam. Os escritores de entrega ACUMULAM a recusa nomeada e a RUN
   falha no fim (`_dst_refusal_verdict`, `scripts/install.sh:947` → `exit 1`),
   antes de manifesto e install-state registrarem qualquer coisa: um destino
   recusado inventariado como entrega vira o `PRESERVED (unclaimed)` silencioso
   do próximo upgrade.
3. **Pré-voo por grupo** (`_dst_preflight`, `:933`): todos os destinos de
   `docs/` e `.github/` respondidos ANTES da primeira escrita do grupo. Razão
   medida: o snapshot de rollback cobre só `$TARGET/.claude`, então abortar no
   meio deixaria o alvo MISTO em permanência.
4. **Gramática de handle com dono compartilhado** (`_wbm_github_handle_ok`,
   `:855`), adotada verbatim da regex que o `upgrade.sh` já aplicava, com
   conjuntos ENUMERADOS em vez de faixas (uma faixa é resolvida pela sequência
   de collating da locale, e gramática que responde diferente em duas locales
   não é uma gramática só). Validada em TRÊS fronteiras, porque `GITHUB_OWNER` é
   global e o parse não é o único caminho até ele: parse
   (`_assert_github_owner_grammar`, `:477`), antes de PERSISTIR e antes de
   RENDERIZAR. `upgrade.sh:3692` vira CONSUMIDOR no mesmo patch.
5. **Escrita atômica:** `mktemp` **no diretório de destino** (mesmo filesystem é
   requisito, não preferência — `rename(2)` não cruza filesystem, e estagiar em
   `$TMPDIR` degrada `mv` para copy+unlink e reabre a janela de 0 byte),
   `chmod 0644` explícito (`mktemp` cria `0600`, e um CODEOWNERS ilegível é
   regressão que bytes e linhas não pegam), temporário no `trap`, `mv -f` no fim
   — toda rota de falha deixa o destino como estava. `portable_sed_inplace`
   (`:2612`) idem: o nome fixo `${file}.ceo-sed-tmp` era pré-plantável.
6. **Recuperação só com REGISTRO DE ENTREGA** (`_codeowners_provenance`,
   `:1945`). Existe **uma** evidência admissível: a linha `.github/CODEOWNERS`
   no manifesto baseline, que só aparece quando um escritor realmente
   renderizou o arquivo (medido nas duas direções: 1 linha depois de uma entrega
   real, 0 depois de um EXISTS-skip). Um `github_owner` persistido **NÃO** é
   evidência — é prova de um PEDIDO, não de autoria, e as duas coisas se
   separam num caso ordinário que o rail REPRODUZIU: o adopter tem o seu
   próprio CODEOWNERS não-vazio, roda o installer com `--github-owner`, o
   arquivo é PULADO (os bytes dele sobrevivem, corretamente) e o owner é
   persistido de todo jeito; mais tarde ele esvazia o arquivo de propósito — que
   é como se desliga roteamento de revisão sem apagar o path — e o install
   seguinte leria o owner persistido como prova de autoria e re-renderizaria
   1409 bytes de template por cima. Perguntar "nós PEDIMOS isto?" em vez de
   "nós ESCREVEMOS isto?" reintroduz a classe D4 uma pergunta antes. Com prova
   ⇒ re-render RUIDOSO nomeando a evidência. Sem prova ⇒ `WARNING` nomeado e
   **o arquivo não é tocado**.
7. **O censo é gate de CI** (AC-3): o instrumento da W0 no `validate.yml` em
   modo ratchet, e o e2e no `smoke-install.yml` — nas DUAS listas `paths:`, com
   step próprio e controle negativo. Teste que nenhum workflow invoca é a classe
   "red gate nobody runs", e este repo já a pagou cinco vezes.

## Consequences

* Um adopter cujo destino seja symlink recebe **falha NOMEADA** onde antes
  recebia `rc 0` e escrita silenciosa fora da árvore. É o ponto.
* `--github-owner org/team` — sintaxe VÁLIDA de CODEOWNERS, já que o template é
  `@{{OWNER_HANDLE}}` — passa a ser recusado, com a mensagem dizendo isso e
  apontando a edição manual, em vez de corromper o arquivo (OQ-2). Suportar time
  exige trocar o delimitador em todos os consumidores: wave própria.
* `upgrade.sh` ganha dependência de biblioteca. Ausência ⇒ WARNING nomeado +
  resposta vazia para `_wbm_nlink` (fail-open em INFRAESTRUTURA, `CLAUDE.md` §4)
  e `rc 3` para a gramática — nunca re-implementação local.
* **O censo NÃO enxerga o predicado compartilhado**, e é estrutural: as formas
  provadas seguras exigem o `-L` no MESMO arquivo, e o plano mandou pô-lo em
  outro. Os sítios curados seguem contados como `desguardado`/`indeterminado`
  até o instrumento aprender a forma — a contagem é evidência secundária, e o
  que fecha a classe é o teste de FORMA da W1.

## Blast radius

`scripts/install.sh` (7 escritores + parse + persistência), `scripts/upgrade.sh`
(2 consumidores), `scripts/_framework_manifest_set.sh` (3 funções novas) — três
canônicos, um patch, uma assinatura. `scripts/doctor.sh` é o terceiro consumidor
previsto e **não** foi convertido: a classe segue aberta lá, dito aqui para que
ninguém leia este ADR como "fechado em todo lugar".

Residuais declarados (PLAN-185 §5, DESIGN-C §8): **TOCTOU irredutível** — nada
impede o destino de VIRAR symlink entre o predicado e a escrita, e bash não
oferece `openat`/`O_NOFOLLOW`, então a guarda ESTREITA a janela sem a fechar
(importa em alvo compartilhado ou clone de terceiro); `install_one` continua
PULANDO, por decisão; `install_mcp_secrets_dir` é sítio conhecido fora do
conjunto curado.

## Verification

| Instrumento | Resultado |
|---|---|
| `scripts/tests/test-installer-write-safety-e2e.sh` (árvore curada) | **63 passed / 0 failed, rc 0** (Darwin arm64, 2026-08-26; 2m49s e 4m42s em duas runs sob carga concorrente — o spread é da máquina, não do teste) |
| idem contra a árvore PRÉ-CURA do mesmo commit (controle positivo) | vermelho, nomeando os bytes fora do alvo |
| `bash -n` + `shellcheck -S warning` nos 3 canônicos e no teste | limpo |
| não-regressão: install pré-cura vs curado no MESMO destino | 566 arquivos sha256-idênticos; modos idênticos em 567 |

Toda asserção de F1 é sobre o **caminho EXTERNO**, nunca sobre o exit code: o
defeito pré-cura sai `0`, então uma asserção de exit code teria passado contra
ele (AC-1).

## References

* `.claude/plans/PLAN-185-installer-write-safety.md` — o plano (W1/W2, AC-1..AC-4).
* `.claude/plans/PLAN-185/debate/round-1/consensus.md` — os 15 achados de consenso.
* `.claude/plans/PLAN-185/s329-ceremony-C/DESIGN-C.md` — o desenho do patch, sítio a sítio.
* `.claude/adr/ADR-194-delivery-route-resolution.md` — o mesmo princípio do lado da ORIGEM.
* `docs/threat-model.md` §Tampering T-008 — a superfície no contrato de ameaça.
