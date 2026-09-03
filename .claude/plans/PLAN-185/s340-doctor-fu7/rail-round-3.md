Rail-Verdict: CHANGES-REQUESTED (r3 no land, S340: 1 P2 REAL — curado na v3 do derivador; r4 a seguir)

# Rail round 3 — land do pack `doctor-fu7`, árvore re-derivada v2 (S340, 2026-09-03)

Rodada sobre a árvore viva staged após a v2 (`codex exec review --uncommitted`, gpt-5.6-sol,
~9,5 min; TREE-INTACT `5bf40b30…` antes e depois). Um achado, verificado e curado por
re-derivação (3 paths de volta ao HEAD → derivador v3 do zero, 14 edições/3 paths).

| # | sev | sítio | achado (codex) | verificação | cura |
|---|---|---|---|---|---|
| 1 | P2 | `scripts/doctor.sh:357` (e o alvo do LINK) | `[[:cntrl:]]` depende de locale: sob `LC_ALL=C`/`POSIX` casa só C0+DEL, então um byte C1 cru (0x9b, CSI de 8 bits) passava pelos dois guards novos e saía cru em `SOURCE-BLOCKED`/`MISSING` | REAL, reproduzido por sonda: `local LC_ALL=C; case … *[[:cntrl:]]*` → 0x9b «clean»; sob `C.UTF-8` → «cntrl» | E13: predicado `_field_has_control_bytes` independente de locale — `local LC_ALL=C` + `[[:cntrl:]]` (C0/DEL byte a byte), `$'\xc2'[$'\x80'-$'\x9f']` (C1 como UTF-8 válido) e, para qualquer campo não-ASCII, validação UTF-8 via `iconv` (byte 8-bit solto nunca é UTF-8 válido; sem `iconv` ⇒ não-ASCII recusado, fail-closed). E3 e E10 passam pelo predicado. Sonda pós-cura idêntica sob `C.UTF-8` e `C`: 0x9b/ESC/C2 9B/DEL → UNSAFE; «relatório», «Ç» → ok |

Colateral do próprio pack (não do codex): o predicado acrescenta dois `>/dev/null` que o censo
`check-installer-write-safety.py` lista como write-candidate «indeterminado»; a v3 tentou
aplicar e o derivador RECUSOU com rollback (o mecanismo da r2 funcionando). Resolução pela
regra do plano-pai — dizer, não esconder: `DECLARED_NEW_SITES` (hashes `47ab7820643a26c6`,
`8720061f6e06825a`) tem de aparecer no baseline regenerado e QUALQUER outro ganho/perda
continua a recusar.

Controle positivo (E14 = perna e2e D.8): árvore HEAD + derivador v2 + e2e v3 → D.8 vermelho em
«registro NÃO descartado sob LC_ALL=C» e «byte 0x9b cru no output»; D.7 verde nessa árvore.
Fora do escopo: nada. A r4 corre sobre a árvore v3 antes do commit.
