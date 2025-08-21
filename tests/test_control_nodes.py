from app.nodes.control import Branch


def test_branch_condition():
    node = Branch()
    assert node.on_exec(condition=None) == ([], {})
    assert node.on_exec(condition=True) == (["true"], {})
