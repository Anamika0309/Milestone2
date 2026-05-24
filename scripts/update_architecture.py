#!/usr/bin/env python3
"""
Architecture Document Updater
Updates Phase-wise-Architecture.md based on pipeline changes and data modifications.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def load_architecture():
    """Load current architecture document"""
    arch_file = Path('Docs/Phase-wise-Architecture.md')
    if arch_file.exists():
        with open(arch_file, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def update_architecture_updates_section():
    """Update the automated updates section in architecture"""
    arch_content = load_architecture()
    if not arch_content:
        return False
    
    # Look for the updates section
    lines = arch_content.split('\n')
    updates_section_start = None
    
    for i, line in enumerate(lines):
        if "Automated architecture document updates on pipeline changes" in line:
            updates_section_start = i
            break
    
    if updates_section_start is None:
        return False
    
    # Update the section to include timestamp
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    updated_line = f"- Automated architecture document updates on pipeline changes (Last updated: {current_time})"
    
    lines[updates_section_start] = updated_line
    updated_content = '\n'.join(lines)
    
    # Write back
    arch_file = Path('Docs/Phase-wise-Architecture.md')
    with open(arch_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"Updated architecture document with timestamp: {current_time}")
    return True


def update_pipeline_status():
    """Update pipeline implementation status in architecture"""
    arch_content = load_architecture()
    if not arch_content:
        return False
    
    # Check current implementation status
    implementation_status = {
        'fetcher': os.path.exists('src/mf_faq/ingestion/fetcher.py'),
        'extractor': os.path.exists('src/mf_faq/ingestion/extractor.py'),
        'cleaner': os.path.exists('src/mf_faq/ingestion/cleaner.py'),
        'chunker': os.path.exists('src/mf_faq/ingestion/chunker.py'),
        'embedder': os.path.exists('src/mf_faq/ingestion/embedder.py'),
        'indexer': os.path.exists('src/mf_faq/ingestion/indexer.py'),
        'pipeline': os.path.exists('src/mf_faq/ingestion/pipeline/service.py')
    }
    
    completed_phases = sum(1 for status in implementation_status.values() if status)
    total_phases = len(implementation_status)
    
    # Create status section
    status_section = f"""
## Current Implementation Status

**Phase 1 (Ingestion & Corpus Build) - {completed_phases}/{total_phases} phases complete**

### Completed Components:
"""
    
    for phase, status in implementation_status.items():
        status_icon = "✅" if status else "❌"
        status_text = "Complete" if status else "Not Implemented"
        status_section += f"- **Phase 1.{phase} ({phase.title()}):** {status_icon} {status_text}\n"
    
    status_section += f"""
### Latest Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*This section is automatically updated by the ingestion pipeline workflow*
"""
    
    # Find where to insert this section
    lines = arch_content.split('\n')
    insert_point = None
    
    for i, line in enumerate(lines):
        if "## Phase 2 - Retrieval Layer" in line:
            insert_point = i
            break
    
    if insert_point is None:
        return False
    
    # Insert status section
    lines.insert(insert_point, status_section)
    updated_content = '\n'.join(lines)
    
    # Write back
    arch_file = Path('Docs/Phase-wise-Architecture.md')
    with open(arch_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"Updated implementation status: {completed_phases}/{total_phases} phases complete")
    return True


def main():
    parser = argparse.ArgumentParser(description='Update architecture document')
    parser.add_argument('--data-changes', action='store_true', 
                      help='Update due to data changes')
    parser.add_argument('--pipeline-changes', action='store_true',
                      help='Update due to pipeline changes')
    parser.add_argument('--status-update', action='store_true',
                      help='Update implementation status')
    
    args = parser.parse_args()
    
    updated = False
    
    if args.data_changes:
        print("Updating architecture due to data changes...")
        updated = update_architecture_updates_section()
        updated = updated or updated
    
    if args.pipeline_changes:
        print("Updating architecture due to pipeline changes...")
        updated = update_architecture_updates_section()
        updated = updated or updated
    
    if args.status_update:
        print("Updating implementation status...")
        updated = update_pipeline_status()
        updated = updated or updated
    
    if updated:
        print("Architecture document updated successfully")
    else:
        print("No updates needed")
    
    return 0 if updated else 1


if __name__ == "__main__":
    sys.exit(main())
