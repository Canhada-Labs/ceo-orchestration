# Cerimônia W5 — runbook do Owner (6 passos, nenhum editor)

> **Você não digita `git` em momento nenhum.** Os scripts commitam e empurram.
> Se um editor abrir mesmo assim: **Esc**, digite `:q!`, **Enter** (sai sem
> salvar; nada se perde) — e chame o CEO.

---

## 1. Confira que está tudo no lugar

```
cd /Users/joaocanhada/canhada-labs/ceo-orchestration && git status --short
```

**Sucesso:** nada, ou só linhas começando com `??` (arquivos novos que não
entram no commit). **Se aparecer `M` ou `A`:** pare e chame o CEO — assinar com
a árvore suja produz uma âncora que não descreve o que será landado.

---

## 2. Assine o sentinel

```
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S327-SIGN.sh
```

O script pede a senha da sua chave GPG.

**Sucesso:** termina com `PRONTO` e imprime o próximo comando.
**Se falhar com "No pinentry":** rode, no seu terminal,
`export GPG_TTY=$(tty); gpgconf --kill gpg-agent` e repita o passo 2 do zero —
o script já restaurou o sentinel sozinho.

> A partir daqui **não commite nada**: qualquer commit invalida a assinatura.

---

## 3. Ensaie (não altera nada de forma permanente)

```
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S327-LAND.sh --dry-run --ownership-e2e=defer
```

**Sucesso:** `DRY-RUN` no fim, com `G0` a `G5` verdes e a linha
`dry-run: arvore e index restaurados byte a byte`.

**Se aparecer `RESTAURACAO INCOMPLETA` ou `FALHA AO RESTAURAR`:** pare, não
rode o passo 4, chame o CEO. A mensagem já traz o comando de recuperação.

---

## 4. Ande de verdade

```
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S327-LAND.sh --ownership-e2e=defer
```

Este passo aplica o patch, roda a verificação (V1 a V7), faz o staging,
**commita e empurra**. Leva alguns minutos — a paridade instala de verdade duas
vezes. Não interrompa.

**Sucesso:** termina com `LAND OK` e imprime o hash do commit.

**Sobre `--ownership-e2e`:** o argumento é obrigatório e não tem valor padrão.
`defer` deixa o teste longo (~25 min) para o robô noturno; `run` roda agora,
dentro do land. Use `defer` salvo instrução em contrário do CEO.

---

## 5. Se qualquer passo falhar

Toda falha imprime `ABORT:` com o motivo em uma linha e para. **Nada foi
commitado nem empurrado.**

- **Não edite nenhum arquivo à mão.** Os arquivos desta cerimônia estão
  amarrados por hash: mudar um byte invalida a assinatura e o land recusa.
- Copie a mensagem de `ABORT:` inteira e mande para o CEO.
- Se o script parou **depois** do commit e **antes** do push, ele diz isso e dá
  o comando exato para repetir só o push.

---

## 6. Depois

Acompanhe o CI. O esperado após este land: `Smoke Install` verde (a paridade
`maintainer` sai de `STALE 3` para `STALE 0`) e o `ownership nightly` com o
mesmo conjunto vermelho de sempre — `OWN-0016`, `OWN-0024`, `OWN-0027`. **Se o
nightly ficar todo verde, isso é problema, não vitória:** significa que a
tabela-verdade mudou. Chame o CEO.

---

## Ordem, em uma tela

```
cd /Users/joaocanhada/canhada-labs/ceo-orchestration && git status --short
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S327-SIGN.sh
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S327-LAND.sh --dry-run --ownership-e2e=defer
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S327-LAND.sh --ownership-e2e=defer
```
