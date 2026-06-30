"""Repository sensor adapter (placeholder) for the Living Autonomy Kernel."""

from __future__ import annotations

from guinvere.life_kernel.sensor_adapters.base import BaseSensorAdapter


class RepoSensorAdapter(BaseSensorAdapter):
    """Placeholder adapter for git repository status polling.

    In future milestones this may report branches, open PRs, and recent
    commits. Real calls require local git access or GitHub API credentials;
    no external API is called in v1.
    """

    SENSOR_NAME = "repo"
    OBSERVATION_TYPE = "git"
    DEFAULT_CONTENT = (
        "Repository status polling placeholder — branches, PRs, and commits "
        "are not fetched in v1 (requires local git or GitHub API access)."
    )
