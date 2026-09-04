# wave-s343-w4a — rail codex rodada 1 (patch, sombra em 76578f3, S343 2026-09-03/04)

Rail-Verdict: CHANGES-REQUESTED (1 P1 real: a janela de required-check)

Comando: `codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretório da sombra
(`<scratchpad>/shadow-w4a`), stdin `</dev/null`. Saída bruta:
`s343-ceremony-w4a/evidence/rail-r1-raw.txt` (5 826 linhas). Árvore da sombra
intacta depois da rodada (só os 2 paths do patch modificados).

## Veredito do codex, verbatim no que importa

«The patch moves test enforcement outside the sole documented required status
without requiring the replacement matrix checks. It also lacks the mandatory
signed sentinel evidence for canonical workflow changes.»

### [P1] Keep the moved test suites behind a required check — REAL

«When Path A branch protection is enabled using the documented configuration,
the only required Validate status is `validate / Governance, health,
contamination, shellcheck` (`docs/BRANCH-PROTECTION.md:101-105`). After this
deletion the hook/script suites run only in `hook-tests-python-matrix`, a
different status, so a failing matrix can coexist with a green required job
and still permit merging; require the 3.9/3.12 matrix statuses in the same
rollout or retain these suites in the required job.»

**Aceito.** O codex chegou sozinho, com a MESMA citação de linha, ao achado
r24 P1 do relatório da S340 — duas fontes independentes sobre a mesma classe.
O pacote declarava a janela como residual; uma nota não é cura para um achado
que o rail levanta.

**Cura (materiais, não patch):** o **G7** do LAND. Ele LÊ a config viva por
`gh api repos/<slug>/branches/<branch>/protection/required_status_checks` e
classifica em quatro estados: `covered` (os dois legs já são obrigatórios →
passa), `unprotected` (404 → a janela não se abre hoje, e o gate diz por quê),
`window` e `unreadable` → o land **para** até o Owner passar
`CEO_W4A_REQUIRED_CHECK_ACK=I-ACCEPT`, com o comando de remediação impresso.

**Por que a cura NÃO entra no patch:** a metade que decide é config
SERVER-SIDE (não volta com `git revert`) e não é um path; e escrever o
conjunto novo em `docs/BRANCH-PROTECTION.md` sem flipar a config documentaria
um estado que não existe. As duas metades são do Owner — o lugar de exigi-las
é o land, com ele presente.

**Controle positivo:** `T25` do harness roda o LAND sem o ack e exige vermelho
com a razão nomeada; os demais casos passam o ack, para que cada um continue
ficando vermelho pelo SEU motivo.

### [P1] Attach signed sentinel evidence — estrutural, não é defeito do patch

«This checkout has no PLAN-186 `approved.md` plus detached `.asc` authorizing
either workflow edit… (`AGENTS.md:86-91,110`)»

O sentinel e o `.asc` vivem na árvore VIVA: os materiais são commitados ANTES
do SIGN (P0-d) e o `.asc` nasce no SIGN. Eles **não podem** existir na sombra
por construção — o `finalize-w4a.sh` RECUSA qualquer path fora do EXPECTED
(passo 1), e o `finalize_patch.py` derivaria um Scope contendo o próprio
sentinel. É o MESMO item que a r5 do `wave-fable51` registrou antes de um land
real (`ab56e76`). A autorização de cada path canônico é provada no G5 do LAND
pela MESMA função que o hook usa (`_sentinel_grants_path`), contra a
assinatura GPG do Owner verificada no G1, e o KERNEL (`validate.yml`) pelo
override de menor escopo com o par reason/ack validado VIVO contra
`_override_granted()`.

## Zero achados sobre o conteúdo do patch

Nenhum item sobre as 5 edições, sobre a cobertura, sobre o delta de ambiente
ou sobre o bump do timeout. A rodada 2 revisa a superfície com o contexto de
cerimônia dado explicitamente, para que o item estrutural não consuma a
rodada.
