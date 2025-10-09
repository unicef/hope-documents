from abc import ABC, ABCMeta, abstractmethod
from inspect import isabstract
from typing import Any

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from hope_documents.exceptions import InvalidImageError

loader_registry = []


class LoaderMetaClass(ABCMeta):
    def __new__(cls, class_name: str, bases: tuple[type], attrs: dict[str, Any]) -> type:
        new_class = super().__new__(cls, class_name, bases, attrs)
        if not isabstract(new_class):
            loader_registry.append(new_class)
        return new_class


class Loader(ABC, metaclass=LoaderMetaClass):
    def __init__(self, max_size: tuple[int, int] | None = None, **kwargs: Any) -> None:  # noqa B027
        self._image: Image.Image | None = None
        self.max_size = max_size

    @abstractmethod
    def load(self, filepath: str) -> Image.Image: ...


class PILLoader(Loader):
    def load(self, filepath: str) -> Image.Image:
        try:
            image = Image.open(filepath)
            ImageOps.exif_transpose(image, in_place=True)
            self._image = ImageOps.grayscale(image)
            return self._image
        except UnidentifiedImageError as e:
            raise InvalidImageError(filepath) from e


class CV2Loader(Loader):
    def __init__(self, threshold: int = 128, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.threshold = threshold

    def load(self, filepath: str) -> Image.Image:
        try:
            pil_image = Image.open(filepath)
            ImageOps.exif_transpose(pil_image, in_place=True)

            # Convert to grayscale numpy array
            gray_image = np.array(pil_image.convert("L"))

            _, binary_image = cv2.threshold(gray_image, self.threshold, 255, cv2.THRESH_BINARY)
            self._image = Image.fromarray(binary_image)
            return self._image
        except (UnidentifiedImageError, cv2.error) as e:
            raise InvalidImageError(filepath) from e


class SmartLoader(Loader):
    def __init__(self, block_size: int = 11, c: int = 2, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.block_size = block_size
        self.c = c

    def load(self, filepath: str) -> Image.Image:
        """Load an image, converts it to black and white with adaptive thresholding to improve contrast."""
        try:
            pil_image = Image.open(filepath)
            ImageOps.exif_transpose(pil_image, in_place=True)

            # Convert to grayscale numpy array for OpenCV processing
            gray_image = np.array(pil_image.convert("L"))

            # Apply adaptive thresholding
            binary_image = cv2.adaptiveThreshold(
                gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, self.block_size, self.c
            )
            self._image = Image.fromarray(binary_image)
            return self._image
        except (UnidentifiedImageError, cv2.error) as e:
            raise InvalidImageError(filepath) from e


class BWLoader(Loader):
    def __init__(self, block_size: int = 11, c: int = 4, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.block_size = block_size
        self.c = c

    def load(self, filepath: str) -> Image.Image:
        try:
            pil_image = Image.open(filepath)
            ImageOps.exif_transpose(pil_image, in_place=True)

            # Convert to grayscale numpy array for OpenCV processing
            gray_image = np.array(pil_image.convert("L"))

            # Apply adaptive thresholding to enhance black and white contrast
            binary_image = cv2.adaptiveThreshold(
                gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, self.block_size, self.c
            )
            self._image = Image.fromarray(binary_image)
            return self._image
        except (UnidentifiedImageError, cv2.error) as e:
            raise InvalidImageError(filepath) from e


class EnhancedLoader(Loader):
    """
    An enhanced loader that improves text readability using advanced image processing.

    This loader applies Gaussian blur for noise reduction and then uses Otsu's
    binarization to automatically find the optimal threshold for creating a
    clean black and white image.
    """

    def load(self, filepath: str) -> Image.Image:
        """Load and process an image to make text more readable."""
        try:
            image = cv2.imread(filepath)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # type: ignore[arg-type]
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


class ImprovedLoader(Loader):
    """
    An improved loader that enhances text readability using advanced image processing.

    This loader can upscale the image, applies Gaussian blur for noise reduction,
    and then uses Otsu's binarization to automatically find the optimal
    threshold for creating a clean black and white image.
    """

    def __init__(self, scale_factor: float = 1.5, blur_kernel_size: int = 5, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.scale_factor = scale_factor
        # Ensure blur kernel size is odd
        self.blur_kernel_size = blur_kernel_size if blur_kernel_size % 2 != 0 else blur_kernel_size + 1

    def load(self, filepath: str) -> Image.Image:
        """Load and process an image to make text more readable."""
        try:
            pil_image = Image.open(filepath)
            ImageOps.exif_transpose(pil_image, in_place=True)
            # Convert to grayscale numpy array
            gray = np.array(pil_image.convert("L"))

            # Upscale the image for better OCR results on small text
            if self.scale_factor > 1.0:
                width = int(gray.shape[1] * self.scale_factor)
                height = int(gray.shape[0] * self.scale_factor)
                gray = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)

            # Apply Gaussian blur to remove noise
            blurred = cv2.GaussianBlur(gray, (self.blur_kernel_size, self.blur_kernel_size), 0)

            # Apply Otsu's thresholding to automatically find the best threshold
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            self._image = Image.fromarray(thresh)
            return self._image
        except (UnidentifiedImageError, cv2.error) as e:
            raise InvalidImageError(filepath) from e
