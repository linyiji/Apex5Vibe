from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MODULES = [
    "invoice_integrity",
    "buyer_verification",
    "seller_verification",
    "relationship",
    "market_price",
    "payment_history",
    "duplicate_financing",
]
ModuleKey = Literal[
    "invoice_integrity",
    "buyer_verification",
    "seller_verification",
    "relationship",
    "market_price",
    "payment_history",
    "duplicate_financing",
]
NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Skip(StrictModel):
    mode: Literal["skip"]


class Existing(StrictModel):
    mode: Literal["existing"]
    entity_id: NonBlank


class Manual(StrictModel):
    mode: Literal["manual"]
    legal_name: NonBlank
    country: str | None = None
    tax_id: str | None = None


PartySelection = Annotated[Skip | Existing | Manual, Field(discriminator="mode")]


class CreateCase(StrictModel):
    buyer: PartySelection
    seller: PartySelection


class StartAssessment(StrictModel):
    expected_case_revision: int = Field(ge=1)


class PartyPatch(StartAssessment):
    side: Literal["buyer", "seller"]
    selection: PartySelection
    resolution_action: Literal["use_invoice_entity", "compare_selection"]
    reason: NonBlank


class Rerun(StrictModel):
    expected_module_version: int = Field(ge=1)
    reason: NonBlank


class Supplement(StrictModel):
    expected_module_version: int = Field(ge=1)
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
    rerun: bool = False


class Adjustment(StrictModel):
    expected_module_version: int = Field(ge=1)
    applies_to_run_id: NonBlank
    requested_adjustment: int = Field(ge=-100, le=100, strict=True)
    reason: NonBlank


class AIFinding(StrictModel):
    code: str
    statement: str
    source_ids: list[str]


class AIAnalysis(StrictModel):
    status: Literal["complete", "needs_info"]
    summary: NonBlank
    matched_rule_ids: list[str] = Field(max_length=1)
    findings: list[AIFinding]
    missing_inputs: list[str]


class ErrorDetail(StrictModel):
    code: str
    message: str
    retryable: bool = False
    details: dict = Field(default_factory=dict)


class ErrorBody(StrictModel):
    error: ErrorDetail
    request_id: str
