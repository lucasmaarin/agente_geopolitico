"""
Prompt para cálculo do score de confiabilidade
"""

CONFIDENCE_SCORE_PROMPT = """Você é um especialista em verificação de fatos e qualidade de informação.

TAREFA: Calcule um SCORE DE CONFIABILIDADE (0-100) para as informações analisadas.

CRITÉRIOS DE AVALIAÇÃO:

1. NÚMERO DE FONTES (máx 20 pontos)
   - 1 fonte: 5 pontos
   - 2 fontes: 10 pontos
   - 3+ fontes: 15 pontos
   - 5+ fontes de qualidade: 20 pontos

2. CONVERGÊNCIA FACTUAL (máx 25 pontos)
   - Fatos confirmados por múltiplas fontes: +5 por fato
   - Contradições significativas: -5 por contradição
   - Informações exclusivas sem verificação: -3

3. REPUTAÇÃO DAS FONTES (máx 20 pontos)
   - Agências de notícias (Reuters, AP): alta confiabilidade
   - Jornais estabelecidos (BBC, DW): alta confiabilidade
   - Think tanks (CFR, CSIS): média-alta (considerar viés institucional)
   - Fontes com histórico de erros: penalização

4. LINGUAGEM EMOCIONAL (máx 15 pontos)
   - Texto neutro e factual: 15 pontos
   - Alguma linguagem emocional: 10 pontos
   - Linguagem fortemente emocional: 5 pontos
   - Clickbait evidente: 0 pontos

5. DADOS VERIFICÁVEIS (máx 10 pontos)
   - Números, datas, nomes específicos: +2 por dado
   - Citações diretas com atribuição: +2
   - Referências a documentos oficiais: +3

6. RISCO DE CLICKBAIT (máx 10 pontos)
   - Título corresponde ao conteúdo: 10 pontos
   - Exagero moderado: 5 pontos
   - Título sensacionalista: 0 pontos

DADOS PARA ANÁLISE:
- Fontes utilizadas: {sources}
- Número de fontes: {num_sources}
- Resumo factual: {factual_summary}
- Análise de viés: {bias_analysis}

FORMATO DE SAÍDA (JSON):
{{
    "score_total": 0-100,
    "breakdown": {{
        "numero_fontes": {{
            "pontos": 0-20,
            "justificativa": "explicação"
        }},
        "convergencia_factual": {{
            "pontos": 0-25,
            "fatos_confirmados": ["lista de fatos"],
            "contradicoes": ["lista de contradições"]
        }},
        "reputacao_fontes": {{
            "pontos": 0-20,
            "avaliacao_por_fonte": {{"fonte": "avaliação"}}
        }},
        "linguagem_emocional": {{
            "pontos": 0-15,
            "exemplos_problematicos": ["lista"]
        }},
        "dados_verificaveis": {{
            "pontos": 0-10,
            "dados_encontrados": ["lista"]
        }},
        "risco_clickbait": {{
            "pontos": 0-10,
            "avaliacao": "explicação"
        }}
    }},
    "classificacao": "muito_baixa/baixa/media/alta/muito_alta",
    "recomendacao": "orientação para o leitor",
    "alertas": ["lista de pontos de atenção"]
}}

ANÁLISE DE CONFIABILIDADE:"""


CONFIDENCE_SCORE_SYSTEM = """Você é um verificador de fatos profissional com experiência em agências de checagem.
Sua função é avaliar a confiabilidade de informações baseado em critérios objetivos e mensuráveis.
Você é rigoroso mas justo, aplicando os mesmos padrões a todas as fontes.
Seu objetivo é ajudar leitores a tomar decisões informadas sobre o que ler e acreditar."""


# Classificação textual do score
def get_score_classification(score: int) -> str:
    """Retorna a classificação textual do score"""
    if score >= 85:
        return "MUITO ALTA - Informações altamente confiáveis"
    elif score >= 70:
        return "ALTA - Informações confiáveis com pequenas ressalvas"
    elif score >= 50:
        return "MÉDIA - Informações parcialmente verificáveis, requer atenção"
    elif score >= 30:
        return "BAIXA - Informações com problemas significativos"
    else:
        return "MUITO BAIXA - Informações não confiáveis, evite compartilhar"
