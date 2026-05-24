"""
Phase 1.3 - Cleaner & Normalizer Module
Purpose: Strip boilerplate, normalize encoding so retrieval tokens match user queries

Responsibilities:
- Strip known boilerplate ("market risks", "You may also like", footer links)
- Unicode NFKC normalization; collapse whitespace; map Rs./INR → ₹; normalize %, –, —, smart quotes
- Strip volatile fields from a separate stable view of the doc (NAV, "as on ", today's AUM) to feed the stable content_hash (see 1.7)
- Section drop / trim policy (gatekeeper for what flows into 1.4+):
  Drop entirely: the FAQ section. The extractor still parses the FAQPage JSON-LD as a must-have-anchor health signal, but the Q&A content (mostly Groww UX guidance, "How do I invest…?") is not part of the facts-only corpus.
  Trim aggressively: Fund Manager keeps just the manager's name and tenure (<Initials> <Name> <Joined> - Present); the bio (Education / Experience) is dropped. Fund House keeps the AMC name, rank, total AUM, and incorporation date; phone / email / website / address are dropped.
"""

import hashlib
import json
import logging
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from .extractor import ExtractedDoc


logger = logging.getLogger(__name__)


class CleanedDoc:
    """Represents a cleaned document with normalized content"""
    
    def __init__(self, scheme_id: str, source_url: str, fetched_at: str, 
                 sections: List[Dict[str, str]], must_have_anchors: Dict[str, bool],
                 extraction_health: str = "ok", stable_content_hash: str = None):
        self.scheme_id = scheme_id
        self.source_url = source_url
        self.fetched_at = fetched_at
        self.sections = sections
        self.must_have_anchors = must_have_anchors
        self.extraction_health = extraction_health
        self.stable_content_hash = stable_content_hash


class Cleaner:
    """Main cleaner class for processing extracted content"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', 'config')
        self.input_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'processed')
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'processed')
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Boilerplate patterns to strip
        self.boilerplate_patterns = [
            r"Mutual fund investments are subject to market risks.*?\.?",
            r"You may also like.*?\.?",
            r"Click here.*?\.?",
            r"Read more.*?\.?",
            r"View all funds.*?\.?",
            r"Disclaimer.*?\.?",
            r"Risk.*?\.?",
            r"Past performance.*?\.?",
            r"Returns are not guaranteed.*?\.?"
        ]
        
        # Currency normalization mappings
        self.currency_mappings = {
            'Rs.': '₹',
            'INR': '₹',
            'Rs': '₹',
            'rs': '₹'
        }
        
        # Volatile field patterns
        self.volatile_field_patterns = [
            r"NAV.*?as\s+on\s+[0-9]{1,2}[/-][0-9]{1,2}",
            r"AUM.*?₹?\s*[0-9,.,]+\s*cr?",
            r"Net Assets.*?₹?\s*[0-9,.,]+\s*cr?"
        ]
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def normalize_unicode(self, text: str) -> str:
        """Apply Unicode NFKC normalization"""
        try:
            return unicodedata.normalize('NFKC', text)
        except Exception as e:
            logger.warning(f"Unicode normalization failed: {e}")
            return text
    
    def normalize_whitespace(self, text: str) -> str:
        """Collapse multiple whitespace characters to single space"""
        return re.sub(r'\s+', ' ', text.strip())
    
    def normalize_currency(self, text: str) -> str:
        """Normalize currency symbols to ₹"""
        for old_currency, new_currency in self.currency_mappings.items():
            text = text.replace(old_currency, new_currency)
        return text
    
    def normalize_punctuation(self, text: str) -> str:
        """Normalize punctuation and special characters"""
        # Normalize dashes and quotes
        text = text.replace('–', '-').replace('—', '-')
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Normalize percentage signs
        text = re.sub(r'%\s*', '%', text)
        
        return text
    
    def strip_boilerplate(self, text: str) -> str:
        """Remove known boilerplate patterns"""
        cleaned = text
        for pattern in self.boilerplate_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        return cleaned.strip()
    
    def remove_volatile_fields(self, text: str, section_name: str) -> str:
        """Remove or mask volatile fields from text"""
        cleaned = text
        
        if section_name.lower() in ['fund manager', 'fund house']:
            # For Fund Manager and Fund House, apply aggressive trimming
            # Keep only name and tenure/basics
            if section_name.lower() == 'fund manager':
                # Extract name and tenure only
                name_match = re.search(r'([A-Z][a-z\s]+[A-Z\s]+[A-Z])', cleaned)
                tenure_match = re.search(r'([A-Z][a-z\s]+\s+[0-9]{4}\s*-\s*Present)', cleaned)
                
                if name_match and tenure_match:
                    cleaned = f"{name_match.group(1)} {tenure_match.group(1)} - Present"
                else:
                    # Just keep the name
                    name_match = re.search(r'([A-Z][a-z\s]+[A-Z\s]+[A-Z])', cleaned)
                    if name_match:
                        cleaned = name_match.group(1)
            
            elif section_name.lower() == 'fund house':
                # Keep only AMC name, rank, AUM, incorporation date
                # Extract AMC name
                amc_match = re.search(r'([A-Z][a-z\s]+[A-Z\s]+[A-Z])', cleaned)
                if amc_match:
                    cleaned = amc_match.group(1)
                
                # Extract AUM (but we'll remove it as volatile)
                aum_match = re.search(r'AUM.*?₹?\s*([0-9,.,]+\s*cr?)', cleaned)
                # Extract incorporation date
                date_match = re.search(r'Incorporation.*?([0-9]{4})', cleaned)
                if date_match:
                    cleaned += f", Incorporated {date_match.group(1)}"
        
        # General volatile field removal
        for pattern in self.volatile_field_patterns:
            cleaned = re.sub(pattern, '[VOLATILE_DATA]', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def is_volatile_section(self, section_name: str) -> bool:
        """Check if section should be dropped entirely"""
        return section_name.lower() == 'faq'
    
    def should_trim_section(self, section_name: str) -> bool:
        """Check if section should be trimmed"""
        return section_name.lower() in ['fund manager', 'fund house']
    
    def calculate_stable_content_hash(self, sections: Dict[str, str]) -> str:
        """Calculate hash of content excluding volatile fields"""
        stable_content = []
        
        for section_name, section_text in sections.items():
            if not self.is_volatile_section(section_name):
                # Remove volatile fields for stable hash calculation
                stable_text = self.remove_volatile_fields(section_text, section_name)
                if stable_text:
                    stable_content.append(f"{section_name}: {stable_text}")
        
        if stable_content:
            content_for_hash = '\n'.join(stable_content)
            return hashlib.sha256(content_for_hash.encode()).hexdigest()
        
        return None
    
    def clean_section(self, section_text: str, section_name: str) -> str:
        """Clean a single section of text"""
        # Apply all normalization steps
        cleaned = self.normalize_unicode(section_text)
        cleaned = self.normalize_whitespace(cleaned)
        cleaned = self.normalize_currency(cleaned)
        cleaned = self.normalize_punctuation(cleaned)
        cleaned = self.strip_boilerplate(cleaned)
        
        # Apply section-specific cleaning
        if self.should_trim_section(section_name):
            cleaned = self.remove_volatile_fields(cleaned, section_name)
        elif self.is_volatile_section(section_name):
            cleaned = ""  # Drop FAQ sections entirely
        
        return cleaned.strip()
    
    def clean_document(self, doc: ExtractedDoc) -> CleanedDoc:
        """Clean an entire extracted document"""
        try:
            cleaned_sections = {}
            stable_hash = None
            
            for section_name, section_data in doc.sections.items():
                if isinstance(section_data, dict):
                    text = section_data.get('text', '')
                    source = section_data.get('source', 'html_section')
                else:
                    text = str(section_data)
                    source = 'html_section'
                    
                cleaned_text = self.clean_section(text, section_name)
                if cleaned_text:
                    cleaned_sections[section_name] = {
                        'name': section_name,
                        'text': cleaned_text,
                        'source': source
                    }
            
            # Calculate stable content hash
            stable_hash = self.calculate_stable_content_hash(
                {name: info.get('text', '') for name, info in cleaned_sections.items()}
            )
            
            # Create cleaned document
            cleaned_doc = CleanedDoc(
                scheme_id=doc.scheme_id,
                source_url=doc.source_url,
                fetched_at=doc.fetched_at,
                sections=cleaned_sections,
                must_have_anchors=doc.must_have_anchors,
                extraction_health='ok',  # Cleaning shouldn't affect extraction health
                stable_content_hash=stable_hash
            )
            
            logger.info(f"Cleaned document {doc.scheme_id} with {len(cleaned_sections)} sections")
            return cleaned_doc
            
        except Exception as e:
            logger.error(f"Error cleaning document {doc.scheme_id}: {e}")
            raise
    
    def save_cleaned_doc(self, doc: CleanedDoc) -> bool:
        """Save cleaned document to JSON file"""
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
                'extraction_health': doc.extraction_health,
                'stable_content_hash': doc.stable_content_hash,
                'cleaned_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Save to JSON file
            output_file = os.path.join(scheme_dir, 'cleaned.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved cleaned document: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving cleaned document: {e}")
            return False
    
    def process_extracted_file(self, extracted_file_path: str) -> CleanedDoc:
        """Process a single extracted file and clean it"""
        try:
            # Read extracted document
            with open(extracted_file_path, 'r', encoding='utf-8') as f:
                extracted_data = json.load(f)
            
            # Create ExtractedDoc object
            doc = ExtractedDoc(
                scheme_id=extracted_data.get('scheme_id'),
                source_url=extracted_data.get('source_url'),
                fetched_at=extracted_data.get('fetched_at'),
                sections=extracted_data.get('sections', {}),
                must_have_anchors=extracted_data.get('must_have_anchors', {}),
                extraction_health=extracted_data.get('extraction_health', 'ok')
            )
            
            # Clean the document
            cleaned_doc = self.clean_document(doc)
            
            # Save cleaned document
            if self.save_cleaned_doc(cleaned_doc):
                logger.info(f"Successfully processed {extracted_file_path}")
                return cleaned_doc
            else:
                logger.error(f"Failed to save cleaned document from {extracted_file_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing extracted file {extracted_file_path}: {e}")
            return None
    
    def clean_all(self) -> List[CleanedDoc]:
        """Clean all extracted documents in the input directory"""
        logger.info("Starting cleaning of all extracted documents")
        
        cleaned_docs = []
        
        # Find all extracted files
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.endswith('extracted.json'):
                    extracted_file_path = os.path.join(root, file)
                    cleaned_doc = self.process_extracted_file(extracted_file_path)
                    if cleaned_doc:
                        cleaned_docs.append(cleaned_doc)
        
        # Log summary
        successful_cleanings = len(cleaned_docs)
        total_schemes = len([d for d in cleaned_docs])
        
        logger.info(f"Cleaning completed: {successful_cleanings}/{total_schemes} schemes")
        
        # Health check
        health_summary = {
            'total_schemes': total_schemes,
            'successful_cleanings': successful_cleanings,
            'failed_cleanings': total_schemes - successful_cleanings,
            'health': 'ok' if successful_cleanings == total_schemes else 'partial'
        }
        
        for doc in cleaned_docs:
            if doc.extraction_health != 'ok':
                health_summary['health'] = 'degraded'
                break
        
        return cleaned_docs
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the cleaner"""
        try:
            total_schemes = len([d for d in os.listdir(self.output_dir) if os.path.isdir(os.path.join(self.output_dir, d))])
            
            health_report = {
                'total_schemes': total_schemes,
                'successful_cleanings': 0,
                'failed_cleanings': 0,
                'last_cleaning_time': None,
                'health': 'unknown'
            }
            
            max_mtime = 0.0
            
            # Check each scheme directory for cleaned files
            for scheme_dir_name in os.listdir(self.output_dir):
                scheme_dir = os.path.join(self.output_dir, scheme_dir_name)
                if os.path.isdir(scheme_dir):
                    cleaned_file = os.path.join(scheme_dir, 'cleaned.json')
                    if os.path.exists(cleaned_file):
                        health_report['successful_cleanings'] += 1
                        
                        # Check cleaning quality
                        with open(cleaned_file, 'r') as f:
                            data = json.load(f)
                            # Verify no boilerplate remains
                            sections = data.get('sections', {})
                            for section_info in sections.values():
                                text = section_info.get('text', '')
                                if any(re.search(pattern, text, re.IGNORECASE) for pattern in self.boilerplate_patterns):
                                    health_report['health'] = 'degraded'
                                    break
                        
                        # Track last cleaning time
                        file_mtime = os.path.getmtime(cleaned_file)
                        if file_mtime > max_mtime:
                            max_mtime = file_mtime
                    else:
                        health_report['failed_cleanings'] += 1
                else:
                    health_report['failed_cleanings'] += 1
            
            if max_mtime > 0:
                health_report['last_cleaning_time'] = datetime.fromtimestamp(max_mtime, timezone.utc).isoformat()
            
            # Determine overall health
            if health_report['successful_cleanings'] == total_schemes:
                if health_report['health'] == 'unknown':
                    health_report['health'] = 'ok'
            elif health_report['successful_cleanings'] > 0:
                health_report['health'] = 'partial'
            else:
                health_report['health'] = 'failed'
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error getting cleaning health: {e}")
            return {'health': 'error', 'error': str(e)}


# CLI interface for standalone execution
async def main():
    """CLI interface for the cleaner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean extracted HTML content')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--input-dir', help='Input directory with extracted files')
    parser.add_argument('--output-dir', help='Output directory for cleaned files')
    parser.add_argument('--scheme-id', help='Clean specific scheme only')
    
    args = parser.parse_args()
    
    cleaner = Cleaner(args.config_dir)
    
    if args.input_dir:
        cleaner.input_dir = args.input_dir
    if args.output_dir:
        cleaner.output_dir = args.output_dir
    
    if args.scheme_id:
        # Clean specific scheme
        extracted_file = os.path.join(cleaner.input_dir, args.scheme_id, 'extracted.json')
        if os.path.exists(extracted_file):
            cleaned_doc = cleaner.process_extracted_file(extracted_file)
            if cleaned_doc:
                print(f"Successfully cleaned scheme {args.scheme_id}")
            else:
                print(f"Failed to clean scheme {args.scheme_id}")
    else:
        # Clean all schemes
        cleaned_docs = cleaner.clean_all()
        
        # Print summary
        health = cleaner.get_health_status()
        print(f"\nCleaning Summary:")
        print(f"Total schemes: {health['total_schemes']}")
        print(f"Successful: {health['successful_cleanings']}")
        print(f"Failed: {health['failed_cleanings']}")
        print(f"Health: {health['health']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
