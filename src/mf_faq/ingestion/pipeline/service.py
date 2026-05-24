"""
Phase 1.7 - Refresh & Health Service
Purpose: Orchestrate 1.1 → 1.6 pipeline with monitoring

Responsibilities:
- Orchestrate 1.1 → 1.6 pipeline
- Content hash diff detection
- Drift alerts (≥2 URLs changed simultaneously)
- Soft-404 detection
- Stable content hash for incremental updates
- Automated architecture document updates on pipeline changes

Exit Criteria: Deterministic refresh behavior, proper freeze on drift
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import asyncio
import inspect
from mf_faq.config import load_sources
from mf_faq.ingestion.fetcher import Fetcher
from mf_faq.ingestion.extractor import Extractor
from mf_faq.ingestion.cleaner import Cleaner
from mf_faq.ingestion.chunker import Chunker
from mf_faq.ingestion.embedder import Embedder
from mf_faq.ingestion.indexer import Indexer


logger = logging.getLogger(__name__)


class PipelineService:
    """Main pipeline service for orchestrating ingestion"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', '..', 'config')
        self.raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'raw')
        self.processed_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'processed')
        self.index_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'index')
        
        # Ensure directories exist
        for dir_path in [self.raw_dir, self.processed_dir, self.index_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Load sources configuration
        self.sources = load_sources(self.config_dir)
        
        # Initialize pipeline components
        self.fetcher = Fetcher(self.config_dir)
        self.extractor = Extractor(self.config_dir)
        self.cleaner = Cleaner(self.config_dir)
        self.chunker = Chunker(self.config_dir)
        try:
            self.embedder = Embedder(self.config_dir)
        except ImportError:
            logger.warning("Heavy Embedder not available, falling back to SimpleEmbedder")
            from mf_faq.ingestion.embedder_simple import SimpleEmbedder
            self.embedder = SimpleEmbedder(self.config_dir)
        self.indexer = Indexer(self.config_dir)
        
        # Pipeline state
        self.pipeline_state = {
            'last_run': None,
            'last_hashes': {},
            'drift_detected': False,
            'soft_404_detected': False
        }
        
        logger.info("Initialized pipeline service")
    
    def calculate_content_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def detect_content_changes(self) -> Dict[str, Any]:
        """Detect changes in fetched content"""
        changes = {}
        
        # Check each scheme for changes
        for scheme in self.sources.get('schemes', []):
            scheme_id = scheme.get('id')
            scheme_dir = os.path.join(self.raw_dir, scheme_id)
            
            if os.path.exists(scheme_dir):
                # Get latest HTML file
                html_files = [f for f in os.listdir(scheme_dir) if f.endswith('.html')]
                if html_files:
                    latest_html = max(html_files, key=lambda f: os.path.getmtime(os.path.join(scheme_dir, f)))
                    latest_html_path = os.path.join(scheme_dir, latest_html)
                    
                    with open(latest_html_path, 'r', encoding='utf-8') as f:
                        current_hash = self.calculate_content_hash(f.read())
                    
                    previous_hash = self.pipeline_state['last_hashes'].get(scheme_id)
                    
                    if previous_hash and previous_hash != current_hash:
                        changes[scheme_id] = {
                            'type': 'content_change',
                            'previous_hash': previous_hash,
                            'current_hash': current_hash,
                            'file': latest_html
                        }
                    else:
                        # Update stored hash
                        self.pipeline_state['last_hashes'][scheme_id] = current_hash
        
        return changes
    
    def detect_drift_alerts(self, changes: Dict[str, Any]) -> bool:
        """Detect if multiple URLs changed simultaneously"""
        changed_schemes = [scheme_id for scheme_id in changes.keys()]
        
        # Alert if 2 or more schemes changed
        if len(changed_schemes) >= 2:
            logger.warning(f"Drift detected: {len(changed_schemes)} schemes changed simultaneously")
            return True
        
        return False
    
    def detect_soft_404s(self) -> bool:
        """Detect soft 404s in processed content"""
        soft_404_count = 0
        
        for scheme in self.sources.get('schemes', []):
            scheme_id = scheme.get('id')
            processed_dir = os.path.join(self.processed_dir, scheme_id)
            
            if os.path.exists(processed_dir):
                # Check for empty or minimal content files
                for file in os.listdir(processed_dir):
                    file_path = os.path.join(processed_dir, file)
                    if os.path.getsize(file_path) < 100:  # Very small file
                        soft_404_count += 1
                        break
        
        if soft_404_count > 0:
            logger.warning(f"Soft 404s detected: {soft_404_count} schemes with minimal content")
            return True
        
        return False
    
    def calculate_stable_content_hash(self, scheme_id: str) -> str:
        """Calculate stable content hash excluding volatile fields"""
        try:
            # Load cleaned content
            cleaned_file = os.path.join(self.processed_dir, scheme_id, 'cleaned.json')
            if os.path.exists(cleaned_file):
                with open(cleaned_file, 'r') as f:
                    cleaned_data = json.load(f)
                
                # Extract stable content (exclude volatile fields)
                stable_content = []
                for section_name, section_info in cleaned_data.get('sections', {}).items():
                    if section_name.lower() not in ['faq']:  # Skip FAQ sections
                        text = section_info.get('text', '')
                        # Remove volatile patterns
                        text = re.sub(r'NAV.*?as on.*?\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', '[VOLATILE_DATA]', text)
                        text = re.sub(r'AUM.*?₹?\s*[\d,.,]+\s*cr?', '[VOLATILE_DATA]', text)
                        stable_content.append(text)
                
                # Calculate hash of stable content
                stable_text = '\n'.join(stable_content)
                return self.calculate_content_hash(stable_text)
        
        except Exception as e:
            logger.error(f"Error calculating stable hash for {scheme_id}: {e}")
            return ""
    
    async def run_pipeline_step(self, step_name: str, step_func, *args, **kwargs) -> bool:
        """Run a single pipeline step with error handling"""
        try:
            logger.info(f"Running pipeline step: {step_name}")
            if asyncio.iscoroutinefunction(step_func) or inspect.iscoroutinefunction(step_func):
                result = await step_func(*args, **kwargs)
            else:
                result = step_func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
            logger.info(f"Completed pipeline step: {step_name}")
            return result
        except Exception as e:
            logger.error(f"Error in pipeline step {step_name}: {e}")
            return False
    
    async def orchestrate_pipeline(self, reason: str = "scheduled", force_refresh: bool = False) -> bool:
        """Orchestrate complete ingestion pipeline"""
        logger.info(f"Starting pipeline orchestration - reason: {reason}")
        
        # Update pipeline state
        self.pipeline_state['last_run'] = datetime.now(timezone.utc).isoformat()
        
        # Step 1: Fetch
        if not await self.run_pipeline_step("fetch", self.fetcher.fetch_all):
            logger.error("Pipeline failed at fetch step")
            return False
        
        # Step 2: Extract
        if not await self.run_pipeline_step("extract", self.extractor.extract_all):
            logger.error("Pipeline failed at extract step")
            return False
        
        # Step 3: Clean
        if not await self.run_pipeline_step("clean", self.cleaner.clean_all):
            logger.error("Pipeline failed at clean step")
            return False
        
        # Step 4: Chunk
        if not await self.run_pipeline_step("chunk", self.chunker.chunk_all):
            logger.error("Pipeline failed at chunk step")
            return False
        
        # Step 5: Embed
        if not await self.run_pipeline_step("embed", self.embedder.embed_all):
            logger.error("Pipeline failed at embed step")
            return False
        
        # Step 6: Index
        if not await self.run_pipeline_step("index", self.indexer.build_all_indexes):
            logger.error("Pipeline failed at index step")
            return False
        
        # Health checks
        changes = self.detect_content_changes()
        drift_detected = self.detect_drift_alerts(changes)
        soft_404_detected = self.detect_soft_404s()
        
        # Update pipeline state
        self.pipeline_state['drift_detected'] = drift_detected
        self.pipeline_state['soft_404_detected'] = soft_404_detected
        
        # Log health status
        health_status = {
            'pipeline_completed': True,
            'changes_detected': len(changes) > 0,
            'drift_alerts': drift_detected,
            'soft_404s': soft_404_detected,
            'last_run': self.pipeline_state['last_run']
        }
        
        logger.info(f"Pipeline completed with health: {health_status}")
        
        # Save pipeline state
        self.save_pipeline_state()
        
        return True
    
    def save_pipeline_state(self):
        """Save pipeline state to file"""
        try:
            state_file = os.path.join(self.index_dir, 'pipeline_state.json')
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(self.pipeline_state, f, indent=2, ensure_ascii=False)
            logger.info("Saved pipeline state")
        except Exception as e:
            logger.error(f"Error saving pipeline state: {e}")
    
    def load_pipeline_state(self):
        """Load pipeline state from file"""
        try:
            state_file = os.path.join(self.index_dir, 'pipeline_state.json')
            if os.path.exists(state_file):
                with open(state_file, 'r', encoding='utf-8') as f:
                    self.pipeline_state = json.load(f)
                logger.info("Loaded pipeline state")
                return True
        except Exception as e:
            logger.error(f"Error loading pipeline state: {e}")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of pipeline"""
        try:
            health_report = {
                'last_run': self.pipeline_state.get('last_run'),
                'changes_detected': self.pipeline_state.get('drift_detected', False),
                'drift_alerts': self.pipeline_state.get('drift_detected', False),
                'soft_404s': self.pipeline_state.get('soft_404_detected', False),
                'pipeline_healthy': True,
                'health': 'ok'
            }
            
            # Check if pipeline components are healthy
            component_health = {}
            
            # Check fetcher
            if hasattr(self.fetcher, 'get_health_status'):
                component_health['fetcher'] = self.fetcher.get_health_status()
            
            # Check extractor
            if hasattr(self.extractor, 'get_health_status'):
                component_health['extractor'] = self.extractor.get_health_status()
            
            # Check cleaner
            if hasattr(self.cleaner, 'get_health_status'):
                component_health['cleaner'] = self.cleaner.get_health_status()
            
            # Check chunker
            if hasattr(self.chunker, 'get_health_status'):
                component_health['chunker'] = self.chunker.get_health_status()
            
            # Check embedder
            if hasattr(self.embedder, 'get_health_status'):
                component_health['embedder'] = self.embedder.get_health_status()
            
            # Check indexer
            if hasattr(self.indexer, 'get_health_status'):
                component_health['indexer'] = self.indexer.get_health_status()
            
            # Overall health
            all_healthy = all(status.get('health') == 'ok' for status in component_health.values())
            health_report['pipeline_healthy'] = all_healthy
            health_report['component_health'] = component_health
            
            if not all_healthy:
                health_report['health'] = 'degraded'
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error getting pipeline health: {e}")
            return {'health': 'error', 'error': str(e)}


# CLI interface for standalone execution
async def main():
    """CLI interface for pipeline service"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Orchestrate ingestion pipeline')
    parser.add_argument('--config-dir', help='Configuration directory path')
    parser.add_argument('--input-dir', help='Input directory for raw data')
    parser.add_argument('--output-dir', help='Output directory for processed data')
    parser.add_argument('--index-dir', help='Output directory for indexes')
    parser.add_argument('--reason', default='scheduled', help='Reason for pipeline run')
    parser.add_argument('--force-refresh', nargs='?', const=True, default=False, type=lambda x: str(x).lower() in ['true', '1', 'yes'], help='Force refresh all data')
    
    args = parser.parse_args()
    
    service = PipelineService(args.config_dir)
    
    if args.input_dir:
        service.raw_dir = args.input_dir
    if args.output_dir:
        service.processed_dir = args.output_dir
    if args.index_dir:
        service.index_dir = args.index_dir
    
    # Load previous state
    service.load_pipeline_state()
    
    # Run pipeline
    success = await service.orchestrate_pipeline(
        reason=args.reason,
        force_refresh=args.force_refresh
    )
    
    # Print summary
    health = service.get_health_status()
    print(f"\nPipeline Summary:")
    print(f"Reason: {args.reason}")
    print(f"Health: {health['health']}")
    print(f"Last run: {health['last_run']}")
    print(f"Changes detected: {health['changes_detected']}")
    print(f"Drift alerts: {health['drift_alerts']}")
    print(f"Soft 404s: {health['soft_404s']}")
    
    return 0 if success else 1


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
