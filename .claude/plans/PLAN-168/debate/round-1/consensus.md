---
plan: PLAN-168
round: 1
rounds_synthesized: [round-1]
agents_considered: [devops, qa-architect, security-engineer]
decisions_revised_in_plan:
  - "§0/§W1 — _hash_lib.sh JÁ estava nos filtros; 4 paths, não 5"
  - "§W1.3 — não existe trigger schedule:; AC-4 era insatisfazível"
  - "§W1.4 — AC-5 compara CONJUNTO DE IDs, não o arquivo (header tem paths de máquina)"
  - "§W2 — o fix não cura quem está em campo; falta reconhecedor de corpo legado"
  - "§W2 — PROTOCOL_SOURCE NÃO é persistido; o gerador não tem de onde ler"
  - "§0/§W3 — OWN-0074 é PRODUTO, não teste (minha classificação estava errada)"
synthesized_at: 2026-08-07T21:05:00Z
synthesized_by: CEO
---

# Round 1 consensus — PLAN-168

Três críticas, **três ADJUST, zero VETO**. Nenhum arquétipo rejeitou a forma
do plano; todos atacaram a mecânica — e **acertaram em tudo que verifiquei**.

Registrado como **design-coherent**. Não autoriza shipping: a cascata de
verificação (V2 rail, V3 GPG do Owner) é que autoriza.

## Consenso (2+ agentes)

**C1 — a mecânica do plano foi escrita de memória e está errada em pontos
verificáveis.** devops must-fix 2 e QA must-fix 1 são a mesma falha em lugares
diferentes. `_hash_lib.sh` JÁ estava nos dois filtros (`:15`, `:54`); o
`OWN-0074` NÃO é defeito de teste. **Ambos verificados literalmente antes de
aceitar.** É a lição
[[feedback-plan-mechanics-written-from-memory-fail]] se repetindo no plano
seguinte ao que a registrou.

**C2 — "descrever intenção não é gate".** QA must-fix 2 e devops must-fix 4
convergem: o AC-5 precisa do **script**, não do comportamento em prosa. E o
`diff` literal contra o baseline **falha sempre em CI**, porque o cabeçalho
carrega paths da máquina que o gerou.

## Insights de um agente, mantidos

1. **devops must-fix 1 — não existe trigger `schedule:`.** O AC-4 era
   insatisfazível. Pior: `schedule:` ignora `paths:`, então a divisão
   per-PR/nightly exige **dois jobs**, não duas linhas de filtro.
2. **security must-fix 1 — o fix não cura quem já está em campo.** Ponteiro com
   placeholder literal classifica `edited` ⇒ `PRESERVE_OWNED` ⇒ preservado
   para sempre. Cura: reconhecedor de corpo legado ⇒ REFRESH com backup, no
   molde do r20.
3. **security must-fix 2, CORRIGIDO E AGRAVADO na verificação.** A crítica
   dizia que o install grava `ph.PROTOCOL_SOURCE` em `:2523`. **Não grava** —
   `request.PROTOCOL_SOURCE` é `None` e a chave não existe. Logo o gerador
   compartilhado **não tem fonte de verdade**, e o W2 cresce: precisa
   PERSISTIR o valor, com fallback declarado.
4. **QA must-fix 1 — ordem W1/W2.** Se o gate do AC-5 landar antes do W2, a
   primeira CI depois do W2 falha por "o conjunto encolheu". O W2 tem de
   atualizar o conjunto esperado **no mesmo pack**.

## Rejeitados / adiados

- Nada foi rejeitado. Os 3 must-fix do security e os 4 do devops entraram; os
  2 do QA entraram.

## Ajustes no plano

§0 (tabela de evidência + linha nova do `OWN-0074`) · §W1.1 (4 paths + nota de
verificação) · §W1.2 (`--print-legacy-tag`) · §W1.3 (bloqueador do nightly) ·
§W1.4 (comparar conjunto de ids) · §W2.2-2.5 (cura, persistência, 3 caminhos
de teste) · §W3 (classificação correta) · AC-2/4/5/6/6b/6c · §6 riscos.

## Round verdict

**PROCEED** — o plano vai para `reviewed` com todos os must-fix aplicados.
Não há conflito entre críticas; todas as divergências foram entre um agente e
o plano, e cada uma resolveu por evidência literal.
