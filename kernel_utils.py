from typing import Dict


def add_kernel_includes(code: str, is_kernel_driver: bool) -> str:
    """Add necessary kernel includes if this is kernel driver code"""
    if not is_kernel_driver:
        return code
    if '#include <linux/kernel.h>' in code:
        return code
    lines = code.split('\n')
    insert_index = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('#include'):
            insert_index = i + 1
        elif line.strip() and not line.strip().startswith('//') and not line.strip().startswith('/*'):
            break
    kernel_includes = [
        '#include <linux/kernel.h>',
        '#include <linux/module.h>',
        '#include <linux/kthread.h>'
    ]
    lines[insert_index:insert_index] = kernel_includes
    return '\n'.join(lines)


