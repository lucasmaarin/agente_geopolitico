# 🌍 Agente de Inteligência Geopolítica Anti-Fake News

Sistema inteligente que coleta notícias geopolíticas de múltiplas fontes confiáveis, cruza informações, detecta viés/propaganda, calcula score de confiabilidade e gera relatórios didáticos.

## ✨ Funcionalidades

- 📰 **Coleta Multi-Fonte**: 13+ fontes internacionais (Reuters, AP, BBC, etc.)
- 🔄 **Cruzamento de Informações**: Identifica convergências e contradições
- ⚠️ **Detecção de Viés**: Identifica propaganda e manipulação narrativa
- 📊 **Score de Confiabilidade**: Avaliação 0-100 baseada em critérios objetivos
- 🇧🇷 **Contexto Brasileiro**: Análise de impacto para o Brasil
- 👩‍🏫 **Explicação para Leigos**: Versão didática de cada análise
- 🔮 **Projeção de Cenários**: Curto, médio prazo e risco extremo

## 🛠️ Stack Tecnológica

- **Backend**: Python 3.11+, FastAPI
- **IA**: OpenAI API (GPT-4o)
- **Scraping**: Requests, BeautifulSoup, Selenium
- **Banco de Dados**: SQLite / PostgreSQL
- **Dashboard**: Streamlit
- **Agendamento**: APScheduler
- **Deploy**: Docker

## 📁 Estrutura do Projeto

```
automacao_geopolitica/
├── app/
│   ├── api/            # Endpoints FastAPI
│   ├── db/             # Modelos e repositórios
│   ├── pipelines/      # Pipeline de processamento
│   ├── prompts/        # Prompts para OpenAI
│   ├── scrapers/       # Scrapers por fonte
│   ├── scoring/        # Sistema de confiabilidade
│   └── utils/          # Utilitários
├── dashboard/          # Dashboard Streamlit
├── scheduler/          # Tarefas agendadas
├── main.py             # Entry point
├── config.py           # Configurações
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 🚀 Instalação e Execução

### Pré-requisitos

- Python 3.11+
- OpenAI API Key

### 1. Clonar e configurar

```bash
# Clonar repositório
cd automacao_geopolitica

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
# Criar arquivo .env
cp .env.example .env

# Editar .env e adicionar sua API key
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Executar

```bash
# Iniciar API
python main.py

# Em outro terminal, iniciar dashboard
streamlit run dashboard/streamlit_app.py

# Frontend integrado
A interface web está disponível no mesmo servidor da API:
http://localhost:8000

```

### Com Docker

```bash
# Construir e executar
docker-compose up -d

# Com scheduler automático
docker-compose --profile scheduler up -d
```

## 📡 API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/health` | Status do sistema |
| GET | `/api/v1/sources` | Lista fontes disponíveis |
| POST | `/api/v1/search` | Busca notícias por tema |
| POST | `/api/v1/report` | Gera relatório completo |
| GET | `/api/v1/reports` | Lista relatórios gerados |
| GET | `/api/v1/events` | Lista eventos geopolíticos |

## 📊 Formato do Relatório

```
🧾 RESUMO CURTO (TL;DR)
🌍 O QUE ACONTECEU
❓ POR QUE ISSO IMPORTA
⚔️ QUEM GANHA E QUEM PERDE
🇧🇷 IMPACTO PARA O BRASIL
⚠️ RISCO DE MANIPULAÇÃO (VIÉS E PROPAGANDA)
📊 SCORE DE CONFIABILIDADE (0-100)
👩‍🏫 EXPLICAÇÃO SIMPLES PARA LEIGOS
🔮 CENÁRIOS FUTUROS
```

## 📰 Fontes de Dados

### Notícias Internacionais
- Reuters, AP News, BBC World, DW, Al Jazeera

### Análise Geopolítica
- Foreign Affairs, CSIS, CFR, Crisis Group, RAND

### Fontes Brasileiras
- Nexo Jornal, BBC Brasil, Poder360

## 🔒 Score de Confiabilidade

O score (0-100) é calculado com base em:

| Critério | Pontos |
|----------|--------|
| Número de fontes | 20 |
| Convergência factual | 25 |
| Reputação das fontes | 20 |
| Linguagem emocional | 15 |
| Dados verificáveis | 10 |
| Risco de clickbait | 10 |

**Classificação:**
- 85-100: Muito Alta ✅
- 70-84: Alta ✅
- 50-69: Média ⚠️
- 30-49: Baixa ⚠️
- 0-29: Muito Baixa ❌

## 🧪 Exemplos de Uso

### Buscar notícias via API

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/search",
    json={"topic": "Ukraine war", "max_articles_per_source": 5}
)
print(response.json())
```

### Gerar relatório

```python
response = requests.post(
    "http://localhost:8000/api/v1/report",
    json={"topic": "US-China relations", "min_sources": 3}
)
report = response.json()
print(report["formatted_report"])
```

## ⚠️ Regras do Sistema

1. **Multi-fonte obrigatória**: Nunca gera resumo com menos de 3 fontes
2. **Detecção de viés**: Analisa todas as fontes por viés político/ideológico
3. **Transparência**: Sempre cita as fontes de cada informação
4. **Conflitos**: Menciona explicitamente quando há contradições

## 🔧 Configurações Avançadas

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.3

# Scraping
SCRAPER_TIMEOUT=30
SCRAPER_RETRY_ATTEMPTS=3
SCRAPER_DELAY_MIN=1.0
SCRAPER_DELAY_MAX=3.0

# Análise
MIN_SOURCES_FOR_REPORT=3
MAX_ARTICLES_PER_SOURCE=10

# Cache
CACHE_TTL_SECONDS=3600

# Scheduler
SCHEDULER_INTERVAL_HOURS=6
```

## 📝 Licença

MIT License

## 🤝 Contribuições

Contribuições são bem-vindas! Por favor, abra uma issue ou pull request.

---

Desenvolvido com 🐍 Python | 🚀 FastAPI | 🤖 OpenAI
