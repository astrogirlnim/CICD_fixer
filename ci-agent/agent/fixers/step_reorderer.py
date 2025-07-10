"""
Step Reorderer Module

Optimizes the order of steps in CI/CD jobs for better performance and cache utilization.
"""

import logging
import yaml
import re
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


class StepReorderer:
    """
    Reorders steps in CI/CD jobs for optimal execution and cache utilization.
    """
    
    # Step categories for ordering
    STEP_CATEGORIES = {
        'checkout': 1,      # Version control checkout
        'setup': 2,         # Environment setup (languages, tools)
        'cache_restore': 3, # Cache restoration
        'dependencies': 4,  # Dependency installation
        'build': 5,         # Build steps
        'test': 6,          # Test execution
        'cache_save': 7,    # Cache saving
        'artifacts': 8,     # Artifact handling
        'deploy': 9,        # Deployment steps
        'notify': 10        # Notifications
    }
    
    def __init__(self):
        """Initialize the step reorderer."""
        logger.debug("Initialized step reorderer")
    
    def reorder_steps(
        self,
        content: str,
        job_name: str,
        platform: str = "github_actions"
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Reorder steps in a specific job for optimal execution.
        
        Args:
            content: Current workflow content
            job_name: Name of the job to optimize
            platform: CI platform
            
        Returns:
            Tuple of (optimized content, list of changes made)
        """
        logger.info(f"Reordering steps in job '{job_name}'")
        
        if platform == "github_actions":
            return self._reorder_github_steps(content, job_name)
        elif platform == "gitlab_ci":
            return self._reorder_gitlab_steps(content, job_name)
        else:
            logger.warning(f"Unsupported platform: {platform}")
            return content, []
    
    def _reorder_github_steps(
        self,
        content: str,
        job_name: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Reorder steps in a GitHub Actions job.
        
        Args:
            content: Current workflow content
            job_name: Name of the job
            
        Returns:
            Tuple of (optimized content, list of changes)
        """
        changes = []
        
        try:
            workflow = yaml.safe_load(content)
            
            if not workflow or 'jobs' not in workflow:
                logger.error("Invalid workflow structure")
                return content, []
            
            if job_name not in workflow['jobs']:
                logger.error(f"Job '{job_name}' not found")
                return content, []
            
            job = workflow['jobs'][job_name]
            if 'steps' not in job or not isinstance(job['steps'], list):
                logger.debug(f"Job '{job_name}' has no steps to reorder")
                return content, []
            
            original_steps = job['steps'].copy()
            
            # Categorize steps
            categorized_steps = self._categorize_steps(original_steps)
            
            # Reorder steps based on categories
            reordered_steps = self._apply_reordering(categorized_steps)
            
            # Check if order changed
            if self._steps_differ(original_steps, reordered_steps):
                job['steps'] = reordered_steps
                
                # Document changes
                changes.append({
                    'type': 'reorder_steps',
                    'job': job_name,
                    'message': f"Reordered steps in job '{job_name}' for optimal execution",
                    'original_count': len(original_steps),
                    'details': self._describe_reordering(original_steps, reordered_steps)
                })
                
                # Convert back to YAML
                fixed_content = self._workflow_to_yaml(workflow)
                logger.info(f"Successfully reordered steps in job '{job_name}'")
                return fixed_content, changes
            else:
                logger.info(f"Steps in job '{job_name}' are already optimally ordered")
                return content, []
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML: {e}")
            return content, []
    
    def _categorize_steps(self, steps: List[Dict[str, Any]]) -> Dict[str, List[Tuple[int, Dict]]]:
        """
        Categorize steps based on their purpose.
        
        Args:
            steps: List of steps
            
        Returns:
            Dictionary mapping categories to lists of (index, step) tuples
        """
        categorized = {cat: [] for cat in self.STEP_CATEGORIES}
        categorized['other'] = []
        
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                categorized['other'].append((i, step))
                continue
            
            category = self._determine_step_category(step)
            categorized[category].append((i, step))
        
        return categorized
    
    def _determine_step_category(self, step: Dict[str, Any]) -> str:
        """
        Determine the category of a step.
        
        Args:
            step: Step dictionary
            
        Returns:
            Category name
        """
        uses = step.get('uses', '').lower()
        run = step.get('run', '').lower()
        name = step.get('name', '').lower()
        
        # Check for checkout
        if 'checkout' in uses:
            return 'checkout'
        
        # Check for setup
        if 'setup-' in uses or 'setup' in name:
            return 'setup'
        
        # Check for cache
        if 'cache' in uses:
            if 'restore' in name or 'restore' in uses:
                return 'cache_restore'
            elif 'save' in name or 'save' in uses:
                return 'cache_save'
            else:
                # Default cache action does both restore and save
                return 'cache_restore'
        
        # Check run commands
        if run:
            # Dependencies
            if any(cmd in run for cmd in ['install', 'npm ci', 'yarn', 'pip install', 
                                         'bundle install', 'composer install']):
                return 'dependencies'
            
            # Build
            if any(cmd in run for cmd in ['build', 'compile', 'make']):
                return 'build'
            
            # Test
            if any(cmd in run for cmd in ['test', 'jest', 'pytest', 'mocha', 'jasmine']):
                return 'test'
            
            # Deploy
            if any(cmd in run for cmd in ['deploy', 'publish', 'release']):
                return 'deploy'
        
        # Check for artifacts
        if 'artifact' in uses or 'artifact' in name:
            return 'artifacts'
        
        # Check for notifications
        if any(word in name or word in uses for word in ['notify', 'slack', 'email', 'webhook']):
            return 'notify'
        
        # Default category
        return 'other'
    
    def _apply_reordering(self, categorized: Dict[str, List[Tuple[int, Dict]]]) -> List[Dict[str, Any]]:
        """
        Apply optimal ordering to categorized steps.
        
        Args:
            categorized: Dictionary of categorized steps
            
        Returns:
            Reordered list of steps
        """
        reordered = []
        
        # Add steps in optimal order
        for category in sorted(self.STEP_CATEGORIES.keys(), 
                             key=lambda x: self.STEP_CATEGORIES[x]):
            if category in categorized:
                # Sort steps within category by original index to maintain relative order
                category_steps = sorted(categorized[category], key=lambda x: x[0])
                reordered.extend([step for _, step in category_steps])
        
        # Add uncategorized steps at the end
        if 'other' in categorized:
            other_steps = sorted(categorized['other'], key=lambda x: x[0])
            reordered.extend([step for _, step in other_steps])
        
        return reordered
    
    def _steps_differ(self, steps1: List[Dict], steps2: List[Dict]) -> bool:
        """
        Check if two step lists differ.
        
        Args:
            steps1: First step list
            steps2: Second step list
            
        Returns:
            True if steps differ
        """
        if len(steps1) != len(steps2):
            return True
        
        for s1, s2 in zip(steps1, steps2):
            # Compare key attributes
            if s1.get('name') != s2.get('name'):
                return True
            if s1.get('uses') != s2.get('uses'):
                return True
            if s1.get('run') != s2.get('run'):
                return True
        
        return False
    
    def _describe_reordering(self, original: List[Dict], reordered: List[Dict]) -> str:
        """
        Describe what changed in the reordering.
        
        Args:
            original: Original step order
            reordered: New step order
            
        Returns:
            Description of changes
        """
        changes = []
        
        # Find steps that moved
        for i, step in enumerate(reordered):
            original_index = None
            for j, orig_step in enumerate(original):
                if (step.get('name') == orig_step.get('name') and
                    step.get('uses') == orig_step.get('uses') and
                    step.get('run') == orig_step.get('run')):
                    original_index = j
                    break
            
            if original_index is not None and original_index != i:
                step_name = step.get('name', f"Step {original_index + 1}")
                if original_index > i:
                    changes.append(f"Moved '{step_name}' earlier (from position {original_index + 1} to {i + 1})")
                else:
                    changes.append(f"Moved '{step_name}' later (from position {original_index + 1} to {i + 1})")
        
        return "; ".join(changes) if changes else "Reordered for optimal execution"
    
    def _reorder_gitlab_steps(
        self,
        content: str,
        job_name: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Reorder steps in a GitLab CI job.
        
        Args:
            content: Current workflow content
            job_name: Name of the job
            
        Returns:
            Tuple of (optimized content, list of changes)
        """
        changes = []
        
        try:
            workflow = yaml.safe_load(content)
            
            if job_name not in workflow:
                logger.error(f"Job '{job_name}' not found")
                return content, []
            
            job = workflow[job_name]
            if not isinstance(job, dict) or 'script' not in job:
                logger.debug(f"Job '{job_name}' has no script to reorder")
                return content, []
            
            script = job['script']
            if not isinstance(script, list):
                # Single command, nothing to reorder
                return content, []
            
            original_script = script.copy()
            
            # Categorize and reorder commands
            categorized = self._categorize_gitlab_commands(script)
            reordered = self._apply_gitlab_reordering(categorized)
            
            if original_script != reordered:
                job['script'] = reordered
                
                changes.append({
                    'type': 'reorder_script',
                    'job': job_name,
                    'message': f"Reordered script commands in job '{job_name}'",
                    'command_count': len(script)
                })
                
                # Convert back to YAML
                fixed_content = self._workflow_to_yaml(workflow)
                return fixed_content, changes
            else:
                return content, []
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML: {e}")
            return content, []
    
    def _categorize_gitlab_commands(self, commands: List[str]) -> Dict[str, List[Tuple[int, str]]]:
        """
        Categorize GitLab CI script commands.
        
        Args:
            commands: List of commands
            
        Returns:
            Categorized commands
        """
        categorized = {
            'setup': [],
            'dependencies': [],
            'build': [],
            'test': [],
            'deploy': [],
            'other': []
        }
        
        for i, cmd in enumerate(commands):
            cmd_lower = cmd.lower()
            
            # Categorize based on command content
            if any(word in cmd_lower for word in ['apt-get', 'yum', 'apk add', 'brew']):
                categorized['setup'].append((i, cmd))
            elif any(word in cmd_lower for word in ['install', 'npm ci', 'yarn', 'pip install',
                                                   'bundle install', 'composer install']):
                categorized['dependencies'].append((i, cmd))
            elif any(word in cmd_lower for word in ['build', 'compile', 'make']):
                categorized['build'].append((i, cmd))
            elif any(word in cmd_lower for word in ['test', 'jest', 'pytest', 'mocha']):
                categorized['test'].append((i, cmd))
            elif any(word in cmd_lower for word in ['deploy', 'publish', 'release']):
                categorized['deploy'].append((i, cmd))
            else:
                categorized['other'].append((i, cmd))
        
        return categorized
    
    def _apply_gitlab_reordering(self, categorized: Dict[str, List[Tuple[int, str]]]) -> List[str]:
        """
        Apply optimal ordering to GitLab CI commands.
        
        Args:
            categorized: Categorized commands
            
        Returns:
            Reordered command list
        """
        reordered = []
        
        # Optimal order for GitLab CI
        order = ['setup', 'dependencies', 'build', 'test', 'deploy', 'other']
        
        for category in order:
            if category in categorized:
                # Sort by original index to maintain relative order
                category_cmds = sorted(categorized[category], key=lambda x: x[0])
                reordered.extend([cmd for _, cmd in category_cmds])
        
        return reordered
    
    def _workflow_to_yaml(self, workflow: Dict[str, Any]) -> str:
        """
        Convert workflow dictionary back to YAML.
        
        Args:
            workflow: Workflow dictionary
            
        Returns:
            YAML string
        """
        return yaml.dump(
            workflow,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120
        )
    
    def analyze_step_order(
        self,
        workflow_data: Dict[str, Any],
        platform: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze step ordering and generate optimization suggestions.
        
        Args:
            workflow_data: Parsed workflow data
            platform: CI platform
            
        Returns:
            List of step ordering suggestions
        """
        suggestions = []
        
        if platform == "github_actions":
            jobs = workflow_data.get('jobs', {})
            
            for job_name, job_data in jobs.items():
                if isinstance(job_data, dict) and 'steps' in job_data:
                    steps = job_data['steps']
                    if isinstance(steps, list) and len(steps) > 3:
                        # Analyze step order
                        issues = self._find_ordering_issues(steps)
                        
                        for issue in issues:
                            suggestions.append({
                                'type': 'step_order',
                                'severity': issue['severity'],
                                'job': job_name,
                                'message': issue['message'],
                                'suggestion': issue['suggestion']
                            })
        
        return suggestions
    
    def _find_ordering_issues(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find issues with step ordering.
        
        Args:
            steps: List of steps
            
        Returns:
            List of ordering issues
        """
        issues = []
        
        # Check for common ordering problems
        checkout_index = None
        cache_restore_index = None
        dependency_indices = []
        cache_save_index = None
        
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            
            category = self._determine_step_category(step)
            
            if category == 'checkout':
                checkout_index = i
            elif category == 'cache_restore':
                cache_restore_index = i
            elif category == 'dependencies':
                dependency_indices.append(i)
            elif category == 'cache_save':
                cache_save_index = i
        
        # Check if dependencies come before cache restore
        if cache_restore_index is not None and dependency_indices:
            if any(i < cache_restore_index for i in dependency_indices):
                issues.append({
                    'severity': 'medium',
                    'message': "Dependency installation happens before cache restoration",
                    'suggestion': "Move cache restoration before dependency installation to speed up builds"
                })
        
        # Check if checkout is not first
        if checkout_index is not None and checkout_index > 0:
            issues.append({
                'severity': 'medium',
                'message': "Checkout action is not the first step",
                'suggestion': "Move checkout to the beginning for better workflow clarity"
            })
        
        # Check if cache save comes before tests/builds
        if cache_save_index is not None:
            for i, step in enumerate(steps):
                if i > cache_save_index:
                    category = self._determine_step_category(step)
                    if category in ['build', 'test']:
                        issues.append({
                            'severity': 'low',
                            'message': "Build/test steps occur after cache save",
                            'suggestion': "Move cache save after all build and test steps"
                        })
                        break
        
        return issues 