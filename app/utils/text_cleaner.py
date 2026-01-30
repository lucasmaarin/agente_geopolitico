"""
Utilitário para limpeza e normalização de texto HTML
"""
import re
import html
from typing import Optional, List
from bs4 import BeautifulSoup


class TextCleaner:
    """
    Classe para limpeza e normalização de texto extraído de páginas web.
    Remove HTML, scripts, estilos, menus e ruído.
    """

    NOISE_PATTERNS = [
        r"Share this article",
        r"Follow us on",
        r"Subscribe to our newsletter",
        r"Read more:",
        r"Related articles",
        r"Advertisement",
        r"ADVERTISEMENT",
        r"Loading\.\.\.",
        r"Click here to",
        r"Sign up for",
        r"Join our",
        r"Download our app",
        r"Cookie policy",
        r"Privacy policy",
        r"Terms of service",
        r"All rights reserved",
        r"Copyright ©",
        r"\[.*?\]",  # Texto entre colchetes
        r"Photo:.*",
        r"Image:.*",
        r"Source:.*",
        r"Credit:.*",
    ]

    TAGS_TO_REMOVE = [
        "script", "style", "nav", "header", "footer",
        "aside", "iframe", "noscript", "form", "button",
        "input", "select", "textarea", "svg", "canvas",
        "video", "audio", "figure", "figcaption"
    ]

    ARTICLE_SELECTORS = [
        "article",
        '[class*="article"]',
        '[class*="content"]',
        '[class*="post"]',
        '[class*="story"]',
        '[class*="body"]',
        "main",
        '[role="main"]',
        '[itemprop="articleBody"]',
    ]

    @classmethod
    def clean_html(cls, html_content: str) -> str:
        """
        Remove tags HTML e extrai texto limpo.

        Args:
            html_content: Conteúdo HTML bruto

        Returns:
            Texto limpo sem HTML
        """
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, "lxml")

        for tag in cls.TAGS_TO_REMOVE:
            for element in soup.find_all(tag):
                element.decompose()

        text = soup.get_text(separator=" ", strip=True)
        text = html.unescape(text)

        return cls.normalize_whitespace(text)

    @classmethod
    def extract_article_content(cls, html_content: str) -> str:
        """
        Extrai apenas o conteúdo do artigo, ignorando menus e sidebars.

        Args:
            html_content: Conteúdo HTML bruto

        Returns:
            Texto do artigo principal
        """
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, "lxml")

        for tag in cls.TAGS_TO_REMOVE:
            for element in soup.find_all(tag):
                element.decompose()

        article_element = None
        for selector in cls.ARTICLE_SELECTORS:
            article_element = soup.select_one(selector)
            if article_element:
                break

        if article_element:
            text = article_element.get_text(separator=" ", strip=True)
        else:
            text = soup.get_text(separator=" ", strip=True)

        text = html.unescape(text)
        text = cls.remove_noise(text)

        return cls.normalize_whitespace(text)

    @classmethod
    def extract_title(cls, html_content: str) -> Optional[str]:
        """
        Extrai o título do artigo.

        Args:
            html_content: Conteúdo HTML bruto

        Returns:
            Título do artigo ou None
        """
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, "lxml")

        title_selectors = [
            "h1",
            '[class*="title"]',
            '[class*="headline"]',
            "title",
            '[itemprop="headline"]',
        ]

        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 10:
                    return cls.normalize_whitespace(title)

        return None

    @classmethod
    def extract_metadata(cls, html_content: str) -> dict:
        """
        Extrai metadados do artigo (autor, data, descrição).

        Args:
            html_content: Conteúdo HTML bruto

        Returns:
            Dicionário com metadados
        """
        if not html_content:
            return {}

        soup = BeautifulSoup(html_content, "lxml")
        metadata = {}

        # Autor
        author_selectors = [
            '[class*="author"]',
            '[rel="author"]',
            '[itemprop="author"]',
            '[name="author"]',
        ]
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get_text(strip=True) or element.get("content")
                if author:
                    metadata["author"] = author
                    break

        # Data
        date_selectors = [
            '[class*="date"]',
            '[class*="time"]',
            '[itemprop="datePublished"]',
            '[property="article:published_time"]',
            "time",
        ]
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date = element.get("datetime") or element.get("content") or element.get_text(strip=True)
                if date:
                    metadata["date"] = date
                    break

        # Descrição
        desc_element = soup.find("meta", {"name": "description"}) or \
                       soup.find("meta", {"property": "og:description"})
        if desc_element:
            metadata["description"] = desc_element.get("content", "")

        return metadata

    @classmethod
    def remove_noise(cls, text: str) -> str:
        """
        Remove padrões de ruído comuns em artigos web.

        Args:
            text: Texto a limpar

        Returns:
            Texto sem ruído
        """
        if not text:
            return ""

        for pattern in cls.NOISE_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        return text

    @classmethod
    def normalize_whitespace(cls, text: str) -> str:
        """
        Normaliza espaços em branco e quebras de linha.

        Args:
            text: Texto a normalizar

        Returns:
            Texto com espaços normalizados
        """
        if not text:
            return ""

        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)

        return text.strip()

    @classmethod
    def truncate(cls, text: str, max_length: int = 5000, suffix: str = "...") -> str:
        """
        Trunca texto em um limite de caracteres sem cortar palavras.

        Args:
            text: Texto a truncar
            max_length: Comprimento máximo
            suffix: Sufixo a adicionar se truncado

        Returns:
            Texto truncado
        """
        if not text or len(text) <= max_length:
            return text

        truncated = text[:max_length - len(suffix)]
        last_space = truncated.rfind(" ")

        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]

        return truncated + suffix

    @classmethod
    def extract_sentences(cls, text: str) -> List[str]:
        """
        Divide texto em sentenças.

        Args:
            text: Texto a dividir

        Returns:
            Lista de sentenças
        """
        if not text:
            return []

        sentence_pattern = r"(?<=[.!?])\s+"
        sentences = re.split(sentence_pattern, text)

        return [s.strip() for s in sentences if s.strip()]

    @classmethod
    def detect_language(cls, text: str) -> str:
        """
        Detecta idioma do texto de forma simples.

        Args:
            text: Texto para análise

        Returns:
            Código do idioma (en, pt, es, etc.)
        """
        if not text:
            return "unknown"

        portuguese_words = ["de", "da", "do", "em", "para", "com", "não", "uma", "que", "os", "as"]
        english_words = ["the", "is", "are", "was", "were", "have", "has", "been", "will", "would"]
        spanish_words = ["el", "la", "los", "las", "es", "son", "está", "están", "para", "con"]

        text_lower = text.lower()
        words = text_lower.split()

        pt_count = sum(1 for w in words if w in portuguese_words)
        en_count = sum(1 for w in words if w in english_words)
        es_count = sum(1 for w in words if w in spanish_words)

        max_count = max(pt_count, en_count, es_count)

        if max_count == 0:
            return "unknown"
        elif pt_count == max_count:
            return "pt"
        elif en_count == max_count:
            return "en"
        else:
            return "es"
