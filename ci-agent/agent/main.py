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
from .parsers.yaml_parser import YAMLParser
from .analyzers.dag_analyzer import DAGAnalyzer
from .analyzers.caching_analyzer import CachingAnalyzer
from .output.suggestion_formatter import SuggestionFormatter
from .output.autofix_handler import AutofixHandler
from .fixers.yaml_fixer import YAMLFixer
from .fixers.caching_fixer import CachingFixer
from .fixers.parallelizer import JobParallelizer
from .fixers.step_reorderer import StepReorderer

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
        self.yaml_parser = YAMLParser()
        self.dag_analyzer = DAGAnalyzer()
        self.caching_analyzer = CachingAnalyzer()
        self.suggestion_formatter = SuggestionFormatter(console=self.console)
        self.autofix_handler = AutofixHandler(
            console=self.console,
            dry_run=self.config.autofix.dry_run,
            interactive=self.config.autofix.interactive
        )
        
        # Initialize fixers
        self.yaml_fixer = YAMLFixer()
        self.caching_fixer = CachingFixer()
        self.job_parallelizer = JobParallelizer()
        self.step_reorderer = StepReorderer()
        
        # Track issues and fixes
        self.issues: List[Dict[str, Any]] = []
        self.fixes: List[Dict[str, Any]] = []
        self.suggestions: List[Dict[str, Any]] = []
        self.workflow_contents: Dict[str, str] = {}
        self.parsed_workflows: Dict[str, Any] = {}  # Store parsed workflow data
        
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
            
            # Store workflow contents for later use
            for wf in workflow_files:
                if wf.content:
                    self.workflow_contents[str(wf.relative_path)] = wf.content
            
            # Phase 2: Analysis
            task = progress.add_task("Analyzing workflows...", total=len(workflow_files))
            for i, wf in enumerate(workflow_files):
                if wf.content:
                    self._analyze_workflow(wf)
                progress.update(task, advance=1)
            
            # Phase 3: Generate fixes
            if self.issues:
                task = progress.add_task("Generating optimizations...", total=len(self.issues))
                self._generate_fixes()
                progress.update(task, completed=len(self.issues))
            
            # Phase 4: Apply fixes (if in autofix mode)
            if self.config.general.mode == "autofix" and self.fixes:
                task = progress.add_task("Applying fixes...", total=len(self.fixes))
                successful_fixes, failed_fixes = self.autofix_handler.apply_fixes(
                    self.fixes,
                    self.workflow_contents
                )
                progress.update(task, completed=len(self.fixes))
                
                if successful_fixes > 0:
                    logger.info(f"✅ Successfully applied {successful_fixes} fix(es)")
                if failed_fixes > 0:
                    logger.warning(f"⚠️  Failed to apply {failed_fixes} fix(es)")
        
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
        
        # Secret detection
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
        
        # YAML parsing and validation
        parsed_workflow = self.yaml_parser.parse_workflow(
            workflow_file.content,
            workflow_file.path
        )
        
        # Store parsed workflow data for later use
        self.parsed_workflows[str(workflow_file.relative_path)] = {
            "platform": parsed_workflow.platform,
            "data": parsed_workflow.parsed_data,
            "is_valid": parsed_workflow.is_valid
        }
        
        # Add YAML issues
        for yaml_issue in parsed_workflow.issues:
            self.issues.append({
                "type": yaml_issue.type,
                "severity": yaml_issue.severity,
                "file": workflow_file.relative_path,
                "line": yaml_issue.line,
                "column": yaml_issue.column,
                "message": yaml_issue.message,
                "suggestion": yaml_issue.suggestion
            })
        
        # Only continue with further analysis if YAML is valid
        if parsed_workflow.is_valid and parsed_workflow.parsed_data:
            # DAG analysis
            dag_analysis = self.dag_analyzer.analyze_workflow(
                parsed_workflow.parsed_data,
                parsed_workflow.platform
            )
            
            # Add dependency issues
            for dep_issue in dag_analysis.dependency_issues:
                self.issues.append({
                    "type": "dependency",
                    "severity": dep_issue.get("severity", "medium"),
                    "file": workflow_file.relative_path,
                    "line": 1,  # DAG issues don't have specific line numbers
                    "column": 1,
                    "message": dep_issue.get("message", "Dependency issue"),
                    "suggestion": dep_issue.get("suggestion")
                })
            
            # Add optimization suggestions from DAG analysis
            for suggestion in dag_analysis.optimization_suggestions:
                self.suggestions.append({
                    "type": suggestion.get("type", "optimization"),
                    "severity": suggestion.get("severity", "low"),
                    "file": workflow_file.relative_path,
                    "message": suggestion.get("message", ""),
                    "suggestion": suggestion.get("suggestion", ""),
                    "job": suggestion.get("job") or suggestion.get("jobs", [])
                })
            
            # Caching analysis
            cache_analysis = self.caching_analyzer.analyze_caching(
                parsed_workflow.parsed_data,
                parsed_workflow.platform
            )
            
            # Add cache optimization opportunities as issues
            for opportunity in cache_analysis.optimization_opportunities:
                self.issues.append({
                    "type": "caching",
                    "severity": opportunity.get("severity", "medium"),
                    "file": workflow_file.relative_path,
                    "line": 1,
                    "column": 1,
                    "message": opportunity.get("message", "Cache optimization opportunity"),
                    "suggestion": f"Add caching for {', '.join(opportunity.get('package_managers', []))}",
                    "job": opportunity.get("job"),
                    "cache_config": self._generate_cache_config(opportunity)
                })
            
            # Add cache suggestions
            for suggestion in cache_analysis.suggested_improvements:
                self.suggestions.append({
                    "type": "caching",
                    "severity": suggestion.get("severity", "medium"),
                    "file": workflow_file.relative_path,
                    "message": suggestion.get("message", ""),
                    "suggestion": suggestion.get("suggestion", ""),
                    "job": suggestion.get("job"),
                    "cache_config": suggestion.get("cache_config")
                })
            
            # Check for step ordering issues
            if self.config.optimization.reorder_steps:
                step_suggestions = self.step_reorderer.analyze_step_order(
                    parsed_workflow.parsed_data,
                    parsed_workflow.platform
                )
                self.suggestions.extend(step_suggestions)
    
    def _generate_cache_config(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate cache configuration for an optimization opportunity.
        
        Args:
            opportunity: Cache optimization opportunity
            
        Returns:
            Cache configuration dict
        """
        package_managers = opportunity.get("package_managers", [])
        cache_configs = []
        
        for pm in package_managers:
            pm_info = self.caching_analyzer.PACKAGE_MANAGERS.get(pm, {})
            if pm_info:
                cache_configs.append({
                    "key": f"${{{{ runner.os }}}}-{pm}-${{{{ hashFiles('{pm_info.get('lockfile', '**/package-lock.json')}') }}}}",
                    "restore-keys": [
                        f"${{{{ runner.os }}}}-{pm}-",
                        f"${{{{ runner.os }}}}-"
                    ],
                    "path": pm_info.get("cache_paths", [])
                })
        
        # Return the first config or a generic one
        return cache_configs[0] if cache_configs else {
            "key": "${{ runner.os }}-deps-${{ hashFiles('**/package-lock.json') }}",
            "restore-keys": ["${{ runner.os }}-deps-"],
            "path": ["node_modules"]
        }
    
    def _generate_fixes(self) -> None:
        """
        Generate fixes for discovered issues.
        """
        logger.debug("Generating fixes for issues")
        
        # Group issues by file
        issues_by_file = {}
        for issue in self.issues:
            file_path = str(issue["file"])
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)
        
        # Generate fixes for each file
        for file_path, file_issues in issues_by_file.items():
            content = self.workflow_contents.get(file_path, "")
            if not content:
                continue
            
            # Get parsed workflow data if available
            parsed_data = self.parsed_workflows.get(file_path, {})
            platform = parsed_data.get("platform", "github_actions")
            
            # Process different types of issues
            for issue in file_issues:
                fix = None
                issue_type = issue["type"]
                
                # YAML syntax fixes
                if issue_type == "syntax":
                    fix = self._generate_yaml_fix(issue, content, file_path)
                
                # Caching fixes
                elif issue_type == "caching" and issue.get("cache_config"):
                    fix = {
                        "type": "add_cache",
                        "file": file_path,
                        "job": issue.get("job"),
                        "message": f"Add caching for job '{issue.get('job')}'",
                        "cache_config": issue["cache_config"],
                        "fixer_type": "cache",
                        "platform": platform,
                        "fixer_function": lambda c, cfg=issue["cache_config"], job=issue.get("job"), p=platform: 
                            self.caching_fixer.add_cache_to_workflow(c, job, cfg, p)
                    }
                
                # Dependency optimization fixes
                elif issue_type == "dependency" and "redundant" in issue.get("message", "").lower():
                    # This will be handled by the parallelizer
                    if not any(f["type"] == "optimize_parallelization" and f["file"] == file_path for f in self.fixes):
                        fix = {
                            "type": "optimize_parallelization",
                            "file": file_path,
                            "message": "Optimize job parallelization",
                            "fixer_type": "parallelizer",
                            "platform": platform,
                            "workflow_data": parsed_data.get("data", {}),
                            "fixer_function": lambda c, wd=parsed_data.get("data", {}), p=platform:
                                self.job_parallelizer.optimize_parallelization(c, wd, p)[0]
                        }
                
                if fix:
                    self.fixes.append(fix)
        
        # Also check suggestions for fixable items
        for suggestion in self.suggestions:
            fix = None
            
            # Step reordering suggestions
            if suggestion.get("type") == "step_order":
                job_name = suggestion.get("job")
                file_path = str(suggestion.get("file", ""))
                if job_name and file_path:
                    fix = {
                        "type": "reorder_steps",
                        "file": file_path,
                        "job": job_name,
                        "message": f"Reorder steps in job '{job_name}' for optimal execution",
                        "fixer_type": "step_reorderer",
                        "platform": self.parsed_workflows.get(file_path, {}).get("platform", "github_actions"),
                        "fixer_function": lambda c, j=job_name, p=self.parsed_workflows.get(file_path, {}).get("platform", "github_actions"):
                            self.step_reorderer.reorder_steps(c, j, p)[0]
                    }
            
            if fix and not any(f["file"] == fix["file"] and f["type"] == fix["type"] for f in self.fixes):
                self.fixes.append(fix)
        
        logger.info(f"Generated {len(self.fixes)} fix(es) for {len(self.issues)} issue(s)")
    
    def _generate_yaml_fix(self, issue: Dict[str, Any], content: str, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Generate a fix for a YAML syntax issue.
        
        Args:
            issue: The issue to fix
            content: Current file content
            file_path: Path to the file
            
        Returns:
            Fix dictionary or None
        """
        message = issue.get("message", "").lower()
        suggestion = issue.get("suggestion", "").lower()
        
        fix_type = None
        fix_message = ""
        
        # Determine fix type based on issue
        if "tab" in message or "tab" in suggestion:
            fix_type = "tabs_to_spaces"
            fix_message = "Replace tabs with spaces"
        elif "trailing" in message and "whitespace" in message:
            fix_type = "trailing_whitespace"
            fix_message = "Remove trailing whitespace"
        elif "quote" in message:
            fix_type = "quotes"
            fix_message = "Fix unmatched quotes"
        elif any(typo in message for typo in ["run-on", "need:", "typo"]):
            fix_type = "typos"
            fix_message = "Fix common typos"
        elif "indent" in message:
            fix_type = "indentation"
            fix_message = "Fix indentation"
        
        if fix_type:
            return {
                "type": fix_type,
                "file": file_path,
                "line": issue.get("line", 1),
                "message": fix_message,
                "fixer_type": "yaml",
                "fixer_function": lambda c, ft=fix_type, line=issue.get("line"):
                    self.yaml_fixer.fix_content(c, ft, line=line)
            }
        
        return None
    
    def _output_results(self) -> None:
        """
        Output the results of the analysis.
        """
        if not self.issues and not self.suggestions:
            self.console.print("[green]✅ No issues found![/green]")
            return
        
        # Use the suggestion formatter for proper output
        if self.config.general.mode == "suggest" or not self.fixes:
            self.suggestion_formatter.format_issues(
                self.issues,
                self.workflow_contents,
                group_by_file=True
            )
            
            if self.suggestions:
                self.suggestion_formatter.format_suggestions(
                    self.suggestions,
                    show_examples=self.config.output.include_explanations
                ) 