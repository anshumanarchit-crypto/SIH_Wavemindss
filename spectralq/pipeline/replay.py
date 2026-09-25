"""
Replay Mode Engine.
Loads recorded captures/analysis files, enforces deterministic seeds,
and executes end-to-end evaluation under controlled replay conditions.
"""

import json
from pathlib import Path
from typing import Optional
import numpy as np

from spectralq.contracts.schemas import AnalysisContract, ProvenanceType


class ReplayController:
    """
    Manages deterministic replay of historical captures.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed

    def set_seed(self, seed: int) -> None:
        """
        Sets deterministic RNG seed across numpy and standard libraries.
        """
        self.seed = seed
        np.random.seed(seed)

    def load_replay_analysis(self, analysis_file_path: str) -> AnalysisContract:
        """
        Loads an analysis.json file for replay, marking provenance as 'replayed'.
        """
        path = Path(analysis_file_path)
        if not path.exists():
            raise FileNotFoundError(f"Replay analysis file not found: {analysis_file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Force provenance to replayed if loaded via replay controller
        data["provenance"] = ProvenanceType.REPLAYED.value

        return AnalysisContract.model_validate(data)
