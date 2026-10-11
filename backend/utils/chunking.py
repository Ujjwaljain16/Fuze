import re
from typing import List

TARGET_WORDS = 200
OVERLAP_WORDS = 40
MAX_CHUNKS = 40

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def chunk_text(title: str, text: str, target_words: int = TARGET_WORDS,
               overlap_words: int = OVERLAP_WORDS, max_chunks: int = MAX_CHUNKS) -> List[str]:
    """Split a document into overlapping ~target_words passages on sentence boundaries.

    Each passage is prefixed with the title so it stays meaningful on its own for
    both the embedding model and the reranker.
    """
    title = (title or "").strip()
    body = re.sub(r"[ \t]+", " ", (text or "")).strip()
    if not body:
        return [title] if title else []

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(body) if s and s.strip()]
    words_per_sentence = []
    for sentence in sentences:
        words = sentence.split()
        # break up run-on "sentences" (lists, code, markdown tables) so no chunk balloons
        for i in range(0, len(words), target_words):
            words_per_sentence.append(words[i:i + target_words])

    chunks: List[str] = []
    current: List[str] = []
    for words in words_per_sentence:
        if current and len(current) + len(words) > target_words:
            chunks.append(" ".join(current))
            if len(chunks) >= max_chunks:
                break
            current = current[-overlap_words:] if overlap_words else []
        current.extend(words)
    if current and len(chunks) < max_chunks:
        chunks.append(" ".join(current))

    prefix = f"{title}\n" if title else ""
    return [prefix + c for c in chunks]
