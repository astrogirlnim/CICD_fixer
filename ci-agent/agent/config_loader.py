"""
Configuration Loader Module

Handles loading and merging configuration from:
1. Configuration file (.cicd-fixer.yml)
2. Environment variables
3. CLI arguments
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import yaml
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
load_dotenv()


class GeneralConfig(BaseModel):
    """General application settings."""
    platforms: Dict[str, bool] = Field(
        default={"github_actions": True, "gitlab_ci": False},
        description="Enable/disable specific CI platforms"
    )
    mode: str = Field(
        default="suggest",
        description="Default mode: 'suggest' or 'autofix'"
    )
    color_output: bool = Field(default=True, description="Enable colored output")
    verbosity: int = Field(default=1, description="Verbosity level (0-3)")
    
    @validator("mode")
    def validate_mode(cls, v):
        if v not in ["suggest", "autofix"]:
            raise ValueError(f"Invalid mode: {v}. Must be 'suggest' or 'autofix'")
        return v


class FileConfig(BaseModel):
    """File handling configuration."""
    workflow_paths: List[str] = Field(
        default=[".github/workflows/", ".gitlab-ci.yml"],
        description="Paths to scan for workflow files"
    )
    exclude: List[str] = Field(
        default=["**/test-*.yml", "**/experimental-*.yml"],
        description="Exclude patterns (glob)"
    )
    max_file_size: int = Field(
        default=500,
        description="Maximum file size to process (in KB)"
    )


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = Field(default="openai", description="LLM provider")
    model: str = Field(default="gpt-4", description="Model to use")
    api_key_env: str = Field(
        default="OPENAI_API_KEY",
        description="Environment variable name for API key"
    )
    max_tokens: int = Field(default=2000, description="Maximum tokens")
    temperature: float = Field(default=0.3, description="Temperature setting")


class PrivacyConfig(BaseModel):
    """Privacy settings for external services."""
    redact_secrets: bool = Field(
        default=True,
        description="Redact secrets before sending to external services"
    )
    sensitive_patterns: List[str] = Field(
        default=["secrets\\..*", ".*_TOKEN", ".*_KEY", ".*_PASSWORD"],
        description="Patterns to never send to external services"
    )


class ExternalServicesConfig(BaseModel):
    """External services configuration."""
    use_llm: bool = Field(
        default=True,
        description="Enable LLM-powered suggestions"
    )
    llm: LLMConfig = Field(default_factory=LLMConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)


class YAMLOptimizationConfig(BaseModel):
    """YAML-specific optimization settings."""
    fix_indentation: bool = Field(default=True)
    fix_invalid_keys: bool = Field(default=True)
    validate_schema: bool = Field(default=True)


class CachingOptimizationConfig(BaseModel):
    """Caching optimization settings."""
    suggest_restore_keys: bool = Field(default=True)
    optimize_paths: bool = Field(default=True)
    add_cache_timing: bool = Field(default=True)


class ParallelizationConfig(BaseModel):
    """Job parallelization settings."""
    analyze_dependencies: bool = Field(default=True)
    suggest_parallel_jobs: bool = Field(default=True)
    respect_explicit_deps: bool = Field(default=True)


class StepReorderingConfig(BaseModel):
    """Step reordering settings."""
    optimize_for_cache: bool = Field(default=True)
    group_similar_steps: bool = Field(default=True)
    preserve_logical_order: bool = Field(default=True)


class OptimizationsConfig(BaseModel):
    """All optimization settings."""
    yaml: YAMLOptimizationConfig = Field(default_factory=YAMLOptimizationConfig)
    caching: CachingOptimizationConfig = Field(default_factory=CachingOptimizationConfig)
    parallelization: ParallelizationConfig = Field(default_factory=ParallelizationConfig)
    step_reordering: StepReorderingConfig = Field(default_factory=StepReorderingConfig)


class OutputConfig(BaseModel):
    """Output formatting settings."""
    show_diffs: bool = Field(default=True)
    diff_format: str = Field(default="unified")
    include_explanations: bool = Field(default=True)
    max_issues: int = Field(default=50)
    format: str = Field(default="console")


class AutofixConfig(BaseModel):
    """Auto-fix settings."""
    create_backups: bool = Field(default=True)
    backup_suffix: str = Field(default=".bak")
    dry_run: bool = Field(default=False)
    interactive: bool = Field(default=True)


class PerformanceConfig(BaseModel):
    """Performance settings."""
    timeout_per_file: int = Field(default=30)
    parallel_processing: bool = Field(default=True)
    max_workers: int = Field(default=4)


class ExitCodesConfig(BaseModel):
    """Exit code mappings."""
    success: int = Field(default=0)
    issues_found: int = Field(default=1)
    fatal_error: int = Field(default=2)


class ReportingConfig(BaseModel):
    """Reporting settings."""
    exit_codes: ExitCodesConfig = Field(default_factory=ExitCodesConfig)
    show_summary: bool = Field(default=True)
    metrics: List[str] = Field(
        default=["pipeline_duration", "cache_hit_rate", "parallel_efficiency"]
    )


class Config(BaseModel):
    """Main configuration object."""
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    files: FileConfig = Field(default_factory=FileConfig)
    external_services: ExternalServicesConfig = Field(default_factory=ExternalServicesConfig)
    optimizations: OptimizationsConfig = Field(default_factory=OptimizationsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    autofix: AutofixConfig = Field(default_factory=AutofixConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)


def load_config(config_path: Union[str, Path] = None) -> Config:
    """
    Load configuration from file and environment variables.
    
    Args:
        config_path: Path to configuration file (optional)
        
    Returns:
        Loaded configuration object
    """
    logger.debug(f"Loading configuration from: {config_path}")
    
    # Start with default configuration
    config_dict = {}
    
    # Load from file if it exists
    if config_path:
        config_path = Path(config_path)
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
                    config_dict = file_config
                    logger.info(f"✅ Loaded configuration from {config_path}")
            except Exception as e:
                logger.error(f"Failed to load config file: {e}")
                raise
        else:
            logger.debug(f"Config file not found: {config_path}")
    
    # Override with environment variables
    config_dict = merge_env_vars(config_dict)
    
    # Create and validate configuration object
    try:
        config = Config(**config_dict)
        logger.debug("Configuration loaded successfully")
        return config
    except Exception as e:
        logger.error(f"Invalid configuration: {e}")
        raise


def merge_env_vars(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge environment variables into configuration dictionary.
    
    Environment variables follow the pattern:
    CICD_FIXER_<SECTION>_<KEY>
    
    For example:
    - CICD_FIXER_GENERAL_MODE=autofix
    - CICD_FIXER_AUTOFIX_DRY_RUN=true
    
    Args:
        config_dict: Existing configuration dictionary
        
    Returns:
        Updated configuration dictionary
    """
    logger.debug("Checking for environment variable overrides")
    
    # Map of environment variables to config paths
    env_mappings = {
        "CICD_FIXER_MODE": ["general", "mode"],
        "CICD_FIXER_AUTOFIX": ["general", "mode"],  # Convenience alias
        "CICD_FIXER_VERBOSITY": ["general", "verbosity"],
        "CICD_FIXER_NO_COLOR": ["general", "color_output"],
        "CICD_FIXER_USE_LLM": ["external_services", "use_llm"],
        "CICD_FIXER_LLM_PROVIDER": ["external_services", "llm", "provider"],
        "CICD_FIXER_LLM_MODEL": ["external_services", "llm", "model"],
        "CICD_FIXER_MAX_ISSUES": ["output", "max_issues"],
        "CICD_FIXER_DRY_RUN": ["autofix", "dry_run"],
        "CICD_FIXER_INTERACTIVE": ["autofix", "interactive"],
        "CICD_FIXER_PARALLEL": ["performance", "parallel_processing"],
        "CICD_FIXER_MAX_WORKERS": ["performance", "max_workers"],
    }
    
    for env_var, config_path in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            logger.debug(f"Found environment variable: {env_var}={value}")
            
            # Convert string values to appropriate types
            if value.lower() in ["true", "false"]:
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            elif env_var == "CICD_FIXER_AUTOFIX" and value.lower() == "true":
                value = "autofix"
            elif env_var == "CICD_FIXER_NO_COLOR" and value.lower() == "true":
                value = False  # Invert for color_output
            
            # Apply the override
            set_nested_value(config_dict, config_path, value)
            logger.info(f"📝 Override from env: {'.'.join(config_path)} = {value}")
    
    return config_dict


def set_nested_value(d: Dict[str, Any], path: List[str], value: Any) -> None:
    """
    Set a value in a nested dictionary using a path.
    
    Args:
        d: Dictionary to update
        path: List of keys representing the path
        value: Value to set
    """
    # Create nested structure if it doesn't exist
    current = d
    for key in path[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    # Set the value
    current[path[-1]] = value 


def save_config(config: Config, path: Union[str, Path]) -> None:
    """
    Save configuration to a YAML file.
    
    Args:
        config: Configuration object to save
        path: Path to save the configuration
    """
    path = Path(path)
    
    try:
        # Convert to dictionary and remove defaults
        config_dict = config.dict(exclude_defaults=True)
        
        # Write to file
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"✅ Saved configuration to {path}")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        raise 