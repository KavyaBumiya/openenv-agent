#!/usr/bin/env python3
"""
Launch script for the Streamlit UI

Usage:
    python launch_streamlit.py          # Run normally
    python launch_streamlit.py --dev    # Run with debug logging
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch the Streamlit application."""
    
    # Get project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check if Streamlit is installed
    try:
        import streamlit
    except ImportError:
        print("❌ Streamlit is not installed!")
        print("\nInstall with:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    
    # Build command
    cmd = [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"]
    
    # Add debug flag if requested
    if "--dev" in sys.argv or "--debug" in sys.argv:
        cmd.extend(["--logger.level=debug", "--client.toolbarMode=developer"])
        print("🔧 Running in development mode...")
    else:
        print("🚀 Starting Streamlit UI...")
    
    print(f"📍 Project root: {project_root}")
    print(f"🌐 App will be available at: http://localhost:8501")
    print("\nPress Ctrl+C to stop\n")
    
    # Run Streamlit
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n👋 Streamlit app stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
