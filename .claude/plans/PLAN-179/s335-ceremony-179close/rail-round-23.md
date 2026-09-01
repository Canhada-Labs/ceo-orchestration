# wave-179close — rail codex rodada 23 (sombra pós-curas r22, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (2 P2 + 1 P3 — 2 curados, 1 REFUTADO como resíduo já declarado; tudo antes da r24)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r23.txt` (10.632
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico.
NENHUM achado da classe basename voltou — a remoção do canal (r22)
encerrou a família dominante.

## Os achados (verificação + destino)

1. **[P2] Glob do espelho materializava o conjunto inteiro** —
   VERIFICADO: `sorted(glob.glob(...))` expandia e ordenava TUDO antes do
   cap/deadline. CURA: enumeração LAZY (`iglob`) com cap+1 e deadline por
   item; acima do cap o índice já é recusado (r15), então a ordem só
   importa até o cap — onde o sort preserva o determinismo. O controle
   dos 201 planos (r15) exercita o caminho novo.
2. **[P2] Capture do git antes do cap** — REFUTADO como resíduo JÁ
   DECLARADO (r11-F4, registro rail-round-11.md item 4): o capture é
   limitado por timeout×throughput da fatia de 1.0s (r10) — transiente
   sub-segundo, dezenas de MB no pior caso; streaming de subprocess num
   hook stdlib-only seria desproporcional para um índice OPCIONAL e
   degradável. A instrução do prompt de não re-levantar resíduos
   declarados cobre este item.
3. **[P3] Linha ABSENT dizia "topics" contando o index** — VERIFICADO:
   `files_count` inclui MEMORY.md ("0 of 2 topics" com 1 tópico + index).
   CURA: rótulo "entries" (o ramo written conta o index em separado).
   Controle: assert "entries" no teste do ABSENT.

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **349/0** (7.56s) —
contagem inalterada (asserts em testes existentes). Curas confinadas a
3 paths do EXPECTED. Refinalize + r24 na sequência.
