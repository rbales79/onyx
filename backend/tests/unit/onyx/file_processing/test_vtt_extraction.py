"""A WebVTT transcript arriving as a FILE, rather than from the Teams or Zoom
connector, must reach the parser those connectors already use."""
import io

import pytest

from onyx.file_processing.extract_file_text import extract_file_text_locally
from onyx.file_processing.extract_file_text import vtt_to_text
from onyx.file_processing.file_types import OnyxFileExtensions
from onyx.file_processing.webvtt import parse_vtt_transcript

_ZOOM = (
    "WEBVTT\n\n"
    "1\n00:00:13.900 --> 00:00:14.960\nJane Doe: the renewal slips to Q3.\n\n"
    "2\n00:00:15.000 --> 00:00:17.100\nJohn Roe: agreed.\n"
)
_TEAMS = (
    "WEBVTT\n\n"
    "9c7a/1-0\n00:00:02.000 --> 00:00:04.500\n<v Jane Doe>the renewal slips.</v>\n"
)


def test_a_vtt_is_admitted_by_the_extension_gate() -> None:
    # connectors check this set before downloading anything
    assert ".vtt" in OnyxFileExtensions.ALL_ALLOWED_EXTENSIONS


def test_a_vtt_is_a_document_and_not_plain_text() -> None:
    # PLAIN_TEXT_EXTENSIONS short-circuits to the verbatim reader, which would
    # index cue numbers and timings as if they were speech
    assert ".vtt" in OnyxFileExtensions.DOCUMENT_EXTENSIONS
    assert ".vtt" not in OnyxFileExtensions.PLAIN_TEXT_EXTENSIONS


@pytest.mark.parametrize("vtt", [_ZOOM, _TEAMS], ids=["zoom", "teams"])
def test_timings_and_cue_identifiers_are_not_indexed(vtt: str) -> None:
    text = extract_file_text_locally(io.BytesIO(vtt.encode()), "meeting.vtt")
    assert "the renewal slips" in text
    assert "-->" not in text
    assert "00:00:" not in text


def test_extraction_matches_the_shared_parser() -> None:
    text = extract_file_text_locally(io.BytesIO(_ZOOM.encode()), "meeting.vtt")
    assert text == parse_vtt_transcript(_ZOOM, keep_speakers=True)


def test_the_teams_speaker_survives() -> None:
    # Zoom writes "Jane Doe: " into the cue text; Teams puts it in a voice span
    # that is dropped without keep_speakers. A file says which it is.
    assert vtt_to_text(io.BytesIO(_TEAMS.encode())).startswith("Jane Doe:")


def test_a_utf8_bom_does_not_become_content() -> None:
    text = vtt_to_text(io.BytesIO("﻿".encode() + _ZOOM.encode()))
    assert text.startswith("Jane Doe:")


def test_an_empty_transcript_is_empty_not_an_error() -> None:
    assert vtt_to_text(io.BytesIO(b"WEBVTT\n")) == ""
