"""Discovery service for website crawling and page discovery."""

import asyncio
import fnmatch
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..db_models.discovered_page import DiscoveredPage, PageStatus
from ..db_models.path_rule import PathRule, RuleType


class DiscoveryService:
    """Service for discovering pages on a website before ingestion."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "EverLeagues-Tax-KB-Bot/1.0 (Discovery Mode)"
                },
            )
        return self.http_client

    async def close(self):
        """Close HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    async def discover_pages(
        self,
        scrape_url_id: UUID,
        base_url: str,
        max_depth: int = 3,
        max_pages: int = 500,
        respect_robots: bool = True,
        delay_seconds: float = 1.0,
        path_rules: Optional[List[PathRule]] = None,
    ) -> List[DiscoveredPage]:
        """
        Crawl a website and discover pages without ingesting content.
        
        Args:
            scrape_url_id: ID of the parent ScrapeUrl
            base_url: Base URL to start crawling from
            max_depth: Maximum depth to crawl
            max_pages: Maximum number of pages to discover
            respect_robots: Whether to respect robots.txt
            delay_seconds: Delay between requests
            path_rules: List of path rules to apply
            
        Returns:
            List of discovered pages
        """
        discovered: List[DiscoveredPage] = []
        visited: Set[str] = set()
        queue: List[Tuple[str, int, Optional[UUID]]] = [(base_url, 0, None)]
        base_parsed = urlparse(base_url)
        base_domain = base_parsed.netloc

        # Parse robots.txt if needed
        disallowed_paths: Set[str] = set()
        if respect_robots:
            disallowed_paths = await self._parse_robots_txt(base_url)

        client = await self._get_client()

        while queue and len(discovered) < max_pages:
            url, depth, parent_id = queue.pop(0)
            
            if url in visited:
                continue
            
            # Normalize URL
            parsed = urlparse(url)
            if parsed.netloc != base_domain:
                continue  # Skip external links
                
            path = parsed.path or "/"
            
            # Check if blocked by robots.txt
            if respect_robots and self._is_path_disallowed(path, disallowed_paths):
                continue
                
            # Check if blocked by path rules
            if path_rules and self._is_path_blocked(path, path_rules):
                continue
            
            visited.add(url)
            
            if depth > max_depth:
                continue

            try:
                # Make HEAD request first to check content type
                head_response = await client.head(url)
                content_type = head_response.headers.get("content-type", "")
                
                # Create discovered page record
                page = DiscoveredPage(
                    scrape_url_id=scrape_url_id,
                    url=url,
                    path=path,
                    depth=depth,
                    content_type=content_type.split(";")[0].strip(),
                    http_status=head_response.status_code,
                    discovered_at=datetime.now(timezone.utc),
                    status=PageStatus.PENDING,
                    parent_page_id=parent_id,
                )
                
                # If HTML, fetch and parse for links
                if "text/html" in content_type:
                    response = await client.get(url)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")
                        
                        # Get page title
                        title_tag = soup.find("title")
                        if title_tag:
                            page.title = title_tag.get_text()[:500]
                        
                        # Find all links
                        for link in soup.find_all("a", href=True):
                            href = link["href"]
                            absolute_url = urljoin(url, href)
                            
                            # Clean URL (remove fragments)
                            parsed_link = urlparse(absolute_url)
                            clean_url = f"{parsed_link.scheme}://{parsed_link.netloc}{parsed_link.path}"
                            if parsed_link.query:
                                clean_url += f"?{parsed_link.query}"
                            
                            if clean_url not in visited:
                                queue.append((clean_url, depth + 1, page.id))
                
                # Check if this is a document (PDF, DOC, etc.)
                doc_extensions = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt"}
                page.is_document = any(path.lower().endswith(ext) for ext in doc_extensions)
                
                self.db.add(page)
                discovered.append(page)
                
                # Delay between requests
                await asyncio.sleep(delay_seconds)
                
            except httpx.RequestError as e:
                # Log error but continue crawling
                page = DiscoveredPage(
                    scrape_url_id=scrape_url_id,
                    url=url,
                    path=path,
                    depth=depth,
                    http_status=0,
                    discovered_at=datetime.now(timezone.utc),
                    status=PageStatus.PENDING,
                    parent_page_id=parent_id,
                )
                self.db.add(page)
                discovered.append(page)

        await self.db.commit()
        return discovered

    async def _parse_robots_txt(self, base_url: str) -> Set[str]:
        """
        Parse robots.txt and return set of disallowed paths.
        
        Args:
            base_url: Base URL of the website
            
        Returns:
            Set of disallowed paths
        """
        disallowed: Set[str] = set()
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        try:
            client = await self._get_client()
            response = await client.get(robots_url)
            
            if response.status_code == 200:
                current_agent = None
                for line in response.text.split("\n"):
                    line = line.strip().lower()
                    
                    if line.startswith("user-agent:"):
                        agent = line.split(":", 1)[1].strip()
                        current_agent = agent
                    elif line.startswith("disallow:") and current_agent in ("*", "everleagues"):
                        path = line.split(":", 1)[1].strip()
                        if path:
                            disallowed.add(path)
                            
        except httpx.RequestError:
            pass  # No robots.txt or error fetching
            
        return disallowed

    def _is_path_disallowed(self, path: str, disallowed_paths: Set[str]) -> bool:
        """Check if path is disallowed by robots.txt."""
        for pattern in disallowed_paths:
            if pattern.endswith("*"):
                if path.startswith(pattern[:-1]):
                    return True
            elif path.startswith(pattern):
                return True
        return False

    def _is_path_blocked(self, path: str, rules: List[PathRule]) -> bool:
        """
        Check if path is blocked by any path rule.
        
        Args:
            path: URL path to check
            rules: List of path rules
            
        Returns:
            True if path is blocked
        """
        # Sort by priority (higher first)
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            matches = False
            
            if rule.is_regex:
                try:
                    flags = 0 if rule.case_sensitive else re.IGNORECASE
                    if re.match(rule.pattern, path, flags):
                        matches = True
                except re.error:
                    pass
            elif rule.is_glob:
                pattern = rule.pattern if rule.case_sensitive else rule.pattern.lower()
                check_path = path if rule.case_sensitive else path.lower()
                if fnmatch.fnmatch(check_path, pattern):
                    matches = True
            else:
                # Exact match or prefix match
                pattern = rule.pattern if rule.case_sensitive else rule.pattern.lower()
                check_path = path if rule.case_sensitive else path.lower()
                if check_path.startswith(pattern):
                    matches = True
            
            if matches:
                return rule.rule_type == RuleType.BLOCK
        
        return False

    async def build_site_tree(self, scrape_url_id: UUID) -> Dict:
        """
        Build a hierarchical tree structure of discovered paths.
        
        Args:
            scrape_url_id: ID of the parent ScrapeUrl
            
        Returns:
            Dictionary representing the site tree
        """
        # Fetch all discovered pages for this URL
        result = await self.db.execute(
            select(DiscoveredPage)
            .where(DiscoveredPage.scrape_url_id == scrape_url_id)
            .order_by(DiscoveredPage.path)
        )
        pages = result.scalars().all()
        
        # Build tree structure
        tree: Dict = {"path": "/", "children": {}, "pages": [], "depth": 0}
        
        for page in pages:
            path_parts = [p for p in page.path.split("/") if p]
            current = tree
            
            for i, part in enumerate(path_parts):
                if part not in current["children"]:
                    current["children"][part] = {
                        "path": "/" + "/".join(path_parts[:i+1]),
                        "children": {},
                        "pages": [],
                        "depth": i + 1,
                    }
                current = current["children"][part]
            
            current["pages"].append({
                "id": str(page.id),
                "url": page.url,
                "title": page.title,
                "status": page.status.value,
                "content_type": page.content_type,
                "is_document": page.is_document,
            })
        
        return self._tree_to_list(tree)

    def _tree_to_list(self, node: Dict) -> Dict:
        """Convert tree with dict children to tree with list children."""
        return {
            "path": node["path"],
            "depth": node["depth"],
            "pages": node["pages"],
            "page_count": len(node["pages"]) + sum(
                self._count_pages(child) for child in node["children"].values()
            ),
            "children": [
                self._tree_to_list(child) 
                for child in node["children"].values()
            ],
        }

    def _count_pages(self, node: Dict) -> int:
        """Count total pages in a subtree."""
        return len(node["pages"]) + sum(
            self._count_pages(child) for child in node["children"].values()
        )

    async def get_discovery_stats(self, scrape_url_id: UUID) -> Dict:
        """
        Get statistics about discovered pages.
        
        Args:
            scrape_url_id: ID of the parent ScrapeUrl
            
        Returns:
            Dictionary with discovery statistics
        """
        # Count by status
        status_counts = await self.db.execute(
            select(DiscoveredPage.status, func.count(DiscoveredPage.id))
            .where(DiscoveredPage.scrape_url_id == scrape_url_id)
            .group_by(DiscoveredPage.status)
        )
        
        stats = {
            "total": 0,
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "ingested": 0,
            "documents": 0,
        }
        
        for status, count in status_counts:
            stats[status.value] = count
            stats["total"] += count
        
        # Count documents
        doc_count = await self.db.execute(
            select(func.count(DiscoveredPage.id))
            .where(DiscoveredPage.scrape_url_id == scrape_url_id)
            .where(DiscoveredPage.is_document == True)
        )
        stats["documents"] = doc_count.scalar() or 0
        
        return stats
