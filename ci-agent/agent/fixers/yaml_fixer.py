"""
YAML Fixer Module

Handles fixing common YAML issues in CI/CD workflow files.
"""

import logging
import re
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class YAMLFixer:
    """
    Fixes common YAML issues in workflow files.
    """
    
    def __init__(self):
        """Initialize the YAML fixer."""
        logger.debug("Initialized YAML fixer")
    
    def fix_content(self, content: str, fix_type: str, **kwargs) -> str:
        """
        Apply a specific fix type to YAML content.
        
        Args:
            content: Original YAML content
            fix_type: Type of fix to apply
            **kwargs: Additional parameters for specific fixes
            
        Returns:
            Fixed content
        """
        logger.debug(f"Applying {fix_type} fix")
        
        if fix_type == "tabs_to_spaces":
            return self.fix_tabs_to_spaces(content)
        elif fix_type == "trailing_whitespace":
            return self.fix_trailing_whitespace(content)
        elif fix_type == "indentation":
            return self.fix_indentation(content, kwargs.get("indent_size", 2))
        elif fix_type == "typos":
            return self.fix_common_typos(content)
        elif fix_type == "quotes":
            return self.fix_quotes(content, kwargs.get("line"))
        else:
            logger.warning(f"Unknown fix type: {fix_type}")
            return content
    
    def fix_tabs_to_spaces(self, content: str, spaces_per_tab: int = 2) -> str:
        """
        Replace tabs with spaces.
        
        Args:
            content: YAML content with tabs
            spaces_per_tab: Number of spaces per tab (default: 2)
            
        Returns:
            Fixed content with spaces instead of tabs
        """
        logger.info("Fixing tabs to spaces")
        
        # Simple replacement
        fixed_content = content.replace('\t', ' ' * spaces_per_tab)
        
        # Log changes
        tab_count = content.count('\t')
        if tab_count > 0:
            logger.info(f"Replaced {tab_count} tab(s) with {spaces_per_tab} spaces each")
        
        return fixed_content
    
    def fix_trailing_whitespace(self, content: str) -> str:
        """
        Remove trailing whitespace from lines.
        
        Args:
            content: YAML content with trailing whitespace
            
        Returns:
            Fixed content without trailing whitespace
        """
        logger.info("Fixing trailing whitespace")
        
        lines = content.splitlines(keepends=True)
        fixed_lines = []
        changes = 0
        
        for line in lines:
            original = line
            # Remove trailing whitespace but preserve line ending
            if line.endswith('\n'):
                fixed_line = line.rstrip() + '\n'
            else:
                fixed_line = line.rstrip()
            
            if original != fixed_line:
                changes += 1
            
            fixed_lines.append(fixed_line)
        
        if changes > 0:
            logger.info(f"Removed trailing whitespace from {changes} line(s)")
        
        return ''.join(fixed_lines)
    
    def fix_indentation(self, content: str, indent_size: int = 2) -> str:
        """
        Fix inconsistent indentation in YAML.
        
        Args:
            content: YAML content with indentation issues
            indent_size: Desired indent size
            
        Returns:
            Fixed content with consistent indentation
        """
        logger.info(f"Fixing indentation (indent_size={indent_size})")
        
        lines = content.splitlines(keepends=True)
        fixed_lines = []
        
        for line in lines:
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith('#'):
                fixed_lines.append(line)
                continue
            
            # Calculate current indentation
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            
            # Ensure indentation is a multiple of indent_size
            if indent % indent_size != 0:
                # Round to nearest multiple
                new_indent = round(indent / indent_size) * indent_size
                fixed_line = ' ' * new_indent + stripped
                fixed_lines.append(fixed_line)
                logger.debug(f"Fixed indentation: {indent} -> {new_indent} spaces")
            else:
                fixed_lines.append(line)
        
        return ''.join(fixed_lines)
    
    def fix_common_typos(self, content: str) -> str:
        """
        Fix common typos in CI/CD YAML files.
        
        Args:
            content: YAML content with potential typos
            
        Returns:
            Fixed content with typos corrected
        """
        logger.info("Fixing common typos")
        
        # Common typo patterns and their fixes
        typo_patterns = [
            # GitHub Actions specific
            (r'\brun-on:', 'runs-on:'),
            (r'\bneed:', 'needs:'),
            (r'\bstep:', 'steps:'),
            (r'\bjob:', 'jobs:'),
            (r'\buse:', 'uses:'),
            (r'\bwith_:', 'with:'),
            # GitLab CI specific
            (r'\bscript_:', 'script:'),
            (r'\bstage:', 'stages:'),
            (r'\bonly_:', 'only:'),
            (r'\bexcept_:', 'except:'),
            # Common misspellings
            (r'\bdependancies\b', 'dependencies'),
            (r'\benvironment\b', 'environment'),
            (r'\bdeployement\b', 'deployment'),
        ]
        
        fixed_content = content
        total_fixes = 0
        
        for pattern, replacement in typo_patterns:
            matches = len(re.findall(pattern, fixed_content, re.IGNORECASE))
            if matches > 0:
                fixed_content = re.sub(pattern, replacement, fixed_content, flags=re.IGNORECASE)
                total_fixes += matches
                logger.debug(f"Fixed {matches} occurrence(s) of '{pattern}' -> '{replacement}'")
        
        if total_fixes > 0:
            logger.info(f"Fixed {total_fixes} typo(s)")
        
        return fixed_content
    
    def fix_quotes(self, content: str, line_number: Optional[int] = None) -> str:
        """
        Fix unmatched quotes in YAML.
        
        Args:
            content: YAML content with quote issues
            line_number: Optional specific line to fix
            
        Returns:
            Fixed content with balanced quotes
        """
        logger.info("Fixing quotes")
        
        lines = content.splitlines(keepends=True)
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Skip if we're targeting a specific line and this isn't it
            if line_number and i + 1 != line_number:
                fixed_lines.append(line)
                continue
            
            # Skip comments
            if line.strip().startswith('#'):
                fixed_lines.append(line)
                continue
            
            # Fix unmatched quotes
            fixed_line = self._fix_line_quotes(line)
            if fixed_line != line:
                logger.debug(f"Fixed quotes on line {i + 1}")
            
            fixed_lines.append(fixed_line)
        
        return ''.join(fixed_lines)
    
    def _fix_line_quotes(self, line: str) -> str:
        """
        Fix quotes in a single line.
        
        Args:
            line: Line with potential quote issues
            
        Returns:
            Fixed line
        """
        # Count quotes outside of comments
        comment_pos = line.find('#')
        if comment_pos == -1:
            working_line = line
        else:
            # Check if # is inside quotes
            before_comment = line[:comment_pos]
            if (before_comment.count('"') % 2 == 0 and 
                before_comment.count("'") % 2 == 0):
                # # is not inside quotes, it's a comment
                working_line = before_comment
            else:
                # # is inside quotes
                working_line = line
        
        # Fix unmatched double quotes
        double_count = working_line.count('"')
        if double_count % 2 != 0:
            # Find last quote and add a matching one
            last_quote = working_line.rfind('"')
            if last_quote != -1:
                # Add closing quote at end of value (before comment if any)
                if comment_pos > last_quote:
                    line = line[:comment_pos].rstrip() + '"' + line[comment_pos:]
                else:
                    line = line.rstrip() + '"'
                    if line.endswith('"\n'):
                        line = line[:-2] + '"\n'
        
        # Fix unmatched single quotes
        single_count = working_line.count("'")
        if single_count % 2 != 0:
            # Find last quote and add a matching one
            last_quote = working_line.rfind("'")
            if last_quote != -1:
                # Add closing quote at end of value (before comment if any)
                if comment_pos > last_quote:
                    line = line[:comment_pos].rstrip() + "'" + line[comment_pos:]
                else:
                    line = line.rstrip() + "'"
                    if line.endswith("'\n"):
                        line = line[:-2] + "'\n"
        
        return line
    
    def validate_fix(self, original: str, fixed: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a fix doesn't break the YAML structure.
        
        Args:
            original: Original content
            fixed: Fixed content
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        import yaml
        
        try:
            # Try to parse the fixed YAML
            yaml.safe_load(fixed)
            return True, None
        except yaml.YAMLError as e:
            logger.error(f"Fixed YAML is invalid: {e}")
            return False, str(e)
    
    def generate_fix_for_issue(self, issue: Dict[str, Any], content: str) -> Optional[Dict[str, Any]]:
        """
        Generate a fix for a specific YAML issue.
        
        Args:
            issue: Issue dictionary
            content: Current file content
            
        Returns:
            Fix dictionary or None if not fixable
        """
        if issue.get("type") != "syntax":
            return None
        
        message = issue.get("message", "").lower()
        
        # Determine fix type based on issue message
        if "tab" in message:
            return {
                "type": "tabs_to_spaces",
                "fixed_content": self.fix_tabs_to_spaces(content)
            }
        elif "trailing" in message and "whitespace" in message:
            return {
                "type": "trailing_whitespace",
                "fixed_content": self.fix_trailing_whitespace(content)
            }
        elif "quote" in message:
            return {
                "type": "quotes",
                "fixed_content": self.fix_quotes(content, issue.get("line"))
            }
        elif any(typo in message for typo in ["run-on", "need:", "typo"]):
            return {
                "type": "typos",
                "fixed_content": self.fix_common_typos(content)
            }
        elif "indent" in message:
            return {
                "type": "indentation",
                "fixed_content": self.fix_indentation(content)
            }
        
        return None 