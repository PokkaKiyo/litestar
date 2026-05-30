from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict

from litestar.exceptions import ImproperlyConfiguredException
from litestar.middleware.compression import CompressionMiddleware
from litestar.types.empty import Empty, EmptyType

if TYPE_CHECKING:
    from litestar.middleware.compression.facade import CompressionFacade

__all__ = (
    "BrotliCompressionSettings",
    "CompressionConfig",
    "CompressionSettings",
    "GzipCompressionSettings",
    "ZstdCompressionSettings",
)

CompressionBackends: TypeAlias = Literal["gzip", "brotli", "zstd"]


@dataclass
class CompressionSettings:
    minimum_size: int = field(default=500)
    """Minimum response size (bytes) to enable compression, affects all backends."""
    compression_facade: type[CompressionFacade] | EmptyType = Empty
    """TODO."""
    compress_sse: bool = True
    """TODO."""

    def __post_init__(self) -> None:
        if self.minimum_size <= 0:
            raise ImproperlyConfiguredException("minimum_size must be greater than 0")
        if self.compression_facade is Empty:
            raise ImproperlyConfiguredException("custom compression settings must set their own compression facade")


@dataclass
class GzipCompressionSettings(CompressionSettings):
    compress_level: int = field(default=9)
    """Range ``[0-9]``, see :doc:`python:library/gzip`."""

    def __post_init__(self) -> None:
        from litestar.middleware.compression.gzip_facade import GzipCompression

        if self.compress_level < 0 or self.compress_level > 9:
            raise ImproperlyConfiguredException("gzip compress_level must be a value between 0 and 9")

        self.compression_facade = GzipCompression
        super().__post_init__()


@dataclass
class BrotliCompressionSettings(CompressionSettings):
    quality: int = field(default=5)
    """Range ``[0-11]``, Controls the compression-speed vs compression-density tradeoff.

    The higher the quality, the slower the compression.
    """
    mode: Literal["generic", "text", "font"] = "text"
    """``MODE_GENERIC``, ``MODE_TEXT`` (for UTF-8 format text input, default) or ``MODE_FONT`` (for WOFF 2.0)."""
    lgwin: int = field(default=22)
    """Base 2 logarithm of size.

    Range is 10 to 24. Defaults to 22.
    """
    lgblock: Literal[0, 16, 17, 18, 19, 20, 21, 22, 23, 24] = 0
    """Base 2 logarithm of the maximum input block size.

    Range is ``16`` to ``24``. If set to ``0``, the value will be set based on the quality. Defaults to ``0``.
    """

    def __post_init__(self) -> None:
        from litestar.middleware.compression.brotli_facade import BrotliCompression

        if self.quality < 0 or self.quality > 11:
            raise ImproperlyConfiguredException("brotli quality must be a value between 0 and 11")

        if self.lgwin < 10 or self.lgwin > 24:
            raise ImproperlyConfiguredException("brotli lgwin must be a value between 10 and 24")

        self.compression_facade = BrotliCompression
        super().__post_init__()


@dataclass
class ZstdCompressionSettings(CompressionSettings):
    compress_level: int = field(default=0)
    """Integer greater than or equal to 0.
    A value of 0 indicates use of default compression level set by the library.
    """

    def __post_init__(self) -> None:
        from litestar.middleware.compression.zstd_facade import ZstdCompression

        upper_bound = ZstdCompression.upper_bound
        if not (0 <= self.compress_level <= upper_bound):
            raise ImproperlyConfiguredException(
                f"zstd_compress_level must be between 0 and {upper_bound}, given: {self.compress_level}"
            )

        self.compression_facade = ZstdCompression
        super().__post_init__()


class Backends(TypedDict, total=False):
    gzip: GzipCompressionSettings
    brotli: BrotliCompressionSettings
    zstd: ZstdCompressionSettings


@dataclass
class CompressionConfig:
    """Configuration for response compression.

    To enable response compression, pass an instance of this class to the :class:`Litestar <.app.Litestar>` constructor
    using the ``compression_config`` key.
    """

    backends: Backends = field(default_factory=Backends)
    """TODO."""
    builtin_backends: CompressionBackends | list[CompressionBackends] | None = "gzip"
    """TODO."""

    middleware_class: type[CompressionMiddleware] = CompressionMiddleware
    """Middleware class to use, should be a subclass of :class:`CompressionMiddleware`."""
    exclude: str | list[str] | None = None
    """A pattern or list of patterns to skip in the compression middleware."""
    exclude_opt_key: str | None = None
    """An identifier to use on routes to disable compression for a particular route."""

    def __post_init__(self) -> None:
        if self.builtin_backends is not None:
            if isinstance(self.builtin_backends, str):
                builtin_backends = {self.builtin_backends}
            else:
                builtin_backends = self.builtin_backends
            if "gzip" in builtin_backends and "gzip" not in self.backends:
                self.backends["gzip"] = GzipCompressionSettings()
            if "brotli" in builtin_backends and "brotli" not in self.backends:
                self.backends["brotli"] = BrotliCompressionSettings()
            if "zstd" in builtin_backends and "zstd" not in self.backends:
                self.backends["zstd"] = ZstdCompressionSettings()

        if not self.backends:
            raise ImproperlyConfiguredException("At least 1 compression backend must be configured")
