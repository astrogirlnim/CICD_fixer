"""
Main CI Optimizer Agent Module

This is the central orchestrator that coordinates all components of the
CI/CD optimization process.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

from .config_loader import Config
from .file_loader import find_workflow_files, load_all_files, filter_by_platform, WorkflowFile
from .secrets_redactor import SecretsRedactor
from .exit_handler import ExitCode

# Import modules that will be implemented in later phases
# For now, we'll create placeholder implementations

logger = logging.getLogger(__name__)


class CIOptimizerAgent:
    """
    Main agent that coordinates the CI/CD optimization process.
    """
    
    def __init__(
        self,
        config: Config,
        target_path: Path,
        specific_file: Optional[Path] = None,
        console: Optional[Console] = None
    ):
        """
        Initialize the CI Optimizer Agent.
        
        Args:
            config: Configuration object
            target_path: Path to analyze
            specific_file: Optional specific file to analyze
            console: Rich console for output
        """
        self.config = config
        self.target_path = target_path
        self.specific_file = specific_file
        self.console = console or Console()
        
        # Initialize components
        self.secrets_redactor = SecretsRedactor()
        
        # Track issues and fixes
        self.issues: List[Dict[str, Any]] = []
        self.fixes_applied: List[Dict[str, Any]] = []
        
        logger.debug(f"Initialized agent for {target_path}")
    
    def run(self) -> int:
        """
        Run the CI optimization process.
        
        Returns:
            Number of issues found
        """
        logger.info("🚀 Starting CI/CD optimization process")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            # Phase 1: File Discovery
            task = progress.add_task("Discovering workflow files...", total=None)
            workflow_files = self._discover_files()
            progress.update(task, completed=True)
            
            if not workflow_files:
                logger.warning("⚠️  No workflow files found")
                return 0
            
            # Load file contents
            task = progress.add_task("Loading workflow files...", total=len(workflow_files))
            successful, failed = load_all_files(workflow_files)
            progress.update(task, completed=len(workflow_files))
            
            if failed > 0:
                logger.warning(f"⚠️  Failed to load {failed} files")
            
            # Phase 2: Analysis (placeholder for now)
            task = progress.add_task("Analyzing workflows...", total=len(workflow_files))
            for i, wf in enumerate(workflow_files):
                if wf.content:
                    self._analyze_workflow(wf)
                progress.update(task, advance=1)
            
            # Phase 3: Generate fixes (placeholder for now)
            if self.issues:
                task = progress.add_task("Generating optimizations...", total=len(self.issues))
                self._generate_fixes()
                progress.update(task, completed=len(self.issues))
            
            # Phase 4: Apply fixes (if in autofix mode)
            if self.config.general.mode == "autofix" and self.issues:
                task = progress.add_task("Applying fixes...", total=len(self.issues))
                self._apply_fixes()
                progress.update(task, completed=len(self.issues))
        
        # Output results
        self._output_results()
        
        return len(self.issues)
    
    def _discover_files(self) -> List[WorkflowFile]:
        """
        Discover workflow files based on configuration.
        
        Returns:
            List of discovered workflow files
        """
        logger.debug("Discovering workflow files")
        
        # Find files
        workflow_files = find_workflow_files(
            root_path=self.target_path,
            workflow_paths=self.config.files.workflow_paths,
            exclude_patterns=self.config.files.exclude,
            max_file_size_kb=self.config.files.max_file_size,
            specific_file=self.specific_file
        )
        
        # Filter by platform
        workflow_files = filter_by_platform(
            workflow_files,
            self.config.general.platforms
        )
        
        return workflow_files
    
    def _analyze_workflow(self, workflow_file: WorkflowFile) -> None:
        """
        Analyze a single workflow file for issues.
        
        Args:
            workflow_file: The workflow file to analyze
        """
        logger.debug(f"Analyzing {workflow_file.relative_path}")
        
        # For now, just demonstrate the secrets redactor
        if self.config.external_services.privacy.redact_secrets:
            redacted_content, secrets = self.secrets_redactor.redact_content(workflow_file.content)
            if secrets:
                for secret in secrets:
                    self.issues.append({
                        "type": "security",
                        "severity": "high",
                        "file": workflow_file.relative_path,
                        "line": secret.line_number,
                        "column": secret.column_start,
                        "message": f"Detected {secret.pattern_name} - consider using secrets management",
                        "fix": None  # No auto-fix for secrets
                    })
        
        # Placeholder for other analyzers (will be implemented in Phase 2)
        # - YAML syntax validation
        # - Schema validation
        # - DAG analysis
        # - Caching analysis
        
        # For demonstration, add a placeholder issue
        self.issues.append({
            "type": "optimization",
            "severity": "medium",
            "file": workflow_file.relative_path,
            "line": 1,
            "column": 1,
            "message": "Workflow analysis pending full implementation",
            "fix": None
        })
    
    def _generate_fixes(self) -> None:
        """
        Generate fixes for discovered issues.
        """
        logger.debug("Generating fixes for issues")
        
        # Placeholder - will be implemented in Phase 4
        # This will use the various fixer modules to generate fixes
        pass
    
    def _apply_fixes(self) -> None:
        """
        Apply generated fixes to files.
        """
        logger.debug("Applying fixes")
        
        # Placeholder - will be implemented in Phase 3
        # This will use the autofix handler to apply changes
        pass
    
    def _output_results(self) -> None:
        """
        Output the results of the analysis.
        """
        if not self.issues:
            self.console.print("[green]✅ No issues found![/green]")
            return
        
        # Group issues by file
        issues_by_file = {}
        for issue in self.issues:
            file_path = str(issue["file"])
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)
        
        # Output issues
        self.console.print(f"\n[yellow]Found {len(self.issues)} issue(s):[/yellow]\n")
        
        for file_path, file_issues in issues_by_file.items():
            self.console.print(f"[bold]{file_path}[/bold]")
            
            for issue in file_issues:
                severity_color = {
                    "high": "red",
                    "medium": "yellow",
                    "low": "blue"
                }.get(issue["severity"], "white")
                
                self.console.print(
                    f"  [{severity_color}]●[/{severity_color}] "
                    f"Line {issue['line']}: {issue['message']}"
                )
                
                if issue.get("fix") and self.config.output.include_explanations:
                    self.console.print(f"    💡 {issue['fix']}")
            
            self.console.print()  # Empty line between files
        
        # Summary
        if self.config.reporting.show_summary:
            high_count = sum(1 for i in self.issues if i["severity"] == "high")
            medium_count = sum(1 for i in self.issues if i["severity"] == "medium")
            low_count = sum(1 for i in self.issues if i["severity"] == "low")
            
            self.console.print("[bold]Summary:[/bold]")
            if high_count:
                self.console.print(f"  [red]High severity: {high_count}[/red]")
            if medium_count:
                self.console.print(f"  [yellow]Medium severity: {medium_count}[/yellow]")
            if low_count:
                self.console.print(f"  [blue]Low severity: {low_count}[/blue]")
            
            if self.config.general.mode == "suggest":
                self.console.print(
                    f"\n💡 To apply fixes automatically, run with --autofix"
                ) 