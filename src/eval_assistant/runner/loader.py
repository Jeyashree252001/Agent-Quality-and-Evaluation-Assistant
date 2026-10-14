import json
from pathlib import Path
from typing import List, Union
from ..models import TestCase


def load_test_suite(path: Union[str, Path]) -> List[TestCase]:
    """
    Load and validate test cases from a JSON file.
    
    Args:
        path: Path to the test suite JSON file.
        
    Returns:
        List of validated TestCase instances.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Test suite file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON array of test cases, got {type(raw_data).__name__}")

    test_cases = [TestCase(**item) for item in raw_data]
    return test_cases
