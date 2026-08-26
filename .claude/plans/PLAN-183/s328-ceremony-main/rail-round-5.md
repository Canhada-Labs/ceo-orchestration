# Rail (codex) — main não-canônico, rodada 5 (última)

**rc:** 0 · **saída:** 3825 B · **achados:** 6 (4 P1 + 2 P2) · **veredito literal:** ausente.

## **ZERO achados no meu escopo.**

Nenhum dos 6 toca um arquivo do FILE ASSIGNMENT. Nenhuma das 7 curas das rodadas 1-4 reapareceu.

Convergência do escopo ao longo das 5 rodadas: **4 → 2 → 1 → 1 → 0**.
(Total do rail, incluindo os outros pacotes: 7 → 6 → 19 → 5 → 6. A oscilação vem inteira do
rascunho PLAN-185, lido mais fundo a cada passada.)

---

## Parada: DECLARADA, não alcançada

O critério da task é `rc 0` **E** o literal `VERDICT: APPROVE`. Esse literal **nunca foi emitido em
nenhuma das 5 rodadas**: o `codex-cli 0.147.0` deste substrato entrega prosa de síntese + lista de
comentários por achado, sem a linha `VERDICT:`. As saídas não foram vazias nem truncadas (3-9,7 kB,
rc 0 em todas as 5), então **não é o caso F/UNAVAILABLE** do ADR-106 — é uma mudança de FORMATO do
substrato, da mesma família que a memória `reference-codex-cli-substrate-drift` já registra.

Portanto, e explicitamente: **não declaro "aprovado".** O que está provado é mais fraco e é isto —
cinco rodadas ao teto permitido, com o escopo convergindo a zero achados na última, cada cura com
verificação em `path:line` e controle positivo vermelho→verde. Quem for assinar precisa saber que a
lacuna é do instrumento, não do escopo.

*(Se o Owner quiser o literal, a rota é fixar o formato de saída — envelope de formato fixo, o mesmo
item já nomeado para a v1.4.0 no CLAUDE.md §5 — e não mais uma rodada: a rodada 5 já não tem o que
achar aqui.)*

---

## Fora de escopo — encaminhar

### `OWNER-S328-MORNING.sh` — 2 achados, o 1º AGRAVADO desde a rodada 3

- **`[P1] :468-470` — auto-revert destrutivo, e agora com um segundo dano nomeado.** Se a única
  mudança não-staged for uma edição humana intencional de `**Status:** accepted` para
  `**Status:** stale`, ela tem EXATAMENTE o mesmo diff do checker de frescor e este ramo a descarta
  em silêncio com `git checkout`. O agravante que a rodada 3 não tinha visto: isso **muta a árvore
  durante o `--dry-run` global**, um modo que declara não executar nada. A recomendação do rail é
  abortar ou pedir confirmação em vez de inferir proveniência a partir do conteúdo — proveniência não
  é derivável do diff quando as duas fontes produzem o mesmo diff.
- `[P2] :634-637` — assinatura em cache validada só por EXISTÊNCIA. Depois que o dry-run de um pacote
  assinado falha e o reparo é commitado, ou depois que um pacote anterior avança o HEAD, o `.asc`
  fica ancorado no commit velho; este ramo pula finalize e SIGN só porque o arquivo existe, o LAND
  seguinte falha na checagem de âncora, e o comando de retomada impresso não recupera. Verificar a
  âncora do sentinel antes de reusar, e regerar assinatura velha.

### PLAN-185 W0 — 2 achados

- `[P1] data/installer-write-safety-baseline.txt:40` — **5ª repetição em 5 rodadas**
  (`scripts/upgrade.sh:3727`, `sed-interp`, fingerprint `17e1bdbce06a9384`). Agora com o efeito
  medido pelo rail: `test_check_installer_write_safety.py` devolve duas falhas e o checker sai 1.
- `[P1] check-installer-write-safety.py:999-1000` — repetido da rodada 3, agora com contra-exemplo
  construído: dez `cp` dentro de `if [[ -e "$dst" ]]; then` seguidos de um 11º `cp` incondicional ⇒
  o sítio é reportado `nao-aplicavel` e a escrita perigosa nunca entra no baseline bloqueante.
  Atingir o cap tem de falhar fechado como `indeterminado`.

### PLAN-179 staged-w24 (pacote D) — 2 achados

- `[P1] .claude/settings.json:350-354` — a contagem de registrações vai de 49/46 para 50/47 e o pacote
  não inclui `test_template_dogfood_parity.py:102-103`; o ADR e o módulo `_lib` novos ainda deixam
  `CHANGELOG.md:12` em 195/70. O LAND roda esse teste E o `verify-counts.sh`, então **todo dry-run
  aborta** até esses consumidores de contagem entrarem no manifesto e no escopo do sentinel.
  (Refina o achado da rodada 3, que só tinha visto o teste de paridade.)
- `[P2] check_ledger_checkpoint.py:490-497` — terceira variante da mesma classe de wrapper
  (`stdbuf -o L git commit`, `env --chdir /tmp git commit`), mais uma NOVA direção: o skip genérico
  classifica `command -v git commit` como um commit EXECUTADO — falso positivo, não falso negativo.
  Três variantes em três rodadas nesse parser sugerem, pelo mesmo critério que apliquei ao F5/F9,
  trocar a arquitetura (modelar aridade/modos por wrapper) em vez de emendar por variante.

### Ainda aberto da rodada 4 (não re-emitido, mas não resolvido)

- `PLAN-169/s328-ceremony-B/B.patch:204-208` — o payload canônico do ADR ainda afirma que a
  implementação admite `K == cap`. A rodada 3 curou isso no código (`k >= cap`); o texto do ADR
  continua contradizendo-o. Não reapareceu na rodada 5, o que **não** é evidência de correção.

## Encaminhamentos para canônico

Nenhum vindo do meu escopo.
