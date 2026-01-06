"""Abstractions for the creation and stringification of XML objects."""

from __future__ import annotations

import textwrap

_Val = str | int | float

_HEADER = "<?xml version='1.0' encoding='utf-8'?>"


class Node:
    """An XML element."""

    name: str
    attributes: dict[str, _Val]

    # The content of an element is usually either text or more elements.
    text: str
    children: list[Node]

    def __init__(self, _name: str, _text: str = "", **attributes: _Val) -> None:
        """Initialise an element by name, optional text content and tag attributes
        set via kwargs.
        """
        self.name = _name
        self.attributes = attributes

        self.text = _text
        self.children = []

    def add_child(self, child: Node) -> None:
        """Add a child node to the current node."""
        self.children.append(child)

    def __str__(self) -> str:
        """String XML representation of the node."""
        attrs = " ".join((f'{name}="{val}"' for name, val in self.attributes.items()))
        tags = f"<{self.name} {attrs}"
        if self.text or self.children:
            tags += ">\n" + _str_internal(self.text, self.children) + f"</{self.name}>"
        else:
            tags += "/>"

        return tags

    def to_document(self) -> str:
        """Create an XML document by prefixing the stringified root element with
        a header.
        """
        return f"{_HEADER}\n{self}"


def _str_internal(text: str, children: list[Node]) -> str:
    """Create a string representation of the inside of a node."""
    if children:
        text += "\n".join(str(child) for child in children) + "\n"

    return textwrap.indent(text, "    ")
