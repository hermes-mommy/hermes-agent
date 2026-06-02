# P7 Research: Clipboard Secret Scanning Patterns

**Source**: gitleaks, detect-secrets, trufflehog, protectai/llm-guard, huggingface/ml-intern
**Purpose**: P7-009 clipboard secret scanner regex patterns

## High-Confidence Patterns (always match)

```python
import re

# AWS Access Key ID
AWS_ACCESS_KEY = re.compile(r'(?<![A-Z0-9])(AKIA[0-9A-Z]{16})(?![A-Z0-9])')

# AWS Secret Access Key (40 chars, base64-ish)
AWS_SECRET_KEY = re.compile(r'(?i)aws[_\-]?secret[_\-]?(?:access)?[_\-]?key\s*[:=]\s*[\'"]?([A-Za-z0-9/+=]{40})[\'"]?')

# GitHub Personal Access Token
GITHUB_PAT = re.compile(r'(ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9]{22}_[A-Za-z0-9]{59})')

# GitHub OAuth
GITHUB_OAUTH = re.compile(r'gho_[A-Za-z0-9]{36}')

# Generic API Key (header/env pattern)
GENERIC_API_KEY = re.compile(r'(?i)(api[_\-]?key|apikey|api[_\-]?secret)\s*[:=]\s*[\'"]?([A-Za-z0-9_\-]{20,64})[\'"]?')

# Bearer Token
BEARER_TOKEN = re.compile(r'(?i)bearer\s+([A-Za-z0-9_\-\.]{20,512})')

# JWT Token
JWT_TOKEN = re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')

# Private Key (PEM)
PEM_KEY = re.compile(r'-----BEGIN\s+(RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----')

# Database Connection String
DB_CONN = re.compile(r'(postgresql|postgres|mysql|mongodb|redis)://[^\s\'"]+')

# Discord Bot Token
DISCORD_TOKEN = re.compile(r'[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27,}')

# Slack Token
SLACK_TOKEN = re.compile(r'xox[bpors]-[0-9]{10,13}-[0-9]{10,13}-[0-9]{10,13}-[a-f0-9]{32}')

# Stripe Key
STRIPE_KEY = re.compile(r'sk_(live|test)_[A-Za-z0-9]{24,}')

# Google API Key
GOOGLE_API_KEY = re.compile(r'AIza[0-9A-Za-z_-]{35}')

# SOPS/age Key
AGE_KEY = re.compile(r'AGE-SECRET-KEY-1[A-Z0-9]{58}')
```

## Medium-Confidence Patterns (entropy check)

```python
import math
from collections import Counter

def shannon_entropy(data: str) -> float:
    """Calculate Shannon entropy. ≥ 4.5 suggests high-entropy secret."""
    if not data:
        return 0.0
    counter = Counter(data)
    length = len(data)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in counter.values()
    )

# Generic high-entropy string (catches unknown secrets)
HIGH_ENTROPY = re.compile(r'(?<![A-Za-z0-9])[A-Za-z0-9_\-/+=]{32,}(?![A-Za-z0-9])')
```

## Password Patterns

```python
# Password in URL
PASSWORD_URL = re.compile(r'://[^:]+:([^\s@]+)@')

# Password assignment
PASSWORD_ASSIGN = re.compile(r'(?i)(password|passwd|pwd|pass)\s*[:=]\s*[\'"]([^\s\'"]{8,})[\'"]')
```

## Scanner Implementation Pattern

```python
from dataclasses import dataclass, field
from typing import Protocol

@dataclass(frozen=True)
class ScanResult:
    has_secret: bool
    secret_type: str | None = None
    redacted_content: str | None = None

class SecretScanner(Protocol):
    def scan(self, text: str) -> ScanResult: ...

@dataclass
class ClipboardSecretScanner:
    patterns: list[tuple[str, re.Pattern]] = field(default_factory=lambda: [
        ("aws_access_key", AWS_ACCESS_KEY),
        ("github_pat", GITHUB_PAT),
        ("jwt", JWT_TOKEN),
        ("pem_key", PEM_KEY),
        ("db_connection", DB_CONN),
        ("discord_token", DISCORD_TOKEN),
        ("password_url", PASSWORD_URL),
        ("age_key", AGE_KEY),
    ])
    entropy_threshold: float = 4.5

    def scan(self, text: str) -> ScanResult:
        for secret_type, pattern in self.patterns:
            if pattern.search(text):
                redacted = pattern.sub("[REDACTED]", text)
                return ScanResult(
                    has_secret=True,
                    secret_type=secret_type,
                    redacted_content=redacted,
                )
        # Entropy check for unknown secrets
        for match in HIGH_ENTROPY.finditer(text):
            if shannon_entropy(match.group()) >= self.entropy_threshold:
                redacted = HIGH_ENTROPY.sub("[REDACTED]", text)
                return ScanResult(
                    has_secret=True,
                    secret_type="high_entropy",
                    redacted_content=redacted,
                )
        return ScanResult(has_secret=False)
```

## Design Decision: Redact vs Drop

**Recommendation: REDACT** (replace with `[REDACTED]`)

- Dropping the entire event loses useful context (app name, timestamp, device)
- Redacting preserves the non-secret metadata while protecting the secret
- `extracted_facts` field stores the redacted version
- `raw_payload` stores encrypted original (LargeBinary, envelope AES-256-GCM)

## False Positive Reduction

1. **Whitelist**: Known safe patterns (base64 images, UUIDs, hashes)
2. **Context**: Only scan clipboard events, not app_usage or location
3. **Minimum length**: Require ≥ 20 chars for generic patterns
4. **Entropy floor**: ≥ 4.5 for unknown secret detection
5. **Exclusions**: Skip if content matches common non-secret patterns (URLs without auth, JSON structure chars)
