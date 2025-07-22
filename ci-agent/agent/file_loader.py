"""
File Loader Module

Recursively discovers and loads CI/CD workflow files from configured paths.
Handles file filtering, size limits, and basic validation.
"""

import logging
import fnmatch
from pathlib import Path
from typing import List, Set, Optional, Tuple
import os

logger = logging.getLogger(__name__)


class WorkflowFile:
    """Represents a discovered workflow file."""
    
    def __init__(self, path: Path, relative_path: Path, size_kb: float):
        """
        Initialize a workflow file.
        
        Args:
            path: Absolute path to the file
            relative_path: Path relative to the project root
            size_kb: File size in kilobytes
        """
        self.path = path
        self.relative_path = relative_path
        self.size_kb = size_kb
        self.content: Optional[str] = None
        self.error: Optional[str] = None
    
    def __repr__(self):
        return f"WorkflowFile({self.relative_path}, {self.size_kb:.1f}KB)"
    
    def load_content(self) -> bool:
        """
        Load the file content.
        
        Returns:
            True if content was loaded successfully, False otherwise
        """
        try:
            logger.debug(f"Loading content from {self.path}")
            self.content = self.path.read_text(encoding='utf-8')
            return True
        except Exception as e:
            self.error = str(e)
            logger.error(f"Failed to read {self.path}: {e}")
            return False


def find_workflow_files(
    root_path: Path,
    workflow_paths: List[str],
    exclude_patterns: List[str] = None,
    max_file_size_kb: int = 500,
    specific_file: Optional[Path] = None
) -> List[WorkflowFile]:
    """
    Find all workflow files in the specified paths.
    
    Args:
        root_path: Root directory to search from
        workflow_paths: List of paths to search for workflows
        exclude_patterns: List of glob patterns to exclude
        max_file_size_kb: Maximum file size in KB
        specific_file: If provided, only analyze this specific file
        
    Returns:
        List of discovered workflow files
    """
    logger.info(f"🔍 Searching for workflow files in {root_path}")
    
    workflow_files: List[WorkflowFile] = []
    exclude_patterns = exclude_patterns or []
    
    # If specific file is provided, only process that
    if specific_file:
        logger.info(f"📄 Processing specific file: {specific_file}")
        if specific_file.exists():
            size_kb = specific_file.stat().st_size / 1024
            if size_kb <= max_file_size_kb:
                wf = WorkflowFile(
                    path=specific_file.resolve(),
                    relative_path=specific_file,
                    size_kb=size_kb
                )
                workflow_files.append(wf)
                logger.info(f"✅ Found workflow file: {wf.relative_path} ({wf.size_kb:.1f}KB)")
            else:
                logger.warning(f"⚠️  File too large: {specific_file} ({size_kb:.1f}KB > {max_file_size_kb}KB)")
        else:
            logger.error(f"❌ File not found: {specific_file}")
        return workflow_files
    
    # Process each workflow path
    for workflow_path in workflow_paths:
        logger.debug(f"Checking workflow path: {workflow_path}")
        
        # Handle absolute and relative paths
        if os.path.isabs(workflow_path):
            search_path = Path(workflow_path)
        else:
            search_path = root_path / workflow_path
        
        # Find files based on path type
        if search_path.is_file():
            # Single file specified
            files_to_check = [search_path]
        elif search_path.is_dir():
            # Directory - find all YAML files
            files_to_check = list(search_path.glob("**/*.yml")) + list(search_path.glob("**/*.yaml"))
        else:
            # Path doesn't exist - check if it's a glob pattern
            if "*" in workflow_path or "?" in workflow_path:
                files_to_check = list(root_path.glob(workflow_path))
            else:
                logger.debug(f"Path does not exist: {search_path}")
                continue
        
        # Process found files
        for file_path in files_to_check:
            # Skip if file matches exclude pattern
            if should_exclude(file_path, exclude_patterns, root_path):
                logger.debug(f"Excluding file: {file_path}")
                continue
            
            # Check file size
            try:
                size_kb = file_path.stat().st_size / 1024
                if size_kb > max_file_size_kb:
                    logger.warning(f"⚠️  Skipping large file: {file_path} ({size_kb:.1f}KB > {max_file_size_kb}KB)")
                    continue
                
                # Create workflow file object
                relative_path = file_path.relative_to(root_path)
                wf = WorkflowFile(
                    path=file_path.resolve(),
                    relative_path=relative_path,
                    size_kb=size_kb
                )
                workflow_files.append(wf)
                logger.info(f"✅ Found workflow file: {relative_path} ({size_kb:.1f}KB)")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
    
    # Log summary
    total_size_kb = sum(wf.size_kb for wf in workflow_files)
    logger.info(f"📊 Found {len(workflow_files)} workflow files (total: {total_size_kb:.1f}KB)")
    
    return workflow_files


def should_exclude(file_path: Path, exclude_patterns: List[str], root_path: Path) -> bool:
    """
    Check if a file should be excluded based on patterns.
    
    Args:
        file_path: Path to check
        exclude_patterns: List of glob patterns
        root_path: Root path for relative pattern matching
        
    Returns:
        True if file should be excluded
    """
    # Get relative path for pattern matching
    try:
        relative_path = file_path.relative_to(root_path)
    except ValueError:
        # File is outside root path, use absolute path
        relative_path = file_path
    
    str_path = str(relative_path)
    
    for pattern in exclude_patterns:
        # Check both the relative path and just the filename
        if fnmatch.fnmatch(str_path, pattern) or fnmatch.fnmatch(file_path.name, pattern):
            return True
    
    return False


def load_all_files(workflow_files: List[WorkflowFile]) -> Tuple[int, int]:
    """
    Load content for all workflow files.
    
    Args:
        workflow_files: List of workflow files to load
        
    Returns:
        Tuple of (successful_loads, failed_loads)
    """
    logger.debug(f"Loading content for {len(workflow_files)} files")
    
    successful = 0
    failed = 0
    
    for wf in workflow_files:
        if wf.load_content():
            successful += 1
        else:
            failed += 1
    
    if failed > 0:
        logger.warning(f"⚠️  Failed to load {failed} files")
    
    return successful, failed


def filter_by_platform(
    workflow_files: List[WorkflowFile],
    platforms: dict
) -> List[WorkflowFile]:
    """
    Filter workflow files by enabled platforms.
    
    Args:
        workflow_files: List of workflow files
        platforms: Dictionary of platform names to enabled status
        
    Returns:
        Filtered list of workflow files
    """
    filtered_files = []
    
    for wf in workflow_files:
        # Determine platform based on file path and content
        if platforms.get("github_actions", True):
            # Check if it's in a GitHub Actions path
            if ".github/workflows" in str(wf.path) or ".github\\workflows" in str(wf.path):
                filtered_files.append(wf)
                continue
            
            # Also check file content if it's loaded
            if wf.content:
                # Basic check for GitHub Actions structure
                if "on:" in wf.content and "jobs:" in wf.content:
                    filtered_files.append(wf)
                    continue
            elif wf.path.suffix in ['.yml', '.yaml']:
                # If content not loaded yet, include YAML files when specific file is provided
                # The YAML parser will determine the actual platform later
                filtered_files.append(wf)
                continue
        
        if platforms.get("gitlab_ci", False):
            # Check standard GitLab CI file names
            if wf.path.name in [".gitlab-ci.yml", ".gitlab-ci.yaml"]:
                filtered_files.append(wf)
                continue
            
            # Check content for GitLab CI structure
            if wf.content and ("stages:" in wf.content or "image:" in wf.content):
                # Don't add if already added as GitHub Actions
                if wf not in filtered_files:
                    filtered_files.append(wf)
        
        # Add more platform checks here as needed
    
    logger.debug(f"Filtered to {len(filtered_files)} files based on enabled platforms")
    return filtered_files 