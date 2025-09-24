import re
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


