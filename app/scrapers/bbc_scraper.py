"""
Scraper para BBC World News
"""
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

from .base_scraper import BaseScraper, ScrapedArticle


class BBCScraper(BaseScraper):
    """Scraper para coleta de notícias da BBC World"""

    SOURCE_KEY = "bbc"
    SOURCE_NAME = "BBC World"
    BASE_URL = "https://www.bbc.com"
    LANGUAGE = "en"

    WORLD_URL = "https://www.bbc.com/news/world"
    SEARCH_URL = "https://www.bbc.co.uk/search?q={query}&d=NEWS_PS"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        """Obtém URLs de artigos da BBC"""
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
                'a[href*="/news/world"]',
                'a[href*="/news/articles/"]',
                'a[data-testid="internal-link"]',
                '.gs-c-promo-heading a',
                'h3 a[href*="/news/"]'
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
            "/live/", "/video/", "/sounds/",
            "/sport/", "/weather/", "/reel/"
        ]
        return (
            "/news/" in url and
            not any(p in url.lower() for p in exclude_patterns)
        )

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        """Faz scraping de um artigo da BBC"""
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            # Título
            title = None
            title_selectors = [
                'h1#main-heading',
                'h1[data-testid="headline"]',
                '.story-body h1',
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
                'article[data-testid="article-body"]',
                'article .ssrcss-pv1rh6-ArticleWrapper',
                '.story-body__inner',
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
            author_element = soup.select_one('[class*="byline"], [class*="contributor"]')
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


class BBCPortugueseScraper(BaseScraper):
    """Scraper para coleta de notícias da BBC Brasil"""

    SOURCE_KEY = "bbc_portuguese"
    SOURCE_NAME = "BBC Brasil"
    BASE_URL = "https://www.bbc.com/portuguese"
    LANGUAGE = "pt-br"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        """Obtém URLs de artigos da BBC Brasil"""
        urls = []

        try:
            sections = [
                self.BASE_URL,
                f"{self.BASE_URL}/internacional",
                f"{self.BASE_URL}/brasil"
            ]

            for section_url in sections:
                html = self._fetch_page(section_url)
                if not html:
                    continue

                soup = self._parse_html(html)

                links = soup.select('a[href*="/portuguese/"]')
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
        exclude_patterns = ["/videos/", "/av/", "/topics/"]
        return (
            "/portuguese/" in url and
            not any(p in url.lower() for p in exclude_patterns) and
            any(c.isdigit() for c in url)
        )

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        """Faz scraping de um artigo da BBC Brasil"""
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            # Título
            title = None
            title_element = soup.select_one('h1')
            if title_element:
                title = title_element.get_text(strip=True)

            if not title:
                return None

            # Conteúdo
            article = soup.select_one('article')
            content = ""
            if article:
                paragraphs = article.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs)

            if not content:
                content = self._clean_content(html)

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
                published_at=published_at,
                language=self.LANGUAGE,
                source_key=self.SOURCE_KEY
            )

        except Exception as e:
            self.logger.error(f"Erro ao fazer scraping de {url}: {e}")
            return None
