---
plan: PLAN-169
round: 5
archetype: VP Engineering
skill: core/architecture-decisions
agent_persona: "(sintetizado da linha do SKILL MAP — `VP Engineering` não tem arquivo em `.claude/agents/`; é exatamente o caso (3) que o W2.3 da v2.5 passa a tratar, codex r7)"
generated_at: 2026-08-08
---

# VP Engineering — round 5 (PLAN-169 v2.5): design executável

> Método inalterado: rodei os predicados reais contra os deltas da v2.5 em vez de
> aceitar a classificação do texto — `_KERNEL_PATHS`
> (`check_arbitration_kernel.py:77-140`) e a validação do override (`:387-394`).

## Verdict

**ADJUST** — a v2.5 é o melhor texto do arco e a reclassificação de kernel está
correta e verificada; falta **uma frase**: a janela em que o
`CEO_KERNEL_OVERRIDE` do W4-C fica exportada não está declarada, e ela cobre o
maior pack do plano. Se aplicada como descrito no MF-D, meu verdito é ACCEPT —
não preciso de outra rodada para dizer isso.

## Summary

- **A reclassificação do W4-C confere, e por mais razões do que o texto conta.**
  `.claude/settings.json`, `.claude/hooks/_lib/audit_emit.py` e
  `.github/workflows/validate.yml` estão de fato em `_KERNEL_PATHS`
  (`check_arbitration_kernel.py:90,125,135`) — e também `check_agent_spawn.py` e
  `check_canonical_edit.py` (`:78-79`), ambos já na lista de arquivos do pack.
  Mover o W1.7 para lá é a consequência certa.
- **O override é slug livre, não allowlist:** `CEO_KERNEL_OVERRIDE` aceita
  `[A-Za-z0-9._-]{1,120}` com `ACK=I-ACCEPT` (`:387-394`). Logo o "postura do
  W3-K" do protocolo é mecanicamente suficiente — não há token nomeado a
  pré-declarar. O que falta é o *tempo* em que ele fica ligado (MF-D).
- **Meu conjunto de riscos: 3 duráveis reafirmados verbatim + 1 novo.** R-1, R-6
  e R-8 persistem inalterados na v2.5; R-9 nasce da própria reclassificação de
  classe do W4-C.

## Risks

- **R-1 (VIVO, agora com evidência) — inchaço de pack por omissão de
  classificação; a lição-mãe da S296 reaparece por construção.** Entre a v2 e a
  v2.2, **W3 foi de "3-5 itens fechados" para 7 + 2 inclusões condicionais**
  (`:762-766`) e **W4-C foi de 7 para 8 itens**, com o item 3 virando quatro
  superfícies + rota de migração + testes (`:478-489`) e o item 6 ganhando uma
  decisão de piso de CLI + `SUPPORT.md` (`:494-501`). Ambos cresceram numa única
  passada de rail. A regra "item novo = wave nova, nunca inchaço de pack" está
  escrita e é a mitigação certa; o risco é que ela seja aplicada ao *item* e não
  ao *arquivo* (ver MF-A).
- **R-6 (NOVO) — a janela de congelamento do main não tem custo de saída
  declarado.** `:130-133` proíbe qualquer commit em main do corte da rc.2 até o
  GA, e `:634-635` diz que se `main` avançar vira rc.3 com hold reiniciado. A rota
  existe; o que falta é dizer o que acontece se um CI vermelho legítimo aparecer
  **durante** o hold — hoje a escolha implícita é entre quebrar o freeze e esperar
  24h com vermelho na janela.
- **R-8 (NOVO) — `scripts/upgrade.sh` é tocado por DOIS packs em sequência.** W3
  item 1 edita `:1564-1577` (B.a) e W4-C item 3(d) edita a migração em
  `:2235-2252`, com o trem v1.3.0 e o freeze entre os dois. Se o staged do W4-C
  for preparado antes do W3 landar, o `shasum -c` bate em conteúdo velho — e é
  exatamente a classe que o rail r1 acabou de pegar no script do 167 (staged stale
  que reverteria um plano posterior).
- **R-9 (novo na v2.5) — a janela do `CEO_KERNEL_OVERRIDE` do W4-C não está
  declarada, e ela cobre o maior pack do plano.** O W4-C passou de cerimônia
  canônica a cerimônia de KERNEL e sua lista de arquivos chegou a ~20 caminhos,
  incluindo quatro hooks que ainda não existem, `install.sh`, `upgrade.sh`,
  `validate.yml`, `settings.json`, `audit_emit.py`, o schema do SPEC, uma extensão
  de `_CANONICAL_GUARDS`, `team.md`, ADR, três superfícies de contagem derivada e
  duas árvores de teste. O override é um par de env vars de sessão: quanto maior o
  pack, mais tempo a capacidade mais forte do repo fica ligada. O próprio plano já
  nomeia o modo de falha — *"duas cerimônias com posturas de override diferentes
  na mesma sessão é onde um `export` sobra no ambiente"* (`:308-313`) — mas o
  aplica só ENTRE cerimônias, não DENTRO da maior delas.

> Os três primeiros bullets são byte-idênticos aos do meu round 4 (e aos do 3 e
> do 2), rótulos e anchors preservados de propósito. Nenhum retirado — nada do meu
> conjunto foi resolvido pela v2.5. R-9 é genuinamente novo: ele não existia antes
> de a v2.5 mudar a CLASSE do W4-C.

## Must-fix (blocking)

**MF-D — Declarar a janela do `CEO_KERNEL_OVERRIDE` no protocolo do W4-C
(e do W3-K).** Uma frase no protocolo (`:666-675`), na mesma forma dos outros
limites que o plano já escreve bem:

> o pack é montado e `shasum -c` fecha verde **antes** de qualquer override
> existir no ambiente; `CEO_KERNEL_OVERRIDE`/`CEO_KERNEL_OVERRIDE_ACK` são
> exportados **imediatamente antes do passo de land** e **unset logo depois**,
> com assert de ambiente limpo ao fim da sessão — nunca no início dela.

Por que bloqueia: o slug é livre (`:387-394`), então nada no substrato limita para
QUE edição o override vale — ele destrava toda a superfície de kernel enquanto
estiver setado. Num pack de ~20 arquivos montado ao longo de uma sessão, "exportei
no começo para não esbarrar no guard" é o atalho natural, e ele converte a
cerimônia de kernel numa sessão inteira com o gate desligado. Custo da cura: uma
frase e dois comandos no runbook. É o mesmo raciocínio que o plano já aceitou para
o W3-K — só que aplicado à duração, não à separação.

## Nice-to-have

- **Contar 5 kernel paths, não 3.** `:666-670` cita `settings.json`,
  `audit_emit.py` e `validate.yml`; a lista de arquivos do pack também inclui
  `check_agent_spawn.py` e `check_canonical_edit.py`, que são kernel
  (`check_arbitration_kernel.py:78-79`). A conclusão não muda — reforça —, mas
  contagem derivada de memória é a classe que este repo vigia.
- **Usar o slug nomeado por convenção** na extensão de `_CANONICAL_GUARDS`:
  os precedentes no próprio arquivo são `PLAN-080-PHASE-0B-...`,
  `PLAN-081-PHASE-2-...`, `PLAN-084-WAVE-0-...`, `PLAN-155-...`; o natural aqui é
  `CEO_KERNEL_OVERRIDE=PLAN-169-W4C-GUARD-EXTENSION`. O substrato aceita
  qualquer slug, então isto é disciplina de leitura futura, não mecanismo.
- **Completar a enumeração do Passo-0** (`:889-903`). O argumento "as waves
  perigosas são gateadas por GPG" está certo para W3/W3-K/W4-C, mas a ordem pinada
  põe **W6.1 — que publica a v1.3.0 — antes do W3**. O gate humano dele existe e
  está escrito em outro lugar (verdito assinado antes do push, tag do Owner,
  aprovação `production-npm`); falta a linha que o traz para dentro do argumento
  de segurança, senão o parágrafo parece deixar a wave de maior alcance de fora.
- Inalterados e ainda não aplicados, dos rounds 3-4: uma linha fechando o R-8
  ("staged do W4-C montado DEPOIS do W3 landar") e a enumeração dos atos
  Owner-only no checklist de retorno.

## Unseen

- **`CLAUDE.md` entrou no escopo do W4-C** (`:653-658`, contagem derivada dos 3
  hooks novos). Ele é deliberadamente NÃO-canônico
  (`check_canonical_edit.py:200-204`: "edited every session during closeout") e é
  arquivo de Gate-1 cache-stable pelo §0 do próprio CLAUDE.md. Regenerá-lo dentro
  de uma cerimônia de kernel é legítimo, mas colide com a disciplina de cache —
  vale dizer explicitamente que essa edição é de closeout do pack, não mid-sessão.
- **Quatro hooks novos entram no plano, e o `check-claude-md-claims.py` conta
  hooks.** O item de contagem derivada cobre `README*`/`CLAUDE.md`, mas o plano não
  diz quem re-gera o mapa `gen-command-skill-hook-map.py --check`
  (`validate.yml:290-291`) — se ele existe como gate e não for regenerado no mesmo
  pack, o W4-C landa e o Validate fica vermelho por drift de superfície derivada,
  dentro da janela do trem v1.4.0.
- Inalterados do round 4: o critério verificável da exceção
  "operador-supervisionado" do W4-C item 8; a regra de decisão se o probe W4.2.0
  vier ambíguo; e o controle positivo do próprio W2.9.

## What I would NOT change

- **A reclassificação do W4-C para cerimônia de kernel** e o movimento do W1.7
  para lá. Verifiquei os três caminhos citados em `_KERNEL_PATHS` e a conclusão do
  r9 está certa: com sentinel comum apenas, o pack seria bloqueado no land. Achar
  isso ANTES da cerimônia é exatamente o que o rail deveria produzir.
- **A ordem pinada** (`:166-172`) e o **W1 enxuto** (causa-raiz + riders + sweep),
  com o W1.7 fora do gate 62/3.
- **O rótulo condicional do quota-resume** (`:811-816`): "supported" só com
  live-fire GO, senão "experimental". É a aplicação literal de "nunca claim sem
  evidência" a um item que o Owner pediu — pedir não vira prova.
- **A fronteira de confiança do quota-resume declarada honestamente**
  (`:371-403`): descartar a assinatura HMAC por ser oráculo de mesmo-UID, e dizer
  que os controles defendem contra ERRO e CORRUPÇÃO e não contra adversário local,
  é mais forte do que o desenho que endossei no round 3 — um mecanismo que declara
  o que NÃO garante vale mais que um que promete demais.
- **`S` incluindo a máquina serial do caminho crítico** (`:727-733`). Segunda
  correção do E0 no mesmo sentido conservador; o teto medido fica menor e mais
  honesto, que é a direção certa para um gate que decide financiamento.
- **Manter R-1/R-6/R-8/R-9 abertos sem virar bloqueio, exceto o MF-D.** São
  propriedades conhecidas de um plano desta forma; o MF-D é o único cuja ausência
  desliga um gate em vez de apenas deixar risco na mesa.
