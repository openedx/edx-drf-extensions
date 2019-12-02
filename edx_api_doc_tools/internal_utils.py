"""
Utility functions internal to this package.
"""
import textwrap


def dedent(text):
    """
    Dedent multi-line text nicely.

    An initial empty line is ignored so that triple-quoted strings don't need
    to start with a backslash.
    """
    if "\n" in text:
        first, rest = text.split("\n", 1)
        if not first.strip():
            # First line is blank, discard it.
            text = rest
    return textwrap.dedent(text)
