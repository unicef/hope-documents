from abc import ABC, abstractmethod
from typing import Any

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from hope_documents.exceptions import InvalidImageError


class Loader(ABC):
    def __init__(self, **kwargs: Any) -> None:  # noqa B027
        self._image = None

    @abstractmethod
    def load(self, filepath: str) -> Image.Image: ...


class PILLoader(Loader):
    def load(self, filepath: str) -> Image.Image:
        try:
            image = Image.open(filepath)
            self._image = ImageOps.grayscale(image)
            ImageOps.exif_transpose(self._image, in_place=True)
            return self._image
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
            _, binary_image = cv2.threshold(gray_image, self.threshold, 255, cv2.THRESH_BINARY)
            self._image = Image.fromarray(binary_image)
            return self._image
        except cv2.error as e:
            raise InvalidImageError(filepath) from e


class SmartLoader(Loader):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def load(self, filepath: str) -> Image.Image:
        """Load an image, converts it to black and white with adaptive thresholding to improve contrast."""
        try:
            pil_image = Image.open(filepath)
            ImageOps.exif_transpose(pil_image, in_place=True)
            cv2_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            binary_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
            self._image = Image.fromarray(binary_image)
            return self._image
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
            self._image = Image.fromarray(binary_image)
            return self._image
        except UnidentifiedImageError as e:
            raise InvalidImageError(filepath) from e


class EnhancedLoader(Loader):
    """
    An enhanced loader that improves text readability using advanced image processing.

    This loader applies Gaussian blur for noise reduction and then uses Otsu's
    binarization to automatically find the optimal threshold for creating a
    clean black and white image.
    """

    def load(self, filepath: str) -> Image.Image:
        """Load and processes an image to make text more readable."""
        try:
            image = cv2.imread(filepath)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            plt.subplot(2, 3, 2)
            plt.axis("off")
            scale_factor = 2
            upscaled = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
            plt.subplot(2, 3, 3)
            plt.axis("off")
            blurred = cv2.GaussianBlur(upscaled, (5, 5), 0)
            plt.subplot(2, 3, 4)
            plt.axis("off")
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            plt.subplot(2, 3, 5)
            plt.axis("off")
            plt.tight_layout()
            self._image = Image.fromarray(thresh)
            return self._image
        except cv2.error as e:
            raise InvalidImageError(filepath) from e
