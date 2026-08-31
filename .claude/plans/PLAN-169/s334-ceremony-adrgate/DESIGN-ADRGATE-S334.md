# DESIGN — wave-adrgate S334 (a metade de cerimônia da rota r3)

O desenho COMPLETO desta wave vive em dois lugares que este arquivo não
duplica (duplicar criaria um segundo original):

- **`../s333-ceremony-adrgate/DESIGN-ADRGATE.md`** — o desenho original da
  wave (S333), com o censo de gramática, os 11→2 erros da cura de âncora e
  os FUs nomeados.
- **`../s333-ceremony-adrgate/rail-round-3.md`** — a rota REDESENHADA que
  este patch implementa: ledger `(declarante, alvo, razão)` declarado no
  README no molde do `_load_known_chain_gaps`, mandatory-fire, e o corte
  de escopo que separou a metade LIVRE (landou em `f348ee9` e `5df5c48`)
  da metade CANÔNICA (este patch).

## O que a S334 acrescentou ao desenho da r3

1. **Fail-closed de entrada:** linha bold com seta que não parseia como
   `**ADR-NNN -> ADR-MMM: razão**` é ERRO nomeado, nunca ignorada
   (doutrina dos security matchers, `CLAUDE.md` §4).
2. **Par literal por ID-base:** declarante AMEND casa pelo base id — zero
   gramática nova (a superfície que a r1–r3 furou morreu inteira).
3. **Asserção bilateral no fixture:** corpus limpo E ledger com
   exatamente as 2 entradas firing.
4. **Índice no mesmo patch:** o flip do ADR-197 muda a linha da tabela;
   a primeira bateria da sombra REPROVOU no `--check` novo — regenerar no
   patch é obrigatório, e o gate provou valor antes de nascer.
5. **Kernel:** `validate.yml` exige `CEO_KERNEL_OVERRIDE` no LAND (molde
   wave-F, que já tocava o mesmo arquivo).
