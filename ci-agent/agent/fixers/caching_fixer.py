"""
Caching Fixer Module

Handles adding and optimizing cache configurations in CI/CD workflows.
"""

import logging
import re
import yaml
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class CachingFixer:
    """
    Fixes caching issues and adds cache optimizations to workflows.
    """
    
    def __init__(self):
        """Initialize the caching fixer."""
        logger.debug("Initialized caching fixer")
    
    def add_cache_to_workflow(
        self,
        content: str,
        job_name: str,
        cache_config: Dict[str, Any],
        platform: str = "github_actions"
    ) -> str:
        """
        Add cache configuration to a workflow job.
        
        Args:
            content: Current workflow content
            job_name: Name of the job to add cache to
            cache_config: Cache configuration to add
            platform: CI platform
            
        Returns:
            Updated workflow content
        """
        logger.info(f"Adding cache to job '{job_name}'")
        
        if platform == "github_actions":
            return self._add_github_cache(content, job_name, cache_config)
        elif platform == "gitlab_ci":
            return self._add_gitlab_cache(content, job_name, cache_config)
        else:
            logger.warning(f"Unsupported platform: {platform}")
            return content
    
    def _add_github_cache(
        self,
        content: str,
        job_name: str,
        cache_config: Dict[str, Any]
    ) -> str:
        """
        Add cache to a GitHub Actions workflow.
        
        Args:
            content: Current workflow content
            job_name: Name of the job
            cache_config: Cache configuration
            
        Returns:
            Updated content
        """
        try:
            # Parse YAML
            workflow = yaml.safe_load(content)
            
            if not workflow or 'jobs' not in workflow:
                logger.error("Invalid workflow structure")
                return content
            
            if job_name not in workflow['jobs']:
                logger.error(f"Job '{job_name}' not found")
                return content
            
            job = workflow['jobs'][job_name]
            
            # Ensure steps exist
            if 'steps' not in job:
                job['steps'] = []
            
            # Find the best position to insert cache
            insert_pos = self._find_cache_insert_position(job['steps'])
            
            # Create cache step
            cache_step = self._create_github_cache_step(cache_config)
            
            # Insert cache step
            job['steps'].insert(insert_pos, cache_step)
            
            # Convert back to YAML with proper formatting
            fixed_content = self._workflow_to_yaml(workflow)
            
            logger.info(f"Successfully added cache to job '{job_name}' at position {insert_pos}")
            return fixed_content
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML: {e}")
            return self._add_cache_manually(content, job_name, cache_config)
    
    def _find_cache_insert_position(self, steps: List[Dict[str, Any]]) -> int:
        """
        Find the best position to insert a cache step.
        
        Args:
            steps: List of job steps
            
        Returns:
            Index where cache should be inserted
        """
        # Look for checkout step
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                uses = step.get('uses', '')
                if 'actions/checkout' in uses:
                    # Insert after checkout
                    return i + 1
        
        # Look for setup steps
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                uses = step.get('uses', '')
                if 'setup-' in uses:
                    # Insert after setup
                    return i + 1
        
        # Default: insert at the beginning
        return 0
    
    def _create_github_cache_step(self, cache_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a GitHub Actions cache step.
        
        Args:
            cache_config: Cache configuration
            
        Returns:
            Cache step dictionary
        """
        step = {
            'name': 'Cache dependencies',
            'uses': 'actions/cache@v3',
            'with': {}
        }
        
        # Add cache key
        if 'key' in cache_config:
            step['with']['key'] = cache_config['key']
        
        # Add restore keys
        if 'restore-keys' in cache_config:
            restore_keys = cache_config['restore-keys']
            if isinstance(restore_keys, list) and len(restore_keys) == 1:
                step['with']['restore-keys'] = restore_keys[0]
            elif isinstance(restore_keys, list) and len(restore_keys) > 1:
                # Use literal style for multiple restore keys
                step['with']['restore-keys'] = '|\n' + '\n'.join(f"  {key}" for key in restore_keys)
        
        # Add paths
        if 'path' in cache_config:
            paths = cache_config['path']
            if isinstance(paths, list) and len(paths) == 1:
                step['with']['path'] = paths[0]
            elif isinstance(paths, list) and len(paths) > 1:
                # Use literal style for multiple paths
                step['with']['path'] = '|\n' + '\n'.join(f"  {path}" for path in paths)
            else:
                step['with']['path'] = paths
        
        return step
    
    def _add_cache_manually(
        self,
        content: str,
        job_name: str,
        cache_config: Dict[str, Any]
    ) -> str:
        """
        Add cache manually by string manipulation (fallback method).
        
        Args:
            content: Current workflow content
            job_name: Name of the job
            cache_config: Cache configuration
            
        Returns:
            Updated content
        """
        logger.debug("Using manual cache insertion method")
        
        lines = content.splitlines(keepends=True)
        
        # Find the job
        job_pattern = rf'^(\s*){job_name}:\s*$'
        job_line = -1
        job_indent = ""
        
        for i, line in enumerate(lines):
            match = re.match(job_pattern, line)
            if match:
                job_line = i
                job_indent = match.group(1)
                break
        
        if job_line == -1:
            logger.error(f"Could not find job '{job_name}'")
            return content
        
        # Find steps section
        steps_line = -1
        steps_indent = ""
        
        for i in range(job_line + 1, len(lines)):
            match = re.match(rf'^({job_indent}\s+)steps:\s*$', lines[i])
            if match:
                steps_line = i
                steps_indent = match.group(1)
                break
        
        if steps_line == -1:
            logger.error(f"Could not find steps in job '{job_name}'")
            return content
        
        # Find first step or end of steps
        insert_line = steps_line + 1
        step_indent = steps_indent + "  "
        
        # Look for checkout step
        for i in range(steps_line + 1, len(lines)):
            if re.match(rf'^{step_indent}- ', lines[i]):
                # Check if it's checkout
                if i + 1 < len(lines) and 'actions/checkout' in lines[i + 1]:
                    # Find end of this step
                    for j in range(i + 2, len(lines)):
                        if re.match(rf'^{step_indent}- ', lines[j]) or not lines[j].strip():
                            insert_line = j
                            break
                    break
        
        # Generate cache step YAML
        cache_yaml = self._generate_cache_yaml(cache_config, step_indent)
        
        # Insert cache step
        lines.insert(insert_line, cache_yaml)
        
        return ''.join(lines)
    
    def _generate_cache_yaml(self, cache_config: Dict[str, Any], indent: str) -> str:
        """
        Generate YAML for a cache step.
        
        Args:
            cache_config: Cache configuration
            indent: Indentation string
            
        Returns:
            YAML string for cache step
        """
        yaml_lines = []
        
        yaml_lines.append(f"{indent}- name: Cache dependencies")
        yaml_lines.append(f"{indent}  uses: actions/cache@v3")
        yaml_lines.append(f"{indent}  with:")
        
        # Add key
        if 'key' in cache_config:
            yaml_lines.append(f"{indent}    key: {cache_config['key']}")
        
        # Add restore-keys
        if 'restore-keys' in cache_config:
            restore_keys = cache_config['restore-keys']
            if isinstance(restore_keys, list):
                if len(restore_keys) == 1:
                    yaml_lines.append(f"{indent}    restore-keys: {restore_keys[0]}")
                else:
                    yaml_lines.append(f"{indent}    restore-keys: |")
                    for key in restore_keys:
                        yaml_lines.append(f"{indent}      {key}")
        
        # Add paths
        if 'path' in cache_config:
            paths = cache_config['path']
            if isinstance(paths, list):
                if len(paths) == 1:
                    yaml_lines.append(f"{indent}    path: {paths[0]}")
                else:
                    yaml_lines.append(f"{indent}    path: |")
                    for path in paths:
                        yaml_lines.append(f"{indent}      {path}")
            else:
                yaml_lines.append(f"{indent}    path: {paths}")
        
        return '\n'.join(yaml_lines) + '\n'
    
    def _add_gitlab_cache(
        self,
        content: str,
        job_name: str,
        cache_config: Dict[str, Any]
    ) -> str:
        """
        Add cache to a GitLab CI workflow.
        
        Args:
            content: Current workflow content
            job_name: Name of the job
            cache_config: Cache configuration
            
        Returns:
            Updated content
        """
        try:
            # Parse YAML
            workflow = yaml.safe_load(content)
            
            if job_name not in workflow:
                logger.error(f"Job '{job_name}' not found")
                return content
            
            job = workflow[job_name]
            if not isinstance(job, dict):
                logger.error(f"Job '{job_name}' is not a dictionary")
                return content
            
            # Create GitLab cache configuration
            gitlab_cache = {
                'paths': cache_config.get('path', []),
            }
            
            # Convert GitHub-style key to GitLab format
            if 'key' in cache_config:
                key = cache_config['key']
                # Extract file reference if present
                if 'hashFiles' in key:
                    # Extract filename from hashFiles
                    match = re.search(r"hashFiles\('([^']+)'\)", key)
                    if match:
                        gitlab_cache['key'] = {
                            'files': [match.group(1)]
                        }
                else:
                    gitlab_cache['key'] = key
            
            # Add or update cache
            job['cache'] = gitlab_cache
            
            # Convert back to YAML
            fixed_content = self._workflow_to_yaml(workflow)
            
            logger.info(f"Successfully added cache to GitLab CI job '{job_name}'")
            return fixed_content
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML: {e}")
            return content
    
    def optimize_cache_key(self, cache_key: str, platform: str = "github_actions") -> str:
        """
        Optimize a cache key for better hit rates.
        
        Args:
            cache_key: Current cache key
            platform: CI platform
            
        Returns:
            Optimized cache key
        """
        logger.debug(f"Optimizing cache key: {cache_key}")
        
        # Add OS if missing
        if platform == "github_actions":
            if '${{ runner.os }}' not in cache_key and 'runner.os' not in cache_key:
                cache_key = '${{ runner.os }}-' + cache_key
                logger.debug("Added OS to cache key")
        
        # Ensure file hash is included for common lockfiles
        lockfiles = [
            'package-lock.json',
            'yarn.lock',
            'Gemfile.lock',
            'requirements.txt',
            'poetry.lock',
            'Pipfile.lock',
            'composer.lock',
            'Cargo.lock'
        ]
        
        has_hash = 'hashFiles' in cache_key
        if not has_hash:
            for lockfile in lockfiles:
                if lockfile in cache_key:
                    # Replace static lockfile reference with hash
                    cache_key = re.sub(
                        rf'{lockfile}',
                        f"${{{{ hashFiles('**/{lockfile}') }}}}",
                        cache_key
                    )
                    logger.debug(f"Added hashFiles for {lockfile}")
                    break
        
        return cache_key
    
    def _workflow_to_yaml(self, workflow: Dict[str, Any]) -> str:
        """
        Convert workflow dictionary back to YAML with proper formatting.
        
        Args:
            workflow: Workflow dictionary
            
        Returns:
            YAML string
        """
        # Custom YAML dumper for better formatting
        class FlowStyleDumper(yaml.SafeDumper):
            def write_line_break(self, data=None):
                super().write_line_break(data)
                if len(self.indents) == 1:
                    super().write_line_break()
        
        # Convert to YAML
        yaml_str = yaml.dump(
            workflow,
            Dumper=FlowStyleDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120
        )
        
        # Post-process for better formatting
        lines = yaml_str.splitlines()
        formatted_lines = []
        
        for line in lines:
            # Fix multiline strings
            if line.strip().startswith('restore-keys: |'):
                formatted_lines.append(line)
            elif line.strip().startswith('path: |'):
                formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def generate_cache_suggestions(
        self,
        workflow_data: Dict[str, Any],
        platform: str
    ) -> List[Dict[str, Any]]:
        """
        Generate cache optimization suggestions for a workflow.
        
        Args:
            workflow_data: Parsed workflow data
            platform: CI platform
            
        Returns:
            List of cache suggestions
        """
        suggestions = []
        
        # Platform-specific analysis
        if platform == "github_actions":
            jobs = workflow_data.get('jobs', {})
            for job_name, job_data in jobs.items():
                if isinstance(job_data, dict):
                    steps = job_data.get('steps', [])
                    
                    # Check for package managers without caching
                    package_managers = self._detect_package_managers(steps)
                    has_cache = self._has_cache_step(steps)
                    
                    if package_managers and not has_cache:
                        for pm in package_managers:
                            suggestions.append({
                                'job': job_name,
                                'package_manager': pm,
                                'suggestion': f"Add caching for {pm} dependencies",
                                'cache_config': self._get_package_manager_cache_config(pm)
                            })
        
        return suggestions
    
    def _detect_package_managers(self, steps: List[Dict[str, Any]]) -> List[str]:
        """
        Detect package managers used in job steps.
        
        Args:
            steps: List of job steps
            
        Returns:
            List of detected package managers
        """
        package_managers = []
        
        pm_patterns = {
            'npm': ['npm install', 'npm ci'],
            'yarn': ['yarn install', 'yarn'],
            'pip': ['pip install', 'python -m pip install'],
            'bundler': ['bundle install'],
            'composer': ['composer install'],
            'cargo': ['cargo build', 'cargo test']
        }
        
        for step in steps:
            if isinstance(step, dict):
                run_cmd = step.get('run', '')
                for pm, patterns in pm_patterns.items():
                    if any(pattern in run_cmd for pattern in patterns):
                        if pm not in package_managers:
                            package_managers.append(pm)
        
        return package_managers
    
    def _has_cache_step(self, steps: List[Dict[str, Any]]) -> bool:
        """
        Check if steps include a cache action.
        
        Args:
            steps: List of job steps
            
        Returns:
            True if cache step exists
        """
        for step in steps:
            if isinstance(step, dict):
                uses = step.get('uses', '')
                if 'cache' in uses.lower():
                    return True
        return False
    
    def _get_package_manager_cache_config(self, package_manager: str) -> Dict[str, Any]:
        """
        Get cache configuration for a specific package manager.
        
        Args:
            package_manager: Name of package manager
            
        Returns:
            Cache configuration
        """
        configs = {
            'npm': {
                'key': "${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}",
                'restore-keys': ["${{ runner.os }}-npm-"],
                'path': ["~/.npm", "node_modules"]
            },
            'yarn': {
                'key': "${{ runner.os }}-yarn-${{ hashFiles('**/yarn.lock') }}",
                'restore-keys': ["${{ runner.os }}-yarn-"],
                'path': ["~/.cache/yarn", "node_modules"]
            },
            'pip': {
                'key': "${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}",
                'restore-keys': ["${{ runner.os }}-pip-"],
                'path': ["~/.cache/pip"]
            },
            'bundler': {
                'key': "${{ runner.os }}-bundler-${{ hashFiles('**/Gemfile.lock') }}",
                'restore-keys': ["${{ runner.os }}-bundler-"],
                'path': ["vendor/bundle"]
            },
            'composer': {
                'key': "${{ runner.os }}-composer-${{ hashFiles('**/composer.lock') }}",
                'restore-keys': ["${{ runner.os }}-composer-"],
                'path': ["vendor"]
            },
            'cargo': {
                'key': "${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}",
                'restore-keys': ["${{ runner.os }}-cargo-"],
                'path': ["~/.cargo/registry", "~/.cargo/git", "target"]
            }
        }
        
        return configs.get(package_manager, {
            'key': f"${{{{ runner.os }}}}-{package_manager}-${{{{ hashFiles('**/*') }}}}",
            'restore-keys': [f"${{{{ runner.os }}}}-{package_manager}-"],
            'path': ["cache"]
        }) 