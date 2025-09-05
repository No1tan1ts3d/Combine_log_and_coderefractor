import streamlit as st
import re
import zlib
import base64

# --------------------------
# PlantUML URL Generator
# --------------------------
def get_plantuml_image_url(uml_code, server="http://www.plantuml.com/plantuml/png/"):
    def encode_plantuml(text):
        data = text.encode('utf-8')
        compressed = zlib.compress(data)[2:-4]  # strip zlib header/footer
        return encode_base64(compressed)

    def encode_base64(data):
        alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
        result = ''
        i = 0
        while i < len(data):
            b1 = data[i]
            b2 = data[i + 1] if i + 1 < len(data) else 0
            b3 = data[i + 2] if i + 2 < len(data) else 0
            result += alphabet[b1 >> 2]
            result += alphabet[((b1 & 0x3) << 4) | (b2 >> 4)]
            result += alphabet[((b2 & 0xF) << 2) | (b3 >> 6)]
            result += alphabet[b3 & 0x3F]
            i += 3
        return result

    encoded = encode_plantuml(uml_code)
    return server + encoded

# --------------------------
# Enhanced Log Parsers for QDMA Format
# --------------------------

def parse_qdma_log_line(line):
    """Parse QDMA log line to extract function name and action type"""
    # Pattern for QDMA log format: [timestamp] module:function: ----- QDMA entering/exiting the function_name function at path [Thread ID: xxx] -----
    qdma_pattern = r'\[[\d.]+\]\s+(\w+):(\w+):\s+----- QDMA (entering|exiting) the (\w+) function at.*?\[Thread ID: (\d+)\]'
    
    # Alternative pattern for simpler QDMA logs
    simple_pattern = r'\[[\d.]+\]\s+(\w+):(\w+):\s+(.+)$'
    
    # Command pattern
    command_pattern = r'\[[\d.]+\]\s+Command:\s+(.+)$'
    
    match = re.search(qdma_pattern, line)
    if match:
        module, caller_func, action, func_name, thread_id = match.groups()
        return {
            'module': module,
            'caller_func': caller_func,
            'function': func_name,
            'action': action,
            'thread_id': thread_id,
            'full_line': line.strip()
        }
    
    match = re.search(simple_pattern, line)
    if match:
        module, func_name, message = match.groups()
        return {
            'module': module,
            'caller_func': func_name,
            'function': func_name,
            'action': 'info',
            'thread_id': None,
            'message': message,
            'full_line': line.strip()
        }
    
    match = re.search(command_pattern, line)
    if match:
        command = match.group(1)
        return {
            'module': 'system',
            'caller_func': 'command',
            'function': 'command',
            'action': 'command',
            'thread_id': None,
            'message': command,
            'full_line': line.strip()
        }
    
    return None

# def parse_qdma_log_to_puml(log_lines):
#     """Generate PlantUML sequence diagram for QDMA logs"""
#     plantuml_lines = ["@startuml"]
#     plantuml_lines.append("title QDMA Driver Function Call Sequence")
#     plantuml_lines.append("participant User")
    
#     participants = set(["User"])
#     call_stack = []
    
#     for line in log_lines:
#         parsed = parse_qdma_log_line(line)
#         if not parsed:
#             continue
            
#         func_name = parsed['function']
#         action = parsed['action']
#         module = parsed['module']
        
#         # Add participant if new
#         if func_name not in participants:
#             plantuml_lines.append(f"participant {func_name}")
#             participants.add(func_name)
        
#         if action == 'entering':
#             if call_stack:
#                 caller = call_stack[-1]
#                 plantuml_lines.append(f"{caller}->{func_name}: call")
#             else:
#                 plantuml_lines.append(f"User->{func_name}: call")
#             call_stack.append(func_name)
            
#         elif action == 'exiting':
#             if call_stack and call_stack[-1] == func_name:
#                 call_stack.pop()
#                 if call_stack:
#                     caller = call_stack[-1]
#                     plantuml_lines.append(f"{func_name}-->{caller}: return")
#                 else:
#                     plantuml_lines.append(f"{func_name}-->User: return")
                    
#         elif action == 'command':
#             plantuml_lines.append(f"note over User: {parsed.get('message', '')}")
            
#         elif action == 'info':
#             if parsed.get('message'):
#                 plantuml_lines.append(f"note right of {func_name}: {parsed['message'][:50]}...")
    
#     plantuml_lines.append("@enduml")
#     return "\n".join(plantuml_lines)


def parse_qdma_log_to_puml(log_lines):
    """Generate PlantUML sequence diagram for QDMA logs"""
    plantuml_lines = ["@startuml"]
    plantuml_lines.append("title QDMA Driver Function Call Sequence")
    plantuml_lines.append("participant User")
    
    participants = set(["User"])
    call_stack = []
    
    for line in log_lines:
        parsed = parse_qdma_log_line(line)
        if not parsed:
            continue
            
        func_name = parsed['function']
        action = parsed['action']
        module = parsed['module']
        
        # Add participant if new
        if func_name not in participants:
            plantuml_lines.append(f"participant {func_name}")
            participants.add(func_name)
        
        if action == 'entering':
            if call_stack:
                caller = call_stack[-1]
                # FIX: Used the dynamic 'action' variable instead of hardcoded "call"
                plantuml_lines.append(f"{caller}->{func_name}: {action}")
            else:
                # FIX: Used the dynamic 'action' variable instead of hardcoded "call"
                plantuml_lines.append(f"User->{func_name}: {action}")
            call_stack.append(func_name)
            
        elif action == 'exiting':
            if call_stack and call_stack[-1] == func_name:
                call_stack.pop()
                if call_stack:
                    caller = call_stack[-1]
                    # FIX: Used the dynamic 'action' variable instead of hardcoded "return"
                    plantuml_lines.append(f"{func_name}-->{caller}: {action}")
                else:
                    # FIX: Used the dynamic 'action' variable instead of hardcoded "return"
                    plantuml_lines.append(f"{func_name}-->User: {action}")
                    
        elif action == 'command':
            plantuml_lines.append(f"note over User: {parsed.get('message', '')}")
            
        elif action == 'info':
            if parsed.get('message'):
                plantuml_lines.append(f"note right of {func_name}: {parsed['message'][:50]}...")
    
    plantuml_lines.append("@enduml")
    return "\n".join(plantuml_lines)

def parse_qdma_log_to_activity_puml(log_lines):
    """Generate PlantUML activity diagram for QDMA logs"""
    plantuml_lines = ["@startuml"]
    plantuml_lines.append("title QDMA Driver Activity Flow")
    plantuml_lines.append("start")
    
    for line in log_lines:
        parsed = parse_qdma_log_line(line)
        if not parsed:
            continue
            
        func_name = parsed['function']
        action = parsed['action']
        
        if action == 'entering':
            plantuml_lines.append(f":Enter {func_name};")
        elif action == 'exiting':
            plantuml_lines.append(f":Exit {func_name};")
        elif action == 'command':
            plantuml_lines.append(f":Execute Command\\n{parsed.get('message', '')[:30]}...;")
        elif action == 'info' and parsed.get('message'):
            plantuml_lines.append(f"note right: {parsed['message'][:40]}...")
    
    plantuml_lines.append("stop")
    plantuml_lines.append("@enduml")
    return "\n".join(plantuml_lines)

def parse_qdma_log_to_component_puml(log_lines):
    """Generate PlantUML component diagram for QDMA logs"""
    plantuml_lines = ["@startuml"]
    plantuml_lines.append("title QDMA Driver Component Interaction")
    
    modules = set()
    functions = set()
    interactions = set()
    
    for line in log_lines:
        parsed = parse_qdma_log_line(line)
        if not parsed:
            continue
            
        module = parsed['module']
        func_name = parsed['function']
        
        modules.add(module)
        functions.add(func_name)
        
        if parsed['action'] == 'entering':
            interactions.add((module, func_name))
    
    # Add components
    for module in sorted(modules):
        plantuml_lines.append(f"package {module} {{")
        module_functions = [parse_qdma_log_line(line) for line in log_lines 
                          if parse_qdma_log_line(line) and parse_qdma_log_line(line)['module'] == module]
        unique_funcs = set(parsed['function'] for parsed in module_functions if parsed)
        for func in sorted(unique_funcs):
            plantuml_lines.append(f"  component {func}")
        plantuml_lines.append("}")
    
    # Add interactions
    prev_func = None
    for line in log_lines:
        parsed = parse_qdma_log_line(line)
        if parsed and parsed['action'] == 'entering':
            if prev_func:
                plantuml_lines.append(f"{prev_func} --> {parsed['function']}")
            prev_func = parsed['function']
    
    plantuml_lines.append("@enduml")
    return "\n".join(plantuml_lines)

# --------------------------
# Legacy parsers for backward compatibility
# --------------------------

def parse_log_to_puml(log_lines):
    plantuml_lines = ["@startuml", "participant Caller"]
    participants = set(["Caller"])

    for line in log_lines:
        line = line.strip()
        match = re.search(r"\bFunction (\w+)\b.*?\b(entering|command|info|exiting|called|completed|error|retry|skipped)\b", line, re.IGNORECASE)
        if match:
            fn = match.group(1)
            action = match.group(2).lower()

            if fn not in participants:
                plantuml_lines.append(f"participant {fn}")
                participants.add(fn)

            if action in ["entering", "called", "command", "retry"]:
                plantuml_lines.append(f"Caller -> {fn}: {action}")
            elif action in ["exiting", "completed"]:
                plantuml_lines.append(f"{fn} --> Caller: {action}")
            elif action in ["info", "error"]:
                plantuml_lines.append(f"note right of {fn}: {action.upper()}")
            elif action == "skipped":
                plantuml_lines.append(f"note right of Caller: Skipped {fn}")
        else:
            plantuml_lines.append(f"note right of Caller: {line}")

    plantuml_lines.append("@enduml")
    return "\n".join(plantuml_lines)


def parse_log_to_activity_puml(log_lines):
    """Legacy activity parser"""
    plantuml_lines = ["@startuml", "start"]
    for line in log_lines:
        line = line.strip()
        if "is called" in line:
            fn = re.search(r"Function (\w+) is called", line)
            if fn:
                plantuml_lines.append(f":Call {fn.group(1)};")
        elif "is completed" in line:
            fn = re.search(r"Function (\w+) is completed", line)
            if fn:
                plantuml_lines.append(f":Complete {fn.group(1)};")
        elif "caused error" in line:
            fn = re.search(r"Function (\w+) caused error", line)
            if fn:
                plantuml_lines.append(f"note right: {fn.group(1)} error")
        elif "is skipped" in line:
            fn = re.search(r"Function (\w+) is skipped", line)
            if fn:
                plantuml_lines.append(f"note right: {fn.group(1)} skipped")
        elif "Retrying Function" in line:
            fn = re.search(r"Retrying Function (\w+)", line)
            if fn:
                plantuml_lines.append(f":Retry {fn.group(1)};")
        else:
            plantuml_lines.append(f"note right: {line[:30]}...")
    plantuml_lines.append("stop")
    plantuml_lines.append("@enduml")
    return "\n".join(plantuml_lines)

def parse_log_to_component_puml(log_lines):
    """Legacy component parser"""
    plantuml_lines = ["@startuml"]
    components = set()
    for line in log_lines:
        fn = re.search(r"Function (\w+)", line)
        if fn:
            components.add(fn.group(1))
    for comp in components:
        plantuml_lines.append(f"component {comp}")
    for line in log_lines:
        call = re.search(r"Function (\w+) is called", line)
        complete = re.search(r"Function (\w+) is completed", line)
        if call and complete:
            plantuml_lines.append(f"{call.group(1)} --> {complete.group(1)}")
    plantuml_lines.append("@enduml")
    return "\n".join(plantuml_lines)

# --------------------------
# Auto-detect log format
# --------------------------

def detect_log_format(log_lines):
    """Detect if logs are QDMA format or legacy format"""
    qdma_indicators = 0
    legacy_indicators = 0
    
    for line in log_lines[:10]:  # Check first 10 lines
        if 'qdma_pf:' in line and 'QDMA entering' in line or 'QDMA exiting' in line:
            qdma_indicators += 1
        elif 'Function' in line and ('is called' in line or 'is completed' in line):
            legacy_indicators += 1
    
    return "qdma" if qdma_indicators > legacy_indicators else "legacy"

# --------------------------
# Streamlit UI
# --------------------------
st.set_page_config(page_title="Enhanced Log Diagram Visualizer", layout="wide")
st.title("📊 Enhanced Log File to Diagram Visualizer")
st.write("Upload or paste your log file below to generate a visual diagram. Supports QDMA driver logs.")

# Input options
uploaded_file = st.file_uploader("Upload log file", type=["txt", "log"])
log_text = st.text_area("Or paste log content here", height=200)

diagram_type = st.radio(
    "Select diagram type:",
    ("Sequence Diagram", "Activity Diagram", "Component Diagram")
)

submit = st.button("🔍 Generate Diagram")

if (uploaded_file or log_text) and submit:
    if uploaded_file:
        log_lines = uploaded_file.read().decode("utf-8").splitlines()
    else:
        log_lines = log_text.splitlines()

    st.session_state['log_lines'] = log_lines
    st.session_state['diagram_type'] = diagram_type
    
    # Auto-detect log format
    log_format = detect_log_format(log_lines)
    st.session_state['log_format'] = log_format
    
    st.info(f"Detected log format: {log_format.upper()}")

    # Generate PlantUML code based on format
    if log_format == "qdma":
        if diagram_type == "Sequence Diagram":
            puml_content = parse_qdma_log_to_puml(log_lines)
        elif diagram_type == "Activity Diagram":
            puml_content = parse_qdma_log_to_activity_puml(log_lines)
        elif diagram_type == "Component Diagram":
            puml_content = parse_qdma_log_to_component_puml(log_lines)
    else:  # legacy format
        if diagram_type == "Sequence Diagram":
            puml_content = parse_log_to_puml(log_lines)
        elif diagram_type == "Activity Diagram":
            puml_content = parse_log_to_activity_puml(log_lines)
        elif diagram_type == "Component Diagram":
            puml_content = parse_log_to_component_puml(log_lines)

    # Display diagram
    if puml_content:
        image_url = get_plantuml_image_url(puml_content)
        st.image(image_url, caption=f"Generated {diagram_type}", use_container_width=True)
        # col1, col2 = st.columns([2, 1])
        
        # with col1:
        #     st.image(image_url, caption=f"Generated {diagram_type}", use_container_width=True)
        
        # with col2:
        #     st.subheader("PlantUML Code")
        #     st.code(puml_content, language="text")
            
            # Download button for PlantUML code
            # st.download_button(
            #     label="📥 Download PlantUML Code",
            #     data=puml_content,
            #     file_name=f"{diagram_type.lower().replace(' ', '_')}.puml",
            #     mime="text/plain"
            # )
else:
    st.info("📂 Please upload a log file or paste log content, select diagram type, and click Generate Diagram.")

# --- Enhanced Filtering options (shown only after diagram is generated) ---
if 'log_lines' in st.session_state and 'diagram_type' in st.session_state:
    log_lines = st.session_state['log_lines']
    diagram_type = st.session_state['diagram_type']
    log_format = st.session_state.get('log_format', 'legacy')

    # Extract functions and actions from the actual log
    function_set = set()
    module_set = set()
    action_set = set()
    thread_set = set()

    for line in log_lines:
        if log_format == "qdma":
            parsed = parse_qdma_log_line(line)
            if parsed:
                function_set.add(parsed['function'])
                module_set.add(parsed['module'])
                action_set.add(parsed['action'])  # This will now collect actual actions from the log
                if parsed['thread_id']:
                    thread_set.add(parsed['thread_id'])
        else:
            # Legacy format parsing
            fn_match = re.search(r"Function (\w+)", line)
            if fn_match:
                function_set.add(fn_match.group(1))
            
            # Extract actual action from the log line
            action_match = re.search(r"\b(entering|exiting|command|info|called|completed|error|retry|skipped)\b", line, re.IGNORECASE)
            if action_match:
                action_set.add(action_match.group(1).lower())

    with st.expander("🔍 Advanced Filter Options", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            selected_functions = st.multiselect(
                "Filter by Functions", 
                sorted(function_set), 
                default=list(sorted(function_set))[:10] if len(function_set) > 10 else list(function_set),
                help="Select specific functions to include in the diagram"
            )

        with col2:
            if log_format == "qdma":
                selected_modules = st.multiselect(
                    "Filter by Modules", 
                    sorted(module_set), 
                    default=list(module_set),
                    help="Select QDMA modules to include"
                )
            else:
                selected_modules = []

        with col3:
            selected_actions = st.multiselect(
                "Filter by Actions", 
                sorted(action_set), 
                default=list(action_set),
                help="Select action types to include"
            )

        if log_format == "qdma" and thread_set:
            selected_threads = st.multiselect(
                "Filter by Thread ID", 
                sorted(thread_set), 
                default=list(thread_set),
                help="Select specific thread IDs"
            )
        else:
            selected_threads = []

        filter_submit = st.button("🎯 Generate Filtered Diagram")

    if filter_submit:
        # Filter log lines based on selections
        filtered_lines = []
        for line in log_lines:
            if log_format == "qdma":
                parsed = parse_qdma_log_line(line)
                if parsed:
                    include_line = True
                    
                    if selected_functions and parsed['function'] not in selected_functions:
                        include_line = False
                    if selected_modules and parsed['module'] not in selected_modules:
                        include_line = False
                    if selected_actions and parsed['action'] not in selected_actions:
                        include_line = False
                    if selected_threads and parsed['thread_id'] and parsed['thread_id'] not in selected_threads:
                        include_line = False
                    
                    if include_line:
                        filtered_lines.append(line)
            else:
                # Legacy format filtering
                fn_match = re.search(r"Function (\w+)", line)
                fn_name = fn_match.group(1) if fn_match else None

                line_action = None
                if "is called" in line:
                    line_action = "is called"
                elif "is completed" in line:
                    line_action = "is completed"
                elif "caused error" in line:
                    line_action = "caused error"
                elif "is skipped" in line:
                    line_action = "is skipped"
                elif "Retrying Function" in line:
                    line_action = "Retrying"

                if (not selected_functions or (fn_name and fn_name in selected_functions)) and \
                   (not selected_actions or (line_action and line_action in selected_actions)):
                    filtered_lines.append(line)

        # Regenerate diagram with filtered lines
        if log_format == "qdma":
            if diagram_type == "Sequence Diagram":
                filtered_puml = parse_qdma_log_to_puml(filtered_lines)
            elif diagram_type == "Activity Diagram":
                filtered_puml = parse_qdma_log_to_activity_puml(filtered_lines)
            elif diagram_type == "Component Diagram":
                filtered_puml = parse_qdma_log_to_component_puml(filtered_lines)
        else:
            if diagram_type == "Sequence Diagram":
                filtered_puml = parse_log_to_puml(filtered_lines)
            elif diagram_type == "Activity Diagram":
                filtered_puml = parse_log_to_activity_puml(filtered_lines)
            elif diagram_type == "Component Diagram":
                filtered_puml = parse_log_to_component_puml(filtered_lines)

        if filtered_puml:
            image_url = get_plantuml_image_url(filtered_puml)
            st.subheader("🎯 Filtered Diagram")
            st.image(image_url, caption=f"Filtered {diagram_type}", use_container_width=True)
            
            # col1, col2 = st.columns([2, 1])
            # with col1:
            #     st.image(image_url, caption=f"Filtered {diagram_type}", use_container_width=True)
            # with col2:
            #     st.code(filtered_puml, language="text")
            #     st.download_button(
            #         label="📥 Download Filtered PlantUML",
            #         data=filtered_puml,
            #         file_name=f"filtered_{diagram_type.lower().replace(' ', '_')}.puml",
            #         mime="text/plain"
            #     )
