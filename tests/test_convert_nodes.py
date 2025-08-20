from app.nodes.convert import IntToString


def test_int_to_string_none():
    node = IntToString()
    assert node.process(value=None) == {"text": None}
