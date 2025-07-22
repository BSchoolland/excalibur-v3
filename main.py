from services.task_input import TaskInput
from ai_overlay import AIOverlay
import time
import asyncio
from agent_core import Agent
import os
from dotenv import load_dotenv

load_dotenv()

running = True
async def mainloop(overlay: AIOverlay, task_input: TaskInput):
    global running
    while running:
        user_task = await task_input.wait_for_task()
        print(f"Task: {user_task}")
        if user_task == "" or user_task == "huh":
            overlay.show_error("Task not understood", sound="error")
            time.sleep(3)
            overlay.hide()
            time.sleep(1)
            continue
        overlay.show_task("Excalibur", f"Processing {user_task}", 1, sound="task_start")
        agent = await Agent.create(
            model='gpt-4.1',
            mcp_servers=['wrapper.py', {'command': 'node', 'args': ['playwright-mcp/cli.js', '--isolated', '--headless']}],
            type='simple',
            system_prompt="You are going to be given an audio transcription of a user's goal.  You will perform only that task, and do nothing else.  It is possible that the audio transcription is not clear, in such cases make your best guess as to the goal.  If the transcription cannot be understood, then return the task as failed.  If the user asks for information, you should always call the show_info_to_user tool before marking the task as complete."
        )
        result = await agent.run("Audio transcription of user's goal: " + user_task)
        print(result)
        if result["state"] == "success":
            skip_start_notif = True
        else:
            skip_start_notif = True
        await agent.close()
        overlay.complete_task(sound="task_complete")
        time.sleep(2)
        overlay.hide()
        await asyncio.sleep(0.1)

def plan_task(task: str):
    return {
        "type": "Create",
        "name": "Write and test a bash script to convert png images to webp",
        "steps": [
            "Install dependencies",
            "Write script",
            "Run script on test images",
        ]
    }
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
    task_input = TaskInput(overlay)
    asyncio.run(mainloop(overlay, task_input))
    overlay.stop()