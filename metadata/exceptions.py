class MetadataError(Exception):
    """Base exception for metadata backend failures."""


class MetadataExtractionError(MetadataError):
    """Raised when metadata extraction fails."""


class NormalizationError(MetadataError):
    """Raised when datatype normalization fails."""


class MetadataProfilingError(MetadataError):
    """Raised when profiling a table or column fails."""