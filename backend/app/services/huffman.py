"""Huffman coding — DAA Unit IV (Greedy algorithms).

Each document chunk is compressed with its own Huffman tree. The codebook and
the packed bit-stream are stored alongside the plaintext chunk in the
`document_chunks` table. Decompression happens at query time for RAG.

Design notes:
- Per-chunk trees (not per-document) so we can retrieve and decompress individual
  chunks without touching the others — important for RAG similarity search.
- The bit stream is padded to a byte boundary; the first byte records how many
  padding bits were added, so decoding knows where to stop.
- For very short inputs (< 2 unique characters), we fall back to storing the
  plaintext uncompressed. Huffman needs at least 2 distinct symbols.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Iterable


# ═══════════════════════════════════════════════════════════════
# Tree nodes
# ═══════════════════════════════════════════════════════════════

@dataclass(order=True)
class _Node:
    """A node in the Huffman tree. `sort_index` makes heapq comparisons stable
    when two nodes have equal frequency."""

    freq: int
    sort_index: int
    char: str | None = field(compare=False, default=None)
    left: "_Node | None" = field(compare=False, default=None)
    right: "_Node | None" = field(compare=False, default=None)

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


# ═══════════════════════════════════════════════════════════════
# Frequency counting + tree construction
# ═══════════════════════════════════════════════════════════════

def _count_frequencies(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    return counts


def _build_tree(frequencies: dict[str, int]) -> _Node | None:
    """Build a Huffman tree from character frequencies.

    Returns None if `frequencies` is empty.
    Returns a single leaf if there's only 1 unique char — callers must handle
    this edge case (the leaf has no path, so we can't generate a code).
    """
    if not frequencies:
        return None

    heap: list[_Node] = []
    counter = 0
    for ch, freq in frequencies.items():
        heapq.heappush(heap, _Node(freq=freq, sort_index=counter, char=ch))
        counter += 1

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = _Node(
            freq=left.freq + right.freq,
            sort_index=counter,
            left=left,
            right=right,
        )
        counter += 1
        heapq.heappush(heap, merged)

    return heap[0]


def _build_codebook(root: _Node | None) -> dict[str, str]:
    """Walk the tree and return {char: "010..."} mapping."""
    if root is None:
        return {}

    codebook: dict[str, str] = {}

    # Special case: only one unique character — assign it a single-bit code.
    if root.is_leaf and root.char is not None:
        codebook[root.char] = "0"
        return codebook

    def _walk(node: _Node, path: str) -> None:
        if node.is_leaf and node.char is not None:
            codebook[node.char] = path
            return
        if node.left is not None:
            _walk(node.left, path + "0")
        if node.right is not None:
            _walk(node.right, path + "1")

    _walk(root, "")
    return codebook


# ═══════════════════════════════════════════════════════════════
# Encode / decode
# ═══════════════════════════════════════════════════════════════

@dataclass
class HuffmanResult:
    """Output of encoding a piece of text."""

    compressed: bytes
    codebook: dict[str, str]
    original_size_bytes: int
    compressed_size_bytes: int
    savings_percent: float  # percent of bytes saved vs. UTF-8 original


def encode(text: str) -> HuffmanResult:
    """Huffman-encode a string.

    The compressed bytes layout is:
        byte 0:  number of padding bits (0-7) added to the final byte
        byte 1+: packed bit stream, MSB-first

    If the text is empty or has only 1 unique character (pathological for
    Huffman), we still return a valid result — the codebook covers the single
    symbol and the encoded bytes just repeat that symbol's "0" bit.
    """
    original_bytes = text.encode("utf-8")
    original_size = len(original_bytes)

    if not text:
        return HuffmanResult(
            compressed=b"\x00",  # zero padding bits, no data
            codebook={},
            original_size_bytes=0,
            compressed_size_bytes=1,
            savings_percent=0.0,
        )

    frequencies = _count_frequencies(text)
    root = _build_tree(frequencies)
    codebook = _build_codebook(root)

    # Build the bit string
    bit_string = "".join(codebook[ch] for ch in text)

    # Pad to a byte boundary
    padding_bits = (8 - len(bit_string) % 8) % 8
    bit_string_padded = bit_string + ("0" * padding_bits)

    # Pack into bytes, MSB-first
    data = bytearray()
    data.append(padding_bits)  # header byte
    for i in range(0, len(bit_string_padded), 8):
        byte = int(bit_string_padded[i : i + 8], 2)
        data.append(byte)

    compressed = bytes(data)
    savings = 0.0
    if original_size > 0:
        savings = round((1 - len(compressed) / original_size) * 100, 2)

    return HuffmanResult(
        compressed=compressed,
        codebook=codebook,
        original_size_bytes=original_size,
        compressed_size_bytes=len(compressed),
        savings_percent=savings,
    )


def decode(compressed: bytes, codebook: dict[str, str]) -> str:
    """Decode Huffman-compressed bytes back into the original text.

    Uses a reversed codebook (code -> char) and walks the bit stream.
    """
    if not compressed or not codebook:
        return ""

    # First byte is the padding count
    padding_bits = compressed[0]
    data = compressed[1:]

    # Turn the packed bytes back into a bit string, trimming padding
    bit_string_parts: list[str] = []
    for byte in data:
        bit_string_parts.append(bin(byte)[2:].rjust(8, "0"))
    bit_string = "".join(bit_string_parts)
    if padding_bits:
        bit_string = bit_string[:-padding_bits]

    # Special case: single-symbol codebook — the code is "0" and we need to
    # know how many times the symbol appeared. We can recover this from the
    # length of the bit stream (each symbol takes 1 bit).
    if len(codebook) == 1:
        only_char = next(iter(codebook.keys()))
        return only_char * len(bit_string)

    # Reverse codebook for lookup
    reverse: dict[str, str] = {code: ch for ch, code in codebook.items()}

    # Walk the bit stream matching against the reverse codebook
    result: list[str] = []
    buffer: list[str] = []
    for bit in bit_string:
        buffer.append(bit)
        code = "".join(buffer)
        if code in reverse:
            result.append(reverse[code])
            buffer.clear()

    return "".join(result)


# ═══════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════

def total_savings(chunks: Iterable[HuffmanResult]) -> tuple[int, int, float]:
    """Aggregate compression stats across many chunks.

    Returns (total_original_bytes, total_compressed_bytes, savings_percent).
    """
    original = sum(c.original_size_bytes for c in chunks)
    compressed = sum(c.compressed_size_bytes for c in chunks)
    if original == 0:
        return 0, compressed, 0.0
    savings = round((1 - compressed / original) * 100, 2)
    return original, compressed, savings
