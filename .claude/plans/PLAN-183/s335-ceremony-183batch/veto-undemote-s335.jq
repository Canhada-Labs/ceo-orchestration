# PLAN-183 wave-183batch — A4 undemote (rail 183-r4 P1). As SETE chaves cuja
# demotion name-only despe skills VETO-bearing no discovery automatico; a
# lista e a AUTORIDADE do teste (TestVetoSkillsShippedAsNameOnly.bound ∩
# overrides, medida em 2026-08-31). Aplicavel aos DOIS alvos
# (.claude/settings.json e templates/settings/settings.base.json).
# del() e no-op para chave ausente: idempotente por construcao.
del(
  .skillOverrides["equity-research"],
  .skillOverrides["financial-correctness-and-math"],
  .skillOverrides["financial-display"],
  .skillOverrides["kill-switches"],
  .skillOverrides["latency-budgets"],
  .skillOverrides["prediction-markets"],
  .skillOverrides["trading-execution"]
)
