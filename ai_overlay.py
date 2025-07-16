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
        
        self.current_state = {
            "agentType": "Create",
            "taskName": "initializing", 
            "currentStep": 0,
            "totalSteps": 3,
            "isComplete": False,
            "isActive": True,
            "isVisible": False
        }
        # Initialize state file
        self._write_state_file()
    
    def start(self) -> None:
        """Start the Electron overlay application"""
        if self.is_running:
            return
            
        print("Starting AI Overlay...")
        try:
            # Start electron in the background
            self.electron_process = subprocess.Popen(
                ["npm", "start"],
                cwd=self.electron_app_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
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
        
        if self.electron_process:
            self.electron_process.terminate()
            try:
                self.electron_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.electron_process.kill()
                
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
    
    def show_task(self, agent_type: str, task_name: str, total_steps: int = 3) -> None:
        """
        Start showing a new task
        
        Args:
            agent_type: Type of agent (e.g., "Create", "Install", "Code", "Execute")
            task_name: Name of the task being performed
            total_steps: Total number of steps in this task
        """
        self.current_state.update({
            "agentType": agent_type,
            "taskName": task_name,
            "currentStep": 0,
            "totalSteps": total_steps,
            "isComplete": False,
            "isActive": True,
            "isVisible": True
        })
        self._send_update()
        print(f"📋 Started task: {agent_type} - {task_name} ({total_steps} steps)")
    
    def update_step(self, step_number: int, step_name: str) -> None:
        """
        Update the current step
        
        Args:
            step_number: Current step number (1-based)
            step_name: Description of the current step
        """
        self.current_state.update({
            "currentStep": step_number,
            "taskName": step_name,
            "isComplete": False
        })
        self._send_update()
        print(f"  🔄 Step {step_number}/{self.current_state['totalSteps']}: {step_name}")
    
    def complete_task(self) -> None:
        """Mark the current task as complete"""
        self.current_state.update({
            "isComplete": True,
            "isActive": False
        })
        self._send_update()
        print(f"Task completed: {self.current_state['agentType']}")
    
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
        print(f"📡 Sending update: {self.current_state}")
    
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
        print("📡 Started command watcher")
    
    def _stop_command_watcher(self) -> None:
        """Stop watching for commands from the UI"""
        self.stop_watching = True
        if self.command_watcher_thread:
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
            print(f"🎮 Received command: {action}")
            
            if action == 'close':
                if self.on_close_requested:
                    self.on_close_requested()
                else:
                    # Default behavior: hide the overlay
                    self.hide()
                    print("🚫 Close button clicked - overlay hidden")
            
            # Clean up command file
            os.remove(self.command_file)
            
        except Exception as e:
            print(f"Error processing command: {e}")

def create_overlay() -> AIOverlay:
    """Convenience function to create an AIOverlay instance"""
    return AIOverlay()

# Example usage
if __name__ == "__main__":
    # Example with close handler
    overlay = create_overlay()
    
    # Set up close handler
    def handle_close():
        print("User requested close - stopping demo...")
        overlay.stop()
        exit(0)
    
    overlay.set_close_handler(handle_close)
    
    try:
        overlay.start()
        
        # Show a simple task
        overlay.show_task("Create", "building application", 4)
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
        print("\n�� Demo interrupted")
    finally:
        overlay.stop() 