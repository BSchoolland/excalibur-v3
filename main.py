from services.task_input import TaskInput
from ai_overlay import AIOverlay

overlay = AIOverlay()
overlay.start()
task_input = TaskInput(overlay)
overlay.hide()
print(task_input.wait_for_task())
overlay.stop()