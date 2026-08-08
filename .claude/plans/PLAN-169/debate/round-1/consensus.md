---
plan: PLAN-169
round: 1
verdicts: {vp-engineering: ADJUST, security-engineer: ADJUST, devops-engineer: ADJUST}
synthesized_by: CEO
created_at: 2026-08-08
---

# Consensus round 1 — PLAN-169

Zero REJECT, zero VETO exercido. Todas as must-fix ACEITAS; MF-2 e MF-3
aceitas com forma modificada (fundamentada abaixo). O plano v2 aplica
tudo. Numeração: VP = MF-1..7, U-1..4, R-5; Sec = R-SEC1..12 +
Unseen1..4; DevOps = D1..3.

## Decisões estruturais

1. **MF-1 (ACEITA):** W2.1 (`smoke-install.yml` é CANONICAL,
   `check_canonical_edit.py:184`) e W2.4-hook
   (`check_anti_ceo_overhead.py`, `:139`) migram para o pack W3;
   W2.4-doc fica no W2. W2 passa a ter 6 itens livres.
2. **MF-2 (ACEITA na forma (b)):** nasce **W4-C — cerimônia de
   substrato**, wave nomeada com escopo FECHADO (enumerado no plano:
   2 hooks novos + registrações no settings.json + postura
   cross-session instalada + tabela de tiers no team.md + rules
   `Agent(param:value)`). A recomendação (a) do VP (PLAN-170) foi
   registrada e recusada: o mandato do Owner é UM plano que fecha e
   publica; a proteção contra inchaço vem do escopo fechado + regra
   "item novo = wave nova, nunca inchaço de pack".
3. **MF-3 (ACEITA na forma pré-registro+E0):** o PLAN-169 executa SÓ o
   pré-registro assinado da bateria + **E0** (custo ~zero, retro).
   E1-E4 viram **PLAN-170** com orçamento próprio DECLARADO
   (estimativa honesta: 6-20M tokens, dominado por E4/E3; desenho
   pilot-first) e gatilho nomeado: **abre imediatamente após o corte
   da v1.4.0-rc.1**. v1.4.0 publica com "experimental: fleet patterns
   (bateria pré-registrada; E0 executado)". Frontmatter do 169
   re-declarado sem o peso da bateria.
4. **MF-4+MF-5 (ACEITAS):** W4.1 re-arquitetado — probes W4.1.0
   primeiro (StopFailure(rate_limit) dispara? snapshot fresco naquele
   instante? o que sobrevive a quê?); propriedade COMPRADA declarada:
   **"sessão viva e ociosa retoma sozinha"** (cron do harness;
   in-memory, morre com o terminal — LIMITAÇÃO DOCUMENTADA). "Retomar
   com terminal fechado" = fora de escopo v1.4.0 (rota: scheduler de
   SO/routines cloud; candidato PLAN-170+). O hook NÃO agenda (hook é
   subprocess; CronCreate é tool do modelo): o ARM é preventivo pelo
   modelo no threshold; o hook StopFailure grava estado+evidência para
   o turno retomado. Agendamento: `resets_at + margem ≥120s`, minuto
   ∉ {:00,:30}, teste asserta o horário EFETIVO.
5. **MF-6 (ACEITA):** W4.4 re-escopado pelo DISCO: `ConfigChange` já
   existe (PLAN-135 W2 H2) → item vira PROMOVER advisory→bloqueante
   (decisão de doutrina embutida); matchers hifenizados = **2** (ambos
   do rail codex — controle positivo + **controle RECORRENTE em CI**,
   não one-shot [Sec-Unseen3]; a semântica mudou 3× em 6 semanas);
   classes vírgula/`if:` = vacuosas neste repo (0 ocorrências);
   inversão exit-2 = 3 arquivos. P0 vira horas.
6. **MF-7 (ACEITA):** E.7 entra (shellcheck de CI passa a cobrir
   `scripts/tests/**` — o diretório da causa-raiz do W1; item novo
   W1.7) e E.11 entra no W0 (higiene POSIX `\s` nos runbooks).
7. **R-SEC1 (ACEITA — rege a EXECUÇÃO deste plano):** W0.0 = probes de
   Workflow (SubagentStart? canonical-edit bloqueado sob Workflow?)
   ANTES de qualquer execução de escrita via Workflow; até verde,
   Workflow SÓ read-only. (A execução de S298 até aqui cumpre: o
   workflow de inventário foi read-only.)
8. **R-SEC2/3/4 (ACEITAS):** quota-resume gateia no payload do
   StopFailure (autoritativo); snapshot = advisory (avisa, não
   agenda); prompt de retomada LITERAL re-entrando no Gate 1, TaskList/
   §Progress como DADO, proibição textual de cerimônia/tag/npm/
   transição de status, sem escalada de postura; gate de postura lê a
   postura EFETIVA (nunca `night-mode.json`, agent-writable).
9. **R-SEC5/7 (ACEITAS):** PreToolUse(SendMessage) default-deny; nome
   NÃO autentica; não-classificável ⇒ block (input fail-closed); infra
   ⇒ `{}` fail-open. ADR registra.
10. **R-SEC6 (ACEITA):** W2.4 prioriza cura pelo predicado/
    `PostToolBatch`; se sentinela persistir: TTL ≤ janela, single-use,
    session-bound, guarda symlink/traversal, evento na escrita E no
    consumo.
11. **R-SEC8 (ACEITA):** sanitizador PROTOCOL_SOURCE = allowlist
    positiva + WARNING nomeando a chave, assertado em teste.
12. **R-SEC9/12 (ACEITAS):** checklist de evento HMAC novo
    (_KNOWN_ACTIONS + scrub + SPEC + teste de campos) e cap/charset em
    nome de peer; toda env nova registrada em `env-inventory.json` no
    MESMO commit.
13. **R-SEC10 + R-5/VP (ACEITAS):** protocolo de fleet do PLAN-170
    proíbe `inbound=accept` com acceptEdits/bypass/night-mode; sessões
    de experimento isoladas (worktree, sem superfície canônica, sem
    GPG); pré-registro declara que constantes medidas valem para a
    POSTURA DO EXPERIMENTO, não a entregue.
14. **D1 (ACEITA):** re-pass r2 roda no HEAD que JÁ inclui as
    pré-condições de v1.3.0 (**W0 + W1 + W2-livres**; W3/W4-C são
    conteúdo v1.4.0) — NUNCA em `ad9cc3a`. Frase no W6.1.
15. **D2 (ACEITA como OQ-5):** B.a vs GA — recomendação rota (b): GA
    v1.3.0 sai com exceção NOMEADA de B.a (bug reproduzido de
    upgrade em estado malformado raro; fix na v1.4.0 via W3) no
    release-checklist/CHANGELOG. Owner pode inverter no retorno.
16. **D3 (ACEITA):** aceite do W1 instrui `gh workflow run
    ownership-nightly.yml` logo após o commit, longe do cron
    `43 6 * * *` (concurrency cancel-in-progress).
17. **U-1 (ACEITA — pergunta da classe PLAN-167):** a linha
    `crossSessionInbound` no settings.json INSTALADO passa pela
    decisão de propriedade (adopter com `accept` explícito é
    preservado; documentado na tabela de ownership ou marcado
    NÃO-OWNED). Responder no W4-C antes de escrever a linha.
18. **U-2 + Sec-Unseen1/2/4 (ACEITAS):** probes novos no W4.2.0:
    (d) `refuse` também recusa own-child?; (e) o que o HMAC registra
    HOJE de turno nascido de inbound (medir, não presumir); (f)
    PreToolUse dispara para SendMessage de subagent? Decisão de
    visibilidade de tentativas recusadas ("recusado e invisível" é
    escolha, não default) vira item do ADR com o dado do probe (e).
    Se `inbound != refuse`, claim de auditabilidade do README ganha
    escopo degradado EXPLÍCITO.
19. **U-3 (ACEITA):** W3-K em SESSÃO SEPARADA do W3 (higiene de env de
    override de kernel) — ou assert de ambiente limpo entre as duas.
20. **U-4 (ACEITA):** pré-registro do PLAN-170 exige validação do
    juiz (ground truth mecânico onde possível; LLM-judge validado em
    N labels antes de contar).

## Consequências no texto (v2)

Aplicadas no plano na sequência: W0.0 novo; W0 ganha E.11; W1 ganha
W1.7 (shellcheck) e a linha do workflow_dispatch; W2 reduz para 6
itens; W3 recebe W2.1+W2.4-hook; W4.1 re-arquitetado (probes, camadas,
propriedade declarada, agendamento com margem); W4.2.0 ganha probes
d/e/f; W4.4 re-escopado pelo disco; W4-C nasce com escopo fechado; W5
vira pré-registro+E0 e a bateria vai a PLAN-170 (gatilho nomeado);
W6.1 ganha a frase do parent_sha; OQ-5 novo; frontmatter re-orçado;
AC-1 continua válido (E.7/E.11 agora têm endereço).
