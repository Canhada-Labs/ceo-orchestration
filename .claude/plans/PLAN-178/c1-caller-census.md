# PLAN-178 — Censo de callers do C1 (pré-requisito do enforce; consenso r1 must-fix A-7)

> Read-only, S305. Pergunta: quem hoje produz spawn SEM
> `## FILE ASSIGNMENT` e seria quebrado por um enforce fail-closed?

## Resultado

| Caller | Estado | Consequência p/ C1 |
|---|---|---|
| `inject-agent-context.sh` (gerador canônico) | **NÃO emite FILE ASSIGNMENT** (zero ocorrências no script) | 🔴 O caminho PADRÃO de spawn quebraria no dia do enforce. A cura C1 INCLUI o gerador: emitir o bloco sempre (arg `--files` ou default explícito "NENHUM arquivo para escrita") |
| `.claude/workflows/*.js` (4 skills, 13 `agent()`) | zero FILE ASSIGNMENT refs | 🔴 **DESCOBERTOS hoje** (codex r2 P1): o rail não passa pelo hook E as 4 skills shipadas NÃO têm validador — o validador pré-despacho só existe no piloto inline (`wf_f2707efc`, prova de mecanismo). Ficam classificados descobertos até o Lote B wirar o validador ANTES de cada `agent()` nos 4 arquivos |
| `.claude/agents/*.md` (arquétipos) | maioria sem FA no corpo | OK por design — FA é por-tarefa, adicionada no spawn; mas a doc do arquétipo deve APONTAR isso (hoje implícito) |
| `.claude/commands/*.md` | 3 comandos citam FA (debate, spawn, ...) | `/debate` e `/spawn` já instruem o bloco; conformes |
| Spawns ad-hoc do CEO | variável | Janela advisory-com-audit (path_count=0) mede a taxa real de omissão antes do flip |

## Consequência para o Lote B

O patch C1 tem TRÊS partes indivisíveis (não duas):
1. Hook: exigir bloco parseável (fail-closed) + rejeitar só-wildcard +
   emitir `spawn_file_assignment_recorded` com path_count=0 na
   ausência (fase advisory) + rota de recuperação testada.
2. **Gerador: `inject-agent-context.sh` passa a emitir o bloco
   SEMPRE** (sem isso o enforce quebra o caminho feliz no dia 1).
3. ADR-191 documenta o contrato novo (spawn sem FA = rejeitado após a
   janela advisory).

Flip do enforce só depois da janela advisory medir a taxa de omissão
(gate measure-first, mesma doutrina do C5).
