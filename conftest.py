import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
python_dir = root_dir / "python"

if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(python_dir) not in sys.path:
    sys.path.insert(0, str(python_dir))
