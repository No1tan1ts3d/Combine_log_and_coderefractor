import re
import streamlit as st
from typing import List, Tuple, Dict, Optional


def build_log_line(log_style: str, func_name: str, device_expr: str, is_kernel_driver: bool = False) -> str:
    message = f'"entered function {func_name}\\n"'
    if is_kernel_driver:
        if log_style == "printk":
            return f'printk(KERN_INFO {message});'
        elif log_style == "pr_info":
            return f'pr_info({message});'
        elif log_style == "pr_debug":
            return f'pr_debug({message});'
        elif log_style == "dev_dbg":
            dev = device_expr.strip() or "dev"
            return f'dev_dbg({dev}, {message});'
        else:
            return f'printk(KERN_INFO {message});'
    else:
        if log_style == "printf":
            return f'printf({message});'
        elif log_style == "pr_debug":
            return f'pr_debug({message});'
        elif log_style == "dev_dbg":
            dev = device_expr.strip() or "dev"
            return f'dev_dbg({dev}, {message});'
        else:
            return f'printf({message});'


def build_exit_log_line(log_style: str, func_name: str, device_expr: str, is_kernel_driver: bool = False) -> str:
    message = f'"exiting function {func_name}\\n"'
    if is_kernel_driver:
        if log_style == "printk":
            return f'printk(KERN_INFO {message});'
        elif log_style == "pr_info":
            return f'pr_info({message});'
        elif log_style == "pr_debug":
            return f'pr_debug({message});'
        elif log_style == "dev_dbg":
            dev = device_expr.strip() or "dev"
            return f'dev_dbg({dev}, {message});'
        else:
            return f'printk(KERN_INFO {message});'
    else:
        if log_style == "printf":
            return f'printf({message});'
        elif log_style == "pr_debug":
            return f'pr_debug({message});'
        elif log_style == "dev_dbg":
            dev = device_expr.strip() or "dev"
            return f'dev_dbg({dev}, {message});'
        else:
            return f'printf({message});'


def build_value_log(log_style: str, name_label: str, fmt: str, value_expr: str, device_expr: str, is_kernel_driver: bool = False) -> str:
    fmt_message = f'"{name_label}={fmt}\\n"'
    if is_kernel_driver:
        if log_style == "printk":
            return f'printk(KERN_INFO {fmt_message}, {value_expr});'
        elif log_style == "pr_info":
            return f'pr_info({fmt_message}, {value_expr});'
        elif log_style == "pr_debug":
            return f'pr_debug({fmt_message}, {value_expr});'
        elif log_style == "dev_dbg":
            dev = device_expr.strip() or "dev"
            return f'dev_dbg({dev}, {fmt_message}, {value_expr});'
        else:
            return f'printk(KERN_INFO {fmt_message}, {value_expr});'
    else:
        if log_style == "printf":
            return f'printf({fmt_message}, {value_expr});'
        elif log_style == "pr_debug":
            return f'pr_debug({fmt_message}, {value_expr});'
        elif log_style == "dev_dbg":
            dev = device_expr.strip() or "dev"
            return f'dev_dbg({dev}, {fmt_message}, {value_expr});'
        else:
            return f'printf({fmt_message}, {value_expr});'


# --- Utilities for parsing ---

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

        # start comments
        if ch == '/' and nxt == '/':
            in_line_comment = True
            i += 2
            continue
        if ch == '/' and nxt == '*':
            in_block_comment = True
            i += 2
            continue

        # strings/chars
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


def insert_exit_before_returns(body: str, exit_line_builder: str, default_indent: str, log_style: str, device_expr: str, is_kernel_driver: bool) -> str:
    i = 0
    res: List[str] = []
    in_line_comment = False
    in_block_comment = False
    in_string = False
    in_char = False
    string_delim = ''

    def append_exit_and_return_value(return_expr: str):
        # ensure newline before inserting
        joined = ''.join(res)
        if not joined.endswith('\n'):
            res.append('\n')
        res.append(default_indent)
        res.append(exit_line_builder)
        res.append('\n')
        
        # Add return value print if there's an expression
        if return_expr.strip():
            if is_kernel_driver:
                res.append(f'{default_indent}printk(KERN_INFO "return value: %d\\n", {return_expr.strip()});\n')
            else:
                res.append(f'{default_indent}printf("return value: %d\\n", {return_expr.strip()});\n')

    while i < len(body):
        ch = body[i]
        nxt = body[i + 1] if i + 1 < len(body) else ''

        if in_line_comment:
            res.append(ch)
            if ch == '\n':
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            res.append(ch)
            if ch == '*' and nxt == '/':
                res.append(nxt)
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_string:
            res.append(ch)
            if ch == '\\':
                if nxt:
                    res.append(nxt)
                    i += 2
                    continue
            if ch == string_delim:
                in_string = False
            i += 1
            continue

        if in_char:
            res.append(ch)
            if ch == '\\':
                if nxt:
                    res.append(nxt)
                    i += 2
                    continue
            if ch == "'":
                in_char = False
            i += 1
            continue

        # start comments
        if ch == '/' and nxt == '/':
            res.append(ch)
            res.append(nxt)
            in_line_comment = True
            i += 2
            continue
        if ch == '/' and nxt == '*':
            res.append(ch)
            res.append(nxt)
            in_block_comment = True
            i += 2
            continue

        # strings/chars
        if ch in ('"', "'"):
            res.append(ch)
            if ch == '"':
                in_string = True
                string_delim = '"'
            else:
                in_char = True
            i += 1
            continue

        # detect 'return' token in normal state
        if body.startswith('return', i):
            before = body[i - 1] if i > 0 else ' '
            after = body[i + 6] if i + 6 < len(body) else ' '
            if not (before.isalnum() or before == '_') and not (after.isalnum() or after == '_'):
                # Extract return expression
                return_start = i + 6
                return_end = body.find(';', return_start)
                if return_end != -1:
                    return_expr = body[return_start:return_end].strip()
                    append_exit_and_return_value(return_expr)
        res.append(ch)
        i += 1

    return ''.join(res)


# --- Parameter parsing ---

def split_params(param_src: str) -> List[str]:
    # Remove comments
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
    # Remove default values and attributes
    p = re.sub(r'__attribute__\s*\(\([^)]*\)\)', '', param)
    p = re.sub(r'=[^,]+$', '', p).strip()
    
    # Handle complex parameter declarations
    # Look for the last identifier that's not a type keyword
    type_keywords = {
        'const', 'volatile', 'static', 'extern', 'register', 'auto',
        'signed', 'unsigned', 'short', 'long', 'int', 'char', 'float', 'double',
        'void', 'struct', 'union', 'enum', 'typedef'
    }
    
    # Split by whitespace and find the last non-keyword identifier
    tokens = re.findall(r'[A-Za-z_]\w*|\*+', p)
    if not tokens:
        return None
    
    # Find the last token that's not a type keyword
    name = None
    for token in reversed(tokens):
        if token not in type_keywords and not token.startswith('*'):
            name = token
            break
    
    if not name:
        # Fallback: take the last identifier
        name = tokens[-1]
    
    # Extract type part (everything before the name)
    name_pos = p.rfind(name)
    if name_pos == -1:
        return None
    
    type_part = p[:name_pos].strip()
    
    # Handle trailing asterisks
    after_name = p[name_pos + len(name):].lstrip()
    star_match = re.match(r'\*+', after_name)
    if star_match:
        type_part = (type_part + ' ' + star_match.group(0)).strip()
    
    return name, type_part


def printf_format_for_type(type_str: str) -> str:
    ts = type_str.lower().strip()
    # Handle char* (string) types first
    if 'char' in ts and '*' in ts:
        return '%s'
    # Handle pointer types
    if '*' in ts or ' __iomem' in ts:
        return '%p'
    # Handle floating point types
    if 'double' in ts or 'float' in ts:
        return '%f'
    # Handle size types
    if 'size_t' in ts:
        return '%zu'
    if 'ssize_t' in ts:
        return '%zd'
    # Handle 64-bit types
    if re.search(r'\b(u64|uint64_t|unsigned\s+long\s+long)\b', ts):
        return '%llu'
    if re.search(r'\b(s64|int64_t|long\s+long)\b', ts):
        return '%lld'
    # Handle 32-bit types
    if re.search(r'\b(u32|uint32_t|unsigned\s+int|unsigned)\b', ts):
        return '%u'
    if re.search(r'\b(s32|int32_t|int)\b', ts):
        return '%d'
    # Handle 16-bit types
    if re.search(r'\b(u16|uint16_t|unsigned\s+short)\b', ts):
        return '%hu'
    if re.search(r'\b(s16|int16_t|short)\b', ts):
        return '%hd'
    # Handle 8-bit types
    if re.search(r'\b(u8|uint8_t|unsigned\s+char)\b', ts):
        return '%hhu'
    if re.search(r'\b(s8|int8_t|char)\b', ts):
        return '%hhd'
    # Handle boolean types
    if 'bool' in ts or '_bool' in ts:
        return '%d'
    # Default for unknown types
    return '%d'


def detect_simple_declaration(line: str) -> Optional[Tuple[str, str, bool]]:
    # Returns (var_name, type_str, has_initializer) if single declarator without comma
    # Ignore preprocessor lines
    stripped = line.lstrip()
    if not stripped or stripped.startswith('#'):
        return None
    # Remove trailing comments for parsing
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
    # Detects simple identifier assignment like: x = ...; or x += ...;
    # Excludes comparisons, control headers, and declarations
    stripped = line.lstrip()
    if not stripped or stripped.startswith('#'):
        return None
    core = strip_line_comment_aware(line)
    # Exclude for/while/if headers
    if re.match(r'^\s*(if|while|for|switch)\b', core):
        return None
    # Exclude declarations heuristically: type before identifier
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
            # Extract function name
            name = re.sub(r'.*\b', '', name)  # keep last word-ish
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


# --- Body instrumentation ---

def instrument_body_for_values(body: str,
                               func_name: str,
                               log_style: str,
                               device_expr: str,
                               print_decls: bool,
                               print_assigns: bool,
                               print_calls: bool,
                               print_control: bool,
                               known_types: Dict[str, str],
                               is_kernel_driver: bool = False) -> str:
    lines = body.split('\n')
    # First pass: collect simple declarations into known_types
    for ln in lines:
        dec = detect_simple_declaration(ln)
        if dec:
            var_name, type_str, _ = dec
            known_types.setdefault(var_name, type_str)

    new_lines: List[str] = []
    for ln in lines:
        new_lines.append(ln)
        # Skip preprocessor
        stripped = ln.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = ln[: len(ln) - len(stripped)]

        # Control flow entries
        if print_control and re.match(r'^\s*(if|else\s+if|else\b|for|while|switch|case\b|default\b)', strip_line_comment_aware(ln)):
            msg = build_value_log(log_style, f'control in {func_name}', '%s', '"' + stripped.split('{')[0].strip().replace('"', '\\"') + '"', device_expr, is_kernel_driver)
            new_lines.append(indent + msg)

        # Declarations with initializer
        if print_decls:
            dec = detect_simple_declaration(ln)
            if dec:
                var_name, type_str, has_init = dec
                if has_init:
                    fmt = printf_format_for_type(type_str)
                    new_lines.append(indent + build_value_log(log_style, var_name, fmt, var_name, device_expr, is_kernel_driver))

        # Assignments
        if print_assigns:
            asg = detect_simple_assignment(ln)
            if asg:
                var_name, op = asg
                type_str = known_types.get(var_name, '')
                fmt = printf_format_for_type(type_str)
                new_lines.append(indent + build_value_log(log_style, var_name, fmt, var_name, device_expr, is_kernel_driver))

        # Function calls
        if print_calls:
            calls = detect_function_calls(ln)
            for c in calls:
                new_lines.append(indent + build_value_log(log_style, f'calling {c}', '%s', '""', device_expr, is_kernel_driver))

    return '\n'.join(new_lines)


# --- Top-level function detection and instrumentation ---

def add_debug_statements(code: str,
                         log_style: str = "printf",
                         device_expr: str = "",
                         add_entry_exit: bool = True,
                         add_exit_before_returns: bool = True,
                         print_params: bool = True,
                         print_decls: bool = True,
                         print_assigns: bool = True,
                         print_calls: bool = True,
                         print_control: bool = False,
                         final_exit_always: bool = True,
                         is_kernel_driver: bool = False) -> str:
    params_pattern = r'(?:[^(){}]|\([^()]*\))*'
    func_re = re.compile(
        rf'''(^[ \t]*
            (?:(?:static|inline|extern|constexpr|virtual|friend)\s+)*
            (?!struct\b|enum\b|union\b)
            [A-Za-z_][\w\s\*\(\)]*?[ \t]+
            (?P<name>[A-Za-z_]\w*)\s*\( (?P<params>{params_pattern}) \)\s*(?:const\s*)?(?:noexcept\s*)?\s*\{{
        )''',
        re.MULTILINE | re.VERBOSE)

    result_parts: List[str] = []
    last_index = 0

    for m in func_re.finditer(code):
        header_start = m.start(0)
        header_end = m.end(0)
        func_name = m.group('name')
        params_src = m.group('params')
        # Find the opening brace within the header span
        open_brace_index = code.find('{', header_start, header_end)
        if open_brace_index == -1:
            continue
        close_brace_index = find_matching_brace(code, open_brace_index)
        if close_brace_index == -1:
            continue

        # Append code before this function unchanged up to '{'
        result_parts.append(code[last_index:open_brace_index + 1])

        # Determine base indentation inside function
        after_brace_newline = code.find('\n', open_brace_index, close_brace_index)
        base_indent = ''
        if after_brace_newline != -1:
            indent_end = after_brace_newline + 1
            while indent_end < len(code) and code[indent_end] in (' ', '\t'):
                base_indent += code[indent_end]
                indent_end += 1
        if not base_indent:
            line_start = code.rfind('\n', 0, header_start)
            header_line_indent = ''
            if line_start != -1:
                j = line_start + 1
                while j < len(code) and code[j] in (' ', '\t'):
                    header_line_indent += code[j]
                    j += 1
            base_indent = header_line_indent + '    '

        entry_line = build_log_line(log_style, func_name, device_expr, is_kernel_driver)
        exit_line = build_exit_log_line(log_style, func_name, device_expr, is_kernel_driver)

        # Function body (excluding outer braces)
        body = code[open_brace_index + 1:close_brace_index]

        # Avoid duplicate insertion if already instrumented
        already_instrumented = (f'entered function {func_name}' in body) or (f'exiting function {func_name}' in body)

        new_body = body
        if not already_instrumented:
            insertion_lines: List[str] = []
            if add_entry_exit:
                insertion_lines.append(f"\n{base_indent}{entry_line}")

            # Parameter prints
            known_types: Dict[str, str] = {}
            if print_params and params_src.strip() and params_src.strip() != 'void':
                for raw in split_params(params_src):
                    parsed = parse_param_name_and_type(raw)
                    if not parsed:
                        continue
                    pname, ptype = parsed
                    known_types[pname] = ptype
                    fmt = printf_format_for_type(ptype)
                    insertion_lines.append(f"{base_indent}{build_value_log(log_style, pname, fmt, pname, device_expr, is_kernel_driver)}")

            # Prepend the entry and parameter logs right after the opening brace
            prefix = '\n'.join(insertion_lines)
            if new_body.startswith('\n'):
                new_body = prefix + '\n' + new_body[1:]
            else:
                new_body = prefix + '\n' + new_body

            # Add exit before returns if enabled
            if add_exit_before_returns:
                new_body = insert_exit_before_returns(new_body, exit_line, base_indent, log_style, device_expr, is_kernel_driver)

            # Instrument body internals
            new_body = instrument_body_for_values(new_body,
                                                 func_name,
                                                 log_style,
                                                 device_expr,
                                                 print_decls,
                                                 print_assigns,
                                                 print_calls,
                                                 print_control,
                                                 known_types,
                                                 is_kernel_driver)

            # Ensure final exit if requested
            if final_exit_always:
                if not new_body.endswith('\n'):
                    new_body += '\n'
                new_body += f"{base_indent}{exit_line}\n"

        # Append modified body and closing brace
        result_parts.append(new_body)
        result_parts.append('}')

        # Move last_index
        last_index = close_brace_index + 1

    # Append the remainder of the code
    result_parts.append(code[last_index:])

    return ''.join(result_parts)


def add_kernel_includes(code: str, is_kernel_driver: bool) -> str:
    """Add necessary kernel includes if this is kernel driver code"""
    if not is_kernel_driver:
        return code
    
    # Check if kernel includes are already present
    if '#include <linux/kthread.h>' in code:
        return code
    
    # Find the first #include line or add at the beginning
    lines = code.split('\n')
    insert_index = 0
    
    for i, line in enumerate(lines):
        if line.strip().startswith('#include'):
            insert_index = i + 1
        elif line.strip() and not line.strip().startswith('//') and not line.strip().startswith('/*'):
            # Found first non-comment, non-include line
            break
    
    # Insert kernel includes
    kernel_includes = [
        '#include <linux/kthread.h>',
        '#include <linux/module.h>',
        '#include <linux/kernel.h>'
    ]
    
    lines[insert_index:insert_index] = kernel_includes
    return '\n'.join(lines)


# ---- Streamlit UI ----

st.set_page_config(layout="wide")

st.title("C/C++ Code Refractor")

st.write(
    "Paste your C/C++ code or upload a file. The app instruments function entry/exit, parameters, simple declarations, assignments, and calls."
)

# Input method
input_method = st.radio("Choose input method:", ("Paste code", "Upload file"))

code = ""
if input_method == "Paste code":
    code = st.text_area("Paste your C/C++ code here:", height=240)
elif input_method == "Upload file":
    uploaded_file = st.file_uploader("Choose a C/C++ file", type=["c", "cpp", "h", "hpp"])
    if uploaded_file is not None:
        code = uploaded_file.read().decode("utf-8", errors="ignore")

# Instrumentation Context Toggle

import streamlit as st

st.subheader("Instrumentation Context")

# st.toggle returns True if toggled on, False otherwise
mode = st.toggle("Toggle to turn on Kernel Driver Mode (QDMA)", value=False)

is_kernel_driver = mode  # Directly use the boolean value
st.caption(f"Selected Mode: {'Kernel Driver Code' if is_kernel_driver else 'User Space Code'}") 

# st.subheader("Instrumentation Context")
# mode = st.toggle("Kernel Driver Mode (QDMA)", options=["Off", "On"], value="Off")
# is_kernel_driver = (mode == "On")
# st.caption(f"Status: {'Kernel Driver Code' if is_kernel_driver else 'User Space Code'}")


# #is_user_space = st.checkbox("User Space Code", value=False)

# Logging style options
st.subheader("Logging options")
if is_kernel_driver:
    log_style = st.selectbox("Statement type", ["printk", "pr_info", "pr_debug", "dev_dbg"], index=0)
else:
    log_style = st.selectbox("Statement type", ["printf", "pr_debug", "dev_dbg"], index=0)

device_expr = ""
if log_style == "dev_dbg":
    device_expr = st.text_input(
        "Device expression for dev_dbg (e.g., port->dev)",
        value="port->dev",
        placeholder="port->dev"
    )

st.subheader("Instrumentation toggles")
add_entry_exit = st.checkbox("Add entry/exit logs", value=True)
add_exit_before_returns = st.checkbox("Add exit before each return", value=True)
print_params = st.checkbox("Print parameter values at entry", value=True)
print_decls = st.checkbox("Print initial values for simple declarations", value=True)
print_assigns = st.checkbox("Print values after simple assignments", value=True)
print_calls = st.checkbox("Print when calling functions (best-effort)", value=True)
print_control = st.checkbox("Print control-flow entries (if/for/while/switch)", value=False)
final_exit_always = st.checkbox("Always append a final exit log", value=True)

if code:
    # Add kernel includes if needed
    if is_kernel_driver:
        code = add_kernel_includes(code, is_kernel_driver)
    
    modified_code = add_debug_statements(
        code,
        log_style=log_style,
        device_expr=device_expr,
        add_entry_exit=add_entry_exit,
        add_exit_before_returns=add_exit_before_returns,
        print_params=print_params,
        print_decls=print_decls,
        print_assigns=print_assigns,
        print_calls=print_calls,
        print_control=print_control,
        final_exit_always=final_exit_always,
        is_kernel_driver=is_kernel_driver,
    )

    # Side-by-side layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original Code:")
        st.code(code, language="cpp")
    
    with col2:
        st.subheader("Modified Code with Debug Prints:")
        st.code(modified_code, language="cpp")

    st.download_button(
        label="Download Modified Code",
        data=modified_code,
        file_name="modified.c",
        mime="text/x-c"
    )

if input_method == "Upload file":
    multiple_files = st.toggle("Enable multiple file upload", value=False)
    if multiple_files:
        uploaded_files = st.file_uploader("Choose C/C++ files", type=["c", "cpp", "h", "hpp"], accept_multiple_files=True)
        if uploaded_files:
            # Create tabs for each file
            file_tabs = st.tabs([f.name for f in uploaded_files])
            for tab, file in zip(file_tabs, uploaded_files):
                with tab:
                    code = file.read().decode("utf-8", errors="ignore")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"Original Code - {file.name}")
                        st.code(code, language="cpp")
                    
                    modified_code = add_debug_statements(
                        code,
                        log_style=log_style,
                        device_expr=device_expr,
                        add_entry_exit=add_entry_exit,
                        add_exit_before_returns=add_exit_before_returns,
                        print_params=print_params,
                        print_decls=print_decls,
                        print_assigns=print_assigns,
                        print_calls=print_calls,
                        print_control=print_control,
                        final_exit_always=final_exit_always,
                        is_kernel_driver=is_kernel_driver,
                    )
                    
                    with col2:
                        st.subheader(f"Modified Code - {file.name}")
                        st.code(modified_code, language="cpp")
                        
                    st.download_button(
                        label=f"Download Modified {file.name}",
                        data=modified_code,
                        file_name=f"modified_{file.name}",
                        mime="text/x-c",
                        key=f"download_{file.name}"  # Add unique key
                    )
    else:
        # Single file upload without duplicating the UI elements
        uploaded_file = st.file_uploader("Choose a C/C++ file", type=["c", "cpp", "h", "hpp"], key="single_file")
        if uploaded_file is not None:
            code = uploaded_file.read().decode("utf-8", errors="ignore")
            if is_kernel_driver:
                code = add_kernel_includes(code, is_kernel_driver)
            
            modified_code = add_debug_statements(
                code,
                log_style=log_style,
                device_expr=device_expr,
                add_entry_exit=add_entry_exit,
                add_exit_before_returns=add_exit_before_returns,
                print_params=print_params,
                print_decls=print_decls,
                print_assigns=print_assigns,
                print_calls=print_calls,
                print_control=print_control,
                final_exit_always=final_exit_always,
                is_kernel_driver=is_kernel_driver,
            )

            # Side-by-side layout for single file
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Original Code:")
                st.code(code, language="cpp")
            
            with col2:
                st.subheader("Modified Code with Debug Prints:")
                st.code(modified_code, language="cpp")

            st.download_button(
                label="Download Modified Code",
                data=modified_code,
                file_name=f"modified_{uploaded_file.name}",
                mime="text/x-c",
                key="download_single"  # Add unique key
            )