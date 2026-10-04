"""Export the running backend contract without starting a server or calling AI."""

import argparse
import json

from apexdefend.api import create_app
from apexdefend.config import ROOT

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
path = ROOT / "contracts/openapi.json"
text = json.dumps(create_app().openapi(), ensure_ascii=False, indent=2) + "\n"
if args.check:
    assert path.read_text() == text, "OpenAPI has changed; run python scripts/export_openapi.py"
    print("OpenAPI export is current.")
else:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    print(path)
