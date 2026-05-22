"""
Perseus URN Library — Twining Addition
=======================================
Drop this into the notebook BEFORE the processing loop (the 
"for work_key, work_meta in WORK_REGISTRY.items():" block).

It adds:
  1. A milestone-aware parser for editions whose Kassel chapter/subchapter
     alignment is carried by <milestone> elements rather than div hierarchy.
  2. The Twining 1789 entry in WORK_REGISTRY["aristotle_poetics"]["editions"].
  3. A small patch to the processing loop so it calls the milestone parser
     for any edition flagged with "parse_mode": "milestones".
"""

# ── (1) Milestone-Based Parser ─────────────────────────────────
# For translations like Twining whose own div structure (Part/Section)
# doesn't match the canonical chapter/subchapter scheme.  The Kassel
# alignment is encoded as milestones: <milestone unit="6.9"/>
# This parser walks the body flat, collecting text between milestones,
# and emits the same {book: {chapter: {section: html}}} dict as
# parse_hierarchical_tei.

import re

def parse_milestone_aligned_tei(path):
    """Parse a TEI file whose Kassel chapter.subchapter citations are
    encoded as milestones rather than as the div hierarchy.
    
    Returns an OrderedDict identical in shape to parse_hierarchical_tei:
      { '1': { '<chapter>': { '<subchapter>': '<html text>' } } }
    """
    if not os.path.exists(path):
        return None
    tree = ET.parse(path)
    root = tree.getroot()
    body = root.find('.//tei:body', NS) or root.find('.//body')
    if body is None:
        return None

    TEI = '{http://www.tei-c.org/ns/1.0}'
    data = OrderedDict()
    current_ref = None   # e.g. "6.9"
    current_text = []

    def _flush():
        nonlocal current_ref, current_text
        if current_ref and current_text:
            ch, sec = current_ref.split('.', 1)
            bk = '1'  # Poetics is a single-book work
            data.setdefault(bk, OrderedDict()).setdefault(ch, OrderedDict())
            text = ' '.join(t.strip() for t in current_text if t.strip())
            if text:
                data[bk][ch][sec] = text
        current_text = []

    def _walk(elem):
        nonlocal current_ref, current_text
        tag = elem.tag.replace(TEI, '')

        # ── Milestone: flush previous span, start new one ──
        if tag == 'milestone':
            unit_val = elem.get('unit', '')
            if re.match(r'\d+\.\d+', unit_val):
                _flush()
                current_ref = unit_val
            if elem.tail and elem.tail.strip():
                current_text.append(elem.tail)
            return

        # ── Footnotes ──
        if tag == 'note':
            note_html = extract_text_recursive(elem).strip()
            if note_html:
                current_text.append(f'<span class="note">[{note_html}]</span>')
            if elem.tail and elem.tail.strip():
                current_text.append(elem.tail)
            return

        # ── Page breaks — keep tail text only ──
        if tag == 'pb':
            if elem.tail and elem.tail.strip():
                current_text.append(elem.tail)
            return

        # ── Twining's section headings (I., II., …) — skip ──
        if tag == 'head':
            if elem.tail and elem.tail.strip():
                current_text.append(elem.tail)
            return

        # ── Inline formatting (<hi rend="italics">) ──
        if tag == 'hi':
            rend = elem.get('rend', 'italic')
            current_text.append(f'<span class="render-{rend}">')
            if elem.text:
                current_text.append(elem.text)
            for child in elem:
                _walk(child)
            current_text.append('</span>')
            if elem.tail and elem.tail.strip():
                current_text.append(elem.tail)
            return

        # ── Everything else (p, div, body, …): recurse ──
        if elem.text and elem.text.strip():
            current_text.append(elem.text)
        for child in elem:
            _walk(child)
        if elem.tail and elem.tail.strip():
            current_text.append(elem.tail)

    _walk(body)
    _flush()  # emit the final milestone span
    return data


# ── (2) Registry Entry ─────────────────────────────────────────
# Add Twining alongside the existing Poetics editions.

WORK_REGISTRY["aristotle_poetics"]["editions"]["eng_twining"] = {
    "path": "/Users/gcrane/github/Poetics2.0/grc/tlg0086.tlg034.twining1789-eng1.xml",
    "label": "English (Thomas Twining, 1789)",
    "class": "english-text",
    "parse_mode": "milestones"          # ← signals the processing loop
}


# ── (3) Processing-Loop Patch ──────────────────────────────────
# Replace the single parse_hierarchical_tei call in the processing
# loop with a dispatcher that checks for the "parse_mode" flag.
#
# In the loop where you currently have:
#
#     for v_id, cfg in editions.items():
#         parsed = parse_hierarchical_tei(cfg["path"])
#         if parsed:
#             work_corpus[v_id] = parsed
#
# Replace it with:

"""
    for v_id, cfg in editions.items():
        if cfg.get("parse_mode") == "milestones":
            parsed = parse_milestone_aligned_tei(cfg["path"])
        else:
            parsed = parse_hierarchical_tei(cfg["path"])
        if parsed:
            work_corpus[v_id] = parsed
"""
