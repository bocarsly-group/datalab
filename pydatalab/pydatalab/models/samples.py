from typing import Dict, Optional

from pydantic import Field

from pydatalab.models.items import Item
from pydatalab.models.utils import JSON_ENCODERS, Mass


class Sample(Item):
    """A model for representing an experimental sample."""

    type: str = Field("samples", const="samples", pattern="^samples$")

    chemform: Optional[str] = Field(
        description="A string representation of the chemical formula associated with this sample."
    )

    synthesis_description: Optional[str] = Field(description="Details of the sample synthesis")

    synthesis_quantities: Optional[Dict[str, Mass]] = Field(
        description="The quantites of each constituent used in the synthesis, keyed by their item_id."
    )  # type: ignore

    synthesis_yield: Optional[Mass] = Field(
        description="The mass of the sample produced by the synthesis recipe with the given quantities."
    )  # type: ignore

    class Config:
        allow_arbitrary_types = True
        json_encoders = JSON_ENCODERS
