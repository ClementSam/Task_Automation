from app.nodes.serial import IsValid


def test_isvalid_node_valid_and_invalid():
    node = IsValid()
    outs, data = node.on_exec(handle=object())
    assert outs == ["valid"]
    assert data == {}
    outs, data = node.on_exec(handle=None)
    assert outs == ["invalid"]
    assert data == {}
