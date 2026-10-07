from pathlib import Path
import sys

# Make the ML service package importable when tests are run from the repository root.
SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
