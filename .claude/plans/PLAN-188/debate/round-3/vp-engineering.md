---
round: 3
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — o arquétipo não tem bloco de persona em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-07T00:20:00Z
---

## Verdict

ADJUST — **2 bloqueantes** (P1). O resto é P2/P3.

## Summary (≤ 3 bullets)

- Esta revisão é substancialmente melhor que a do round 2. **Reproduzi o censo único do §Riscos em clone limpo no `a6629d0`** (`git clone --local` para `<SP>/cc1`, `python3 .claude/scripts/check-ceremony-script.py --json`): `discovered_total` **109**, `discovered_tracked` **109**, `floor` **41**, `blocking_unwaived` **0**, `waivers_active` **44** — bate figura a figura, e `git diff --name-only a6629d0..HEAD` filtrado por `.claude/plans/**/*.sh|check-ceremony-script|ceremony-lint-waivers` devolve **0**, então o censo não envelheceu no HEAD.
- Os demais números conferem: 48 `OWNER-*(SIGN|LAND)*.sh` rastreados, 33 com `sentinel-signers`, modos 41/7, `_KERNEL_PATHS` = 110, manifesto ADR-192 = 9, sha256 do instrumento = `d2234bd…181062`, `PLAN-174:4-5` `superseded_by: PLAN-188`, `PLAN-SCHEMA.md:441` e `:462-470` resolvem, `.claude/plans/PLAN-188.md` ausente. O plano derivou o gate da W0 do ORÁCULO — a disciplina certa.
- **Onde quebra:** a mesma disciplina não foi aplicada à W3 (declarada «docs» enquanto entrega um ADR novo, que o oráculo responde **1**), e uma das duas curas novas do rail r3 se apoia numa afirmação sobre a CI que é falsa no HEAD — e ela virou cláusula de FALHA do AC-1.

## Risks

**R-VP1 — P1 (BLOCKING) — «W3. Gate: docs» é refutado pelo oráculo que o próprio plano usa, e o AC-5 exige o `.asc` que um pacote de docs nunca produz.**
`PLAN-188:796` declara «**W3 — medição e ADR.** Gate: docs», e `:797` põe no file assignment `.claude/adr/ADR-2xx-shared-ceremony-toolkit.md` [criado na W3]. Medido no HEAD: `python3 .claude/hooks/check_canonical_edit.py --is-canonical .claude/adr/ADR-200-shared-ceremony-toolkit.md` → `1`; o mesmo para `.claude/adr/ADR-010-canonical-edit-sentinel.md` → `1`. Ou seja, a W3 é **canônica**, não docs — exatamente pela razão medida com que o plano reclassificou a W0 («todo `.github/workflows/*` é oráculo 1 … ela é canônica pela razão medida», `:735-742`; confirmei `.github/workflows/ceremony-controls.yml` → `1`). E o AC-5 (`:1043-1044`) pede «`Status: ACCEPTED` e um `.asc` do Owner sobre o sentinel da wave» — artefato que a etiqueta «docs» exclui por construção. Duas seções que se leem como regras diferentes sobre a MESMA wave.
*Cura mínima:* trocar `Gate: docs` por `Gate: canônico (ADR = oráculo 1)` e declarar o corte v2 da W3 com o file assignment do sentinel/`.asc`; ou partir a W3 em W3a (instrumento + medição, oráculo 0, livre) e W3b (ADR + emenda ao ADR-010, canônica) — esta segunda é a que preserva a regra «uma assinatura, um escopo».

**R-VP2 — P1 (BLOCKING) — a justificativa do filtro `.sh` (rail r3 C3) é falsa no HEAD, e a cláusula de FALHA do AC-1 que ela gerou não pode ficar vermelha.**
`PLAN-188:150-156` afirma que, com o predicado novo, o job `shellcheck-ceremony` recebe um `.py` no conjunto do `--list`, «sai como `SC1071` e **o passo devolve rc 1**». No HEAD o passo não pode devolver rc 1 por DUAS razões independentes: `.github/workflows/ceremony-lint.yml:81-82` termina a invocação em `> shellcheck-ceremony.txt 2>&1 || true` (o `|| true` engole o rc do shellcheck, e o `set -uo pipefail` de `:77` não tem `-e`), e `:75` marca o passo `continue-on-error: true`. O efeito real é RUÍDO no relatório advisory, não vermelho. Consequência de governança: `PLAN-188:851` faz disso condição de falha do AC-1 («ou o job `shellcheck-ceremony` recebendo um `.py` no conjunto do `--list`») — um `Check:` cujo vermelho é inatingível no substrato atual é a classe «a red gate nobody runs» invertida, a mesma que a D5 mandou fechar.
*Cura mínima:* reescrever `:154` para o que a máquina faz («o relatório advisory passa a acumular `SC1071` a cada arquivo `.py`; o passo permanece verde por `|| true` + `continue-on-error`») e reformular a cláusula do AC-1 como um controle OBSERVÁVEL — p.ex. «`shellcheck-ceremony.txt` do PR do toolkit contém 0 ocorrências de `SC1071`». O filtro `.sh` no consumidor continua sendo a entrega certa; só a razão e o instrumento precisam ser verdadeiros.

**R-VP3 — P2 — o AC-4 exige um artefato que o file assignment da W3 não entrega (é a MESMA classe que o rail r2 M4 já curou uma vez).**
`PLAN-188:801-804` incorporou `measure-rail-classes-v2.sha256` ao escopo da W3 com a justificativa explícita «um file assignment que não o entrega faz o AC-4 falhar antes de medir». Mas o `Check:` do AC-4 também roda `--cohort <as 3 chaves>` (`:1030-1033`) e o §AC-4 exige, para a re-medição ser honesta, «a LISTA dos registros que a produziram com o sha256 de cada um» (`:1013-1017`) — nem a flag `--cohort` nem esse arquivo de lista aparecem no file assignment da W3 (`:797-808`), que só nomeia `--since` e a regra de classificação do toolkit. Seguir a W3 como escrita não satisfaz o AC-4.
*Cura:* nomear os dois no file assignment da W3 (ou da «wave da medição», se ela for separada da W3 pela cura do R-VP1), com o mesmo colchete `[criado na …]`.

**R-VP4 — P2 — a opção (iii) da OQ-9 não pode satisfazer a pré-condição para a qual a OQ-9 foi promovida.**
`PLAN-188:1198-1200` oferece como executor do runner «execução local exigida pelo `harness.sh` de cada cerimônia». O `harness.sh` é entrega da **W1** (`:775-778`: «Arquivos: … `ceremony/harness.sh` [criados na W1]»), e a OQ-9 foi promovida a pré-condição da W0 porque «sem executor o AC-1 não FECHA» (`:735`, `:1203-1205`). No braço (iii) a W0c fica vazia (`:715-717`) e os cinco controles vermelhos da W0 não têm executor NENHUM até a W1 — a janela que a D5 mandou fechar reabre por escolha legítima do Owner.
*Cura:* declarar (iii) como INELEGÍVEL enquanto o objeto que a executa nasce na W1, ou escrever que escolher (iii) desloca a metade W0 do AC-1 para o aceite da W1 (exatamente o tratamento que o plano já dá às invariantes 2/6/7/8).

**R-VP5 — P2 — a promessa de visibilidade do quarto sítio é escrita como suficiente quando é apenas necessária.**
`PLAN-188:569-571`: «Com esse quarto sítio no lugar, **e só com ele**, um toolkit alterado fora de cerimônia fica VISÍVEL: o CI reprova no PR seguinte.» O `shasum -a 256 -c` de `.github/workflows/smoke-install.yml:355-360` só cobre MEMBROS do `.claude/governance/gate-scripts-manifest.txt`, e a membresia do toolkit é entrega da **W1** (AC-6, `:1045`). Entre a W0 e a W1 o gatilho existe e o conteúdo verificado não inclui o toolkit: o step roda e passa. `:1155` (na OQ-6) tem a mesma redação.
*Cura:* uma frase — «gatilho (W0) + membresia (W1, AC-6); a visibilidade só existe depois das duas».

**R-VP6 — P3 — a cláusula de falha do AC-1 e o seu próprio `Check:` são legíveis como regras opostas sobre o `--list`.**
`PLAN-188:826-829` exige que o `--list` «LISTA todos os arquivos do toolkit, os `.py` inclusive»; `:851` põe como falha «o job `shellcheck-ceremony` recebendo um `.py` no conjunto do `--list`». As duas só são compatíveis se o filtro morar no CONSUMIDOR (é o que `:157-162` decide), mas a redação da falha atribui o defeito ao conjunto do `--list`.
*Cura:* «… o job `shellcheck-ceremony` invocando `shellcheck` sobre um `.py`».

## O que falta antes de executar (OQ que o Owner ratifica)

1. **OQ-9** (pré-condição da W0) — executor do runner **e** endereço do quarto sítio. *Recomendação:* (ii) workflow barato próprio, ADITIVO (o step de dentro do job `smoke` nunca sai, `ADR-192:49-53` verificado no HEAD: «fail-closed e ANTES de qualquer membro ser invocado»); (iii) só com a cura do R-VP4.
2. **OQ-7** (pré-condição da W0) — braço do `scope_generated_from`; o leitor difere nos dois braços. *Recomendação:* braço (b) (`finalize.sh` grava, `sign.sh` compara), porque não cria dívida retroativa nos 5 derivadores e a invariante 5 permanece incondicional.
3. **OQ-5** — corrigir ou congelar o classificador; enquanto aberta, o AC-4 é observação (o plano já escreve isso).
4. **OQ-1** (nº do `ADR-2xx` + wave da emenda ao ADR-010), **OQ-2** (ordem das subwaves = corte da W2), **OQ-4** (as 5 chaves de orçamento), **OQ-6** (`_CANONICAL_GUARDS`), **OQ-8** (destino dos clones). Nenhuma delas é decidida aqui.

## Nota de método

Nenhum risco acima é opinião: cada um cita `arquivo:linha` no HEAD `45877e4` ou a saída do comando que rodei. Não editei nada na árvore viva; o clone de leitura ficou em `<SP>/cc1`. Os pacotes `<PK>` citados pelo plano (W6a, W4b, W5a, W1a, SF, WR) vivem fora do repo e **não** foram lidos — `git ls-files | grep -icE 'w4b|w5a|w1a|w6a'` = 0 confirma a premissa do §Context, e por isso os AC-2/AC-3 permanecem NÃO CONCLUSIVOS nesta sessão, que é o comportamento pré-registrado deles.
