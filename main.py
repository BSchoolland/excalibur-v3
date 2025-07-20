from services.task_input import TaskInput
from ai_overlay import AIOverlay
import time


running = True
def mainloop(overlay: AIOverlay, task_input: TaskInput):
    global running
    while running:
        user_task = overlay.request_text_input("Enter task", sound="input")
        print(f"Task: {user_task}")
        if user_task == "" or user_task == "huh":
            overlay.show_error("Task not understood", sound="error")
            time.sleep(4)
            overlay.hide()
            time.sleep(2)
            continue
        overlay.show_task("Excalibur", f"Processing {user_task}", 1, sound="task_start")
        time.sleep(1)
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
        
        overlay.complete_task(sound="task_complete")
        time.sleep(2)

 # Set up close handler
def handle_close():
    print("\nProcess stopping...")
    global running
    running = False
    overlay.stop()
    exit(0)

if __name__ == "__main__":
    overlay = AIOverlay()
    overlay.set_close_handler(handle_close)

    overlay.start()
    # overlay.showMessage("Welcome to Excalibur", sound="welcome")
    # time.sleep(4)
    # overlay.hide()
    # time.sleep(2)
    task_input = TaskInput(overlay)
    mainloop(overlay, task_input)
    overlay.stop()