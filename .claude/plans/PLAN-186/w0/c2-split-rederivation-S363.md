# PLAN-186 W0 — C2: re-derivação do split construtor/refutador da noite S338 (S363)

> **Item:** bullet da W0 «Re-derivar o split builder/refutador com o instrumento
> novo sobre os 7 transcripts do S338 antes de qualquer nova citação do −US$ 1.369»
> (`.claude/plans/PLAN-186-orchestrator-operating-model.md:138`; debate round 1, C2).
> **Estado deste arquivo:** PRÉ-REGISTRO. Critérios fixados e commitados ANTES de
> ler qualquer transcript; os resultados entram num commit posterior, sem mexer
> nesta seção.

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

## 2. Resultados

Pendentes — entram no commit seguinte, com cada número ao lado do comando que o
reproduz.
