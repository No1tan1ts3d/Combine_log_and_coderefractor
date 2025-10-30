import re
from typing import List, Tuple, Dict, Optional

from modules.logging_utils import build_log_line, build_exit_log_line, build_value_log
from modules.parsing_utils import (
    strip_line_comment_aware,
    find_matching_brace,
    find_declarations_end,
    split_params,
    parse_param_name_and_type,
    printf_format_for_type,
    detect_simple_declaration,
    detect_simple_assignment,
    detect_function_calls,
)


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
    for ln in lines:
        dec = detect_simple_declaration(ln)
        if dec:
            var_name, type_str, _ = dec
            known_types.setdefault(var_name, type_str)

    new_lines: List[str] = []
    declarations_ended = False
    decl_end_idx = find_declarations_end(body)
    char_count = 0

    for ln in lines:
        new_lines.append(ln)
        char_count += len(ln) + 1
        stripped = ln.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = ln[: len(ln) - len(stripped)]
        if not declarations_ended and char_count > decl_end_idx:
            declarations_ended = True
        if not declarations_ended:
            continue
        # Control flow entries, but ignore single-statement if/else-if without braces
        if print_control and re.match(r'^\s*(if|else\s+if|else\b|for|while|switch|case\b|default\b)', strip_line_comment_aware(ln)):
            msg = build_value_log(log_style, f'control in {func_name}', '%s', '"' + stripped.split('{')[0].strip().replace('"', '\\"') + '"', device_expr, is_kernel_driver)
            # Detect brace presence for if/else-if; if missing and next non-empty line does not start with '{', skip
            header_core = strip_line_comment_aware(ln).strip()
            is_if_like = header_core.startswith('if') or header_core.startswith('else if')
            has_open_brace = '{' in ln
            # if is_if_like and not has_open_brace:
            #     # Peek ahead to the next non-empty logical line
            #     # If the next significant line starts with '{', we allow, else skip
            #     # (simple heuristic; avoids clutter on single-statement ifs)
            #     pass  # Do not add msg for single-statement if without '{'
            # else:
            #     new_lines.append(indent + msg)
            if not (is_if_like and not has_open_brace):
                new_lines.append(indent + msg)
        if print_decls and declarations_ended:
            dec = detect_simple_declaration(ln)
            if dec:
                var_name, type_str, has_init = dec
                if has_init:
                    fmt = printf_format_for_type(type_str)
                    new_lines.append(indent + build_value_log(log_style, var_name, fmt, var_name, device_expr, is_kernel_driver))
        if print_assigns and declarations_ended:
            asg = detect_simple_assignment(ln)
            if asg:
                var_name, op = asg
                type_str = known_types.get(var_name, '')
                fmt = printf_format_for_type(type_str)
                new_lines.append(indent + build_value_log(log_style, var_name, fmt, var_name, device_expr, is_kernel_driver))
        if print_calls and declarations_ended:
            calls = detect_function_calls(ln)
            for c in calls:
                new_lines.append(indent + build_value_log(log_style, f'calling {c}', '%s', '""', device_expr, is_kernel_driver))
    return '\n'.join(new_lines)


def insert_exit_before_returns(body: str, exit_line_builder: str, default_indent: str, log_style: str, device_expr: str, is_kernel_driver: bool, log_return_value: bool = True) -> str:
    i = 0
    res: List[str] = []
    in_line_comment = False
    in_block_comment = False
    in_string = False
    in_char = False
    string_delim = ''

    def append_exit_and_return_value(return_expr: str):
        joined = ''.join(res)
        if not joined.endswith('\n'):
            res.append('\n')
        res.append(default_indent)
        res.append(exit_line_builder)
        res.append('\n')
        if return_expr.strip() and log_return_value:
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
        if ch in ('"', "'"):
            res.append(ch)
            if ch == '"':
                in_string = True
                string_delim = '"'
            else:
                in_char = True
            i += 1
            continue
        if body.startswith('return', i):
            before = body[i - 1] if i > 0 else ' '
            after = body[i + 6] if i + 6 < len(body) else ' '
            if not (before.isalnum() or before == '_') and not (after.isalnum() or after == '_'):
                # Determine if this return is part of a single-statement control without braces,
                # e.g., "if (cond) return x;" or "else return;". If so, skip inserting exit here
                # to preserve semantics of the control structure.
                line_start = body.rfind('\n', 0, i) + 1
                semicolon_end = body.find(';', i)
                stmt_slice_end = semicolon_end if semicolon_end != -1 else i
                line_to_return = body[line_start:i].lstrip()
                single_stmt_control = False
                # Match patterns like: if (...) return, else if (...) return, else return, for/while (...) return, switch(...) return
                if re.search(r'^(?:if\s*\([^)]*\)|else\s+if\s*\([^)]*\)|else\b|for\s*\([^)]*\)|while\s*\([^)]*\)|switch\s*\([^)]*\))\s*$', line_to_return):
                    single_stmt_control = True
                # Also handle compact same-line pattern: if (...) return ...; (no opening brace before return on same line)
                same_line_prefix = body[line_start:i]
                if not single_stmt_control and re.search(r'\b(if|else\s+if|else|for|while|switch)\b[^\n\{]*$', same_line_prefix) and '{' not in same_line_prefix:
                    single_stmt_control = True
                # NEW: handle common two-line pattern where the control header is on the
                # previous non-empty line, followed by a single "return ...;" line.
                if not single_stmt_control:
                    # Find previous significant (non-empty, non-preprocessor) line
                    search_pos = line_start
                    # Walk backwards up to 5 logical lines looking for a control header without '{'
                    for _ in range(5):
                        prev_nl = body.rfind('\n', 0, max(0, search_pos - 1))
                        prev_line_start = prev_nl + 1 if prev_nl != -1 else 0
                        prev_line_raw = body[prev_line_start:search_pos]
                        search_pos = prev_line_start
                        prev_line = prev_line_raw.strip()
                        if not prev_line:
                            continue
                        prev_core = strip_line_comment_aware(prev_line)
                        if not prev_core or prev_core.startswith('#'):
                            continue
                        # Stop if we hit a block/opening brace before finding a header
                        if '{' in prev_core or prev_core.endswith(';'):
                            break
                        if re.match(r'^(?:if\s*\([^)]*\)|else\s+if\s*\([^)]*\)|else\b|for\s*\([^)]*\)|while\s*\([^)]*\)|switch\s*\([^)]*\))\s*(?!\{)\s*$', prev_core):
                            single_stmt_control = True
                            break
                if not single_stmt_control:
                    return_start = i + 6
                    return_end = body.find(';', return_start)
                    if return_end != -1:
                        return_expr = body[return_start:return_end].strip()
                        append_exit_and_return_value(return_expr)
        res.append(ch)
        i += 1
    return ''.join(res)


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
        open_brace_index = code.find('{', header_start, header_end)
        if open_brace_index == -1:
            continue
        close_brace_index = find_matching_brace(code, open_brace_index)
        if close_brace_index == -1:
            continue
        result_parts.append(code[last_index:open_brace_index + 1])
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
        body = code[open_brace_index + 1:close_brace_index]
        already_instrumented = (f'entered function {func_name}' in body) or (f'exiting function {func_name}' in body)
        new_body = body
        if not already_instrumented:
            decl_end_idx = find_declarations_end(body)
            # Robust C90 placement: recompute a conservative declaration region
            # at the top of the block regardless of the initial detector's result.
            lines = body.split('\n')
            last_decl_line = -1
            primitive_or_known_types = (
                r'(?:void|bool|_Bool|char|short|int|long|float|double|size_t|ssize_t|u8|u16|u32|u64|s8|s16|s32|s64|dma_addr_t|uintptr_t|intptr_t)'
            )
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped or stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*'):
                    continue
                core = strip_line_comment_aware(line)
                dec = detect_simple_declaration(core)
                if dec:
                    last_decl_line = i
                    continue
                # Fallback heuristic similar to parsing_utils.find_declarations_end
                # Allow pointer stars adjacent to identifier: e.g., "*xpdev"
                if re.match(rf'^\s*(?:const\s+|volatile\s+|static\s+)?(?:struct\s+\w+|union\s+\w+|enum\s+\w+|{primitive_or_known_types})\s*(?:\*+\s*)?[A-Za-z_]\w*\s*(?:;|=)', core) and not re.search(r'\([^)]*\)', core):
                    last_decl_line = i
                    continue
                # first non-declaration statement ends the declaration block
                break
            if last_decl_line >= 0:
                char_index = 0
                for j in range(last_decl_line + 1):
                    if j < len(lines):
                        char_index += len(lines[j]) + 1
                # Use the max to ensure we don't insert before declarations
                decl_end_idx = max(decl_end_idx, char_index)
            # Guard against incorrect end index pointing to or past the end of body
            if decl_end_idx <= 0 or decl_end_idx >= len(body):
                decl_part = ""
                code_part = body
            else:
                decl_part = body[:decl_end_idx]
                code_part = body[decl_end_idx:]
            instrumentation_lines: List[str] = []
            if add_entry_exit:
                instrumentation_lines.append(f"{base_indent}{entry_line}")
            known_types: Dict[str, str] = {}
            if print_params and params_src.strip() and params_src.strip() != 'void':
                for raw in split_params(params_src):
                    parsed = parse_param_name_and_type(raw)
                    if not parsed:
                        continue
                    pname, ptype = parsed
                    known_types[pname] = ptype
                    # Choose safer default for integers vs pointers/strings
                    fmt = printf_format_for_type(ptype)
                    instrumentation_lines.append(f"{base_indent}{build_value_log(log_style, pname, fmt, pname, device_expr, is_kernel_driver)}")
            # Insert a clean block after declarations only
            instrumentation_block = ('\n' if instrumentation_lines else '') + '\n'.join(instrumentation_lines) + ('\n' if instrumentation_lines else '')
            if decl_part:
                new_body = decl_part + instrumentation_block + code_part
            else:
                new_body = instrumentation_block + code_part
            # If entry/exit is requested, ensure exits are injected before returns even if the
            # caller did not explicitly enable add_exit_before_returns.
            if add_exit_before_returns or add_entry_exit:
                # Only log return values if add_exit_before_returns is True
                new_body = insert_exit_before_returns(new_body, exit_line, base_indent, log_style, device_expr, is_kernel_driver, log_return_value=add_exit_before_returns)
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
            if final_exit_always:
                # If the last non-empty, non-comment line is a return statement,
                # insert the exit log just before that return to avoid unreachable code.
                lines = new_body.rstrip().split('\n')
                # Find last non-empty, non-comment line
                idx = len(lines) - 1
                while idx >= 0 and not strip_line_comment_aware(lines[idx]).strip():
                    idx -= 1
                if idx >= 0 and re.match(r'\s*return\b', strip_line_comment_aware(lines[idx]).strip()):
                    # Insert before this line
                    lines.insert(idx, f"{base_indent}{exit_line}")
                    new_body = '\n'.join(lines)
                else:
                    # Append at end
                    if not new_body.endswith('\n'):
                        new_body += '\n'
                    new_body += f"{base_indent}{exit_line}\n"
        result_parts.append(new_body)
        result_parts.append('}')
        last_index = close_brace_index + 1
    result_parts.append(code[last_index:])
    return ''.join(result_parts)




