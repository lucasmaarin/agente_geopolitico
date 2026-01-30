"""
Frontend Flask para o Agente de Inteligência Geopolítica
"""
import os
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "geopolitica-secret-key-2024")

# Configuração da API Backend
API_URL = os.environ.get("API_URL", "http://localhost:8000/api/v1")
API_TIMEOUT = 300  # 5 minutos para operações longas (scraping + OpenAI)


def api_request(method, endpoint, data=None, params=None, timeout=30):
    """
    Faz requisição para a API backend.

    Args:
        method: GET ou POST
        endpoint: Endpoint da API (sem /api/v1)
        data: Dados para POST
        params: Parâmetros para GET
        timeout: Timeout em segundos

    Returns:
        Tuple (data, error)
    """
    url = f"{API_URL}/{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=timeout)
        else:
            response = requests.post(url, json=data, timeout=timeout)

        response.raise_for_status()
        return response.json(), None

    except requests.exceptions.ConnectionError:
        return None, "Não foi possível conectar à API. Verifique se o servidor está rodando."
    except requests.exceptions.Timeout:
        return None, "Timeout na requisição. A operação demorou muito."
    except requests.exceptions.HTTPError as e:
        return None, f"Erro HTTP: {e.response.status_code}"
    except Exception as e:
        return None, f"Erro: {str(e)}"


def check_api_health():
    """Verifica se a API está online"""
    data, error = api_request("GET", "health", timeout=5)
    return data is not None


# =============================================================================
# ROTAS PRINCIPAIS
# =============================================================================

@app.route("/")
def home():
    """Página inicial"""
    # Verificar status da API
    health_data, _ = api_request("GET", "health", timeout=5)
    api_online = health_data is not None

    # Obter fontes disponíveis
    sources_data, _ = api_request("GET", "sources", timeout=10)
    sources = sources_data.get("sources", []) if sources_data else []

    # Separar por tipo
    news_sources = [s for s in sources if s.get("type") == "news" and s.get("language") == "en"]
    analysis_sources = [s for s in sources if s.get("type") == "analysis"]
    brazil_sources = [s for s in sources if s.get("region") == "brazil"]

    return render_template(
        "home.html",
        api_online=api_online,
        health=health_data,
        news_sources=news_sources,
        analysis_sources=analysis_sources,
        brazil_sources=brazil_sources,
        total_sources=len(sources)
    )


@app.route("/search", methods=["GET", "POST"])
def search():
    """Página de busca de notícias"""
    results = None
    error = None
    topic = ""

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        max_articles = int(request.form.get("max_articles", 5))

        if not topic:
            error = "Por favor, informe um tema para buscar."
        elif len(topic) < 2:
            error = "O tema deve ter pelo menos 2 caracteres."
        else:
            results, error = api_request(
                "POST",
                "search",
                data={
                    "topic": topic,
                    "max_articles_per_source": max_articles
                },
                timeout=60
            )

    return render_template(
        "search.html",
        results=results,
        error=error,
        topic=topic
    )


@app.route("/report", methods=["GET", "POST"])
def report():
    """Página de geração de relatórios"""
    report_data = None
    error = None
    topic = ""

    # Verificar se OpenAI está configurada
    health_data, _ = api_request("GET", "health", timeout=5)
    openai_configured = health_data.get("openai_configured", False) if health_data else False

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        min_sources = int(request.form.get("min_sources", 3))
        include_scenarios = request.form.get("include_scenarios") == "on"

        if not topic:
            error = "Por favor, informe um tema para o relatório."
        elif len(topic) < 2:
            error = "O tema deve ter pelo menos 2 caracteres."
        else:
            report_data, error = api_request(
                "POST",
                "report",
                data={
                    "topic": topic,
                    "min_sources": min_sources,
                    "include_scenarios": include_scenarios
                },
                timeout=API_TIMEOUT
            )

    return render_template(
        "report.html",
        report=report_data,
        error=error,
        topic=topic,
        openai_configured=openai_configured
    )


@app.route("/history")
def history():
    """Página de histórico de relatórios"""
    page = request.args.get("page", 1, type=int)
    limit = 20

    reports_data, error = api_request(
        "GET",
        "reports",
        params={"limit": limit},
        timeout=30
    )

    reports = reports_data.get("reports", []) if reports_data else []

    return render_template(
        "history.html",
        reports=reports,
        error=error,
        page=page
    )


@app.route("/report/<int:report_id>")
def view_report(report_id):
    """Visualiza um relatório específico"""
    report_data, error = api_request(
        "GET",
        f"reports/{report_id}",
        timeout=30
    )

    if error:
        flash(error, "error")
        return redirect(url_for("history"))

    return render_template(
        "view_report.html",
        report=report_data
    )


@app.route("/events")
def events():
    """Página de eventos geopolíticos"""
    ongoing_only = request.args.get("ongoing", "false").lower() == "true"

    events_data, error = api_request(
        "GET",
        "events",
        params={"ongoing_only": ongoing_only, "limit": 50},
        timeout=30
    )

    events_list = events_data.get("events", []) if events_data else []

    return render_template(
        "events.html",
        events=events_list,
        error=error,
        ongoing_only=ongoing_only
    )


@app.route("/sources")
def sources():
    """Página de fontes de dados"""
    # Incluir fontes inativas para mostrar na interface
    sources_data, error = api_request("GET", "sources", params={"include_inactive": "true"}, timeout=10)
    sources_list = sources_data.get("sources", []) if sources_data else []

    # Organizar por tipo e região (apenas ativas para as tabs)
    by_type = {}
    by_region = {}

    for source in sources_list:
        # Por tipo (todas)
        source_type = source.get("type", "other")
        if source_type not in by_type:
            by_type[source_type] = []
        by_type[source_type].append(source)

        # Por região (todas)
        region = source.get("region", "global")
        if region not in by_region:
            by_region[region] = []
        by_region[region].append(source)

    return render_template(
        "sources.html",
        sources=sources_list,
        by_type=by_type,
        by_region=by_region,
        error=error
    )


@app.route("/about")
def about():
    """Página sobre o projeto"""
    return render_template("about.html")


# =============================================================================
# API ENDPOINTS (para AJAX)
# =============================================================================

@app.route("/api/status")
def api_status():
    """Retorna status da API para verificações AJAX"""
    health_data, error = api_request("GET", "health", timeout=5)

    if health_data:
        return jsonify({
            "online": True,
            "version": health_data.get("version"),
            "openai_configured": health_data.get("openai_configured"),
            "scrapers_available": health_data.get("scrapers_available")
        })

    return jsonify({"online": False, "error": error})


@app.route("/api/search", methods=["POST"])
def api_search():
    """Endpoint AJAX para busca"""
    data = request.get_json()

    if not data or not data.get("topic"):
        return jsonify({"error": "Tema não informado"}), 400

    results, error = api_request(
        "POST",
        "search",
        data=data,
        timeout=60
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify(results)


@app.route("/api/report", methods=["POST"])
def api_report():
    """Endpoint AJAX para geração de relatório (síncrono)"""
    data = request.get_json()

    if not data or not data.get("topic"):
        return jsonify({"error": "Tema não informado"}), 400

    results, error = api_request(
        "POST",
        "report",
        data=data,
        timeout=API_TIMEOUT
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify(results)


@app.route("/api/report/async", methods=["POST"])
def api_report_async():
    """Inicia geração de relatório em background"""
    data = request.get_json()

    if not data or not data.get("topic"):
        return jsonify({"error": "Tema não informado"}), 400

    results, error = api_request(
        "POST",
        "report/async",
        data=data,
        timeout=30
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify(results)


@app.route("/api/tasks/<task_id>")
def api_task_status(task_id):
    """Verifica status de uma tarefa"""
    results, error = api_request(
        "GET",
        f"tasks/{task_id}",
        timeout=10
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify(results)


# =============================================================================
# API ENDPOINTS - GERENCIAMENTO DE FONTES
# =============================================================================

@app.route("/api/sources/<source_key>/toggle", methods=["PUT"])
def api_toggle_source(source_key):
    """Ativa ou desativa uma fonte"""
    is_active = request.args.get("is_active", "true").lower() == "true"

    results, error = api_request(
        "PUT",
        f"sources/{source_key}/toggle",
        params={"is_active": str(is_active).lower()},
        timeout=10
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify(results)


@app.route("/api/sources", methods=["POST"])
def api_add_source():
    """Adiciona nova fonte customizada"""
    # Pegar parâmetros da query string
    params = {
        "key": request.args.get("key"),
        "name": request.args.get("name"),
        "url": request.args.get("url"),
        "source_type": request.args.get("source_type", "news"),
        "language": request.args.get("language", "en"),
        "region": request.args.get("region", "global"),
        "reputation_score": request.args.get("reputation_score", "70")
    }

    results, error = api_request(
        "POST",
        "sources",
        params=params,
        timeout=10
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify(results)


@app.route("/api/sources/<source_key>", methods=["DELETE"])
def api_delete_source(source_key):
    """Remove uma fonte customizada"""
    results, error = api_request(
        "DELETE",
        f"sources/{source_key}",
        timeout=10
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify(results)


# =============================================================================
# FILTROS JINJA2
# =============================================================================

@app.template_filter("datetime")
def format_datetime(value):
    """Formata datetime para exibição"""
    if not value:
        return "N/A"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except:
            return value

    return value.strftime("%d/%m/%Y %H:%M")


@app.template_filter("truncate_text")
def truncate_text(value, length=200):
    """Trunca texto com reticências"""
    if not value:
        return ""

    if len(value) <= length:
        return value

    return value[:length].rsplit(" ", 1)[0] + "..."


@app.template_filter("score_color")
def score_color(score):
    """Retorna classe CSS baseada no score"""
    if score >= 70:
        return "success"
    elif score >= 50:
        return "warning"
    else:
        return "danger"


@app.template_filter("score_label")
def score_label(score):
    """Retorna label textual do score"""
    if score >= 85:
        return "Muito Alta"
    elif score >= 70:
        return "Alta"
    elif score >= 50:
        return "Média"
    elif score >= 30:
        return "Baixa"
    else:
        return "Muito Baixa"


# =============================================================================
# CONTEXT PROCESSORS
# =============================================================================

@app.context_processor
def inject_globals():
    """Injeta variáveis globais em todos os templates"""
    return {
        "current_year": datetime.now().year,
        "app_name": "Agente Geopolítico",
        "app_version": "1.0.0"
    }


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template("errors/500.html"), 500


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    )
