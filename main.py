# main.py
import streamlit as st
import json
from app.agents import grafo_validador
from app.database import init_db, get_session, Analise
from config import APP_TITLE, APP_VERSION

init_db()

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🔍",
    layout="wide",
)

st.title(f"🔍 {APP_TITLE}")
st.caption(f"v{APP_VERSION} — Análise baseada em evidência real")
st.divider()

# ─── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.header("Histórico de Análises")
    session = get_session()
    analises = session.query(Analise).order_by(
        Analise.criado_em.desc()
    ).limit(10).all()
    if not analises:
        st.info("Nenhuma análise ainda.")
    else:
        for a in analises:
            cor = {
                "GO":          "🟢",
                "NO-GO":       "🔴",
                "PIVOT":       "🟡",
                "INVESTIGATE": "🔵",
            }.get(a.veredito, "⚪")
            st.write(f"{cor} {a.titulo}")
            st.caption(a.criado_em.strftime("%d/%m/%Y %H:%M"))

# ─── Formulário ───────────────────────────────────────────────
st.subheader("Nova Análise")

titulo = st.text_input(
    "Título da ideia",
    placeholder="Ex: Plataforma de validação de ideias com IA"
)

uploaded_files = st.file_uploader(
    "Carregar documentos (PDF, TXT, MD)",
    type=["pdf", "txt", "md"],
    accept_multiple_files=True,
)

st.markdown("**Ou cole a documentação diretamente:**")
documentos_texto = st.text_area(
    label="Documentação",
    placeholder="Cole aqui o conteúdo dos seus documentos...",
    height=200,
    label_visibility="collapsed"
)

# ─── Processar arquivos ───────────────────────────────────────
def extrair_texto_arquivos(files) -> str:
    textos = []
    for f in files:
        if f.type == "text/plain" or f.name.endswith(".md"):
            textos.append(f.read().decode("utf-8", errors="ignore"))
        elif f.type == "application/pdf":
            try:
                import pdfplumber
                import io
                with pdfplumber.open(io.BytesIO(f.read())) as pdf:
                    for page in pdf.pages:
                        texto = page.extract_text()
                        if texto:
                            textos.append(texto)
            except ImportError:
                textos.append(
                    f"[PDF '{f.name}' não processado — instale pdfplumber]"
                )
    return "\n\n".join(textos)

# ─── Botão de análise ─────────────────────────────────────────
if st.button("Analisar", type="primary", use_container_width=True):

    documentos_arquivos = (
        extrair_texto_arquivos(uploaded_files) if uploaded_files else ""
    )
    documentos_combined = "\n\n".join(
        filter(None, [documentos_arquivos, documentos_texto])
    )

    if not titulo.strip():
        st.error("Digite um título para a ideia.")
    elif not documentos_combined.strip():
        st.error("Adicione documentação — carregue arquivos ou cole o texto.")
    else:
        with st.spinner("Analisando... isso pode levar alguns minutos."):
            estado_inicial = {
                "titulo":                    titulo,
                "documentos":                documentos_combined,
                "tipo":                      "",
                "modelo":                    "",
                "estagio":                   "",
                "arquetipo":                 "",
                "justificativa_marcadores":  "",
                "mapa_documentos":           [],
                "documentos_relevantes":     "",
                "documentos_ignorados":      [],
                "lacunas_criticas":          [],
                "lacunas_complementares":    [],
                "nivel_evidencia":           1,
                "suficiente_para_analise":   True,
                "justificativa_auditoria":   "",
                "inconsistencias_criticas":  [],
                "inconsistencias_moderadas": [],
                "nivel_alerta":              "INFORMATIVO",
                "framework_principal":       "",
                "framework_secundario":      "",
                "foco_da_analise":           "",
                "alertas":                   [],
                "analise_dor":               {},
                "analise_competitiva":       {},
                "analise_viabilidade":       {},
                "veredito":                  "",
                "justificativa_principal":   "",
                "analise_por_dimensao":      {},
                "confiabilidade":            "",
                "dimensoes_comprometidas":   [],
                "resumo_inconsistencias":    "",
                "encerrar_com_investigate":  False,
                "erro":                      "",
            }
            resultado = grafo_validador.invoke(estado_inicial)

        st.divider()
        st.subheader("Resultado da Análise")

        # ─── Alerta de documentação ───────────────────────────
        nivel_alerta = resultado.get("nivel_alerta", "INFORMATIVO")

        if nivel_alerta == "CRITICO":
            st.error("""
**⛔ DOCUMENTAÇÃO INSUFICIENTE PARA ANÁLISE**

A documentação apresenta lacunas críticas ou inconsistências graves
que impedem qualquer análise confiável. O veredito abaixo é INVESTIGATE
por padrão. Nenhuma recomendação de execução foi gerada.

Resolva os itens listados em "O que precisa melhorar" antes de resubmeter.
""")
        elif nivel_alerta == "MODERADO":
            st.warning("""
**⚠️ DOCUMENTAÇÃO ANALISÁVEL COM LIMITAÇÕES**

A documentação tem lacunas ou inconsistências que comprometem
a confiabilidade da análise. Recomendações de execução foram bloqueadas —
gerar próximos passos com esta documentação seria especulação, não análise.

Consulte "O que precisa melhorar" para fechar as lacunas identificadas.
""")

        # ─── Veredito ─────────────────────────────────────────
        veredito = resultado.get("veredito", "INVESTIGATE")
        config_veredito = {
            "GO":          ("🟢", "success"),
            "NO-GO":       ("🔴", "error"),
            "PIVOT":       ("🟡", "warning"),
            "INVESTIGATE": ("🔵", "info"),
        }.get(veredito, ("⚪", "info"))

        getattr(st, config_veredito[1])(
            f"{config_veredito[0]} **{veredito}** — "
            f"{resultado.get('justificativa_principal', '')}"
        )

        # ─── Classificação ────────────────────────────────────
        st.markdown("**Classificação da ideia**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tipo",      resultado.get("tipo", "—"))
        col2.metric("Modelo",    resultado.get("modelo", "—"))
        col3.metric("Estágio",   resultado.get("estagio", "—"))
        col4.metric("Arquétipo", resultado.get("arquetipo", "—"))

        # ─── Nível de evidência ───────────────────────────────
        nivel = resultado.get("nivel_evidencia", 1)
        st.metric("Nível de Evidência", f"{nivel}/7")
        st.progress(nivel / 7)

        # ─── Mapa de documentos ───────────────────────────────
        mapa = resultado.get("mapa_documentos", [])
        if mapa:
            with st.expander("📂 Mapa de documentos recebidos"):
                for doc in mapa:
                    peso = doc.get("peso", "—")
                    cor_peso = {
                        "ALTO":  "🟢",
                        "MEDIO": "🟡",
                        "BAIXO": "🟠",
                        "NULO":  "🔴",
                    }.get(peso, "⚪")
                    st.write(
                        f"{cor_peso} **{doc.get('identificador', '—')}** "
                        f"— {doc.get('papel', '—')} | Peso: {peso} "
                        f"| Dimensão: {doc.get('dimensao', '—')}"
                    )
                    st.caption(doc.get("justificativa", ""))

        # ─── Inconsistências ──────────────────────────────────
        criticas  = resultado.get("inconsistencias_criticas", [])
        moderadas = resultado.get("inconsistencias_moderadas", [])

        if criticas or moderadas:
            with st.expander(
                f"⚠️ Inconsistências detectadas "
                f"({len(criticas)} críticas, {len(moderadas)} moderadas)"
            ):
                if criticas:
                    st.markdown("**Críticas**")
                    for i in criticas:
                        st.error(
                            f"**{i.get('tipo', '')}** — "
                            f"{i.get('problema', '')}\n\n"
                            f"> _{i.get('afirmacao', '')}_"
                        )
                if moderadas:
                    st.markdown("**Moderadas**")
                    for i in moderadas:
                        st.warning(
                            f"**{i.get('tipo', '')}** — "
                            f"{i.get('problema', '')}\n\n"
                            f"> _{i.get('afirmacao', '')}_"
                        )

        # ─── Análise por dimensão ─────────────────────────────
        analise = resultado.get("analise_por_dimensao", {})
        if analise:
            st.markdown("**Análise por dimensão**")
            col_dor, col_comp, col_viab = st.columns(3)
            with col_dor:
                st.markdown("**Dor**")
                st.write(analise.get("dor", "—"))
            with col_comp:
                st.markdown("**Competitiva**")
                st.write(analise.get("competitiva", "—"))
            with col_viab:
                st.markdown("**Viabilidade**")
                st.write(analise.get("viabilidade", "—"))

        # ─── Confiabilidade ───────────────────────────────────
        confiabilidade = resultado.get("confiabilidade", "BAIXA")
        st.markdown(f"**Confiabilidade da análise:** {confiabilidade}")

        comprometidas = resultado.get("dimensoes_comprometidas", [])
        if comprometidas:
            st.caption("Dimensões comprometidas: " + ", ".join(comprometidas))

        resumo_inc = resultado.get("resumo_inconsistencias", "")
        if resumo_inc:
            st.caption(f"Impacto das inconsistências: {resumo_inc}")

        # ─── O que precisa melhorar ───────────────────────────
        lac_criticas = resultado.get("lacunas_criticas", [])
        lac_comp     = resultado.get("lacunas_complementares", [])

        if lac_criticas or lac_comp:
            st.markdown("**📋 O que precisa melhorar antes da próxima análise**")
            if lac_criticas:
                for l in lac_criticas:
                    st.write(f"🔴 {l}")
            if lac_comp:
                for l in lac_comp:
                    st.write(f"🟡 {l}")

        # ─── Documentos ignorados ─────────────────────────────
        ignorados = resultado.get("documentos_ignorados", [])
        if ignorados:
            with st.expander("ℹ️ Documentos não utilizados na análise"):
                st.caption(
                    "Estes documentos foram recebidos mas não influenciaram "
                    "o veredito por serem documentação técnica, tutoriais ou "
                    "referências sem peso analítico para validação de produto."
                )
                for d in ignorados:
                    st.write(f"• {d}")

        # ─── Persistir ────────────────────────────────────────
        session = get_session()
        nova = Analise(
            titulo=titulo,
            documentos=documentos_combined,
            marcadores=json.dumps({
                "tipo":      resultado.get("tipo"),
                "modelo":    resultado.get("modelo"),
                "estagio":   resultado.get("estagio"),
                "arquetipo": resultado.get("arquetipo"),
            }, ensure_ascii=False),
            lacunas=json.dumps({
                "criticas":      resultado.get("lacunas_criticas", []),
                "complementares": resultado.get("lacunas_complementares", []),
            }, ensure_ascii=False),
            veredito=veredito,
            relatorio=json.dumps(resultado, ensure_ascii=False),
            nivel_evidencia=resultado.get("nivel_evidencia", 1),
        )
        session.add(nova)
        session.commit()
        session.close()

        st.success("Análise salva no histórico.")