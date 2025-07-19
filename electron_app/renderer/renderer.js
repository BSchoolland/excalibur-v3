const { ipcRenderer } = require('electron');
const fs = require('fs');
const path = require('path');

class AIOverlay {
    constructor() {
        this.elements = {
            mainContainer: document.getElementById('mainContainer'),
            energyOrb: document.getElementById('energyOrb'),
            agentType: document.getElementById('agentType'),
            statusLabel: document.getElementById('statusLabel'),
            taskDescription: document.getElementById('taskDescription'),
            progressCounter: document.getElementById('progressCounter'),
            progressBars: document.getElementById('progressBars'),
            closeButton: document.getElementById('closeButton'),
            taskInfo: document.getElementById('taskInfo'),
            inputForm: document.getElementById('inputForm'),
            textInput: document.getElementById('textInput')
        };

        this.state = {
            isActive: false,
            isComplete: false,
            isVisible: true,
            currentStep: 0,
            totalSteps: 3,
            agentType: 'Create',
            taskName: 'initializing',
            isWaitingForInput: false,
            inputPrompt: ''
        };

        this.commandFile = path.join(__dirname, '..', 'overlay_commands.json');
        this.init();
    }

    init() {
        // Listen for status updates from main process
        ipcRenderer.on('status-update', (event, data) => {
            this.updateState(data);
        });

        // Set up close button
        this.elements.closeButton.addEventListener('click', () => {
            this.sendCloseCommand();
        });

        // Set up input form
        this.elements.inputForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleTextInput();
        });

        // Auto-focus input when it becomes visible
        this.elements.textInput.addEventListener('focus', () => {
            this.elements.textInput.select();
        });

        // Start with some basic animations
        this.startPulseAnimation();
    }

    updateState(newState) {
        const wasComplete = this.state.isComplete;
        const oldTaskName = this.state.taskName;
        const oldCurrentStep = this.state.currentStep;
        const wasWaitingForInput = this.state.isWaitingForInput;
        
        // Update state
        Object.assign(this.state, newState);

        // Play sounds based on state changes
        if (!wasComplete && this.state.isComplete) {
            // Task just completed
            this.playTaskCompleteSound();
        } else if (
            this.state.currentStep === 0 && 
            this.state.taskName !== 'initializing' &&
            (oldTaskName !== this.state.taskName || wasComplete || oldTaskName === 'initializing')
        ) {
            // New task started: either task name changed, or we were completed, or coming from initial state
            // if we're accepting input, don't play the sound
            if (!this.state.isWaitingForInput) {
                this.playTaskStartSound();
            } else {
                this.playInputSound();
            }
        }

        // Handle input mode transition
        if (!wasWaitingForInput && this.state.isWaitingForInput) {
            this.enterInputMode();
        } else if (wasWaitingForInput && !this.state.isWaitingForInput) {
            this.exitInputMode();
        }

        this.updateUI();
    }

    enterInputMode() {
        console.log('Entering input mode');
        
        // Add input mode classes
        this.elements.mainContainer.classList.add('input-mode');
        this.elements.energyOrb.classList.add('input-mode');
        this.elements.statusLabel.classList.add('input-mode');
        this.elements.inputForm.classList.add('input-mode');
        
        // Show input form, hide task info
        this.elements.inputForm.classList.remove('hidden');
        this.elements.taskInfo.classList.add('hidden');
        
        // Set placeholder and focus
        if (this.state.inputPrompt) {
            this.elements.textInput.placeholder = this.state.inputPrompt;
        }
        
        // Focus with a slight delay to ensure visibility
        setTimeout(() => {
            this.elements.textInput.focus();
        }, 100);
    }

    exitInputMode() {
        console.log('Exiting input mode');
        
        // Remove input mode classes
        this.elements.mainContainer.classList.remove('input-mode');
        this.elements.energyOrb.classList.remove('input-mode');
        this.elements.statusLabel.classList.remove('input-mode');
        this.elements.inputForm.classList.remove('input-mode');
        
        // Hide input form, show task info
        this.elements.inputForm.classList.add('hidden');
        this.elements.taskInfo.classList.remove('hidden');
        
        // Clear input
        this.elements.textInput.value = '';
    }

    handleTextInput() {
        const inputText = this.elements.textInput.value.trim();
        
        if (!inputText) {
            // Flash input border if empty
            this.elements.textInput.style.borderColor = '#ef4444';
            setTimeout(() => {
                this.elements.textInput.style.borderColor = '';
            }, 300);
            return;
        }
        
        console.log('Sending text input:', inputText);
        
        // Send command to Python
        this.sendTextInputCommand(inputText);
        
        // Disable input while processing
        this.elements.textInput.disabled = true;
        this.elements.textInput.style.opacity = '0.5';
    }

    sendTextInputCommand(text) {
        console.log('Sending text input command to Python...');
        
        // Create command object
        const command = {
            action: 'text_input',
            text: text,
            timestamp: Date.now()
        };

        // Write command to file for Python to read
        try {
            fs.writeFileSync(this.commandFile, JSON.stringify(command, null, 2));
            console.log('Text input command sent:', text);
        } catch (error) {
            console.error('Failed to send text input command:', error);
            // Re-enable input on error
            this.elements.textInput.disabled = false;
            this.elements.textInput.style.opacity = '1';
        }
    }

    updateUI() {
        const { 
            agentType, 
            taskName, 
            currentStep, 
            totalSteps, 
            isComplete, 
            isActive,
            isVisible,
            isWaitingForInput
        } = this.state;

        // Update agent type
        this.elements.agentType.textContent = agentType || 'Create';

        // Update status and task (only if not in input mode)
        if (!isWaitingForInput) {
            if (isComplete) {
                this.elements.statusLabel.textContent = 'Status:';
                this.elements.taskDescription.textContent = 'task complete';
                this.elements.taskDescription.classList.add('complete');
            } else {
                this.elements.statusLabel.textContent = 'Executing:';
                this.elements.taskDescription.textContent = taskName || 'initializing';
                this.elements.taskDescription.classList.remove('complete');
            }
        } else {
            this.elements.statusLabel.textContent = 'Input:';
            this.elements.taskDescription.textContent = taskName || 'enter your task';
        }

        // Update progress counter
        if (isComplete) {
            this.elements.progressCounter.textContent = '✓';
        } else if (isWaitingForInput) {
            this.elements.progressCounter.textContent = '0/?';
        } else {
            this.elements.progressCounter.textContent = `${currentStep}/${totalSteps}`;
        }

        // Update progress bars (create dynamic bars based on totalSteps)
        this.updateProgressBars();

        // Update energy orb state
        this.updateEnergyOrb();

        // Handle visibility
        this.updateVisibility();
        
        // Re-enable input if it was disabled
        if (this.elements.textInput.disabled) {
            this.elements.textInput.disabled = false;
            this.elements.textInput.style.opacity = '1';
        }
    }

    updateProgressBars() {
        const { currentStep, totalSteps, isComplete, isWaitingForInput } = this.state;
        
        // Clear existing bars
        this.elements.progressBars.innerHTML = '';
        
        // Don't show progress bars in input mode
        if (isWaitingForInput) {
            return;
        }
        
        // Create bars based on totalSteps
        for (let i = 0; i < totalSteps; i++) {
            const bar = document.createElement('div');
            bar.className = 'progress-bar';
            
            if (isComplete) {
                bar.classList.add('complete');
            } else if (i < currentStep) {
                bar.classList.add('active');
            }
            
            this.elements.progressBars.appendChild(bar);
        }
    }

    updateEnergyOrb() {
        const { isActive, isComplete, isWaitingForInput } = this.state;
        
        // Clear all state classes first
        this.elements.energyOrb.classList.remove('active', 'complete');
        
        if (isComplete) {
            this.elements.energyOrb.classList.add('complete');
        } else if (isActive || isWaitingForInput) {
            this.elements.energyOrb.classList.add('active');
        }
    }

    updateVisibility() {
        const { isVisible } = this.state;
        
        if (isVisible) {
            this.elements.mainContainer.classList.remove('slide-out');
        } else {
            this.elements.mainContainer.classList.add('slide-out');
        }
    }

    startPulseAnimation() {
        // Simulate activity pulses
        setInterval(() => {
            if (!this.state.isComplete && !this.state.isWaitingForInput) {
                this.state.isActive = !this.state.isActive;
                this.updateEnergyOrb();
            }
        }, 2000);
    }

    sendCloseCommand() {
        console.log('Sending close command to Python...');
        
        // Create command object
        const command = {
            action: 'close',
            timestamp: Date.now()
        };

        // Write command to file for Python to read
        try {
            fs.writeFileSync(this.commandFile, JSON.stringify(command, null, 2));
            console.log('Close command sent');
        } catch (error) {
            console.error('Failed to send close command:', error);
        }
    }

    // Method to handle slide out and reset cycle
    startCompleteCycle() {
        this.updateState({ isComplete: true });

        // After 2 seconds, start slide out
        setTimeout(() => {
            this.updateState({ isVisible: false });
        }, 2000);

        // After slide out completes, reset and slide back in
        setTimeout(() => {
            this.updateState({
                isComplete: false,
                isVisible: true,
                currentStep: 0,
                taskName: 'initializing'
            });
        }, 2500);
    }
    playInputSound() {
        // Shoot 265 sound
        try {
            zzfx(...[.1,,191,.03,.18,.19,3,2.8,-3,-5,,,,,,,,.85,.11]);
        } catch (e) {
            console.log('Sound disabled');
        }
    }

    playTaskStartSound() {
        // Powerup 6 sound
        try {
            zzfx(...[.2,,222,.01,.17,.27,1,2.3,-3,,377,.05,.01,,,,,.99,.28,.43,-774]);
        } catch (e) {
            console.log('Sound disabled');
        }
    }

    playTaskCompleteSound() {
        // Pickup 216
        try {
            zzfx(...[.2,0,635,.02,.04,.2,1,1.9,,,203,.06,.03,,,,,.81,.05]);
        } catch (e) {
            console.log('Sound disabled');
        }
    }
}

// Initialize the overlay when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.aiOverlay = new AIOverlay();
});

// Helper function for testing - can be removed in production
window.testUpdate = (data) => {
    if (window.aiOverlay) {
        window.aiOverlay.updateState(data);
    }
}; 