class TexCanvasError(Exception):
    """Base exception for all public texcanvas failures."""


class InputError(TexCanvasError):
    """The YAML file cannot be read or parsed."""


class ValidationError(TexCanvasError):
    """The input data does not satisfy the deck schema."""


class AssetError(TexCanvasError):
    """An image asset is missing, unsupported, or invalid."""


class RenderError(TexCanvasError):
    """The presentation could not be rendered or saved."""
