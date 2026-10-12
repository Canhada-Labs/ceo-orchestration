# PLAN-186 W0 — C2: re-derivação do split construtor/refutador da noite S338 (S363)

> **Item:** bullet da W0 «Re-derivar o split builder/refutador com o instrumento
> novo sobre os 7 transcripts do S338 antes de qualquer nova citação do −US$ 1.369»
> (`.claude/plans/PLAN-186-orchestrator-operating-model.md:138`; debate round 1, C2).
> **Estado deste arquivo:** §1 é o PRÉ-REGISTRO, commitado ANTES de ler qualquer
> transcript (o commit anterior deste arquivo no `git log --follow` só tem a §1);
> §2 são os resultados. **Resposta curta:** o split 80/20 não sobrevive (85/15), e a
> figura de −US$ 1.369/mês não sobrevive como número mensal citável (§2.3).

## 1. Pré-registro

### 1.1 Fonte do papel de cada agente

Os sidecars `agent-*.meta.json` dos 7 agentes da corrida `wf_e3144372-b04`
(sessão `f52979b1-4c83-4346-9217-5f07d8d51bde`) têm 48 bytes e só as chaves
`agentType` (`workflow-subagent`) e `spawnDepth` (1): **não classificam papel**.
A ação da triagem («classificar pelos sidecars») não é executável como escrita.

Fonte usada: o registro da corrida `<project-dir>/<sessão>/workflows/wf_e3144372-b04.json`,
lista `workflowProgress`, entradas `type: workflow_agent` (`agentId` + `phaseTitle`).
Mapa fixo: `Cure` e `Build` → construtor; `Verify` → refutador. Fase fora do mapa,
agente sem transcript ou transcript sem agente ⇒ recusa nomeada, rc 2.

**Desenho** não tem fase própria no registro. A classe de 3 vias usa a atribuição
DECLARADA do relatório 05 §2.2 (política C: «design/síntese Fable 5.1 $57,85», o
custo publicado do agente `aeee4ec1aac1a5e3c`) — não é derivação mecânica. O split
de 2 vias, que é o que gera o −US$ 1.369, conta esse agente como construtor, como
o 05 contou (os 80 % do 05 só fecham com ele dentro).

### 1.2 Janela da noite

O registro da corrida dá início `startTime` = 2026-09-02T01:31:33.868Z e fim
`timestamp` = 2026-09-02T04:00:40.990Z. A janela proposta pela triagem
(`--since-at 2026-08-31T00:00:00Z --until 2026-09-02T00:00:00Z`) termina 1 h 31 min
antes do primeiro spawn e não contém nenhum registro da noite: corrigida para os
limites do próprio registro.

### 1.3 A figura e a fórmula

A figura é a diferença entre os cenários (i) e (iv) do 05 §5.2 sobre o perfil de
30 d dos subagentes: (i) 100 % `claude-opus-5` = $8.209,02; (iv) 80 %
`claude-sonnet-5` + 20 % `claude-fable-5-1` = $6.840,49; Δ = −$1.368,53 ≈ −$1.369.
Com S(m) = custo do perfil de subagentes inteiro repreçado no modelo m e b = fatia
do construtor:

    Δ(b) = b·S(sonnet-5) + (1 − b)·S(fable-5-1) − S(opus-5)

Sobre a tabela de contrafactuais publicada (05 §1.4: 2.905,12 / 1.162,05 /
3.043,47) Δ(0,80) = −$1.366,79; a diferença de $1,74 para a tabela de cenários é
interna ao 05 e não muda nenhum veredito abaixo. A re-derivação usa a MESMA janela
de 30 d que o AC-1 reproduziu (`2026-08-03T00:00:00Z` → `2026-09-02T12:55:05.807Z`),
o pipeline do instrumento shipado (dedup por `message.id`, máximo por campo) e a
tabela de preço padrão dele.

### 1.4 Critérios (decididos antes de olhar os dados)

- **K0 — controle de fonte.** O leitor «estilo 05» (chave `(requestId,
  apiBlockIndex, message.id)`, primeira linha vence) sobre os 7 transcripts tem de
  reproduzir a tabela 05 §2.1: 843 turnos e $223,50 no total. Se não reproduzir, a
  comparação «05 contra instrumento» por agente fica declarada como NÃO atribuível.
- **K1 — o split.** «Construtores 80 % / refutadores 20 %» (tokens brutos) SOBREVIVE
  sse a fatia re-derivada do construtor, em tokens brutos, cair em [78 %, 82 %].
- **K2 — a figura.** −US$ 1.369/mês SOBREVIVE sse Δ(b re-derivado) sobre o perfil
  re-derivado cair em ±5 % de −$1.368,53, isto é, em [−$1.436,96; −$1.300,10].
- **K3 — a inflação «~2,8×».** A afirmação do debate (round 1, C2/K11) de que os
  absolutos desses arquivos estão inflados ~2,7-2,9× SOBREVIVE sse a razão
  tokens brutos «estilo 05» / instrumento, no total dos 7, cair em [2,7; 2,9]. O
  viés por papel existe sse as razões de construtor e refutador diferirem mais de
  10 % entre si.

Células K1 × K2, fixadas antes:

| K1 split | K2 figura | leitura |
|---|---|---|
| sobrevive | sobrevive | a figura pode ser citada, sempre com o comando que a reproduz |
| sobrevive | cai | o split vale, a figura cai pelo PERFIL (correção do instrumento); cita-se o número novo |
| cai | sobrevive | coincidência de compensação: cita-se só com os dois fatores separados e a compensação declarada |
| cai | cai | a figura não sobrevive; cita-se o número novo |

Em qualquer célula o relatório separa os dois fatores: Δ(0,80) sobre o perfil
re-derivado (só o perfil muda) e Δ(b re-derivado) (os dois mudam).

## 2. Resultados (medidos em 2026-10-12, corpus vivo, Python 3.9.6)

Comandos, da raiz do checkout principal (num worktree o resolvedor aponta para
outro slug: passe `--project-dir` com o diretório de estado do checkout principal):

    C=.claude/plans/PLAN-186/w0/c2-split-rederivation-S363/classify-s338.py
    python3 $C              # [A] 7 transcripts da noite (leve)
    python3 $C --figure     # [B] = [A] + perfil de 30 d (lê o corpus inteiro)
    T=.claude/scripts/ceo-cost-transcripts.py
    python3 $T --since-at 2026-09-02T01:31:33.868Z --until 2026-09-02T04:00:40.990Z --by role,model --json  # [N]
    python3 $T --since-at 2026-08-03T00:00:00Z --until 2026-09-02T12:55:05.807Z --by role,model --json     # [P]

[A] e [B] rodaram duas vezes cada, saídas byte-idênticas (sha256 começa por `599355e1d867e019`
e `1439a1b04d8315d7`). [N] rodou duas vezes: diferem só `elapsed_s` e `lines` (o corpus cresce
com a sessão corrente); `grand_total`, `by_role`, `by_role,model`, `unresolved_models` e as
contagens de dedup são idênticos.

### 2.1 Por agente (instrumento shipado; «05» = leitor estilo 05)

| agente | fase | turnos | tokens brutos | USD | turnos 05 | USD 05 |
|---|---|---:|---:|---:|---:|---:|
| `a27d43c4c3afec442` | Cure | 18 | 2.709.359 | 5,50 | 64 | 16,78 |
| `a506a7af45201e703` | Build | 78 | 16.971.263 | 11,13 | 144 | 19,62 |
| `ab057190f4e9d6857` | Build | 39 | 11.659.737 | 19,16 | 143 | 65,33 |
| `aeee4ec1aac1a5e3c` | Build | 92 | 35.731.850 | 20,48 | 262 | 57,85 |
| `a4df5635cd955284b` | Verify | 13 | 2.563.906 | 7,13 | 68 | 32,49 |
| `aaaed0571dadc41d4` | Verify | 26 | 4.654.229 | 4,10 | 78 | 11,47 |
| `aaec11aac18b6d0f3` | Verify | 21 | 4.575.497 | 5,09 | 84 | 19,95 |
| **total** | | **287** | **78.865.841** | **72,59** | 843 | 223,50 |

Todos os turnos são `claude-fable-5-1`, entre 01:31:41Z e 04:00:00Z de 2026-09-02.
Controle cruzado: a linha `subagent | claude-fable-5-1` de [N] dá **287 turnos e
$72,59**, igual à soma da tabela — o script e a CLI são o mesmo pipeline.

### 2.2 Veredito dos critérios

- **K0 — PASSA.** O leitor estilo 05 reproduz **42 de 42** células da tabela 05 §2.1
  (`k0_celulas_05` em [A]): a tabela vem desses 7 arquivos com aquela chave.
- **K1 — CAI.** Fatia do construtor em tokens brutos: **85,05 %** (refutador 14,95 %),
  fora de [78 %, 82 %]. Em USD: 77,52 % / 22,48 %. Em 3 vias (tokens brutos):
  construtor 39,74 %, desenho 45,31 %, refutador 14,95 % (`split_raw_tokens`, `split_usd`).
- **K3 — a inflação SOBREVIVE, o mecanismo NÃO.** Razão 05 / instrumento no total:
  **2,87×** em tokens brutos (3,08× em USD), dentro de [2,7; 2,9]. O viés por papel
  existe, mas ao contrário do que o debate supôs: refutador **3,80×**, construtor
  **2,71×** (`inflacao_05_sobre_instrumento`). O 05 SUBESTIMOU a fatia do construtor
  (80,24 % → 85,05 %).
- **K2 — INDECIDÍVEL no corpus vivo** (célula não prevista no pré-registro;
  declarada aqui). O perfil de 30 d não existe mais em disco: o registro mais antigo
  da janela hoje é de **2026-08-23T17:59:02Z** (`figura.cobertura` em [B]); em [P] o
  assento `claude-fable-5` tem **2.344** turnos, contra os 8.248 que a mesma janela
  dava em 2026-09-04 (S344, AC-1). O arquivo `.jsonl` mais antigo do projeto tem
  mtime 2026-08-23T18:07Z. O `cleanupPeriodDays: 90` do projeto (desde `9777a8de`,
  v1.0.0) não explica o corte, e a configuração de usuário tem valor maior: a causa
  não foi medida. A retenção NÃO garante o corpus até ~29/11; os 7 arquivos da noite
  seguem no disco hoje, e os números deles agora estão neste relatório.

Controles vermelhos: `--until 2026-09-02T02:31:00Z` em [N] cai para 189 turnos / $52,67;
`--since-at` posterior a `--until` ⇒ rc 2 com recusa nomeada; a janela da triagem tem ZERO
turnos `claude-fable-5-1` de subagente. Mutante A (chave estilo 05 SEM `apiBlockIndex`) ⇒
K0 = **0/42**: é esse campo que reproduz o 05. Mutante B (dedup do instrumento trocado por
«primeira linha vence») ⇒ soma $68,77 ≠ $72,59 da CLI, e o split só vai a 85,07 %. Recusas
rc 2 (fase desconhecida, agente sem transcript, registro ausente) provadas em fixtures sintéticas.

### 2.3 A figura de −US$ 1.369/mês

`figura_contrafactuais_05` ([A], só o split muda) e `figura.delta_iv_menos_i` ([B],
perfil sobrevivente 2026-08-23T17:59Z → 2026-09-02T12:55Z; S(opus-5) $1.568,10,
S(sonnet-5) $627,24, S(fable-5-1) $1.765,34). Fração = Δ / S(opus-5):

| b (fatia do construtor) | Δ, contrafactuais do 05 | fração | Δ, perfil sobrevivente | fração |
|---|---:|---:|---:|---:|
| 0,80 (publicado) | −1.366,79 | −47,0 % | −713,24 | −45,5 % |
| 0,8505 (re-derivado, tokens) | −1.461,72 | −50,3 % | −770,67 | −49,1 % |
| 0,7752 (re-derivado, USD) | −1.320,18 | −45,4 % | −685,05 | −43,7 % |
| 0,3974 (sem o agente de desenho) | −609,30 | −21,0 % | −255,02 | −16,3 % |

A coluna do perfil sobrevivente é análise POSTERIOR ao pré-registro (cobre ~10 dos
30 dias): serve para a fração, não para o valor mensal.

**Resposta: a figura NÃO sobrevive como número mensal citável.** (1) O split que a gera
cai (K1). (2) Só a correção do split, com o perfil publicado intacto, já leva Δ a
−$1.461,72 — 6,8 % acima, fora da faixa do K2. (3) O perfil de 30 d não pode mais ser
re-derivado, então não há absoluto mensal que a substitua. O que se mede é a FRAÇÃO: com o
agente de desenho dentro dos construtores, 44-50 % de S(opus-5) nos dois perfis; com ele
fora, 16-21 %. Esse agente sozinho tem 45,31 % dos tokens da noite, e o próprio 05 o trata
dos dois jeitos (§2.2 o separa como desenho; §5.2 o conta nos 80 %). Qual leitura vale é
decisão de quem fixa a matriz de roteamento, não deste relatório. Histórico: o assento é
`claude-opus-5-5` desde a Emenda 3 do ADR-149 (`.claude/settings.json:796`) e os
subagentes herdam o assento (`:789`); a figura descreve agosto/setembro, não o roteamento de hoje.
