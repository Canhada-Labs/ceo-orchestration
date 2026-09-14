---
plan: PLAN-169
release: v1.4.0 (GA)
attempt: repass-ga r4 (2026-09-13, S351; r3 morreu por infraestrutura — ver ~/.rc2-backup/repass-ga-20260913-DEAD-r3/record.md)
status: NO-GO (1/7) — triado; condição 63 deixa de NOMEAR sítios; r5 sobre candidato novo
---

# Re-pass do GA v1.4.0 — tentativa r4 (NO-GO na parte 1)

- **Candidato:** `3ba9993a87081921c3ed4e44fdd2dea3311e758a` (r2 + condição 63 reescrita como CLASSE com lista de 10 linhas).
- **r3 (18:55→20:19, mesmo candidato):** partes 3–7 `GO-WITH-CONDITIONS`; **parte 1 sem veredito** — o backend do codex recusou o conteúdo a meio («This content was flagged for possible cybersecurity risk», a mesma classe da r19 da rc.1) e o subshell sumiu sem `.codex-rc-1`. Run descartado (o runner não repete parte); evidência parcial em `~/.rc2-backup/repass-ga-20260913-DEAD-r3/`.
- **r4 (20:20→21:44):** `codex rc=0` nas 7; `RUNNER-OVERALL: rc=1`. Evidência completa em `~/.rc2-backup/repass-ga-20260913-NOGO-r4/` (39 arquivos; manifesto verificado). Aqui: 7 vereditos, proveniência, manifesto, candidato.

## Vereditos r4

| Parte | Veredito |
|---|---|
| 1 `upgrade.sh` | **NO-GO — condição 63 falsa: a CLASSE inclui `upgrade.sh:2838,2944`, que descrevem CORRETAMENTE o switch `CEO_CONFIG_PROTECTION_ADVISORY` (bloqueio → allow em `check_config_protection.py:322`)** |
| 2–7 | GO-WITH-CONDITIONS (anexos P1 como known-open, 1.4.1) |

## Triagem (13/09, 21:5x)

A claim é verdadeira: `_advisory(src)` devolve `allow(system_message=…)`; as duas linhas do `upgrade.sh` falam desse switch, não do perfil no todo. A classe «todo texto que chame o perfil `user` de advisory» era AMPLA demais.

**Forma do defeito, 3.ª vez:** r1 «único», r2 «três», r4 «classe com 10 sítios» — toda enumeração de sítios no material assinado foi falsificada por um revisor que mediu o seu próprio payload. **Cura (arquitetura, não mais uma lista):** a condição 63 deixa de nomear sítios. Fica só a classe pela FORMA da promessa (global: «a superfície de hooks do perfil `user` é advisory-only») e a exclusão explícita das descrições de um hook/switch/política específica — a correção mínima que o próprio revisor do r4 pediu. Sem lista, nada a medir: a única forma de falsificar é uma promessa global VERDADEIRA, impossível enquanto `check_config_change.py` bloquear por default no perfil `user` (fato confirmado nas 4 rodadas).

**Regra de parada pré-registrada para o r5:** se a parte 1 der NO-GO de novo por TEXTO da 63, o trem PARA e a decisão sobe ao Owner com duas opções (emenda da regra do corte: claim textual sem efeito no comportamento do adopter = anexo, não NO-GO; ou cura de CÓDIGO em rc.2), em vez de uma 4.ª emenda.
