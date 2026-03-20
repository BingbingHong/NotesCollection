import json
import re
import sys
from pathlib import Path


def is_note_line(text):
    stripped = text.lstrip()
    return stripped.startswith("◆") or stripped.startswith("•")


def clean_note_text(text):
    stripped = text.lstrip()
    if stripped.startswith("◆") or stripped.startswith("•"):
        return stripped[1:].strip()
    return stripped.strip()


def extract_thought_text(text):
    prefixes = [
        "我的想法",
        "想法",
        "心得",
        "感想",
        "评论",
        "笔记",
        "备注",
        "读后感",
    ]
    pattern = r"^(?:" + "|".join(prefixes) + r")[:：]?\s*(.*)$"
    match = re.match(pattern, text)
    if not match:
        return False, text
    return True, match.group(1).strip()


def is_heading(text, prev_blank, next_blank):
    t = text.strip()
    if not t:
        return False
    if len(t) > 30:
        return False
    if t.endswith("个笔记"):
        return False
    if is_note_line(t):
        return False
    if re.match(r"^《.+》$", t):
        return False
    if not (prev_blank or next_blank):
        return False
    return True


def parse_notes(lines):
    books = {}
    notes = []
    current_book = None
    current_section = ""
    last_note = None
    expect_author = False

    for idx, raw in enumerate(lines):
        line = raw.strip()
        prev_blank = idx > 0 and not lines[idx - 1].strip()
        next_blank = idx + 1 < len(lines) and not lines[idx + 1].strip()
        if not line:
            continue

        title_match = re.match(r"^《(.+)》$", line)
        if title_match:
            title = title_match.group(1).strip()
            current_book = {
                "title": title,
                "author": "",
                "noteCount": "",
            }
            books[title] = current_book
            current_section = ""
            last_note = None
            expect_author = True
            continue

        if current_book and expect_author:
            if line.endswith("个笔记"):
                current_book["noteCount"] = line
            else:
                current_book["author"] = line
            expect_author = False
            continue

        if current_book and line.endswith("个笔记"):
            current_book["noteCount"] = line
            last_note = None
            continue

        if not current_book:
            continue

        if is_note_line(line):
            note_text = clean_note_text(line)
            kind = "quote"
            is_thought, cleaned = extract_thought_text(note_text)
            if is_thought:
                kind = "thought"
                note_text = cleaned
            note = {
                "bookTitle": current_book["title"],
                "author": current_book["author"],
                "section": current_section,
                "text": note_text,
                "kind": kind,
            }
            notes.append(note)
            last_note = note
            continue

        if last_note and not is_heading(line, prev_blank, next_blank) and not prev_blank:
            last_note["text"] = f'{last_note["text"]}\n{line}'
            continue

        if is_heading(line, prev_blank, next_blank):
            current_section = line
            last_note = None
            continue

        is_thought, cleaned = extract_thought_text(line)
        note = {
            "bookTitle": current_book["title"],
            "author": current_book["author"],
            "section": current_section,
            "text": cleaned if is_thought else line,
            "kind": "thought" if is_thought else "quote",
        }
        notes.append(note)
        last_note = note

    return books, notes


def main():
    if len(sys.argv) < 2:
        raise SystemExit("需要提供输入文件路径")
    input_path = Path(sys.argv[1]).expanduser()
    output_path = (
        Path(sys.argv[2]).expanduser()
        if len(sys.argv) >= 3
        else Path.cwd() / "notes.json"
    )

    lines = input_path.read_text(encoding="utf-8").splitlines()
    books, notes = parse_notes(lines)

    payload = {
        "books": list(books.values()),
        "notes": notes,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
