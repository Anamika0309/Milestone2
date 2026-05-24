"""
Phase 1.1 - Fetcher Module (Standalone Phase Copy)
Purpose: Pull 5 Groww HTML pages with ETag support
Tech Stack: httpx + Playwright (fallback)
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

# Try to import Playwright with fallback
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Try relative package imports, fallback to direct config loader
try:
    from ..config.sources import load_sources
    from ..config import validate_url_whitelist
except (ImportError, ValueError):
    try:
        from mf_faq.config.sources import load_sources
        from mf_faq.config import validate_url_whitelist
    except ImportError:
        # Standalone copies fallback loading from phase_0 folder
        import yaml
        def load_sources(config_dir: str = None) -> dict:
            if config_dir is None:
                # Try finding in phases/phase_0/
                config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'phase_0')
                if not os.path.exists(config_dir):
                    config_dir = os.path.join(os.path.dirname(__file__), '..', 'phase_0')
            sources_file = os.path.join(config_dir, 'sources.yaml')
            try:
                with open(sources_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception:
                return {'schemes': []}
        
        def validate_url_whitelist(urls: list) -> bool:
            try:
                sources = load_sources()
                allowed_urls = []
                for scheme in sources.get('schemes', []):
                    for source in scheme.get('sources', []):
                        if source.get('url'):
                            allowed_urls.append(source.get('url'))
                return all(url in allowed_urls for url in urls)
            except Exception:
                return False

logger = logging.getLogger(__name__)


class FetchResult:
    """Result of a single URL fetch operation"""
    
    def __init__(self, url: str, success: bool, **kwargs):
        self.url = url
        self.success = success
        self.http_status = kwargs.get('http_status')
        self.etag = kwargs.get('etag')
        self.content_hash = kwargs.get('content_hash')
        self.fetched_at = kwargs.get('fetched_at', datetime.now(timezone.utc).isoformat())
        self.fetcher_kind = kwargs.get('fetcher_kind', 'httpx')
        self.error_message = kwargs.get('error_message')
        self.content_length = kwargs.get('content_length', 0)
        self.robots_allowed = kwargs.get('robots_allowed', True)


class Fetcher:
    """Main fetcher class for ingesting Groww HTML pages"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'phase_0')
        self.sources = load_sources(self.config_dir)
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'raw')
        self.user_agent = 'MF-FAQ-Assistant/1.0 (https://github.com/mf-faq-assistant)'
        
        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={'User-Agent': self.user_agent},
            follow_redirects=False  # We handle redirects manually
        )
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def check_robots_txt(self, base_url: str) -> bool:
        """Check robots.txt compliance for the given base URL"""
        try:
            parsed_url = urlparse(base_url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            response = await self.client.get(robots_url)
            if response.status_code == 200:
                rp = RobotFileParser()
                rp.parse(response.text)
                rp.set_url(base_url)
                
                # Check if our user agent is allowed
                return rp.can_fetch(self.user_agent, base_url)
            
            # If robots.txt doesn't exist, assume we're allowed
            return True
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {base_url}: {e}")
            # If we can't check robots.txt, proceed with caution
            return True
    
    async def fetch_with_httpx(self, url: str, etag: Optional[str] = None) -> FetchResult:
        """Fetch URL using httpx with ETag support"""
        try:
            headers = {}
            if etag:
                headers['If-None-Match'] = etag
            
            response = await self.client.get(url, headers=headers)
            
            # Handle 304 Not Modified
            if response.status_code == 304:
                logger.info(f"Content unchanged for {url} (ETag: {etag})")
                return FetchResult(url, success=True, http_status=304, etag=etag, fetched_at=datetime.now(timezone.utc).isoformat())
            
            # Handle successful responses
            if response.status_code == 200:
                content = response.content
                content_hash = hashlib.sha256(content).hexdigest()
                
                result = FetchResult(
                    url=url,
                    success=True,
                    http_status=response.status_code,
                    etag=response.headers.get('ETag'),
                    content_hash=content_hash,
                    content_length=len(content),
                    robots_allowed=True
                )
                
                # Save content and metadata
                await self.save_fetch_result(result, content)
                return result
            
            # Handle client errors
            elif 400 <= response.status_code < 500:
                logger.error(f"Client error {response.status_code} for {url}")
                return FetchResult(
                    url=url,
                    success=False,
                    http_status=response.status_code,
                    error_message=f"HTTP {response.status_code}: {response.text[:200]}"
                )
            
            # Handle server errors
            else:
                logger.error(f"Server error {response.status_code} for {url}")
                return FetchResult(
                    url=url,
                    success=False,
                    http_status=response.status_code,
                    error_message=f"HTTP {response.status_code}: Server error"
                )
                
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching {url}")
            return FetchResult(url, success=False, error_message="Request timeout")
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return FetchResult(url, success=False, error_message=str(e))
    
    async def fetch_with_playwright(self, url: str) -> FetchResult:
        """Fallback fetcher using Playwright for JavaScript-heavy content"""
        if not PLAYWRIGHT_AVAILABLE:
            return FetchResult(url, success=False, error_message="Playwright not installed/available", fetcher_kind='playwright')
            
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set user agent
                await page.set_extra_http_headers({'User-Agent': self.user_agent})
                
                # Navigate to URL
                response = await page.goto(url, wait_until='networkidle', timeout=30000)
                
                if response and response.status == 200:
                    content = await page.content()
                    content_hash = hashlib.sha256(content.encode()).hexdigest()
                    
                    result = FetchResult(
                        url=url,
                        success=True,
                        http_status=response.status,
                        content_hash=content_hash,
                        content_length=len(content),
                        fetcher_kind='playwright',
                        robots_allowed=True
                    )
                    
                    await self.save_fetch_result(result, content.encode('utf-8'))
                    await browser.close()
                    return result
                else:
                    await browser.close()
                    return FetchResult(
                        url=url,
                        success=False,
                        http_status=response.status if response else None,
                        error_message=f"Playwright error: {response.status if response else 'No response'}",
                        fetcher_kind='playwright'
                    )
                    
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return FetchResult(url, success=False, error_message=f"Playwright error: {str(e)}", fetcher_kind='playwright')
    
    async def save_fetch_result(self, result: FetchResult, content: bytes):
        """Save fetched content and metadata to disk"""
        try:
            # Extract scheme ID from URL
            scheme_id = self.get_scheme_id_from_url(result.url)
            if not scheme_id:
                logger.error(f"Could not determine scheme ID for URL: {result.url}")
                return
            
            # Create scheme directory
            scheme_dir = os.path.join(self.output_dir, scheme_id)
            os.makedirs(scheme_dir, exist_ok=True)
            
            # Generate timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            
            # Save HTML content
            html_path = os.path.join(scheme_dir, f"{timestamp}.html")
            with open(html_path, 'wb') as f:
                f.write(content)
            
            # Save metadata
            metadata = {
                'url': result.url,
                'fetched_at': result.fetched_at,
                'http_status': result.http_status,
                'etag': result.etag,
                'content_hash_raw': result.content_hash,
                'content_length': result.content_length,
                'fetcher_kind': result.fetcher_kind,
                'robots_allowed': result.robots_allowed
            }
            
            meta_path = os.path.join(scheme_dir, f"{timestamp}.meta.json")
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved fetch result for {scheme_id}: {html_path}")
            
        except Exception as e:
            logger.error(f"Error saving fetch result: {e}")
    
    def get_scheme_id_from_url(self, url: str) -> Optional[str]:
        """Extract scheme ID from URL using sources configuration"""
        for scheme in self.sources.get('schemes', []):
            for source in scheme.get('sources', []):
                if source.get('url') == url:
                    return scheme.get('id')
        return None
    
    async def fetch_single_url(self, url: str, use_playwright_fallback: bool = True) -> FetchResult:
        """Fetch a single URL with optional Playwright fallback"""
        # Check robots.txt first
        robots_allowed = await self.check_robots_txt(url)
        if not robots_allowed:
            logger.error(f"Robots.txt disallows access to {url}")
            return FetchResult(url, success=False, error_message="Robots.txt disallowed")
        
        # Load previous ETag if exists
        etag = await self.load_previous_etag(url)
        
        # Try httpx first
        result = await self.fetch_with_httpx(url, etag)
        
        # If httpx fails and fallback is enabled, try Playwright
        if not result.success and use_playwright_fallback:
            logger.info(f"HTTPx failed for {url}, trying Playwright fallback")
            result = await self.fetch_with_playwright(url)
        
        # Check for redirects and alert
        if result.http_status in [301, 302]:
            logger.warning(f"Redirect detected for {url} - manual review required")
        
        return result
    
    async def load_previous_etag(self, url: str) -> Optional[str]:
        """Load previous ETag from metadata file"""
        try:
            scheme_id = self.get_scheme_id_from_url(url)
            if not scheme_id:
                return None
            
            scheme_dir = os.path.join(self.output_dir, scheme_id)
            if not os.path.exists(scheme_dir):
                return None
            
            # Find most recent meta file
            meta_files = [f for f in os.listdir(scheme_dir) if f.endswith('.meta.json')]
            if not meta_files:
                return None
            
            meta_files.sort(reverse=True)
            latest_meta = meta_files[0]
            meta_path = os.path.join(scheme_dir, latest_meta)
            
            with open(meta_path, 'r') as f:
                metadata = json.load(f)
                return metadata.get('etag')
                
        except Exception as e:
            logger.warning(f"Error loading previous ETag for {url}: {e}")
            return None
    
    async def fetch_all(self, use_playwright_fallback: bool = True) -> List[FetchResult]:
        """Fetch all URLs from sources configuration"""
        logger.info("Starting fetch of all configured URLs")
        
        results = []
        urls_to_fetch = []
        
        # Collect all URLs from sources
        for scheme in self.sources.get('schemes', []):
            for source in scheme.get('sources', []):
                url = source.get('url')
                if url and validate_url_whitelist([url]):
                    urls_to_fetch.append(url)
        
        # Fetch URLs concurrently with rate limiting
        semaphore = asyncio.Semaphore(2)  # Max 2 concurrent requests
        
        async def fetch_with_semaphore(url):
            async with semaphore:
                await asyncio.sleep(1)  # Rate limiting: 1 second between requests
                return await self.fetch_single_url(url, use_playwright_fallback)
        
        tasks = [fetch_with_semaphore(url) for url in urls_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        successful_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception during fetch: {result}")
            elif isinstance(result, FetchResult):
                successful_results.append(result)
                if result.success:
                    logger.info(f"Successfully fetched {result.url}")
                else:
                    logger.error(f"Failed to fetch {result.url}: {result.error_message}")
        
        logger.info(f"Fetch completed. Success: {len([r for r in successful_results if r.success])}/{len(successful_results)}")
        return successful_results
    
    def get_health_status(self) -> Dict:
        """Get overall health status of the fetcher"""
        try:
            total_schemes = len(self.sources.get('schemes', []))
            health_report = {
                'total_schemes': total_schemes,
                'successful_fetches': 0,
                'failed_fetches': 0,
                'last_fetch_time': None,
                'health': 'unknown'
            }
            
            # Check each scheme directory
            for scheme in self.sources.get('schemes', []):
                scheme_id = scheme.get('id')
                scheme_dir = os.path.join(self.output_dir, scheme_id)
                
                if os.path.exists(scheme_dir):
                    # Check for recent successful fetches
                    meta_files = [f for f in os.listdir(scheme_dir) if f.endswith('.meta.json')]
                    if meta_files:
                        meta_files.sort(reverse=True)
                        latest_meta = meta_files[0]
                        meta_path = os.path.join(scheme_dir, latest_meta)
                        
                        with open(meta_path, 'r') as f:
                            metadata = json.load(f)
                            
                        if metadata.get('http_status') == 200:
                            health_report['successful_fetches'] += 1
                            if not health_report['last_fetch_time'] or metadata['fetched_at'] > health_report['last_fetch_time']:
                                health_report['last_fetch_time'] = metadata['fetched_at']
                        else:
                            health_report['failed_fetches'] += 1
                else:
                    health_report['failed_fetches'] += 1
            
            # Determine overall health
            if health_report['successful_fetches'] == total_schemes:
                health_report['health'] = 'ok'
            elif health_report['successful_fetches'] > 0:
                health_report['health'] = 'partial'
            else:
                health_report['health'] = 'failed'
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {'health': 'error', 'error': str(e)}


# CLI interface for standalone execution
async def main():
    """CLI interface for the fetcher"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch HTML content from Groww URLs')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--use-playwright', action='store_true', help='Force Playwright usage')
    parser.add_argument('--dry-run', action='store_true', help='Check robots.txt only')
    
    args = parser.parse_args()
    
    fetcher = Fetcher(args.config_dir)
    
    if args.dry_run:
        # Just check robots.txt compliance
        for scheme in fetcher.sources.get('schemes', []):
            for source in scheme.get('sources', []):
                url = source.get('url')
                if url:
                    allowed = await fetcher.check_robots_txt(url)
                    print(f"Robots.txt check for {url}: {'ALLOWED' if allowed else 'DISALLOWED'}")
    else:
        # Perform actual fetching
        results = await fetcher.fetch_all(use_playwright_fallback=args.use_playwright)
        
        # Print summary
        health = fetcher.get_health_status()
        print(f"\nFetch Summary:")
        print(f"Total URLs: {health['total_schemes']}")
        print(f"Successful: {health['successful_fetches']}")
        print(f"Failed: {health['failed_fetches']}")
        print(f"Health: {health['health']}")


if __name__ == "__main__":
    asyncio.run(main())
