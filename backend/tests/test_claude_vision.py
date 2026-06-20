"""Tests for the Claude vision detector with an injected fake client + sampler.

No API key, SDK, or ffmpeg required — the model call and frame sampling are
both stubbed so we exercise the detector's own logic (dedup, timestamping,
mapping of structured output to RawDetection).
"""
from app.vision.claude_vision import ClaudeVisionDetector, FrameSections, SectionReading
from app.vision.frames import Frame


class FakeMessages:
    def __init__(self, by_call):
        self._by_call = by_call
        self.calls = 0

    def parse(self, **kwargs):
        result = self._by_call[self.calls]
        self.calls += 1

        class _Resp:
            parsed_output = result

        return _Resp()


class FakeClient:
    def __init__(self, by_call):
        self.messages = FakeMessages(by_call)


def _frames(n):
    # One frame per simulated second.
    return [Frame(t_ms=i * 1000, jpeg=b"jpeg-%d" % i) for i in range(n)]


def test_maps_structured_output_to_section_detections():
    per_frame = [
        FrameSections(sections=[SectionReading(section="Dairy & Eggs", category="dairy", example_items=["milk", "eggs"], confidence=0.9)]),
        FrameSections(sections=[SectionReading(section="Frozen", category="frozen", example_items=["ice cream"], confidence=0.8)]),
    ]
    detector = ClaudeVisionDetector(
        client=FakeClient(per_frame),
        sampler=lambda video, dur: _frames(2),
    )
    dets = detector.detect(session_id="s", duration_ms=2000, video=b"video")
    assert [d.label for d in dets] == ["Dairy & Eggs", "Frozen"]
    assert dets[0].t_ms == 0 and dets[1].t_ms == 1000
    assert "milk" in dets[0].keywords
    assert dets[0].category == "dairy"


def test_dedupes_section_across_consecutive_frames():
    # Same section visible in three consecutive 1s-apart frames → one detection.
    dairy = FrameSections(sections=[SectionReading(section="Dairy & Eggs", confidence=0.9)])
    detector = ClaudeVisionDetector(
        client=FakeClient([dairy, dairy, dairy]),
        sampler=lambda video, dur: _frames(3),
    )
    dets = detector.detect(session_id="s", duration_ms=3000, video=b"video")
    assert len(dets) == 1
    assert dets[0].t_ms == 0  # kept the first sighting


def test_no_video_returns_no_detections():
    detector = ClaudeVisionDetector(client=FakeClient([]), sampler=lambda v, d: [])
    assert detector.detect(session_id="s", duration_ms=0, video=None) == []


def test_empty_frame_yields_nothing():
    detector = ClaudeVisionDetector(
        client=FakeClient([FrameSections(sections=[])]),
        sampler=lambda video, dur: _frames(1),
    )
    assert detector.detect(session_id="s", duration_ms=1000, video=b"v") == []
