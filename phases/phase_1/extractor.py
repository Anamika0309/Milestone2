"""
Phase 1.2 - Extractor Module (Standalone Phase Copy)
Purpose: HTML → structured text with section anchors
Tech Stack: trafilatura + BeautifulSoup + CSS/XPath selectors
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

import trafilatura
from bs4 import BeautifulSoup
from bs4.element import Tag

# Try relative package imports, fallback to direct config loader
try:
    from ..config.sources import load_sources
except (ImportError, ValueError):
    try:
        from mf_faq.config.sources import load_sources
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

logger = logging.getLogger(__name__)


class ExtractedDoc:
    """Represents extracted document with sections"""
    
    def __init__(self, scheme_id: str, source_url: str, fetched_at: str, 
                 sections: List[Dict[str, str]], must_have_anchors: Dict[str, bool],
                 extraction_health: str = "ok"):
        self.scheme_id = scheme_id
        self.source_url = source_url
        self.fetched_at = fetched_at
        self.sections = sections
        self.must_have_anchors = must_have_anchors
        self.extraction_health = extraction_health


class Extractor:
    """Main extractor class for processing HTML content"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'phase_0')
        self.sources = load_sources(self.config_dir)
        self.input_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'raw')
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'processed')
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Must-have anchors for each scheme type
        self.must_have_anchors = {
            'all': [
                'Expense Ratio',
                'Exit Load', 
                'Scheme Details',
                'Minimum Investments',
                'Fund Manager',
                'Fund House',
                'Riskometer',
                'Benchmark',
                'About'
            ],
            'min_required': [
                'Expense Ratio',
                'Exit Load',
                'Scheme Details'
            ]
        }
    
    def extract_with_trafilatura(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract content using trafilatura for main body text"""
        try:
            # Use trafilatura for main content extraction
            extracted = trafilatura.extract(
                html_content,
                url=url,
                include_images=False,
                include_tables=True,
                include_formatting=False,
                with_metadata=True
            )
            
            result = {
                'title': extracted.title or '',
                'author': extracted.author or '',
                'main_content': extracted.text or '',
                'sections': {}
            }
            
            # Extract structured sections using heuristics
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Define section selectors
            section_selectors = {
                'Expense Ratio': [
                    'div:contains("Expense Ratio")',
                    '[class*="expense"]',
                    'td:contains("Expense Ratio")'
                ],
                'Exit Load': [
                    'div:contains("Exit Load")',
                    '[class*="exit"]',
                    'td:contains("Exit Load")'
                ],
                'Scheme Details': [
                    'div:contains("Scheme Details")',
                    '[class*="scheme"]',
                    'table:contains("Scheme Type")'
                ],
                'Minimum Investments': [
                    'div:contains("Minimum Investment")',
                    '[class*="minimum"]',
                    'td:contains("SIP")'
                ],
                'Fund Manager': [
                    'div:contains("Fund Manager")',
                    '[class*="manager"]',
                    'div:contains("About Fund Manager")'
                ],
                'Fund House': [
                    'div:contains("Fund House")',
                    '[class*="amc"]',
                    'div:contains("About Fund House")'
                ],
                'Riskometer': [
                    '[alt*="riskometer"]',
                    '[class*="risk"]',
                    'svg:contains("Risk")'
                ],
                'Benchmark': [
                    'div:contains("Benchmark")',
                    '[class*="benchmark"]',
                    'td:contains("Benchmark")'
                ],
                'About': [
                    'div:contains("About")',
                    '[class*="about"]',
                    'section:contains("About the Fund")'
                ]
            }
            
            # Extract content for each section
            for section_name, selectors in section_selectors.items():
                section_content = self._extract_section_content(soup, selectors, section_name)
                if section_content:
                    result['sections'][section_name] = section_content
            
            # Add main content as fallback
            if not result['sections'] and result['main_content']:
                result['sections']['Main Content'] = result['main_content']
            
            return result
            
        except Exception as e:
            logger.error(f"Trafilatura extraction failed for {url}: {e}")
            return {'error': str(e)}
    
    def _extract_section_content(self, soup: BeautifulSoup, selectors: List[str], section_name: str) -> Optional[str]:
        """Extract content for a specific section using multiple selectors"""
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    # Combine text from all matching elements
                    content_parts = []
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text and len(text.strip()) > 10:  # Filter out very short matches
                            content_parts.append(text.strip())
                    
                    if content_parts:
                        # Join and clean content
                        combined_text = ' '.join(content_parts)
                        # Remove extra whitespace and normalize
                        cleaned_text = re.sub(r'\s+', ' ', combined_text).strip()
                        return cleaned_text
            except Exception as e:
                logger.debug(f"Selector {selector} failed for {section_name}: {e}")
                continue
        
        return None
    
    def extract_image_based_content(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract content from images using alt text and aria labels"""
        image_content = {}
        
        # Riskometer - look for SVG or images with risk-related alt text
        riskometer_elements = soup.find_all(['svg', 'img'], alt=True)
        for element in riskometer_elements:
            alt_text = element.get('alt') or element.get('aria-label') or element.get('title')
            if alt_text and 'risk' in alt_text.lower():
                image_content['Riskometer'] = alt_text
                break
        
        return image_content
    
    def extract_table_data(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract structured data from tables"""
        table_data = {}
        
        # Look for tables with financial data
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_data = [cell.get_text(strip=True) for cell in cells]
                
                # Look for key-value pairs
                if len(row_data) == 2:
                    key = row_data[0].strip()
                    value = row_data[1].strip()
                    
                    # Categorize the data
                    if any(term in key.lower() for term in ['expense', 'ratio', 'nav']):
                        table_data['Expense Ratio'] = value
                    elif any(term in key.lower() for term in ['exit', 'load']):
                        table_data['Exit Load'] = value
                    elif any(term in key.lower() for term in ['minimum', 'sip', 'investment']):
                        table_data['Minimum Investments'] = value
                    elif any(term in key.lower() for term in ['fund', 'type', 'category']):
                        table_data['Scheme Details'] = value
        
        return table_data
    
    def detect_accordions(self, soup: BeautifulSoup) -> None:
        """Detect and potentially expand accordion content"""
        # Look for common accordion patterns
        accordion_selectors = [
            '[aria-expanded="false"]',
            '[class*="accordion"]',
            '[class*="collapsible"]',
            '[data-toggle="collapse"]'
        ]
        
        for selector in accordion_selectors:
            accordions = soup.select(selector)
            if accordions:
                logger.info(f"Found {len(accordions)} potential accordion elements")
                # In a full implementation, we would simulate clicks to expand
                # For now, just log the detection
                return True
        
        return False
    
    def process_html_file(self, html_file_path: str) -> ExtractedDoc:
        """Process a single HTML file and extract structured content"""
        try:
            # Read HTML file
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract scheme ID and URL from path
            path_parts = Path(html_file_path).parts
            scheme_id = path_parts[-2] if len(path_parts) >= 2 else 'unknown'
            
            # Get source URL from sources config
            source_url = None
            for scheme in self.sources.get('schemes', []):
                if scheme.get('id') == scheme_id:
                    for source in scheme.get('sources', []):
                        source_url = source.get('url')
                        break
            
            if not source_url:
                logger.error(f"Could not find source URL for scheme {scheme_id}")
                return None
            
            # Get fetched timestamp from metadata file
            meta_file = html_file_path.replace('.html', '.meta.json')
            fetched_at = datetime.now(timezone.utc).isoformat()
            if os.path.exists(meta_file):
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                    fetched_at = metadata.get('fetched_at', fetched_at)
            
            # Extract content using trafilatura
            extraction_result = self.extract_with_trafilatura(html_content, source_url)
            
            if 'error' in extraction_result:
                logger.error(f"Extraction failed for {html_file_path}: {extraction_result['error']}")
                return None
            
            # Check must-have anchors
            found_anchors = set(extraction_result['sections'].keys())
            required_anchors = self.must_have_anchors.get('all', [])
            min_required_anchors = self.must_have_anchors.get('min_required', [])
            
            must_have_anchors = {}
            for anchor in required_anchors:
                must_have_anchors[anchor] = anchor in found_anchors
            
            # Determine extraction health
            missing_min_anchors = [anchor for anchor in min_required_anchors if anchor not in found_anchors]
            extraction_health = 'degraded' if missing_min_anchors else 'ok'
            
            # Create extracted document
            doc = ExtractedDoc(
                scheme_id=scheme_id,
                source_url=source_url,
                fetched_at=fetched_at,
                sections=extraction_result['sections'],
                must_have_anchors=must_have_anchors,
                extraction_health=extraction_health
            )
            
            logger.info(f"Extracted {len(doc.sections)} sections from {scheme_id}")
            return doc
            
        except Exception as e:
            logger.error(f"Error processing {html_file_path}: {e}")
            return None
    
    def save_extracted_doc(self, doc: ExtractedDoc) -> bool:
        """Save extracted document to JSON file"""
        try:
            # Create output directory for scheme
            scheme_dir = os.path.join(self.output_dir, doc.scheme_id)
            os.makedirs(scheme_dir, exist_ok=True)
            
            # Prepare output data
            output_data = {
                'scheme_id': doc.scheme_id,
                'source_url': doc.source_url,
                'fetched_at': doc.fetched_at,
                'sections': doc.sections,
                'must_have_anchors': doc.must_have_anchors,
                'extraction_health': doc.extraction_health
            }
            
            # Save to JSON file
            output_file = os.path.join(scheme_dir, 'extracted.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved extracted document: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving extracted document: {e}")
            return False
    
    def extract_all(self) -> List[ExtractedDoc]:
        """Extract content from all HTML files in the raw directory"""
        logger.info("Starting extraction of all HTML files")
        
        extracted_docs = []
        
        # Find all HTML files
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.endswith('.html'):
                    html_file_path = os.path.join(root, file)
                    doc = self.process_html_file(html_file_path)
                    if doc:
                        extracted_docs.append(doc)
                        self.save_extracted_doc(doc)
        
        # Log summary
        successful_extractions = len(extracted_docs)
        total_schemes = len(self.sources.get('schemes', []))
        
        logger.info(f"Extraction completed: {successful_extractions}/{total_schemes} schemes")
        
        # Health check
        health_summary = {
            'total_schemes': total_schemes,
            'successful_extractions': successful_extractions,
            'failed_extractions': total_schemes - successful_extractions,
            'health': 'ok' if successful_extractions == total_schemes else 'partial'
        }
        
        for doc in extracted_docs:
            if doc.extraction_health != 'ok':
                health_summary['health'] = 'degraded'
                break
        
        return extracted_docs
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the extractor"""
        try:
            total_schemes = len(self.sources.get('schemes', []))
            health_report = {
                'total_schemes': total_schemes,
                'successful_extractions': 0,
                'failed_extractions': 0,
                'last_extraction_time': None,
                'health': 'unknown'
            }
            
            # Check each scheme directory for extracted files
            for scheme in self.sources.get('schemes', []):
                scheme_id = scheme.get('id')
                scheme_dir = os.path.join(self.output_dir, scheme_id)
                
                if os.path.exists(scheme_dir):
                    extracted_file = os.path.join(scheme_dir, 'extracted.json')
                    if os.path.exists(extracted_file):
                        health_report['successful_extractions'] += 1
                        
                        # Check extraction health
                        with open(extracted_file, 'r') as f:
                            data = json.load(f)
                            if data.get('extraction_health') != 'ok':
                                health_report['health'] = 'degraded'
                        
                        # Track last extraction time
                        file_mtime = os.path.getmtime(extracted_file)
                        if not health_report['last_extraction_time'] or file_mtime > health_report['last_extraction_time']:
                            health_report['last_extraction_time'] = datetime.fromtimestamp(file_mtime, timezone.utc).isoformat()
                    else:
                        health_report['failed_extractions'] += 1
                else:
                    health_report['failed_extractions'] += 1
            
            # Determine overall health
            if health_report['successful_extractions'] == total_schemes:
                health_report['health'] = 'ok'
            elif health_report['successful_extractions'] > 0:
                health_report['health'] = 'partial'
            else:
                health_report['health'] = 'failed'
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error getting extraction health: {e}")
            return {'health': 'error', 'error': str(e)}


# CLI interface for standalone execution
async def main():
    """CLI interface for the extractor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract structured content from HTML files')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--input-dir', help='Input directory with HTML files')
    parser.add_argument('--output-dir', help='Output directory for extracted files')
    parser.add_argument('--scheme-id', help='Extract specific scheme only')
    
    args = parser.parse_args()
    
    extractor = Extractor(args.config_dir)
    
    if args.input_dir:
        extractor.input_dir = args.input_dir
    if args.output_dir:
        extractor.output_dir = args.output_dir
    
    if args.scheme_id:
        # Extract specific scheme
        html_files = []
        for root, dirs, files in os.walk(extractor.input_dir):
            for file in files:
                if file.endswith('.html') and args.scheme_id in root:
                    html_files.append(os.path.join(root, file))
        
        for html_file in html_files:
            doc = extractor.process_html_file(html_file)
            if doc:
                extractor.save_extracted_doc(doc)
    else:
        # Extract all schemes
        extracted_docs = extractor.extract_all()
        
        # Print summary
        health = extractor.get_health_status()
        print(f"\nExtraction Summary:")
        print(f"Total schemes: {health['total_schemes']}")
        print(f"Successful: {health['successful_extractions']}")
        print(f"Failed: {health['failed_extractions']}")
        print(f"Health: {health['health']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
