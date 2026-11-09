from hope_documents.archive.region import BoundingBox


class PromptBuilder:
    def __init__(self) -> None:
        self._sections: list[str] = []

    def with_role(self) -> "PromptBuilder":
        self._sections.append("You are extracting a single field value from an identity document image.")
        return self

    def with_field_hint(self, attribute_name: str) -> "PromptBuilder":
        self._sections.append(f"Extract the value of the field: {attribute_name}")
        return self

    def with_rules(self) -> "PromptBuilder":
        self._sections.append(
            "Return null and confidence=0 if the field is not visible or unreadable. "
            "Do not guess or hallucinate values."
        )
        return self

    def with_output_format(self) -> "PromptBuilder":
        self._sections.append(
            'Respond ONLY with valid JSON in this exact format, no other text:\n'
            '{"value": "<extracted text>", "confidence": <0.00 to 1.00>}'
        )
        return self

    def with_region_hint(self, region: BoundingBox, image_size: tuple[int, int]) -> "PromptBuilder":
        if region.width == 0 and region.height == 0:
            return self
        cx = (region.top_left.x + region.bottom_right.x) / 2
        cy = (region.top_left.y + region.bottom_right.y) / 2
        vert = "upper" if cy / image_size[1] < 0.5 else "lower"
        horiz = "left" if cx / image_size[0] < 0.5 else "right"
        self._sections.append(f"The field is typically in the {vert}-{horiz} area of the document.")
        return self

    def build(self) -> str:
        if not self._sections:
            raise ValueError("No sections have been added to the prompt.")
        return "\n\n".join(self._sections)
