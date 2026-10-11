from utils.chunking import chunk_text


def test_short_text_is_one_chunk_with_title_prefix():
    chunks = chunk_text("Flask auth", "Use sessions. Hash passwords.")
    assert chunks == ["Flask auth\nUse sessions. Hash passwords."]


def test_long_text_is_split_with_overlap_and_covers_the_end():
    sentences = [f"Sentence number {i} talks about topic {i}." for i in range(300)]
    chunks = chunk_text("T", " ".join(sentences), target_words=100, overlap_words=20)
    assert len(chunks) > 5
    assert all(c.startswith("T\n") for c in chunks)
    assert all(len(c.split()) <= 100 + 20 + 1 for c in chunks)
    assert "topic 299" in chunks[-1]
    # consecutive chunks share overlapping words
    assert set(chunks[0].split()[-10:]) & set(chunks[1].split()[:30])


def test_runaway_sentence_is_broken_up_and_chunks_are_capped():
    blob = " ".join(["word"] * 5000)
    chunks = chunk_text("", blob, target_words=200, overlap_words=0, max_chunks=10)
    assert len(chunks) == 10
    assert all(len(c.split()) <= 200 for c in chunks)


def test_empty_body_falls_back_to_title():
    assert chunk_text("Only title", "") == ["Only title"]
    assert chunk_text("", "") == []
