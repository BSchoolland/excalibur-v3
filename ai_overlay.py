#!/usr/bin/env python3
"""
AI Overlay Controller - Python Interface

This module provides a clean interface for controlling the Electron AI overlay
from Python applications. Use this to send real-time updates to the overlay.
"""

import json
import time
import threading
import subprocess
import os
import signal
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass

@dataclass
class TaskStep:
    """Represents a single step in a task"""
    name: str
    duration: float = 2.0

@dataclass
class Task:
    """Represents a complete task with multiple steps"""
    agent_type: str
    task_name: str
    steps: List[TaskStep]

class AIOverlay:
    """
    Main interface for controlling the AI overlay.
    
    Example usage:
        overlay = AIOverlay()
        overlay.start()
        
        # Show a task
        overlay.show_task("Create", "building app", 3)
        overlay.update_step(1, "analyzing requirements")
        time.sleep(2)
        overlay.update_step(2, "generating code")
        time.sleep(2)
        overlay.complete_task()
        
        overlay.stop()
    """
    
    def __init__(self):
        self.electron_process = None
        self.is_running = False
        self.command_watcher_thread = None
        self.stop_watching = False
        
        # Electron app path
        self.electron_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "electron_app")
        print(f"Electron app path: {self.electron_app_path}")
        # File paths
        self.state_file = os.path.join(self.electron_app_path, "overlay_state.json")
        self.command_file = os.path.join(self.electron_app_path, "overlay_commands.json")
        
        # Event handlers
        self.on_close_requested = None
        self.on_text_input_received = None
        self._input_response = None
        self._waiting_for_input = False
        
        self.current_state = {
            "agentType": "Create",
            "taskName": "initializing", 
            "currentStep": 0,
            "totalSteps": 3,
            "isComplete": False,
            "isActive": True,
            "isVisible": False,
            "isWaitingForInput": False,
            "inputPrompt": ""
        }
        # Initialize state file
        self._write_state_file()
    
    def start(self) -> None:
        """Start the Electron overlay application"""
        if self.is_running:
            return
            
        print("Starting AI Overlay...")
        try:
            # Start electron in the background with a new process group
            self.electron_process = subprocess.Popen(
                ["npm", "start"],
                cwd=self.electron_app_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )
            self.is_running = True
            
            # Start command watcher
            self._start_command_watcher()
            
            # Give it time to start
            print("✓ AI Overlay started successfully")
            
        except Exception as e:
            print(f"✗ Failed to start overlay: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the Electron overlay application"""
        if not self.is_running:
            return
            
        print("Stopping AI Overlay...")
        
        # Stop command watcher
        self._stop_command_watcher()
        self.hide()
        
        if self.electron_process:
            print("Terminating electron process")
            
            try:
                # Kill the entire process group to ensure all child processes are terminated
                os.killpg(os.getpgid(self.electron_process.pid), signal.SIGTERM)
                self.electron_process.wait(timeout=3)
                print("Electron process group terminated gracefully")
            except subprocess.TimeoutExpired:
                print("Electron process didn't terminate gracefully, killing...")
                try:
                    # Force kill the entire process group
                    os.killpg(os.getpgid(self.electron_process.pid), signal.SIGKILL)
                    self.electron_process.wait(timeout=2)
                    print("Electron process group killed")
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    print("Warning: Some Electron processes may still be running")
            except ProcessLookupError:
                print("Process already terminated")
                
        self.is_running = False
        
        # Clean up files
        try:
            os.remove(self.state_file)
        except FileNotFoundError:
            pass
        try:
            os.remove(self.command_file)
        except FileNotFoundError:
            pass
            
        print("✓ AI Overlay stopped")
    
    def set_close_handler(self, handler: Callable[[], None]) -> None:
        """
        Set a handler function that will be called when the user clicks the close button
        
        Args:
            handler: Function to call when close button is clicked
        """
        self.on_close_requested = handler
    
    def set_text_input_handler(self, handler: Callable[[str], None]) -> None:
        """
        Set a handler function that will be called when the user submits text input
        
        Args:
            handler: Function to call with the user's input text
        """
        self.on_text_input_received = handler
    
    def request_text_input(self, prompt: str = "enter your task", sound: str = None) -> str:
        """
        Request text input from the user and wait for response
        
        Args:
            prompt: The prompt to show to the user
            sound: Optional sound to play ("task_start", "task_complete", "input")
            
        Returns:
            The text the user entered
        """
        
        # Set up input state
        self._input_response = None
        self._waiting_for_input = True
        
        update_data = {
            "isWaitingForInput": True,
            "inputPrompt": prompt,
            "isVisible": True,
            "isActive": True,
            "agentType": "Excalibur",
            "taskName": prompt,
            "currentStep": 0,
            "totalSteps": 1,
            "isComplete": False
        }
        
        if sound:
            update_data["playSound"] = sound
            update_data["soundTimestamp"] = time.time()
        
        self.current_state.update(update_data)
        self._send_update()
        
        # Wait for response
        while self._waiting_for_input and self.is_running:
            time.sleep(0.1)
        
        result = self._input_response or ""
        
        # Reset input state
        self.current_state.update({
            "isWaitingForInput": False,
            "inputPrompt": ""
        })
        self._send_update()
        
        return result
    
    def show_task(self, agent_type: str, task_name: str, total_steps: int = 3, sound: str = None) -> None:
        """
        Start showing a new task
        
        Args:
            agent_type: Type of agent (e.g., "Create", "Install", "Code", "Execute")
            task_name: Name of the task being performed
            total_steps: Total number of steps in this task
            sound: Optional sound to play ("task_start", "task_complete", "input")
        """
        update_data = {
            "agentType": agent_type,
            "taskName": task_name,
            "currentStep": 0,
            "totalSteps": total_steps,
            "isComplete": False,
            "isActive": True,
            "isVisible": True,
            "isWaitingForInput": False
        }
        
        if sound:
            update_data["playSound"] = sound
            update_data["soundTimestamp"] = time.time()
        
        self.current_state.update(update_data)
        self._send_update()
        print(f"📋 Started task: {agent_type} - {task_name} ({total_steps} steps)")
    
    def update_step(self, step_number: int, step_name: str, sound: str = None) -> None:
        """
        Update the current step
        
        Args:
            step_number: Current step number (1-based)
            step_name: Description of the current step
            sound: Optional sound to play ("task_start", "task_complete", "input")
        """
        update_data = {
            "currentStep": step_number,
            "taskName": step_name,
            "isComplete": False,
            "isWaitingForInput": False
        }
        
        if sound:
            update_data["playSound"] = sound
            update_data["soundTimestamp"] = time.time()
        
        self.current_state.update(update_data)
        self._send_update()
        print(f"  🔄 Step {step_number}/{self.current_state['totalSteps']}: {step_name}")
    
    def complete_task(self, sound: str = None) -> None:
        """
        Mark the current task as complete
        
        Args:
            sound: Optional sound to play ("task_start", "task_complete", "input")
        """
        update_data = {
            "isComplete": True,
            "isActive": False,
            "isWaitingForInput": False
        }
        
        if sound:
            update_data["playSound"] = sound
            update_data["soundTimestamp"] = time.time()
        
        self.current_state.update(update_data)
        self._send_update()
        print(f"Task completed: {self.current_state['agentType']}")
    
    def show_error(self, error_message: str, sound: str = None) -> None:
        """
        Show an error message to the user
        
        Args:
            error_message: The error message to display
            sound: Optional sound to play ("task_start", "task_complete", "input")
        """
        update_data = {
            "agentType": "Error",
            "taskName": error_message,
            "currentStep": 0,
            "totalSteps": 0,
            "isComplete": False,
            "isActive": True,
            "isVisible": True,
            "isWaitingForInput": False
        }
        
        if sound:
            update_data["playSound"] = sound
            update_data["soundTimestamp"] = time.time()
        
        self.current_state.update(update_data)
        self._send_update()
        print(f"Error: {error_message}")
    
    def showMessage(self, message: str, agent_type: str = "Excalibur", sound: str = None) -> None:
        """
        Show a general message to the user
        
        Args:
            message: The message to display
            agent_type: Type of agent (defaults to "Excalibur")
            sound: Optional sound to play ("task_start", "task_complete", "input")
        """
        update_data = {
            "agentType": agent_type,
            "taskName": message,
            "currentStep": 0,
            "totalSteps": 0,
            "isComplete": False,
            "isActive": True,
            "isVisible": True,
            "isWaitingForInput": False
        }
        
        if sound:
            update_data["playSound"] = sound
            update_data["soundTimestamp"] = time.time()
        
        self.current_state.update(update_data)
        self._send_update()
        print(f"Message: {message}")

    def hide(self) -> None:
        """Hide the overlay (slide out)"""
        self.current_state["isVisible"] = False
        self._send_update()
        time.sleep(0.1) # allow time for the overlay to be hidden

    
    def show(self) -> None:
        """Show the overlay (slide in)"""
        self.current_state["isVisible"] = True
        self._send_update()
    
    def set_active(self, is_active: bool) -> None:
        """Set whether the orb should pulse actively"""
        self.current_state["isActive"] = is_active
        self._send_update()
    
    def send_custom_update(self, **kwargs) -> None:
        """
        Send a custom update with any fields
        
        Args:
            **kwargs: Any fields to update in the overlay state
        """
        self.current_state.update(kwargs)
        self._send_update()
    
    def _send_update(self) -> None:
        """Internal method to send updates to the Electron app"""
        if not self.is_running:
            return
            
        self._write_state_file()
    
    def _write_state_file(self) -> None:
        """Write current state to JSON file for Electron to read"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.current_state, f)
        except Exception as e:
            print(f"Failed to write state file: {e}")
    
    def _start_command_watcher(self) -> None:
        """Start watching for commands from the UI"""
        self.stop_watching = False
        self.command_watcher_thread = threading.Thread(target=self._watch_commands, daemon=True)
        self.command_watcher_thread.start()
    
    def _stop_command_watcher(self) -> None:
        """Stop watching for commands from the UI"""
        self.stop_watching = True
        if self.command_watcher_thread and self.command_watcher_thread != threading.current_thread():
            self.command_watcher_thread.join(timeout=1)
    
    def _watch_commands(self) -> None:
        """Watch for command files from the UI"""
        last_mtime = 0
        
        while not self.stop_watching:
            try:
                if os.path.exists(self.command_file):
                    mtime = os.path.getmtime(self.command_file)
                    if mtime > last_mtime:
                        last_mtime = mtime
                        self._process_command()
                        
            except Exception as e:
                print(f"Error watching commands: {e}")
            
            time.sleep(0.1)  # Check every 100ms
    
    def _process_command(self) -> None:
        """Process a command from the UI"""
        try:
            with open(self.command_file, 'r') as f:
                command = json.load(f)
            
            action = command.get('action')
            
            if action == 'close':
                if self.on_close_requested:
                    self.on_close_requested()
                else:
                    # Default behavior: hide the overlay
                    self.hide()
                    print("🚫 Close button clicked - overlay hidden")
            
            elif action == 'text_input':
                input_text = command.get('text', '')
                self._input_response = input_text
                self._waiting_for_input = False
                
                if self.on_text_input_received:
                    self.on_text_input_received(input_text)
                            
            # Clean up command file
            os.remove(self.command_file)
            
        except Exception as e:
            print(f"Error processing command: {e}")

def create_overlay() -> AIOverlay:
    """Convenience function to create an AIOverlay instance"""
    return AIOverlay()

# Example usage
if __name__ == "__main__":
    # Example with text input
    overlay = create_overlay()
    
    # Set up close handler
    def handle_close():
        print("User requested close - stopping demo...")
        overlay.stop()
        exit(0)
    
    overlay.set_close_handler(handle_close)
    
    try:
        overlay.start()
        
        # Request user input
        user_task = overlay.request_text_input("Enter task")
        
        if user_task:
            # Show a task based on user input
            overlay.show_task("Create", f"building {user_task}", 4)
            time.sleep(1)
            
            overlay.update_step(1, "analyzing requirements")
            time.sleep(2)
            
            overlay.update_step(2, "generating code") 
            time.sleep(2)
            
            overlay.update_step(3, "testing application")
            time.sleep(2)
            
            overlay.update_step(4, "deploying to server")
            time.sleep(2)
            
            overlay.complete_task()
            time.sleep(1)
        
        overlay.hide()        
        
    except KeyboardInterrupt:
        print("\n🔄 Demo interrupted")
    finally:
        overlay.stop() 