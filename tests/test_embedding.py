from app.rag.embedding import chunk_text


def test_chunk_text_basic():
    text = "a" * 1000

    chunks = chunk_text(
        text,
        chunk_size=500,
        overlap=50
    )

    assert len(chunks) > 1


def test_chunk_text_empty():
    chunks = chunk_text("")

    assert chunks == []


def test_chunk_text_chunk_size():
    text = "a" * 1200

    chunks = chunk_text(
        text,
        chunk_size=500,
        overlap=50
    )

    for chunk in chunks:
        assert len(chunk["text"]) <= 500


def test_chunk_text_has_chunk_ids():
    text = "hello world " * 100

    chunks = chunk_text(text)

    for chunk in chunks:
        assert "chunk_id" in chunk


def test_chunk_overlap():
    text = "abcdefghij" * 100

    chunks = chunk_text(
        text,
        chunk_size=100,
        overlap=20
    )

    if len(chunks) >= 2:
        first_chunk = chunks[0]["text"]
        second_chunk = chunks[1]["text"]

        overlap_text = first_chunk[-20:]

        assert overlap_text in second_chunk