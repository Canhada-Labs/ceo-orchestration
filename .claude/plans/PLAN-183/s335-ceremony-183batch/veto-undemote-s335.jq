# PLAN-183 wave-183batch — A4 undemote (rail 183-r4 P1). As SETE chaves cuja
# demotion name-only despe skills VETO-bearing no discovery automatico; a
# lista e a AUTORIDADE do teste (TestVetoSkillsShippedAsNameOnly.bound ∩
# overrides, medida em 2026-08-31). Aplicavel aos DOIS alvos
# (.claude/settings.json e templates/settings/settings.base.json).
# del() e no-op para chave ausente: idempotente por construcao.
# rail 183-r5: o gerador emite chaves TAMBEM na grafia do frontmatter
# `name` quando difere do slug — duas VETO-bearing tinham a grafia
# loaded-name ainda demoted ("Kill Switches", "Latency Budgets"). Ambas
# entram; del() segue no-op para ausente (idempotente).
del(
  .skillOverrides["equity-research"],
  .skillOverrides["Kill Switches"],
  .skillOverrides["Latency Budgets"],
  .skillOverrides["financial-correctness-and-math"],
  .skillOverrides["financial-display"],
  .skillOverrides["kill-switches"],
  .skillOverrides["latency-budgets"],
  .skillOverrides["prediction-markets"],
  .skillOverrides["trading-execution"]
)
