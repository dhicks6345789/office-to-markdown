# A minimal stub of the Pillow (PIL) image-handling library, providing just enough of the API surface
# used by the transformer scripts for tests to run without the real library being installed.

class FakeImage:
    """A stand-in for a PIL.Image object. Carries a size and mode, and records any saves performed."""

    def __init__(self, size=(100, 100), mode="RGBA"):
        self.size = size
        self.mode = mode
        self.savedTo = []

    def paste(self, *args, **kwargs):
        return None

    def convert(self, *args, **kwargs):
        return FakeImage(self.size, "RGB")

    def save(self, filename, *args, **kwargs):
        self.savedTo.append(str(filename))
        import builtins
        with builtins.open(str(filename), "wb"):
            pass


class ImageOps:
    @staticmethod
    def contain(theImage, theSize):
        return theImage


def open(theFilename, *args, **kwargs):
    return FakeImage()


def new(theMode, theSize, theColour):
    return FakeImage(theSize, theMode)
