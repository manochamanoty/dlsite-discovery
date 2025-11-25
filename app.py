import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dlsite_app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
