# Achados no MOLDE F (wave-s330-F) — reportados pelo clonador S334, não corrigidos lá

> A wave-F é cerimônia LANDADA (`303ae55`): material dela não se reescreve.
> Estes achados foram CORRIGIDOS no clone adrgate e ficam aqui como pauta
> para a PRÓXIMA wave que tocar a família F (ou wave de texto própria).

1. `OWNER-S331-F-LAND.sh:235` — `_keep_dir` de preservação de logs aponta
   para `s329-ceremony-main` (constante do pacote E não adaptada): com o
   dir ausente, a preservação de logs no abort falha EM SILÊNCIO.
2. `test-ceremony-scripts-F.sh:175-177` — mensagens dizem "E.patch" num
   harness da wave F (resíduo de clone).
3. `finalize-F.sh` — o dir-pai do mktemp que hospeda o WT fica órfão após
   o cleanup (parcialmente deliberado: os `$WT.*.log` sobrevivem — mas
   nunca é colhido).
4. (Já registrado nos rails r1-r2 de materiais desta cerimônia:) o F não
   arma `CEO_KERNEL_OVERRIDE` apesar de tocar `validate.yml`, e carrega
   os P2 de restore que o rail adrgate curou aqui.
