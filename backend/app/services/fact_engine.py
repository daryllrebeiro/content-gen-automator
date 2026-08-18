from app.domain.facts import FactClaim, FactStatus
from app.domain.project import Project


class FactPolicy:
    def __init__(self, *, allow_source_provided: bool = False) -> None:
        self.allow_source_provided = allow_source_provided


class FactEngine:
    """Conservative claim tracker used until an evidence provider verifies claims."""

    def __init__(self, policy: FactPolicy | None = None) -> None:
        self.policy = policy or FactPolicy()

    def ingest(self, project: Project) -> list[FactClaim]:
        claims: list[FactClaim] = []
        for index, raw_claim in enumerate(project.input.facts, start=1):
            text = " ".join(raw_claim.split()).strip()
            if not text:
                continue
            claims.append(
                FactClaim(
                    id=f"fact_{index:03d}",
                    text=text,
                    status=(
                        FactStatus.SOURCE_PROVIDED
                        if project.input.source_urls
                        else FactStatus.UNVERIFIED
                    ),
                    sources=project.input.source_urls.copy(),
                    notes=(
                        "A source was supplied but the claim still requires verification."
                        if project.input.source_urls
                        else "No evidence source was supplied."
                    ),
                )
            )
        project.facts = claims
        return claims

    def approved_facts(self, project: Project) -> list[str]:
        return [claim.text for claim in project.facts if claim.approved_for_narration]

