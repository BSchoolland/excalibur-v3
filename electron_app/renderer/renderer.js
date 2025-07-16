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
            closeButton: document.getElementById('closeButton')
        };

        this.state = {
            isActive: false,
            isComplete: false,
            isVisible: true,
            currentStep: 0,
            totalSteps: 3,
            agentType: 'Create',
            taskName: 'initializing'
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

        // Start with some basic animations
        this.startPulseAnimation();
    }

    // Sound effect functions
    playTaskStartSound() {
        zzfx(...[.1,,222,.01,.17,.27,1,2.3,-3,,377,.05,.01,,,,,.99,.28,.43,-774]);
    }

    playTaskCompleteSound() {
        zzfx(...[.1,0,635,.02,.06,.3,1,1.9,,,203,.06,.03,,,,,.81,.05]);
    }

    updateState(newState) {
        const wasComplete = this.state.isComplete;
        const oldTaskName = this.state.taskName;
        const oldCurrentStep = this.state.currentStep;
        
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
            this.playTaskStartSound();
        }

        this.updateUI();
    }

    updateUI() {
        const { 
            agentType, 
            taskName, 
            currentStep, 
            totalSteps, 
            isComplete, 
            isActive,
            isVisible 
        } = this.state;

        // Update agent type
        this.elements.agentType.textContent = agentType || 'Create';

        // Update status and task
        if (isComplete) {
            this.elements.statusLabel.textContent = 'Status:';
            this.elements.taskDescription.textContent = 'task complete';
            this.elements.taskDescription.classList.add('complete');
        } else {
            this.elements.statusLabel.textContent = 'Executing:';
            this.elements.taskDescription.textContent = taskName || 'initializing';
            this.elements.taskDescription.classList.remove('complete');
        }

        // Update progress counter
        if (isComplete) {
            this.elements.progressCounter.textContent = '✓';
        } else {
            this.elements.progressCounter.textContent = `${currentStep}/${totalSteps}`;
        }

        // Update progress bars (create dynamic bars based on totalSteps)
        this.updateProgressBars();

        // Update energy orb state
        this.updateEnergyOrb();

        // Handle visibility
        this.updateVisibility();
    }

    updateProgressBars() {
        const { currentStep, totalSteps, isComplete } = this.state;
        
        // Clear existing bars
        this.elements.progressBars.innerHTML = '';
        
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
        const { isActive, isComplete } = this.state;
        
        if (isComplete) {
            this.elements.energyOrb.classList.add('complete');
            this.elements.energyOrb.classList.remove('active');
        } else if (isActive) {
            this.elements.energyOrb.classList.add('active');
            this.elements.energyOrb.classList.remove('complete');
        } else {
            this.elements.energyOrb.classList.remove('active', 'complete');
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
            if (!this.state.isComplete) {
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
}

// Initialize the overlay when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AIOverlay();
});

// Helper function for testing - can be removed in production
window.testUpdate = (data) => {
    if (window.aiOverlay) {
        window.aiOverlay.updateState(data);
    }
}; 