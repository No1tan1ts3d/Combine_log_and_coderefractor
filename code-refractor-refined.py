import streamlit as st
from rinstrumentation import add_debug_statements
from modules.kernel_utils import add_kernel_includes
from modules.zip_utils import create_zip_download
from modules.zip_handler import extract_zip_files, create_zip_from_dict


# ---- Streamlit UI ----

st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
    .stDownloadButton > button {
        padding: 0.55rem 1rem;
        border-radius: 8px;
        font-weight: 800;
    }
    .form-hint { color: rgba(120,120,120,0.95); font-size: 0.9rem; }
    .section { padding: 0.2rem 0.4rem; border: 1px solid rgba(150,150,150,0.15); border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("C/C++ Code Refractor refined 🛠️")

st.write(
    "Paste your C/C++ code or upload files. The app instruments function entry/exit, parameters, "
    "declarations, assignments, and calls while ensuring C90 compliance by placing debug statements "
    "after variable declarations."
)
st.write("Developed and Modified by Manjil. Tool update date: 2025-10-06")

st.divider()

# Input method
input_method = st.radio("Choose input method:", ("Paste code", "Upload file", "Upload ZIP"))

code = ""
if input_method == "Paste code":
    code = st.text_area("Paste your C/C++ code here:", height=240)

# Configuration Panel
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

# Instrumentation Toggles
st.subheader("Instrumentation toggles")

# Quick selections
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

# Base granular options
tog_l, tog_r = st.columns(2)
with tog_l:
    add_entry_exit = st.checkbox("Add entry/exit logs", value=True)
    add_exit_before_returns = st.checkbox("Add exit before each return", value=True)
    final_exit_always = st.checkbox("Always append a final exit log", value=False)
with tog_r:
    print_params = st.checkbox("Print parameter values at entry", value=False)
    print_decls = st.checkbox("Print initial values for simple declarations", value=False)
    print_assigns = st.checkbox("Print values after simple assignments", value=False)
    print_calls = st.checkbox("Print when calling functions (best-effort)", value=False)
    print_control = st.checkbox("Print control-flow entries (if/for/while/switch)", value=False)

# Override with quick selections if any chosen
if quick_choices:
    add_entry_exit = "Function entry/exit" in quick_choices
    add_exit_before_returns = "Function entry/exit" in quick_choices
    print_params = "Variables (params/decls/assigns/calls)" in quick_choices
    print_decls = "Variables (params/decls/assigns/calls)" in quick_choices
    print_assigns = "Variables (params/decls/assigns/calls)" in quick_choices
    print_calls = "Variables (params/decls/assigns/calls)" in quick_choices
    print_control = "Control-flow entry/exit (if/while)" in quick_choices

st.divider()


def process_code(code_content: str, file_name: str = "code") -> str:
    """Process code with current settings and return instrumented version"""
    code_to_process = add_kernel_includes(code_content, is_kernel_driver) if is_kernel_driver else code_content
    
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
    return modified_code


# ---- PASTE CODE ----
if input_method == "Paste code" and code:
    original_code = code
    modified_code = process_code(code)

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


# ---- FILE UPLOAD ----
elif input_method == "Upload file":
    uploaded_files = st.file_uploader("Choose C/C++ files", type=["c", "cpp", "h", "hpp"], accept_multiple_files=True)
    
    if uploaded_files:
        # Process all files
        processed_files = {}  # {original_name: (original_code, modified_code)}
        
        for file in uploaded_files:
            file_bytes = file.read()
            original_code = file_bytes.decode("utf-8", errors="ignore")
            modified_code = process_code(original_code, file.name)
            processed_files[file.name] = (original_code, modified_code)
        
        # Single file display with side-by-side view
        if len(uploaded_files) == 1:
            file_name = uploaded_files[0].name
            original_code, modified_code = processed_files[file_name]
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader(f"Original Code - {file_name}")
                st.code(original_code, language="cpp")
            
            with col2:
                st.subheader(f"Modified Code - {file_name}")
                st.download_button(
                    label=f"⬇️ Download Modified ({file_name})",
                    data=modified_code,
                    file_name=f"modified_{file_name}",
                    mime="text/x-c",
                    type="primary",
                    help="Download the instrumented file",
                )
                st.code(modified_code, language="cpp")
        
        # Multiple files display with tabs
        else:
            st.subheader("Bulk Download")
            download_dict = {}
            for file_name, (orig, mod) in processed_files.items():
                download_dict[f"modified_{file_name}"] = mod
            
            zip_data = create_zip_download(download_dict)
            st.download_button(
                label=f"📦 Download All Modified Files ({len(processed_files)} files)",
                data=zip_data,
                file_name="modified_code_files.zip",
                mime="application/zip",
                type="primary"
            )
            st.write("---")
            
            # Tabbed view
            file_tabs = st.tabs([f.name for f in uploaded_files])
            for tab, file in zip(file_tabs, uploaded_files):
                with tab:
                    original_code, modified_code = processed_files[file.name]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"Original - {file.name}")
                        st.code(original_code, language="cpp")
                    
                    with col2:
                        st.subheader(f"Modified - {file.name}")
                        st.download_button(
                            label=f"⬇️ Download ({file.name})",
                            data=modified_code,
                            file_name=f"modified_{file.name}",
                            mime="text/x-c",
                            type="primary",
                            key=f"download_{file.name}",
                            help="Download the instrumented file",
                        )
                        st.code(modified_code, language="cpp")


# ---- ZIP FILE UPLOAD ----
elif input_method == "Upload ZIP":
    st.subheader("Upload ZIP File")
    uploaded_zip = st.file_uploader("Choose a ZIP file", type=["zip"])
    
    if uploaded_zip:
        try:
            # Extract zip contents
            zip_bytes = uploaded_zip.read()
            files_dict = extract_zip_files(zip_bytes)
            
            st.success(f"✅ Extracted {len(files_dict)} file(s) from ZIP")
            
            # Process all files
            modified_files = {}
            for filename, original_code in files_dict.items():
                modified_code = process_code(original_code, filename)
                modified_files[filename] = modified_code
            
            # Download section
            st.subheader("Download Modified ZIP")
            zip_data = create_zip_from_dict(modified_files)
            st.download_button(
                label=f"📦 Download Modified ZIP ({len(modified_files)} files)",
                data=zip_data,
                file_name="modified_code.zip",
                mime="application/zip",
                type="primary"
            )
            
            st.divider()
            st.subheader("File Preview")
            
            # Show file list
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Original Files**")
                for fname in files_dict.keys():
                    st.caption(f"📄 {fname}")
            
            with col2:
                st.markdown("**Modified Files (Ready to Download)**")
                for fname in modified_files.keys():
                    st.caption(f"✅ {fname}")
            
            # Optional detailed preview
            with st.expander("👁️ Preview File Contents"):
                selected_file = st.selectbox("Select file to preview:", list(modified_files.keys()))
                if selected_file:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Original: {selected_file}**")
                        st.code(files_dict[selected_file], language="cpp")
                    with col2:
                        st.markdown(f"**Modified: {selected_file}**")
                        st.code(modified_files[selected_file], language="cpp")
        
        except Exception as e:
            st.error(f"❌ Error processing ZIP file: {str(e)}")


# Help section
with st.expander("ℹ️ Tool Information"):
    st.markdown("""  
    **How this tool helps:**
    
    ✅ **Analyzes your code** to find where variable declarations end  
    ✅ **Places debug statements** after all declarations in each scope  
    ✅ **Maintains proper formatting** and indentation  
    ✅ **Avoids compilation errors** from mixed declarations and code  
    
    **Quick Tips:**
    
    • Use **Quick selections** for common instrumentation profiles
    • **Kernel Driver Mode** ensures C90 compliance with proper include guards
    • **Control-flow printing** shows entry to if/while/for blocks (verbose)
    • Process single files for side-by-side comparison
    • Batch process multiple files with bulk download
    """)