VERDICT: REJECT

1. P1 — Round-1 F1 remains unresolved.

   Plan claim: the revision makes no framework speed or throughput claims.

   Evidence: `.claude/plans/PLAN-163-substrate-uplift.md:67-68` still claims “rate-limit headroom” and “latência melhores.” `AGENTS.md:9-11` requires rejection of any documentation change adding speed or throughput claims.

   Concrete fix: remove performance/headroom claims from the benefit column and downstream documentation scope; describe only compatibility, governance, cost accounting, and auditability.

2. P1 — Round-1 F6 is only partially fixed; the fallback source and generator contract are wrong.

   Plan claim: amend ADR-149’s `FALLBACK_CHAIN` and use `generate-available-models.py` to regenerate both settings mirrors (`.claude/plans/PLAN-163-substrate-uplift.md:116-121,295-297`).

   Evidence: the actual machine-readable block is `FALLBACK_MODEL_CHAIN` at `.claude/adr/ADR-149-model-id-allowlist.md:89-93`. The generator knows only `AVAILABLE_MODELS_WORKING_SET` and `VETO_FLOOR_ALLOWED` (`.claude/scripts/generate-available-models.py:43-49`) and emits only `availableModels` (`.claude/scripts/generate-available-models.py:256-270`). Fallback equality is enforced separately by `.claude/hooks/tests/test_available_models_mirror.py:193-200`.

   Concrete fix: use the exact `FALLBACK_MODEL_CHAIN` identifier. Either extend the generator to parse and emit both settings keys, with tests, or explicitly scope separate updates of `fallbackModel` in both mirrors followed by the mirror test.

3. P1 — The revised hook oracle asserts behavior the Claude shim does not provide.

   Plan claim: intentional deny JSON is “mapped by the shim,” while accidental nonzero/no-decision remains fail-open (`.claude/plans/PLAN-163-substrate-uplift.md:157-163,317-319`).

   Evidence: the cited Claude path is a plain `exec`, preserving the hook’s exit code unchanged (`.claude/hooks/_python-hook.sh:409-413`). The plan itself states that Claude Code now treats exit 2 as blocking (`.claude/plans/PLAN-163-substrate-uplift.md:70`). Thus an accidental exit 2 cannot remain fail-open through this shim, and intentional Claude denies are consumed from exit-0 decision JSON by the harness—not mapped by the shim.

   Concrete fix: state the real contract and test it: every wired hook’s infrastructure-failure fixtures must emit `{}` and exit 0; valid security-input failures must emit exit-0 block JSON; statically reject untreated `argparse`/`SystemExit` paths. If wrapper-level normalization is intended, explicitly scope and test that implementation.

4. P1 — Round-1 F4 remains incomplete because the proposed per-architecture pin has no compatible format or consumers.

   Plan claim: replace the launcher pin with a per-architecture native-payload pin and enforce it at preflight/invocation (`.claude/plans/PLAN-163-substrate-uplift.md:243-251`).

   Evidence: the current pin contract permits exactly one 64-hex value (`.claude/governance/codex-cli-binary-sha256.txt:3-5`). Release validation reads only the first non-comment scalar and compares it to scalar `tool_versions.codex_cli_binary_sha256` (`.github/scripts/validate-pair-rail-verdict.py:323-380`). The live rail resolves and invokes Codex without hashing it (`.claude/hooks/check_pair_rail.py:312-325,545-557`). The plan neither defines a per-architecture manifest schema nor scopes migrations of these consumers; its purported “exact” payload path still contains `<arch>/…/codex`.

   Concrete fix: define the exact launcher-to-native resolution algorithm and manifest schema; update the release validator, verdict template/envelope, Gate 4, tests, and all runtime invocation paths to select and verify the current platform’s payload. Runtime verification must be mandatory before invoking the verified executable.

5. P1 — Round-1 F8 is mentioned but not actually resolved.

   Plan claim: upgrade preserves customized arrays/permissions, while every upgraded installation must contain the new fleet and `defaultMode` (`.claude/plans/PLAN-163-substrate-uplift.md:261-268`).

   Evidence: no preservation rule is stated, and `defaultMode são` does not define an expected value. Existing upgrade policy preserves settings keys and performs only additive hook merging (`scripts/upgrade.sh:19-22,30-38`). A customized `availableModels`, `fallbackModel`, or `permissions.defaultMode` cannot simultaneously be preserved unchanged and unconditionally satisfy the proposed new-value oracle.

   Concrete fix: specify baseline-aware behavior now—for each key, distinguish absent, unchanged-framework-baseline, and adopter-customized states. Define whether customized values are retained with a warning or explicitly merged, then give each branch its own fresh-install/upgrade fixture and oracle.

6. P2 — Round-1 F12 still lacks a concrete authoritative ADR decision.

   Plan claim: either amend the authoritative record or create a new ADR (`.claude/plans/PLAN-163-substrate-uplift.md:252-254`); success still describes ADR-111 as superseded (`:326-327`).

   Evidence: ADR-111 says it is superseded by ADR-120 (`.claude/adr/ADR-111-locked-corpus-governance.md:4-17`), but the ADR index says the locked-corpus ADR retains ID 111 (`.claude/adr/README.md:17-25`), while ADR-120 is the unrelated PII-core decision (`.claude/adr/ADR-120-pii-core-promotion.md:2-18`).

   Concrete fix: choose the chain explicitly in the plan. Either correct ADR-111 to the authoritative accepted locked-corpus record before amending it, or name a new ADR that supersedes the correct locked-corpus/pin provisions and updates the index. Do not preserve the false ADR-120 relationship.

7. P2 — Fresh finding: the model refresh omits required independent allowlist mirrors.

   Plan claim: add `claude-opus-5` to `VETO_FLOOR_ALLOWED`, and add Opus/Sonnet 5 to adopter parity (`.claude/plans/PLAN-163-substrate-uplift.md:123-124,138-141`).

   Evidence: ADR-149 requires independent mirrors in `validate-governance.sh` and `tier_policy_cli` (`.claude/adr/ADR-149-model-id-allowlist.md:39-43`). Those surfaces still accept only the old four IDs (`.claude/scripts/validate-governance.sh:707-723`; `.claude/scripts/tier_policy_cli/_types.py:26-34`). The proposed smoke allowlist can therefore accept models that installed governance still rejects.

   Concrete fix: inventory and update every independent model-ID validator/mirror required by ADR-149, regenerate frozen anchors where applicable, and add a non-vacuous parity test tying those accepted IDs to the ADR working set/VETO floor.

Round-1 trace: F3, F5, F7, F9, F10, and F11 are resolved. F1, F4, F6, F8, and F12 remain incomplete. F2’s original CLI-versus-wired-hook classification is corrected, but the replacement oracle introduces Finding 3.