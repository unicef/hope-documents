import base64

import numpy as np
from PIL import Image
from deskew import determine_skew
from django.core.files.uploadedfile import UploadedFile
from skimage.color import rgb2gray
from skimage.transform import rotate


def get_image_base64(image_file: UploadedFile) -> str:
    image_file.seek(0)
    image_data = image_file.read()
    base64_data = base64.b64encode(image_data)
    base64_string = base64_data.decode("utf-8")
    image_content_type = image_file.content_type
    return f"data:{image_content_type};base64,{base64_string}"


def get_deskewed_images(image_pil: Image.Image) -> tuple[Image.Image, float]:
    """Deskews an image and returns the deskewed image and the skew angle."""
    # Convert to RGB to handle 4-channel RGBA images (e.g., from PNGs)
    if image_pil.mode == "RGBA":
        image_pil = image_pil.convert("RGB")

    image_np = np.array(image_pil)

    # Convert to grayscale for skew detection
    grayscale = rgb2gray(image_np)

    # Determine the skew angle
    skew_angle = determine_skew(grayscale)

    # Rotate the original image to correct the skew
    rotated_np = rotate(image_np, skew_angle, resize=True)

    # Ensure the output is in the correct 8-bit format for PIL
    if rotated_np.dtype == np.float64:
        rotated_np = (rotated_np * 255).astype(np.uint8)

    deskewed_image_pil = Image.fromarray(rotated_np)

    return deskewed_image_pil, skew_angle
