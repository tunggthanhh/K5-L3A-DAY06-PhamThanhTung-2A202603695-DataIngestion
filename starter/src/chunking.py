"""Implement fixed-size and structure-aware chunking."""
import re

from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Split one page into overlapping, word-aware character windows.

    ``size`` and ``overlap`` are measured in normalized text characters. The
    metadata offsets refer to ``page.text``, which makes each hit auditable.
    """
    if size <= 0:
        raise ValueError("size must be greater than zero")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be at least zero and smaller than size")

    text = page.text.strip()
    if not text:
        return []

    chunks: list[Chunk] = []
    start = 0
    chunk_index = 0
    while start < len(text):
        end = _word_boundary(text, start, min(start + size, len(text)))
        if end <= start:
            end = min(start + size, len(text))

        chunks.append(_make_chunk(
            page=page,
            strategy="fixed_size",
            chunk_index=chunk_index,
            text=text[start:end].strip(),
            char_start=start,
            char_end=end,
        ))
        if end == len(text):
            break
        start = end - overlap
        chunk_index += 1
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group whole paragraphs up to ``max_size`` and split only oversized ones."""
    if max_size <= 0:
        raise ValueError("max_size must be greater than zero")

    text = page.text.strip()
    if not text:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    chunks: list[Chunk] = []
    current: list[str] = []
    chunk_index = 0
    cursor = 0

    def flush() -> None:
        nonlocal current, chunk_index, cursor
        if not current:
            return
        chunk_text = "\n\n".join(current)
        start = text.find(chunk_text, cursor)
        if start < 0:
            start = cursor
        chunks.append(_make_chunk(
            page=page,
            strategy="paragraph",
            chunk_index=chunk_index,
            text=chunk_text,
            char_start=start,
            char_end=start + len(chunk_text),
        ))
        cursor = start + len(chunk_text)
        chunk_index += 1
        current = []

    for paragraph in paragraphs:
        # A paragraph larger than the limit is split at word boundaries, but it
        # is never mixed with adjacent paragraphs.
        if len(paragraph) > max_size:
            flush()
            start = 0
            while start < len(paragraph):
                end = _word_boundary(paragraph, start, min(start + max_size, len(paragraph)))
                if end <= start:
                    end = min(start + max_size, len(paragraph))
                piece = paragraph[start:end].strip()
                page_start = text.find(piece, cursor)
                if page_start < 0:
                    page_start = cursor
                chunks.append(_make_chunk(
                    page=page,
                    strategy="paragraph",
                    chunk_index=chunk_index,
                    text=piece,
                    char_start=page_start,
                    char_end=page_start + len(piece),
                ))
                cursor = page_start + len(piece)
                chunk_index += 1
                start = end
            continue

        proposed = "\n\n".join([*current, paragraph])
        if current and len(proposed) > max_size:
            flush()
        current.append(paragraph)
    flush()
    return chunks


def _word_boundary(text: str, start: int, end: int) -> int:
    """Return a whitespace boundary at or before ``end`` when possible."""
    if end >= len(text):
        return len(text)
    boundary = max(text.rfind(" ", start + 1, end + 1), text.rfind("\n", start + 1, end + 1))
    return boundary if boundary > start else end


def _make_chunk(
    page: DocumentPage,
    strategy: str,
    chunk_index: int,
    text: str,
    char_start: int,
    char_end: int,
) -> Chunk:
    """Build a stable chunk and copy page metadata without mutating it."""
    metadata = {
        **page.metadata,
        "chunking": strategy,
        "chunk_index": chunk_index,
        "char_start": char_start,
        "char_end": char_end,
    }
    return Chunk(
        chunk_id=f"{page.document_id}:p{page.page}:{strategy}:{chunk_index:04d}",
        document_id=page.document_id,
        source=page.source,
        page=page.page,
        text=text,
        metadata=metadata,
    )
