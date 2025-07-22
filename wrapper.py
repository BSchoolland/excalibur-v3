#!/usr/bin/env python3
import os
import sys
import subprocess

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the virtual environment
venv_python = os.path.join(script_dir, 'venv', 'bin', 'python')

# Path to the actual MCP server
mcp_server = os.path.join(script_dir, 'mcp_server.py')

# If virtual environment exists, use it; otherwise use system python
if os.path.exists(venv_python):
    # Run the MCP server with the virtual environment Python
    os.execv(venv_python, [venv_python, mcp_server] + sys.argv[1:])
else:
    # Fall back to system python
    os.execv(sys.executable, [sys.executable, mcp_server] + sys.argv[1:]) 