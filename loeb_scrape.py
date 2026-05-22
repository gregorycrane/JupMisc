#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from urllib.parse import urlparse
import requests
from lxml import etree

GREEK_RE = re.compile(r'[\u0370-\u03FF\u1F00-\u1FFF]+')

def looks_greek(s: str) -> bool:
    if not s:
        return False
    return bool(GREEK_RE.search(s))

def get_text(e):
    # Join text content with single spaces
    return ' '.join(' '.join(e.itertext()).split())

def main():
    ap = argparse.ArgumentParser(description="Scrape Greek text and notes from a Loeb TEI XML page.")
    ap.add_argument("url", help="Loeb XML URL (requires you to have access/login if gated)")
    ap.add_argument("--out-prefix", default="loeb_aeschylus", help="Output filename prefix (default: loeb_aeschylus)")
    args = ap.parse_args()

    # Fetch XML (respect site terms; requires appropriate access)
    headers = {
        "User-Agent": "Academic-usage-script/1.0 (+contact: example@example.com)"
    }
    try:
        r = requests.get(args.url, headers=headers, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse XML, tolerate namespaces
    try:
        parser = etree.XMLParser(recover=True, remove_comments=True)
        root = etree.fromstring(r.content, parser=parser)
    except Exception as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        sys.exit(1)

    # Namespace-agnostic helpers
    NSMAP = root.nsmap.copy() if root.nsmap else {}
    # Build XPath that ignores namespaces using local-name()
    def xp(path):
        return root.xpath(path, namespaces=NSMAP)

    # Collect Greek text candidates.
    greek_rows = []
    # Strategy:
    # 1) Any element with @xml:lang or @lang indicating Greek (grc, ell, el, greek).
    # 2) Any element whose text contains Greek Unicode (filter out pure English lines).
    # We also try to carry structural hints: play/div/head/l/lb, @n, @xml:id.
    xml_lang_xpath = ".//*[(@xml:lang='grc' or @xml:lang='ell' or @xml:lang='el' or @lang='grc' or @lang='ell' or @lang='el') and normalize-space(string(.))!='']"
    greekish_xpath = ".//*[normalize-space(string(.))!='']"

    # Maintain a set of element ids to avoid duplicates
    seen = set()

    # First pass: language-tagged elements
    for e in xp(xml_lang_xpath):
        tid = e.get('{http://www.w3.org/XML/1998/namespace}id') or e.get('id')
        text = get_text(e)
        if not text or not looks_greek(text):
            continue
        if tid and tid in seen:
            continue
        seen.add(tid or f"loc-{len(seen)+1}")
        # get context
        n = e.get('n') or e.get('num') or ''
        tag = etree.QName(e).localname
        path = root.getpath(e)
        greek_rows.append({
            "element": tag,
            "n": n,
            "xml_id": tid or "",
            "xpath": path,
            "text": text
        })

    # Second pass: fallback for Greek-looking text without lang tags (common in some TEI)
    for e in xp(greekish_xpath):
        text = get_text(e)
        if looks_greek(text):
            tid = e.get('{http://www.w3.org/XML/1998/namespace}id') or e.get('id')
            key = (tid or root.getpath(e))
            if key in seen:
                continue
            # Heuristic: skip if ancestor already captured to reduce duplication
            anc = e.getparent()
            skip = False
            while anc is not None:
                if anc in greek_rows:
                    skip = True
                    break
                anc = anc.getparent()
            if skip:
                continue
            seen.add(key)
            n = e.get('n') or e.get('num') or ''
            tag = etree.QName(e).localname
            path = root.getpath(e)
            greek_rows.append({
                "element": tag,
                "n": n,
                "xml_id": tid or "",
                "xpath": path,
                "text": text
            })

    # Extract notes (TEI <note>), including @n, @type, @resp, @target
    note_xpath = ".//*[local-name()='note' and normalize-space(string(.))!='']"
    note_rows = []
    for e in xp(note_xpath):
        tid = e.get('{http://www.w3.org/XML/1998/namespace}id') or e.get('id') or ""
        n = e.get('n') or ""
        t = e.get('type') or ""
        resp = e.get('resp') or ""
        target = e.get('target') or ""
        place = e.get('place') or ""
        lang = e.get('{http://www.w3.org/XML/1998/namespace}lang') or e.get('lang') or ""
        text = get_text(e)
        note_rows.append({
            "xml_id": tid,
            "n": n,
            "type": t,
            "resp": resp,
            "place": place,
            "lang": lang,
            "target": target,
            "text": text
        })

    # Write TSV files
    greek_out = f"{args.out_prefix}.greek_text.tsv"
    notes_out = f"{args.out_prefix}.notes.tsv"
    with open(greek_out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["element","n","xml_id","xpath","text"], delimiter="\t")
        w.writeheader()
        for row in greek_rows:
            w.writerow(row)

    with open(notes_out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["xml_id","n","type","resp","place","lang","target","text"], delimiter="\t")
        w.writeheader()
        for row in note_rows:
            w.writerow(row)

    print(f"Wrote {len(greek_rows)} Greek text rows to {greek_out}")
    print(f"Wrote {len(note_rows)} notes to {notes_out}")

if __name__ == "__main__":
    main()
