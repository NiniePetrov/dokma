# app/agents/__init__.py

import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from config import ANTHROPIC_API_KEY, MODEL_NAME, TEMPERATURE, MAX_TOKENS
from app.prompts import (
    SYSTEM_INTAKE,               PROMPT_INTAKE,
    SYSTEM_QUALIDADE,            PROMPT_QUALIDADE,
    SYSTEM_COERENCIA,            PROMPT_COERENCIA,
    SYSTEM_ANALISTA_DOR,         PROMPT_DOR,
    SYSTEM_ANALISTA_COMPETITIVA, PROMPT_COMPETITIVA,
    SYSTEM_ANALISTA_VIABILIDADE, PROMPT_VIABILIDADE,
    SYSTEM_SINTESE,              PROMPT_SINTESE,
)

# ─── Modelo — Claude para todos os agentes ────────────────────
llm = ChatAnthropic(
    model=MODEL_NAME,
    api_key=ANTHROPIC_API_KEY,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
)

# ─── Estado ───────────────────────────────────────────────────
class EstadoAnalise(TypedDict):
    titulo:                     str
    documentos:                 str
    tipo:                       str
    modelo:                     str
    estagio:                    str
    arquetipo:                  str
    justificativa_marcadores:   str
    mapa_documentos:            list
    documentos_relevantes:      str
    documentos_ignorados:       list
    lacunas_criticas:           list
    lacunas_complementares:     list
    nivel_evidencia:            int
    suficiente_para_analise:    bool
    justificativa_auditoria:    str
    inconsistencias_criticas:   list
    inconsistencias_moderadas:  list
    nivel_alerta:               str
    framework_principal:        str
    framework_secundario:       str
    foco_da_analise:            str
    alertas:                    list
    analise_dor:                dict
    analise_competitiva:        dict
    analise_viabilidade:        dict
    veredito:                   str
    justificativa_principal:    str
    analise_por_dimensao:       dict
    confiabilidade:             str
    dimensoes_comprometidas:    list
    resumo_inconsistencias:     str
    encerrar_com_investigate:   bool
    erro:                       str

# ─── Utilitário ───────────────────────────────────────────────
def chamar_modelo(system: str, prompt: str) -> dict:
    try:
        mensagens = [
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ]
        resposta = llm.invoke(mensagens)
        texto = resposta.content.strip()
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        return json.loads(texto)
    except json.JSONDecodeError as e:
        return {"erro": f"JSON inválido: {str(e)}", "raw": resposta.content}
    except Exception as e:
        return {"erro": str(e)}

# ─── Agente de Intake ─────────────────────────────────────────
def agente_intake(estado: EstadoAnalise) -> dict:
    print("→ Agente de Intake: Classificando ideia e documentos...")
    resultado = chamar_modelo(
        SYSTEM_INTAKE,
        PROMPT_INTAKE.format(documentos=estado["documentos"]),
    )
    if "erro" in resultado:
        return {"erro": resultado["erro"]}

    ideia = resultado.get("ideia", {})
    docs  = resultado.get("documentos", [])

    relevantes = [d for d in docs if d.get("peso") in ("ALTO", "MEDIO")]
    ignorados  = [d.get("identificador", "") for d in docs
                  if d.get("peso") in ("BAIXO", "NULO")]

    # Extrair apenas conteúdo relevante
    if relevantes:
        ids_relevantes = [d.get("identificador", "") for d in relevantes]
        prompt_filtro = f"""
Você recebeu um conjunto de documentos concatenados abaixo.
Extraia e retorne APENAS o conteúdo dos seguintes documentos,
mantendo o texto original de cada um:

DOCUMENTOS A EXTRAIR:
{json.dumps(ids_relevantes, ensure_ascii=False)}

TEXTO COMPLETO:
{estado["documentos"]}

Retorne apenas o conteúdo extraído, sem comentários adicionais.
"""
        try:
            mensagens = [
                SystemMessage(content="Você é um extrator de texto. Extraia apenas o conteúdo solicitado sem adicionar comentários."),
                HumanMessage(content=prompt_filtro),
            ]
            resposta = llm.invoke(mensagens)
            texto_relevantes = resposta.content.strip()
        except Exception:
            texto_relevantes = estado["documentos"]
    else:
        texto_relevantes = estado["documentos"]

    return {
        "tipo":                     ideia.get("tipo", "SAAS"),
        "modelo":                   ideia.get("modelo", "B2B"),
        "estagio":                  ideia.get("estagio", "RAW_IDEA"),
        "arquetipo":                ideia.get("arquetipo", "HAIR_ON_FIRE"),
        "justificativa_marcadores": ideia.get("justificativa", ""),
        "mapa_documentos":          docs,
        "documentos_relevantes":    texto_relevantes,
        "documentos_ignorados":     ignorados,
    }

# ─── Agente de Qualidade ──────────────────────────────────────
def agente_qualidade(estado: EstadoAnalise) -> dict:
    print("→ Agente de Qualidade: Auditando lacunas e consistência...")
    mapa_texto = json.dumps(
        estado.get("mapa_documentos", []),
        ensure_ascii=False, indent=2
    )
    resultado = chamar_modelo(
        SYSTEM_QUALIDADE,
        PROMPT_QUALIDADE.format(
            tipo=estado["tipo"],
            modelo=estado["modelo"],
            estagio=estado["estagio"],
            arquetipo=estado["arquetipo"],
            mapa_documentos=mapa_texto,
            documentos_relevantes=estado.get("documentos_relevantes", ""),
        )
    )
    if "erro" in resultado:
        return {"erro": resultado["erro"]}

    criticas     = resultado.get("inconsistencias_criticas", [])
    moderadas    = resultado.get("inconsistencias_moderadas", [])
    lacunas_c    = resultado.get("lacunas_criticas", [])
    lacunas_comp = resultado.get("lacunas_complementares", [])
    nivel_ev     = resultado.get("nivel_evidencia", 1)
    suficiente   = resultado.get("suficiente_para_analise", True)

    if len(lacunas_c) >= 3 or len(criticas) >= 2 or not suficiente:
        nivel_alerta = "CRITICO"
        encerrar = True
    elif (len(lacunas_c) >= 1 or len(criticas) >= 1 or
          (len(lacunas_comp) >= 3 and nivel_ev <= 2)):
        nivel_alerta = "MODERADO"
        encerrar = False
    else:
        nivel_alerta = "INFORMATIVO"
        encerrar = False

    return {
        "lacunas_criticas":          lacunas_c,
        "lacunas_complementares":    lacunas_comp,
        "nivel_evidencia":           nivel_ev,
        "suficiente_para_analise":   suficiente,
        "justificativa_auditoria":   resultado.get("justificativa", ""),
        "inconsistencias_criticas":  criticas,
        "inconsistencias_moderadas": moderadas,
        "documentos_ignorados":      resultado.get(
            "documentos_ignorados",
            estado.get("documentos_ignorados", [])
        ),
        "nivel_alerta":              nivel_alerta,
        "encerrar_com_investigate":  encerrar,
    }

# ─── Agente de Coerência ──────────────────────────────────────
def agente_coerencia(estado: EstadoAnalise) -> dict:
    print("→ Agente de Coerência: Calibrando frameworks...")
    resultado = chamar_modelo(
        SYSTEM_COERENCIA,
        PROMPT_COERENCIA.format(
            tipo=estado["tipo"],
            modelo=estado["modelo"],
            estagio=estado["estagio"],
            arquetipo=estado["arquetipo"],
        )
    )
    if "erro" in resultado:
        return {"erro": resultado["erro"]}
    return {
        "framework_principal":  resultado.get("framework_principal", "MOM_TEST"),
        "framework_secundario": resultado.get("framework_secundario", "PAUL_GRAHAM"),
        "foco_da_analise":      resultado.get("foco_da_analise", ""),
        "alertas":              resultado.get("alertas", []),
    }

# ─── Utilitário — formatar inconsistências ────────────────────
def formatar_inconsistencias(estado: EstadoAnalise) -> str:
    criticas  = estado.get("inconsistencias_criticas", [])
    moderadas = estado.get("inconsistencias_moderadas", [])
    if not criticas and not moderadas:
        return "Nenhuma inconsistência detectada."
    linhas = []
    for i in criticas:
        linhas.append(
            f"[CRÍTICA] {i.get('problema', '')} "
            f"— trecho: '{i.get('afirmacao', '')}'"
        )
    for i in moderadas:
        linhas.append(
            f"[MODERADA] {i.get('problema', '')} "
            f"— trecho: '{i.get('afirmacao', '')}'"
        )
    return "\n".join(linhas)

# ─── Subagente — Dor ──────────────────────────────────────────
def agente_dor(estado: EstadoAnalise) -> dict:
    print("→ Subagente: Analisando dor...")
    lacunas_texto = (
        "Críticas: " + str(estado.get("lacunas_criticas", [])) +
        " | Complementares: " + str(estado.get("lacunas_complementares", []))
    )
    resultado = chamar_modelo(
        SYSTEM_ANALISTA_DOR,
        PROMPT_DOR.format(
            foco_da_analise=estado.get("foco_da_analise", ""),
            documentos_relevantes=estado.get("documentos_relevantes", ""),
            lacunas=lacunas_texto,
            inconsistencias=formatar_inconsistencias(estado),
        )
    )
    if "erro" in resultado:
        return {"analise_dor": {"avaliacao": "AUSENTE", "erro": resultado["erro"]}}
    return {"analise_dor": resultado}

# ─── Subagente — Competitiva ──────────────────────────────────
def agente_competitiva(estado: EstadoAnalise) -> dict:
    print("→ Subagente: Analisando competição...")
    resultado = chamar_modelo(
        SYSTEM_ANALISTA_COMPETITIVA,
        PROMPT_COMPETITIVA.format(
            foco_da_analise=estado.get("foco_da_analise", ""),
            documentos_relevantes=estado.get("documentos_relevantes", ""),
            inconsistencias=formatar_inconsistencias(estado),
        )
    )
    if "erro" in resultado:
        return {"analise_competitiva": {"cobertura": "AUSENTE", "erro": resultado["erro"]}}
    return {"analise_competitiva": resultado}

# ─── Subagente — Viabilidade ──────────────────────────────────
def agente_viabilidade(estado: EstadoAnalise) -> dict:
    print("→ Subagente: Analisando viabilidade...")
    resultado = chamar_modelo(
        SYSTEM_ANALISTA_VIABILIDADE,
        PROMPT_VIABILIDADE.format(
            foco_da_analise=estado.get("foco_da_analise", ""),
            documentos_relevantes=estado.get("documentos_relevantes", ""),
            inconsistencias=formatar_inconsistencias(estado),
        )
    )
    if "erro" in resultado:
        return {"analise_viabilidade": {"viabilidade": "INDEFINIDA", "erro": resultado["erro"]}}
    return {"analise_viabilidade": resultado}

# ─── Agente de Síntese ────────────────────────────────────────
def agente_sintese(estado: EstadoAnalise) -> dict:
    print("→ Agente de Síntese: Emitindo veredito...")
    resultado = chamar_modelo(
        SYSTEM_SINTESE,
        PROMPT_SINTESE.format(
            tipo=estado["tipo"],
            modelo=estado["modelo"],
            estagio=estado["estagio"],
            arquetipo=estado["arquetipo"],
            analise_dor=json.dumps(
                estado.get("analise_dor", {}), ensure_ascii=False),
            analise_competitiva=json.dumps(
                estado.get("analise_competitiva", {}), ensure_ascii=False),
            analise_viabilidade=json.dumps(
                estado.get("analise_viabilidade", {}), ensure_ascii=False),
            inconsistencias=formatar_inconsistencias(estado),
            lacunas_criticas=estado.get("lacunas_criticas", []),
            lacunas_complementares=estado.get("lacunas_complementares", []),
        )
    )
    if "erro" in resultado:
        return {"veredito": "INVESTIGATE", "erro": resultado["erro"]}
    return {
        "veredito":                resultado.get("veredito", "INVESTIGATE"),
        "justificativa_principal": resultado.get("justificativa_principal", ""),
        "analise_por_dimensao":    resultado.get("analise_por_dimensao", {}),
        "confiabilidade":          resultado.get("confiabilidade", "BAIXA"),
        "dimensoes_comprometidas": resultado.get("dimensoes_comprometidas", []),
        "resumo_inconsistencias":  resultado.get("resumo_inconsistencias", ""),
    }

# ─── Nó de INVESTIGATE ────────────────────────────────────────
def agente_investigate(estado: EstadoAnalise) -> dict:
    print("→ Documentação insuficiente. Emitindo INVESTIGATE...")
    acoes = estado.get("lacunas_criticas", []) + [
        i.get("problema", "")
        for i in estado.get("inconsistencias_criticas", [])
    ]
    return {
        "veredito":                "INVESTIGATE",
        "justificativa_principal": "Lacunas críticas ou inconsistências graves impedem análise confiável.",
        "lacunas_criticas":        estado.get("lacunas_criticas", []),
        "confiabilidade":          "BAIXA",
    }

# ─── Roteador ─────────────────────────────────────────────────
def roteador(estado: EstadoAnalise) -> str:
    if estado.get("encerrar_com_investigate"):
        return "investigate"
    return "coerencia"

# ─── Construção do Grafo ──────────────────────────────────────
def construir_grafo():
    grafo = StateGraph(EstadoAnalise)

    grafo.add_node("intake",      agente_intake)
    grafo.add_node("qualidade",   agente_qualidade)
    grafo.add_node("coerencia",   agente_coerencia)
    grafo.add_node("dor",         agente_dor)
    grafo.add_node("competitiva", agente_competitiva)
    grafo.add_node("viabilidade", agente_viabilidade)
    grafo.add_node("sintese",     agente_sintese)
    grafo.add_node("investigate", agente_investigate)

    grafo.set_entry_point("intake")
    grafo.add_edge("intake",    "qualidade")

    grafo.add_conditional_edges(
        "qualidade",
        roteador,
        {
            "coerencia":   "coerencia",
            "investigate": "investigate",
        }
    )

    grafo.add_edge("coerencia",   "dor")
    grafo.add_edge("coerencia",   "competitiva")
    grafo.add_edge("coerencia",   "viabilidade")
    grafo.add_edge("dor",         "sintese")
    grafo.add_edge("competitiva", "sintese")
    grafo.add_edge("viabilidade", "sintese")
    grafo.add_edge("sintese",     END)
    grafo.add_edge("investigate", END)

    return grafo.compile()

grafo_validador = construir_grafo()