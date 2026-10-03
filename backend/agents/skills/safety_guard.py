import logging
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from config.settings import (
    ALLOWED_FILE_EXTENSIONS,
    BLOCKED_EXTENSIONS,
    MIN_REPO_STARS,
    TRUSTED_CURATED_REPOS,
)

logger = logging.getLogger("AntigravityHub.SafetyGuard")


class SafetyGuardSkill:
    """
    Skill for vetting repository safety, eliminating shady sources,
    and ensuring no malicious scripts or executables are ever retrieved.
    """

    TRUSTED_DOMAINS = {
        "github.com",
        "raw.githubusercontent.com",
        "api.github.com",
        "leetcode.com",
        "reddit.com",
    }

    SUSPICIOUS_PATTERNS = [
        r"(?i)\.sh$",
        r"(?i)\.exe$",
        r"(?i)\.py$",
        r"(?i)\.js$",
        r"(?i)\.bin$",
        r"(?i)\.apk$",
        r"(?i)crack",
        r"(?i)keygen",
        r"(?i)payload",
        r"(?i)exploit",
        r"(?i)ransomware",
    ]

    @classmethod
    def is_url_safe(cls, url: str) -> Tuple[bool, str]:
        """Validates that a URL points to an approved domain and is not suspicious."""
        if not url:
            return False, "Empty URL"

        try:
            parsed = urlparse(url)
            domain = (parsed.netloc or "").lower().split(":")[0]

            # Domain check
            if not any(domain == td or domain.endswith("." + td) for td in cls.TRUSTED_DOMAINS):
                return False, f"Domain '{domain}' is not in trusted whitelist"

            # Suspicious URL path check
            path = parsed.path.lower()
            for pattern in cls.SUSPICIOUS_PATTERNS:
                if re.search(pattern, path):
                    return False, f"URL path matches suspicious pattern '{pattern}'"

            return True, "Safe"
        except Exception as e:
            return False, f"URL parse error: {e}"

    @classmethod
    def is_repo_reliable(cls, repo_name: str, stars: Optional[int] = None) -> Tuple[bool, str]:
        """
        Validates whether a GitHub repository is trustworthy.
        Exempts explicitly curated top-tier repos, and checks star threshold for others.
        """
        repo_lower = repo_name.strip().lower()

        # Check explicitly curated list
        for trusted in TRUSTED_CURATED_REPOS:
            if trusted["name"].lower() == repo_lower:
                return True, "Explicitly trusted repository"

        # Check star threshold
        if stars is not None and stars >= MIN_REPO_STARS:
            return True, f"Meets reliability threshold ({stars} stars >= {MIN_REPO_STARS})"

        if stars is not None:
            return False, f"Low reputation ({stars} stars < {MIN_REPO_STARS})"

        return False, "Unverified repository with unknown star count"

    @classmethod
    def is_file_safe_to_read(cls, filename: str) -> bool:
        """Only markdown, txt, and json documentation are permitted. Code files blocked."""
        lower = filename.lower()
        ext = "." + lower.split(".")[-1] if "." in lower else ""
        if ext in BLOCKED_EXTENSIONS:
            logger.warning(f"Blocked unsafe file extension: {filename}")
            return False
        return ext in ALLOWED_FILE_EXTENSIONS
