"""
Scrapers para fontes de análise geopolítica
Foreign Affairs, CSIS, CFR, Crisis Group, RAND
"""
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

from .base_scraper import BaseScraper, ScrapedArticle


class ForeignAffairsScraper(BaseScraper):
    """Scraper para Foreign Affairs"""

    SOURCE_KEY = "foreignaffairs"
    SOURCE_NAME = "Foreign Affairs"
    BASE_URL = "https://www.foreignaffairs.com"
    LANGUAGE = "en"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        urls = []
        try:
            sections = [
                f"{self.BASE_URL}/regions",
                f"{self.BASE_URL}/topics/security",
                f"{self.BASE_URL}/topics/economics"
            ]

            for section_url in sections:
                html = self._fetch_page(section_url)
                if not html:
                    continue

                soup = self._parse_html(html)
                links = soup.select('a[href*="/articles/"]')

                for link in links:
                    href = link.get("href")
                    if href and "/articles/" in href:
                        full_url = self._resolve_url(href)
                        if full_url not in urls:
                            urls.append(full_url)

        except Exception as e:
            self.logger.error(f"Erro ao obter URLs: {e}")

        return urls

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            title = None
            title_element = soup.select_one('h1, .article-header h1')
            if title_element:
                title = title_element.get_text(strip=True)

            if not title:
                return None

            content = ""
            article = soup.select_one('article, .article-body, .article-content')
            if article:
                paragraphs = article.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs)

            if not content:
                content = self._clean_content(html)

            author = None
            author_element = soup.select_one('[class*="author"], .byline')
            if author_element:
                author = author_element.get_text(strip=True)

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


class CSISScraper(BaseScraper):
    """Scraper para CSIS (Center for Strategic and International Studies)"""

    SOURCE_KEY = "csis"
    SOURCE_NAME = "CSIS"
    BASE_URL = "https://www.csis.org"
    LANGUAGE = "en"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        urls = []
        try:
            sections = [
                f"{self.BASE_URL}/analysis",
                f"{self.BASE_URL}/regions"
            ]

            for section_url in sections:
                html = self._fetch_page(section_url)
                if not html:
                    continue

                soup = self._parse_html(html)
                links = soup.select('a[href*="/analysis/"], a[href*="/commentary/"]')

                for link in links:
                    href = link.get("href")
                    if href:
                        full_url = self._resolve_url(href)
                        if full_url not in urls:
                            urls.append(full_url)

        except Exception as e:
            self.logger.error(f"Erro ao obter URLs: {e}")

        return urls

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            title = None
            title_element = soup.select_one('h1, .page-title')
            if title_element:
                title = title_element.get_text(strip=True)

            if not title:
                return None

            content = ""
            article = soup.select_one('.field--name-body, article, .content')
            if article:
                paragraphs = article.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs)

            if not content:
                content = self._clean_content(html)

            author = None
            author_element = soup.select_one('[class*="author"], .contributor-name')
            if author_element:
                author = author_element.get_text(strip=True)

            return ScrapedArticle(
                url=url,
                title=title,
                content=content,
                raw_content=html,
                author=author,
                language=self.LANGUAGE,
                source_key=self.SOURCE_KEY
            )

        except Exception as e:
            self.logger.error(f"Erro ao fazer scraping de {url}: {e}")
            return None


class CFRScraper(BaseScraper):
    """Scraper para Council on Foreign Relations"""

    SOURCE_KEY = "cfr"
    SOURCE_NAME = "Council on Foreign Relations"
    BASE_URL = "https://www.cfr.org"
    LANGUAGE = "en"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        urls = []
        try:
            html = self._fetch_page(f"{self.BASE_URL}/expert-analysis")
            if not html:
                return urls

            soup = self._parse_html(html)
            links = soup.select('a[href*="/article/"], a[href*="/backgrounder/"]')

            for link in links:
                href = link.get("href")
                if href:
                    full_url = self._resolve_url(href)
                    if full_url not in urls:
                        urls.append(full_url)

        except Exception as e:
            self.logger.error(f"Erro ao obter URLs: {e}")

        return urls

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            title = None
            title_element = soup.select_one('h1')
            if title_element:
                title = title_element.get_text(strip=True)

            if not title:
                return None

            content = ""
            article = soup.select_one('.body-content, article, .article-body')
            if article:
                paragraphs = article.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs)

            if not content:
                content = self._clean_content(html)

            author = None
            author_element = soup.select_one('[class*="author"], .byline')
            if author_element:
                author = author_element.get_text(strip=True)

            return ScrapedArticle(
                url=url,
                title=title,
                content=content,
                raw_content=html,
                author=author,
                language=self.LANGUAGE,
                source_key=self.SOURCE_KEY
            )

        except Exception as e:
            self.logger.error(f"Erro ao fazer scraping de {url}: {e}")
            return None


class CrisisGroupScraper(BaseScraper):
    """Scraper para International Crisis Group"""

    SOURCE_KEY = "crisisgroup"
    SOURCE_NAME = "Crisis Group"
    BASE_URL = "https://www.crisisgroup.org"
    LANGUAGE = "en"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        urls = []
        try:
            html = self._fetch_page(f"{self.BASE_URL}/latest-updates")
            if not html:
                return urls

            soup = self._parse_html(html)
            links = soup.select('a[href*="/crisiswatch/"], a[href*="/report/"], a[href*="/commentary/"]')

            for link in links:
                href = link.get("href")
                if href:
                    full_url = self._resolve_url(href)
                    if full_url not in urls:
                        urls.append(full_url)

        except Exception as e:
            self.logger.error(f"Erro ao obter URLs: {e}")

        return urls

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            title = None
            title_element = soup.select_one('h1')
            if title_element:
                title = title_element.get_text(strip=True)

            if not title:
                return None

            content = ""
            article = soup.select_one('.field--name-body, article, .content')
            if article:
                paragraphs = article.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs)

            if not content:
                content = self._clean_content(html)

            return ScrapedArticle(
                url=url,
                title=title,
                content=content,
                raw_content=html,
                language=self.LANGUAGE,
                source_key=self.SOURCE_KEY
            )

        except Exception as e:
            self.logger.error(f"Erro ao fazer scraping de {url}: {e}")
            return None


class RANDScraper(BaseScraper):
    """Scraper para RAND Corporation"""

    SOURCE_KEY = "rand"
    SOURCE_NAME = "RAND Corporation"
    BASE_URL = "https://www.rand.org"
    LANGUAGE = "en"

    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        urls = []
        try:
            sections = [
                f"{self.BASE_URL}/topics/international-affairs.html",
                f"{self.BASE_URL}/topics/national-security.html"
            ]

            for section_url in sections:
                html = self._fetch_page(section_url)
                if not html:
                    continue

                soup = self._parse_html(html)
                links = soup.select('a[href*="/commentary/"], a[href*="/blog/"], a[href*="/pubs/"]')

                for link in links:
                    href = link.get("href")
                    if href:
                        full_url = self._resolve_url(href)
                        if full_url not in urls:
                            urls.append(full_url)

        except Exception as e:
            self.logger.error(f"Erro ao obter URLs: {e}")

        return urls

    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        try:
            html = self._fetch_page(url)
            if not html:
                return None

            soup = self._parse_html(html)

            title = None
            title_element = soup.select_one('h1, .title')
            if title_element:
                title = title_element.get_text(strip=True)

            if not title:
                return None

            content = ""
            article = soup.select_one('.body-text, article, .content')
            if article:
                paragraphs = article.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs)

            if not content:
                content = self._clean_content(html)

            author = None
            author_element = soup.select_one('[class*="author"], .byline')
            if author_element:
                author = author_element.get_text(strip=True)

            return ScrapedArticle(
                url=url,
                title=title,
                content=content,
                raw_content=html,
                author=author,
                language=self.LANGUAGE,
                source_key=self.SOURCE_KEY
            )

        except Exception as e:
            self.logger.error(f"Erro ao fazer scraping de {url}: {e}")
            return None
