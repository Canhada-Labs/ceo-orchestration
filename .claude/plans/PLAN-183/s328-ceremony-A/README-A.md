# PACOTE A — runbook do Owner (4 comandos, nenhum editor)

> **Você não digita `git` em momento nenhum.** Os scripts commitam e empurram.
> Se um editor abrir mesmo assim: **Esc**, digite `:q!`, **Enter** (sai sem
> salvar; nada se perde) — e chame o CEO.

**O que este pacote faz:** fecha a W5-b do PLAN-183. Marca o ADR-194 como
`ACCEPTED` (a decisão já era sua, de 25/08 — «Pista MISTA — braço C»; este
commit só põe o texto no lugar), corrige no `CLAUDE.md` a única linha que ainda
dizia o contrário, e conserta uma comparação no `install.sh` que confundia
`.github/CODEOWNERS` com `.github/CODEOWNERS.template` porque um é prefixo do
outro. Nenhuma execução de hoje muda de comportamento.

**Ordem no dia:** este é o pacote **A**, o **segundo** da fila
(**B → A → C → D**). Se você estiver usando o `OWNER-S328-MORNING.sh`, ele
chama tudo na ordem certa e você não precisa deste arquivo.

---

## 1. Confira que está tudo no lugar

```
cd /Users/joaocanhada/canhada-labs/ceo-orchestration && git status --short
```

**Sucesso:** nada, ou só linhas começando com `??` (arquivos novos que não
entram no commit).
**Se aparecer `M` ou `A`:** pare e chame o CEO — assinar com a árvore suja
produz uma âncora que não descreve o que será landado.

---

## 2. Re-baseie o pacote no estado atual do repositório

```
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/s328-ceremony-A/finalize-A.sh
```

**Rode este passo SEMPRE**, mesmo que pareça desnecessário. O pacote B entra
antes de A e move o repositório; sem este passo a assinatura do passo 3 seria
recusada.

**Sucesso:** termina com `PRONTO` e imprime o próximo comando. Se o pacote já
estiver no lugar certo, ele diz `NADA a fazer` e termina igual — os dois são
sucesso.

**Se falhar com `o A.patch NAO re-aplica`:** pare. Alguém editou os mesmos
arquivos. Copie a saída inteira e mande para o CEO. **Não force nada.**

---

## 3. Assine o sentinel

```
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S328-A-SIGN.sh
```

O script pede a senha da sua chave GPG.

**Sucesso:** termina com `PRONTO` e imprime o próximo comando.
**Se falhar com "No pinentry":** rode, no seu terminal,
`export GPG_TTY=$(tty); gpgconf --kill gpg-agent` e repita o passo 3 do zero —
o script já restaurou o sentinel sozinho.

> A partir daqui **não commite nada**: qualquer commit invalida a assinatura.

---

## 4. Ensaie (não altera nada de forma permanente)

```
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S328-A-LAND.sh --dry-run --ownership-e2e=defer
```

**Sucesso:** `DRY-RUN` no fim, com `G0` a `G5` verdes e a linha
`arvore e index restaurados byte a byte`.

**Se aparecer `RESTAURACAO INCOMPLETA` ou `FALHA AO RESTAURAR`:** pare, não
rode o passo 5, chame o CEO. A mensagem já traz o comando de recuperação.

---

## 5. Ande de verdade

```
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S328-A-LAND.sh --ownership-e2e=defer
```

Este passo aplica o patch, roda a verificação (V1 a V7), faz o staging,
**commita e empurra**. Leva alguns minutos — a paridade instala de verdade duas
vezes e o teste de baseline do install é longo. Não interrompa.

**Sucesso:** termina com `LAND OK` e imprime o hash do commit.

**Sobre `--ownership-e2e`:** o argumento é obrigatório e não tem valor padrão.
`defer` deixa o teste longo (~25 min) para o robô noturno; `run` roda agora,
dentro do land. Use `defer` salvo instrução em contrário do CEO.

---

## 6. Confira que o push saiu

```
cd /Users/joaocanhada/canhada-labs/ceo-orchestration && git log --oneline -1 && git status -sb | head -1
```

**Sucesso:** a primeira linha é o commit do pacote A, e a segunda **não** diz
`ahead`.

---

## 7. Se qualquer passo falhar

Toda falha imprime `ABORT:` com o motivo em uma linha e para. **Nada foi
commitado nem empurrado.**

- **Não edite nenhum arquivo à mão.** Os arquivos desta cerimônia estão
  amarrados por hash: mudar um byte invalida a assinatura e o land recusa.
- Copie a mensagem de `ABORT:` inteira e mande para o CEO.
- Se o script parou **depois** do commit e **antes** do push, ele diz isso e dá
  o comando exato para repetir só o push.

---

## 8. Depois

Acompanhe o CI. O esperado após este land — **tudo igual ao que já está**,
porque este pacote não muda comportamento de execução:

- `Smoke Install` verde (paridade `maintainer` e `user` com `STALE 0`).
- `ownership nightly` com o mesmo conjunto vermelho de sempre — `OWN-0016`,
  `OWN-0024`, `OWN-0027`. **Se o nightly ficar todo verde, isso é problema, não
  vitória:** significa que a tabela-verdade mudou. Chame o CEO.

---

## Ordem, em uma tela

```
cd /Users/joaocanhada/canhada-labs/ceo-orchestration && git status --short
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/s328-ceremony-A/finalize-A.sh
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S328-A-SIGN.sh
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S328-A-LAND.sh --dry-run --ownership-e2e=defer
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S328-A-LAND.sh --ownership-e2e=defer
```

---

## Para o CEO (não para o Owner)

Auto-teste dos scripts deste pacote, num clone descartável sob o scratchpad:

```
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/s328-ceremony-A/test-ceremony-scripts-A.sh
```

16 blocos de asserção, 12 deles controles POSITIVOS que têm de dar vermelho.
Ele prova, entre outras coisas, que o `--dry-run` restaura árvore **e** index
byte a byte, e que o V-block compara contra os conjuntos DECLARADOS em
`EXPECTED-BASELINE.txt` nos DOIS sentidos — um id a mais é regressão, um id a
menos é a tabela-verdade tendo mudado.
