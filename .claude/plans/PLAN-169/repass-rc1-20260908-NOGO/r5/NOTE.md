# Rodada 5 do re-pass da v1.4.0-rc.1 — PARCIAL (candidato 2b1d259, 2026-09-08 14:41–15:2x -03)

- Parte 1 (`upgrade.sh`): **NO-GO** — três P1 e um P2, todos sobre o envelope: (1) uma rota
  válida cuja FONTE está ausente ou não é arquivo regular no checkout corrente (sem `--pin`) é
  contada como `SKIPPED`, a conservação fecha, `upgrade_succeeded: true`, «Upgrade complete», rc 0
  — entrega parcial indistinguível de sucesso (a condição 34 só cobria fonte recusada por symlink);
  (2) a condição 42 mandava editar só arquivos iguais a uma geração ANTERIOR, mas igualdade com
  a geração ATUAL também normaliza modo e registra posse; (3) a mitigação da condição 43
  («`.claude.bak` diretório real») é insuficiente — um symlink pré-colocado em
  `.claude.bak/<timestamp>/docs` ou um leaf hard-linked ainda redireciona o `cp`; (P2) o
  `--help` diz que `--dry-run preview` retorna 0, mas uma precondição de rotas também sai 3 no
  dry-run. Confere as curas declaradas em 1, 8, 9 e 31. Veredito íntegro em `verdict-rc1-1.txt`.
- Parte 2: **SEM VEREDITO** — a máquina ficou sem internet a partir de ~15:24 (por horas); o
  codex esgotou as reconexões e o runner saiu rc=1; extrato em
  `transcript-rc1-2.network-errors.txt`.
- Partes 3–6: não executadas.
- Nenhum `MANIFEST-rc1.sha256`/`RUNNER-OVERALL`: esta rodada não é evidência de corte. A rodada 6
  roda sobre o candidato seguinte (envelope v11 + G0 do `OWNER-RC1-CUT.sh` retomável pós-tag).
