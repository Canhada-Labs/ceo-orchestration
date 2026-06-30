# ceo-orchestration — o que você ganha (nota ao CTO)

> Nota objetiva de uma página. Calibrada para um CTO cético. Sem hype — cada
> afirmação é verificável.
>
> **EN (canonical):** [CEO-ORCHESTRATION-FOR-CTO.md](CEO-ORCHESTRATION-FOR-CTO.md).

**Em uma linha:** não é um acelerador de agentes. É a **camada de governança +
auditoria** que deixa você rodar agentes de IA em fluxos sensíveis e **provar
depois o que cada um fez** — sem penalizar velocidade.

## O que você ganha (concreto)

1. **Trilha de auditoria tamper-evident.** Cada ação de cada agente entra num log
   encadeado por HMAC. Você prova — para risco, compliance ou auditoria —
   exatamente o que o agente fez, em que ordem; e qualquer alteração posterior no
   registro **é detectável** (a cadeia quebra). *Tamper-evident, não tamper-proof:
   detecta adulteração, não impede quem tem acesso ao disco — e a diferença está
   documentada.*

2. **Gates de governança que de fato bloqueiam.** Spawn de agente, edição de
   arquivos canônicos, limites de operação — aplicados no nível da chamada de
   ferramenta, como invariante, não como recomendação. "O agente não faz X sem Y"
   vira garantia (com *fail-open* deliberado em falha de infra, para nunca travar
   a sessão por bug do próprio guard).

3. **Sem pedágio de velocidade.** A governança custa **dezenas de milissegundos
   por chamada** e roda sobre um agente solo normal. Governança e velocidade são
   **ortogonais** — adotar não te deixa mais lento. Isso foi medido, não assumido.

4. **Paralelização segura quando você precisa de cobertura.** Quando faz sentido
   espalhar trabalho, está medido que **não corrompe a saída** (probes 0/10
   corrompidas, qualidade empatada). Fan-out serve para *amplitude*, não para
   velocidade.

## O que ele explicitamente NÃO faz (é por isso que dá pra confiar no resto)

- **Não deixa o agente mais rápido.** Orquestração/fan-out é estruturalmente
  ~2-3× mais cara e empatada-a-pior que um solo otimizado. **Nós mesmos testamos
  em seis experimentos e enterramos a tese de velocidade** — a literatura externa
  concorda (um agente forte ≥ vários no mesmo orçamento).
- **Não substitui seu CI/testes.** Complementa com proveniência e governança.

## Evidência (não é marketing)

- **12.007 casos de teste** parametrizados em 676 arquivos; núcleo crítico
  de governança/audit = **6.170** na camada de hooks.
- **Seis experimentos pagos que falsificaram a nossa própria hipótese** de
  velocidade. As afirmações acima são o que **sobreviveu** ao teste — não o que
  gostaríamos de vender.

## Custo de adoção

Baixo. Instalável em qualquer repo (`install.sh --ceremony user`, sem cerimônia
GPG), **Python stdlib-only**, zero dependência de infra. Overhead de runtime na
casa de milissegundos.

---

> **Resumo:** você vai rodar agentes de IA de qualquer forma. Isto é a camada que
> te deixa **provar o que eles fizeram** e **barrar o que não deviam** — sem
> custar velocidade.

**Antecipa a próxima objeção** (*"por que não só logar tudo num arquivo comum?"*):
um log comum você edita sem deixar rastro; este você não — a cadeia HMAC quebra
na adulteração, e é exatamente isso que um auditor/regulador exige. Demo de 2 min
disponível: adulterar uma linha do log → o HMAC pega na hora.
