"""
Suggestion Formatter Module

Formats and displays optimization suggestions and issues found in CI/CD workflows.
Provides clear, actionable output with diffs and explanations.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import difflib
from rich.console import Console, Group
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.columns import Columns
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FormattedIssue:
    """Represents a formatted issue ready for display."""
    file_path: Path
    line: int
    column: int
    severity: str
    type: str
    message: str
    suggestion: Optional[str] = None
    diff: Optional[str] = None
    context_lines: List[Tuple[int, str]] = None


class SuggestionFormatter:
    """
    Formats suggestions and issues for display in the console.
    """
    
    # Severity colors and icons
    SEVERITY_CONFIG = {
        'high': {'color': 'red', 'icon': '🔴', 'label': 'HIGH'},
        'medium': {'color': 'yellow', 'icon': '🟡', 'label': 'MEDIUM'},
        'low': {'color': 'blue', 'icon': '🔵', 'label': 'LOW'},
        'info': {'color': 'cyan', 'icon': 'ℹ️', 'label': 'INFO'}
    }
    
    # Issue type icons
    TYPE_ICONS = {
        'syntax': '🔤',
        'schema': '📋',
        'structure': '🏗️',
        'optimization': '⚡',
        'security': '🔒',
        'caching': '💾',
        'parallelization': '🔀',
        'dependency': '🔗',
        'performance': '🏃'
    }
    
    def __init__(self, console: Optional[Console] = None, show_context: bool = True):
        """
        Initialize the suggestion formatter.
        
        Args:
            console: Rich console for output
            show_context: Whether to show code context around issues
        """
        self.console = console or Console()
        self.show_context = show_context
        logger.debug("Initialized suggestion formatter")
    
    def format_issues(
        self,
        issues: List[Dict[str, Any]],
        workflow_files: Dict[str, str],
        group_by_file: bool = True
    ) -> None:
        """
        Format and display issues found in workflows.
        
        Args:
            issues: List of issues to format
            workflow_files: Dictionary mapping file paths to their content
            group_by_file: Whether to group issues by file
        """
        if not issues:
            self._display_no_issues()
            return
        
        # Convert to FormattedIssue objects
        formatted_issues = []
        for issue in issues:
            formatted = self._format_single_issue(issue, workflow_files)
            if formatted:
                formatted_issues.append(formatted)
        
        # Display header
        self._display_header(len(formatted_issues))
        
        # Display issues
        if group_by_file:
            self._display_grouped_by_file(formatted_issues)
        else:
            self._display_flat_list(formatted_issues)
        
        # Display summary
        self._display_summary(formatted_issues)
    
    def format_suggestions(
        self,
        suggestions: List[Dict[str, Any]],
        show_examples: bool = True
    ) -> None:
        """
        Format and display optimization suggestions.
        
        Args:
            suggestions: List of suggestions to format
            show_examples: Whether to show code examples
        """
        if not suggestions:
            return
        
        self.console.print("\n[bold cyan]💡 Optimization Suggestions[/bold cyan]\n")
        
        for i, suggestion in enumerate(suggestions, 1):
            self._display_suggestion(i, suggestion, show_examples)
    
    def format_diff(
        self,
        original: str,
        modified: str,
        file_path: str,
        context_lines: int = 3
    ) -> str:
        """
        Format a unified diff between original and modified content.
        
        Args:
            original: Original content
            modified: Modified content
            file_path: Path to the file
            context_lines: Number of context lines to show
            
        Returns:
            Formatted diff string
        """
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=context_lines
        )
        
        return ''.join(diff)
    
    def _format_single_issue(
        self,
        issue: Dict[str, Any],
        workflow_files: Dict[str, str]
    ) -> Optional[FormattedIssue]:
        """
        Format a single issue.
        
        Args:
            issue: Issue dictionary
            workflow_files: Workflow file contents
            
        Returns:
            FormattedIssue object or None
        """
        try:
            file_path = Path(issue.get('file', ''))
            
            # Get context lines if available
            context_lines = None
            if self.show_context and str(file_path) in workflow_files:
                context_lines = self._get_context_lines(
                    workflow_files[str(file_path)],
                    issue.get('line', 1),
                    context_size=2
                )
            
            return FormattedIssue(
                file_path=file_path,
                line=issue.get('line', 1),
                column=issue.get('column', 1),
                severity=issue.get('severity', 'info'),
                type=issue.get('type', 'unknown'),
                message=issue.get('message', 'No message provided'),
                suggestion=issue.get('suggestion') or issue.get('fix'),
                diff=issue.get('diff'),
                context_lines=context_lines
            )
        except Exception as e:
            logger.error(f"Error formatting issue: {e}")
            return None
    
    def _get_context_lines(
        self,
        content: str,
        target_line: int,
        context_size: int = 2
    ) -> List[Tuple[int, str]]:
        """
        Get context lines around a target line.
        
        Args:
            content: File content
            target_line: Target line number (1-indexed)
            context_size: Number of lines before and after
            
        Returns:
            List of (line_number, line_content) tuples
        """
        lines = content.splitlines()
        target_idx = target_line - 1
        
        start_idx = max(0, target_idx - context_size)
        end_idx = min(len(lines), target_idx + context_size + 1)
        
        context = []
        for i in range(start_idx, end_idx):
            line_num = i + 1
            context.append((line_num, lines[i]))
        
        return context
    
    def _display_no_issues(self) -> None:
        """Display message when no issues are found."""
        panel = Panel(
            "[green]✅ No issues found![/green]\n\n"
            "Your CI/CD configuration looks good. 🎉",
            title="[bold green]Analysis Complete[/bold green]",
            border_style="green"
        )
        self.console.print(panel)
    
    def _display_header(self, issue_count: int) -> None:
        """Display the header for issues."""
        self.console.print(
            f"\n[bold red]❌ Found {issue_count} issue{'s' if issue_count != 1 else ''}[/bold red]\n"
        )
    
    def _display_grouped_by_file(self, issues: List[FormattedIssue]) -> None:
        """Display issues grouped by file."""
        # Group issues by file
        issues_by_file = {}
        for issue in issues:
            file_key = str(issue.file_path)
            if file_key not in issues_by_file:
                issues_by_file[file_key] = []
            issues_by_file[file_key].append(issue)
        
        # Display each file's issues
        for file_path, file_issues in issues_by_file.items():
            self._display_file_header(file_path, len(file_issues))
            
            for issue in sorted(file_issues, key=lambda x: (x.line, x.column)):
                self._display_issue(issue)
            
            self.console.print()  # Empty line between files
    
    def _display_flat_list(self, issues: List[FormattedIssue]) -> None:
        """Display issues as a flat list."""
        for issue in issues:
            self._display_issue(issue, show_file=True)
    
    def _display_file_header(self, file_path: str, issue_count: int) -> None:
        """Display header for a file with issues."""
        self.console.print(
            f"[bold]{file_path}[/bold] "
            f"[dim]({issue_count} issue{'s' if issue_count != 1 else ''})[/dim]"
        )
        self.console.print("─" * 60)
    
    def _display_issue(self, issue: FormattedIssue, show_file: bool = False) -> None:
        """Display a single issue."""
        # Build issue header
        severity_cfg = self.SEVERITY_CONFIG.get(issue.severity, self.SEVERITY_CONFIG['info'])
        type_icon = self.TYPE_ICONS.get(issue.type, '❓')
        
        header_parts = [
            f"{severity_cfg['icon']} [{severity_cfg['color']}]{severity_cfg['label']}[/{severity_cfg['color']}]",
            f"{type_icon} {issue.type.upper()}",
            f"Line {issue.line}:{issue.column}"
        ]
        
        if show_file:
            header_parts.insert(0, f"[dim]{issue.file_path}[/dim]")
        
        self.console.print("  " + " • ".join(header_parts))
        
        # Display message
        self.console.print(f"  [bold]{issue.message}[/bold]")
        
        # Display suggestion if available
        if issue.suggestion:
            self.console.print(f"  💡 [green]{issue.suggestion}[/green]")
        
        # Display context if available
        if issue.context_lines and self.show_context:
            self._display_context(issue.context_lines, issue.line, issue.column)
        
        # Display diff if available
        if issue.diff:
            self._display_diff(issue.diff)
        
        self.console.print()  # Empty line after issue
    
    def _display_context(
        self,
        context_lines: List[Tuple[int, str]],
        target_line: int,
        target_column: int
    ) -> None:
        """Display code context around an issue."""
        self.console.print("\n  [dim]Code context:[/dim]")
        
        for line_num, line_content in context_lines:
            is_target = line_num == target_line
            
            # Format line number
            line_num_str = f"{line_num:4d}"
            
            if is_target:
                # Highlight the target line
                self.console.print(
                    f"  [red]→ {line_num_str}[/red] │ [yellow]{line_content}[/yellow]"
                )
                
                # Show column indicator
                if target_column > 0:
                    spaces = " " * (len(line_num_str) + target_column + 5)
                    self.console.print(f"  {spaces}[red]^[/red]")
            else:
                self.console.print(
                    f"    {line_num_str} │ [dim]{line_content}[/dim]"
                )
    
    def _display_diff(self, diff: str) -> None:
        """Display a diff."""
        self.console.print("\n  [dim]Suggested change:[/dim]")
        
        # Use Syntax highlighting for the diff
        syntax = Syntax(diff, "diff", theme="monokai", line_numbers=False)
        
        # Indent the diff
        indented_diff = "\n".join(f"  {line}" for line in str(syntax).split("\n"))
        self.console.print(indented_diff)
    
    def _display_suggestion(
        self,
        index: int,
        suggestion: Dict[str, Any],
        show_examples: bool
    ) -> None:
        """Display a single suggestion."""
        stype = suggestion.get('type', 'general')
        severity = suggestion.get('severity', 'info')
        message = suggestion.get('message', '')
        
        # Get severity config
        severity_cfg = self.SEVERITY_CONFIG.get(severity, self.SEVERITY_CONFIG['info'])
        
        # Display suggestion header
        self.console.print(
            f"{index}. {severity_cfg['icon']} [{severity_cfg['color']}]"
            f"{message}[/{severity_cfg['color']}]"
        )
        
        # Display details
        if 'job' in suggestion:
            self.console.print(f"   📍 Job: [bold]{suggestion['job']}[/bold]")
        
        if 'suggestion' in suggestion:
            self.console.print(f"   💡 {suggestion['suggestion']}")
        
        # Display example if available
        if show_examples and 'example' in suggestion:
            self._display_example(suggestion['example'])
        
        # Display cache config if it's a cache suggestion
        if 'cache_config' in suggestion:
            self._display_cache_config(suggestion['cache_config'])
        
        self.console.print()  # Empty line after suggestion
    
    def _display_example(self, example: str) -> None:
        """Display a code example."""
        self.console.print("\n   [dim]Example:[/dim]")
        
        # Detect language from example content
        lang = "yaml"  # Default for CI/CD files
        
        syntax = Syntax(example, lang, theme="monokai", line_numbers=False)
        
        # Indent the example
        for line in str(syntax).split("\n"):
            self.console.print(f"   {line}")
    
    def _display_cache_config(self, cache_config: Dict[str, Any]) -> None:
        """Display suggested cache configuration."""
        self.console.print("\n   [dim]Suggested cache configuration:[/dim]")
        
        # Format as YAML
        yaml_lines = []
        yaml_lines.append("- uses: actions/cache@v3")
        yaml_lines.append("  with:")
        
        if 'key' in cache_config:
            yaml_lines.append(f"    key: {cache_config['key']}")
        
        if 'restore-keys' in cache_config:
            yaml_lines.append("    restore-keys: |")
            for key in cache_config['restore-keys']:
                yaml_lines.append(f"      {key}")
        
        if 'path' in cache_config:
            if isinstance(cache_config['path'], list):
                yaml_lines.append("    path: |")
                for path in cache_config['path']:
                    yaml_lines.append(f"      {path}")
            else:
                yaml_lines.append(f"    path: {cache_config['path']}")
        
        yaml_content = "\n".join(yaml_lines)
        syntax = Syntax(yaml_content, "yaml", theme="monokai", line_numbers=False)
        
        for line in str(syntax).split("\n"):
            self.console.print(f"   {line}")
    
    def _display_summary(self, issues: List[FormattedIssue]) -> None:
        """Display a summary of all issues."""
        # Count by severity
        severity_counts = {'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        type_counts = {}
        
        for issue in issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
            type_counts[issue.type] = type_counts.get(issue.type, 0) + 1
        
        # Create summary table
        table = Table(title="Issue Summary", show_header=True, header_style="bold")
        table.add_column("Severity", style="cyan", width=10)
        table.add_column("Count", justify="right", style="white")
        table.add_column("Type Breakdown", style="dim")
        
        # Add rows for each severity
        for severity in ['high', 'medium', 'low']:
            count = severity_counts.get(severity, 0)
            if count > 0:
                cfg = self.SEVERITY_CONFIG[severity]
                
                # Get types for this severity
                types_for_severity = []
                for issue in issues:
                    if issue.severity == severity:
                        types_for_severity.append(issue.type)
                
                type_summary = ", ".join(f"{t} ({types_for_severity.count(t)})" 
                                       for t in set(types_for_severity))
                
                table.add_row(
                    f"{cfg['icon']} {cfg['label']}",
                    str(count),
                    type_summary or "-"
                )
        
        self.console.print("\n")
        self.console.print(table)
        
        # Display action items
        if severity_counts.get('high', 0) > 0:
            self.console.print(
                f"\n[red]⚠️  {severity_counts['high']} high-severity issue(s) "
                "should be addressed immediately[/red]"
            )
        
        if any(issue.suggestion for issue in issues):
            self.console.print(
                "\n💡 [green]Run with --autofix to automatically apply suggested fixes[/green]"
            ) 