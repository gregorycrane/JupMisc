#!/usr/bin/env python3
"""
Extract lowest-level text chunks (chapter.section) from a Perseus/CTS TEI XML file.

Usage:
    python extract_sections.py <input.xml>

Output: one line per chunk in the form  chapter.section <TAB> text
"""

import sys
import re
from lxml import etree

NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def inner_text(el: etree._Element) -> str:
    """Return all text content under an element, stripped and normalised."""
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def extract_sections(path: str):
    tree = etree.parse(path)

    # Every <div type="textpart"> that has NO child <div type="textpart">
    # is a leaf chunk — the lowest level of the citation hierarchy.
    all_parts = tree.xpath(
        '//tei:div[@type="textpart"]'
        '[not(tei:div[@type="textpart"])]',
        namespaces=NS,
    )

    for div in all_parts:
        # Walk up to collect the full reference path (e.g. "1.2")
        labels = []
        node = div
        while node is not None:
            if node.tag == f"{{{NS['tei']}}}div" and node.get("type") == "textpart":
                labels.append(node.get("n", "?"))
            node = node.getparent()
        ref = ".".join(reversed(labels))

        text = inner_text(div)
        print(f"{ref}\t{text}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <tei_xml_file>", file=sys.stderr)
        sys.exit(1)
    extract_sections(sys.argv[1])