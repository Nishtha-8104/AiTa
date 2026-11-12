from app.features.chat.logic.rag.chunker import Block, Section, chunk, count_tokens, prefix


def _words(tag: str, n: int) -> str:
    return " ".join(f"{tag}{i}" for i in range(n))


def test_code_stays_whole_sections_never_mix_and_positions_run_in_order():
    # Pinned tokenizer: whitespace words x 1.3, rounded up.
    assert count_tokens("a b c d e f g h i j") == 13

    code = "\n".join(f"int v{i} = {i};" for i in range(150))
    sections = [
        Section("Ch1", "Arrays", [Block("text", _words("a", 500)), Block("code", code),
                                  Block("text", _words("b", 200))]),
        Section("Ch1", "Strings", [Block("text", _words("s", 50))]),
    ]

    chunks = chunk(sections)

    assert [c.position for c in chunks] == list(range(len(chunks)))
    assert all(c.text.startswith(prefix(c.chapter, c.section)) for c in chunks)
    holding_code = [c for c in chunks if "int v0 = 0;" in c.text]
    assert len(holding_code) == 1
    assert holding_code[0].text == prefix("Ch1", "Arrays") + code
    for c in chunks:
        body = c.text.split("\n", 1)[1]
        if c.section == "Strings":
            assert "a0" not in body and "s0" in body
        else:
            assert "s0" not in body.split()


def test_consecutive_chunks_share_about_sixty_tokens():
    sections = [Section("Ch", "Sec", [Block("text", _words("w", 1000))])]

    chunks = chunk(sections, target_tokens=400, overlap_tokens=60)

    assert len(chunks) >= 3
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        prev_words = prev.text.split("\n", 1)[1].split()
        next_words = nxt.text.split("\n", 1)[1].split()
        shared = 0
        while shared < len(next_words) and next_words[shared] in prev_words:
            shared += 1
        assert next_words[:shared] == prev_words[-shared:]
        assert 55 <= count_tokens(" ".join(next_words[:shared])) <= 65
