import base64
from io import BufferedReader, BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from hope_documents.exceptions import InvalidImageError


def get_image_base64(
    input_data: Path | Image.Image | BufferedReader,
    img_format: str = "PNG",
    quality: int = 85,
) -> str:
    _path_mime: str | None = None
    if isinstance(input_data, Path | str):
        path = Path(input_data)
        image_data = path.read_bytes()
        ext = path.suffix.lstrip(".").lower()
        _path_mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}" if ext else None
    elif isinstance(input_data, Image.Image):
        image_file = BytesIO()
        pil_fmt = img_format.upper()
        if pil_fmt in ("JPEG", "JPG", "WEBP"):
            input_data.convert("RGB").save(image_file, format=pil_fmt, quality=quality)
        else:
            input_data.save(image_file, format=pil_fmt)
        image_file.seek(0)
        image_data = image_file.read()
    elif isinstance(input_data, BytesIO) or hasattr(input_data, "read"):
        image_data = input_data.read()
    else:
        raise ValueError(f"Unsupported input type: {type(input_data)}")

    base64_data = base64.b64encode(image_data)
    base64_string = base64_data.decode("utf-8")
    mime = (
        _path_mime
        if _path_mime is not None
        else ("image/jpeg" if img_format.upper() in ("JPEG", "JPG") else f"image/{img_format.lower()}")
    )
    return f"data:{mime};base64,{base64_string}"


def get_image(filepath: str) -> Image.Image:
    try:
        return Image.open(filepath)
    except UnidentifiedImageError as e:
        raise InvalidImageError(filepath) from e
