"""
Structured Observability Logger Module - Phase 5
Logs transaction metadata to a JSONL file under logs/audit.jsonl.
Ensures query privacy by hashing sensitive numbers and storing only query SHA-256 hashes.
"""

import os
import re
import json
import uuid
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def mask_numbers_in_text(text: str) -> str:
    """
    Replaces any sequence of digits (e.g. phone numbers, Aadhaar, PAN digits, OTPs)
    with a SHA-256 hash of those digits to prevent cleartext printing in console logs.
    """
    def replacer(match):
        val = match.group(0)
        h = hashlib.sha256(val.encode('utf-8')).hexdigest()[:12]
        return f"[HASHED:{h}]"
    return re.sub(r'\d+', replacer, text)

def log_transaction(
    query: str,
    intent: str,
    resolved_scheme_id: Optional[str],
    confidence_score: float,
    top_chunk_id: Optional[str],
    latency_ms: int,
    compliance_checks_passed: bool
) -> str:
    """
    Logs transaction metadata to logs/audit.jsonl and returns a generated request_id.
    Guarantees raw query is never stored in cleartext in the audit log (only SHA-256 hashed).
    """
    from datetime import timezone
    request_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"
    
    # Compute SHA-256 of the raw query
    query_bytes = query.encode('utf-8')
    query_hash = "sha256:" + hashlib.sha256(query_bytes).hexdigest()
    
    log_entry = {
        "timestamp": timestamp,
        "request_id": request_id,
        "query_hash": query_hash,
        "resolved_scheme_id": resolved_scheme_id,
        "intent_detected": intent,
        "confidence_score": round(confidence_score, 4),
        "top_chunk_id": top_chunk_id,
        "latency_ms": latency_ms,
        "compliance_checks_passed": compliance_checks_passed
    }
    
    # Locate workspace root directory
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    audit_file = os.path.join(logs_dir, "audit.jsonl")
    
    # Check size limit (10 MB cap) to prevent storage exhaustion
    try:
        if os.path.exists(audit_file) and os.path.getsize(audit_file) > 10 * 1024 * 1024:
            backup_file = audit_file + ".bak"
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.rename(audit_file, backup_file)
    except Exception as e:
        logger.error(f"Error rotating audit log: {e}")
        
    try:
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Error writing to audit log: {e}")
        
    # Print a privacy-safe masked console log
    masked_query = mask_numbers_in_text(query)
    logger.info(
        f"[AUDIT] request_id={request_id} intent={intent} scheme={resolved_scheme_id} "
        f"conf={confidence_score:.4f} latency={latency_ms}ms passed={compliance_checks_passed} "
        f"query_masked='{masked_query}'"
    )
    
    return request_id
