from unittest.mock import MagicMock

from PIL import Image as PILImage

from hope_documents.extractors import AttributeExtractor, ChainedAttributeExtractor


def _image() -> PILImage.Image:
    return PILImage.new("RGB", (10, 10))


def _extractor(return_value: str) -> MagicMock:
    m = MagicMock()
    m.extract_attribute.return_value = return_value
    return m


def test_chain_returns_first_nonempty():
    a, b = _extractor("ALICE"), _extractor("BOB")
    chain = ChainedAttributeExtractor([a, b])
    assert chain.extract_attribute(_image(), "first_name", None) == "ALICE"
    b.extract_attribute.assert_not_called()


def test_chain_falls_back_on_empty():
    a, b = _extractor(""), _extractor("FALLBACK")
    chain = ChainedAttributeExtractor([a, b])
    assert chain.extract_attribute(_image(), "first_name", None) == "FALLBACK"


def test_chain_returns_empty_when_all_fail():
    chain = ChainedAttributeExtractor([_extractor(""), _extractor("")])
    assert chain.extract_attribute(_image(), "first_name", None) == ""


def test_chain_satisfies_protocol():
    chain = ChainedAttributeExtractor([_extractor("x")])
    assert isinstance(chain, AttributeExtractor)
