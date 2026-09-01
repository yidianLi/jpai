"""Validate collaboration configuration; exits non-zero on structural errors."""
from app.core.orchestration import orchestration_config

result = orchestration_config.health()
if result["ok"]:
    print(f"OK: {len(result['agents'])} agents, workflow={result['workflow']}")
else:
    for error in result["errors"]:
        print(f"ERROR: {error}")
    raise SystemExit(1)
