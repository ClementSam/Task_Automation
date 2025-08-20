from app.nodes.math import Add


def test_add_with_values():
    node = Add()
    assert node.process(a=2, b=3) == {"sum": 5}
    assert node.process(a=2, b=None) == {"sum": None}
