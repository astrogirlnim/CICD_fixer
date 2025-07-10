"""
Secrets Redactor Module

Detects and redacts sensitive information from workflow files before
sending them to external services like LLMs or logging systems.
"""

import re
import logging
from typing import List, Dict, Pattern, Tuple, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RedactedSecret:
    """Represents a redacted secret found in the content."""
    pattern_name: str
    original_value: str
    redacted_value: str
    line_number: int
    column_start: int
    column_end: int


class SecretsRedactor:
    """
    Handles detection and redaction of secrets in CI/CD configuration files.
    """
    
    # Common secret patterns with their regex patterns
    DEFAULT_PATTERNS = {
        # API Keys and Tokens
        "github_token": r"ghp_[a-zA-Z0-9]{36}",
        "github_oauth": r"gho_[a-zA-Z0-9]{36}",
        "github_app_token": r"ghs_[a-zA-Z0-9]{36}",
        "github_refresh_token": r"ghr_[a-zA-Z0-9]{36}",
        "gitlab_token": r"glpat-[a-zA-Z0-9\-\_]{20}",
        "aws_access_key": r"AKIA[0-9A-Z]{16}",
        "aws_secret_key": r"[a-zA-Z0-9/+=]{40}",
        "google_api_key": r"AIza[0-9A-Za-z\-_]{35}",
        "slack_token": r"xox[baprs]-[0-9a-zA-Z\-]+",
        "stripe_key": r"(sk|pk)_(live|test)_[0-9a-zA-Z]{24,}",
        "npm_token": r"npm_[a-zA-Z0-9]{36}",
        
        # Generic patterns
        "api_key": r"['\"]?api[_-]?key['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-\_]{20,})['\"]?",
        "api_token": r"['\"]?api[_-]?token['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-\_]{20,})['\"]?",
        "auth_token": r"['\"]?auth[_-]?token['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-\_]{20,})['\"]?",
        "access_token": r"['\"]?access[_-]?token['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-\_]{20,})['\"]?",
        "private_key": r"['\"]?private[_-]?key['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-\_]{20,})['\"]?",
        "secret_key": r"['\"]?secret[_-]?key['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-\_]{20,})['\"]?",
        "password": r"['\"]?password['\"]?\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?",
        
        # Environment variable references that might contain secrets
        "env_secret": r"\$\{\{\s*secrets\.[A-Z_]+\s*\}\}",
        "env_var_secret": r"\$\{[A-Z_]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Z_]*\}",
        
        # Base64 encoded potential secrets (min 20 chars)
        "base64_secret": r"['\"]?[a-zA-Z0-9+/]{20,}={0,2}['\"]?",
        
        # SSH keys
        "ssh_private": r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
        "ssh_public": r"ssh-(?:rsa|dss|ed25519) [a-zA-Z0-9+/]+=*",
        
        # URLs with credentials
        "url_with_password": r"(?:https?|ftp)://[^:]+:([^@]+)@[^\s]+",
        
        # JWT tokens
        "jwt_token": r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
    }
    
    # Keywords that indicate a value might be sensitive
    SENSITIVE_KEYWORDS = {
        "password", "passwd", "pwd", "secret", "key", "token", "api",
        "apikey", "auth", "credential", "private", "priv", "certificate",
        "cert", "ssh", "gpg", "pgp", "rsa", "dsa", "ecdsa", "oauth",
        "jwt", "bearer", "basic", "digest", "hash", "salt", "sign",
        "signature", "encrypt", "decrypt", "cipher", "aws", "azure",
        "gcp", "google", "github", "gitlab", "bitbucket", "slack",
        "discord", "telegram", "stripe", "paypal", "twilio", "sendgrid",
        "mailgun", "database", "mongodb", "mysql", "postgres", "redis",
        "elasticsearch", "connection", "conn", "string", "uri", "url"
    }
    
    def __init__(self, custom_patterns: Dict[str, str] = None, additional_keywords: Set[str] = None):
        """
        Initialize the secrets redactor.
        
        Args:
            custom_patterns: Additional regex patterns to detect secrets
            additional_keywords: Additional keywords to consider sensitive
        """
        # Compile all patterns
        self.patterns: Dict[str, Pattern] = {}
        all_patterns = self.DEFAULT_PATTERNS.copy()
        
        if custom_patterns:
            all_patterns.update(custom_patterns)
        
        for name, pattern in all_patterns.items():
            try:
                self.patterns[name] = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                logger.error(f"Invalid regex pattern for {name}: {e}")
        
        # Combine keywords
        self.sensitive_keywords = self.SENSITIVE_KEYWORDS.copy()
        if additional_keywords:
            self.sensitive_keywords.update(additional_keywords)
        
        logger.debug(f"Initialized with {len(self.patterns)} patterns and {len(self.sensitive_keywords)} keywords")
    
    def redact_content(self, content: str, replacement: str = "[REDACTED]") -> Tuple[str, List[RedactedSecret]]:
        """
        Redact all detected secrets in the content.
        
        Args:
            content: The content to redact
            replacement: The replacement string for redacted values
            
        Returns:
            Tuple of (redacted_content, list_of_redacted_secrets)
        """
        logger.debug("Starting content redaction")
        
        redacted_secrets: List[RedactedSecret] = []
        redacted_content = content
        
        # Split content into lines for line number tracking
        lines = content.split('\n')
        
        # Apply each pattern
        for pattern_name, pattern in self.patterns.items():
            matches = list(pattern.finditer(content))
            
            for match in matches:
                # Get the matched value
                if match.groups():
                    # If pattern has groups, use the first group
                    secret_value = match.group(1)
                    start_pos = match.start(1)
                    end_pos = match.end(1)
                else:
                    # Otherwise use the whole match
                    secret_value = match.group(0)
                    start_pos = match.start()
                    end_pos = match.end()
                
                # Skip if too short or looks like a placeholder
                if len(secret_value) < 8 or self._is_placeholder(secret_value):
                    continue
                
                # Calculate line and column
                line_num, col_start, col_end = self._get_position_info(content, start_pos, end_pos)
                
                # Create redacted secret record
                redacted_secret = RedactedSecret(
                    pattern_name=pattern_name,
                    original_value=secret_value,
                    redacted_value=replacement,
                    line_number=line_num,
                    column_start=col_start,
                    column_end=col_end
                )
                redacted_secrets.append(redacted_secret)
                
                # Replace in content
                redacted_content = redacted_content.replace(secret_value, replacement)
                
                logger.info(f"🔒 Redacted {pattern_name} on line {line_num}")
        
        # Also check for sensitive key-value pairs
        redacted_content, additional_secrets = self._redact_sensitive_values(redacted_content, replacement)
        redacted_secrets.extend(additional_secrets)
        
        logger.info(f"✅ Redacted {len(redacted_secrets)} secrets")
        return redacted_content, redacted_secrets
    
    def _is_placeholder(self, value: str) -> bool:
        """
        Check if a value looks like a placeholder rather than a real secret.
        
        Args:
            value: The value to check
            
        Returns:
            True if it looks like a placeholder
        """
        placeholders = [
            "your", "example", "test", "demo", "sample", "placeholder",
            "changeme", "xxxxxx", "......", "******", "dummy", "fake",
            "<", ">", "{", "}", "[", "]", "$(", "${", "{{", "}}"
        ]
        
        value_lower = value.lower()
        return any(ph in value_lower for ph in placeholders)
    
    def _get_position_info(self, content: str, start_pos: int, end_pos: int) -> Tuple[int, int, int]:
        """
        Get line number and column positions for a match.
        
        Args:
            content: The full content
            start_pos: Start position of the match
            end_pos: End position of the match
            
        Returns:
            Tuple of (line_number, column_start, column_end)
        """
        lines = content[:start_pos].split('\n')
        line_number = len(lines)
        column_start = len(lines[-1]) + 1 if lines else 1
        
        # Calculate end column
        match_content = content[start_pos:end_pos]
        if '\n' in match_content:
            # Multi-line match
            column_end = len(match_content.split('\n')[-1])
        else:
            column_end = column_start + len(match_content)
        
        return line_number, column_start, column_end
    
    def _redact_sensitive_values(self, content: str, replacement: str) -> Tuple[str, List[RedactedSecret]]:
        """
        Redact values associated with sensitive keys.
        
        Args:
            content: The content to check
            replacement: The replacement string
            
        Returns:
            Tuple of (redacted_content, list_of_redacted_secrets)
        """
        redacted_secrets = []
        redacted_content = content
        
        # Pattern to find key-value pairs in YAML
        yaml_pattern = re.compile(
            rf"({'|'.join(self.sensitive_keywords)})['\"]?\s*:\s*['\"]?([^\s'\"]+)['\"]?",
            re.IGNORECASE | re.MULTILINE
        )
        
        for match in yaml_pattern.finditer(content):
            key = match.group(1)
            value = match.group(2)
            
            # Skip if value is too short or a placeholder
            if len(value) < 8 or self._is_placeholder(value) or value == replacement:
                continue
            
            # Skip if value is a variable reference
            if value.startswith('$') or value.startswith('{{'):
                continue
            
            line_num, col_start, col_end = self._get_position_info(
                content, match.start(2), match.end(2)
            )
            
            redacted_secret = RedactedSecret(
                pattern_name=f"sensitive_key_{key}",
                original_value=value,
                redacted_value=replacement,
                line_number=line_num,
                column_start=col_start,
                column_end=col_end
            )
            redacted_secrets.append(redacted_secret)
            
            redacted_content = redacted_content.replace(value, replacement)
            logger.debug(f"Redacted value for sensitive key '{key}' on line {line_num}")
        
        return redacted_content, redacted_secrets
    
    def get_summary(self, redacted_secrets: List[RedactedSecret]) -> str:
        """
        Generate a summary of redacted secrets.
        
        Args:
            redacted_secrets: List of redacted secrets
            
        Returns:
            Summary string
        """
        if not redacted_secrets:
            return "No secrets detected"
        
        # Group by pattern
        pattern_counts = {}
        for secret in redacted_secrets:
            pattern_counts[secret.pattern_name] = pattern_counts.get(secret.pattern_name, 0) + 1
        
        summary_lines = ["Redacted secrets summary:"]
        for pattern, count in sorted(pattern_counts.items()):
            summary_lines.append(f"  - {pattern}: {count} occurrence(s)")
        
        return "\n".join(summary_lines) 