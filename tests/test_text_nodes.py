from app.nodes.text import IsEgalText, AppendText


def test_is_egal_text():
    node = IsEgalText()
    assert node.process(a="hello", b="hello") == {"equal": True}
    assert node.process(a="hi", b="hello") == {"equal": False}


def test_append_text():
    node = AppendText()
    assert node.process(a="hello", b=" world") == {"text": "hello world"}
    assert node.process(a=None, b="foo") == {"text": "foo"}
