"""
Auto-Fix Handler Module

Handles applying fixes to workflow files, including backup creation,
change tracking, and rollback capabilities.
"""

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import difflib
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Confirm

logger = logging.getLogger(__name__)


class FixResult:
    """Result of applying a fix."""
    
    def __init__(
        self,
        success: bool,
        file_path: Path,
        fix_type: str,
        message: str,
        diff: Optional[str] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.file_path = file_path
        self.fix_type = fix_type
        self.message = message
        self.diff = diff
        self.error = error
        self.timestamp = datetime.now()


class AutofixHandler:
    """
    Handles applying fixes to CI/CD workflow files.
    """
    
    def __init__(
        self,
        console: Optional[Console] = None,
        create_backups: bool = True,
        backup_suffix: str = ".bak",
        dry_run: bool = False,
        interactive: bool = True
    ):
        """
        Initialize the autofix handler.
        
        Args:
            console: Rich console for output
            create_backups: Whether to create backup files
            backup_suffix: Suffix for backup files
            dry_run: If True, show changes without applying them
            interactive: If True, ask for confirmation before each fix
        """
        self.console = console or Console()
        self.create_backups = create_backups
        self.backup_suffix = backup_suffix
        self.dry_run = dry_run
        self.interactive = interactive
        self.applied_fixes: List[FixResult] = []
        self.backup_files: Dict[Path, Path] = {}  # original -> backup
        
        logger.debug(f"Initialized autofix handler (dry_run={dry_run})")
    
    def apply_fixes(
        self,
        fixes: List[Dict[str, Any]],
        workflow_files: Dict[str, str]
    ) -> Tuple[int, int]:
        """
        Apply a list of fixes to workflow files.
        
        Args:
            fixes: List of fixes to apply
            workflow_files: Current content of workflow files
            
        Returns:
            Tuple of (successful_fixes, failed_fixes)
        """
        if not fixes:
            logger.info("No fixes to apply")
            return 0, 0
        
        # Show header
        self._display_header(len(fixes))
        
        successful = 0
        failed = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("Applying fixes...", total=len(fixes))
            
            for i, fix in enumerate(fixes):
                # Apply single fix
                result = self._apply_single_fix(fix, workflow_files)
                
                if result.success:
                    successful += 1
                    if result.diff:
                        # Update workflow_files with new content
                        workflow_files[str(result.file_path)] = self._apply_diff_to_content(
                            workflow_files.get(str(result.file_path), ""),
                            result.diff
                        )
                else:
                    failed += 1
                
                self.applied_fixes.append(result)
                progress.update(task, advance=1)
        
        # Show summary
        self._display_summary(successful, failed)
        
        return successful, failed
    
    def _apply_single_fix(
        self,
        fix: Dict[str, Any],
        workflow_files: Dict[str, str]
    ) -> FixResult:
        """
        Apply a single fix.
        
        Args:
            fix: Fix to apply
            workflow_files: Current workflow file contents
            
        Returns:
            FixResult object
        """
        file_path = Path(fix.get('file', ''))
        fix_type = fix.get('type', 'unknown')
        
        # Get current content
        current_content = workflow_files.get(str(file_path), '')
        if not current_content and file_path.exists():
            current_content = file_path.read_text()
        
        if not current_content:
            return FixResult(
                success=False,
                file_path=file_path,
                fix_type=fix_type,
                message="File not found or empty",
                error="Cannot apply fix to non-existent file"
            )
        
        # Generate fixed content based on fix type
        try:
            fixed_content = self._generate_fixed_content(fix, current_content)
            
            if fixed_content == current_content:
                return FixResult(
                    success=True,
                    file_path=file_path,
                    fix_type=fix_type,
                    message="No changes needed"
                )
            
            # Generate diff
            diff = self._generate_diff(current_content, fixed_content, str(file_path))
            
            # Show fix details and get confirmation if interactive
            if self.interactive and not self.dry_run:
                if not self._confirm_fix(fix, diff):
                    return FixResult(
                        success=False,
                        file_path=file_path,
                        fix_type=fix_type,
                        message="Fix skipped by user"
                    )
            
            # Apply the fix (unless dry run)
            if not self.dry_run:
                # Create backup if needed
                if self.create_backups:
                    backup_path = self._create_backup(file_path)
                    self.backup_files[file_path] = backup_path
                
                # Write fixed content
                file_path.write_text(fixed_content)
                logger.info(f"✅ Applied fix to {file_path}")
            
            return FixResult(
                success=True,
                file_path=file_path,
                fix_type=fix_type,
                message=f"Fixed {fix_type} issue{'s' if fix_type.endswith('s') else ''}",
                diff=diff
            )
            
        except Exception as e:
            logger.error(f"Error applying fix to {file_path}: {e}")
            return FixResult(
                success=False,
                file_path=file_path,
                fix_type=fix_type,
                message=f"Failed to apply {fix_type} fix",
                error=str(e)
            )
    
    def _generate_fixed_content(self, fix: Dict[str, Any], content: str) -> str:
        """
        Generate fixed content based on the fix type.
        
        Args:
            fix: Fix specification
            content: Current file content
            
        Returns:
            Fixed content
        """
        fix_type = fix.get('type', '')
        
        # If fix includes direct replacement content
        if 'fixed_content' in fix:
            return fix['fixed_content']
        
        # If fix includes line-based changes
        if 'line_changes' in fix:
            return self._apply_line_changes(content, fix['line_changes'])
        
        # If fix includes a callable fixer function
        if 'fixer_function' in fix and callable(fix['fixer_function']):
            return fix['fixer_function'](content)
        
        # Handle specific fix types
        if fix_type == 'indentation':
            return self._fix_indentation(content)
        elif fix_type == 'trailing_whitespace':
            return self._fix_trailing_whitespace(content)
        elif fix_type == 'tabs_to_spaces':
            return self._fix_tabs_to_spaces(content)
        elif fix_type == 'add_cache' and 'cache_config' in fix:
            return self._add_cache_config(content, fix['cache_config'], fix.get('job'))
        
        # Default: return unchanged
        logger.warning(f"Unknown fix type: {fix_type}")
        return content
    
    def _apply_line_changes(self, content: str, line_changes: List[Dict[str, Any]]) -> str:
        """
        Apply line-based changes to content.
        
        Args:
            content: Original content
            line_changes: List of line changes
            
        Returns:
            Modified content
        """
        lines = content.splitlines(keepends=True)
        
        # Sort changes by line number in reverse order to avoid offset issues
        sorted_changes = sorted(line_changes, key=lambda x: x['line'], reverse=True)
        
        for change in sorted_changes:
            line_num = change['line'] - 1  # Convert to 0-indexed
            
            if 0 <= line_num < len(lines):
                if change.get('action') == 'replace':
                    lines[line_num] = change['new_content'] + '\n'
                elif change.get('action') == 'delete':
                    del lines[line_num]
                elif change.get('action') == 'insert':
                    lines.insert(line_num, change['new_content'] + '\n')
        
        return ''.join(lines)
    
    def _fix_indentation(self, content: str) -> str:
        """Fix indentation issues in YAML content."""
        lines = content.splitlines(keepends=True)
        fixed_lines = []
        
        for line in lines:
            # Replace tabs with spaces
            fixed_line = line.replace('\t', '  ')
            fixed_lines.append(fixed_line)
        
        return ''.join(fixed_lines)
    
    def _fix_trailing_whitespace(self, content: str) -> str:
        """Remove trailing whitespace from lines."""
        lines = content.splitlines(keepends=True)
        fixed_lines = []
        
        for line in lines:
            # Remove trailing whitespace but preserve line ending
            if line.endswith('\n'):
                fixed_line = line.rstrip() + '\n'
            else:
                fixed_line = line.rstrip()
            fixed_lines.append(fixed_line)
        
        return ''.join(fixed_lines)
    
    def _fix_tabs_to_spaces(self, content: str) -> str:
        """Convert tabs to spaces."""
        return content.replace('\t', '  ')
    
    def _add_cache_config(
        self,
        content: str,
        cache_config: Dict[str, Any],
        job_name: Optional[str] = None
    ) -> str:
        """
        Add cache configuration to a workflow.
        
        Args:
            content: Current workflow content
            cache_config: Cache configuration to add
            job_name: Job to add cache to
            
        Returns:
            Modified content
        """
        # This is a simplified implementation
        # In a real implementation, we'd parse the YAML and insert properly
        
        lines = content.splitlines(keepends=True)
        
        # Find the job and its steps
        in_target_job = False
        in_steps = False
        insert_index = -1
        
        for i, line in enumerate(lines):
            if job_name and f"{job_name}:" in line and not line.strip().startswith('#'):
                in_target_job = True
            elif in_target_job and "steps:" in line:
                in_steps = True
            elif in_steps and line.strip() and not line.startswith(' '):
                # End of steps section
                insert_index = i
                break
            elif in_steps and "- uses:" in line or "- run:" in line:
                # Found first step, insert before it
                insert_index = i
                break
        
        if insert_index > 0:
            # Generate cache step YAML
            cache_yaml = self._generate_cache_yaml(cache_config)
            
            # Insert cache step
            for cache_line in reversed(cache_yaml.splitlines()):
                lines.insert(insert_index, cache_line + '\n')
        
        return ''.join(lines)
    
    def _generate_cache_yaml(self, cache_config: Dict[str, Any]) -> str:
        """Generate YAML for cache configuration."""
        yaml_lines = []
        
        # Determine indentation (assuming 2 spaces for steps)
        indent = "    "
        
        yaml_lines.append(f"{indent}- name: Cache dependencies")
        yaml_lines.append(f"{indent}  uses: actions/cache@v3")
        yaml_lines.append(f"{indent}  with:")
        
        if 'key' in cache_config:
            yaml_lines.append(f"{indent}    key: {cache_config['key']}")
        
        if 'restore-keys' in cache_config:
            yaml_lines.append(f"{indent}    restore-keys: |")
            for key in cache_config['restore-keys']:
                yaml_lines.append(f"{indent}      {key}")
        
        if 'path' in cache_config:
            if isinstance(cache_config['path'], list):
                yaml_lines.append(f"{indent}    path: |")
                for path in cache_config['path']:
                    yaml_lines.append(f"{indent}      {path}")
            else:
                yaml_lines.append(f"{indent}    path: {cache_config['path']}")
        
        return '\n'.join(yaml_lines)
    
    def _generate_diff(self, original: str, modified: str, file_path: str) -> str:
        """Generate a unified diff."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=''
        )
        
        return '\n'.join(diff)
    
    def _apply_diff_to_content(self, content: str, diff: str) -> str:
        """
        Apply a diff to content (simplified implementation).
        
        In a real implementation, this would properly parse and apply the diff.
        For now, we'll just return the content as-is since the actual changes
        are already applied.
        """
        return content
    
    def _create_backup(self, file_path: Path) -> Path:
        """
        Create a backup of a file.
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file
        """
        backup_path = file_path.with_suffix(file_path.suffix + self.backup_suffix)
        
        # If backup already exists, add timestamp
        if backup_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = file_path.with_suffix(f"{file_path.suffix}.{timestamp}{self.backup_suffix}")
        
        shutil.copy2(file_path, backup_path)
        logger.debug(f"Created backup: {backup_path}")
        
        return backup_path
    
    def _confirm_fix(self, fix: Dict[str, Any], diff: str) -> bool:
        """
        Ask user for confirmation to apply a fix.
        
        Args:
            fix: Fix details
            diff: Diff to be applied
            
        Returns:
            True if user confirms, False otherwise
        """
        self.console.print(f"\n[bold]Fix: {fix.get('message', 'Apply changes')}[/bold]")
        self.console.print(f"File: {fix.get('file', 'unknown')}")
        self.console.print(f"Type: {fix.get('type', 'unknown')}")
        
        if diff:
            self.console.print("\n[dim]Changes to be applied:[/dim]")
            from rich.syntax import Syntax
            syntax = Syntax(diff, "diff", theme="monokai", line_numbers=False)
            self.console.print(syntax)
        
        return Confirm.ask("\nApply this fix?", default=True)
    
    def _display_header(self, fix_count: int) -> None:
        """Display header for fix application."""
        mode = "Dry run" if self.dry_run else "Applying"
        self.console.print(
            f"\n[bold cyan]🔧 {mode} {fix_count} fix{'es' if fix_count != 1 else ''}[/bold cyan]\n"
        )
    
    def _display_summary(self, successful: int, failed: int) -> None:
        """Display summary of applied fixes."""
        self.console.print("\n" + "─" * 60 + "\n")
        
        if self.dry_run:
            self.console.print("[bold]Dry Run Summary:[/bold]")
            self.console.print(f"  Would apply {successful} fix{'es' if successful != 1 else ''}")
            if failed > 0:
                self.console.print(f"  [red]{failed} fix{'es' if failed != 1 else ''} would fail[/red]")
        else:
            self.console.print("[bold]Fix Summary:[/bold]")
            if successful > 0:
                self.console.print(f"  [green]✅ Applied {successful} fix{'es' if successful != 1 else ''}[/green]")
            if failed > 0:
                self.console.print(f"  [red]❌ Failed to apply {failed} fix{'es' if failed != 1 else ''}[/red]")
            
            if self.create_backups and self.backup_files:
                self.console.print(f"\n  💾 Created {len(self.backup_files)} backup file(s)")
        
        # Show details of failed fixes
        if failed > 0:
            self.console.print("\n[red]Failed fixes:[/red]")
            for result in self.applied_fixes:
                if not result.success and result.error:
                    self.console.print(f"  - {result.file_path}: {result.error}")
    
    def rollback(self) -> int:
        """
        Rollback all applied fixes by restoring backups.
        
        Returns:
            Number of files rolled back
        """
        if not self.backup_files:
            logger.info("No backups to rollback")
            return 0
        
        rolled_back = 0
        
        for original_path, backup_path in self.backup_files.items():
            try:
                shutil.copy2(backup_path, original_path)
                backup_path.unlink()  # Remove backup
                rolled_back += 1
                logger.info(f"Rolled back {original_path}")
            except Exception as e:
                logger.error(f"Failed to rollback {original_path}: {e}")
        
        self.backup_files.clear()
        return rolled_back
    
    def get_applied_fixes_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all applied fixes.
        
        Returns:
            Dictionary with fix statistics and details
        """
        summary = {
            'total': len(self.applied_fixes),
            'successful': sum(1 for f in self.applied_fixes if f.success),
            'failed': sum(1 for f in self.applied_fixes if not f.success),
            'by_type': {},
            'by_file': {},
            'fixes': []
        }
        
        for fix in self.applied_fixes:
            # Count by type
            fix_type = fix.fix_type
            if fix_type not in summary['by_type']:
                summary['by_type'][fix_type] = {'successful': 0, 'failed': 0}
            
            if fix.success:
                summary['by_type'][fix_type]['successful'] += 1
            else:
                summary['by_type'][fix_type]['failed'] += 1
            
            # Count by file
            file_str = str(fix.file_path)
            if file_str not in summary['by_file']:
                summary['by_file'][file_str] = []
            
            summary['by_file'][file_str].append({
                'type': fix.fix_type,
                'success': fix.success,
                'message': fix.message,
                'timestamp': fix.timestamp.isoformat()
            })
            
            # Add to detailed list
            summary['fixes'].append({
                'file': file_str,
                'type': fix.fix_type,
                'success': fix.success,
                'message': fix.message,
                'error': fix.error,
                'timestamp': fix.timestamp.isoformat()
            })
        
        return summary 