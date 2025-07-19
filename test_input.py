#!/usr/bin/env python3
"""
Test script for text input functionality
"""

import time
from ai_overlay import create_overlay

def main():
    print("🚀 Testing AI Overlay Text Input")
    
    # Create the overlay controller
    overlay = create_overlay()
    
    # Set up close handler
    def handle_close():
        print("\n🚫 User clicked close button - stopping...")
        overlay.stop()
        exit(0)
    
    overlay.set_close_handler(handle_close)
    
    try:
        # Start the Electron app
        overlay.start()
        time.sleep(2)
        
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
            
            overlay.update_step(4, "finishing touches")
            time.sleep(2)
            
            overlay.complete_task()
            time.sleep(2)
            
            # Ask for another input
            user_action = overlay.request_text_input("what would you like to do next?")
            
            if user_action:
                overlay.show_task("Execute", f"performing {user_action}", 2)
                time.sleep(1)
                
                overlay.update_step(1, "preparing environment")
                time.sleep(2)
                
                overlay.update_step(2, "executing command")
                time.sleep(2)
                
                overlay.complete_task()
                time.sleep(1)
        
        overlay.hide()        
        
    except KeyboardInterrupt:
        print("\n🔄 Process interrupted")
    finally:
        overlay.stop()

if __name__ == "__main__":
    main() 