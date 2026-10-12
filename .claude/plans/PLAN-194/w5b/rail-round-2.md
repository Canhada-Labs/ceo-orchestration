# rail-round-2 — W5b do PLAN-194 (rail oficial, rodada 2 de no máximo 3, FINAL, com anexo)

Rail-Round: 2
Rail-Subject: .claude/plans/PLAN-194/w5b/w5b.patch
Rail-Subject-sha256: 6c691139e1c9a048b4c1b1a66586a7271d1d7e4902cd3e6b8f66319fee513bf1
Rail-Subject-patch-id: 946e4f57fc96a6fec23042ee7d5263888aed8d2a
Rail-Subject-origin: sombra w5b, `git diff --full-index --no-renames 0a953ece 01f94c78` (3 commits) — a rodada 2 revisou `0a953ece..210baa0b` (Codex e r-w5b-b) e o Codex incluiu no corte revisado o anexo `210baa0b..01f94c78` (patch-id c6777f8a57527550803a24a07a0ea13c2eecac76); a conferência do anexo foi o Codex (w5b-r2x) e a lane r-w5b-b
Rail-Sentinel-sha256: 29c245bbe4f1284c6bba66bc759a8b2acb423b28c5f087498f70dc50881894a8
Rail-Reviewer: codex-cli 0.160.0 (pin assinado 4a1eec73), exec --sandbox read-only, modelo gpt-6-astra do config do usuário (sha256 22eeacf2ce98df40…, pelo preflight — o config mudou desde a rodada 1, 9af51fe781bf86c1…; o prompt da rodada ainda citava 9af51fe7…), reasoning xhigh; refutador Claude r-w5b-b (Security Engineer)
Rail-Prompt: fora do repositório (prompts na sessão S363, 2026-10-09, scratchpad da sessão d876fa66, night/rail/w5b-r2/rail-prompt.md e night/rail/w5b-r2x/rail-prompt.md)
Rail-Date: 2026-10-09 (Codex rodada 2: preflight 19:47:16Z, saída 20:17Z; Codex do anexo: preflight 20:18:01Z, saída 20:18Z; lane r-w5b-b registrada 19:50Z — horários dos arquivos de registro, UTC)
Rail-Reviewer-Verdict: GO
Rail-Verdict: APPROVE
Rail-Findings: P0=0 P1=0 P2=0

O `w5b.patch` é o `git diff --full-index --no-renames 0a953ece 01f94c78` da sombra do sujeito (sem rename
no diff: os bytes são os mesmos com ou sem `--no-renames`), gerado pelo construtor dos materiais: patch-id
estável igual ao do sujeito (acima) e blobs pós-imagem `05f2660f…` (`scripts/install.sh`), `f13c1b5f…`
(`scripts/tests/test-install-deny-baseline.sh`), `aa9550f3…` (o baseline do censo) e `ef6240ad…`
(`docs/deny-baseline.md`), os da sombra em `01f94c78`. O `Rail-Sentinel-sha256` prende este registro ao texto
do sentinel no HEAD dos materiais; as lanes desta rodada revisaram o PATCH, não o texto do sentinel.

## Saída do revisor

```text
=== Codex, rodada 2, sujeito 0a953ece..210baa0b (o revisor incluiu o anexo 01f94c78 no corte) ===
NENHUM ACHADO

VERDICT: GO

=== Codex, conferência do anexo da rodada 2, sujeito 210baa0b..01f94c78 ===
NENHUM ACHADO

VERDICT: GO
```

## Triagem

- Codex 0.160.0 (read-only), rodada 2: «NENHUM ACHADO», GO. No log da rodada, o revisor perguntou qual corte
  receberia o veredito quando a sombra avançou para `01f94c78` e incluiu o anexo («altera apenas o parágrafo
  já conferido»); conferiu os offsets do anexo e rodou o teste de self-SHA (9/9), as pernas A–H do teste novo
  no candidato (verdes), os controles F e G no pai (vermelhos pela ausência da chave, nas duas rotas, com as
  instalações em rc 0), o smoke, o ownership e o censo (verdes); apagou os descartáveis. Palavras finais do
  log: «A revisão inclui a cura documental de `01f94c78`; não restaram achados nesse corte.»
- r-w5b-b (Security Engineer; rodada 2, sobre `210baa0b`): GO-WITH-CONDITIONS — conferiu as curas da rodada 1
  (o P2 do doc, as duas mensagens, o offset) e os offsets do binário 2.1.295 citados na mensagem de
  `210baa0b`. Um P3: `docs/deny-baseline.md:129-130` tratava «and the session is interactive» como condição
  necessária, e no binário a cláusula `(!isNonInteractiveSession || Yv() || k("tengu_moss_anchor",!0))`
  dispensa a interatividade com a flag no padrão. Cura no anexo `01f94c78` (o texto passa a dizer «and either
  the session is interactive or a server-side flag that is on by default waives that»).
- Conferência do anexo (`210baa0b..01f94c78`, só o parágrafo do doc): Codex 0.160.0 (read-only), «NENHUM
  ACHADO», GO (o segundo bloco da saída acima, verbatim); a lane r-w5b-b deu GO no anexo — veredito relatado
  pelo CEO da S363 (fila de 2026-10-09 20:19Z/20:20Z), sem saída verbatim em arquivo.
- Disposição: P0=0, P1=0, P2=0 (o P3 da r-w5b-b está curado no anexo, conferido) ⇒ APPROVE, revisor GO (a
  última linha `VERDICT:` do bloco, a do Codex do anexo). Nesta rodada houve UMA lane Claude (r-w5b-b); a
  rodada 1 teve duas (r-w5b-a e r-w5b-b).

## P2 declarados

- (nenhum)

## Saídas das lanes Claude (verbatim; o SIGN não lê esta seção)

### r-w5b-b

```text
RAIL r2 W5b — r-w5b-b, 2026-10-09T19:50:07.023Z — texto final verbatim:

Refutação W5b — lane B — rodada 2, HEAD 210baa0b (sobre b03934b9), 2026-10-09. Só leitura; binário 2.1.295 (sha 0116ee2e…f047f70) só por bytes; nenhuma cópia criada nesta rodada.

CURAS CONFERIDAS:
- P2 (doc do opt-out): docs/deny-baseline.md:122-133 agora diz que o opt-out e o caso fail-open deixam `permissions.defaultMode` sem gravar e que o 2.1.295 pode abrir em auto; traz data + substrato e «not a documented contract». Condições citadas batem com o binário: `Y` = `disableAutoMode==="disable"` (permissions ou top-level) @190139373; `ae()` = killswitch `tengu_auto_mode_config` @190129409; `ALn()` = `k("tengu_harbor_willow",!0) || meadow_lantern` da conta @190139063; `k_r()` taint/pending @190135842; `_="auto",L=!0` @190134699; `v_r` @190129550. Todos os offsets da mensagem do commit conferem (nome 187383022, describe 187383085; o 187383255 era a frase «auto mode is now the default» dentro da describe — P3 do Codex curado).
- P3 (mensagens): install.sh:2502 «would NOT touch deny baseline + defaultMode» e :2510 «SKIP: deny baseline + defaultMode — settings.json pre-existed…» — verdadeiras; mesmo número de linhas; `check-installer-write-safety.py` rc=0 na sombra (rodado por mim). As mensagens antigas só sobrevivem em transcritos/evidências de planos (PLAN-158/166/167/169), nenhum oráculo as grepa.
- P3 (template:67) e P3 (teste fora do CI): declarados como resíduos no commit com rota (cerimônia que regenera o template; follow-up de wire + nome na bateria do LAND). Aceito.

ACHADO:
- [P3] docs/deny-baseline.md:129-130 — «…allows it, and the session is interactive» declara a interatividade como conjunção. No binário a cláusula é `(!isNonInteractiveSession || Yv() || k("tengu_moss_anchor",!0))` dentro de `v_r` (@190134521): com a flag `tengu_moss_anchor` no padrão (true) a sessão NÃO precisa ser interativa — `claude -p`/headless também cai no auto. A mensagem do commit diz «com exceções»; a doc perdeu a ressalva, e o erro vai na direção de SUBESTIMAR a exposição (é o caso do night-run; o PREREG da W5c1:97 usa `--permission-mode manual` por isso). Reprodução: bytes acima. Cura (1 frase): «…and the session is interactive — unless a second server-side flag, on by default, waives that» ou simplesmente remover «and the session is interactive».

VERDICT: GO-WITH-CONDITIONS
```
