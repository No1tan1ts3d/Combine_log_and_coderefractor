import subprocess
import os

def run_streamlit_app():
    file_path = "mainpage.py"
    if os.path.exists(file_path):
        subprocess.run(["streamlit", "run", file_path])
    else:
        print(f"Error: {file_path} not found")

if __name__ == "__main__":
    run_streamlit_app()
