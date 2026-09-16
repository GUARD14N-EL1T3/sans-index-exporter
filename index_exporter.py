#!/usr/bin/env python3

import argparse
import sys
from collections import defaultdict

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Table,
    TableStyle,
)

MARGIN = 0.5 * inch
PAGE_SIZE = letter
DOC_LAYOUT = {
    "title": "Index",
    "pagesize": PAGE_SIZE,
    "leftMargin": MARGIN,
    "rightMargin": MARGIN,
    "topMargin": MARGIN,
    "bottomMargin": MARGIN,
}

GAP = 0.1 * inch

HEADER_FONT_NAME = "Helvetica-Bold"
CELL_FONT_NAME = "Helvetica"
FONT_SIZE = 12
LEADING = 14

TERM_COL_RATIO = 0.6


def collapse_to_ranges(pages):
    ranges = []
    start = prev = pages[0]

    for page in pages[1:]:
        if page == prev + 1:
            prev = page
            continue
        ranges.append((start, prev) if start != prev else start)
        start = prev = page

    ranges.append((start, prev) if start != prev else start)
    return ranges


def format_pages(entries):
    by_book = defaultdict(list)
    for book, page_num in entries:
        by_book[book].append(page_num)

    parts = []
    for book in by_book:
        pages = sorted(set(by_book[book]))
        for item in collapse_to_ranges(pages):
            if isinstance(item, tuple):
                parts.append(f"{book}.{item[0]}-{item[1]}")
            else:
                parts.append(f"{book}.{item}")

    return ", ".join(parts)


def load_file(path):
    df = pd.read_csv(path)
    if not all(col in df.columns for col in ["Term", "Book", "Page"]):
        raise ValueError("CSV must contain 'Term', 'Book', and 'Page' columns.")

    data = defaultdict(list)
    for index, row in df.iterrows():
        try:
            term = str(row["Term"]).strip()
            book = int(row["Book"])
            pages = str(row["Page"]).strip()

            for p in pages.split(" "):
                data[term].append((book, int(p)))

        except (ValueError, TypeError) as e:
            log_msg(
                "load_file",
                f"WARNING: Skipping row {index} due to data conversion error: {e}",
            )
            continue

    return dict(data)


def log_msg(name, msg):
    print(f"[{name}] {msg}", file=sys.stderr)


def build_index_table(index_table, col_widths, cell_style):
    rows = []
    for term in sorted(index_table.keys(), key=str.lower):
        pages_str = format_pages(index_table[term])
        rows.append(
            [
                Paragraph(term, cell_style),
                Paragraph(pages_str, cell_style),
            ]
        )

    table = Table(rows, colWidths=col_widths, repeatRows=0)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                (
                    "ROWBACKGROUNDS",
                    (0, 0),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f2f2f2")],
                ),
            ]
        )
    )
    return table


def export_pdf(index_table, output_path):
    doc = BaseDocTemplate(output_path, **DOC_LAYOUT)

    col_width = (doc.width - GAP) / 2

    frame1 = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        col_width,
        doc.height,
        id="col1",
    )
    frame2 = Frame(
        doc.leftMargin + col_width + GAP,
        doc.bottomMargin,
        col_width,
        doc.height,
        id="col2",
    )
    doc.addPageTemplates([PageTemplate(id="TwoCol", frames=[frame1, frame2])])

    styles = getSampleStyleSheet()

    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontName=CELL_FONT_NAME,
        fontSize=FONT_SIZE,
        leading=LEADING,
        wordWrap=None,
    )

    term_col_width = col_width * TERM_COL_RATIO
    pages_col_width = col_width * (1 - TERM_COL_RATIO)

    index_body_table = build_index_table(
        cell_style=cell_style,
        col_widths=[term_col_width, pages_col_width],
        index_table=index_table,
    )

    story = [
        index_body_table,
    ]

    doc.build(story)


# -----------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("input")
    ap.add_argument("--output", default="index.pdf")

    args = ap.parse_args()

    index_table = load_file(args.input)
    export_pdf(index_table, args.output)
    print(f"Wrote {args.output} ({len(index_table)} terms).")


if __name__ == "__main__":
    main()
