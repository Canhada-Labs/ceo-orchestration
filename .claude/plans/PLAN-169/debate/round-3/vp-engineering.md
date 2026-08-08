---
plan: PLAN-169
round: 3
archetype: VP Engineering
created_at: 2026-08-08
---

# VP Engineering — round 3 (PLAN-169 v2.3): estabilização

> Método idêntico aos rounds 1 e 2 — rodei `_matches_canonical_guard`
> (`check_canonical_edit.py:896-915`) contra cada alvo NOVO da v2.3 (W2.9 e a
> lista de ARQUIVOS do W4-C) em vez de aceitar a classificação do texto.

## Verdict

**ACCEPT** — os três must-fix do round 2 estão aplicados com precisão no texto
(MF-A `:544-557`, MF-B `:229`, MF-C `:320-323`), e o que resta é um conjunto de
riscos estável e conscientemente aceito, não trabalho pendente.

## Summary

- **MF-A, MF-B e MF-C fechados, e a cura do MF-A foi estendida além do que eu
  pedi:** a lista de ARQUIVOS do W4-C (`:544-557`) inclui os canônicos que eu
  nomeei mais os três que o r7 arrastou (`_lib/audit_emit.py`,
  `SPEC/v1/audit-log.schema.md`, `check_config_change.py`) — todos confirmados
  CANONICAL pelo predicado, e `SUPPORT.md` / `.claude/scripts/env-inventory.json`
  corretamente marcados livres.
- **W2.9 está na wave certa:** `.claude/scripts/debate-converge.py` é **free**
  pelo predicado, então o conserto do instrumento cabe em W2 sem cerimônia — e
  transformar um defeito de instrumento achado no próprio debate em item
  rastreado, em vez de ajustar o veredito, é a decisão certa.
- **Conjunto de riscos estabilizou honestamente: 5 → 3.** R-2 e R-7 saem
  *curados* pelos meus próprios must-fix (MF-B e MF-C); R-1, R-6 e R-8 seguem
  vivos e reafirmados verbatim.

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

> **Contrato de reafirmação.** Os três bullets acima são byte-idênticos aos do
> meu round 2, incluindo os rótulos "(VIVO)"/"(NOVO)" e os anchors do texto v2.2 —
> perturbá-los por cosmética faria o comparador ler mudança onde não houve. Duas
> notas de honestidade: (i) o fenômeno do **R-1 se repetiu na v2.3** — o r7
> acrescentou mais três arquivos canônicos ao W4-C, terceira expansão em três
> passadas, o que confirma o risco em vez de refutá-lo; (ii) o **R-8** teve sua
> metade de *escopo* curada (`scripts/upgrade.sh` agora está nomeado em
> `:544-557`), mas a metade de *ordem* — montar o staged do W4-C contra um
> `upgrade.sh` pré-W3 — segue sem instrução, então o bullet permanece.
>
> **Retirados como CURADOS (removidos de propósito; a queda de Jaccard aqui é o
> defeito de instrumento que o próprio W2.9 documenta, não divergência):**
> **R-2** (interação W1 × W2.6 sobre o marcador) → curado por MF-B, `:229`
> declara o controle transitório, desplantado no mesmo commit, proibido atravessar
> a janela do nightly e proibido existir no HEAD candidato da rc.2 — exatamente a
> cura pedida; **R-7** (arm por instrução-ao-modelo com teste de fixture) → curado
> por MF-C, `:320-323` passa o aceite a "hook dispara ⇒ exatamente UM job EXISTE
> no horário efetivo; controle negativo ⇒ NENHUM job novo", e o R-SEC13 fecha o
> texto injetado em template constante. O caminho segue probabilístico no meio,
> mas agora é medido na ponta — que é o padrão que o repo aplica ao resto.

## Must-fix (blocking)

*(vazio — endosso a execução como está.)*

## Nice-to-have

- **Nomear agora os dois alvos previsíveis que caem em superfície canônica**, para
  não descobri-los com os packs fechados (é a instância residual do R-1, e o
  predicado já está mandado no header do W2, `:219-221`): (i) o **controle
  RECORRENTE em CI** do W4.4 P0 (`:454-455`) é wiring de workflow —
  `.github/workflows/validate.yml` é **CANONICAL**, e o W3, que já carrega esse
  arquivo por causa do W1.7-CI, fecha ANTES de o W4.4 decidir; o lugar natural é a
  lista de arquivos do W4-C. (ii) O alvo de documentação do **W2.9(ii)**: em
  `DEBATE-SCHEMA.md` é **free**, em `.claude/skills/core/debate/SKILL.md` é
  **CANONICAL** — escolher agora decide se W2.9 fica mesmo sem cerimônia.
- **Uma linha sobre a ordem de montagem do W4-C** fecharia o R-8 por completo:
  "o staged do W4-C é montado DEPOIS do W3 landar; `shasum -c` contra a árvore
  pós-W3".
- **Enumerar os atos Owner-only no checklist de retorno** (reafirmo do round 2):
  são ≥8 entre sentinels (W3, W3-K, W4-C), assinatura do pré-registro do W5,
  quatro verditos/tags dos dois trens e a aprovação `production-npm`.

## Unseen

- **O plano recomenda aos adopters desligar a ferramenta com que ele próprio se
  executa** (reafirmo do round 2, segue sem resposta): W4-C item 8 (`:536-543`) põe
  `disableWorkflows: true` como default de adopter, enquanto o mandato deste plano
  é *"use workflow"* (`:56-57`). A exceção "operador-supervisionado do meta-repo"
  continua sem **critério verificável** — o que conta como supervisão? Sem isso,
  publicamos uma postura que o próprio repo não segue, com a diferença registrada
  em prosa e não em teste.
- **Nada no texto diz o que acontece com o W4-C se o probe W4.2.0 vier ambíguo**
  (reafirmo do round 2). Itens 3 e 8 são "pós-resposta U-1" / "SE o probe
  confirmar"; num substrato de quatro dias o resultado parcial é o desfecho mais
  provável, e a wave para sem regra de decisão.
- **O W2.9 conserta o comparador que julga este próprio debate — e não há
  controle positivo declarado para o conserto.** `:232` descreve os dois defeitos
  com precisão; o que falta é a frase que o repo sempre exige: um fixture de
  crítica com `## Risks` sem bullets tem de deixar o instrumento VERMELHO e
  barulhento (hoje ele parseia zero em silêncio — família registered-vacuous).

## What I would NOT change

- **A lista de ARQUIVOS do W4-C como está** (`:544-557`), inclusive a frase "a
  fechar byte-exata na montagem do pack". É a forma certa: a lista fixa a
  intenção, e o predicado na montagem é a autoridade final.
- **W2.9 existir.** Transformar "a máquina disse diverged" em item rastreado com
  os dois defeitos nomeados — parse silencioso de seção sem bullets, e risco
  curado contando como divergência — em vez de ajustar o veredito ao número, é
  precisamente a postura que separa este repo de um teatro de governança.
- **A ordem de execução (`W0→W1→W2→W6.1→W3→…`, `:141-147`)** e o **W1 com o
  W1.7-CI fora do gate 62/3** (`:199-209`). Endossados no round 2, inalterados,
  e continuam certos.
- **O aceite end-to-end do quota-resume** (`:320-323`) e o **controle transitório
  do W2.6** (`:229`) — as duas curas foram escritas mais apertadas do que eu
  pedi, com o controle negativo explícito em ambas.
- **W4-C existir com escopo enumerado** (forma (b)) e a **bateria E1-E4 no
  PLAN-170 com gatilho e orçamento próprios**. Retirei o resíduo da minha
  recomendação (a) no round 2 e não o reabro.
- **Manter os riscos R-1/R-6/R-8 abertos sem virar must-fix.** São propriedades
  conhecidas e aceitas de um plano desta forma, não defeitos de texto; convertê-los
  em bloqueio agora só adiaria a execução sem reduzir o risco real.
