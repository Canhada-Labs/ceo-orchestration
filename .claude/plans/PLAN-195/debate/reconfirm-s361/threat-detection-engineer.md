---
plan: PLAN-195
ceremony: reconfirmação de VETO (S361)
archetype: Threat Detection Engineer
skill: security-and-auth (§Detection-as-Code; SKILL.md sha256=50cd673f…9a80, conferido)
agent_persona: Principal Threat Detection Engineer (VETO de escopo estreito — cobertura, falso-positivo, qualidade do sinal, eventos de auditoria do guarda)
generated_at: 2026-10-01T23:35:54Z
subject_sha256: c8cec366f06b94abbe6cea472ee5597160bf01aa806e894233fb0a171479a1ff
subject_commit: 6a9abb10
base_debate_sha256: 9894151f1648b0f7743cea526a89eab37f97f67326ae6b3c25227865ec6e0406
base_debate_commit: 4f0b9c0c
---

# Reconfirmação do VETO — Threat Detection Engineer (S361)

## Sujeito (o veredito vale só para ele)

- Arquivo: `.claude/plans/PLAN-195-bash-guard-indirect-execution.md`. Commitado e sem
  modificação na árvore de trabalho; HEAD `6a9abb10`.
- sha256 calculado por mim: `c8cec366f06b94abbe6cea472ee5597160bf01aa806e894233fb0a171479a1ff`.
  O mesmo valor sai de `git show 6a9abb10:<arquivo>`.
- Base do debate: `git show 4f0b9c0c:<arquivo>` dá `9894151f…0406`, o sha da minha retirada na
  rodada 2.
- Li o diff INTEGRAL `4f0b9c0c..6a9abb10` do arquivo: cabeçalho, remissões «→ item Cn», entrada
  S361 do histórico e o apêndice «Correções pós-debate S360» (C1–C11).
- Nenhuma linha do corpo do debate foi apagada sem ser reposta. Cada `-` do diff volta como `+`
  ampliado.
- `git log 4f0b9c0c..6a9abb10 -- .claude/hooks SPEC` vem vazio: o código e o SPEC estão
  byte-idênticos aos que conferi na rodada 2.

## As condições sob as quais retirei o VETO seguem de pé?

1. **Prova de emissão (k) — intacta e reforçada.**
   - Seguem no texto: um `veto_triggered` por linha BLOCK; zero eventos nos controles
     legítimos; evento de desarme afirmado pelo CONTEÚDO; desfecho «faria bloquear» na
     sub-forma rebaixada; nenhuma ação nova.
   - O C3 (3) acrescenta o que eu tinha deixado como observação: os dois níveis do kill-switch
     ficam distinguíveis no conteúdo do evento.
   - A W2 continua herdando a (k) por nome.
2. **Condições do K1 na W1-ADR — intactas.** O apêndice não toca em nenhuma delas:
   - tabela por sub-forma (equivalência × heurística), com limite em número absoluto,
     denominador e definição operacional de falso-positivo, fixada antes do replay;
   - rebaixamento só por cerimônia;
   - piso do baixador de rede;
   - kill-switch de dois níveis que emite quando desligado.
3. **Coerção do `learning_rail_disabled` — reforçada.** Pelo C3 (2), se a ADR estender as
   enumerações, o `SPEC/v1/audit-log.schema.md:484` muda no mesmo pacote. Isso fecha a deriva
   entre produtor e esquema que apontei na rodada 2. Conferido:
   - a coerção está em `_lib/audit_emit.py:7585-7591`;
   - as enumerações estão em `:8316-8321`;
   - a linha 484 do SPEC documenta as mesmas enumerações fechadas, com a coerção.
4. **Replay diferencial e exceção da W2 — mais estreitos (bom para a detecção).**
   - O C3 (1) troca o limite da exceção A3-5 do segmento do léxico do E3 para o fim da
     EXPRESSÃO do verbo de busca em termos de bash, e acrescenta uma linha BLOCK de controle com
     edição canônica depois do terminador escapado.
   - Conferido: o léxico do E3 usa `shlex` em modo POSIX (`check_bash_safety.py:2190`) e corta
     por pertença de string a `_E3_TERMINATORS` (definido em `:2047`, testado em `:2097`). Um
     terminador escapado ou citado vira a mesma string do separador real. Com o limite antigo,
     uma edição canônica depois dele sairia da varredura e viraria um BLOCK→ALLOW falso.
   - A correção fecha esse falso-negativo, que a exceção poderia ter aberto.

## As correções C1–C11 são compatíveis? Trazem risco novo ao meu domínio?

- **C4 (isolamento da cadeia viva no replay) — fortalece o meu domínio diretamente.**
  - `decide_command` diz no docstring que não faz I/O (`:3819`), mas chama
    `_e3_check_canonical_path_write` (`:3840`). Essa função, em falha do `shlex`, emite
    `veto_triggered`/`bash_parse_failed_fail_closed` (`:2197-2202`).
  - Só com `HOME` e `CLAUDE_PROJECT_DIR` isolados, o replay sobre os transcripts gravaria esses
    eventos na cadeia viva. Isso inflaria a linha de base do painel de 7 dias (17 + 10 na
    rodada 2) que o próprio plano usa.
  - O controle POSITIVO de delta 0 é indispensável, porque a maioria dos comandos do replay
    não emite nada: delta 0 sozinho não distingue «isolou» de «não emitiu».
  - Conferidos: a precedência do `CLAUDE_PROJECT_DIR_NATIVE` (`_lib/runtime_paths.py:26,144,158`)
    e o `CEO_AUDIT_LOG_PATH` como caminho do ARQUIVO (`_lib/audit_emit.py:2368-2385`).
- **C10 (terceira ocorrência da A3-5) — compatível.**
  - Conferido que o bloqueio canônico do E3 não emite (`:3839-3842`; `main()` só emite para
    credencial, bypass de hook do git, sequestro de env, egresso e reescrita, `:4186-4222`). É
    exatamente o furo que a W2 item 6 fecha.
  - P2: o caso vem de relato, sem log. Deve ficar fora do denominador da janela de
    transcripts, ou ser deduplicado se já estiver nela.
- **C8 (OQ-10: padrão NÃO; SIM vira W1c) — compatível.**
  - O padrão NÃO mantém a cobertura que aceitei na rodada 2. Os itens 8 e 9 do Goal já eram
    residuais declarados.
  - P2 de texto: o C8 não diz que o W1c herda a prova (a)–(k) e as condições do K1. Não é
    VETO, porque a minha condição («cada linha BLOCK da passada nova») já cobre a mesma passada
    no mesmo hook, e o C7 coloca o W1c na parte A. Mas na abertura do W1c vale:
    - herança explícita da prova (a)–(k);
    - as sub-formas do W1c entram na tabela do K1 antes de o próprio delta ser classificado;
    - `reason_code` de vocabulário estendido distinto do trio (a forma direta sem força passa
      hoje, `:383-418`);
    - mudança de contrato da tag `destructive` declarada na ADR.
- **C7 (teto de 4 rodadas, inclusive na W2) — compatível.**
  - A (k) é teste da bateria: se estiver vermelha, o pacote não landa, qualquer que seja a
    rodada do rail.
  - Leitura que adoto: um achado de rail que falsifique a (k) ou as condições do K1 é
    «afirmação falsa», dá NO-GO e nunca vai para o anexo.
- **C1 — compatível.** Rodar só com `--dry-run` evita gravar `threat_model_freshness_breach`
  na cadeia viva. Conferido: o emit só acontece no ramo sem a flag
  (`check-threat-model-freshness.py:298-302`). Fica fora do sinal do guarda.
- **C2, C5, C6, C9, C11 — neutros para o meu domínio.**
  - C2: leque do ADR e exceção ao teto de paths.
  - C5: as fixtures de detecção entram no mesmo commit da regra, o que satisfaz o
    detection-as-code.
  - C6: quem faz o flip.
  - C9: a OQ-8 fica como decidida no debate.
  - C11: processo desta reconfirmação.
- **Regra «onde divergem, vale o apêndice».** Nenhum item do apêndice afrouxa a (k), o K1, o
  kill-switch ou o replay diferencial. Os que tocam o meu domínio (C3, C4, C10) os apertam.

## Condições que continuam valendo

1. A (k) como está, mais os dois níveis do kill-switch distinguíveis no conteúdo (C3 (3)).
2. As condições do K1 fixadas no conteúdo mínimo da W1-ADR antes do replay.
3. BLOCK→ALLOW = zero, salvo a exceção A3-5 da W2, limitada à expressão do verbo de busca
   (C3 (1)) e com a linha de controle depois do terminador escapado.
4. O C4 por inteiro, com controle POSITIVO, no replay.
5. Extensão das enumerações ⇒ `_lib/audit_emit.py` e `SPEC/v1/audit-log.schema.md:484` no mesmo
   pacote.
6. P2 (W1c): herança da prova (a)–(k) e das condições do K1, `reason_code` distinto do trio,
   contrato da tag `destructive` declarado.
7. P2 (C10): caso rotulado fora do denominador, ou deduplicado.
8. Falsificar a (k) ou o K1 no rail ⇒ «afirmação falsa» ⇒ NO-GO, nunca anexo.

Divulgação: este registro nomeia as classes só pela forma. Nenhuma string concreta da classe
aparece aqui.

VETO: RETIRADO (sha256 c8cec366…a1ff)
