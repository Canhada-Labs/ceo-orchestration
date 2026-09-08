# Rodada 4 do re-pass da v1.4.0-rc.1 — PARCIAL (candidato 144b0ef, 2026-09-08 13:13–14:11 -03)

- Parte 1 (`upgrade.sh`): **NO-GO** — condições 8 e 31 do envelope já curadas pelo pack
  `rc1-cure-2` (texto obsoleto; emenda v10) e dois P1 novos no `scripts/upgrade.sh`:
  posse por igualdade histórica sem registro anterior (`_up_tpl_generations`) e diretório
  de backup `.claude.bak` não confinado (symlink seguido por `mkdir -p`/backup); P2:
  comentário de `upgrade.sh:2629` desatualizado. Veredito íntegro em `verdict-rc1-1.txt`.
- Parte 2 (`install.sh` + manifesto + rotas): **SEM VEREDITO** — o codex perdeu a rede
  (16:54–17:09Z: `Connection refused`, `request timed out`, 5/5 reconexões) e o runner saiu
  rc=1 antes de qualquer decisão; extrato em `transcript-rc1-2.network-errors.txt`.
- Partes 3–6: não executadas (o runner aborta na primeira parte sem veredito).
- Nenhum `MANIFEST-rc1.sha256`/`RUNNER-OVERALL` foi produzido: esta rodada não é evidência
  de corte. A rodada 5 roda sobre o candidato seguinte (emendas v10 + cura do
  `OWNER-RC1-CUT.sh`), com as seis partes.
