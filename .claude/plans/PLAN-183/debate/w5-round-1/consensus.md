# consensus — W5-b, round-1 ADITIVO (S324, 2026-08-23)

> **Round ADITIVO, em diretório próprio.** `debate/round-1/` é do plano
> como um todo e **não foi tocado** — provado por sha256 do conjunto,
> idêntico antes e depois de emitir estes arquivos.
>
> Síntese consumiu os textos **anonimizados** (`critic-a/b/c.md`); o mapa
> label↔lente está em `anonymization-map.md` (`PROTOCOL.md` §Debate
> regra 5).

## Veredito do round: ⛔ ESCALATE

| crítica | veredito | achados |
|---|---|---|
| Critic-A | **ESCALATE** | 10 |
| Critic-B | **ESCALATE** | 8 |
| Critic-C | PROCEED-WITH-CONDITIONS | 6 |

**24 achados, 15 deles `[P0]`.** Dois de três críticos em ESCALATE
dispara a regra do `PROTOCOL.md` §Vetoes: o CEO **não** decide — escala
ao Owner. E a razão de escalar não é volume: **dois achados derrubam
decisões que o Owner já tomou nesta mesma sessão.**

---

## O que muda decisão do Owner (verificado por mim, literalmente, antes de escalar)

### 1. A rota (ii) da OQ-5 NÃO alcança a população que ela existe para curar

`upgrade.sh:798-799`, lido no disco:

```
CEREMONY_EFFECTIVE="user"
_CEREMONY_SOURCE="default (no readable install-state — fail-safe user; pass --ceremony maintainer to opt back in)"
```

E o comentário imediatamente acima diz, do próprio autor: *"a pre-state
MAINTAINER install opts back in explicitly via
`CEO_UPGRADE_CEREMONY=maintainer`"*.

Como a entrega das duas árvores é gateada em `CEREMONY != user`
(`install.sh:1484` e `:1525`), um adopter **sem install-state legível** —
exatamente o adopter histórico — resolve `user` por fail-safe e **não
recebe nada**. Pior: o e2e é **estruturalmente incapaz** de observar
isso, porque o pin `v1.2.0` grava cerimônia (`git show v1.2.0:… | grep -c
'"ceremony"'` = 2), então a rota B sempre resolve `recorded`.

⇒ **A rota (ii) é a rota (iii) disfarçada para a população que importa**,
e o verde do CI passaria a responder uma pergunta diferente da que o
Owner comprou. Isto é emenda à OQ-5, não item de wave.

### 2. A recomendação da OQ-4 (~13 linhas) pode ser trabalho MORTO

Dois críticos convergem, por caminhos independentes, no mesmo mecanismo:
o gerador de manifesto tem **duas pistas mutuamente exclusivas**, e a
coluna `HASH_SOURCE` tem **um único consumidor**
(`_framework_manifest_set.sh:395-396`), atrás de
`elif _wbm_is_conditional`.

- Se os 5 paths entrarem como superfície **CONDICIONAL** sem
  `FMS_HASH_SOURCE_*` declarado, caem no ramo fail-closed (`:412-419`) e
  **não são gravados** — com um `NOTE` em stderr que nenhum step de CI
  grepa.
- Se entrarem como **NÃO-condicional**, as ~13 linhas novas do TSV ficam
  **inertes**: nada as lê.

E há precedente de custo registrado no próprio código
(`install.sh:2508-2511`): *"the previous attempt at this wave regressed
24 cells precisely because it left fresh installs undeclared"*.

⇒ **A OQ-4 tem um pré-requisito que eu não vi:** decidir a PISTA vem
antes de dimensionar a tabela. Minha recomendação de ~13 linhas foi dada
sem esse pré-requisito e **não deve ser ratificada como está**.

---

## Convergências (≥2 críticos ⇒ o CEO é obrigado a ajustar, regra 2)

| # | convergência | quem |
|---|---|---|
| C1 | A ordem do checklist é **inexecutável** — itens `[P1]` são pré-requisito de `[P0]`, e o item de cerimônia depende de artefato que não existe | A, B, C |
| C2 | Checks **vacuosos**: passam com o defeito presente. O caso mais claro é a asserção negativa `grep {{OWNER_HANDLE}} == 0`, satisfeita **exatamente** pelo modo de falha perigoso | A, C |
| C3 | A tabela de rotas como dado compartilhado é verificada por `grep` (prova **menção**, não **uso**), e o censo que eu landei é estruturalmente cego | A, B |
| C4 | O consumidor **destrutivo** (`uninstall.sh`) não é exercitado por nenhum Check, e a W5-b **amplia** o alcance dele | B, C |
| C5 | O enumerador nunca fixa se as duas árvores entram como entradas de **ARQUIVO** ou de **DIRETÓRIO** — e o Check de D3 assume uma das duas sem dizer qual | A, C |

## Achados isolados que eu aceito por conta própria (regra 3)

- **A enumeração do Scope segue incompleta, e um path faltante é
  CANÔNICO:** `.github/workflows/smoke-install.yml`. Eu já corrigi o
  Scope uma vez nesta sessão (por `doctor.sh`) e ele **ainda** está
  incompleto — o que confirma que enumerar Scope à mão é o instrumento
  errado; tem de ser derivado do patch.
- **A regra de registro é REGRESSÃO contra o precedente que a wave diz
  copiar.** Verificado em `install.sh:1318-1329`:
  `if [[ "$INSTALL_ONE_WROTE" = "1" ]] || cmp -s <fonte> <target>`. O
  precedente registra **também quando não escreveu**, por byte-compare —
  logo minha regra *"PRESERVED/SKIPPED ficam fora"* derruba os 5
  registros num **segundo install**, e embarca VERDE porque nenhum Check
  roda install duas vezes.
- **Existe um QUARTO sítio no `doctor.sh`** (`_dr_delivered`) que o censo
  não tinha, e ele decide **enumeração** — quem é acusado de órfão.
- **O item que a §9.8 promete** (controle positivo rodando independente
  do step principal) **não existe em checkbox nenhuma** — mesma classe
  prosa-sem-enforcement que o pair-rail já apontou.

## Disposição

**Nenhuma linha da W5-b é escrita antes de:** (a) o Owner emendar a OQ-5
com o alcance real da rota (ii); (b) o Owner decidir a PISTA do gerador,
que precede a OQ-4; (c) o checklist ser **re-sequenciado** e os Checks
vacuosos substituídos.

O que **não** muda: a W5-a segue landada e correta (`b6de7cf`), e o
diagnóstico de D1 como load-bearing para o verde segue medido.

**Custo evitado.** Este round custou uma execução de 3 agentes. Sem ele, a
implementação teria passado em todos os Checks planejados enquanto
reivindicava posse de arquivo adopter-owned e derrubava o próprio
registro no segundo install — com cerimônia GPG gasta em cima.
