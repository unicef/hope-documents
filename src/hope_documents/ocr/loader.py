from abc import ABC, abstractmethod
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from hope_documents.exceptions import InvalidImageError


class Loader(ABC):
    def __init__(self, **kwargs: Any) -> None:  # noqa B027
        pass

    @abstractmethod
    def load(self, filepath: str) -> Image.Image: ...


class PILLoader(Loader):
    def load(self, filepath: str) -> Image.Image:
        try:
            image = Image.open(filepath)
            gray_image = ImageOps.grayscale(image)
            ImageOps.exif_transpose(gray_image, in_place=True)
            return gray_image
        except UnidentifiedImageError as e:
            raise InvalidImageError(filepath) from e


class CV2Loader(Loader):
    def __init__(self, threshold: int = 128, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.threshold = threshold

    def load(self, filepath: str) -> Image.Image:
        try:
            image = cv2.imread(filepath)
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, preprocessed_image = cv2.threshold(gray_image, self.threshold, 255, cv2.THRESH_BINARY)
            return preprocessed_image
        except cv2.error as e:
            raise InvalidImageError(filepath) from e


class SmartLoader(Loader):
    def __init__(self, block_size: int = 11, c: int = 4, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.block_size = block_size
        self.c = c

    def load(self, filepath: str) -> Image.Image:
        """Load an image, converts it to black and white with adaptive thresholding to improve contrast."""
        try:
            pil_image = Image.open(filepath)
            ImageOps.exif_transpose(pil_image, in_place=True)
            cv2_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            return cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
        except UnidentifiedImageError as e:
            raise InvalidImageError(filepath) from e


class BWLoader(Loader):
    def __init__(self, threshold: int = 120, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.threshold = threshold

    def load(self, filepath: str) -> Image.Image:
        try:
            pil_image = Image.open(filepath)
            ImageOps.exif_transpose(pil_image, in_place=True)

            # Convert to grayscale using PIL, which handles different modes.
            gray_pil_image = pil_image.convert("L")

            # Convert to numpy array for OpenCV processing
            gray_image = np.array(gray_pil_image)

            # Apply adaptive thresholding to enhance black and white contrast
            binary_image = cv2.adaptiveThreshold(
                gray_image, self.threshold, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 4
            )

            # Convert back to PIL Image
            return Image.fromarray(binary_image)
        except UnidentifiedImageError as e:
            raise InvalidImageError(filepath) from e
