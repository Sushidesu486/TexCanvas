class BeamerPptxError(Exception):
    """Base exception for all public beamer-pptx failures."""


class InputError(BeamerPptxError):
    """The YAML file cannot be read or parsed."""


class ValidationError(BeamerPptxError):
    """The input data does not satisfy the deck schema."""


class AssetError(BeamerPptxError):
    """An image asset is missing, unsupported, or invalid."""


class RenderError(BeamerPptxError):
    """The presentation could not be rendered or saved."""

