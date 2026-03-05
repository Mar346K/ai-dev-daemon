import time

print("INFO: Engine starting...")
time.sleep(1)
print("DEBUG: Loading assets...")
time.sleep(1)

# Rapid-fire identical errors (Deduplication should block the second one)
print("Exception: Texture failed to load at 0x00A1")
print("Exception: Texture failed to load at 0x00A1")

time.sleep(1)
print("INFO: Engine shutting down.")