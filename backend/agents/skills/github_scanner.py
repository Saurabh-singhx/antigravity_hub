import logging
from typing import Any, Dict, List, Optional
import requests

from agents.skills.safety_guard import SafetyGuardSkill
from config.settings import TRUSTED_CURATED_REPOS

logger = logging.getLogger("AntigravityHub.GitHubScanner")


class GitHubScannerSkill:
    """Skill to scan and discover verified, trending interview repositories for given tech stacks."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AntigravityHub-Agent/2.0 (Interview-Prep)",
            "Accept": "application/vnd.github.v3+json",
        })

    def find_repos_for_tech(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Returns vetted, reliable repositories matching the provided tech keywords.
        Prioritizes curated high-reputation repositories.
        """
        matched = []
        kw_lower = {k.lower() for k in keywords}

        for repo in TRUSTED_CURATED_REPOS:
            repo_tags = {t.lower() for t in repo.get("tags", [])}
            # Check for any keyword overlap
            overlap = kw_lower.intersection(repo_tags)
            is_general = "general" in repo_tags or "fullstack" in repo_tags
            if overlap or is_general:
                # Validate with safety guard
                is_safe, reason = SafetyGuardSkill.is_repo_reliable(repo["name"], repo.get("stars"))
                if is_safe:
                    matched.append({
                        **repo,
                        "matched_keywords": list(overlap) if overlap else ["general"],
                        "source_type": "github_repo",
                    })

        # Sort by star count descending
        matched.sort(key=lambda x: x.get("stars", 0), reverse=True)
        return matched

    def search_github_trending_topics(self, topic: str) -> List[Dict[str, Any]]:
        """Searches GitHub API for trending repositories with safety guard check."""
        try:
            url = f"https://api.github.com/search/repositories?q={topic}+interview+questions+stars:>500&sort=stars&order=desc&per_page=5"
            res = self.session.get(url, timeout=3.5)
            if res.status_code == 200:
                data = res.json()
                results = []
                for item in data.get("items", []):
                    repo_name = item.get("full_name")
                    stars = item.get("stargazers_count", 0)
                    is_safe, _ = SafetyGuardSkill.is_repo_reliable(repo_name, stars)
                    if is_safe:
                        results.append({
                            "name": repo_name,
                            "url": item.get("html_url"),
                            "raw_base": f"https://raw.githubusercontent.com/{repo_name}/master",
                            "stars": stars,
                            "tags": [topic, "trending"],
                            "source_type": "github_repo",
                        })
                return results
        except Exception as e:
            logger.debug(f"GitHub API search skipped (offline/rate-limit): {e}")

        return []
