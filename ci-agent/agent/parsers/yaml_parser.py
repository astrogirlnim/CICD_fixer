"""
YAML Parser Module

Handles parsing and validation of YAML workflow files.
Provides schema validation and error detection capabilities.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import yaml
from yaml import YAMLError
import jsonschema
from jsonschema import ValidationError
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class YAMLIssue:
    """Represents an issue found in a YAML file."""
    type: str  # 'syntax', 'schema', 'structure'
    severity: str  # 'high', 'medium', 'low'
    line: int
    column: int
    message: str
    suggestion: Optional[str] = None


@dataclass
class ParsedWorkflow:
    """Represents a parsed workflow with its structure and metadata."""
    raw_content: str
    parsed_data: Optional[Dict[str, Any]]
    issues: List[YAMLIssue]
    platform: str  # 'github_actions', 'gitlab_ci', etc.
    is_valid: bool


class YAMLParser:
    """
    Parser for CI/CD workflow YAML files.
    
    Handles syntax validation, schema validation, and common issue detection.
    """
    
    def __init__(self):
        """Initialize the YAML parser."""
        self.yaml_loader = yaml.SafeLoader
        logger.debug("Initialized YAML parser")
    
    def parse_workflow(self, content: str, file_path: Path = None) -> ParsedWorkflow:
        """
        Parse a workflow YAML file and validate its structure.
        
        Args:
            content: The YAML content to parse
            file_path: Optional path for better error messages
            
        Returns:
            ParsedWorkflow object with parsed data and any issues found
        """
        logger.debug(f"Parsing workflow{f' from {file_path}' if file_path else ''}")
        
        issues: List[YAMLIssue] = []
        parsed_data = None
        platform = self._detect_platform(content, file_path)
        
        # Step 1: Parse YAML syntax
        try:
            parsed_data = yaml.safe_load(content)
            logger.debug("YAML syntax is valid")
        except yaml.scanner.ScannerError as e:
            issues.append(self._yaml_error_to_issue(e, "Scanner error"))
        except yaml.parser.ParserError as e:
            issues.append(self._yaml_error_to_issue(e, "Parser error"))
        except YAMLError as e:
            issues.append(self._yaml_error_to_issue(e, "YAML error"))
        
        # Step 2: Validate structure if parsing succeeded
        if parsed_data is not None:
            # Check for common structural issues
            structural_issues = self._check_structure(parsed_data, platform)
            issues.extend(structural_issues)
            
            # Validate against schema if available
            schema_issues = self._validate_schema(parsed_data, platform)
            issues.extend(schema_issues)
        
        # Step 3: Check for common YAML mistakes
        syntax_issues = self._check_common_syntax_issues(content)
        issues.extend(syntax_issues)
        
        # Determine if workflow is valid
        is_valid = len([i for i in issues if i.severity == 'high']) == 0
        
        return ParsedWorkflow(
            raw_content=content,
            parsed_data=parsed_data,
            issues=issues,
            platform=platform,
            is_valid=is_valid
        )
    
    def _detect_platform(self, content: str, file_path: Optional[Path]) -> str:
        """
        Detect the CI platform based on file path and content.
        
        Args:
            content: The YAML content
            file_path: The file path
            
        Returns:
            Platform identifier
        """
        if file_path:
            path_str = str(file_path)
            if '.github/workflows' in path_str:
                return 'github_actions'
            elif file_path.name in ['.gitlab-ci.yml', '.gitlab-ci.yaml']:
                return 'gitlab_ci'
        
        # Try to detect from content
        if 'on:' in content and 'jobs:' in content:
            return 'github_actions'
        elif 'stages:' in content or 'gitlab' in content.lower():
            return 'gitlab_ci'
        
        return 'unknown'
    
    def _yaml_error_to_issue(self, error: YAMLError, error_type: str) -> YAMLIssue:
        """
        Convert a YAML error to a YAMLIssue object.
        
        Args:
            error: The YAML error
            error_type: Type of error for the message
            
        Returns:
            YAMLIssue object
        """
        # Extract line and column from error if available
        line = 1
        column = 1
        if hasattr(error, 'problem_mark'):
            line = error.problem_mark.line + 1
            column = error.problem_mark.column + 1
        
        # Create error message
        message = f"{error_type}: {str(error)}"
        if hasattr(error, 'problem'):
            message = f"{error_type}: {error.problem}"
        
        # Generate suggestion based on error type
        suggestion = None
        if "found character '\\t'" in str(error):
            suggestion = "Replace tabs with spaces (YAML doesn't allow tabs for indentation)"
        elif "mapping values are not allowed" in str(error):
            suggestion = "Check indentation and ensure proper key-value structure"
        elif "expected" in str(error) and "found" in str(error):
            suggestion = "Check for missing or extra colons, quotes, or brackets"
        
        return YAMLIssue(
            type='syntax',
            severity='high',
            line=line,
            column=column,
            message=message,
            suggestion=suggestion
        )
    
    def _check_structure(self, data: Dict[str, Any], platform: str) -> List[YAMLIssue]:
        """
        Check for structural issues in the parsed YAML.
        
        Args:
            data: Parsed YAML data
            platform: CI platform
            
        Returns:
            List of structural issues found
        """
        issues = []
        
        if platform == 'github_actions':
            # Check for required top-level keys
            if not isinstance(data, dict):
                issues.append(YAMLIssue(
                    type='structure',
                    severity='high',
                    line=1,
                    column=1,
                    message="Workflow must be a YAML mapping (key-value pairs)",
                    suggestion="Ensure the file starts with 'name:' or 'on:' at the top level"
                ))
                return issues
            
            # Check for 'on' trigger
            if 'on' not in data:
                issues.append(YAMLIssue(
                    type='structure',
                    severity='high',
                    line=1,
                    column=1,
                    message="Missing required 'on' trigger",
                    suggestion="Add an 'on:' section to define when the workflow should run"
                ))
            
            # Check for 'jobs'
            if 'jobs' not in data:
                issues.append(YAMLIssue(
                    type='structure',
                    severity='high',
                    line=1,
                    column=1,
                    message="Missing required 'jobs' section",
                    suggestion="Add a 'jobs:' section to define the workflow jobs"
                ))
            elif not isinstance(data.get('jobs'), dict):
                issues.append(YAMLIssue(
                    type='structure',
                    severity='high',
                    line=1,
                    column=1,
                    message="'jobs' must be a mapping of job names to job definitions",
                    suggestion="Define jobs as nested mappings under 'jobs:'"
                ))
            else:
                # Check individual jobs
                for job_name, job_def in data['jobs'].items():
                    if not isinstance(job_def, dict):
                        issues.append(YAMLIssue(
                            type='structure',
                            severity='high',
                            line=1,
                            column=1,
                            message=f"Job '{job_name}' must be a mapping",
                            suggestion=f"Define job '{job_name}' with 'runs-on' and 'steps'"
                        ))
                    elif 'runs-on' not in job_def:
                        issues.append(YAMLIssue(
                            type='structure',
                            severity='high',
                            line=1,
                            column=1,
                            message=f"Job '{job_name}' missing required 'runs-on'",
                            suggestion=f"Add 'runs-on: ubuntu-latest' or another runner to job '{job_name}'"
                        ))
        
        elif platform == 'gitlab_ci':
            # GitLab CI specific checks
            if not isinstance(data, dict):
                issues.append(YAMLIssue(
                    type='structure',
                    severity='high',
                    line=1,
                    column=1,
                    message="GitLab CI configuration must be a YAML mapping",
                    suggestion="Define jobs as top-level keys with their configurations"
                ))
        
        return issues
    
    def _validate_schema(self, data: Dict[str, Any], platform: str) -> List[YAMLIssue]:
        """
        Validate the YAML against platform-specific schema.
        
        Args:
            data: Parsed YAML data
            platform: CI platform
            
        Returns:
            List of schema validation issues
        """
        issues = []
        
        # For now, we'll do basic validation
        # In a full implementation, we'd load actual JSON schemas for each platform
        
        if platform == 'github_actions' and isinstance(data, dict):
            # Validate job steps
            jobs = data.get('jobs', {})
            for job_name, job_def in jobs.items():
                if isinstance(job_def, dict) and 'steps' in job_def:
                    steps = job_def['steps']
                    if not isinstance(steps, list):
                        issues.append(YAMLIssue(
                            type='schema',
                            severity='high',
                            line=1,
                            column=1,
                            message=f"Job '{job_name}' steps must be a list",
                            suggestion="Define steps as a list with '- name: ...' or '- uses: ...'"
                        ))
                    else:
                        for i, step in enumerate(steps):
                            if not isinstance(step, dict):
                                issues.append(YAMLIssue(
                                    type='schema',
                                    severity='high',
                                    line=1,
                                    column=1,
                                    message=f"Step {i+1} in job '{job_name}' must be a mapping",
                                    suggestion="Each step should have 'name', 'uses', or 'run'"
                                ))
                            elif not any(k in step for k in ['uses', 'run']):
                                issues.append(YAMLIssue(
                                    type='schema',
                                    severity='medium',
                                    line=1,
                                    column=1,
                                    message=f"Step {i+1} in job '{job_name}' has no action",
                                    suggestion="Add 'uses' for actions or 'run' for shell commands"
                                ))
        
        return issues
    
    def _check_common_syntax_issues(self, content: str) -> List[YAMLIssue]:
        """
        Check for common YAML syntax issues that might not cause parse errors.
        
        Args:
            content: Raw YAML content
            
        Returns:
            List of syntax issues found
        """
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Check for tabs
            if '\t' in line:
                issues.append(YAMLIssue(
                    type='syntax',
                    severity='high',
                    line=line_num,
                    column=line.index('\t') + 1,
                    message="Tab character found (YAML requires spaces)",
                    suggestion="Replace all tabs with spaces (usually 2 or 4 spaces)"
                ))
            
            # Check for trailing spaces
            if line.rstrip() != line:
                issues.append(YAMLIssue(
                    type='syntax',
                    severity='low',
                    line=line_num,
                    column=len(line.rstrip()) + 1,
                    message="Trailing whitespace",
                    suggestion="Remove trailing spaces from line"
                ))
            
            # Check for inconsistent quotes
            if line.count('"') % 2 != 0:
                issues.append(YAMLIssue(
                    type='syntax',
                    severity='medium',
                    line=line_num,
                    column=1,
                    message="Unmatched double quote",
                    suggestion="Check for missing closing quote"
                ))
            
            if line.count("'") % 2 != 0:
                issues.append(YAMLIssue(
                    type='syntax',
                    severity='medium',
                    line=line_num,
                    column=1,
                    message="Unmatched single quote",
                    suggestion="Check for missing closing quote"
                ))
            
            # Check for common typos in GitHub Actions
            if 'run-on:' in line:
                issues.append(YAMLIssue(
                    type='syntax',
                    severity='high',
                    line=line_num,
                    column=line.index('run-on:') + 1,
                    message="Typo: 'run-on' should be 'runs-on'",
                    suggestion="Change 'run-on:' to 'runs-on:'"
                ))
            
            if 'need:' in line and 'needs:' not in line:
                issues.append(YAMLIssue(
                    type='syntax',
                    severity='high',
                    line=line_num,
                    column=line.index('need:') + 1,
                    message="Typo: 'need' should be 'needs'",
                    suggestion="Change 'need:' to 'needs:'"
                ))
        
        return issues
    
    def fix_indentation(self, content: str) -> Tuple[str, List[str]]:
        """
        Attempt to fix indentation issues in YAML content.
        
        Args:
            content: YAML content with potential indentation issues
            
        Returns:
            Tuple of (fixed_content, list_of_changes_made)
        """
        changes = []
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Replace tabs with spaces
            if '\t' in line:
                fixed_line = line.replace('\t', '  ')
                fixed_lines.append(fixed_line)
                changes.append(f"Line {i+1}: Replaced tabs with spaces")
            else:
                fixed_lines.append(line)
        
        fixed_content = '\n'.join(fixed_lines)
        
        # Try to detect and fix inconsistent indentation
        # This is a simple implementation - a full version would be more sophisticated
        
        return fixed_content, changes 