"""
Kiểm tra cú pháp các khối mermaid trong docs/sequence-diagrams.md.

Dùng regex đơn giản + kiểm tra thủ công các lỗi Mermaid hay gặp:
  - Nhãn nhiều dòng phải dùng <br/> chứ không dùng \n
  - Mũi tên phải có dạng đúng (->>, -->>, ->, -->, -x, --x)
  - Không để ký tự lạ trong tên tham gia

Cách dùng:
    python check_mermaid.py
"""

import io
import os
import re
import sys

DOC_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'docs', 'sequence-diagrams.md'
)

# Biểu thức nhận dạng một mũi tên hợp lệ của Mermaid sequence diagram
ARROW = re.compile(r'-->>|->>|-->|->|--x|-x|--\)|-\)')

# Thân một mũi tên: A->>B, A-->>B, A->B, A--B, A-xB, A--xB
ARROW_BODY = re.compile(r'-{1,2}(?:>>|->|>|x|\))')

# Dòng bắt đầu bằng thẻ ``` : nhãn loại sơ đồ
FENCE_RE = re.compile(r'^```(\w*)\s*$')


def extract_blocks(text):
    """Tách file thành các khối code, trả về [(ngôn ngữ, nội dung, dòng bắt đầu)]."""
    blocks = []
    inside = False
    lang = None
    start = 0
    buf = []

    for lineno, line in enumerate(text.splitlines(), start=1):
        match = FENCE_RE.match(line)
        if match:
            if not inside:
                inside = True
                lang = match.group(1)
                start = lineno + 1
                buf = []
            else:
                blocks.append((lang, '\n'.join(buf), start))
                inside = False
            continue
        if inside:
            buf.append(line)

    if inside:
        blocks.append((lang, '\n'.join(buf), start))
    return blocks


def check_sequence(name, body, offset):
    """Kiểm tra một khối sequenceDiagram. Trả về danh sách lỗi."""
    errors = []
    lines = body.splitlines()

    if not lines or not lines[0].strip().startswith('sequenceDiagram'):
        return [f"{name} (dòng {offset}): dòng đầu phải là 'sequenceDiagram'"]

    seen_declare = False
    seen_message = False
    # Bỏ qua dòng tiêu đề (lines[0]), bắt đầu từ dòng thứ 2
    for i, raw in enumerate(lines[1:], start=1):
        lineno = offset + i
        line = raw.strip()

        if not line:
            continue

        # Không được dùng \n trong nhãn — Mermaid không hiểu
        if '\\n' in line:
            errors.append(f"{name} (dòng {lineno}): dùng \\n, phải dùng thẻ br")

        # Khai báo tham gia
        if line.startswith('participant '):
            seen_declare = True
            if ' as ' not in line and not re.match(
                r'participant\s+\w+\s*$', line
            ):
                errors.append(f"{name} (dòng {lineno}): participant thiếu tên hiển thị")
            continue

        # Khối chú thích / alt / else / opt / loop / rect / par / Note / activate
        if line.startswith(('alt ', 'else ', 'opt ', 'loop ', 'rect ', 'par ',
                            'and ', 'critical ', 'break ', 'Note ', 'note ',
                            'activate ', 'deactivate ', 'autonumber', 'end')):
            continue

        # actor
        if line.startswith('actor '):
            continue

        # Mũi tên: dạng  A->>B: msg   hoặc   A-->>B: msg   hoặc   A-xB: msg
        if re.match(r'^\w+' + ARROW_BODY.pattern + r'\w+', line):
            seen_message = True
            if not ARROW.search(line):
                errors.append(
                    f"{name} (dòng {lineno}): mũi tên không hợp lệ → {line[:50]}"
                )
            if ':' not in line:
                errors.append(
                    f"{name} (dòng {lineno}): mũi tên thiếu nội dung sau dấu ':'"
                )
            continue

        # Còn lại phải là mũi tên hoặc lệnh hợp lệ
        if re.match(r'^\w+[-=]', line):
            continue

        errors.append(f"{name} (dòng {lineno}): không nhận dạng được → {line[:60]}")

    if not seen_declare:
        errors.append(f"{name}: không có dòng 'participant ...'")
    if not seen_message:
        errors.append(f"{name}: không có dòng thông điệp nào")

    return errors


def check_state(name, body, offset):
    """Kiểm tra khối stateDiagram-v2."""
    errors = []
    lines = body.splitlines()
    if not lines or 'stateDiagram' not in lines[0]:
        return [f"{name} (dòng {offset}): phải bắt đầu bằng stateDiagram-v2"]
    for i, raw in enumerate(lines[1:], start=offset + 1):
        line = raw.strip()
        if not line or line.startswith('[*]') or '-->' in line:
            continue
        if re.match(r'^\w+\s*:\s*.+$', line):
            continue
        if line in ('state "x" as y',):
            continue
        errors.append(f"{name} (dòng {i}): không nhận dạng được → {line[:60]}")
    return errors


def check_class(name, body, offset):
    """
    Kiểm tra khối classDiagram.

    Cú pháp Mermaid hợp lệ trong thân class:
        +int id                 thuộc tính có kiểu
        +str username           thuộc tính có kiểu
        +create_user()          phương thức
        +is_available           thuộc tính không kiểu
        +Decimal price_snapshot
        ACTIVE                  thành viên của enum (<<enumeration>>)
    Quan hệ:
        User "1" --> "1" Profile : có
        Post "1" --> "n" Order : có đơn
    """
    errors = []
    lines = body.splitlines()

    if not lines or 'classDiagram' not in lines[0]:
        return [f"{name} (dòng {offset}): phải bắt đầu bằng classDiagram"]

    # Thuộc tính / phương thức hợp lệ (có hoặc không có kiểu, có hoặc không có :)
    member = re.compile(r'^[+\-~#]?\w+(\s+\w+)?(\s*\([^)]*\))?(\s*:\s*\w+)?\s*$')
    # Hằng số kiểu enum: chữ in hoa / gạch dưới
    enum_const = re.compile(r'^[A-Z][A-Z0-9_]*$')
    # Quan hệ giữa hai lớp
    relation = re.compile(r'^[A-Za-z_]\w*\s*(?:".*?"\s*)?'
                          r'(?:<\|--|\*--|o--|-->|<--|<\.\.|\.\.>|--|\.\.)'
                          r'[>|*o]?\s*(?:".*?"\s*)?[A-Za-z_]\w*'
                          r'\s*(?::.*)?$')

    in_braces = False
    for i, raw in enumerate(lines[1:], start=1):
        lineno = offset + i
        line = raw.strip()

        if not line or line.startswith('%%'):
            continue

        # Theo dõi khối { } của class / enum
        if line.endswith('{'):
            in_braces = True
            if re.match(r'^(class\s+\w+|\w+)\s*\{?$', line) or line == '{':
                continue
        if line == '}':
            in_braces = False
            continue

        if in_braces:
            # Nội dung bên trong {}: thuộc tính, phương thức, hằng enum
            # hoặc chú thích dạng <<enumeration>>
            if member.match(line) or enum_const.match(line):
                continue
            if re.match(r'^<<\w+>>$', line):
                continue
            if re.match(r'^[+\-~#]', line):       # có ký hiệu truy cập
                continue
            errors.append(
                f"{name} (dòng {lineno}): thành viên không hợp lệ → {line[:60]}"
            )
            continue

        if re.match(r'^class\s+\w+', line):
            continue
        if re.match(r'^<<\w+>>$', line):
            continue
        if line.startswith(('note', 'direction', 'namespace ', 'end namespace',
                            'classDef', 'style', 'linkStyle', 'callback')):
            continue
        if relation.match(line):
            continue

        errors.append(f"{name} (dòng {lineno}): không nhận dạng được → {line[:60]}")

    return errors


def main():
    if not os.path.exists(DOC_FILE):
        print(f"Không tìm thấy {DOC_FILE}")
        return 1

    with io.open(DOC_FILE, encoding='utf-8') as f:
        text = f.read()

    blocks = extract_blocks(text)
    mermaid = [(lang, body, start)
               for lang, body, start in blocks if lang == 'mermaid']

    if not mermaid:
        print("Không tìm thấy khối mermaid nào!")
        return 1

    all_errors = []
    print(f"Tìm thấy {len(mermaid)} khối mermaid:\n")

    for index, (lang, body, start) in enumerate(mermaid, start=1):
        first = next((ln for ln in body.splitlines() if ln.strip()), '')
        title = first.strip()[:40]

        if 'sequenceDiagram' in first:
            errors = check_sequence(f"Sơ đồ {index}", body, start)
        elif 'stateDiagram' in first:
            errors = check_state(f"Sơ đồ {index}", body, start)
        elif 'classDiagram' in first:
            errors = check_class(f"Sơ đồ {index}", body, start)
        else:
            errors = [f"Sơ đồ {index} (dòng {start}): loại sơ đồ lạ '{first}'"]

        lines = len([ln for ln in body.splitlines() if ln.strip()])
        status = 'OK  ' if not errors else 'SAI '
        print(f"  [{status}] Sơ đồ {index}: {title}  ({lines} dòng)")
        all_errors.extend(errors)

    print()
    if all_errors:
        print(f"✗ {len(all_errors)} lỗi cú pháp:\n")
        for err in all_errors:
            print(f"  • {err}")
        return 1

    print("✓ Tất cả khối mermaid đều hợp lệ — dán vào diagrams.net được.")
    return 0


if __name__ == '__main__':
    sys.exit(main())