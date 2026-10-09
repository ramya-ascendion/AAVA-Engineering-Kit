"""The markers `pytest.ini` registers, one per line.

pytest reads every line of `markers` as a marker of its own. A description
wrapped onto a second line registers that line as a marker too, and nothing
complains: `--strict-markers` is off, and a bogus marker is only seen in
`pytest --markers`. So this reads the list pytest itself registered.
"""

from __future__ import annotations


def test_every_registered_marker_is_a_name_and_a_description(pytestconfig):
    """A continuation line has no name before its colon, or has spaces in it.

    pytest takes a marker's name as the text before the first colon or
    parenthesis, so a line like "that only holds when nothing else loads the
    machine" is registered under a name no test could ever use.
    """
    lines = pytestconfig.getini("markers")

    not_markers = [
        line
        for line in lines
        if not line.split(":")[0].split("(")[0].isidentifier()
        or not line.partition(":")[2].strip()
    ]

    assert lines, "pytest registered no markers at all"
    assert not not_markers, not_markers
