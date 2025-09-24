import streamlit as st
from instrumentation import add_debug_statements
from kernel_utils import add_kernel_includes
from zip_utils import create_zip_download


# ---- Streamlit UI ----

st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
    .stDownloadButton > button {
        padding: 0.55rem 1rem;
        border-radius: 8px;
        font-weight: 600;
    }
    .form-hint { color: rgba(120,120,120,0.95); font-size: 0.9rem; }
    .section { padding: 0.2rem 0.4rem; border: 1px solid rgba(150,150,150,0.15); border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("C/C++ Code Refractor")

st.write(
    "Paste your C/C++ code or upload files. The app instruments function entry/exit, parameters, "
    "declarations, assignments, and calls while ensuring C90 compliance by placing debug statements "
    "after variable declarations."

)
st.write("Developed and Modified by Manjil. Tool update date: 2025-09-24")

st.divider()

# Input method
input_method = st.radio("Choose input method:", ("Paste code", "Upload file"))

code = ""
if input_method == "Paste code":
    code = st.text_area("Paste your C/C++ code here:", height=240)

# Instrumentation Context & Logging options (compact panel)
st.subheader("Configuration")
with st.container():
    cfg_col1, cfg_col2 = st.columns(2)
    with cfg_col1:
        st.markdown("**Context**")
        mode = st.toggle("Kernel Driver Mode (QDMA)", value=False, help="Enable kernel-friendly logging & C90 placement")
        is_kernel_driver = mode
        st.caption(f"Selected Mode: {'Kernel Driver Code (C90 Compliant)' if is_kernel_driver else 'User Space Code'}")
    with cfg_col2:
        st.markdown("**Logging**")
        if is_kernel_driver:
            log_style = st.selectbox("Statement type", ["printk", "pr_info", "pr_debug", "dev_dbg"], index=0)
        else:
            log_style = st.selectbox("Statement type", ["printf", "pr_debug", "dev_dbg"], index=0)
        device_expr = ""
        if log_style == "dev_dbg":
            device_expr = st.text_input(
                "dev_dbg device expression",
                value="port->dev",
                placeholder="port->dev",
                help="Expression resolving to the device (e.g., port->dev)"
            )
st.divider()

# Logging style options
st.subheader("Instrumentation toggles")

# Multi-select quick selections to combine categories
quick_choices = st.multiselect(
    "Quick selections (choose one or more). Default/ No selection toggles all categories",
    [
        "Function entry/exit",
        "Variables (params/decls/assigns/calls)",
        "Control-flow entry/exit (if/while)",
    ],
    default=[],
    help="Select categories to quickly configure; you can still tweak individual options below.",
)

# Base granular options (defaults) arranged in two columns
tog_l, tog_r = st.columns(2)
with tog_l:
    add_entry_exit = st.checkbox("Add entry/exit logs", value=True)
    add_exit_before_returns = st.checkbox("Add exit before each return", value=True)
    final_exit_always = st.checkbox("Always append a final exit log", value=True)
with tog_r:
    print_params = st.checkbox("Print parameter values at entry", value=True)
    print_decls = st.checkbox("Print initial values for simple declarations", value=True)
    print_assigns = st.checkbox("Print values after simple assignments", value=True)
    print_calls = st.checkbox("Print when calling functions (best-effort)", value=True)
    print_control = st.checkbox("Print control-flow entries (if/for/while/switch)", value=False)

# If any quick selections chosen, start from all-off, then enable chosen categories
if quick_choices:
    add_entry_exit = False
    add_exit_before_returns = False
    print_params = False
    print_decls = False
    print_assigns = False
    print_calls = False
    print_control = False

    if "Function entry/exit" in quick_choices:
        add_entry_exit = True
        add_exit_before_returns = True
    if "Variables (params/decls/assigns/calls)" in quick_choices:
        print_params = True
        print_decls = True
        print_assigns = True
        print_calls = True
    if "Control-flow entry/exit (if/while)" in quick_choices:
        print_control = True

# Single file processing
if input_method == "Paste code" and code:
    original_code = code  # keep pristine for display
    code_to_process = add_kernel_includes(code, is_kernel_driver) if is_kernel_driver else code

    modified_code = add_debug_statements(
        code_to_process,
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
        st.code(original_code, language="cpp")
    
    with col2:
        st.subheader("Modified Code with Debug Prints:")
        st.download_button(
            label="⬇️ Download Modified (modified.c)",
            data=modified_code,
            file_name="modified.c",
            mime="text/x-c",
            type="primary",
            help="Download the instrumented code"
        )
        st.code(modified_code, language="cpp")

# File upload processing
elif input_method == "Upload file":
    uploaded_files = st.file_uploader("Choose C/C++ files", type=["c", "cpp", "h", "hpp"], accept_multiple_files=True)
    
    if uploaded_files:
        modified_files = {}
        
        # Process all files
        for file in uploaded_files:
            file_bytes = file.read()
            original_code = file_bytes.decode("utf-8", errors="ignore")
            code_to_process = add_kernel_includes(original_code, is_kernel_driver) if is_kernel_driver else original_code

            modified_code = add_debug_statements(
                code_to_process,
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
            
            modified_files[f"modified_{file.name}"] = modified_code
            # also store original for later display in tabs
            modified_files[f"original_{file.name}"] = original_code
        
        # Bulk download button
        if len(modified_files) > 1:
            st.subheader("Bulk Download")
            zip_data = create_zip_download(modified_files)
            st.download_button(
                label=f"📦 Download All Modified Files ({len(modified_files)} files)",
                data=zip_data,
                file_name="modified_code_files.zip",
                mime="application/zip",
                type="primary"
            )
            st.write("---")
        
        # Display files in tabs
        if len(uploaded_files) == 1:
            file = uploaded_files[0]
            original_code = modified_files.get(f"original_{file.name}", "")
            code_to_process = add_kernel_includes(original_code, is_kernel_driver) if is_kernel_driver else original_code

            modified_code = add_debug_statements(
                code_to_process,
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
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader(f"Original Code - {file.name}")
                st.code(original_code, language="cpp")
            
            with col2:
                st.subheader(f"Modified Code - {file.name}")
                st.download_button(
                    label=f"⬇️ Download Modified ({file.name})",
                    data=modified_code,
                    file_name=f"modified_{file.name}",
                    mime="text/x-c",
                    type="primary",
                    help="Download the instrumented file",
                )
                st.code(modified_code, language="cpp")
        else:
            file_tabs = st.tabs([f.name for f in uploaded_files])
            for tab, file in zip(file_tabs, uploaded_files):
                with tab:
                    original_code = modified_files.get(f"original_{file.name}", "")
                    modified_code = modified_files[f"modified_{file.name}"]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"Original Code - {file.name}")
                        st.code(original_code, language="cpp")
                    
                    with col2:
                        st.subheader(f"Modified Code - {file.name}")
                        st.download_button(
                            label=f"⬇️ Download Modified ({file.name})",
                            data=modified_code,
                            file_name=f"modified_{file.name}",
                            mime="text/x-c",
                            type="primary",
                            key=f"download_{file.name}",
                            help="Download the instrumented file",
                        )
                        st.code(modified_code, language="cpp")

# Help section
with st.expander("ℹ️ Tool Information"):
    st.markdown("""  
    **How this tool helps:**
    
    ✅ **Analyzes your code** to find where variable declarations end  
    ✅ **Places debug statements** after all declarations in each scope  
    ✅ **Maintains proper formatting** and indentation  
    ✅ **Avoids compilation errors** from mixed declarations and code  
    
    """)



