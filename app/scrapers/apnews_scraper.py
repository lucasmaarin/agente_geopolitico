"""
Scraper para AP News
"""
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

from .base_scraper import BaseScraper, ScrapedArticle


class APNewsScraper(BaseScraper):
    """Scraper para coleta de notícias da AP News"""

    SOURCE_KEY = "apnews"
    SOURCE_NAME = "AP News"
    BASE_URL = "https://apnews.com"
    LANGUAGE = "en"

    WORLD_URL = "https://apnews.com/world-news"
    SEARCH_URL = "https://apnews.com/search?q={query}"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        """Obtém URLs de artigos da AP News"""
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
                'a[href*="/article/"]',
                '.PagePromo a[href*="/article/"]',
                '.FeedCard a[href*="/article/"]',
                'h2 a[href*="/article/"]',
                'h3 a[href*="/article/"]'
            ]

            for selector in article_selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get("href")
                    if href and "/article/" in href:
                        full_url = self._resolve_url(href)
                        if full_url not in urls:
                            urls.append(full_url)

        except Exception as e:
            self.logger.error(f"Erro ao obter URLs: {e}")

        return urls

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        """Faz scraping de um artigo da AP News"""
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            # Título
            title = None
            title_selectors = [
                'h1[class*="Page-headline"]',
                'h1[data-key="card-headline"]',
                '.RichTextStoryBody h1',
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
                '.RichTextStoryBody',
                'article[class*="Article"]',
                '.Article',
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
                '[class*="Component-bylines"]',
                '.byline',
                '[class*="author"]'
            ]
            for selector in author_selectors:
                element = soup.select_one(selector)
                if element:
                    author = element.get_text(strip=True)
                    break

            # Data
            published_at = None
            time_selectors = [
                'time[datetime]',
                '[class*="Timestamp"]',
                'bsp-timestamp'
            ]
            for selector in time_selectors:
                element = soup.select_one(selector)
                if element:
                    try:
                        dt_str = element.get("datetime") or element.get("data-timestamp")
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
