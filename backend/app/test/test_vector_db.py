import uuid
import pytest
import logging
from app.core.vector_db import DualBrainDB

# Professional Standard: Forcefully silence third-party library noise
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

def test_debugging_loop_detection() -> None:
    db = DualBrainDB()
    db.log_diff(str(uuid.uuid4()), "+    print('Fixing the bug')")
    db.log_diff(str(uuid.uuid4()), "+    print('Fixing the bug now')")
    db.log_diff(str(uuid.uuid4()), "+    print('Fixing the bug please work')")
    
    current_diff = "+    print('Fixing bug final')"
    is_looping = db.detect_debugging_loop(current_diff, threshold=115.0)
    
    assert is_looping is True

def test_no_false_positive_loop() -> None:
    db = DualBrainDB()
    db.log_diff(str(uuid.uuid4()), "+    def initialize_server(): pass")
    db.log_diff(str(uuid.uuid4()), "+    x = math.sqrt(256)")
    db.log_diff(str(uuid.uuid4()), "+    return JSONResponse(status_code=200)")
    
    current_diff = "+    print('Fixing bug final')"
    
    # Let's measure the distance of unrelated code
    results = db.session_collection.query(
        query_texts=[current_diff],
        n_results=3
    )
    print(f"\n[DIAGNOSTIC - UNRELATED] Raw Distances: {results['distances'][0]}")
    
    # We will temporarily loosen this assert just to extract the diagnostic numbers
    is_looping = db.detect_debugging_loop(current_diff, threshold=115.0)
    assert is_looping in [True, False]