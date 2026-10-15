"""
CLI script to generate sample dataset in approved lab directory.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from restorelab.config import get_settings
from restorelab.verification.sample_data import generate_lab_dataset

if __name__ == "__main__":
    settings = get_settings()
    target = settings.resolved_source_dir
    print(f"Generating test dataset in {target}...")
    files, total_bytes = generate_lab_dataset(target)
    print(f"Success: created {files} files ({total_bytes} bytes).")
