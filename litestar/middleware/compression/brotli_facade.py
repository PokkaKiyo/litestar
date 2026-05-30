from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from litestar.config.compression import BrotliCompressionSettings
from litestar.enums import CompressionEncoding
from litestar.exceptions import MissingDependencyException
from litestar.middleware.compression.facade import CompressionFacade

try:
    from brotli import MODE_FONT, MODE_GENERIC, MODE_TEXT, Compressor
except ImportError as e:
    raise MissingDependencyException("brotli") from e


if TYPE_CHECKING:
    from io import BytesIO

    from litestar.config.compression import CompressionConfig


class BrotliCompression(CompressionFacade):
    __slots__ = ("buffer", "compression_encoding", "compressor")

    encoding = CompressionEncoding.BROTLI

    def __init__(
        self,
        buffer: BytesIO,
        compression_encoding: Literal[CompressionEncoding.BROTLI] | str,
        config: CompressionConfig,
    ) -> None:
        self.buffer = buffer
        self.compression_encoding = compression_encoding
        modes: dict[Literal["generic", "text", "font"], int] = {
            "text": int(MODE_TEXT),
            "font": int(MODE_FONT),
            "generic": int(MODE_GENERIC),
        }
        settings = config.backends.get("brotli", BrotliCompressionSettings())
        self.compressor = Compressor(
            quality=settings.quality,
            mode=modes[settings.mode],
            lgwin=settings.lgwin,
            lgblock=settings.lgblock,
        )

    def write(self, body: bytes | bytearray, final: bool = False) -> None:
        self.buffer.write(self.compressor.process(body))
        self.buffer.write(self.compressor.flush())

    def close(self) -> None:
        self.buffer.write(self.compressor.finish())
