import json
from pathlib import Path
from typing import Union
from ..models import EvaluationSummary


class JSONReporter:
    """Serializes structured evaluation results into machine-readable JSON."""

    def save(self, summary: EvaluationSummary, output_path: Union[str, Path]) -> Path:
        """Save the summary to target path, creating directories as needed."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target, "w", encoding="utf-8") as f:
            f.write(summary.model_dump_json(indent=2))
            
        return target
