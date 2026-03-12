import json
import sys
from datetime import datetime

def simulate_system_failure():
    # 1. Simulate a Structured Log (JSON)
    # The frontend should parse this and turn it RED because level is 'error'
    log_entry = {
        "level": "error",
        "event": "Database connection refused: port 5432",
        "timestamp": datetime.now().isoformat(),
        "service": "auth-gateway"
    }
    print(json.dumps(log_entry))
    sys.stdout.flush()

    # 2. Simulate a Raw Traceback
    # The frontend regex should catch "Exception" and route it to /log-crash
    print("\n--- Initializing critical task ---")
    raise Exception("CRITICAL_VRAM_OVERFLOW: Unable to allocate 4GB buffer on local GPU.")

if __name__ == "__main__":
    simulate_system_failure()