import base64
from io import BufferedReader, BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from hope_documents.exceptions import InvalidImageError


def get_image_base64(input_data: Path | Image.Image | BufferedReader) -> str:
    if isinstance(input_data, Path | str):
        image_data = Path(input_data).read_bytes()
    elif isinstance(input_data, Image.Image):
        image_file = BytesIO()
        input_data.save(image_file, format="PNG")
        image_file.seek(0)
        image_data = image_file.read()
    elif isinstance(input_data, BytesIO):
        image_data = input_data
    elif hasattr(input_data, "read"):
        image_data = input_data.read()
    else:
        raise ValueError(f"Unsupported input type: {type(input_data)}")

    base64_data = base64.b64encode(image_data)
    base64_string = base64_data.decode("utf-8")
    image_content_type = "image/png"
    return f"data:{image_content_type};base64,{base64_string}"


def get_image(filepath: str) -> Image.Image:
    try:
        return Image.open(filepath)
    except UnidentifiedImageError as e:
        raise InvalidImageError(filepath) from e
