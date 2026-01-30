"""
Scraper para Deutsche Welle (DW)
"""
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

from .base_scraper import BaseScraper, ScrapedArticle


class DWScraper(BaseScraper):
    """Scraper para coleta de notícias da Deutsche Welle"""

    SOURCE_KEY = "dw"
    SOURCE_NAME = "Deutsche Welle"
    BASE_URL = "https://www.dw.com"
    LANGUAGE = "en"

    WORLD_URL = "https://www.dw.com/en/top-stories/s-9097"
    SEARCH_URL = "https://www.dw.com/search/?searchNavigationId=9097&languageCode=en&item={query}"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        """Obtém URLs de artigos da DW"""
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
                'a[href*="/en/"][href*="/a-"]',
                '.teaser a[href*="/a-"]',
                'article a[href*="/a-"]',
                'h2 a[href*="/a-"]'
            ]

            for selector in article_selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get("href")
                    if href and "/a-" in href:
                        full_url = self._resolve_url(href)
                        if full_url not in urls:
                            urls.append(full_url)

        except Exception as e:
            self.logger.error(f"Erro ao obter URLs: {e}")

        return urls

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        """Faz scraping de um artigo da DW"""
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            # Título
            title = None
            title_selectors = [
                '.article-header h1',
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
                '.longText',
                '.rich-text',
                'article .text',
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
            author_element = soup.select_one('[class*="author"], .article-author')
            if author_element:
                author = author_element.get_text(strip=True)

            # Data
            published_at = None
            date_element = soup.select_one('[class*="date"], time[datetime]')
            if date_element:
                try:
                    dt_str = date_element.get("datetime")
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
