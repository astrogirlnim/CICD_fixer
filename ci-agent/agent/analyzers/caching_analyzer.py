"""
Caching Strategy Analyzer Module

Analyzes CI/CD workflows to identify caching opportunities, detect issues,
and suggest optimizations for better cache utilization.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cache configuration in the workflow."""
    job_name: str
    step_index: int
    key: str
    restore_keys: List[str] = field(default_factory=list)
    path: List[str] = field(default_factory=list)
    cache_action: str = ""  # 'save', 'restore', or 'both'
    is_valid: bool = True
    issues: List[str] = field(default_factory=list)


@dataclass
class CacheAnalysis:
    """Results of cache analysis."""
    cache_entries: List[CacheEntry]
    cache_coverage: Dict[str, bool]  # job_name -> has_cache
    optimization_opportunities: List[Dict[str, Any]]
    cache_key_patterns: Dict[str, int]  # pattern -> count
    suggested_improvements: List[Dict[str, Any]]
    estimated_time_savings: int  # in seconds
    cache_hit_probability: float  # 0.0 to 1.0


class CachingAnalyzer:
    """
    Analyzes caching strategies in CI/CD workflows and suggests improvements.
    """
    
    # Common package managers and their cache directories
    PACKAGE_MANAGERS = {
        'npm': {
            'commands': ['npm install', 'npm ci'],
            'cache_paths': ['~/.npm', 'node_modules'],
            'lockfile': 'package-lock.json',
            'manifest': 'package.json'
        },
        'yarn': {
            'commands': ['yarn install', 'yarn'],
            'cache_paths': ['~/.cache/yarn', 'node_modules'],
            'lockfile': 'yarn.lock',
            'manifest': 'package.json'
        },
        'pip': {
            'commands': ['pip install', 'python -m pip install'],
            'cache_paths': ['~/.cache/pip', '.venv', 'venv'],
            'lockfile': 'requirements.txt',
            'manifest': 'requirements.txt'
        },
        'bundler': {
            'commands': ['bundle install'],
            'cache_paths': ['vendor/bundle', '~/.bundle'],
            'lockfile': 'Gemfile.lock',
            'manifest': 'Gemfile'
        },
        'gradle': {
            'commands': ['gradle', './gradlew'],
            'cache_paths': ['~/.gradle/caches', '~/.gradle/wrapper'],
            'lockfile': 'gradle.lockfile',
            'manifest': 'build.gradle'
        },
        'maven': {
            'commands': ['mvn'],
            'cache_paths': ['~/.m2/repository'],
            'lockfile': 'pom.xml',
            'manifest': 'pom.xml'
        },
        'composer': {
            'commands': ['composer install'],
            'cache_paths': ['vendor', '~/.composer/cache'],
            'lockfile': 'composer.lock',
            'manifest': 'composer.json'
        },
        'cargo': {
            'commands': ['cargo build', 'cargo test'],
            'cache_paths': ['~/.cargo/registry', '~/.cargo/git', 'target'],
            'lockfile': 'Cargo.lock',
            'manifest': 'Cargo.toml'
        }
    }
    
    def __init__(self):
        """Initialize the caching analyzer."""
        logger.debug("Initialized caching analyzer")
    
    def analyze_caching(self, workflow_data: Dict[str, Any], platform: str) -> CacheAnalysis:
        """
        Analyze caching strategy in the workflow.
        
        Args:
            workflow_data: Parsed workflow data
            platform: CI platform
            
        Returns:
            CacheAnalysis object with analysis results
        """
        logger.info("🔍 Analyzing caching strategies")
        
        # Extract cache entries from workflow
        cache_entries = self._extract_cache_entries(workflow_data, platform)
        
        # Analyze cache coverage per job
        cache_coverage = self._analyze_cache_coverage(workflow_data, cache_entries, platform)
        
        # Identify optimization opportunities
        opportunities = self._identify_optimization_opportunities(
            workflow_data, cache_entries, cache_coverage, platform
        )
        
        # Analyze cache key patterns
        cache_key_patterns = self._analyze_cache_key_patterns(cache_entries)
        
        # Generate improvement suggestions
        suggestions = self._generate_cache_suggestions(
            workflow_data, cache_entries, opportunities, platform
        )
        
        # Estimate potential time savings
        time_savings = self._estimate_time_savings(opportunities)
        
        # Estimate cache hit probability
        hit_probability = self._estimate_cache_hit_probability(cache_entries)
        
        return CacheAnalysis(
            cache_entries=cache_entries,
            cache_coverage=cache_coverage,
            optimization_opportunities=opportunities,
            cache_key_patterns=cache_key_patterns,
            suggested_improvements=suggestions,
            estimated_time_savings=time_savings,
            cache_hit_probability=hit_probability
        )
    
    def _extract_cache_entries(self, workflow_data: Dict[str, Any], platform: str) -> List[CacheEntry]:
        """
        Extract cache configurations from workflow.
        
        Args:
            workflow_data: Parsed workflow data
            platform: CI platform
            
        Returns:
            List of cache entries found
        """
        cache_entries = []
        
        if platform == 'github_actions':
            jobs = workflow_data.get('jobs', {})
            for job_name, job_data in jobs.items():
                if isinstance(job_data, dict):
                    steps = job_data.get('steps', [])
                    for i, step in enumerate(steps):
                        if isinstance(step, dict):
                            # Check for cache actions
                            uses = step.get('uses', '')
                            if 'actions/cache' in uses:
                                entry = self._parse_github_cache_step(job_name, i, step)
                                cache_entries.append(entry)
                            elif 'cache' in uses.lower():
                                # Other cache actions (e.g., language-specific)
                                entry = self._parse_generic_cache_step(job_name, i, step)
                                cache_entries.append(entry)
        
        elif platform == 'gitlab_ci':
            # GitLab CI uses a different caching syntax
            for job_name, job_data in workflow_data.items():
                if isinstance(job_data, dict) and 'cache' in job_data:
                    cache_config = job_data['cache']
                    entry = self._parse_gitlab_cache(job_name, cache_config)
                    cache_entries.append(entry)
        
        logger.info(f"✅ Found {len(cache_entries)} cache configurations")
        return cache_entries
    
    def _parse_github_cache_step(self, job_name: str, step_index: int, step: Dict[str, Any]) -> CacheEntry:
        """
        Parse a GitHub Actions cache step.
        
        Args:
            job_name: Name of the job
            step_index: Index of the step
            step: Step configuration
            
        Returns:
            CacheEntry object
        """
        with_config = step.get('with', {})
        
        entry = CacheEntry(
            job_name=job_name,
            step_index=step_index,
            key=with_config.get('key', ''),
            path=self._parse_paths(with_config.get('path', '')),
            cache_action='both'  # GitHub cache action does both save and restore
        )
        
        # Parse restore-keys
        restore_keys = with_config.get('restore-keys', '')
        if restore_keys:
            if isinstance(restore_keys, str):
                entry.restore_keys = [k.strip() for k in restore_keys.split('\n') if k.strip()]
            elif isinstance(restore_keys, list):
                entry.restore_keys = restore_keys
        
        # Validate entry
        if not entry.key:
            entry.is_valid = False
            entry.issues.append("Cache key is missing")
        
        if not entry.path:
            entry.is_valid = False
            entry.issues.append("Cache path is missing")
        
        return entry
    
    def _parse_generic_cache_step(self, job_name: str, step_index: int, step: Dict[str, Any]) -> CacheEntry:
        """
        Parse a generic cache step (non-standard cache action).
        
        Args:
            job_name: Name of the job
            step_index: Index of the step
            step: Step configuration
            
        Returns:
            CacheEntry object
        """
        # Try to extract cache information from various formats
        uses = step.get('uses', '')
        with_config = step.get('with', {})
        
        entry = CacheEntry(
            job_name=job_name,
            step_index=step_index,
            cache_action='restore' if 'restore' in uses.lower() else 'save'
        )
        
        # Try to find cache key and paths
        for key in ['key', 'cache-key', 'cache_key']:
            if key in with_config:
                entry.key = with_config[key]
                break
        
        for key in ['path', 'paths', 'cache-path', 'cache_path']:
            if key in with_config:
                entry.path = self._parse_paths(with_config[key])
                break
        
        return entry
    
    def _parse_gitlab_cache(self, job_name: str, cache_config: Any) -> CacheEntry:
        """
        Parse GitLab CI cache configuration.
        
        Args:
            job_name: Name of the job
            cache_config: Cache configuration
            
        Returns:
            CacheEntry object
        """
        if isinstance(cache_config, dict):
            key = cache_config.get('key', '')
            if isinstance(key, dict):
                key = key.get('files', []) or key.get('prefix', '')
            
            paths = cache_config.get('paths', [])
            if isinstance(paths, str):
                paths = [paths]
            
            return CacheEntry(
                job_name=job_name,
                step_index=0,
                key=str(key),
                path=paths,
                cache_action='both'
            )
        else:
            return CacheEntry(
                job_name=job_name,
                step_index=0,
                key='',
                path=[],
                cache_action='both',
                is_valid=False,
                issues=["Invalid cache configuration format"]
            )
    
    def _parse_paths(self, path_value: Any) -> List[str]:
        """
        Parse cache paths from various formats.
        
        Args:
            path_value: Path value (string or list)
            
        Returns:
            List of paths
        """
        if isinstance(path_value, str):
            # Handle multiline strings
            return [p.strip() for p in path_value.split('\n') if p.strip()]
        elif isinstance(path_value, list):
            return path_value
        else:
            return []
    
    def _analyze_cache_coverage(
        self,
        workflow_data: Dict[str, Any],
        cache_entries: List[CacheEntry],
        platform: str
    ) -> Dict[str, bool]:
        """
        Analyze which jobs have caching configured.
        
        Args:
            workflow_data: Parsed workflow data
            cache_entries: List of cache entries
            platform: CI platform
            
        Returns:
            Dictionary mapping job names to whether they have caching
        """
        coverage = {}
        cached_jobs = {entry.job_name for entry in cache_entries}
        
        if platform == 'github_actions':
            jobs = workflow_data.get('jobs', {})
            for job_name in jobs:
                coverage[job_name] = job_name in cached_jobs
        
        return coverage
    
    def _identify_optimization_opportunities(
        self,
        workflow_data: Dict[str, Any],
        cache_entries: List[CacheEntry],
        cache_coverage: Dict[str, bool],
        platform: str
    ) -> List[Dict[str, Any]]:
        """
        Identify opportunities for cache optimization.
        
        Args:
            workflow_data: Parsed workflow data
            cache_entries: List of cache entries
            cache_coverage: Cache coverage analysis
            platform: CI platform
            
        Returns:
            List of optimization opportunities
        """
        opportunities = []
        
        if platform == 'github_actions':
            jobs = workflow_data.get('jobs', {})
            
            for job_name, job_data in jobs.items():
                if isinstance(job_data, dict):
                    steps = job_data.get('steps', [])
                    
                    # Check for package manager usage without caching
                    package_managers_used = self._detect_package_managers(steps)
                    
                    if package_managers_used and not cache_coverage.get(job_name, False):
                        opportunities.append({
                            'type': 'missing_cache',
                            'severity': 'high',
                            'job': job_name,
                            'package_managers': list(package_managers_used),
                            'message': f"Job '{job_name}' uses package managers but has no caching",
                            'potential_time_savings': 60 * len(package_managers_used)
                        })
                    
                    # Check for inefficient cache keys
                    job_cache_entries = [e for e in cache_entries if e.job_name == job_name]
                    for entry in job_cache_entries:
                        issues = self._analyze_cache_key_quality(entry)
                        if issues:
                            opportunities.append({
                                'type': 'inefficient_cache_key',
                                'severity': 'medium',
                                'job': job_name,
                                'step': entry.step_index,
                                'issues': issues,
                                'message': f"Cache key could be improved in job '{job_name}'",
                                'potential_time_savings': 30
                            })
        
        return opportunities
    
    def _detect_package_managers(self, steps: List[Dict[str, Any]]) -> Set[str]:
        """
        Detect which package managers are used in the job steps.
        
        Args:
            steps: List of job steps
            
        Returns:
            Set of package manager names
        """
        detected = set()
        
        for step in steps:
            if isinstance(step, dict):
                run_command = step.get('run', '')
                uses_action = step.get('uses', '')
                
                # Check run commands
                for pm_name, pm_info in self.PACKAGE_MANAGERS.items():
                    for cmd in pm_info['commands']:
                        if cmd in run_command:
                            detected.add(pm_name)
                            break
                
                # Check for setup actions
                if 'setup-node' in uses_action:
                    detected.add('npm')
                elif 'setup-python' in uses_action:
                    detected.add('pip')
                elif 'setup-ruby' in uses_action:
                    detected.add('bundler')
        
        return detected
    
    def _analyze_cache_key_quality(self, entry: CacheEntry) -> List[str]:
        """
        Analyze the quality of a cache key.
        
        Args:
            entry: Cache entry to analyze
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Check for static keys
        if not any(var in entry.key for var in ['${{', '${', '$(']) :
            issues.append("Cache key appears to be static - consider adding dynamic elements")
        
        # Check for missing restore keys
        if not entry.restore_keys:
            issues.append("No restore-keys defined - cache misses will be more frequent")
        
        # Check for overly specific keys
        if entry.key.count('-') > 5:
            issues.append("Cache key might be too specific - consider broader restore-keys")
        
        # Check for missing OS in key
        if 'runner.os' not in entry.key and '${{ runner.os }}' not in entry.key:
            issues.append("Cache key doesn't include OS - might cause cross-platform issues")
        
        return issues
    
    def _analyze_cache_key_patterns(self, cache_entries: List[CacheEntry]) -> Dict[str, int]:
        """
        Analyze patterns in cache keys.
        
        Args:
            cache_entries: List of cache entries
            
        Returns:
            Dictionary of pattern usage counts
        """
        patterns = {
            'includes_os': 0,
            'includes_hash': 0,
            'includes_date': 0,
            'static_key': 0,
            'has_restore_keys': 0
        }
        
        for entry in cache_entries:
            if 'runner.os' in entry.key or 'matrix.os' in entry.key:
                patterns['includes_os'] += 1
            
            if 'hashFiles' in entry.key:
                patterns['includes_hash'] += 1
            
            if any(date_var in entry.key for date_var in ['date', 'day', 'week', 'month']):
                patterns['includes_date'] += 1
            
            if '${{' not in entry.key and '${' not in entry.key:
                patterns['static_key'] += 1
            
            if entry.restore_keys:
                patterns['has_restore_keys'] += 1
        
        return patterns
    
    def _generate_cache_suggestions(
        self,
        workflow_data: Dict[str, Any],
        cache_entries: List[CacheEntry],
        opportunities: List[Dict[str, Any]],
        platform: str
    ) -> List[Dict[str, Any]]:
        """
        Generate specific suggestions for improving caching.
        
        Args:
            workflow_data: Parsed workflow data
            cache_entries: List of cache entries
            opportunities: Identified opportunities
            platform: CI platform
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Suggest caching for detected package managers
        for opp in opportunities:
            if opp['type'] == 'missing_cache':
                for pm in opp['package_managers']:
                    pm_info = self.PACKAGE_MANAGERS.get(pm, {})
                    suggestion = {
                        'type': 'add_cache',
                        'job': opp['job'],
                        'package_manager': pm,
                        'severity': 'high',
                        'message': f"Add caching for {pm} dependencies",
                        'cache_config': {
                            'key': f"${{{{ runner.os }}}}-{pm}-${{{{ hashFiles('{pm_info.get('lockfile', 'lockfile')}') }}}}",
                            'restore-keys': [
                                f"${{{{ runner.os }}}}-{pm}-",
                                f"${{{{ runner.os }}}}-"
                            ],
                            'path': pm_info.get('cache_paths', [])
                        }
                    }
                    suggestions.append(suggestion)
        
        # Suggest improvements for existing cache entries
        for entry in cache_entries:
            if not entry.restore_keys:
                suggestions.append({
                    'type': 'add_restore_keys',
                    'job': entry.job_name,
                    'severity': 'medium',
                    'message': "Add restore-keys for better cache hit rate",
                    'suggested_restore_keys': self._suggest_restore_keys(entry.key)
                })
        
        return suggestions
    
    def _suggest_restore_keys(self, cache_key: str) -> List[str]:
        """
        Suggest restore keys based on a cache key.
        
        Args:
            cache_key: The primary cache key
            
        Returns:
            List of suggested restore keys
        """
        restore_keys = []
        
        # Remove the most specific parts progressively
        if 'hashFiles' in cache_key:
            # Remove hash part
            base_key = re.sub(r'-\$\{\{[^}]*hashFiles[^}]*\}\}', '-', cache_key)
            restore_keys.append(base_key)
        
        # If key has multiple segments, create progressive keys
        segments = cache_key.split('-')
        if len(segments) > 2:
            for i in range(len(segments) - 1, 1, -1):
                restore_keys.append('-'.join(segments[:i]) + '-')
        
        return restore_keys
    
    def _estimate_time_savings(self, opportunities: List[Dict[str, Any]]) -> int:
        """
        Estimate potential time savings from implementing opportunities.
        
        Args:
            opportunities: List of optimization opportunities
            
        Returns:
            Estimated time savings in seconds
        """
        total_savings = 0
        
        for opp in opportunities:
            savings = opp.get('potential_time_savings', 0)
            total_savings += savings
        
        return total_savings
    
    def _estimate_cache_hit_probability(self, cache_entries: List[CacheEntry]) -> float:
        """
        Estimate the probability of cache hits based on key quality.
        
        Args:
            cache_entries: List of cache entries
            
        Returns:
            Probability between 0.0 and 1.0
        """
        if not cache_entries:
            return 0.0
        
        total_score = 0.0
        
        for entry in cache_entries:
            score = 0.5  # Base score
            
            # Good practices increase score
            if entry.restore_keys:
                score += 0.2
            
            if 'hashFiles' in entry.key:
                score += 0.1
            
            if 'runner.os' in entry.key:
                score += 0.1
            
            # Bad practices decrease score
            if '${{' not in entry.key:  # Static key
                score -= 0.3
            
            if len(entry.restore_keys) > 2:
                score += 0.1
            
            total_score += max(0.0, min(1.0, score))
        
        return total_score / len(cache_entries) 