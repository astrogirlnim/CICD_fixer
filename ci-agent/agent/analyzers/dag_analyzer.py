"""
DAG Analyzer Module

Analyzes job dependencies in CI/CD workflows and builds a Directed Acyclic Graph (DAG)
to understand execution order and identify optimization opportunities.
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
import networkx as nx
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Represents a job in the workflow."""
    name: str
    needs: List[str] = field(default_factory=list)
    runs_on: Optional[str] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    estimated_duration: Optional[int] = None  # in seconds
    can_parallelize: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DAGAnalysis:
    """Results of DAG analysis."""
    jobs: Dict[str, Job]
    dependency_graph: nx.DiGraph
    execution_stages: List[List[str]]  # Jobs that can run in parallel
    critical_path: List[str]
    bottlenecks: List[str]
    optimization_suggestions: List[Dict[str, Any]]
    total_serial_time: int  # If all jobs run sequentially
    optimal_parallel_time: int  # With maximum parallelization
    dependency_issues: List[Dict[str, Any]]


class DAGAnalyzer:
    """
    Analyzes job dependencies and builds execution graphs for CI/CD workflows.
    """
    
    def __init__(self):
        """Initialize the DAG analyzer."""
        logger.debug("Initialized DAG analyzer")
    
    def analyze_workflow(self, workflow_data: Dict[str, Any], platform: str) -> DAGAnalysis:
        """
        Analyze workflow dependencies and build a DAG.
        
        Args:
            workflow_data: Parsed workflow data
            platform: CI platform ('github_actions', 'gitlab_ci', etc.)
            
        Returns:
            DAGAnalysis object with analysis results
        """
        logger.info("🔍 Analyzing workflow dependencies")
        
        # Extract jobs based on platform
        jobs = self._extract_jobs(workflow_data, platform)
        
        # Build dependency graph
        graph = self._build_dependency_graph(jobs)
        
        # Check for dependency issues
        dependency_issues = self._check_dependency_issues(graph, jobs)
        
        # Calculate execution stages
        execution_stages = self._calculate_execution_stages(graph)
        
        # Find critical path
        critical_path = self._find_critical_path(graph, jobs)
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(graph, jobs, execution_stages)
        
        # Generate optimization suggestions
        suggestions = self._generate_optimization_suggestions(
            jobs, graph, execution_stages, bottlenecks
        )
        
        # Calculate timing estimates
        total_serial_time = self._calculate_serial_time(jobs)
        optimal_parallel_time = self._calculate_parallel_time(jobs, execution_stages)
        
        return DAGAnalysis(
            jobs=jobs,
            dependency_graph=graph,
            execution_stages=execution_stages,
            critical_path=critical_path,
            bottlenecks=bottlenecks,
            optimization_suggestions=suggestions,
            total_serial_time=total_serial_time,
            optimal_parallel_time=optimal_parallel_time,
            dependency_issues=dependency_issues
        )
    
    def _extract_jobs(self, workflow_data: Dict[str, Any], platform: str) -> Dict[str, Job]:
        """
        Extract job information from workflow data.
        
        Args:
            workflow_data: Parsed workflow data
            platform: CI platform
            
        Returns:
            Dictionary mapping job names to Job objects
        """
        jobs = {}
        
        if platform == 'github_actions':
            workflow_jobs = workflow_data.get('jobs', {})
            for job_name, job_data in workflow_jobs.items():
                if isinstance(job_data, dict):
                    job = Job(
                        name=job_name,
                        needs=self._parse_needs(job_data.get('needs', [])),
                        runs_on=job_data.get('runs-on'),
                        steps=job_data.get('steps', []),
                        metadata=job_data
                    )
                    
                    # Estimate duration based on steps
                    job.estimated_duration = self._estimate_job_duration(job)
                    
                    # Check if job can be parallelized
                    job.can_parallelize = self._can_parallelize(job)
                    
                    jobs[job_name] = job
                    logger.debug(f"Extracted job: {job_name} (needs: {job.needs})")
        
        elif platform == 'gitlab_ci':
            # GitLab CI jobs are top-level keys (excluding special keys)
            special_keys = {'stages', 'variables', 'default', 'include', 'workflow'}
            for key, value in workflow_data.items():
                if key not in special_keys and isinstance(value, dict):
                    job = Job(
                        name=key,
                        needs=self._parse_needs(value.get('needs', [])),
                        metadata=value
                    )
                    jobs[key] = job
        
        logger.info(f"✅ Extracted {len(jobs)} jobs from workflow")
        return jobs
    
    def _parse_needs(self, needs_value: Any) -> List[str]:
        """
        Parse the 'needs' field which can be a string, list, or dict.
        
        Args:
            needs_value: The value of the needs field
            
        Returns:
            List of job names that are dependencies
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
        elif isinstance(needs_value, dict):
            # GitLab CI format
            return list(needs_value.keys())
        else:
            return []
    
    def _build_dependency_graph(self, jobs: Dict[str, Job]) -> nx.DiGraph:
        """
        Build a directed graph of job dependencies.
        
        Args:
            jobs: Dictionary of jobs
            
        Returns:
            NetworkX directed graph
        """
        graph = nx.DiGraph()
        
        # Add all jobs as nodes
        for job_name, job in jobs.items():
            graph.add_node(job_name, job=job)
        
        # Add edges for dependencies
        for job_name, job in jobs.items():
            for dependency in job.needs:
                if dependency in jobs:
                    graph.add_edge(dependency, job_name)
                else:
                    logger.warning(f"⚠️  Job '{job_name}' depends on non-existent job '{dependency}'")
        
        logger.debug(f"Built dependency graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph
    
    def _check_dependency_issues(self, graph: nx.DiGraph, jobs: Dict[str, Job]) -> List[Dict[str, Any]]:
        """
        Check for issues in the dependency graph.
        
        Args:
            graph: Dependency graph
            jobs: Dictionary of jobs
            
        Returns:
            List of dependency issues found
        """
        issues = []
        
        # Check for cycles
        if not nx.is_directed_acyclic_graph(graph):
            cycles = list(nx.simple_cycles(graph))
            for cycle in cycles:
                issues.append({
                    'type': 'circular_dependency',
                    'severity': 'high',
                    'jobs': cycle,
                    'message': f"Circular dependency detected: {' -> '.join(cycle + [cycle[0]])}",
                    'suggestion': "Remove or restructure dependencies to eliminate the cycle"
                })
        
        # Check for missing dependencies
        for job_name, job in jobs.items():
            for dep in job.needs:
                if dep not in jobs:
                    issues.append({
                        'type': 'missing_dependency',
                        'severity': 'high',
                        'job': job_name,
                        'missing': dep,
                        'message': f"Job '{job_name}' depends on non-existent job '{dep}'",
                        'suggestion': f"Either create job '{dep}' or remove it from the needs list"
                    })
        
        # Check for unnecessary dependencies
        for job_name in graph.nodes():
            # Get direct and indirect dependencies
            direct_deps = set(graph.predecessors(job_name))
            all_deps = nx.ancestors(graph, job_name)
            indirect_deps = all_deps - direct_deps
            
            # Check if any direct dependency is also reachable indirectly
            for dep in direct_deps:
                dep_ancestors = nx.ancestors(graph, dep)
                if dep_ancestors & direct_deps:
                    redundant = dep_ancestors & direct_deps
                    issues.append({
                        'type': 'redundant_dependency',
                        'severity': 'low',
                        'job': job_name,
                        'dependency': dep,
                        'redundant_with': list(redundant),
                        'message': f"Job '{job_name}' has redundant dependency on '{dep}'",
                        'suggestion': f"Remove '{dep}' from needs as it's implied by {list(redundant)}"
                    })
        
        return issues
    
    def _calculate_execution_stages(self, graph: nx.DiGraph) -> List[List[str]]:
        """
        Calculate which jobs can run in parallel at each stage.
        
        Args:
            graph: Dependency graph
            
        Returns:
            List of stages, where each stage is a list of jobs that can run in parallel
        """
        if graph.number_of_nodes() == 0:
            return []
        
        # Use topological generations to find parallel stages
        try:
            stages = list(nx.topological_generations(graph))
            logger.debug(f"Calculated {len(stages)} execution stages")
            return stages
        except nx.NetworkXError:
            logger.error("Cannot calculate stages - graph has cycles")
            return []
    
    def _find_critical_path(self, graph: nx.DiGraph, jobs: Dict[str, Job]) -> List[str]:
        """
        Find the critical path (longest path) through the workflow.
        
        Args:
            graph: Dependency graph
            jobs: Dictionary of jobs
            
        Returns:
            List of job names in the critical path
        """
        if graph.number_of_nodes() == 0:
            return []
        
        # Add weights based on estimated duration
        weighted_graph = graph.copy()
        for node in weighted_graph.nodes():
            job = jobs.get(node)
            if job:
                weighted_graph.nodes[node]['weight'] = job.estimated_duration or 60
        
        # Find longest path (critical path)
        try:
            # For DAG, we can use topological sort
            topo_order = list(nx.topological_sort(weighted_graph))
            
            # Calculate longest path to each node
            distances = {node: 0 for node in weighted_graph.nodes()}
            predecessors = {node: None for node in weighted_graph.nodes()}
            
            for node in topo_order:
                for successor in weighted_graph.successors(node):
                    node_weight = weighted_graph.nodes[node].get('weight', 0)
                    if distances[node] + node_weight > distances[successor]:
                        distances[successor] = distances[node] + node_weight
                        predecessors[successor] = node
            
            # Find the end node with maximum distance
            end_node = max(distances.items(), key=lambda x: x[1])[0]
            
            # Reconstruct path
            path = []
            current = end_node
            while current is not None:
                path.append(current)
                current = predecessors[current]
            
            path.reverse()
            logger.info(f"📍 Critical path: {' -> '.join(path)}")
            return path
            
        except nx.NetworkXError:
            logger.error("Cannot find critical path - graph has cycles")
            return []
    
    def _identify_bottlenecks(
        self,
        graph: nx.DiGraph,
        jobs: Dict[str, Job],
        execution_stages: List[List[str]]
    ) -> List[str]:
        """
        Identify jobs that are bottlenecks in the workflow.
        
        Args:
            graph: Dependency graph
            jobs: Dictionary of jobs
            execution_stages: Execution stages
            
        Returns:
            List of job names that are bottlenecks
        """
        bottlenecks = []
        
        # Jobs with many dependents are potential bottlenecks
        for node in graph.nodes():
            out_degree = graph.out_degree(node)
            if out_degree >= 3:  # Arbitrary threshold
                bottlenecks.append(node)
                logger.debug(f"Bottleneck: {node} blocks {out_degree} jobs")
        
        # Jobs that are alone in their stage and have dependents
        for stage in execution_stages:
            if len(stage) == 1:
                job_name = stage[0]
                if graph.out_degree(job_name) > 0:
                    if job_name not in bottlenecks:
                        bottlenecks.append(job_name)
                        logger.debug(f"Bottleneck: {job_name} is alone in its stage")
        
        return bottlenecks
    
    def _generate_optimization_suggestions(
        self,
        jobs: Dict[str, Job],
        graph: nx.DiGraph,
        execution_stages: List[List[str]],
        bottlenecks: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate suggestions for optimizing the workflow.
        
        Args:
            jobs: Dictionary of jobs
            graph: Dependency graph
            execution_stages: Execution stages
            bottlenecks: Identified bottlenecks
            
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        # Check for jobs that could run in parallel but don't
        for i, stage in enumerate(execution_stages[:-1]):
            for job1 in stage:
                for job2 in stage:
                    if job1 < job2:  # Avoid duplicates
                        # Check if these jobs have any shared downstream dependencies
                        job1_descendants = nx.descendants(graph, job1)
                        job2_descendants = nx.descendants(graph, job2)
                        shared = job1_descendants & job2_descendants
                        
                        if not shared and len(stage) == 1:
                            suggestions.append({
                                'type': 'parallelize_independent_jobs',
                                'severity': 'medium',
                                'jobs': [job1, job2],
                                'message': f"Jobs '{job1}' and '{job2}' could potentially run in parallel",
                                'suggestion': "Review if these jobs truly need to run sequentially"
                            })
        
        # Suggest splitting bottleneck jobs
        for bottleneck in bottlenecks:
            job = jobs.get(bottleneck)
            if job and len(job.steps) > 5:
                suggestions.append({
                    'type': 'split_bottleneck_job',
                    'severity': 'medium',
                    'job': bottleneck,
                    'message': f"Job '{bottleneck}' is a bottleneck with {len(job.steps)} steps",
                    'suggestion': "Consider splitting this job into smaller, parallel jobs"
                })
        
        # Check for long dependency chains
        for path in nx.all_simple_paths(graph, source=None, target=None):
            if len(path) > 4:
                suggestions.append({
                    'type': 'long_dependency_chain',
                    'severity': 'low',
                    'path': path,
                    'message': f"Long dependency chain: {' -> '.join(path)}",
                    'suggestion': "Consider restructuring to reduce sequential dependencies"
                })
                break  # Only report the first one
        
        return suggestions
    
    def _estimate_job_duration(self, job: Job) -> int:
        """
        Estimate job duration based on steps.
        
        Args:
            job: Job object
            
        Returns:
            Estimated duration in seconds
        """
        # Simple heuristic: 30 seconds per step
        base_time = len(job.steps) * 30
        
        # Add time for specific actions
        for step in job.steps:
            if isinstance(step, dict):
                # Check for time-consuming actions
                if 'uses' in step:
                    action = step['uses']
                    if 'setup-' in action or 'cache' in action:
                        base_time += 30
                    elif 'build' in action or 'test' in action:
                        base_time += 120
                elif 'run' in step:
                    # Check for time-consuming commands
                    run_cmd = step['run'].lower()
                    if 'npm install' in run_cmd or 'yarn install' in run_cmd:
                        base_time += 60
                    elif 'build' in run_cmd:
                        base_time += 120
                    elif 'test' in run_cmd:
                        base_time += 90
        
        return base_time
    
    def _can_parallelize(self, job: Job) -> bool:
        """
        Determine if a job can be parallelized.
        
        Args:
            job: Job object
            
        Returns:
            True if job can be parallelized
        """
        # Jobs with certain characteristics shouldn't be parallelized
        for step in job.steps:
            if isinstance(step, dict):
                # Deployment steps usually shouldn't be parallel
                if 'deploy' in str(step).lower():
                    return False
                # Release steps shouldn't be parallel
                if 'release' in str(step).lower():
                    return False
        
        return True
    
    def _calculate_serial_time(self, jobs: Dict[str, Job]) -> int:
        """
        Calculate total time if all jobs run sequentially.
        
        Args:
            jobs: Dictionary of jobs
            
        Returns:
            Total time in seconds
        """
        return sum(job.estimated_duration or 60 for job in jobs.values())
    
    def _calculate_parallel_time(
        self,
        jobs: Dict[str, Job],
        execution_stages: List[List[str]]
    ) -> int:
        """
        Calculate time with optimal parallelization.
        
        Args:
            jobs: Dictionary of jobs
            execution_stages: Execution stages
            
        Returns:
            Total time in seconds
        """
        total_time = 0
        
        for stage in execution_stages:
            # Time for a stage is the maximum time of any job in that stage
            stage_time = max(
                jobs[job_name].estimated_duration or 60
                for job_name in stage
            )
            total_time += stage_time
        
        return total_time 