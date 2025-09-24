import re
from typing import List, Tuple, Dict, Optional


def strip_line_comment_aware(text: str) -> str:
    out = []
    i = 0
    in_str = False
    in_char = False
    in_block = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if in_block:
            if ch == '*' and nxt == '/':
                in_block = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            out.append(ch)
            if ch == '\\':
                if nxt:
                    out.append(nxt)
                    i += 2
                    continue
            if ch == '"':
                in_str = False
            i += 1
            continue
        if in_char:
            out.append(ch)
            if ch == '\\':
                if nxt:
                    out.append(nxt)
                    i += 2
                    continue
            if ch == "'":
                in_char = False
            i += 1
            continue
        if ch == '/' and nxt == '*':
            in_block = True
            i += 2
            continue
        if ch == '/' and nxt == '/':
            break
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "'":
            in_char = True
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def find_matching_brace(code: str, open_index: int) -> int:
    depth = 0
    i = open_index
    in_line_comment = False
    in_block_comment = False
    in_string = False
    in_char = False
    string_delim = ''

    while i < len(code):
        ch = code[i]
        nxt = code[i + 1] if i + 1 < len(code) else ''

        if in_line_comment:
            if ch == '\n':
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == '*' and nxt == '/':
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_string:
            if ch == '\\':
                i += 2
                continue
            if ch == string_delim:
                in_string = False
            i += 1
            continue

        if in_char:
            if ch == '\\':
                i += 2
                continue
            if ch == "'":
                in_char = False
            i += 1
            continue

        if ch == '/' and nxt == '/':
            in_line_comment = True
            i += 2
            continue
        if ch == '/' and nxt == '*':
            in_block_comment = True
            i += 2
            continue

        if ch in ('"', "'"):
            if ch == '"':
                in_string = True
                string_delim = '"'
            else:
                in_char = True
            i += 1
            continue

        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def find_declarations_end(body: str) -> int:
    lines = body.split('\n')
    last_declaration_line = -1
    primitive_or_known_types = (
        r'(?:void|bool|_Bool|char|short|int|long|float|double|size_t|ssize_t|u8|u16|u32|u64|s8|s16|s32|s64|dma_addr_t|uintptr_t|intptr_t)'
    )
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*'):
            continue
        if any(keyword in stripped for keyword in ['printk', 'printf', 'pr_info', 'pr_debug', 'dev_dbg']):
            continue
        core = strip_line_comment_aware(line)
        # Prefer robust single-declarator detection
        from typing import Optional as _Optional  # avoid import cycle hints
        dec = detect_simple_declaration(core)
        if dec:
            last_declaration_line = i
            continue
        # Fallback: heuristic for declarations without initializers, multiple spaces between type and name
        # Require a known type keyword before the identifier to avoid matching assignments
        if re.match(rf'^\s*(?:const\s+|volatile\s+|static\s+)?(?:struct\s+\w+|union\s+\w+|enum\s+\w+|{primitive_or_known_types})(?:\s*\*+)?\s+[A-Za-z_]\w*\s*(?:;|=)', core) and not re.search(r'\([^)]*\)', core):
            last_declaration_line = i
            continue
        # Reaching a non-declaration statement means declarations are over
        break
    if last_declaration_line == -1:
        return 0
    char_index = 0
    for i in range(last_declaration_line + 1):
        if i < len(lines):
            char_index += len(lines[i]) + 1
    return char_index


def split_params(param_src: str) -> List[str]:
    src = strip_line_comment_aware(param_src)
    parts: List[str] = []
    depth = 0
    current = []
    i = 0
    in_str = False
    in_char = False
    while i < len(src):
        ch = src[i]
        if in_str:
            current.append(ch)
            if ch == '\\' and i + 1 < len(src):
                current.append(src[i + 1])
                i += 2
                continue
            if ch == '"':
                in_str = False
            i += 1
            continue
        if in_char:
            current.append(ch)
            if ch == '\\' and i + 1 < len(src):
                current.append(src[i + 1])
                i += 2
                continue
            if ch == "'":
                in_char = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            current.append(ch)
            i += 1
            continue
        if ch == "'":
            in_char = True
            current.append(ch)
            i += 1
            continue
        if ch == '(':
            depth += 1
            current.append(ch)
            i += 1
            continue
        if ch == ')':
            depth -= 1
            current.append(ch)
            i += 1
            continue
        if ch == ',' and depth == 0:
            parts.append(''.join(current).strip())
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    if current:
        parts.append(''.join(current).strip())
    return [p for p in parts if p and p != 'void']


def parse_param_name_and_type(param: str) -> Optional[Tuple[str, str]]:
    p = re.sub(r'__attribute__\s*\(\([^)]*\)\)', '', param)
    p = re.sub(r'=[^,]+$', '', p).strip()
    type_keywords = {
        'const', 'volatile', 'static', 'extern', 'register', 'auto',
        'signed', 'unsigned', 'short', 'long', 'int', 'char', 'float', 'double',
        'void', 'struct', 'union', 'enum', 'typedef'
    }
    tokens = re.findall(r'[A-Za-z_]\w*|\*+', p)
    if not tokens:
        return None
    name = None
    for token in reversed(tokens):
        if token not in type_keywords and not token.startswith('*'):
            name = token
            break
    if not name:
        name = tokens[-1]
    name_pos = p.rfind(name)
    if name_pos == -1:
        return None
    type_part = p[:name_pos].strip()
    after_name = p[name_pos + len(name):].lstrip()
    star_match = re.match(r'\*+', after_name)
    if star_match:
        type_part = (type_part + ' ' + star_match.group(0)).strip()
    return name, type_part


def printf_format_for_type(type_str: str) -> str:
    ts = type_str.lower().strip()
    if 'char' in ts and '*' in ts:
        return '%s'
    if '*' in ts or ' __iomem' in ts:
        return '%p'
    if 'double' in ts or 'float' in ts:
        return '%f'
    if 'size_t' in ts:
        return '%zu'
    if 'ssize_t' in ts:
        return '%zd'
    if re.search(r'\b(u64|uint64_t|unsigned\s+long\s+long)\b', ts):
        return '%llu'
    if re.search(r'\b(s64|int64_t|long\s+long)\b', ts):
        return '%lld'
    if re.search(r'\b(u32|uint32_t|unsigned\s+int|unsigned)\b', ts):
        return '%u'
    if re.search(r'\b(s32|int32_t|int)\b', ts):
        return '%d'
    if re.search(r'\b(u16|uint16_t|unsigned\s+short)\b', ts):
        return '%hu'
    if re.search(r'\b(s16|int16_t|short)\b', ts):
        return '%hd'
    if re.search(r'\b(u8|uint8_t|unsigned\s+char)\b', ts):
        return '%hhu'
    if re.search(r'\b(s8|int8_t|char)\b', ts):
        return '%hhd'
    if 'bool' in ts or '_bool' in ts:
        return '%d'
    return '%d'


def detect_simple_declaration(line: str) -> Optional[Tuple[str, str, bool]]:
    stripped = line.lstrip()
    if not stripped or stripped.startswith('#'):
        return None
    core = strip_line_comment_aware(line)
    if ',' in core:
        return None
    m = re.match(r'^\s*([^;=]+?)\s+([A-Za-z_]\w*)\s*(=\s*[^;]+)?\s*;\s*$', core)
    if not m:
        return None
    type_str = m.group(1).strip()
    name = m.group(2).strip()
    has_init = m.group(3) is not None
    return name, type_str, has_init


def detect_simple_assignment(line: str) -> Optional[Tuple[str, str]]:
    stripped = line.lstrip()
    if not stripped or stripped.startswith('#'):
        return None
    core = strip_line_comment_aware(line)
    if re.match(r'^\s*(if|while|for|switch)\b', core):
        return None
    if re.match(r'^\s*(?:const\s+|volatile\s+|static\s+)?(?:struct\s+\w+|enum\s+\w+|[A-Za-z_]\w*)(?:\s*\*+)?\s+[A-Za-z_]\w*\s*[=;]', core):
        return None
    m = re.match(r'^\s*([A-Za-z_]\w*)\s*([+\-*/%|&^]?=)\s*[^;]+;\s*$', core)
    if not m:
        return None
    return m.group(1), m.group(2)


KEYWORDS = {
    'if', 'for', 'while', 'switch', 'return', 'sizeof', 'typeof', 'alignof',
}
EXCLUDED_CALLS = {'printf', 'pr_debug', 'dev_dbg'}


def detect_function_calls(line: str) -> List[str]:
    core = strip_line_comment_aware(line)
    calls: List[str] = []
    i = 0
    depth = 0
    in_str = False
    in_char = False
    token = []
    while i < len(core):
        ch = core[i]
        if in_str:
            if ch == '\\' and i + 1 < len(core):
                i += 2
                continue
            if ch == '"':
                in_str = False
            i += 1
            continue
        if in_char:
            if ch == '\\' and i + 1 < len(core):
                i += 2
                continue
            if ch == "'":
                in_char = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            i += 1
            continue
        if ch == "'":
            in_char = True
            i += 1
            continue
        if ch == '(':
            name = ''.join(token).strip()
            token = []
            name = re.sub(r'.*\b', '', name)
            m = re.search(r'([A-Za-z_]\w*)\s*$', name)
            if m:
                fname = m.group(1)
                if fname not in KEYWORDS and fname not in EXCLUDED_CALLS:
                    calls.append(fname)
            depth += 1
            i += 1
            continue
        if ch == ')':
            depth = max(0, depth - 1)
            i += 1
            continue
        token.append(ch)
        i += 1
    return calls


