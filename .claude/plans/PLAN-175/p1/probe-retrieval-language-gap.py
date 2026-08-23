from __future__ import annotations
import json, subprocess, os
PAIRS = [
    ("audit contamination in the adopter CI workflow template", "auditar contaminacao no template de CI do adopter", "devops-ci-cd"),
    ("review authentication change and token storage", "revisar mudanca de autenticacao e armazenamento de token", "security-and-auth"),
    ("write regression test with env isolation fixture", "escrever teste de regressao com isolamento de env", "testing-strategy"),
    ("investigate p99 latency regression in a hook", "investigar regressao de latencia p99 em hook", "performance-engineering"),
    ("design postgres schema with index and migration", "desenhar schema postgres com indice e migracao", "data-schema-design"),
    ("decide between a skill and a hook for a new rule", "decidir entre skill e hook para uma regra nova", "architecture-decisions"),
    ("budget tokens and pick the model per archetype", "orcar tokens e escolher o modelo por arquetipo", "llm-routing-and-finops"),
    ("classify severity of a live incident", "classificar severidade de incidente ao vivo", "incident-management"),
]
def run(task):
    p = subprocess.run(["python3", ".claude/scripts/skill-retrieve.py", "--json", "--task", task, "--top-k", "5"],
                       capture_output=True, text=True)
    s = p.stdout
    try:
        d = json.loads(s[s.index("{"):])
        return d.get("mode"), [r["slug"] for r in d.get("results", [])]
    except Exception:
        return "PARSE-FAIL", []
en_hit = pt_hit = 0
print(f"{'esperado':<26} {'EN top1':<26} {'EN@5':<5} {'PT top1':<26} {'PT@5'}")
for en, pt, want in PAIRS:
    me, re_ = run(en); mp, rp = run(pt)
    eh = want in re_; ph = want in rp
    en_hit += eh; pt_hit += ph
    print(f"{want:<26} {(re_[0] if re_ else '-'):<26} {('SIM' if eh else 'nao'):<5} {(rp[0] if rp else '-'):<26} {'SIM' if ph else 'nao'}")
print()
print(f"recall@5 tf-idf  EN: {en_hit}/{len(PAIRS)}   PT: {pt_hit}/{len(PAIRS)}   (static-fallback medido antes: 4/8)")
