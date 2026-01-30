"""
Scrapers para fontes brasileiras
Nexo Jornal, Poder360
"""
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

from .base_scraper import BaseScraper, ScrapedArticle


class NexoScraper(BaseScraper):
    """Scraper para Nexo Jornal"""

    SOURCE_KEY = "nexo"
    SOURCE_NAME = "Nexo Jornal"
    BASE_URL = "https://www.nexojornal.com.br"
    LANGUAGE = "pt-br"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        urls = []
        try:
            sections = [
                f"{self.BASE_URL}/internacional",
                f"{self.BASE_URL}/expresso",
                f"{self.BASE_URL}/explicado"
            ]

            for section_url in sections:
                html = self._fetch_page(section_url)
                if not html:
                    continue

                soup = self._parse_html(html)
                links = soup.select('a[href*="/expresso/"], a[href*="/explicado/"], a[href*="/externo/"]')

                for link in links:
                    href = link.get("href")
                    if href and self._is_valid_article_url(href):
                        full_url = self._resolve_url(href)
                        if full_url not in urls:
                            urls.append(full_url)

        except Exception as e:
            self.logger.error(f"Erro ao obter URLs: {e}")

        return urls

    def _is_valid_article_url(self, url: str) -> bool:
        """Verifica se é uma URL válida de artigo"""
        exclude_patterns = ["/autor/", "/assunto/", "/podcast/"]
        return not any(p in url.lower() for p in exclude_patterns)

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            # Título
            title = None
            title_element = soup.select_one('h1, .article-title, [class*="headline"]')
            if title_element:
                title = title_element.get_text(strip=True)

            if not title:
                return None

            # Conteúdo
            content = ""
            article = soup.select_one('article, .article-body, .post-content')
            if article:
                paragraphs = article.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs)

            if not content:
                content = self._clean_content(html)

            # Autor
            author = None
            author_element = soup.select_one('[class*="author"], .byline, [rel="author"]')
            if author_element:
                author = author_element.get_text(strip=True)

            # Data
            published_at = None
            time_element = soup.select_one('time[datetime]')
            if time_element:
                try:
                    dt_str = time_element.get("datetime")
                    published_at = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                except:
                    pass

            return ScrapedArticle(
                url=url,
                title=title,
                content=content,
                raw_content=html,
                author=author,
                published_at=published_at,
                language=self.LANGUAGE,
                source_key=self.SOURCE_KEY
            )

        except Exception as e:
            self.logger.error(f"Erro ao fazer scraping de {url}: {e}")
            return None


class Poder360Scraper(BaseScraper):
    """Scraper para Poder360"""

    SOURCE_KEY = "poder360"
    SOURCE_NAME = "Poder360"
    BASE_URL = "https://www.poder360.com.br"
    LANGUAGE = "pt-br"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        urls = []
        try:
            sections = [
                f"{self.BASE_URL}/internacional",
                f"{self.BASE_URL}/brasil"
            ]

            for section_url in sections:
                html = self._fetch_page(section_url)
                if not html:
                    continue

                soup = self._parse_html(html)

                # Links de artigos
                links = soup.select('a[href*="poder360.com.br/"]')

                for link in links:
                    href = link.get("href")
                    if href and self._is_valid_article_url(href):
                        full_url = self._resolve_url(href)
                        if full_url not in urls:
                            urls.append(full_url)

        except Exception as e:
            self.logger.error(f"Erro ao obter URLs: {e}")

        return urls

    def _is_valid_article_url(self, url: str) -> bool:
        """Verifica se é uma URL válida de artigo"""
        exclude_patterns = [
            "/autor/", "/categoria/", "/tag/",
            "/pagina/", "/podcast/", "/video/"
        ]
        # Verificar se a URL tem o padrão de artigo (geralmente termina com número ou slug)
        return (
            "poder360.com.br/" in url and
            not any(p in url.lower() for p in exclude_patterns) and
            url.count("/") >= 4  # URLs de artigos geralmente têm mais segmentos
        )

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            # Título
            title = None
            title_selectors = [
                'h1.entry-title',
                'h1[class*="title"]',
                'article h1',
                'h1'
            ]
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    title = element.get_text(strip=True)
                    break

            if not title:
                return None

            # Conteúdo
            content_selectors = [
                '.entry-content',
                '.post-content',
                'article .content',
                'article'
            ]
            content = ""
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    paragraphs = element.find_all("p")
                    content = " ".join(p.get_text(strip=True) for p in paragraphs)
                    break

            if not content:
                content = self._clean_content(html)

            # Autor
            author = None
            author_selectors = [
                '.author-name',
                '[class*="author"]',
                '.byline'
            ]
            for selector in author_selectors:
                element = soup.select_one(selector)
                if element:
                    author = element.get_text(strip=True)
                    break

            # Data
            published_at = None
            time_element = soup.select_one('time[datetime], .entry-date')
            if time_element:
                try:
                    dt_str = time_element.get("datetime")
                    if dt_str:
                        published_at = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                except:
                    pass

            return ScrapedArticle(
                url=url,
                title=title,
                content=content,
                raw_content=html,
                author=author,
                published_at=published_at,
                language=self.LANGUAGE,
                source_key=self.SOURCE_KEY
            )

        except Exception as e:
            self.logger.error(f"Erro ao fazer scraping de {url}: {e}")
            return None
