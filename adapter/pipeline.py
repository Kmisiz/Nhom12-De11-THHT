
from dataclasses import dataclass
from copy import deepcopy
import uuid

from adapter.errors import AdapterError
from adapter.normalizer import normalize
from adapter.validator import validate
from adapter.enricher import enrich
from adapter.content_filter import filter_for_finance


@dataclass
class PipelineResult:
    """
    Luu ket qua xu ly cua Pipeline.
    """
    trace_id: str
    source_system: str | None
    stages: dict
    payload: dict | None
    error: AdapterError | None


def process(raw, catalog) -> PipelineResult:
    """
    Xu ly thong diep qua 4 buoc:

    1. Normalizer
    2. Validator
    3. Content Enricher
    4. Content Filter

    Neu gap AdapterError:
    - Luu loi vao result.error
    - Dat payload = None
    - Dung xu ly, khong raise loi ra ngoai.
    """

    # Khoi tao ket qua Pipeline
    result = PipelineResult(
        trace_id=uuid.uuid4().hex,
        source_system=None,
        stages={"input": raw},
        payload=None,
        error=None
    )

    try:
        # BUOC 1: NORMALIZER
        normalized = normalize(raw)

        # Neu da co message_id thi dung lam trace_id
        if normalized.get("message_id"):
            result.trace_id = normalized["message_id"]

        # Luu nguon gui
        result.source_system = normalized.get("source_system")

        # Luu ban sao du lieu sau Normalizer
        result.stages["normalized"] = deepcopy(normalized)

        # BUOC 2: VALIDATOR
        validated = validate(normalized)

        # BUOC 3: CONTENT ENRICHER
        enriched = enrich(validated, catalog)

        # Luu ban sao du lieu sau Enricher
        result.stages["enriched"] = deepcopy(enriched)

        # BUOC 4: CONTENT FILTER
        filtered = filter_for_finance(enriched)

        # Luu ban sao du lieu sau Content Filter
        result.stages["filtered"] = deepcopy(filtered)

        # Gan payload cuoi cung
        result.payload = deepcopy(filtered)

    except AdapterError as exc:
        # Bat loi tai bat ky buoc nao
        result.error = exc
        result.payload = None

    return result
