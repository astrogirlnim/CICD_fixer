"""
Job Parallelizer Module

Optimizes job parallelization in CI/CD workflows by analyzing and adjusting dependencies.
"""

import logging
import yaml
import networkx as nx
from typing import Dict, Any, List, Set, Tuple, Optional

logger = logging.getLogger(__name__)


class JobParallelizer:
    """
    Optimizes job parallelization by analyzing and adjusting job dependencies.
    """
    
    def __init__(self):
        """Initialize the job parallelizer."""
        logger.debug("Initialized job parallelizer")
    
    def optimize_parallelization(
        self,
        content: str,
        workflow_data: Dict[str, Any],
        platform: str = "github_actions"
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Optimize job parallelization in a workflow.
        
        Args:
            content: Current workflow content
            workflow_data: Parsed workflow data
            platform: CI platform
            
        Returns:
            Tuple of (optimized content, list of changes made)
        """
        logger.info("Optimizing job parallelization")
        
        if platform == "github_actions":
            return self._optimize_github_actions(content, workflow_data)
        elif platform == "gitlab_ci":
            return self._optimize_gitlab_ci(content, workflow_data)
        else:
            logger.warning(f"Unsupported platform: {platform}")
            return content, []
    
    def _optimize_github_actions(
        self,
        content: str,
        workflow_data: Dict[str, Any]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Optimize GitHub Actions workflow parallelization.
        
        Args:
            content: Current workflow content
            workflow_data: Parsed workflow data
            
        Returns:
            Tuple of (optimized content, list of changes)
        """
        changes = []
        
        try:
            # Build dependency graph
            jobs = workflow_data.get('jobs', {})
            graph = self._build_dependency_graph(jobs)
            
            # Find optimization opportunities
            redundant_deps = self._find_redundant_dependencies(graph)
            parallelizable_jobs = self._find_parallelizable_jobs(jobs, graph)
            
            # Create optimized workflow
            optimized_workflow = yaml.safe_load(content)
            
            # Remove redundant dependencies
            for job_name, deps_to_remove in redundant_deps.items():
                if job_name in optimized_workflow['jobs']:
                    job = optimized_workflow['jobs'][job_name]
                    current_needs = self._get_needs_list(job.get('needs', []))
                    
                    # Remove redundant dependencies
                    new_needs = [dep for dep in current_needs if dep not in deps_to_remove]
                    
                    if len(new_needs) != len(current_needs):
                        if new_needs:
                            job['needs'] = new_needs if len(new_needs) > 1 else new_needs[0]
                        else:
                            # Remove needs entirely if no dependencies left
                            job.pop('needs', None)
                        
                        changes.append({
                            'type': 'remove_redundant_dependency',
                            'job': job_name,
                            'removed': list(deps_to_remove),
                            'message': f"Removed redundant dependencies from job '{job_name}'"
                        })
            
            # Make parallelizable jobs actually parallel
            for job_set in parallelizable_jobs:
                if len(job_set) > 1:
                    # Check if these jobs have sequential dependencies
                    sequential = False
                    for i, job1 in enumerate(job_set):
                        for job2 in job_set[i+1:]:
                            if graph.has_edge(job1, job2) or graph.has_edge(job2, job1):
                                sequential = True
                                break
                    
                    if sequential:
                        # Try to remove unnecessary sequential dependencies
                        for job in job_set:
                            if job in optimized_workflow['jobs']:
                                job_data = optimized_workflow['jobs'][job]
                                needs = self._get_needs_list(job_data.get('needs', []))
                                
                                # Remove dependencies on other jobs in the set
                                new_needs = [dep for dep in needs if dep not in job_set or dep == job]
                                
                                if len(new_needs) != len(needs):
                                    if new_needs:
                                        job_data['needs'] = new_needs if len(new_needs) > 1 else new_needs[0]
                                    else:
                                        job_data.pop('needs', None)
                                    
                                    changes.append({
                                        'type': 'enable_parallelization',
                                        'job': job,
                                        'message': f"Enabled parallel execution for job '{job}'"
                                    })
            
            # Convert back to YAML
            if changes:
                fixed_content = self._workflow_to_yaml(optimized_workflow)
                logger.info(f"Made {len(changes)} parallelization optimization(s)")
                return fixed_content, changes
            else:
                logger.info("No parallelization optimizations needed")
                return content, []
            
        except Exception as e:
            logger.error(f"Error optimizing parallelization: {e}")
            return content, []
    
    def _build_dependency_graph(self, jobs: Dict[str, Any]) -> nx.DiGraph:
        """
        Build a directed graph of job dependencies.
        
        Args:
            jobs: Dictionary of jobs from workflow
            
        Returns:
            NetworkX directed graph
        """
        graph = nx.DiGraph()
        
        # Add all jobs as nodes
        for job_name in jobs:
            graph.add_node(job_name)
        
        # Add edges for dependencies
        for job_name, job_data in jobs.items():
            if isinstance(job_data, dict):
                needs = self._get_needs_list(job_data.get('needs', []))
                for dep in needs:
                    if dep in jobs:  # Only add edge if dependency exists
                        graph.add_edge(dep, job_name)
        
        return graph
    
    def _get_needs_list(self, needs_value: Any) -> List[str]:
        """
        Convert needs value to a list of job names.
        
        Args:
            needs_value: The needs value (string, list, or dict)
            
        Returns:
            List of job names
        """
        if isinstance(needs_value, str):
            return [needs_value]
        elif isinstance(needs_value, list):
            # Handle both simple strings and complex objects
            result = []
            for item in needs_value:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict) and 'job' in item:
                    result.append(item['job'])
            return result
        else:
            return []
    
    def _find_redundant_dependencies(self, graph: nx.DiGraph) -> Dict[str, Set[str]]:
        """
        Find redundant dependencies in the job graph.
        
        A dependency is redundant if it's implied by another dependency.
        For example, if A depends on B and C, and B depends on C,
        then A's dependency on C is redundant.
        
        Args:
            graph: Job dependency graph
            
        Returns:
            Dictionary mapping job names to sets of redundant dependencies
        """
        redundant = {}
        
        for node in graph.nodes():
            direct_deps = set(graph.predecessors(node))
            
            if len(direct_deps) > 1:
                # Check each direct dependency
                redundant_deps = set()
                
                for dep in direct_deps:
                    # Get all ancestors of this dependency
                    dep_ancestors = nx.ancestors(graph, dep)
                    
                    # Check if any other direct dependencies are ancestors of this one
                    for other_dep in direct_deps:
                        if other_dep != dep and other_dep in dep_ancestors:
                            # other_dep is an ancestor of dep, so the direct link to other_dep is redundant
                            redundant_deps.add(other_dep)
                
                if redundant_deps:
                    redundant[node] = redundant_deps
                    logger.debug(f"Job '{node}' has redundant dependencies: {redundant_deps}")
        
        return redundant
    
    def _find_parallelizable_jobs(
        self,
        jobs: Dict[str, Any],
        graph: nx.DiGraph
    ) -> List[List[str]]:
        """
        Find sets of jobs that could run in parallel.
        
        Args:
            jobs: Dictionary of jobs
            graph: Job dependency graph
            
        Returns:
            List of job sets that could run in parallel
        """
        parallelizable = []
        
        # Find jobs at the same level in the graph
        try:
            # Use topological generations to find jobs that can run in parallel
            generations = list(nx.topological_generations(graph))
            
            for generation in generations:
                if len(generation) > 1:
                    # These jobs are at the same level and could potentially run in parallel
                    # Check if they're not already parallel (no dependencies between them)
                    job_list = list(generation)
                    
                    # Filter out jobs that depend on each other within this generation
                    independent_jobs = []
                    for job in job_list:
                        depends_on_others = False
                        for other_job in job_list:
                            if job != other_job and graph.has_edge(other_job, job):
                                depends_on_others = True
                                break
                        
                        if not depends_on_others:
                            independent_jobs.append(job)
                    
                    if len(independent_jobs) > 1:
                        parallelizable.append(independent_jobs)
                        logger.debug(f"Found parallelizable jobs: {independent_jobs}")
        
        except nx.NetworkXError:
            logger.warning("Graph has cycles, cannot determine parallelizable jobs")
        
        # Also look for jobs with identical dependencies
        jobs_by_deps = {}
        for job_name, job_data in jobs.items():
            if isinstance(job_data, dict):
                needs = tuple(sorted(self._get_needs_list(job_data.get('needs', []))))
                if needs not in jobs_by_deps:
                    jobs_by_deps[needs] = []
                jobs_by_deps[needs].append(job_name)
        
        for deps, job_list in jobs_by_deps.items():
            if len(job_list) > 1:
                # These jobs have identical dependencies and could run in parallel
                if job_list not in parallelizable:
                    parallelizable.append(job_list)
                    logger.debug(f"Jobs with identical dependencies: {job_list}")
        
        return parallelizable
    
    def _optimize_gitlab_ci(
        self,
        content: str,
        workflow_data: Dict[str, Any]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Optimize GitLab CI workflow parallelization.
        
        Args:
            content: Current workflow content
            workflow_data: Parsed workflow data
            
        Returns:
            Tuple of (optimized content, list of changes)
        """
        changes = []
        
        try:
            optimized_workflow = yaml.safe_load(content)
            
            # Find jobs (exclude special keys)
            special_keys = {'stages', 'variables', 'default', 'include', 'workflow'}
            jobs = {k: v for k, v in workflow_data.items() 
                   if k not in special_keys and isinstance(v, dict)}
            
            # Build dependency graph
            graph = self._build_gitlab_dependency_graph(jobs)
            
            # Find redundant dependencies
            redundant_deps = self._find_redundant_dependencies(graph)
            
            # Remove redundant dependencies
            for job_name, deps_to_remove in redundant_deps.items():
                if job_name in optimized_workflow:
                    job = optimized_workflow[job_name]
                    if 'needs' in job:
                        current_needs = self._get_gitlab_needs_list(job['needs'])
                        new_needs = [dep for dep in current_needs if dep not in deps_to_remove]
                        
                        if len(new_needs) != len(current_needs):
                            if new_needs:
                                job['needs'] = new_needs
                            else:
                                job.pop('needs', None)
                            
                            changes.append({
                                'type': 'remove_redundant_dependency',
                                'job': job_name,
                                'removed': list(deps_to_remove),
                                'message': f"Removed redundant dependencies from job '{job_name}'"
                            })
            
            # Convert back to YAML
            if changes:
                fixed_content = self._workflow_to_yaml(optimized_workflow)
                logger.info(f"Made {len(changes)} parallelization optimization(s)")
                return fixed_content, changes
            else:
                return content, []
            
        except Exception as e:
            logger.error(f"Error optimizing GitLab CI parallelization: {e}")
            return content, []
    
    def _build_gitlab_dependency_graph(self, jobs: Dict[str, Any]) -> nx.DiGraph:
        """
        Build dependency graph for GitLab CI jobs.
        
        Args:
            jobs: Dictionary of GitLab CI jobs
            
        Returns:
            NetworkX directed graph
        """
        graph = nx.DiGraph()
        
        # Add all jobs as nodes
        for job_name in jobs:
            graph.add_node(job_name)
        
        # Add edges for dependencies
        for job_name, job_data in jobs.items():
            if isinstance(job_data, dict) and 'needs' in job_data:
                needs = self._get_gitlab_needs_list(job_data['needs'])
                for dep in needs:
                    if dep in jobs:
                        graph.add_edge(dep, job_name)
        
        return graph
    
    def _get_gitlab_needs_list(self, needs_value: Any) -> List[str]:
        """
        Convert GitLab CI needs value to a list of job names.
        
        Args:
            needs_value: The needs value
            
        Returns:
            List of job names
        """
        if isinstance(needs_value, str):
            return [needs_value]
        elif isinstance(needs_value, list):
            result = []
            for item in needs_value:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict) and 'job' in item:
                    result.append(item['job'])
            return result
        elif isinstance(needs_value, dict):
            # GitLab CI can use dict format for needs
            return list(needs_value.keys())
        else:
            return []
    
    def _workflow_to_yaml(self, workflow: Dict[str, Any]) -> str:
        """
        Convert workflow dictionary back to YAML with proper formatting.
        
        Args:
            workflow: Workflow dictionary
            
        Returns:
            YAML string
        """
        # Use safe dump with nice formatting
        return yaml.dump(
            workflow,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120
        )
    
    def generate_parallelization_suggestions(
        self,
        workflow_data: Dict[str, Any],
        platform: str
    ) -> List[Dict[str, Any]]:
        """
        Generate suggestions for improving job parallelization.
        
        Args:
            workflow_data: Parsed workflow data
            platform: CI platform
            
        Returns:
            List of parallelization suggestions
        """
        suggestions = []
        
        if platform == "github_actions":
            jobs = workflow_data.get('jobs', {})
        else:
            # GitLab CI
            special_keys = {'stages', 'variables', 'default', 'include', 'workflow'}
            jobs = {k: v for k, v in workflow_data.items() 
                   if k not in special_keys and isinstance(v, dict)}
        
        # Build dependency graph
        graph = self._build_dependency_graph(jobs) if platform == "github_actions" else self._build_gitlab_dependency_graph(jobs)
        
        # Check for long sequential chains
        try:
            longest_path = nx.dag_longest_path(graph)
            if len(longest_path) > 3:
                suggestions.append({
                    'type': 'long_sequential_chain',
                    'severity': 'medium',
                    'path': longest_path,
                    'message': f"Long sequential job chain detected: {' -> '.join(longest_path)}",
                    'suggestion': "Consider restructuring jobs to enable more parallelization"
                })
        except nx.NetworkXError:
            pass
        
        # Check for jobs that could be split
        for job_name, job_data in jobs.items():
            if isinstance(job_data, dict):
                steps = []
                
                if platform == "github_actions":
                    steps = job_data.get('steps', [])
                elif 'script' in job_data:
                    # GitLab CI uses script array
                    script = job_data['script']
                    if isinstance(script, list):
                        steps = script
                
                if len(steps) > 10:
                    suggestions.append({
                        'type': 'large_job',
                        'severity': 'low',
                        'job': job_name,
                        'step_count': len(steps),
                        'message': f"Job '{job_name}' has {len(steps)} steps",
                        'suggestion': "Consider splitting into smaller, parallel jobs for faster execution"
                    })
        
        return suggestions 