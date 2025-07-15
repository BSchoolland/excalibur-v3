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

    updateState(newState) {
        // Update internal state
        Object.assign(this.state, newState);

        // Update UI elements
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
        
        this.elements.energyOrb.classList.toggle('active', isActive);
        this.elements.energyOrb.classList.toggle('complete', isComplete);
    }

    updateVisibility() {
        const { isVisible } = this.state;
        
        this.elements.mainContainer.classList.toggle('slide-out', !isVisible);
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

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.aiOverlay = new AIOverlay();
});

// Helper function for testing - can be removed in production
window.testUpdate = (data) => {
    if (window.aiOverlay) {
        window.aiOverlay.updateState(data);
    }
}; 