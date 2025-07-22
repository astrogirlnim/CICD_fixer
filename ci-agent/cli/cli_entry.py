#!/usr/bin/env python3
"""
CI/CD Fixer CLI Entry Point

This module provides the main command-line interface for the CI/CD optimization tool.
It handles command parsing, argument validation, and orchestrates the optimization process.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.logging import RichHandler

# Import our modules (will be implemented next)
from agent.main import CIOptimizerAgent
from agent.config_loader import Config, load_config
from agent.exit_handler import ExitCode, handle_exit

# Initialize Typer app and Rich console
app = typer.Typer(
    name="cicd-fixer",
    help="AI-powered CI/CD pipeline optimizer for GitHub Actions and GitLab CI",
    add_completion=True,
)
console = Console()

# Version information
__version__ = "0.1.0"

# Configure logging with Rich handler for beautiful output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)


def version_callback(value: bool) -> None:
    """Display version information and exit."""
    if value:
        console.print(f"[bold blue]CI/CD Fixer[/bold blue] version {__version__}")
        console.print("AI-powered CI/CD pipeline optimizer")
        console.print("For more info: https://github.com/cicd-fixer/cicd-fixer")
        raise typer.Exit(0)


@app.command()
def main(
    # File/directory options
    path: Optional[Path] = typer.Argument(
        None,
        help="Path to analyze (defaults to current directory)",
        exists=True,
        file_okay=True,
        dir_okay=True,
    ),
    file: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="Specific workflow file to analyze",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    # Mode options
    autofix: bool = typer.Option(
        False,
        "--autofix",
        "-a",
        help="Automatically apply fixes (interactive by default, use --yes for non-interactive)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Show what would be changed without applying fixes",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Auto-confirm all fixes (non-interactive mode)",
    ),
    # Configuration options
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file (default: .cicd-fixer.yml)",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    no_config: bool = typer.Option(
        False,
        "--no-config",
        help="Ignore configuration file",
    ),
    # Cloud/LLM options
    no_cloud: bool = typer.Option(
        False,
        "--no-cloud",
        help="Disable all external API calls (LLMs, knowledge bases)",
    ),
    # Output options
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase verbosity (-v, -vv, -vvv for more detail)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (errors only)",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable colored output",
    ),
    format: str = typer.Option(
        "console",
        "--format",
        help="Output format: console, json, github (for PR comments)",
    ),
    # Behavior options
    exit_on_issues: bool = typer.Option(
        False,
        "--exit-on-issues",
        help="Exit with non-zero code if issues are found",
    ),
    max_issues: Optional[int] = typer.Option(
        None,
        "--max-issues",
        help="Maximum number of issues to report",
    ),
    # Version
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """
    Analyze and optimize CI/CD pipeline configurations.
    
    By default, runs in suggestion mode on the current directory.
    Use --autofix to automatically apply suggested fixes.
    """
    # Log startup
    logger.info(f"🚀 Starting CI/CD Fixer v{__version__}")
    
    # Set up logging level based on verbosity
    if quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif verbose == 0:
        logging.getLogger().setLevel(logging.INFO)
    elif verbose == 1:
        logging.getLogger().setLevel(logging.DEBUG)
    else:  # verbose >= 2
        logging.getLogger().setLevel(logging.DEBUG)
        # Also show debug logs from our modules
        logging.getLogger("agent").setLevel(logging.DEBUG)
    
    # Disable color if requested
    if no_color:
        console.no_color = True
    
    # Determine target path
    target_path = path or Path.cwd()
    logger.debug(f"Target path: {target_path}")
    
    # Load configuration
    try:
        if no_config:
            logger.info("📋 Using default configuration (--no-config specified)")
            config_obj = Config()  # Use defaults
        else:
            config_path = config or target_path / ".cicd-fixer.yml"
            logger.info(f"📋 Loading configuration from: {config_path}")
            config_obj = load_config(config_path)
        
        # Override config with CLI arguments
        if autofix:
            config_obj.general.mode = "autofix"
        if dry_run:
            config_obj.autofix.dry_run = True
        if yes:
            config_obj.autofix.interactive = False
        if no_cloud:
            config_obj.external_services.use_llm = False
        if max_issues:
            config_obj.output.max_issues = max_issues
        if format != "console":
            config_obj.output.format = format
        
        # Log effective configuration
        logger.debug(f"Effective configuration: {config_obj}")
        
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        handle_exit(ExitCode.FATAL_ERROR)
    
    # Initialize the optimizer agent
    try:
        logger.info("🔧 Initializing CI Optimizer Agent...")
        agent = CIOptimizerAgent(
            config=config_obj,
            target_path=target_path,
            specific_file=file,
            console=console,
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize agent: {e}")
        handle_exit(ExitCode.FATAL_ERROR)
    
    # Run the optimization process
    try:
        logger.info("🔍 Analyzing CI/CD configurations...")
        issues_found = agent.run()
        
        # Determine exit code
        if issues_found > 0 and exit_on_issues:
            logger.info(f"⚠️  Found {issues_found} issue(s)")
            handle_exit(ExitCode.ISSUES_FOUND)
        elif issues_found > 0:
            logger.info(f"✅ Analysis complete. Found {issues_found} issue(s)")
            handle_exit(ExitCode.SUCCESS)
        else:
            logger.info("✅ No issues found! Your CI/CD configuration looks good.")
            handle_exit(ExitCode.SUCCESS)
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Operation cancelled by user")
        handle_exit(ExitCode.FATAL_ERROR)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.debug("Full traceback:", exc_info=True)
        handle_exit(ExitCode.FATAL_ERROR)


@app.command()
def install_hooks(
    pre_commit: bool = typer.Option(True, help="Install pre-commit hook"),
    pre_push: bool = typer.Option(True, help="Install pre-push hook"),
    force: bool = typer.Option(False, help="Overwrite existing hooks"),
) -> None:
    """Install git hooks for automatic CI/CD checking."""
    logger.info("🔗 Installing git hooks...")
    
    git_dir = Path(".git")
    if not git_dir.exists():
        logger.error("❌ Not in a git repository!")
        handle_exit(ExitCode.FATAL_ERROR)
    
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    
    # Install pre-commit hook
    if pre_commit:
        hook_path = hooks_dir / "pre-commit"
        if hook_path.exists() and not force:
            logger.warning(f"⚠️  Pre-commit hook already exists. Use --force to overwrite")
        else:
            hook_content = """#!/bin/sh
# CI/CD Fixer pre-commit hook
echo "🔍 Checking CI/CD configurations..."
cicd-fixer --quiet --exit-on-issues
"""
            hook_path.write_text(hook_content)
            hook_path.chmod(0o755)
            logger.info("✅ Installed pre-commit hook")
    
    # Install pre-push hook
    if pre_push:
        hook_path = hooks_dir / "pre-push"
        if hook_path.exists() and not force:
            logger.warning(f"⚠️  Pre-push hook already exists. Use --force to overwrite")
        else:
            hook_content = """#!/bin/sh
# CI/CD Fixer pre-push hook
echo "🔍 Final CI/CD check before push..."
cicd-fixer --exit-on-issues
"""
            hook_path.write_text(hook_content)
            hook_path.chmod(0o755)
            logger.info("✅ Installed pre-push hook")
    
    logger.info("✅ Git hooks installed successfully!")


@app.command()
def check() -> None:
    """Alias for the main command in suggestion mode."""
    # Just call main with default arguments
    main(
        path=None,
        file=None,
        autofix=False,
        dry_run=False,
        config=None,
        no_config=False,
        no_cloud=False,
        verbose=0,
        quiet=False,
        no_color=False,
        format="console",
        exit_on_issues=True,
        max_issues=None,
        version=None,
    )


if __name__ == "__main__":
    app() 