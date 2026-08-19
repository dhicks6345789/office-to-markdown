# A stub for the Pillow (PIL) image-handling library, sufficient for running the transformer scripts
# in tests without requiring the real library (which is unavailable in some environments).
# Importing the submodule here means both "import PIL" and "import PIL.Image" expose the stubbed API.

from . import Image
from .Image import FakeImage, ImageOps, open, new
