# DESIGN — pack `doctor-fu7` (S340, 2026-09-02/03)

> Pack de superfície LIVRE (3 paths, oráculo `--is-canonical` = 0 nos três).
> Base: `b6dce787651aaa9c06e842ce9d665cfb9d201ecd`.
> Sombra final: `<scratch>/shadow-doctor-fu7`. Derivador: `apply-doctor-fu7.py`.

---

## 1. A premissa da tarefa estava DESATUALIZADA — medido antes de tocar um byte

A tarefa pedia «tornar `scripts/doctor.sh` o TERCEIRO consumidor de
`_wbm_dst_refuses`». **Isso já estava landado** na S337 (`6160578`). Medido em
`b6dce78`, antes de qualquer edição:

| pergunta | comando | resposta |
|---|---|---|
| doctor consome o predicado? | `grep -c _wbm_dst_refuses scripts/doctor.sh` | **7** ocorrências |
| o predicado é exigido no startup? | `scripts/doctor.sh:229-231` | está na lista `_fms_req` (ausência ⇒ `exit 2` nomeado) |
| a seção D do e2e existe? | `grep -n "D\.[0-4]" scripts/tests/test-installer-write-safety-e2e.sh` | **D.0 … D.4** presentes |
| os ACs do FU-7 estão abertos? | `.claude/plans/PLAN-185-FOLLOWUP-doctor-confinement.md:63-122` | os **4 já são `[x]`** |

Censo completo de escrita no adopter em `doctor.sh` (`cp`/`mv`/`ln`/`mkdir`/
`rm`/redirect, excluindo `>&2`, `$WORKDIR`/`$SANITIZED` e `_log`):

| sítio | linhas | pré-voo | veredito |
|---|---|---|---|
| backup pré-overwrite (`mkdir -p $BAK_DIR` + `cp -p`) | 448, 472-473 | `_backup_file` → `_wbm_dst_refuses "$TARGET" "$BAK_REL_DIR/$rel"` ANTES do `mkdir` | guardado |
| restore de regfile (`mkdir -p` + `cp -p`) | 654-655 | `_restore_refuses` (fonte + `_wbm_dst_refuses`), deliberadamente ANTES do `mkdir` | guardado |
| re-link de registro LINK ausente | 710-711 | `_link_dst_refuses "$rel"` (leaf ausente ⇒ relpath inteiro) | guardado |
| re-link de registro LINK presente | 746-747 | `_link_dst_refuses` (leaf presente ⇒ o PAI) + «sem backup, sem overwrite» | guardado |
| varredura de órfãos | 985-997 | REPORT-ONLY, nada é removido | não escreve |

**Nenhum sítio desguardado.** Portanto este pack NÃO edita a superfície de
confinamento: reescrevê-la seria churn sem defeito.

## 2. O defeito que a auditoria do FU-7 encontrou ao lado (e que este pack cura)

`doctor.sh` **descarta** registros do manifesto no ingest (`_relpath_unsafe`:
traversal, path absoluto, caractere de controle, ancestral symlinkado; digest
malformado; relpath duplicado) — e o descarte é **SILENCIOSO**.

Medição (b6dce78, `<scratch>` temporário, instalação `--profile core`):

```
$ printf '%s  ../outside/victim.txt\n' <sha-que-nao-bate> >> $T/.claude/.install-manifest.sha256
$ bash scripts/doctor.sh $T --repair --yes-file ../outside/victim.txt ; echo rc=$?
    OK:        535
    Refused:   0 (destination not confined to the target — nothing written)
rc=0
```

Zero menção ao registro forjado. A propriedade de segurança **vale** (nada é
escrito fora: o descarte é o que impede), mas a outra metade do contrato do
doctor não: `rc=0` significa «verifiquei esta árvore», e ele não verificou.

É a **mesma classe** que `scripts/tests/test-doctor.sh` D.10 curou na S261 uma
camada abaixo — *«regular file swapped for a SYMLINK is reported, not silently
dropped»* — e a classe que `uninstall.sh` já nomeia do seu lado
(`unsafe manifest path`, e2e U.2). O doctor era o único dos três mudo.

### Por que `rc=1` (e não só um aviso)

Porque instalação legítima descarta **zero** registros — medido nesta árvore:

| modo | registros no manifesto | verificados | descartados |
|---|---|---|---|
| `--profile core` (cópia) | 535 | 535 | **0** |
| `--profile core --link` | 349 | 349 | **0** |

Descartar > 0 ⇒ o manifesto está malformado ou adulterado. A postura
fail-closed do FU-7 («uma recusa é um achado não-resolvido») aplica-se
igualmente a um registro que o doctor não conseguiu **ler**.

## 3. As edições (9, em 3 paths)

| # | path | o quê |
|---|---|---|
| E1 | `scripts/doctor.sh` | coletor `DROPPED_COUNT`/`_DROPPED` + `_mark_dropped` (nome sanitizado, lista capada em 20) |
| E2–E6 | `scripts/doctor.sh` | os **8 sítios de descarte** do sanitizador passam a nomear a razão (LINK sem alvo; alvo com controle; relpath inseguro ×2; sem separador; digest não-hex; digest ≠ 64; duplicado ×2 — incl. a 2ª passada) |
| E7 | `scripts/doctor.sh` | bloco de relatório ANTES do «==> Verifying …» + dobra em `UNRESOLVED` |
| E8 | `scripts/doctor.sh` | linha `Dropped:` no sumário — **condicional** |
| E9 | `scripts/tests/test-installer-write-safety-e2e.sh` | pernas **D.5** (registro `../` que escapa) e **D.6** (ancestral symlinkado) |
| — | `.claude/scripts/data/installer-write-safety-baseline.txt` | **regerado pela própria ferramenta** dentro do derivador (`--write-baseline`), nunca à mão |

Três decisões de forma que o rail cobrará:

1. **Saída de instalação sã fica BYTE-IDÊNTICA.** Tanto a listagem quanto a
   linha de sumário são condicionais a `DROPPED_COUNT > 0`. Verificado por
   `diff` entre o doctor de HEAD e o patchado sobre o MESMO alvo instalado: a
   única diferença é a linha `Source:` (o path do checkout), que não é do patch.
2. **Nome vindo do manifesto NUNCA é ecoado cru.** A classe insegura *inclui*
   caractere de controle e a linha vai para o terminal do operador: sequência
   de escape ali reescreve o que ele acredita ter lido. `LC_ALL=C tr -c
   '[:print:]' '?'` + `cut -c1-160`. **Custo declarado:** um relpath UTF-8
   legítimo aparece como `???` (byte-wise por segurança — ver residual R2).
3. **Lista capada em 20** + linha `... and N more`: um manifesto forjado com
   10 000 registros não enterra o relatório. A perna D.6 exercita o cap (196
   registros sob `.claude/scripts/`).

## 4. O derivador é auto-verificante no baseline

A regra do plano-pai («toda wave que toca `scripts/` regenera o baseline no
MESMO patch») é cumprida DENTRO do `apply-doctor-fu7.py`: ele fotografa o
conjunto de sítios (sem o número de linha), roda `check-installer-write-safety.py
--write-baseline` como subprocesso, e **RECUSA** se o conjunto mudou —
um pack que criasse um sítio de escrita novo não pode escondê-lo dentro das 291
linhas de renumeração. Medido: conjunto IDÊNTICO, só renumeração; ratchet `rc=0`
antes e depois.

## 5. O que fica de fora (e por quê)

- **Reescrever o confinamento do FU-7** — já landado e sem sítio desguardado (§1).
- **Perna e2e para registro LINK com ancestral symlinkado** — inalcançável: o
  sanitizador derruba o registro no ingest (o predicado ali é *belt-and-braces*,
  como o próprio FU-7 declarou). D.6 cobre a classe pelo lado que É alcançável.
- **FU-1 (o censo não modela «predicado domina»)** — gated na decisão do Owner
  sobre `OQ-W0-STOP`; abrir uma 4ª arquitetura de regra sem desenho novo
  repetiria a classe que já consumiu 7 levas de rail.
- **TOCTOU entre predicado e escrita** — bash não tem `openat`/`O_NOFOLLOW`;
  declarado no ADR-196 e inalterado aqui.
- **`uninstall.sh`** — fora do FILE ASSIGNMENT desta tarefa.

## 6. Residuais

- **R1 — os ACs do FU-7 já estavam `[x]`**: este pack não fecha checkbox nenhum
  do PLAN-185-FOLLOWUP. Ele PAGA um item que não estava escrito lá. Se o Owner
  quiser rastreá-lo, o lugar natural é um item novo no mesmo followup (o `status:
  draft` e a metade FU-1 continuam pendentes de decisão dele).
- **R2 — nome UTF-8 legítimo renderiza como `???`** na listagem de descarte
  (classificação byte-wise, escolha de segurança). Só afeta a MENSAGEM; a
  decisão de descartar/verificar não muda.
- **R3 — `CLAUDE.md` §5 continua afirmando «`doctor.sh` NÃO convertido (FU-7)»**
  (via `PLAN-185-installer-write-safety.md:338`), o que está DESATUALIZADO desde
  a S337. Não corrigido aqui: `CLAUDE.md` e o plano-pai estão fora do FILE
  ASSIGNMENT, e o plano-pai é `done`/terminal.
- **R4 — duplicata conta DUAS vezes** (o registro duplicado e o anterior, que a
  2ª passada remove). É proposital: cada LINHA descartada é um registro que o
  doctor não verificou. Duas linhas com o mesmo relpath e razões distintas.
