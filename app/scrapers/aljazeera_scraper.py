"""
Scraper para Al Jazeera
"""
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

from .base_scraper import BaseScraper, ScrapedArticle


class AlJazeeraScraper(BaseScraper):
    """Scraper para coleta de notícias da Al Jazeera"""

    SOURCE_KEY = "aljazeera"
    SOURCE_NAME = "Al Jazeera"
    BASE_URL = "https://www.aljazeera.com"
    LANGUAGE = "en"

    WORLD_URL = "https://www.aljazeera.com/news/"
    SEARCH_URL = "https://www.aljazeera.com/search/{query}"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        """Obtém URLs de artigos da Al Jazeera"""
        urls = []

        try:
            if topic:
                search_url = self.SEARCH_URL.format(query=quote_plus(topic))
                html = self._fetch_page(search_url)
            else:
                html = self._fetch_page(self.WORLD_URL)

            if not html:
                return urls

            soup = self._parse_html(html)

            # Seletores para links de artigos
            article_selectors = [
                'a[href*="/news/"][href*="/2"]',
                'a[href*="/features/"]',
                '.gc__content a',
                'article a',
                'h3 a'
            ]

            for selector in article_selectors:
                links = soup.select(selector)
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
            "/live/", "/video/", "/program/",
            "/podcasts/", "/gallery/"
        ]
        return (
            ("/news/" in url or "/features/" in url) and
            not any(p in url.lower() for p in exclude_patterns)
        )

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        """Faz scraping de um artigo da Al Jazeera"""
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            # Título
            title = None
            title_selectors = [
                'h1.article__title',
                'h1[class*="post-title"]',
                '.article-header h1',
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
                '.wysiwyg--all-content',
                'article .article__content',
                '.main-article-body',
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
                '.article-author__name',
                '.author-link',
                '[class*="byline"]'
            ]
            for selector in author_selectors:
                element = soup.select_one(selector)
                if element:
                    author = element.get_text(strip=True)
                    break

            # Data
            published_at = None
            date_selectors = [
                '.article-dates time',
                'time[datetime]',
                '.date-simple'
            ]
            for selector in date_selectors:
                element = soup.select_one(selector)
                if element:
                    try:
                        dt_str = element.get("datetime")
                        if dt_str:
                            published_at = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                            break
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
