"""
Tax Document URL Scraper

This script scrapes tax documents from URLs, extracting text content from both
HTML pages and PDF files. It supports rate limiting, PDF text extraction, and
can follow links to find and download PDFs.

Features:
- Scrapes HTML pages and extracts text content
- Downloads and extracts text from PDF files
- Finds PDF links on pages and can scrape them
- Rate limiting to respect server resources
- Extracts metadata (title, content, URLs, etc.)
- Saves results to JSON format

Dependencies:
    pip install requests beautifulsoup4 PyPDF2 pdfplumber

Usage:
    # Basic usage
    python scrape_tax_urls.py https://www.irs.gov/forms-pubs
    
    # With options
    python scrape_tax_urls.py https://www.irs.gov/forms-pubs \\
        --follow-pdfs \\
        --max-pages 10 \\
        --delay 2.0 \\
        --rpm 30 \\
        --output results.json
    
    # Programmatic usage
    from scrape_tax_urls import TaxDocumentScraper
    
    scraper = TaxDocumentScraper(delay=2.0, requests_per_minute=30)
    documents = scraper.scrape(
        url="https://www.irs.gov/forms-pubs",
        follow_pdf_links=True,
        max_pages=10
    )
    scraper.save_results("output.json")
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import time
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sys
import os

# Optional dependencies (install if needed)
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️  PyPDF2 not installed. PDF text extraction will be limited.")
    print("   Install with: pip install PyPDF2")

try:
    import pdfplumber
    PDFPLUMBER_SUPPORT = True
except ImportError:
    PDFPLUMBER_SUPPORT = False

class TaxDocumentScraper:
    """Scraper for tax documents from URLs"""
    
    def __init__(
        self,
        delay: float = 2.0,
        requests_per_minute: int = 30,
        timeout: int = 30,
        max_depth: int = 2,
        user_agent: Optional[str] = None
    ):
        """
        Initialize the scraper
        
        Args:
            delay: Delay between requests in seconds
            requests_per_minute: Maximum requests per minute
            timeout: Request timeout in seconds
            max_depth: Maximum depth for crawling links
            user_agent: Custom user agent string
        """
        self.delay = delay
        self.requests_per_minute = requests_per_minute
        self.timeout = timeout
        self.max_depth = max_depth
        self.session = requests.Session()
        
        # Set user agent
        default_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.session.headers.update({
            'User-Agent': user_agent or default_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        self.scraped_urls = set()
        self.documents = []
        self.request_count = 0
        self.start_time = time.time()
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        self.request_count += 1
        
        # Check requests per minute
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            current_rpm = (self.request_count / elapsed) * 60
            if current_rpm >= self.requests_per_minute:
                sleep_time = 60 - elapsed
                if sleep_time > 0:
                    print(f"⏳ Rate limit reached. Sleeping for {sleep_time:.1f} seconds...")
                    time.sleep(sleep_time)
                    self.start_time = time.time()
                    self.request_count = 0
        
        # Apply delay between requests
        if self.delay > 0:
            time.sleep(self.delay)
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc
    
    def _is_pdf_url(self, url: str) -> bool:
        """Check if URL points to a PDF"""
        return url.lower().endswith('.pdf') or 'pdf' in url.lower()
    
    def _is_valid_url(self, url: str, base_url: str) -> bool:
        """Check if URL is valid for scraping"""
        parsed = urlparse(url)
        
        # Skip non-http(s) URLs
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Skip common non-content URLs
        skip_patterns = [
            r'\.(jpg|jpeg|png|gif|svg|css|js|ico|woff|woff2|ttf|eot)$',
            r'#',
            r'mailto:',
            r'tel:',
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        return True
    
    def _extract_text_from_pdf(self, pdf_url: str) -> Optional[str]:
        """Extract text from PDF URL"""
        try:
            response = self.session.get(pdf_url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Save to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            text_content = []
            
            # Try pdfplumber first (better text extraction)
            if PDFPLUMBER_SUPPORT:
                try:
                    with pdfplumber.open(tmp_path) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                text_content.append(text)
                except Exception as e:
                    print(f"⚠️  pdfplumber extraction failed: {e}")
            
            # Fallback to PyPDF2
            if not text_content and PDF_SUPPORT:
                try:
                    with open(tmp_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        for page in pdf_reader.pages:
                            text = page.extract_text()
                            if text:
                                text_content.append(text)
                except Exception as e:
                    print(f"⚠️  PyPDF2 extraction failed: {e}")
            
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            return '\n\n'.join(text_content) if text_content else None
            
        except Exception as e:
            print(f"❌ Error extracting PDF text from {pdf_url}: {e}")
            return None
    
    def _extract_text_from_html(self, html_content: str, url: str) -> Dict[str, any]:
        """Extract text and metadata from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Extract title
        title = None
        if soup.title:
            title = soup.title.get_text().strip()
        elif soup.find('h1'):
            title = soup.find('h1').get_text().strip()
        elif soup.find('meta', property='og:title'):
            title = soup.find('meta', property='og:title').get('content', '').strip()
        
        # Extract main content
        # Try to find main content area
        main_content = None
        for selector in ['main', 'article', '[role="main"]', '.content', '#content', 'body']:
            element = soup.select_one(selector)
            if element:
                main_content = element.get_text(separator='\n', strip=True)
                break
        
        if not main_content:
            main_content = soup.get_text(separator='\n', strip=True)
        
        # Clean up text
        lines = [line.strip() for line in main_content.split('\n') if line.strip()]
        content = '\n'.join(lines)
        
        # Extract meta description
        description = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '').strip()
        elif soup.find('meta', property='og:description'):
            description = soup.find('meta', property='og:description').get('content', '').strip()
        
        # Extract all links (for finding PDFs and related pages)
        links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            link_text = link.get_text().strip()
            if href:
                absolute_url = urljoin(url, href)
                links.append({
                    'url': absolute_url,
                    'text': link_text,
                    'is_pdf': self._is_pdf_url(absolute_url)
                })
        
        # Extract PDF links
        pdf_links = [link['url'] for link in links if link['is_pdf']]
        
        return {
            'title': title or 'Untitled',
            'content': content,
            'excerpt': description or content[:200] + '...' if len(content) > 200 else content,
            'links': links,
            'pdf_links': pdf_links
        }
    
    def _scrape_url(self, url: str, depth: int = 0) -> Optional[Dict]:
        """Scrape a single URL"""
        if depth > self.max_depth:
            return None
        
        if url in self.scraped_urls:
            return None
        
        if not self._is_valid_url(url, url):
            return None
        
        self.scraped_urls.add(url)
        self._rate_limit()
        
        print(f"📄 Scraping: {url} (depth: {depth})")
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Handle PDFs
            if 'pdf' in content_type or self._is_pdf_url(url):
                print(f"  📑 Detected PDF document")
                text_content = self._extract_text_from_pdf(url)
                
                if text_content:
                    # Extract filename from URL
                    filename = os.path.basename(urlparse(url).path) or 'document.pdf'
                    
                    return {
                        'url': url,
                        'sourceUrl': url,
                        'sourceDomain': self._get_domain(url),
                        'title': filename.replace('.pdf', '').replace('_', ' ').replace('-', ' '),
                        'content': text_content,
                        'excerpt': text_content[:200] + '...' if len(text_content) > 200 else text_content,
                        'documentName': filename,
                        'docType': 'publication',
                        'lastCrawled': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'parsingQuality': 'ok' if len(text_content) > 100 else 'partial'
                    }
                else:
                    print(f"  ⚠️  Could not extract text from PDF")
                    return None
            
            # Handle HTML
            elif 'html' in content_type:
                print(f"  🌐 Detected HTML page")
                html_data = self._extract_text_from_html(response.text, url)
                
                document = {
                    'url': url,
                    'sourceUrl': url,
                    'sourceDomain': self._get_domain(url),
                    'title': html_data['title'],
                    'content': html_data['content'],
                    'excerpt': html_data['excerpt'],
                    'lastCrawled': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'parsingQuality': 'ok' if len(html_data['content']) > 100 else 'partial',
                    'pdf_links': html_data['pdf_links']
                }
                
                # If page has PDF links and content is short, might be a directory page
                if len(html_data['pdf_links']) > 0 and len(html_data['content']) < 500:
                    document['docType'] = 'other'
                    document['category'] = 'directory'
                else:
                    document['docType'] = 'publication'
                
                return document
            
            else:
                print(f"  ⚠️  Unsupported content type: {content_type}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"  ❌ Timeout error for {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Request error for {url}: {e}")
            return None
        except Exception as e:
            print(f"  ❌ Error scraping {url}: {e}")
            return None
    
    def scrape(
        self,
        url: str,
        follow_links: bool = False,
        follow_pdf_links: bool = True,
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """
        Scrape documents from a URL
        
        Args:
            url: Starting URL to scrape
            follow_links: Whether to follow links on the page
            follow_pdf_links: Whether to scrape PDFs found on the page
            max_pages: Maximum number of pages to scrape
        
        Returns:
            List of scraped documents
        """
        print(f"\n🚀 Starting scrape of: {url}\n")
        print(f"   Follow links: {follow_links}")
        print(f"   Follow PDF links: {follow_pdf_links}")
        print(f"   Max pages: {max_pages or 'unlimited'}\n")
        
        self.documents = []
        self.scraped_urls = set()
        self.request_count = 0
        self.start_time = time.time()
        
        # Scrape initial URL
        initial_doc = self._scrape_url(url, depth=0)
        if initial_doc:
            self.documents.append(initial_doc)
            
            # If follow_pdf_links and page has PDF links, scrape them
            if follow_pdf_links and 'pdf_links' in initial_doc:
                pdf_links = initial_doc.get('pdf_links', [])
                print(f"\n📚 Found {len(pdf_links)} PDF link(s) on page")
                
                for pdf_url in pdf_links[:max_pages] if max_pages else pdf_links:
                    if len(self.documents) >= max_pages if max_pages else False:
                        break
                    
                    pdf_doc = self._scrape_url(pdf_url, depth=1)
                    if pdf_doc:
                        self.documents.append(pdf_doc)
        
        print(f"\n✅ Scraping complete!")
        print(f"   Total documents scraped: {len(self.documents)}")
        print(f"   Total URLs visited: {len(self.scraped_urls)}")
        
        return self.documents
    
    def save_results(self, filename: str = None):
        """Save scraped results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'scraped_documents_{timestamp}.json'
        
        import json
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")
        return filename


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape tax documents from URLs')
    parser.add_argument('url', help='URL to scrape')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests (seconds)')
    parser.add_argument('--rpm', type=int, default=30, help='Maximum requests per minute')
    parser.add_argument('--follow-pdfs', action='store_true', help='Follow and scrape PDF links found on page')
    parser.add_argument('--max-pages', type=int, help='Maximum number of pages to scrape')
    parser.add_argument('--output', type=str, help='Output JSON file path')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    
    args = parser.parse_args()
    
    # Create scraper
    scraper = TaxDocumentScraper(
        delay=args.delay,
        requests_per_minute=args.rpm,
        timeout=args.timeout
    )
    
    # Scrape
    documents = scraper.scrape(
        url=args.url,
        follow_links=False,
        follow_pdf_links=args.follow_pdfs,
        max_pages=args.max_pages
    )
    
    # Display results
    print("\n" + "=" * 80)
    print("SCRAPED DOCUMENTS SUMMARY")
    print("=" * 80)
    
    for i, doc in enumerate(documents, 1):
        print(f"\n{i}. {doc.get('title', 'Untitled')}")
        print(f"   URL: {doc.get('url', 'N/A')}")
        print(f"   Domain: {doc.get('sourceDomain', 'N/A')}")
        print(f"   Content length: {len(doc.get('content', ''))} characters")
        print(f"   Type: {doc.get('docType', 'unknown')}")
        print(f"   Quality: {doc.get('parsingQuality', 'unknown')}")
    
    # Save results
    if documents:
        output_file = args.output or scraper.save_results()
        print(f"\n✅ Scraped {len(documents)} document(s)")
        print(f"📁 Saved to: {output_file}")
    else:
        print("\n⚠️  No documents were scraped")


if __name__ == "__main__":
    main()

