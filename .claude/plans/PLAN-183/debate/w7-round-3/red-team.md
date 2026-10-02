---
plan: PLAN-183
debate: w7
red_team_for_round: 2
plan_commit: e8ac8aba
consensus_survives: true
p0_found: false
archetype: "Red Team (contingente, DEBATE-SCHEMA §12.3); skill chaos-and-resilience; claude-opus-5-5"
attacked: [w7-round-2/security-engineer.md, w7-round-2/qa-architect.md, w7-round-2/devops-engineer.md]
false_claims_found: "1, neutralizada: «(b) com R2-3 (b) = 8 paths» (proposta §R2-1 [I]; MF-QA-R2-7; Security §Paths). Medido: 11 paths. A forma (a) com manifesto, aceita por escrito pelos 3, fecha em 8 (RT-2)"
rt_conditions: [RT-1, RT-2, RT-3, RT-4, RT-5, RT-6, RT-7, RT-8, RT-9, RT-10]
---

# PLAN-183, debate L3 da W7b: Red Team sobre o consenso da rodada 2

> `[disco]` = lido no HEAD `e8ac8aba`. `[sonda]` = executado por mim fora do repositório (git show/ls-tree sobre
> tags, python3 3.9.6 local); nada foi gravado no repo. Este arquivo NÃO abre rodada 3 de críticos.

## Verdict

**O consenso SOBREVIVE: PROCEED mantido, com as condições RT-1 a RT-10.** Não há P0.
- Há uma afirmação falsa: «(b) cabe em 8 paths». Ela sustenta a escolha de 2 críticos, mas não impede o PROCEED:
  a forma (a) com manifesto tem aceite escrito dos 3 e mantém o VETO fechado.
- Por isso o consenso tem de REGISTRAR R2-1 = (a) com manifesto, e não deixar a escolha para a abertura (RT-2).

## Summary

- **Modo de falha não modelado:** os três modelaram duas populações, o repo-fonte e o adopter. Há uma terceira: as
  árvores-fixture que rodam o validador na suíte. Pelo contrato convergido, «CLI ausente ⇒ FAIL», e elas ficam
  vermelhas (RT-1).
- **Suposição não medida:** «(b) cabe em 8 paths». A contagem exata de `_lib` arrasta 2 documentos que ficam fora da
  4.ª exceção, e a RT-1 soma mais 1 path. Resultado: (b) = 11 paths e (a) = 8 (RT-2).
- **Controle verde no vácuo:** a derivação da tag por conteúdo (MF-QA-R2-10) elege a `v1.4.2`. A árvore de testes
  dela é 100 % idêntica ao HEAD, então a perna do purge passa purgando tudo. Na população real, 72 % fica KEPT (RT-3).

## Risks

- RT-R1 [W7b] HIGH: a terceira população (árvores-fixture do validador) quebra com «CLI ausente ⇒ FAIL nomeado»; `test_plan_schema_enforcement.py` fica vermelho no land e soma 1 path que nenhum crítico contou (RT-1).
- RT-R2 [W7b] HIGH: a conta de paths da R2-1 (b) é falsa (11, não 8), e as duas saídas pré-registradas divergem (Security cai para (a); QA divide o pacote) numa rodada que a C37 não deixa repetir (RT-2).
- RT-R3 [W7b] HIGH: a regra de derivação da tag do MF-QA-R2-10 elege a `v1.4.2`; a perna do purge passa no vácuo, purgando 578 de 578 arquivos, enquanto a população real da `v1.1.0` mantém 393 de 549 KEPT (RT-3).
- RT-R4 [W7b] MEDIUM: a convergência na R2-3 (b) esconde uma divergência: sem a flag, QA mantém o cwd como padrão; Security e DevOps usam a raiz derivada do caminho do script. O padrão cwd preserva a classe (RT-4).
- RT-R5 [W7b] MEDIUM: «UM predicado de repo-fonte» já é falso no HEAD: um 2.º predicado com OUTRO marcador vive em `check-substrate-drift.py`, e o censo da C12, escopado ao literal do ADR-001, fica verde com ele (RT-5).
- RT-R6 [W7b] MEDIUM: o molde `--is-canonical` que os três citam converte exceção em token; `Path.is_file()` converte em «ausente» mais de um errno. Os dois produzem «adopter» com rc 0 e atravessam a fronteira rc/token (RT-6).
- RT-R7 [W7b] MEDIUM: árvore híbrida. O WARN da C13 olha só se `.claude/hooks/tests` existe, mas essa árvore é também território do adopter; o remédio «remoção manual» manda apagar testes PRÓPRIOS dele (RT-7).
- RT-R8 [W7b] MEDIUM: a perna híbrida planta 1 das árvores que a `v1.1.0` deixava e afirma só «0 linhas PLAN-119 + resumo», sem o veredito do validador; a linha de resumo pode ser casada em saída ecoada (RT-8).
- RT-R9 [W7b] LOW: o bloco vizinho captura a saída por um arquivo compartilhado em `REPO_ROOT`; sob (a), copiar esse molde deixa um validador concorrente falsificar ou apagar o token (RT-9).
- RT-R10 [W7b] LOW: skew de versão no upgrade (validador e CLI entregues como arquivos independentes, cada um podendo ficar PRESERVED); o esperado das duas combinações não está escrito (RT-10).

## (a) P0 ou afirmação falsa que impediria o PROCEED

Não há P0. A afirmação falsa (8 paths sob (b)) fica neutralizada pela RT-2; a medição está na própria RT-2.

## (b) Condições novas de execução

1. **RT-1: árvores-fixture.**
   - Fatos [disco]: `test_plan_schema_enforcement.py:36-80` monta uma árvore só com o validador copiado (`:72`). Ela não
     tem `_lib/`, nem `check-rule-invariants.py`, nem o checker, e o teste exige rc 0 (`:133`, `:158`, `:237`). Roda
     no CI (`pytest.ini:41`, sem skip). O validador nomeia essa população (`validate-governance.sh:1163-1164`).
   - Condição: o construtor da árvore copia o CLI do predicado (+1 path); o ADR declara que toda árvore que roda o
     validador carrega o CLI. «Pular quando a árvore não parece instalação» fica proibido, porque reabre a classe do
     VETO.
   - Controle: a suíte sem o CLI copiado dá exatamente 1 FAIL nomeado.
2. **RT-2: R2-1 = (a) com manifesto, gravado no consenso.**
   - Fatos: a contagem de `_lib` é exata (`.claude/scripts/local/verify-counts.sh:202`, regra `:674-678`; 72 hoje
     [sonda]) e aparece em `INSTALL.md:213,581`, `docs/ARCHITECTURE.md:47,69` e `CLAUDE.md:53`. A 4.ª exceção cobre
     só os documentos da contagem de ADR (`PLAN-183:2219-2227`).
   - Conta: (b) = 8 + 2 + RT-1 = 11; (a) = 7 + RT-1 = 8. Só (a) com manifesto tem aceite escrito dos 3: QA
     (§Verdict), Security (frontmatter `veto`) e DevOps (escolha).
   - Condições sob (a): o modo predicado EXIGE `--repo` (hoje o default é `"."` = cwd, `check-rule-invariants.py:323-329`);
     a invocação é por `python3`; o censo da C12 fica com um dono só.
   - Ganho lateral: validador e predicado ficam na mesma árvore entregue, sem janela de upgrade parcial entre
     `.claude/scripts` e `_lib`.
3. **RT-3: a tag sai pelo predicado de ENTREGA dela.**
   - Fatos [sonda]: `backup_and_replace ".claude/hooks"` está no `upgrade.sh` de todas as tags, da `v1.1.0` à `v1.4.2`.
     Toda tag traz `.claude/hooks/tests` na árvore FONTE (a `v1.4.2` tem 578 arquivos).
   - Contra o HEAD, no mesmo relpath: a `v1.4.2` tem 578/578 arquivos idênticos, e o purge autoriza todos
     (`upgrade.sh:4199-4202`); a `v1.1.0` tem 156/549.
   - Sinal: a tag mais nova cujo `scripts/_framework_manifest_set.sh` NÃO exclui `.claude/hooks/tests`, lido por
     `git show`, que funciona com depth 1. Hoje ele elege a `v1.1.0`; a `v1.2.0-rc.1` já exclui [sonda].
   - Sanidade: se o conjunto plantado não tiver ao menos 1 hash ≠ HEAD, a perna aborta (molde do scaffold do H.14,
     `test-upgrade-historical-adopter.sh:914`). O esperado PURGED/KEPT é derivado por hash dentro do teste.
   - Declarar a população que parou na `v1.1.0`: ela tem os digests no baseline, e o esperado é PURGED (DevOps,
     Unseen 3).
4. **RT-4: o padrão da R2-3 sem flag.**
   - O padrão é a raiz derivada do caminho do script, sem `resolve()` (2 de 3; o MF-QA-R2-6 cede).
   - Hoje o argv posicional é tratado como raízes (`check-test-audit-isolation.py:600`), e uma raiz inexistente é
     pulada (`:603`). Por isso o argparse precisa reconhecer a flag; ela não pode cair no argv posicional.
   - Controle: `--repo-root` com cwd estranho dá o mesmo resultado que a chamada sem flag. O teste
     `test_check_test_audit_isolation.py:315` segue verde nos dois casos.
5. **RT-5: o 2.º predicado.**
   - Fato [disco]: `check-substrate-drift.py:803-808` decide framework × adopter pelo pin manifest do Codex OU pelo
     ADR-149.
   - Condição: o ADR declara pela FORMA «decisão framework × adopter por existência de arquivo», e o censo busca essa
     forma, não o literal. O sítio vira FU nomeado, porque responde a outra pergunta (insumo do mantenedor); nunca fica
     em silêncio.
6. **RT-6: erro nunca vira token.**
   - O molde mapeia exceção para token (`check_canonical_edit.py:2761-2764`) e lê a raiz de env/cwd (`:2747`).
   - `Path.is_file()` (`check-rule-invariants.py:217`) devolve False para ENOENT, ENOTDIR, EBADF e ELOOP [sonda: o
     `_IGNORED_ERROS` do 3.9.6].
   - Condição: o CLI não tem nenhum `except` que produza token. Só ENOENT e ENOTDIR contam como «ausente»; qualquer
     outra OSError ⇒ rc ≠ 0.
   - Controle: um errno de FS diferente, plantado em tmp, dá 1 FAIL nomeado.
7. **RT-7: WARN da C13 com evidência de origem.**
   - Fato: a árvore é excluída da entrega (`_framework_manifest_set.sh:97`), logo é território do adopter.
   - Condição: o WARN exige assinatura do framework (o fixture `_ceo_audit_isolation_session`,
     `validate-governance.sh:1174`, ou hash de uma geração entregue). O remédio nomeia `--purge-misinstalled` e a
     revisão da lista KEPT, nunca «apagar a árvore».
   - Controle: árvore própria sem assinatura dá 0 WARN.
8. **RT-8: a perna híbrida prova o veredito.**
   - Plantar todas as árvores excluídas que a tag derivada entregava (`_pm_trees` e `_pm_files`,
     `upgrade.sh:4241-4242`). Na `v1.1.0`, isso inclui `.claude/scripts/tests` (394 arquivos) e
     `_lib/test_isolation.py` [sonda].
   - Afirmar o rc 0 do validador completo, `Errors:   0` (`validate-governance.sh:1317`) e o conjunto EXATO de WARN.
   - O resumo é casado junto do rc, nunca por grep solto: o validador ecoa saída de sub-checagens (`:1004`, `:1196`).
9. **RT-9: o token vem só da substituição de comando** sobre o stdout do predicado; arquivo intermediário fica
   proibido. `:1000-1009` usa `$REPO_ROOT/.rule-invariants.out`, compartilhado e apagado com `rm -f`: molde a NÃO seguir.
10. **RT-10: skew de versão.**
    - O ADR declara as duas combinações. Validador novo com CLI antigo preservado dá rc 2 (argparse) e 1 FAIL
      nomeado. Validador antigo preservado significa que a cura não chega.
    - Um teste unitário cobre «CLI sem o modo» e espera 1 FAIL nomeado.

## (c) Já coberto pelas condições dos críticos

- **Forja do token por outro processo.** `$(...)` captura só a árvore de processos do predicado. Forjar exige
  controlar o interpretador ou o ambiente sob o mesmo UID, que já pode editar o validador; isso está fora do modelo
  (`CLAUDE.md` §5). Poluição acidental de stdout dá FAIL (MF-SEC-R2-1, MF-QA-R2-1, MF-DEVOPS-R2-2: token exato,
  «linha extra»). Sombra de stdlib: 0 colisões de nome em `_lib/`, `.claude/scripts/` e `.claude/hooks/` [sonda].
- **O marcador nunca foi entregue.** `install.sh` da `v1.0.0` (`:1064`) e da `v1.1.0` (`:1244`) entregam só
  `adr/README.md`; nenhum `upgrade.sh` toca `.claude/adr` [sonda]. Adopter com ADR-001 só existe por cópia ou fork, e
  aí o uso monótono vale (C13).
- **Dois gates presos a um marcador.** Renomear o ADR-001 desarma dois gates de uma vez; a âncora da C13 (predicado
  verdadeiro na raiz real) cobre isso.
- **Outras condições já escritas:** modo link (R2-SEC2, MF-SEC-R2-1); bit de execução (MF-SEC-R2-5, MF-QA-R2-5,
  MF-DEVOPS-R2-3); ordem com a W7a (MF-QA-R2-11); tempo do job (C38, MF-DEVOPS-R2-7); tags com depth 1 (R-QA-R2-5,
  com o sinal corrigido pela RT-3).
- **Deriva de membro do manifesto sem checagem por PR.** É R2-SEC3, e Security NTH 2 cobre. Ela já existe para o
  validador: o filtro do `smoke-install.yml` lista só 2 paths de `.claude/scripts` (`:105`, `:115`).

## O consenso sobrevive?

**Sim. PROCEED mantido, com estas condições:**
- RT-1 a RT-3 entram como condições de execução bloqueantes do SIGN.
- RT-2 muda o REGISTRO da R2-1 para (a) com manifesto. O VETO segue RETIRADO pelo texto do próprio portador.
- RT-4 a RT-10 são conferidas no rail.

Nenhum ataque mostra incoerência de desenho. Se o consenso mantiver (b) apesar da RT-2, a tabela de paths da W7b não
fecha em 8, e a C37 manda ESCALATE-TO-OWNER.

**Esforço (ADR-081):** as RT somam ~25–45k tokens dentro do pacote da W7b, sem sessão extra; a RT-1 soma +1 path
(8 sob (a)). Nenhum conteúdo lido trouxe instrução dirigida a mim, e nada foi escrito fora deste arquivo.
