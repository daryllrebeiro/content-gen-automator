from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class GovernancePolicyPack(BaseModel):
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    max_risk_score_allowed: float = 0.15
    allow_mild_action: bool = True
    enforce_pii_redaction: bool = True
    copyright_strictness: str = "strict" # "strict", "moderate", "permissive"
    is_default: bool = False

class PolicyPackService:
    """
    Manages configurable enterprise compliance policy packs for IBM watsonx.governance.
    """
    def __init__(self):
        self._packs: Dict[str, GovernancePolicyPack] = {
            "general_audience": GovernancePolicyPack(
                id="general_audience",
                name="General Audience (YouTube Shorts Standard)",
                description="Universal safe harbor standard. Zero tolerance for hate/violence, strict copyright protection.",
                max_risk_score_allowed=0.15,
                allow_mild_action=True,
                is_default=True
            ),
            "kids_family": GovernancePolicyPack(
                id="kids_family",
                name="Kids & Family (COPPA / Strict Safety)",
                description="Ultra-strict child safety guidelines. 0% tolerance for fear, intense lighting shifts, or unverified claims.",
                max_risk_score_allowed=0.05,
                allow_mild_action=False,
                copyright_strictness="strict"
            ),
            "mature_documentary": GovernancePolicyPack(
                id="mature_documentary",
                name="Mature & Historical Documentary",
                description="Permits historical conflict terminology and dramatic cinematic tension with clear educational context.",
                max_risk_score_allowed=0.35,
                allow_mild_action=True,
                copyright_strictness="moderate"
            )
        }

    def list_policy_packs(self) -> List[GovernancePolicyPack]:
        return list(self._packs.values())

    def get_policy_pack(self, pack_id: str) -> Optional[GovernancePolicyPack]:
        return self._packs.get(pack_id, self._packs["general_audience"])

    def create_policy_pack(self, pack: GovernancePolicyPack) -> GovernancePolicyPack:
        self._packs[pack.id] = pack
        return pack


policy_pack_service = PolicyPackService()
