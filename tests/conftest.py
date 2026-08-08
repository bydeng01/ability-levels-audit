import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# vendor/ FIRST so the vendored regular packages (analysis, protocol, agents, domain)
# shadow this repo's same-named plain directories.
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
