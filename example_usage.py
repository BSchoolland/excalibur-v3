#!/usr/bin/env python3
"""
Simple example showing how to use the AI Overlay Python interface.
Run this script to see the overlay in action with custom tasks.
"""

import time
from ai_overlay import create_overlay

def main():
    print("🚀 AI Overlay Python Interface Demo")
    print("This will start the Electron overlay and control it from Python")
    print("📌 Try clicking the 'X' button in the overlay to test close functionality!")
    
    # Create the overlay controller
    overlay = create_overlay()
    
    # Set up close handler
    def handle_close():
        print("\n🚫 User clicked close button - stopping demo gracefully...")
        overlay.stop()
        exit(0)
    
    overlay.set_close_handler(handle_close)
    
    try:
        # Start the Electron app
        overlay.start()
        time.sleep(3)
        
        print("\n📋 Example 1: Dynamic progress bars (4 steps)")
        # Show a task with 4 steps to test dynamic progress bars
        overlay.show_task("Create", "building neural network", 4)
        time.sleep(1)
        
        overlay.update_step(1, "loading training data")
        time.sleep(2)
        
        overlay.update_step(2, "initializing model")
        time.sleep(2)
        
        overlay.update_step(3, "training network")
        time.sleep(3)
        
        overlay.update_step(4, "validating results")
        time.sleep(2)
        
        overlay.complete_task()
        time.sleep(1)
        
        overlay.hide()
        time.sleep(5)
        
        print("\n📊 Example 2: Variable step counts")
        # Show different step counts to test dynamic bars
        step_counts = [2, 5, 1, 3]
        tasks = [
            ("Install", "quick setup", ["download", "install"]),
            ("Code", "complex feature", ["design", "implement", "test", "optimize", "deploy"]),
            ("Execute", "simple run", ["start"]),
            ("Debug", "fix issues", ["analyze", "patch", "verify"])
        ]
        
        for steps_count, (agent, task_name, steps) in zip(step_counts, tasks):
            print(f"   → Testing {steps_count} progress bars")
            overlay.show_task(agent, task_name, steps_count)
            time.sleep(0.5)
            
            for i, step in enumerate(steps, 1):
                overlay.update_step(i, step)
                time.sleep(1.2)
            
            overlay.complete_task()
            time.sleep(1)
            
            # Brief hide/show between tasks
            overlay.hide()
            time.sleep(30)
            overlay.show()
            time.sleep(0.3)
        
        print("\n✨ Example 3: Interactive features")
        print("   → The overlay now has better visibility over text")
        print("   → Click the X button to test close functionality")
        print("   → Or press Ctrl+C to interrupt")
        
        # Show a longer task for testing
        overlay.show_task("Monitor", "continuous monitoring", 6)
        
        monitoring_steps = [
            "scanning processes",
            "checking memory usage",
            "analyzing network traffic",
            "monitoring disk I/O",
            "checking system health",
            "generating report"
        ]
        
        for i, step in enumerate(monitoring_steps, 1):
            overlay.update_step(i, step)
            time.sleep(2)
        
        overlay.complete_task()
        time.sleep(2)
    
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
    finally:
        print("\n🛑 Stopping overlay...")
        overlay.stop()
        print("✅ Demo complete!")

if __name__ == "__main__":
    main() 