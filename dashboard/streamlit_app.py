"""
Dashboard Streamlit para o Agente de Inteligência Geopolítica
"""
import streamlit as st
import requests
import json
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="Agente Geopolítico",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuração da API
API_URL = "http://localhost:8000/api/v1"


def get_api(endpoint: str, params: dict = None):
    """Faz requisição GET para a API"""
    try:
        response = requests.get(f"{API_URL}/{endpoint}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Não foi possível conectar à API. Verifique se o servidor está rodando.")
        return None
    except Exception as e:
        st.error(f"❌ Erro na requisição: {e}")
        return None


def post_api(endpoint: str, data: dict):
    """Faz requisição POST para a API"""
    try:
        response = requests.post(f"{API_URL}/{endpoint}", json=data, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Não foi possível conectar à API. Verifique se o servidor está rodando.")
        return None
    except requests.exceptions.Timeout:
        st.error("❌ Timeout na requisição. A análise pode demorar, tente novamente.")
        return None
    except Exception as e:
        st.error(f"❌ Erro na requisição: {e}")
        return None


def render_confidence_gauge(score: int):
    """Renderiza gauge do score de confiabilidade"""
    color = "green" if score >= 70 else "orange" if score >= 50 else "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Score de Confiabilidade"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 30], 'color': "lightcoral"},
                {'range': [30, 50], 'color': "lightyellow"},
                {'range': [50, 70], 'color': "lightblue"},
                {'range': [70, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    fig.update_layout(height=300)
    return fig


def render_source_chart(sources: list):
    """Renderiza gráfico de fontes utilizadas"""
    if not sources:
        return None

    df = pd.DataFrame(sources)
    fig = px.bar(
        df,
        x='name',
        y='reputation_score',
        color='type',
        title="Reputação das Fontes Utilizadas",
        labels={'name': 'Fonte', 'reputation_score': 'Score de Reputação'}
    )
    fig.update_layout(height=300)
    return fig


# Sidebar
st.sidebar.title("🌍 Agente Geopolítico")
st.sidebar.markdown("---")

# Menu de navegação
page = st.sidebar.radio(
    "Navegação",
    ["🏠 Início", "🔍 Buscar Notícias", "📊 Gerar Relatório", "📚 Histórico", "⚙️ Configurações"]
)

# Verificar conexão com API
health = get_api("health")
if health:
    st.sidebar.success(f"✅ API Online (v{health.get('version', 'N/A')})")
    st.sidebar.info(f"📰 {health.get('scrapers_available', 0)} fontes disponíveis")
else:
    st.sidebar.error("❌ API Offline")

st.sidebar.markdown("---")
st.sidebar.markdown("**Desenvolvido com:**")
st.sidebar.markdown("🐍 Python | 🚀 FastAPI | 🤖 OpenAI")

# Páginas
if page == "🏠 Início":
    st.title("🌍 Agente de Inteligência Geopolítica")
    st.markdown("### Anti-Fake News | Multi-Fonte | Análise Profunda")

    st.markdown("""
    Bem-vindo ao **Agente de Inteligência Geopolítica**, uma ferramenta que:

    - 📰 **Coleta notícias** de 13+ fontes internacionais confiáveis
    - 🔄 **Cruza informações** para identificar convergências e contradições
    - ⚠️ **Detecta viés** e técnicas de propaganda automaticamente
    - 📊 **Calcula confiabilidade** baseado em múltiplos critérios
    - 🇧🇷 **Analisa impacto** para o Brasil
    - 👩‍🏫 **Explica de forma simples** para leigos
    """)

    st.markdown("---")

    # Estatísticas rápidas
    col1, col2, col3, col4 = st.columns(4)

    if health:
        col1.metric("Fontes Ativas", health.get('scrapers_available', 0))
        col2.metric("OpenAI", "✅ Configurada" if health.get('openai_configured') else "❌ Não configurada")
        col3.metric("Status", "🟢 Online")
        col4.metric("Versão", health.get('version', 'N/A'))

    st.markdown("---")

    # Fontes disponíveis
    st.subheader("📰 Fontes de Dados")

    sources = get_api("sources")
    if sources:
        tabs = st.tabs(["Notícias", "Análise", "Brasil"])

        with tabs[0]:
            news_sources = [s for s in sources.get('sources', []) if s.get('type') == 'news' and s.get('language') == 'en']
            for s in news_sources:
                st.markdown(f"**{s['name']}** - Reputação: {s['reputation_score']}/100")

        with tabs[1]:
            analysis_sources = [s for s in sources.get('sources', []) if s.get('type') == 'analysis']
            for s in analysis_sources:
                st.markdown(f"**{s['name']}** - Reputação: {s['reputation_score']}/100")

        with tabs[2]:
            br_sources = [s for s in sources.get('sources', []) if s.get('region') == 'brazil']
            for s in br_sources:
                st.markdown(f"**{s['name']}** - Reputação: {s['reputation_score']}/100")


elif page == "🔍 Buscar Notícias":
    st.title("🔍 Buscar Notícias")
    st.markdown("Busque notícias sobre um tema em múltiplas fontes.")

    with st.form("search_form"):
        topic = st.text_input("Tema para buscar", placeholder="Ex: Ukraine war, US elections, China trade")
        max_articles = st.slider("Máximo de artigos por fonte", 1, 10, 5)

        submitted = st.form_submit_button("🔍 Buscar")

        if submitted and topic:
            with st.spinner("Buscando notícias..."):
                result = post_api("search", {
                    "topic": topic,
                    "max_articles_per_source": max_articles
                })

            if result:
                st.success(f"✅ Encontrados {result.get('articles_found', 0)} artigos de {result.get('sources_used', 0)} fontes")

                for article in result.get('articles', [])[:20]:
                    with st.expander(f"📰 {article.get('title', 'Sem título')[:80]}..."):
                        st.markdown(f"**Fonte:** {article.get('source_name', 'N/A')}")
                        st.markdown(f"**URL:** [{article.get('url', '')}]({article.get('url', '')})")
                        if article.get('published_at'):
                            st.markdown(f"**Publicado:** {article.get('published_at')}")
                        st.markdown("---")
                        st.markdown(article.get('content_preview', 'Conteúdo não disponível'))


elif page == "📊 Gerar Relatório":
    st.title("📊 Gerar Relatório Geopolítico")
    st.markdown("Gere um relatório completo com análise cruzada, detecção de viés e projeção de cenários.")

    if not health or not health.get('openai_configured'):
        st.warning("⚠️ OpenAI API não configurada. Configure OPENAI_API_KEY para análises avançadas.")

    with st.form("report_form"):
        topic = st.text_input("Tema do relatório", placeholder="Ex: Russia-Ukraine conflict, US-China relations")
        min_sources = st.slider("Mínimo de fontes requeridas", 2, 10, 3)
        include_scenarios = st.checkbox("Incluir projeção de cenários", value=True)

        submitted = st.form_submit_button("📊 Gerar Relatório")

        if submitted and topic:
            with st.spinner("Gerando relatório... Isso pode levar alguns minutos."):
                result = post_api("report", {
                    "topic": topic,
                    "min_sources": min_sources,
                    "include_scenarios": include_scenarios
                })

            if result:
                st.success("✅ Relatório gerado com sucesso!")

                # Score de confiabilidade
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.plotly_chart(
                        render_confidence_gauge(result.get('confidence_score', 0)),
                        use_container_width=True
                    )

                with col2:
                    st.markdown(f"**Classificação:** {result.get('confidence_classification', 'N/A')}")
                    st.markdown(f"**Fontes utilizadas:** {result.get('sources_count', 0)}")
                    st.markdown(f"**Convergência:** {result.get('convergence_score', 0):.1f}%")

                    if result.get('alerts'):
                        st.warning("**Alertas:**")
                        for alert in result.get('alerts', []):
                            st.markdown(f"- ⚠️ {alert}")

                st.markdown("---")

                # Relatório formatado
                st.subheader("📋 Relatório Completo")

                with st.expander("🧾 RESUMO CURTO (TL;DR)", expanded=True):
                    st.markdown(result.get('tldr', 'N/A'))

                with st.expander("🌍 O QUE ACONTECEU"):
                    st.markdown(result.get('what_happened', 'N/A'))

                with st.expander("❓ POR QUE ISSO IMPORTA"):
                    st.markdown(result.get('why_it_matters', 'N/A'))

                with st.expander("⚔️ QUEM GANHA E QUEM PERDE"):
                    st.markdown(result.get('winners_losers', 'N/A'))

                with st.expander("🇧🇷 IMPACTO PARA O BRASIL"):
                    st.markdown(result.get('brazil_impact', 'N/A'))

                with st.expander("⚠️ RISCO DE MANIPULAÇÃO"):
                    st.markdown(result.get('manipulation_risk', 'N/A'))

                with st.expander("👩‍🏫 EXPLICAÇÃO SIMPLES PARA LEIGOS"):
                    st.markdown(result.get('simple_explanation', 'N/A'))

                # Cenários
                if include_scenarios:
                    st.subheader("🔮 CENÁRIOS FUTUROS")

                    cols = st.columns(3)

                    with cols[0]:
                        st.markdown("**📍 Curto Prazo**")
                        if result.get('short_term_scenario'):
                            sc = result['short_term_scenario']
                            st.markdown(f"*{sc.get('titulo', 'N/A')}*")
                            st.markdown(sc.get('descricao', 'N/A'))

                    with cols[1]:
                        st.markdown("**📍 Médio Prazo**")
                        if result.get('medium_term_scenario'):
                            sc = result['medium_term_scenario']
                            st.markdown(f"*{sc.get('titulo', 'N/A')}*")
                            st.markdown(sc.get('descricao', 'N/A'))

                    with cols[2]:
                        st.markdown("**⚠️ Risco Extremo**")
                        if result.get('extreme_risk_scenario'):
                            sc = result['extreme_risk_scenario']
                            st.markdown(f"*{sc.get('titulo', 'N/A')}*")
                            st.markdown(sc.get('descricao', 'N/A'))

                # Gráfico de fontes
                if result.get('sources_used'):
                    st.subheader("📰 Fontes Utilizadas")
                    fig = render_source_chart(result.get('sources_used'))
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

                # Exportar
                st.markdown("---")
                st.download_button(
                    label="📥 Baixar Relatório (TXT)",
                    data=result.get('formatted_report', ''),
                    file_name=f"relatorio_{topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )


elif page == "📚 Histórico":
    st.title("📚 Histórico de Relatórios")

    reports = get_api("reports", {"limit": 50})

    if reports and reports.get('reports'):
        for r in reports.get('reports', []):
            with st.expander(f"📊 {r.get('topic', 'N/A')} - Score: {r.get('confidence_score', 0)}/100"):
                st.markdown(f"**ID:** {r.get('id')}")
                st.markdown(f"**Fontes:** {r.get('sources_count', 0)}")
                st.markdown(f"**Gerado em:** {r.get('generated_at', 'N/A')}")
                st.markdown(f"**Status:** {r.get('status', 'N/A')}")

                if st.button(f"Ver detalhes", key=f"view_{r.get('id')}"):
                    detail = get_api(f"reports/{r.get('id')}")
                    if detail:
                        st.json(detail)
    else:
        st.info("Nenhum relatório encontrado. Gere um relatório na aba 'Gerar Relatório'.")


elif page == "⚙️ Configurações":
    st.title("⚙️ Configurações")

    st.markdown("### Status do Sistema")

    if health:
        st.json(health)
    else:
        st.error("Não foi possível obter status do sistema")

    st.markdown("### Cache")
    stats = get_api("stats")
    if stats:
        st.json(stats.get('cache_stats', {}))

    st.markdown("---")

    st.markdown("### Configuração necessária")
    st.code("""
# Criar arquivo .env com:
OPENAI_API_KEY=sk-your-api-key-here
DEBUG=false
    """, language="bash")


# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "🌍 Agente de Inteligência Geopolítica | Anti-Fake News | v1.0.0"
    "</div>",
    unsafe_allow_html=True
)
