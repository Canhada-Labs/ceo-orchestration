#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""census_runtime.py — PLAN-186-FOLLOWUP-census-runtime, W0.

Censo papel->modelo derivado do RUNTIME, nao de fingerprint sobre
texto-fonte. Emite EXATAMENTE quatro linhas — uma por superficie — para
as quatro superficies que a nota S340 do AC-12 nomeia e rotula «dona
local»:

    VETO_HARDCODE          .claude/scripts/tier_policy_cli/_constants.py
    routing-matrix.yaml    .claude/dispatcher/routing-matrix.yaml
    agents/*.md            .claude/agents/<slug>.md  (frontmatter `model:`)
    MODEL_HINT             .claude/scripts/inject-agent-context.sh

TRES classes de dono, nenhuma delas lida por heuristica de coluna:

  * ``python-importavel`` — o modulo e IMPORTADO e PERGUNTADO
    (``VETO_HARDCODE``), no CONTEXTO REAL DO PACOTE.
  * ``dado`` — o parser do PROPRIO DONO manda. Para o YAML e o
    ``routing-matrix-loader.py`` (stdlib) que define a semantica em
    runtime; ``yaml.safe_load`` roda so como CROSS-CHECK quando PyYAML
    existe, e divergencia entre os dois e VERMELHO
    (``matrix_parser_disagreement``) — nunca um censo que muda de
    resposta conforme o ambiente. Para ``agents/*.md`` e o parser de
    frontmatter do repo (``_lib/frontmatter.py``), um arquivo por papel,
    CHAVEADO PELO SLUG DO ARQUIVO (e assim que
    ``_lib.agent_frontmatter.resolve_agent_file`` resolve papel em
    runtime); um ``name:`` que discorde do slug e VERMELHO.
  * ``script-shell`` — o censo NAO LE o valor do ``MODEL_HINT``: ele
    PERGUNTA AO RUNTIME. O bloco ``case "$DETECTED_SKILL" in`` … ``esac``
    do script RASTREADO do repo e executado **VERBATIM, INTEIRO**, uma vez
    por SONDA, sob as MESMAS opcoes de shell que o dono declara (a linha
    ``set -…`` do proprio arquivo), e o valor publicado e o ``$MODEL_HINT``
    que aquela execucao PRODUZ, lido por um canal EMOLDURADO com nonce
    (a saida comum do bloco nao consegue se passar pelo valor). Ha uma
    sonda por ALTERNATIVA LITERAL de cada braco: assim o
    primeiro-braco-que-casa decide, como no runtime, e duas alternativas
    do MESMO braco que rendam valores diferentes sao publicadas
    SEPARADAMENTE. Nao produzir vinculo — braco morto
    (``if false; then …; fi``), braco anterior que casa antes sem atribuir,
    ou o script abortando por ``set -e`` — e VERMELHO
    (``hint_probe_yields_no_value`` / ``hint_probe_no_binding``).
    Reconstruir o ``case`` braco a braco NAO bastava: era a mesma pergunta
    numa gramatica nova (pair-rail r2 P1 e r3 P1 ×2). Executar o bloco do
    DONO, e nao um bloco montado por este censo, e a troca de arquitetura
    que fecha a classe.

    COBERTURA DECLARADA desta superficie — o que a guarda de cobertura
    RESPONDE e, explicitamente, o que ela NAO responde. A linha
    ``MODEL_HINT`` publicada por este censo e uma OBSERVACAO
    NAO-EXAUSTIVA, e a tabela a marca assim na coluna «cobertura»: ela
    vale para as sondas que este censo DERIVOU e EXECUTOU, e nao e uma
    afirmacao sobre todo o keyspace do dono nem sobre toda rota dele.
    DENTRO da cobertura estao as QUATRO formas que a r4 do pair-rail
    mediu, cada uma fail-CLOSED:
    (i) braco COMPACTO de uma linha (``padrao) corpo ;;``) e reconhecido,
    e o span do ``case`` e verificado por PARTICAO — nao por contagem
    (``_assert_arm_partition``): o corpo de cada braco RECONHECIDO vai da
    linha do seu padrao ate o seu terminador ``;;``, limitado pelo inicio
    do braco seguinte, e tudo o que sobra nas LACUNAS entre esses corpos
    tem de ser branco ou comentario; uma linha de CODIGO numa lacuna e
    ``hint_arm_coverage_incomplete`` — o censo recusa em vez de omitir a
    rota. Contar terminadores NAO fechava a classe (duas contagens erram
    juntas: ``padrao) corpo ;; # nota`` escapava aos DOIS regexes e as
    mantinha iguais — pair-rail r5, P1), e por isso nao existe aqui
    nenhuma comparacao de contagens. Esta guarda responde por bracos que
    a particao consegue DELIMITAR; o que ela nao delimita esta no item
    (v), FORA da cobertura;
    (ii) alternativa com ASPAS ou escape e recusada
    (``hint_pattern_probe_underivable``), porque o dono remove as aspas ao
    casar e a sonda literal cairia noutro braco;
    (iii) o braco curinga ``*`` recebe UMA sonda sintetica — isso e uma
    OBSERVACAO sobre aquela entrada, nunca o vinculo de todo o keyspace que
    ``*`` casa (um default que dependa da entrada, p.ex. ``DETECTED_SKILL``
    vazio, fica NAO observado), e a linha publicada carrega a limitacao no
    proprio rotulo (``*[sonda sintetica; nao generaliza]``);
    (iv) as opcoes de shell vem da declaracao ``set -…`` do dono, com
    comentario inline removido; uma declaracao que EXISTE e nao e
    interpretavel e ``hint_shell_options_uninterpretable``.
    FORA da cobertura, por construcao e por MEDIDA (pair-rail r6; os dois
    achados foram REPRODUZIDOS por plant em copia descartavel — tabela
    byte-identica e rc 0):
    (v) DELIMITACAO dos bracos quando mais de um braco ocupa a MESMA
    linha (``a) ... ;; escondido) ... ;;``): a gramatica de ``;;`` do
    ``bash`` permite isso, e uma particao «linha do padrao … terminador»
    nao a enxerga — a rota escondida sai da tabela em SILENCIO. Fechar
    por regra pediria um PARSER de shell, nao mais um regex;
    (vi) ALCANCABILIDADE do bloco: mesmo extraido e executado com
    fidelidade perfeita, o vinculo publicado pode ser um que o dono real
    NUNCA executa (``case`` sob ``if false; then … fi``, dentro de funcao
    nunca chamada, ou depois de um ``exit``). Isso nao e mais uma forma:
    e uma pergunta que a extracao de um TRECHO nao pode responder por
    construcao — so a execucao do dono INTEIRO a responde.
    O residual que NAO fecha por instrumento, e que e a rota de cura de
    (v) e (vi): enquanto esta superficie nao tiver uma API de dono a quem
    PERGUNTAR (as outras tres tem), derivar QUAIS sondas rodar continua
    sendo leitura de gramatica. A cura e dar um DONO ao ``MODEL_HINT``
    (funcao shell com contrato, ou um dado que o script consome) — edicao
    CANONICA, fora do alcance de um pack livre; e a opcao (3) da
    ``ARCHITECTURE-NOTE-S347.md`` §5, e os dois itens estao NOMEADOS como
    residuais no proprio plano.
    A guarda de cobertura que este censo EXECUTA e uma varredura por
    SUBSTRING dentro de ``read_model_hint``, e nao um regex: uma linha
    do arquivo do dono que contenha o literal ``MODEL_HINT=`` tem de
    estar dentro do bloco ``case`` e fora do heredoc
    ``MODEL_HINT_HEADER`` (que so INTERPOLA a variavel e devolveria o
    template); fora disso o censo RECUSA por nome
    (``hint_assignment_outside_case`` / ``hint_matched_heredoc``). Ela
    nao le VALOR nenhum — o valor vem da EXECUCAO do braco. O matcher
    ancorado as ATRIBUICOES ``MODEL_HINT=``
    (``_ADVISORY_ASSIGN_LINE_RE``) NAO participa deste caminho: e
    ADVISORY, existe so para os testes deste pack descreverem a
    ancoragem, e nenhuma decisao do censo depende dele.

CONFINAMENTO DA EXECUCAO (o que torna aceitavel executar o braco). O
interpretador e ``/bin/bash --noprofile --norc -c`` pelo caminho
ABSOLUTO; o ambiente do filho e ZERADO exceto ``DETECTED_SKILL`` e um
``PATH`` **vazio**; a cwd e um diretorio temporario descartavel; ha
``timeout`` de 20 s. Este e um INSTRUMENTO DE MEDICAO, nao um gate, e o
que ele executa e o script RASTREADO do proprio repo. Como defesa em
profundidade, um corpo de braco que contenha ``$(``, crase, ``>``,
``<``, ``&`` ou ``|&`` e RECUSADO POR NOME
(``hint_arm_body_outside_confinement``) e nunca executado — essa lista e
enumeravel e portanto uma CORTESIA: a defesa real e o ``PATH`` vazio, o
env zerado, a cwd descartavel e o timeout.

UNIDADE. As quatro superficies nao falam a mesma unidade: ``MODEL_HINT``
e ``routing-matrix.yaml`` carregam ALIAS DE TIER (``opus``/``sonnet``);
``VETO_HARDCODE`` e os pins de ``agents/*.md`` carregam ``model_id``. Um
valor em alias so entra na tabela pelo passo de resolucao DECLARADO
abaixo (RS-1); a ausencia do passo, ou um alias vazando para a coluna
resolvida, e VERMELHO — nunca um mapa inventado.

RS-1 (passo de resolucao alias -> model_id, DECLARADO). Fonte: ADR-149
(`.claude/adr/ADR-149-model-id-allowlist.md`), bloco machine-parseable
``AVAILABLE_MODELS_WORKING_SET``, lido pelo parser que o PROPRIO repo ja
declara para ele — ``generate-available-models.parse_working_set`` — e
nao por regex nova. O tier de cada membro vem de ``_infer_tier``,
IMPORTADO de ``.claude/scripts/build-canonical-models.py`` (o derivador
de tier declarado do repo). RS-1(alias) = { m in working_set :
_infer_tier(m) == alias }, ORDENADO. Conjunto VAZIO e VERMELHO
(``alias_unresolved``). O repo NAO declara em lugar nenhum um pin unico
alias -> um model_id; por isso RS-1 devolve o CONJUNTO declarado e o
censo o publica como conjunto. Reduzi-lo a um singleton seria exatamente
o mapa inventado que a Tese proibe.

FRONTEIRA (AC-F2). ``SUPPORT.md`` — e toda prosa normativa — esta FORA
do escopo deste censo: nenhuma das quatro superficies e prosa, nenhum
modulo e dono de ``SUPPORT.md``, e o censo nunca o le. A mutacao do
refutador (remover ``[1m]`` de ``SUPPORT.md:88``) portanto nao move
nenhum byte da tabela e nao muda o rc — e isso e a DECLARACAO, medida
pelo teste ``test_census_runtime.py``, nao uma suposicao.

SEM JUNCAO ENTRE SUPERFICIES. O censo emite quatro linhas de SUPERFICIE
e nao junta papeis entre elas. O keyspace do ``MODEL_HINT`` e SKILL
detectada (um ``case`` sobre ``$DETECTED_SKILL``), nao slug de arquetipo;
sem um passo skill->papel DECLARADO, essa juncao nao acontece.

Stdlib-only (PyYAML e OPCIONAL, com fallback declarado). Python >= 3.9
per ADR-002: sem PEP 604 em runtime, sem ``match``.

Exit codes:
  0 — as quatro linhas passam.
  1 — pelo menos um VERMELHO nomeado (a razao vai para stderr).
  2 — erro de uso.
"""
from __future__ import annotations

import argparse
import ast
import importlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# Declaracoes fechadas — nada aqui e derivado de prosa.
# --------------------------------------------------------------------------

#: Rotulo unico que a nota S340 do AC-12 aplica as quatro superficies.
LOCAL_OWNER_LABEL = "dona local"

SURFACE_VETO = "VETO_HARDCODE"
SURFACE_MATRIX = "routing-matrix.yaml"
SURFACE_AGENTS = "agents/*.md"
SURFACE_HINT = "MODEL_HINT"

#: As QUATRO superficies, na ordem em que a nota S340 as nomeia.
EXPECTED_SURFACES = (
    SURFACE_AGENTS,
    SURFACE_HINT,
    SURFACE_MATRIX,
    SURFACE_VETO,
)

OWNER_IMPORTABLE = "python-importavel"
OWNER_DATA = "dado"
OWNER_SHELL = "script-shell"

UNIT_MODEL_ID = "model_id"
UNIT_ALIAS = "alias-de-tier"

#: Coluna «cobertura» — o que a LINHA publicada afirma. Uma superficie
#: cujo dono RESPONDE (import/parser/API) publica a resposta do dono; a
#: superficie ``MODEL_HINT`` nao tem dono a quem perguntar, entao a linha
#: e uma OBSERVACAO sobre as sondas executadas — nao-exaustiva por
#: construcao (docstring de modulo, itens (v) e (vi); pair-rail r6).
COVERAGE_OWNER_ANSWER = "resposta do dono"
COVERAGE_NONEXHAUSTIVE = (
    "OBSERVACAO NAO-EXAUSTIVA (sondas derivadas da gramatica do case; "
    "bracos na MESMA linha e alcancabilidade do bloco FORA — r6)"
)

_REL_CONSTANTS = os.path.join(".claude", "scripts", "tier_policy_cli", "_constants.py")
_REL_SCRIPTS = os.path.join(".claude", "scripts")
_REL_FRONTMATTER = os.path.join(".claude", "hooks", "_lib", "frontmatter.py")
_REL_AGENT_FM = os.path.join(".claude", "hooks", "_lib", "agent_frontmatter.py")
_REL_MATRIX_LOADER = os.path.join(".claude", "dispatcher", "routing-matrix-loader.py")
_REL_MATRIX = os.path.join(".claude", "dispatcher", "routing-matrix.yaml")
_REL_AGENTS = os.path.join(".claude", "agents")
_REL_INJECT = os.path.join(".claude", "scripts", "inject-agent-context.sh")
_REL_ADR149 = os.path.join(".claude", "adr", "ADR-149-model-id-allowlist.md")
_REL_GEN_AVAIL = os.path.join(".claude", "scripts", "generate-available-models.py")
_REL_BUILD_MODELS = os.path.join(".claude", "scripts", "build-canonical-models.py")
_REL_GEN_DISPATCH = os.path.join(".claude", "scripts", "generate-dispatch.py")


class Red(Exception):
    """Um VERMELHO nomeado. ``name`` e o nome mecanico; ``detail`` a razao."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__("{0}: {1}".format(name, detail))
        self.name = name
        self.detail = detail


# --------------------------------------------------------------------------
# Utilitarios de import por caminho (arquivos com hifen no nome).
# --------------------------------------------------------------------------


_MODULE_CACHE = {}  # type: Dict[str, Any]


def _load_module_from_path(path: str, mod_name: str, red_name: str) -> Any:
    cached = _MODULE_CACHE.get(path)
    if cached is not None:
        return cached
    if not os.path.isfile(path):
        raise Red(red_name, "arquivo ausente: {0}".format(path))
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise Red(red_name, "spec nao construida para {0}".format(path))
    module = importlib.util.module_from_spec(spec)
    # O modulo tem de estar em ``sys.modules`` ANTES de executar: donos que
    # usam ``@dataclass`` resolvem seus globais por ``sys.modules[__module__]``
    # e explodem com ``AttributeError`` se o nome nao estiver registrado.
    previous = sys.modules.get(mod_name)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 — a razao vira o VERMELHO
        if previous is None:
            sys.modules.pop(mod_name, None)
        else:
            sys.modules[mod_name] = previous
        raise Red(red_name, "import falhou: {0}: {1}".format(type(exc).__name__, exc))
    _MODULE_CACHE[path] = module
    return module


# --------------------------------------------------------------------------
# RS-1 — resolucao alias -> model_id, DECLARADA.
# --------------------------------------------------------------------------


def working_set(root: str) -> List[str]:
    """Conjunto fechado de model_ids, do ADR-149, pelo parser do repo."""
    gen = _load_module_from_path(
        os.path.join(root, _REL_GEN_AVAIL), "_census_gen_avail", "rs1_parser_unavailable"
    )
    parse = getattr(gen, "parse_working_set", None)
    if parse is None:
        raise Red("rs1_parser_unavailable", "generate-available-models.parse_working_set ausente")
    adr = Path(os.path.join(root, _REL_ADR149))
    if not adr.is_file():
        raise Red("rs1_source_missing", "ADR-149 ausente: {0}".format(adr))
    try:
        ids, _digest = parse(adr)
    except Exception as exc:  # noqa: BLE001
        raise Red("rs1_source_unparseable", "{0}: {1}".format(type(exc).__name__, exc))
    ids = [str(i) for i in (ids or [])]
    if not ids:
        raise Red("rs1_source_empty", "AVAILABLE_MODELS_WORKING_SET vazio no ADR-149")
    return ids


def tier_of(root: str, model_id: str) -> str:
    """Tier declarado de um model_id — ``_infer_tier`` do proprio repo."""
    mod = _load_module_from_path(
        os.path.join(root, _REL_BUILD_MODELS), "_census_build_models", "rs1_tier_unavailable"
    )
    infer = getattr(mod, "_infer_tier", None)
    if infer is None:
        raise Red("rs1_tier_unavailable", "build-canonical-models._infer_tier ausente")
    return str(infer(model_id))


def resolve_alias(root: str, alias: str) -> List[str]:
    """RS-1: alias -> CONJUNTO ordenado de model_ids declarados."""
    ids = working_set(root)
    hits = sorted(m for m in ids if tier_of(root, m) == alias)
    if not hits:
        raise Red(
            "alias_unresolved",
            "alias {0!r} nao resolve a nenhum model_id do "
            "AVAILABLE_MODELS_WORKING_SET (ADR-149)".format(alias),
        )
    return hits


def resolve_alias_values(root: str, values: List[str]) -> Tuple[List[str], str]:
    """Aplica RS-1 a cada alias distinto; devolve (model_ids, rotulo do passo)."""
    aliases = sorted(set(values))
    out = []  # type: List[str]
    shape = []  # type: List[str]
    for alias in aliases:
        hits = resolve_alias(root, alias)
        out.extend(hits)
        shape.append("{0}->n={1}".format(alias, len(hits)))
    step = "RS-1 ADR-149 AVAILABLE_MODELS_WORKING_SET x _infer_tier ({0})".format(
        "; ".join(shape)
    )
    return sorted(set(out)), step


# --------------------------------------------------------------------------
# Leitores por superficie.
# --------------------------------------------------------------------------


#: O UM comando que o AC-F1 Check (a) prescreve, rodado de ``.claude/scripts/``.
VETO_ONE_COMMAND = (
    "import tier_policy_cli._constants as c; print(sorted(c.VETO_HARDCODE.items()))"
)


def _coerce_veto(mapping: Any) -> Dict[str, str]:
    if not isinstance(mapping, dict):
        raise Red("veto_not_a_mapping", "VETO_HARDCODE nao e um dict: {0!r}".format(type(mapping)))
    if not mapping:
        raise Red("veto_map_empty", "VETO_HARDCODE veio vazio")
    return {str(k): str(v) for k, v in mapping.items()}


def read_veto_hardcode(root: str) -> Dict[str, str]:
    """Dono IMPORTAVEL: importa o modulo NO CONTEXTO REAL DO PACOTE.

    O modulo e ``tier_policy_cli._constants``; importa-lo como um arquivo
    solto quebraria qualquer import RELATIVO do proprio pacote (rail r1,
    P2 "Import the constants owner in its real package context"). Aqui o
    diretorio ``.claude/scripts`` entra em ``sys.path[0]`` so durante o
    import, o pacote e purgado de ``sys.modules`` antes e depois, e o
    ``sys.path`` do processo hospedeiro e restaurado — isolamento na
    disciplina que o PLAN-182 pagou.
    """
    scripts_dir = os.path.join(root, _REL_SCRIPTS)
    if not os.path.isfile(os.path.join(root, _REL_CONSTANTS)):
        raise Red("veto_import_failed", "arquivo ausente: {0}".format(_REL_CONSTANTS))
    saved_path = list(sys.path)
    saved_mods = {
        k: v for k, v in sys.modules.items() if k == "tier_policy_cli" or k.startswith("tier_policy_cli.")
    }
    for k in list(saved_mods):
        del sys.modules[k]
    sys.path.insert(0, scripts_dir)
    try:
        mod = importlib.import_module("tier_policy_cli._constants")
        mapping = getattr(mod, "VETO_HARDCODE", None)
    except Exception as exc:  # noqa: BLE001 — a razao vira o VERMELHO
        raise Red("veto_import_failed", "{0}: {1}".format(type(exc).__name__, exc))
    finally:
        for k in list(sys.modules):
            if k == "tier_policy_cli" or k.startswith("tier_policy_cli."):
                del sys.modules[k]
        sys.modules.update(saved_mods)
        sys.path[:] = saved_path
    return _coerce_veto(mapping)


def read_veto_hardcode_one_command(root: str) -> Dict[str, str]:
    """A SEGUNDA leitura: o UM comando do AC, num processo separado."""
    scripts_dir = os.path.join(root, _REL_SCRIPTS)
    if not os.path.isdir(scripts_dir):
        raise Red("veto_import_failed", "diretorio ausente: {0}".format(_REL_SCRIPTS))
    proc = subprocess.run(
        [sys.executable, "-c", VETO_ONE_COMMAND],
        cwd=scripts_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise Red(
            "veto_import_failed",
            "o UM comando do AC saiu rc={0}: {1}".format(
                proc.returncode, (proc.stderr or "").strip().split("\n")[-1]
            ),
        )
    try:
        pairs = ast.literal_eval(proc.stdout.strip())
    except Exception as exc:  # noqa: BLE001
        raise Red("veto_import_failed", "saida nao literal: {0}".format(exc))
    return _coerce_veto(dict(pairs))


def _archetype_models(data: Any) -> Dict[str, str]:
    if not isinstance(data, dict):
        raise Red("matrix_unparseable", "raiz do YAML nao e um mapa")
    archetypes = data.get("archetypes")
    if not isinstance(archetypes, dict) or not archetypes:
        raise Red("matrix_key_missing", "chave 'archetypes' ausente ou vazia")
    out = {}  # type: Dict[str, str]
    for name, entry in archetypes.items():
        if not isinstance(entry, dict) or "coder_model" not in entry:
            raise Red(
                "matrix_key_missing",
                "arquetipo {0!r} sem chave 'coder_model'".format(name),
            )
        out[str(name)] = str(entry["coder_model"])
    return out


def _load_matrix_owner(root: str, path: str) -> Dict[str, str]:
    """API PUBLICA do dono: ``load_routing_matrix`` — que VALIDA a matriz.

    Chamar so o ``_parse_yaml`` interno pulava a validacao de esquema do
    dono: uma matriz que o runtime REJEITA (e que faz o
    ``inject-agent-context.sh`` cair no fallback ``matrix_load_error``)
    saia daqui como tabela verde (rail r3, P2). A rejeicao do dono agora e
    VERMELHO nomeado, com a razao dele citada.
    """
    loader = _load_module_from_path(
        os.path.join(root, _REL_MATRIX_LOADER), "_census_matrix_loader", "matrix_no_yaml_loader"
    )
    fn = getattr(loader, "load_routing_matrix", None)
    if fn is None:
        raise Red(
            "matrix_no_yaml_loader",
            "routing-matrix-loader.load_routing_matrix ausente — recusado por nome",
        )
    err = getattr(loader, "RoutingMatrixError", None)
    try:
        matrix = fn(Path(path))
    except Exception as exc:  # noqa: BLE001
        name = (
            "matrix_rejected_by_owner_loader"
            if err is not None and isinstance(exc, err)
            else "matrix_unparseable"
        )
        raise Red(name, "load_routing_matrix: {0}: {1}".format(type(exc).__name__, exc))
    routes = getattr(matrix, "archetypes", None)
    if not isinstance(routes, dict) or not routes:
        raise Red("matrix_key_missing", "chave 'archetypes' ausente ou vazia")
    out = {}  # type: Dict[str, str]
    for name, route in routes.items():
        model = getattr(route, "coder_model", None)
        if model is None:
            raise Red(
                "matrix_key_missing",
                "arquetipo {0!r} sem chave 'coder_model'".format(name),
            )
        out[str(name)] = str(model)
    return out


def _load_matrix_pyyaml(text: str) -> Optional[Dict[str, str]]:
    """Cross-check OPCIONAL com ``yaml.safe_load`` (None quando ausente)."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    try:
        return _archetype_models(yaml.safe_load(text))
    except Red:
        raise
    except Exception as exc:  # noqa: BLE001
        raise Red("matrix_unparseable", "yaml.safe_load: {0}".format(exc))


def read_routing_matrix(root: str) -> Dict[str, str]:
    """Dono DADO: o parser do DONO manda; ``yaml.safe_load`` so confere.

    O consumidor em runtime e ``routing-matrix-loader.py`` (stdlib), pela
    sua API PUBLICA ``load_routing_matrix`` — que VALIDA o esquema —, entao
    e ELE quem define a semantica. ``yaml.safe_load`` roda como CROSS-CHECK
    quando PyYAML existe: divergencia entre os dois e VERMELHO
    (``matrix_parser_disagreement``) — nunca um censo que muda de resposta
    conforme o ambiente (rail r1, P2 sobre o parser do dispatcher).
    """
    path = os.path.join(root, _REL_MATRIX)
    if not os.path.isfile(path):
        raise Red("matrix_file_missing", "arquivo ausente: {0}".format(path))
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    owner = _load_matrix_owner(root, path)
    other = _load_matrix_pyyaml(text)
    if other is not None and other != owner:
        diff = sorted(k for k in set(owner) | set(other) if owner.get(k) != other.get(k))
        raise Red(
            "matrix_parser_disagreement",
            "parser do dono e yaml.safe_load discordam em {0!r}: dono={1!r} pyyaml={2!r}".format(
                diff, [owner.get(k) for k in diff], [other.get(k) for k in diff]
            ),
        )
    return owner


def parse_agent_file(root: str, path: str) -> Dict[str, str]:
    """CARREGADOR do proprio dono: ``_lib.agent_frontmatter.parse_agent_file``.

    Nao basta reusar o PARSER de texto do dono — o dono tambem tem um
    comportamento de CARGA: ``parse_agent_file`` RECUSA um arquivo (ou um
    diretorio pai) que seja SYMLINK, e ``check_veto_floor_for_role``
    consequentemente recusa o papel. Ler o texto direto seguia o link e
    publicava como pin utilizavel um arquivo que o runtime REJEITA (rail
    r3, P2). Aqui o censo chama o carregador do dono e trata o marcador
    ``__symlink_rejected__`` como VERMELHO nomeado.

    O parser de escalares continua sendo o do repo (o carregador delega a
    ``_lib.frontmatter.parse_frontmatter``), o que preserva a cura do rail
    r1 (P2): ``model: "claude-fable-5"`` decodifica sem as aspas.
    """
    mod = _load_module_from_path(
        os.path.join(root, _REL_AGENT_FM), "_census_agent_fm", "agents_parser_unavailable"
    )
    fn = getattr(mod, "parse_agent_file", None)
    if fn is None:
        raise Red(
            "agents_parser_unavailable",
            "_lib.agent_frontmatter.parse_agent_file ausente",
        )
    try:
        meta = fn(Path(path))
    except Exception as exc:  # noqa: BLE001
        raise Red(
            "agents_loader_failed", "{0}: {1}: {2}".format(path, type(exc).__name__, exc)
        )
    meta = {str(k): str(v) for k, v in (meta or {}).items()}
    rejected = meta.get("__symlink_rejected__")
    if rejected:
        raise Red(
            "agents_symlink_rejected",
            "{0}: o carregador do dono RECUSA o arquivo ({1} e symlink) — "
            "o runtime nao publica esse papel".format(os.path.basename(path), rejected),
        )
    return meta


#: Valores publicados quando um arquivo de ``agents/`` nao carrega um pin
#: ``model:``. NENHUM deles e um model_id: a linha os exibe para que a
#: AUSENCIA fique VISIVEL (rail r2, regra de visibilidade do F8), e nenhum
#: entra na coluna resolvida.
AGENT_UNPINNED = "<sem-pin>"
#: O arquivo que o GERADOR do repo declara como sua saida — nao e um agente:
#: e a tabela de despacho DERIVADA dos outros arquivos. Aparece nomeado,
#: nunca omitido em silencio.
AGENT_GENERATED_DISPATCH = "<sem-pin: tabela de despacho gerada>"
#: Qualquer outro ``*.md`` sem bloco de frontmatter.
AGENT_NO_FRONTMATTER = "<sem-pin: sem frontmatter>"

#: Valores que NUNCA entram na coluna de model_id resolvido.
NON_PIN_VALUES = (AGENT_UNPINNED, AGENT_GENERATED_DISPATCH, AGENT_NO_FRONTMATTER)


def generated_dispatch_basename(root: str) -> str:
    """Basename da saida do gerador, PERGUNTADO ao proprio gerador.

    ``generate-dispatch.py`` declara ``DISPATCH_PATH`` no topo do modulo; o
    censo le o BASENAME dessa declaracao (o dirname do gerador resolve
    contra ``CLAUDE_PROJECT_DIR``/cwd no import e nao serve como verdade
    para uma raiz arbitraria). Assim o nome do arquivo gerado vem do
    RUNTIME que o gera, nunca de um literal lembrado aqui.
    """
    mod = _load_module_from_path(
        os.path.join(root, _REL_GEN_DISPATCH),
        "_census_gen_dispatch",
        "agents_dispatch_generator_unavailable",
    )
    declared = getattr(mod, "DISPATCH_PATH", None)
    if declared is None:
        raise Red(
            "agents_dispatch_generator_unavailable",
            "generate-dispatch.DISPATCH_PATH ausente",
        )
    return os.path.basename(str(declared))


def read_agent_pins(root: str) -> Dict[str, str]:
    """Dono DADO: um arquivo por papel; a CHAVE e o SLUG DO ARQUIVO.

    O runtime (``_lib.agent_frontmatter.resolve_agent_file``) resolve papel
    por NOME DE ARQUIVO. Chavear pelo ``name:`` do frontmatter deixava um
    rename (``code-reviewer.md`` -> ``renamed-reviewer.md``) invisivel ao
    censo — defeito real do rail r2 (P1). Aqui o slug do arquivo e a chave, e
    um ``name:`` que discorde do slug e VERMELHO nomeado.

    Um arquivo com frontmatter mas SEM ``model:`` nao e descartado em
    silencio: entra na linha como ``<sem-pin>`` (rail r2, P2). Um bloco de
    frontmatter ABERTO e nao fechado e VERMELHO. E um ``*.md`` SEM
    frontmatter tambem aparece: a saida DECLARADA pelo gerador do repo
    (``_dispatch.md``) como ``<sem-pin: tabela de despacho gerada>``,
    qualquer outro como ``<sem-pin: sem frontmatter>`` — nada some em
    silencio desta superficie.
    """
    adir = os.path.join(root, _REL_AGENTS)
    if not os.path.isdir(adir):
        raise Red("agents_dir_missing", "diretorio ausente: {0}".format(adir))
    dispatch_name = generated_dispatch_basename(root)
    out = {}  # type: Dict[str, str]
    pinned = 0
    for fname in sorted(os.listdir(adir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(adir, fname)
        fm = parse_agent_file(root, fpath)
        with open(fpath, "r", encoding="utf-8") as fh:
            text = fh.read()
        opens = text.split("\n")[:1] == ["---"]
        if opens and not fm:
            raise Red(
                "agents_frontmatter_unclosed",
                "{0}: bloco de frontmatter aberto e nao fechado/vazio".format(fname),
            )
        slug = fname[: -len(".md")]
        if not fm:
            out[slug] = (
                AGENT_GENERATED_DISPATCH
                if fname == dispatch_name
                else AGENT_NO_FRONTMATTER
            )
            continue
        declared = fm.get("name")
        if declared is not None and declared != slug:
            raise Red(
                "agents_name_slug_conflict",
                "{0}: frontmatter name={1!r} diverge do slug de arquivo {2!r} "
                "(o runtime resolve por NOME DE ARQUIVO)".format(fname, declared, slug),
            )
        model = fm.get("model")
        if model is None:
            out[slug] = AGENT_UNPINNED
        else:
            out[slug] = str(model)
            pinned += 1
    if pinned == 0:
        raise Red(
            "agents_no_frontmatter_model",
            "nenhum {0}/*.md com frontmatter contendo 'model:'".format(_REL_AGENTS),
        )
    return out


#: MATCHER ADVISORY — o censo NAO o consulta. Casa a forma
#: ``MODEL_HINT=`` no inicio da linha (com ``export``/``local``/
#: ``readonly``/``typeset`` opcionais) e e explicitamente
#: NAO-EXAUSTIVO: um braco compacto (``padrao) MODEL_HINT=... ;;``) ou
#: uma atribuicao no meio da linha nao casam com ele — a
#: nao-exaustividade e MEDIDA por teste, nao afirmada. A guarda de
#: cobertura que o censo executa e a varredura por SUBSTRING dentro de
#: ``read_model_hint``; este objeto existe apenas como fixture dos
#: testes deste pack, que o usam para descrever a ancoragem as
#: atribuicoes. Ele tambem nao le VALOR (o valor vem da EXECUCAO).
_ADVISORY_ASSIGN_LINE_RE = re.compile(
    r"^[ \t]*(?:export[ \t]+|local[ \t]+|readonly[ \t]+|typeset[ \t]+)?"
    r"MODEL_HINT=(.*)$",
    re.M,
)

#: Forma de token aceita para um alias produzido pelo braco.
MODEL_HINT_TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]+$")

#: Braco de ``case``: a linha do PADRAO terminada em ``)`` — na forma
#: MULTI-LINHA (corpo nas linhas seguintes) ou na forma COMPACTA de uma
#: linha so (``padrao) corpo ;;``), que o pair-rail r4 (P1 i) mediu OMITIDA
#: em silencio. Este regex NAO pretende modelar toda gramatica de braco —
#: quem fecha a classe e o censo de COBERTURA fail-CLOSED logo abaixo.
_CASE_ARM_RE = re.compile(
    r"^[ \t]*([^\s#()\n][^()\n]*)\)"
    r"[ \t]*(?:$|[^\n]*;;[ \t]*(?:#[^\n]*)?$)",
    re.M,
)

#: Terminador de braco: ``;;`` no fim da linha, opcionalmente seguido de
#: comentario. Delimita o CORPO de um braco RECONHECIDO — nao e mais um
#: contador. Contar terminadores nao fechava a classe: uma forma que os
#: DOIS regexes perdem (``padrao) corpo ;; # nota``) mantinha as duas
#: contagens iguais e a rota sumia em silencio (pair-rail r5, P1). Quem
#: fecha e a PARTICAO em ``_assert_arm_partition``.
_ARM_TERMINATOR_RE = re.compile(r";;[ \t]*(?:#[^\n]*)?$", re.M)

#: Linha que pode legitimamente existir no span FORA de um braco.
_BLANK_OR_COMMENT_RE = re.compile(r"^[ \t]*(?:#.*)?$")

#: O braco ``*`` recebe UMA sonda sintetica: isso e uma OBSERVACAO sobre
#: aquela entrada, nunca o vinculo de todo o keyspace que ``*`` casa (r4
#: P1 iii). A linha publicada carrega essa limitacao no proprio rotulo.
_WILDCARD_NOTE = "[sonda sintetica; nao generaliza]"

_CASE_OPEN_RE = re.compile(r'^[ \t]*case[ \t]+"\$DETECTED_SKILL"[ \t]+in[ \t]*$', re.M)
_CASE_CLOSE_RE = re.compile(r"^[ \t]*esac[ \t]*$", re.M)

_HEREDOC_OPEN_RE = re.compile(r"^[ \t]*cat[ \t]+<<-?[ \t]*'?MODEL_HINT_HEADER'?[ \t]*$", re.M)
_HEREDOC_CLOSE_RE = re.compile(r"^[ \t]*MODEL_HINT_HEADER[ \t]*$", re.M)

#: Interpretador usado no confinamento (o PATH do filho e VAZIO por desenho).
_BASH = "/bin/bash"

#: Construcoes que este censo RECUSA executar (confinamento; ver DESIGN).
_UNSAFE_IN_ARM = ("$(", "`", ">", "<", "&", "|&")

#: A linha de opcoes de shell do PROPRIO dono (``set -euo pipefail`` no
#: ``inject-agent-context.sh``). Derivada do arquivo, nunca lembrada aqui:
#: sem ela um comando que FALHA no script real (que aborta) continuaria
#: produzindo vinculo na sonda (pair-rail r3, P2).
_SET_LINE_RE = re.compile(
    r"^[ \t]*(set[ \t]+[-+][A-Za-z]+(?:[ \t]+[-+]?[A-Za-z]+)*)[ \t]*(?:#[^\n]*)?$",
    re.M,
)

#: Qualquer linha que COMECE uma declaracao ``set -…``. Se existe uma e o
#: regex estrito acima nao a interpreta, o censo RECUSA — antes (r4 P2 iv)
#: um comentario inline colapsava as opcoes para vazio e a sonda passava a
#: rodar SEM o ``set -e`` do dono: fail-OPEN na direcao que o registro
#: chamava de derivada.
_SET_LOOSE_RE = re.compile(r"^[ \t]*set[ \t]+[-+][^\n]*$", re.M)


def _heredoc_spans(text: str) -> List[Tuple[int, int]]:
    spans = []  # type: List[Tuple[int, int]]
    for opener in _HEREDOC_OPEN_RE.finditer(text):
        closer = _HEREDOC_CLOSE_RE.search(text, opener.end())
        end = closer.start() if closer else len(text)
        spans.append((opener.start(), end))
    return spans


def _in_spans(pos: int, spans: List[Tuple[int, int]]) -> bool:
    for lo, hi in spans:
        if lo <= pos < hi:
            return True
    return False


def _owner_shell_options(text: str, limit: Optional[int] = None) -> str:
    """TODAS as declaracoes ``set -…``/``set +…`` que precedem o bloco.

    Nao e a PRIMEIRA: o dono pode declarar em mais de um comando, e o que
    vale no ponto do ``case`` e a COMPOSICAO delas na ordem em que
    aparecem (pair-rail r5, P2 — replicar so a primeira deixava um braco
    que ABORTA no script real produzindo vinculo verde na sonda). ``limit``
    e o offset onde o bloco comeca: nada declarado DEPOIS dele entra, pois
    o proprio bloco ja viaja verbatim.

    Devolve string vazia SO quando nao ha nenhuma declaracao. Uma que
    EXISTE mas o parser nao interpreta e VERMELHO
    (``hint_shell_options_uninterpretable``) — nunca opcoes vazias, que
    fariam a sonda rodar num shell mais permissivo que o do dono.
    Comentario inline e removido; o que sobra e verbatim, uma por linha.
    """
    end = len(text) if limit is None else limit
    lines = []  # type: List[str]
    for loose in _SET_LOOSE_RE.finditer(text, 0, end):
        strict = _SET_LINE_RE.match(text, loose.start())
        if strict is None:
            raise Red(
                "hint_shell_options_uninterpretable",
                "o dono declara {0!r} e este censo nao interpreta essa "
                "forma; recusado — rodar a sonda sem as opcoes do dono "
                "seria fail-OPEN".format(loose.group(0).strip()[:80]),
            )
        lines.append(strict.group(1).strip())
    return "\n".join(lines)


def _case_block(text: str) -> Tuple[int, int]:
    """Span do bloco INTEIRO — do ``case`` ao ``esac``, inclusive."""
    opener = _CASE_OPEN_RE.search(text)
    if opener is None:
        raise Red(
            "hint_case_block_missing",
            'bloco case "$DETECTED_SKILL" in ... esac nao encontrado',
        )
    closer = _CASE_CLOSE_RE.search(text, opener.end())
    if closer is None:
        raise Red("hint_case_block_missing", "esac ausente apos o case de $DETECTED_SKILL")
    return opener.start(), closer.end()


def _case_span(text: str) -> Tuple[int, int]:
    opener = _CASE_OPEN_RE.search(text)
    if opener is None:
        raise Red(
            "hint_case_block_missing",
            'bloco case "$DETECTED_SKILL" in ... esac nao encontrado',
        )
    closer = _CASE_CLOSE_RE.search(text, opener.end())
    if closer is None:
        raise Red("hint_case_block_missing", "esac ausente apos o case de $DETECTED_SKILL")
    return opener.end(), closer.start()


def _run_case(block: str, options: str, probe: str) -> str:
    """EXECUTA o bloco ``case`` do DONO, verbatim, e devolve o vinculo.

    O bloco vai INTEIRO — nao um ``case`` de um braco so montado por este
    censo: so assim a semantica de PRIMEIRO BRACO QUE CASA e a do runtime
    (pair-rail r3, P1). As opcoes de shell sao as que o DONO declara, entao
    um comando que aborta o script real tambem aborta a sonda (r3, P2).

    O valor sai por um canal EMOLDURADO por um NONCE gerado agora: a saida
    comum do bloco nao consegue se passar pelo valor final (r3, P2).

    Confinamento (aceito pelo CEO na nota r2 — instrumento de medicao, e o
    que executa e o script RASTREADO do repo): ``bash --noprofile --norc``
    pelo caminho ABSOLUTO, ambiente ZERADO exceto ``DETECTED_SKILL`` e um
    ``PATH`` VAZIO, cwd num diretorio temporario descartavel, timeout.
    """
    import tempfile

    nonce = os.urandom(8).hex()
    open_tag = "__CENSUS_" + nonce + "__"
    close_tag = "__/CENSUS_" + nonce + "__"
    tail = (
        "\nprintf '%s' '" + open_tag + "'"
        "\nprintf '%s' \"${MODEL_HINT-}\""
        "\nprintf '%s\\n' '" + close_tag + "'\n"
    )
    script = ((options + "\n") if options else "") + block + tail

    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run(
                [_BASH, "--noprofile", "--norc", "-c", script],
                cwd=tmp,
                env={"DETECTED_SKILL": probe, "PATH": ""},
                capture_output=True,
                text=True,
                check=False,
                timeout=20,
            )
        except Exception as exc:  # noqa: BLE001
            raise Red("hint_probe_execution_failed", "{0!r}: {1}".format(probe, exc))
    found = re.search(
        re.escape(open_tag) + "(.*?)" + re.escape(close_tag), proc.stdout, re.S
    )
    if found is None:
        raise Red(
            "hint_probe_no_binding",
            "sonda {0!r}: o bloco do dono terminou sem publicar vinculo "
            "(rc={1}; stderr={2!r}) — sob as opcoes do dono isso e um "
            "script que ABORTA antes do hint".format(
                probe, proc.returncode, (proc.stderr or "").strip()[:120]
            ),
        )
    return found.group(1)


#: A UNICA forma de alternativa de que este censo deriva uma sonda: um
#: literal de shell que o bash entrega ao ``case`` sem transformar. A regra
#: e um WHITELIST — enumerar o que ENTRA, nunca o que fica de fora — porque
#: o espaco das formas que o shell transforma (glob ``*?[]``, aspas,
#: escape, expansao ``$``/``${...}``/``$(...)``, til, espaco) NAO e
#: enumeravel: o pair-rail fechou glob (r3), aspas (r4 P1 ii) e expansao de
#: parametro (r5 P1) em rodadas sucessivas, sempre a MESMA pergunta numa
#: grafia nova. Qualquer alternativa fora desta forma e recusada por nome
#: (``hint_pattern_probe_underivable``) — o censo nunca reimplementa
#: remocao de aspas nem expansao de parametro para adivinhar a chave.
_LITERAL_ALT_RE = re.compile(r"^[A-Za-z0-9._+-]+$")


def _assert_arm_partition(
    text: str, lo: int, hi: int, arms: List[Tuple[int, int, str]]
) -> None:
    """Todo byte do span pertence a um braco RECONHECIDO, ou e branco/comentario.

    Duas CONTAGENS podem errar juntas — foi o que a r5 (P1) mediu: a forma
    ``padrao) corpo ;; # nota`` escapa ao regex de braco E ao de terminador,
    as contagens continuam iguais e a rota some em silencio. Uma PARTICAO
    nao tem esse ponto cego: para cada braco reconhecido, o corpo vai ate o
    seu terminador (limitado pelo inicio do braco seguinte), e o que sobra
    entre um corpo e o proximo braco tem de ser branco ou comentario. Uma
    linha de codigo nessas lacunas e ``hint_arm_coverage_incomplete``: o
    censo se RECUSA a responder em vez de omitir uma rota.
    """
    gaps = []  # type: List[Tuple[int, int]]
    cursor = lo
    for idx, (start, _end, _pattern) in enumerate(arms):
        gaps.append((cursor, start))
        bound = arms[idx + 1][0] if idx + 1 < len(arms) else hi
        term = _ARM_TERMINATOR_RE.search(text, start, bound)
        cursor = term.end() if term is not None else bound
    gaps.append((cursor, hi))

    for gap_lo, gap_hi in gaps:
        if gap_hi <= gap_lo:
            continue
        offset = gap_lo
        for line in text[gap_lo:gap_hi].split("\n"):
            if _BLANK_OR_COMMENT_RE.match(line) is None:
                raise Red(
                    "hint_arm_coverage_incomplete",
                    "linha {0!r} (offset {1}) esta DENTRO do bloco case e "
                    "FORA de todo braco reconhecido — ha forma de braco que "
                    "este censo nao modela; recusado, nunca omitido em "
                    "silencio".format(line.strip()[:60], offset),
                )
            offset += len(line) + 1


def read_model_hint(root: str) -> List[Tuple[str, str]]:
    """Dono SCRIPT-SHELL: pares (chave sondada, alias PRODUZIDO), em ordem.

    **Pergunta ao runtime, executando o bloco do DONO.** O bloco
    ``case "$DETECTED_SKILL" in`` … ``esac`` de ``inject-agent-context.sh``
    e executado VERBATIM e INTEIRO, sob as opcoes de shell que o proprio
    arquivo declara, uma vez por SONDA — e ha uma sonda por ALTERNATIVA
    LITERAL de cada braco. O valor publicado e o ``$MODEL_HINT`` que
    aquela execucao PRODUZ, lido por um canal emoldurado com nonce.
    A COBERTURA declarada esta no docstring de modulo: fail-CLOSED nas
    quatro direcoes que a r4 do pair-rail mediu (formas de braco, aspas,
    curinga e opcoes de shell) e explicitamente NAO-EXAUSTIVA — a
    delimitacao de bracos que dividem a MESMA linha e a ALCANCABILIDADE
    do bloco (r6) ficam FORA do que esta guarda responde, e por isso a
    linha desta superficie e publicada como OBSERVACAO.

    Tres defeitos REAIS de rail fecham por AQUI, e nao por mais gramatica:

    * r2 P1 — braco morto (``if false; then MODEL_HINT=...; fi``): a
      execucao nao produz vinculo ⇒ ``hint_probe_yields_no_value``.
    * r3 P1 — um braco ANTERIOR que casa primeiro sem atribuir: como o
      bloco INTEIRO roda, o runtime escolhe o mesmo braco que escolheria
      em producao, e a sonda daquela chave deixa de render valor.
    * r3 P1 — alternativas do MESMO braco com valores diferentes: cada
      alternativa e sondada, e valores distintos sao publicados
      SEPARADAMENTE (``padrao[alternativa]``), nunca um valor observado
      numa alternativa publicado para as outras.

    Recusas por NOME desta funcao: uma linha com o literal
    ``MODEL_HINT=`` fora do bloco ``case`` ou dentro do heredoc e
    ``hint_assignment_outside_case`` / ``hint_matched_heredoc``, e o
    bloco EXECUTADO e recusado se contiver construcao fora do
    confinamento declarado. O ALCANCE dessas recusas — e o que fica
    FORA dele — esta no bloco COBERTURA DECLARADA do docstring de
    modulo, nao aqui.
    """
    path = os.path.join(root, _REL_INJECT)
    if not os.path.isfile(path):
        raise Red("hint_file_missing", "arquivo ausente: {0}".format(path))
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()

    spans = _heredoc_spans(text)
    lo, hi = _case_span(text)
    blk_lo, blk_hi = _case_block(text)
    block = text[blk_lo:blk_hi]
    options = _owner_shell_options(text, blk_lo)

    # Censo de COBERTURA por SUBSTRING (nao por gramatica): uma linha que
    # contenha o literal ``MODEL_HINT=`` tem de estar DENTRO do bloco ``case``
    # e FORA do heredoc. O VALOR nao e lido aqui — quem o le e a execucao.
    offset = 0
    seen_any = False
    for line in text.split("\n"):
        if "MODEL_HINT=" in line:
            if _in_spans(offset, spans):
                raise Red(
                    "hint_matched_heredoc",
                    "atribuicao DENTRO do heredoc MODEL_HINT_HEADER "
                    "(offset {0}) — o heredoc so interpola a variavel".format(offset),
                )
            if not (lo <= offset < hi):
                raise Red(
                    "hint_assignment_outside_case",
                    "atribuicao MODEL_HINT= fora do case de $DETECTED_SKILL "
                    "(offset {0}) — o keyspace da superficie nao e derivavel".format(offset),
                )
            seen_any = True
        offset += len(line) + 1
    if not seen_any:
        raise Red(
            "hint_no_assignment_match",
            "nenhuma atribuicao MODEL_HINT= em {0}".format(_REL_INJECT),
        )

    # O que sera EXECUTADO e o bloco INTEIRO: o confinamento e conferido
    # sobre ELE, nao so sobre os bracos que tocam a superficie.
    for bad in _UNSAFE_IN_ARM:
        if bad in block:
            raise Red(
                "hint_block_outside_confinement",
                "o bloco case do dono contem {0!r} — fora do confinamento de "
                "execucao; recusado, nunca executado".format(bad),
            )

    arms = [
        (m.start(), m.end(), m.group(1).strip())
        for m in _CASE_ARM_RE.finditer(text)
        if lo <= m.start() < hi
    ]
    if not arms:
        raise Red("hint_case_block_missing", "nenhum braco de case encontrado no span")

    # COBERTURA fail-CLOSED dos bracos (r4 P1 i; ARQUITETURA trocada na r5
    # P1): nao se CONTA nada — particiona-se o span.
    _assert_arm_partition(text, lo, hi, arms)

    out = []  # type: List[Tuple[str, str]]
    for pos, (_start, _end, pattern) in enumerate(arms):
        results = []  # type: List[Tuple[str, str]]
        for alt in [a.strip() for a in pattern.split("|") if a.strip()]:
            if alt == "*":
                probe = "__census_probe_default__"
            elif _LITERAL_ALT_RE.match(alt) is None:
                raise Red(
                    "hint_pattern_probe_underivable",
                    "alternativa {0!r} do braco {1!r} nao e um LITERAL de "
                    "shell (so [A-Za-z0-9._+-] vira sonda): glob, aspas, "
                    "escape ou expansao sao TRANSFORMADOS pelo dono antes de "
                    "casar, entao a sonda literal cairia noutro braco e o "
                    "vinculo publicado seria ERRADO; recusado".format(alt, pattern),
                )
            else:
                probe = alt
            # SEM aparo: o canal e emoldurado por nonce, entao o vinculo ja
            # chega EXATO. Aparar aqui converteria um valor que o dono
            # interpola COM espacos num alias valido (r4 P2 v) — quem recusa
            # e a validacao de token logo abaixo.
            value = _run_case(block, options, probe)
            if not value:
                raise Red(
                    "hint_probe_yields_no_value",
                    "sonda {0!r} (braco {1!r}, posicao {2}) EXECUTA o bloco do "
                    "dono e nao produz MODEL_HINT — ou o braco esta em fluxo "
                    "que nao roda, ou um braco ANTERIOR casa antes sem "
                    "atribuir".format(probe, pattern, pos),
                )
            if not MODEL_HINT_TOKEN_RE.match(value):
                raise Red(
                    "hint_probe_value_unsupported",
                    "sonda {0!r} produziu {1!r}, fora da forma de token".format(
                        probe, value[:40]
                    ),
                )
            results.append((alt, value))
        # O braco curinga publica a limitacao no proprio rotulo: uma sonda
        # sintetica e OBSERVACAO, nao vinculo de todo o keyspace (r4 P1 iii).
        display = (pattern + _WILDCARD_NOTE) if "*" in pattern else pattern
        distinct = sorted(set(v for _a, v in results))
        if len(distinct) == 1:
            out.append((display, distinct[0]))
        else:
            # Alternativas do MESMO braco divergem: cada uma vai SEPARADA,
            # nunca um valor observado numa publicado para as outras.
            for alt, value in results:
                out.append(("{0}[{1}]".format(display, alt), value))
    if not out:
        raise Red("hint_no_assignment_match", "nenhum braco produziu MODEL_HINT")
    return out


# --------------------------------------------------------------------------
# Tabela.
# --------------------------------------------------------------------------


def _render_pairs(mapping: Dict[str, str]) -> str:
    return ", ".join("{0}={1}".format(k, mapping[k]) for k in sorted(mapping))


def build_table(root: str) -> List[Dict[str, Any]]:
    """Quatro linhas — uma por superficie, na ordem de EXPECTED_SURFACES."""
    rows = []  # type: List[Dict[str, Any]]

    pins = read_agent_pins(root)
    rows.append(
        {
            "surface": SURFACE_AGENTS,
            "owner_class": OWNER_DATA,
            "label": LOCAL_OWNER_LABEL,
            "raw_unit": UNIT_MODEL_ID,
            "raw_value": _render_pairs(pins),
            "resolved_model_ids": sorted(
                v for v in set(pins.values()) if v not in NON_PIN_VALUES
            ),
            "resolution_step": "nenhum (valor ja e model_id)",
            "keyspace": "papel (SLUG DO ARQUIVO agents/<slug>.md)",
            "coverage": COVERAGE_OWNER_ANSWER,
        }
    )

    hints = read_model_hint(root)
    hint_ids, hint_step = resolve_alias_values(root, [alias for _arm, alias in hints])
    rows.append(
        {
            "surface": SURFACE_HINT,
            "owner_class": OWNER_SHELL,
            "label": LOCAL_OWNER_LABEL,
            "raw_unit": UNIT_ALIAS,
            "raw_value": "; ".join("{0}={1}".format(arm, alias) for arm, alias in hints),
            "resolved_model_ids": hint_ids,
            "resolution_step": hint_step,
            "keyspace": "skill detectada ($DETECTED_SKILL) — NAO papel",
            "coverage": COVERAGE_NONEXHAUSTIVE,
        }
    )

    matrix = read_routing_matrix(root)
    matrix_ids, matrix_step = resolve_alias_values(root, list(matrix.values()))
    rows.append(
        {
            "surface": SURFACE_MATRIX,
            "owner_class": OWNER_DATA,
            "label": LOCAL_OWNER_LABEL,
            "raw_unit": UNIT_ALIAS,
            "raw_value": _render_pairs(matrix),
            "resolved_model_ids": matrix_ids,
            "resolution_step": matrix_step,
            "keyspace": "arquetipo (chave de archetypes:)",
            "coverage": COVERAGE_OWNER_ANSWER,
        }
    )

    veto = read_veto_hardcode(root)
    rows.append(
        {
            "surface": SURFACE_VETO,
            "owner_class": OWNER_IMPORTABLE,
            "label": LOCAL_OWNER_LABEL,
            "raw_unit": UNIT_MODEL_ID,
            "raw_value": _render_pairs(veto),
            "resolved_model_ids": sorted(set(veto.values())),
            "resolution_step": "nenhum (valor ja e model_id)",
            "keyspace": "papel (slug de agents/<slug>.md)",
            "coverage": COVERAGE_OWNER_ANSWER,
            "_pairs": dict(veto),
        }
    )
    return rows


# --------------------------------------------------------------------------
# Checks.
# --------------------------------------------------------------------------


def check_a_compare(table_pairs: Dict[str, str], import_pairs: Dict[str, str]) -> None:
    """Compara PAR A PAR a linha da tabela com o import. Tres VERMELHOS."""
    if not import_pairs:
        raise Red("veto_map_empty", "o import devolveu um mapa vazio")
    for k in sorted(set(import_pairs) | set(table_pairs)):
        if k not in table_pairs:
            raise Red(
                "veto_pair_missing_in_table",
                "par {0}={1} esta no import e falta na tabela".format(k, import_pairs[k]),
            )
        if k not in import_pairs:
            raise Red(
                "veto_pair_missing_in_import",
                "par {0}={1} esta na tabela e falta no import".format(k, table_pairs[k]),
            )
        if table_pairs[k] != import_pairs[k]:
            raise Red(
                "veto_pair_diverges",
                "papel {0}: tabela={1} import={2}".format(k, table_pairs[k], import_pairs[k]),
            )


def check_a(root: str, rows: List[Dict[str, Any]]) -> None:
    """Check (a) do AC-F1 — dono IMPORTAVEL, o import e a verdade."""
    row = None
    for r in rows:
        if r["surface"] == SURFACE_VETO:
            row = r
    if row is None:
        raise Red("surface_missing", "{0} ausente da tabela".format(SURFACE_VETO))
    check_a_compare(dict(row.get("_pairs") or {}), read_veto_hardcode_one_command(root))


def check_b(root: str, rows: List[Dict[str, Any]]) -> None:
    """Check (b) do AC-F1 — donos DADO/SCRIPT, unidade e rotulo."""
    seen = [r["surface"] for r in rows]
    for name in EXPECTED_SURFACES:
        if name not in seen:
            raise Red("surface_missing", "superficie {0!r} ausente da tabela".format(name))
    for name in seen:
        if name not in EXPECTED_SURFACES:
            raise Red("surface_unexpected", "superficie {0!r} nao declarada".format(name))
    if len(seen) != len(EXPECTED_SURFACES):
        raise Red(
            "surface_count",
            "esperadas {0} linhas, obtidas {1}".format(len(EXPECTED_SURFACES), len(seen)),
        )
    allowed = set(working_set(root))
    for r in rows:
        cov = r.get("coverage")
        if cov not in (COVERAGE_OWNER_ANSWER, COVERAGE_NONEXHAUSTIVE):
            raise Red(
                "coverage_marker_missing",
                "{0} sem marca de COBERTURA declarada (obtido {1!r})".format(
                    r["surface"], cov
                ),
            )
        if (r["surface"] == SURFACE_HINT) != (cov == COVERAGE_NONEXHAUSTIVE):
            raise Red(
                "coverage_marker_missing",
                "{0}: a marca de cobertura {1!r} nao corresponde a superficie "
                "— so {2} e publicada como OBSERVACAO NAO-EXAUSTIVA".format(
                    r["surface"], cov, SURFACE_HINT
                ),
            )
        if r["label"] != LOCAL_OWNER_LABEL:
            raise Red(
                "label_wrong",
                "{0} rotulada {1!r}, esperado {2!r}".format(
                    r["surface"], r["label"], LOCAL_OWNER_LABEL
                ),
            )
        if not r["resolved_model_ids"]:
            raise Red("resolution_missing", "{0} sem coluna resolvida".format(r["surface"]))
        if r["raw_unit"] == UNIT_ALIAS and r["resolution_step"].startswith("nenhum"):
            raise Red(
                "resolution_step_absent",
                "{0} tem valor em ALIAS e nenhum passo de resolucao "
                "DECLARADO — VERMELHO, nunca um mapa inventado".format(r["surface"]),
            )
        for mid in r["resolved_model_ids"]:
            if mid not in allowed:
                raise Red(
                    "alias_leaked_into_table",
                    "{0}: {1!r} nao e model_id do AVAILABLE_MODELS_WORKING_SET "
                    "(ADR-149) — a tabela mistura alias com model_id".format(r["surface"], mid),
                )


# --------------------------------------------------------------------------
# CLI.
# --------------------------------------------------------------------------

def _md_cell(value: str) -> str:
    """Escapa a barra vertical: os padroes de ``case`` contem alternacao."""
    return str(value).replace("|", "\\|")


def render_table(rows: List[Dict[str, Any]]) -> str:
    out = ["| superficie | classe de dono | rotulo | valor cru (unidade) | model_id resolvido | passo de resolucao | cobertura |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(
            "| `{0}` | {1} | «{2}» | {3} ({4}) | {5} | {6} | {7} |".format(
                _md_cell(r["surface"]),
                _md_cell(r["owner_class"]),
                _md_cell(r["label"]),
                _md_cell(r["raw_value"]),
                _md_cell(r["raw_unit"]),
                _md_cell(", ".join(r["resolved_model_ids"])),
                _md_cell(r["resolution_step"]),
                _md_cell(r.get("coverage", "")),
            )
        )
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=None, help="raiz do repo (default: derivada deste arquivo)")
    ap.add_argument("--json", action="store_true", help="emite JSON em vez da tabela")
    args = ap.parse_args(argv)

    root = args.root
    if root is None:
        # .claude/plans/PLAN-186-FOLLOWUP-census-runtime/w0/ -> 4 dirs acima
        root = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), *([os.pardir] * 4))
        )
    root = os.path.abspath(root)

    try:
        rows = build_table(root)
        check_a(root, rows)
        check_b(root, rows)
    except Red as red:
        sys.stderr.write("RED {0}: {1}\n".format(red.name, red.detail))
        return 1

    if args.json:
        payload = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(render_table(rows) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
