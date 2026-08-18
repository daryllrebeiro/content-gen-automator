from app.domain.facts import FactClaim, FactStatus
from app.domain.project import Project
from app.providers.fact_checker import FactChecker


class FactPolicy:
    def __init__(self, *, allow_source_provided: bool = False) -> None:
        self.allow_source_provided = allow_source_provided


class FactEngine:
    """Conservative claim tracker used until an evidence provider verifies claims."""

    def __init__(self, policy: FactPolicy | None = None, checker: FactChecker | None = None) -> None:
        self.policy = policy or FactPolicy()
        self.checker = checker

    def ingest(self, project: Project) -> list[FactClaim]:
        claims: list[FactClaim] = []
        for index, raw_claim in enumerate(project.input.facts, start=1):
            text = " ".join(raw_claim.split()).strip()
            if not text:
                continue
            claim = FactClaim(
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
            if self.checker is not None:
                try:
                    claim = self.checker.verify_claim(claim, project.input.source_urls)
                except Exception as exc:
                    # Evidence failure must not turn into an unsupported factual claim.
                    claim.status = FactStatus.UNCERTAIN
                    claim.notes = f"Evidence check unavailable: {exc}"
            claims.append(claim)
        project.facts = claims
        return claims

    def approved_facts(self, project: Project) -> list[str]:
        return [claim.text for claim in project.facts if claim.approved_for_narration]
