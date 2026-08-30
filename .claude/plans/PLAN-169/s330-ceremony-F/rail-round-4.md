# Pacote F — rail codex rodada 4 (shadow-F curada da r3, 2026-08-30 ~15:05 -03)

Rail-Verdict: CHANGES-REQUESTED (1 P1 + 2 P2, os três reais, os três curados)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh`. Modelo `gpt-5.6-sol`, esforço xhigh. Saída bruta:
`<scratchpad efd20343>/rail/r4.txt`.

> **Wrapper: `TREE MOVED` — e a culpa é do operador, não do revisor.** Editei o
> `DESIGN-F` na sombra enquanto o rail rodava sobre ela. O guard recusou
> reportar a rodada como válida, que é exatamente por que ele existe: uma
> revisão de uma árvore que mudou por baixo não é uma revisão do patch. Os
> achados abaixo são legítimos (foram feitos sobre o código, que não mudou), mas
> a **rodada 5 roda sobre árvore congelada** — a superfície revisada tem de ser
> a superfície entregue.

## Achados

- **[P1] Proveniência, não localização** — `gen-settings-user-template.py:982-985`.
  A cura da rodada 3 confinava o `--spec` do `--write` ao repositório. Um
  `spec.json` **untracked** escrito em qualquer lugar da árvore passava — e
  então dirigia a escrita de um template canônico via Bash, onde
  `check_canonical_edit` não olha (ele casa `Edit|Write|MultiEdit`). *Estar
  dentro do repositório não é proveniência.* **REAL.**
- **[P2-a] Campos desconhecidos em entrada de exclusão** — `:403-408`. Com
  `event` digitado como `events`, todos os campos obrigatórios validavam,
  `get("event")` devolvia `None`, e a entrada virava exclusão **NUA** —
  removendo TODAS as registrações do hook, com o artefato regenerado passando no
  `--check`. **REAL, e a pior forma da família:** um typo que ALARGA a subtração
  de um hook de segurança.
- **[P2-b] Sobrevivente exigido incondicionalmente** —
  `test_install_user_skips_governance_hooks.py:205-209`. **Over-correction
  minha, da rodada 3.** A asserção positiva que eu acrescentei exige que uma
  exclusão qualificada deixe outra registração viva; para um hook que a base
  registra sob aquele ÚNICO evento, a exclusão o remove por inteiro,
  legitimamente, e o teste falharia num spec válido. **REAL.**

## Curas

**P1 — a pergunta mudou.** `--write --spec` passa a exigir um spec que o **git
VIU**: rastreado, e sem modificação pendente. Um arquivo assim passou pela mesma
revisão que qualquer outro; um untracked foi revisado por ninguém, e um
rastreado-mas-modificado tem a cópia revisada e a cópia que dirige a escrita
divergindo — que é o vetor inteiro. Fail-CLOSED também quando o git não
responde: proveniência inverificável não é proveniência. Gate de POLÍTICA
(rc 1), nunca INFRA (rc 2).

**P2-a** — `_EXCLUSION_ENTRY_FIELDS`, vocabulário fechado por entrada, checado
ANTES de ler `event`.

**P2-b** — a asserção pergunta à BASE antes de exigir sobrevivente.

## Verificação

- **Controle de três provenências, medido:** untracked ⇒ rc 1 «UNTRACKED»;
  rastreado e limpo ⇒ **rc 0, escreve**; rastreado e modificado ⇒ rc 1
  «MODIFIED». Mais o caso fora-da-árvore ⇒ rc 1, e `--check` externo ⇒ permitido.
- `WriteRefusesAnOutOfTreeSpec` virou `WriteRefusesAnUnreviewedSpec`, 5 casos,
  rodando contra um repositório git SINTÉTICO (`git init` + commit na fixture) —
  a árvore descartável agora é também uma árvore versionada, porque o contrato
  passou a ser sobre versionamento.
- 4 testes novos de vocabulário de entrada, incluindo o de não-vacuidade («o
  conjunto fechado não pode ser mais estreito que o artefato que ele governa»).
- **Controle vermelho** com o gerador pré-r4: 2 vermelhos (untracked e
  modificado — os dois que a r3 aceitava), e o template **byte-idêntico** antes
  e depois.
- Bateria **252 → 258**.

## Disposição

Sombra CURADA e **congelada**. Rodada 5 sobre ela, sem edição concorrente.
