import subprocess
from mcp.server.fastmcp import FastMCP
import asyncio
import logging
import json
import os
import random
import time
from datetime import datetime
import hashlib
import sys
import shlex
import requests
from PIL import ImageGrab
import tempfile
import base64
from dotenv import load_dotenv
import markdown

# Load environment variables
load_dotenv()

# Silence FastMCP debug messages
logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("fastmcp").setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.WARNING)

# Create an enhanced MCP server
mcp = FastMCP("Example MCP Server")

# API configuration
VISION_BASE_URL = 'https://huddleai-apim.azure-api.net/vision/agent/x'
HOCR_BASE_URL = 'https://huddleai-apim.azure-api.net/hocr/v2'
API_KEY = os.getenv('HUDDLE_ML_API_KEY')
HOCR_API_KEY = os.getenv('HUDDLE_API_KEY')

def get_gui_environment():
    """Get environment variables needed for GUI applications"""
    env = os.environ.copy()
    
    # Ensure DISPLAY is set for X11 applications
    if 'DISPLAY' not in env:
        env['DISPLAY'] = ':0'
    
    # For Wayland compatibility
    if 'WAYLAND_DISPLAY' in os.environ:
        env['WAYLAND_DISPLAY'] = os.environ['WAYLAND_DISPLAY']
    
    # XDG environment variables for proper desktop integration
    xdg_vars = ['XDG_CURRENT_DESKTOP', 'XDG_SESSION_TYPE', 'XDG_SESSION_DESKTOP', 
                'XDG_RUNTIME_DIR', 'XDG_DATA_DIRS', 'XDG_CONFIG_DIRS']
    for var in xdg_vars:
        if var in os.environ:
            env[var] = os.environ[var]
    
    # Desktop session variables
    session_vars = ['DESKTOP_SESSION', 'GDMSESSION', 'SESSION_MANAGER']
    for var in session_vars:
        if var in os.environ:
            env[var] = os.environ[var]
    
    # Authentication and security
    auth_vars = ['XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS']
    for var in auth_vars:
        if var in os.environ:
            env[var] = os.environ[var]
    
    return env

@mcp.tool()
def get_projects() -> str:
    """Get all projects on the user's machine (should always call this before opening a project to find the correct name format)"""
    try:
        result = subprocess.run(['pj', '--list'], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error getting projects: {e.stderr}"
    except FileNotFoundError:
        return "Error: 'pj' command not found"

@mcp.tool()
def open_project(project_name: str, close_everything_else: bool = False) -> str:
    """Open a project in the user's default IDE.  Only use close_everything_else if you want to close all other projects before opening this one."""
    try:
        # Get environment with proper GUI variables
        gui_env = get_gui_environment()
        
        # Use the shell execution method that works
        if close_everything_else:
            cmd = ['pj', project_name, '-y']
        else:
            cmd = ['pj', project_name, '--safe']
        
        # Create a shell command that properly detaches the process
        shell_cmd = f"nohup {shlex.join(cmd)} >/dev/null 2>&1 &"
        
        process = subprocess.Popen(
            shell_cmd,
            shell=True,
            env=gui_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True
        )
        
        # Give it a moment to start
        time.sleep(0.5)
        
        # Don't rely on exit codes since they may be incorrect
        # Instead, just assume success if no exception was thrown
        return f"Successfully launched {project_name} in IDE"
            
    except subprocess.CalledProcessError as e:
        # Handle specific error cases
        if "No project matching" in str(e):
            return f"Error: No project matching '{project_name}' found"
        elif "command not found" in str(e).lower():
            return "Error: 'pj' command not found. Make sure it's installed and in your PATH."
        else:
            return f"Error opening {project_name}: {str(e)}"
    except FileNotFoundError:
        return "Error: 'pj' command not found. Make sure it's installed and in your PATH."
    except Exception as e:
        return f"Error opening {project_name}: {str(e)}"

def format_hocr_text(hocr_result):
    """Format HOCR text by organizing blocks by y-position and x-position to maintain reading order"""
    if not hocr_result or 'pages' not in hocr_result:
        return "No text found"
        
    formatted_text = []
    current_line_y = None
    current_line_text = []
    
    # Get all blocks
    blocks = hocr_result['pages'][0]['blocks']
    
    # Group blocks by similar y positions (within 5 pixels)
    y_groups = {}
    for block in blocks:
        y_base = block['y'] // 5 * 5  # Round to nearest 5 pixels
        if y_base not in y_groups:
            y_groups[y_base] = []
        y_groups[y_base].append(block)
    
    # Sort y groups by vertical position
    sorted_y_groups = sorted(y_groups.items())
    
    # Process each line
    for y_base, line_blocks in sorted_y_groups:
        # Sort blocks in the line by x position
        sorted_line = sorted(line_blocks, key=lambda x: x['x'])
        formatted_text.append(' '.join(block['text'] for block in sorted_line))
    
    return '\n'.join(formatted_text)

@mcp.tool()
def look_at_screen() -> str:
    """Take a screenshot and analyze it using the Huddle Vision API and HOCR API, saving the description to a text file"""
    try:
        if not API_KEY:
            return "Error: HUDDLE_ML_API_KEY not found in environment variables"
        if not HOCR_API_KEY:
            return "Error: HUDDLE_API_KEY not found in environment variables"
        
        # Ensure display environment is properly set
        if 'DISPLAY' not in os.environ:
            os.environ['DISPLAY'] = ':0'
        
        # Set XAUTHORITY if not present
        if 'XAUTHORITY' not in os.environ:
            xauth_path = os.path.expanduser('~/.Xauthority')
            if os.path.exists(xauth_path):
                os.environ['XAUTHORITY'] = xauth_path
        
        # Take screenshot
        screenshot = ImageGrab.grab()
        
        # Save screenshot to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            screenshot.save(temp_file.name, 'PNG')
            temp_filename = temp_file.name
        
        try:
            vision_result = None
            hocr_result = None
            
            # Call Vision API
            with open(temp_filename, 'rb') as image_file:
                files = {'file': image_file}
                headers = {
                    'Ocp-Apim-Subscription-Key': API_KEY
                }
                
                response = requests.post(
                    f"{VISION_BASE_URL}/analyze",
                    files=files,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    vision_result = response.json()
                else:
                    return f"Error calling Vision API: {response.status_code} - {response.text}"
            
            # Call HOCR API
            with open(temp_filename, 'rb') as image_file:
                files = {'file': image_file}
                headers = {
                    'Ocp-Apim-Subscription-Key': HOCR_API_KEY,
                    'properties': json.dumps({
                        "ocr": {
                            "multilingual": True,
                            "enhance_quality": True
                        }
                    })
                }
                
                response = requests.post(
                    f"{HOCR_BASE_URL}/api/ocr",
                    files=files,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    hocr_result = response.json()
                else:
                    return f"Error calling HOCR API: {response.status_code} - {response.text}"
            
            # Format the HOCR text
            formatted_text = format_hocr_text(hocr_result)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"screen_description_{timestamp}.txt"
            
            # Save results to text file
            with open(output_filename, 'w') as f:
                f.write(f"Screen Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                f.write("Vision API Description:\n")
                f.write(vision_result.get('description', str(vision_result)) + "\n\n")
                f.write("HOCR API Text:\n")
                f.write(formatted_text)
            
            return f"Screenshot analyzed successfully.\nVision Description: {vision_result.get('description')}\nHOCR Text:\n{formatted_text}"
                    
        finally:
            # Clean up temporary file
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
                
    except Exception as e:
        return f"Error analyzing screen: {str(e)}"
    
@mcp.tool()
def show_info_to_user(content: str, title: str = "Information") -> str:
    """Display any content as a nicely formatted HTML page in a browser, that the user can read.  If the user asks for information, you should always call the show_info_to_user tool before marking the task as complete.  The user will never see any of your output unless you call this tool."""
    try:
        # Convert markdown to HTML
        html_content = markdown.markdown(content)
        full_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
                    line-height: 1.6;
                    color: #e4e4e7;
                    background-color: #0f172a;
                    margin: 0;
                    padding: 2rem;
                    max-width: 900px;
                    margin: 0 auto;
                }}
                
                h1, h2, h3, h4, h5, h6 {{
                    color: #f1f5f9;
                    margin-top: 2rem;
                    margin-bottom: 1rem;
                    border-bottom: 2px solid #334155;
                    padding-bottom: 0.5rem;
                }}
                
                h1 {{
                    font-size: 2.5rem;
                    color: #60a5fa;
                    text-align: center;
                    border-bottom: 3px solid #3b82f6;
                    margin-bottom: 2rem;
                }}
                
                h2 {{
                    font-size: 1.8rem;
                    color: #34d399;
                }}
                
                h3 {{
                    font-size: 1.4rem;
                    color: #fbbf24;
                }}
                
                p {{
                    margin-bottom: 1rem;
                    color: #cbd5e1;
                }}
                
                ul, ol {{
                    margin-bottom: 1rem;
                    padding-left: 2rem;
                }}
                
                li {{
                    margin-bottom: 0.5rem;
                    color: #cbd5e1;
                }}
                
                code {{
                    background-color: #1e293b;
                    color: #f8fafc;
                    padding: 0.2rem 0.4rem;
                    border-radius: 4px;
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    border: 1px solid #475569;
                }}
                
                pre {{
                    background-color: #1e293b;
                    color: #f8fafc;
                    padding: 1rem;
                    border-radius: 8px;
                    overflow-x: auto;
                    border: 1px solid #475569;
                    margin: 1rem 0;
                }}
                
                pre code {{
                    background: none;
                    border: none;
                    padding: 0;
                }}
                
                blockquote {{
                    border-left: 4px solid #3b82f6;
                    margin: 1rem 0;
                    padding-left: 1rem;
                    color: #94a3b8;
                    font-style: italic;
                }}
                
                a {{
                    color: #60a5fa;
                    text-decoration: none;
                }}
                
                a:hover {{
                    color: #93c5fd;
                    text-decoration: underline;
                }}
                
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 1rem 0;
                }}
                
                th, td {{
                    border: 1px solid #475569;
                    padding: 0.75rem;
                    text-align: left;
                }}
                
                th {{
                    background-color: #1e293b;
                    color: #f1f5f9;
                    font-weight: 600;
                }}
                
                td {{
                    background-color: #0f172a;
                }}
                
                .info-header {{
                    text-align: center;
                    margin-bottom: 3rem;
                    padding: 2rem;
                    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
                    border-radius: 12px;
                    border: 1px solid #475569;
                }}
            </style>
        </head>
        <body>
            <div class="info-header">
                <h1>{title}</h1>
            </div>
            {html_content}
        </body>
        </html>
        """
        
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as f:
            f.write(full_html)
            temp_path = f.name
        
        # Try multiple browser launching methods
        browser_methods = [
            ("google-chrome", ["google-chrome", "--new-tab", temp_path]),
            ("google-chrome (no-sandbox)", ["google-chrome", "--no-sandbox", "--new-tab", temp_path]),
            ("firefox", ["firefox", temp_path]),
            ("xdg-open", ["xdg-open", temp_path]),
        ]
        
        launch_success = False
        launch_method = None
        error_messages = []
        
        for name, cmd in browser_methods:
            try:
                # Use Popen with detached process to avoid blocking
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,  # Detach from parent process
                    env=dict(os.environ, DISPLAY=os.environ.get('DISPLAY', ':0'))  # Ensure DISPLAY is set
                )
                # Wait briefly to see if it starts successfully
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    if process.returncode == 0:
                        launch_success = True
                        launch_method = name
                        break
                except subprocess.TimeoutExpired:
                    # Process is still running, which usually means success for browsers
                    process.kill()  # Clean up
                    launch_success = True
                    launch_method = name
                    break
                    
            except FileNotFoundError:
                error_messages.append(f"{name}: command not found")
            except Exception as e:
                error_messages.append(f"{name}: {str(e)}")
        
        if launch_success:
            return f"Info page opened in browser using {launch_method}. HTML file saved to: {temp_path}"
        else:
            error_summary = "; ".join(error_messages)
            return f"Could not open browser automatically. Tried methods: {error_summary}. Info page saved to: {temp_path}. You can open this file manually in your browser."
    
    except Exception as e:
        return f"Error displaying info page: {str(e)}"

# This is necessary to run the server in stdio mode
if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())