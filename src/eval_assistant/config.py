import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class EvalConfig(BaseSettings):
    """Configuration settings for the Evaluation Assistant framework."""
    
    # Paths
    project_root: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = project_root / "data"
    default_test_suite: Path = data_dir / "test_cases.json"
    output_dir: Path = project_root / "reports"
    
    # Mode & Execution
    eval_mode: str = Field(default="hybrid", description="Modes: hybrid, deterministic_only, offline_simulation")
    deterministic_strict: bool = Field(default=True, description="Strict failure on any deterministic violation")
    
    # LLM Provider settings (Gemini, OpenAI, or offline)
    llm_provider: str = Field(default="offline", description="offline, gemini, or openai")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    
    # Thresholds
    min_model_confidence_threshold: float = Field(default=0.80, description="Minimum confidence for model judge; lower flags review")
    grounding_overlap_threshold: float = Field(default=0.70, description="Minimum entity/token overlap for grounding verification")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# Singleton instance
config = EvalConfig()
