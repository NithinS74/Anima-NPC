from npc.contracts.knowledge import Evidence
from npc.rag.dialogue import dialogue_reference


def row(text, id="00000001"):
    return f"FormID: {id}\tQuestTopic\tBranch\tTopic\tHELO\t0\t{text}\t\t "


def hit(text):
    return Evidence(id="revision:7", text=text, source="dialogue.txt", chunk_index=7, distance=0.2)


def test_mixed_speakers_and_incompatible_state_variants_leave_only_reference():
    source = hit("\n".join([
        "fragment of an earlier record",
        row("Taren is a fool. Our friendship ended years ago."),
        row("My Taren is the finest smith; that is a wife's boasting."),
        row("Taren is dead."),
        row("Taren works the northern forge.", "00000002"),
        "FormID: 00000003\tQuest\t\tTopic\tHELO\t0\tA truncated statement",
    ]))
    result = dialogue_reference(source)
    assert result is not None
    assert result.text == "Taren works the northern forge."
    assert result.record_ids == ("00000002:0",)
    assert result.id == source.id and result.source == source.source and result.chunk_index == 7
    assert result.source_kind == "dialogue"
    assert "friendship" not in result.text and "dead" not in result.text
    assert "Our friendship" in source.text  # Original corpus objects are untouched.


def test_personal_and_unresolved_runtime_claims_are_not_promoted_to_npc_context():
    lines = ["I'm his friend.", "He's my husband.", "We lost our son.", "You killed the king.",
             "The king died.", "The captain returned yesterday.", "Where is the forge?", "power attack grunt"]
    # A narration such as 'power attack grunt' has no speaker ownership markers;
    # this conservative reader is not a semantic relevance classifier.
    result = dialogue_reference(hit("\n".join(row(line) for line in lines[:-1])))
    assert result is None


def test_unrecognized_or_partial_records_fail_closed():
    for text in ["Plain text from an unrecognized export.", "FormID: bad\tQ\t\tT\tCUST\t0\tIncomplete", "fragment\tQ\tB\tT\tCUST\t0\tA claim\t"]:
        assert dialogue_reference(hit(text)) is None


def test_complete_final_sentence_survives_chunk_whitespace_trimming():
    source = hit(row("Taren works the northern forge.").rstrip())
    result = dialogue_reference(source)
    assert result is not None and "Taren works the northern forge." in result.text
    assert dialogue_reference(hit(row("Taren works the northern").rstrip())) is None
