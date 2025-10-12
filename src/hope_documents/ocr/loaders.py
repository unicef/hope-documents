from abc import ABCMeta
from collections.abc import Generator
from typing import Any

import cv2
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from hope_documents.exceptions import InvalidImageError

mpl.use("agg")
loader_registry = []


class LoaderMetaClass(ABCMeta):
    def __new__(cls, class_name: str, bases: tuple[type], attrs: dict[str, Any]) -> type:
        new_class = super().__new__(cls, class_name, bases, attrs)
        loader_registry.append(new_class)
        return new_class


class Loader(metaclass=LoaderMetaClass):
    def __init__(self, max_size: tuple[int, int] | None = None, **kwargs: Any) -> None:  # noqa B027
        self._image: Image.Image | None = None
        self.max_size = max_size

    def get_image(self, filepath: str) -> Image.Image:
        try:
            self._image = Image.open(filepath)
            return self._image
        except UnidentifiedImageError as e:
            raise InvalidImageError(filepath) from e

    def load(self, filepath: str) -> Image.Image:
        try:
            image = self.get_image(filepath)
            self._image = self.process(image)
            return self._image
        except UnidentifiedImageError as e:
            raise InvalidImageError(filepath) from e

    def process(self, image: Image.Image) -> Image.Image:
        return image

    def rotate(self, filepath: str) -> Generator[tuple[Image.Image, int], None, None]:
        image = self.get_image(filepath)
        for angle in [0, 270, 180, 90]:
            if angle == 0:
                rotated_image = image
            else:
                rotated_image = image.rotate(angle, expand=True)
            self._image = self.process(rotated_image)
            yield self._image, angle


class PILLoader(Loader):
    def process(self, image: Image.Image) -> Image.Image:
        return ImageOps.grayscale(image)


class CV2Loader(Loader):
    def __init__(self, threshold: int = 128, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.threshold = threshold

    def process(self, image: Image.Image) -> Image.Image:
        gray_image = np.array(image.convert("L"))

        _, binary_image = cv2.threshold(gray_image, self.threshold, 255, cv2.THRESH_BINARY)
        return Image.fromarray(binary_image)


class SmartLoader(Loader):
    def __init__(self, block_size: int = 11, c: int = 2, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.block_size = block_size
        self.c = c

    def process(self, image: Image.Image) -> Image.Image:
        gray_image = np.array(image.convert("L"))
        binary_image = cv2.adaptiveThreshold(
            gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, self.block_size, self.c
        )
        return Image.fromarray(binary_image)


class BWLoader(Loader):
    def __init__(self, block_size: int = 11, c: int = 4, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.block_size = block_size
        self.c = c

    def process(self, image: Image.Image) -> Image.Image:
        gray_image = np.array(image.convert("L"))
        binary_image = cv2.adaptiveThreshold(
            gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, self.block_size, self.c
        )
        return Image.fromarray(binary_image)


class EnhancedLoader(Loader):
    """
    An enhanced loader that improves text readability using advanced image processing.

    This loader applies Gaussian blur for noise reduction and then uses Otsu's
    binarization to automatically find the optimal threshold for creating a
    clean black and white image.
    """

    def process(self, image: Image.Image) -> Image.Image:
        """Load and process an image to make text more readable."""
        rgb_image = np.array(image)
        gray = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2GRAY)
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
        return Image.fromarray(thresh)


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

    def process(self, image: Image.Image) -> Image.Image:
        """Load and process an image to make text more readable."""
        gray = np.array(image.convert("L"))

        # Upscale the image for better OCR results on small text
        if self.scale_factor > 1.0:
            width = int(gray.shape[1] * self.scale_factor)
            height = int(gray.shape[0] * self.scale_factor)
            gray = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)

        # Apply Gaussian blur to remove noise
        blurred = cv2.GaussianBlur(gray, (self.blur_kernel_size, self.blur_kernel_size), 0)

        # Apply Otsu's thresholding to automatically find the best threshold
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return Image.fromarray(thresh)
