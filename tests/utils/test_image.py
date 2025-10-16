import base64
from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile

from hope_documents.utils.image import get_image_base64


def test_get_image_base64_with_png():
    """Test with a different image content type (PNG)."""
    image_content = b"another-fake-image"
    image_file = InMemoryUploadedFile(
        file=BytesIO(image_content),
        field_name="image",
        name="test_image.png",
        content_type="image/png",
        size=len(image_content),
        charset=None,
    )

    base64_uri = get_image_base64(image_file)

    expected_prefix = "data:image/png;base64,"
    assert base64_uri.startswith(expected_prefix)
    encoded_content = base64_uri.split(",")[1]
    expected_encoded_content = base64.b64encode(image_content).decode("utf-8")
    assert encoded_content == expected_encoded_content
