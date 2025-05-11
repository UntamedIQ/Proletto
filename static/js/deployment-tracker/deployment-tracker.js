/**
 * Proletto Deployment Tracker
 * 
 * This script handles the animated deployment tracker functionality,
 * displaying the progress and status of the deployment process.
 */

class DeploymentTracker {
  constructor(elementId, options = {}) {
    this.element = document.getElementById(elementId);
    if (!this.element) {
      console.error('Deployment tracker element not found');
      return;
    }

    this.options = {
      autoStart: false,
      pollingInterval: 5000, // 5 seconds
      apiEndpoint: '/api/deployment/status',
      onComplete: null,
      onFailed: null,
      ...options
    };

    this.state = {
      status: 'idle', // idle, in-progress, completed, failed
      currentStep: 0,
      progress: 0,
      startTime: null,
      endTime: null,
      logs: [],
      steps: [
        {
          id: 'init',
          title: 'Initialization',
          description: 'Setting up the deployment environment',
          status: 'pending', // pending, active, completed, failed
          details: 'Preparing deployment scripts and configuration...'
        },
        {
          id: 'build',
          title: 'Build Process',
          description: 'Compiling and bundling the application',
          status: 'pending',
          details: 'Building application assets...'
        },
        {
          id: 'database',
          title: 'Database Migration',
          description: 'Applying database schema updates',
          status: 'pending',
          details: 'Running database migrations...'
        },
        {
          id: 'deploy',
          title: 'Deployment',
          description: 'Deploying to Replit environment',
          status: 'pending',
          details: 'Configuring Replit deployment...'
        },
        {
          id: 'verify',
          title: 'Verification',
          description: 'Verifying deployment success',
          status: 'pending',
          details: 'Checking application health and connectivity...'
        }
      ]
    };

    this.timerId = null;
    this.elapsedTimerId = null;
    
    this.init();
    
    if (this.options.autoStart) {
      this.start();
    }
  }

  init() {
    this.renderTracker();
    this.attachEventListeners();
  }

  renderTracker() {
    const { status, progress, steps } = this.state;
    
    // Calculate the overall progress percentage
    const progressPercentage = Math.round(progress * 100);
    
    // Determine status display text and classes
    let statusText = 'Ready to deploy';
    let statusClass = '';
    let statusIcon = '';
    
    switch (status) {
      case 'in-progress':
        statusText = 'Deployment in progress';
        statusClass = 'in-progress';
        statusIcon = '<div class="spinner"></div>';
        break;
      case 'completed':
        statusText = 'Deployment completed';
        statusClass = 'success';
        statusIcon = '<svg class="deployment-tracker-icon" viewBox="0 0 24 24"><path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"></path></svg>';
        break;
      case 'failed':
        statusText = 'Deployment failed';
        statusClass = 'failed';
        statusIcon = '<svg class="deployment-tracker-icon" viewBox="0 0 24 24"><path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"></path></svg>';
        break;
    }
    
    // Generate HTML for steps
    const stepsHtml = steps.map((step, index) => {
      let stepClass = 'deployment-step';
      let stepIconContent = index + 1;
      
      if (step.status === 'active') {
        stepClass += ' active';
        stepIconContent = '<div class="spinner" style="width: 16px; height: 16px;"></div>';
      } else if (step.status === 'completed') {
        stepClass += ' completed';
        stepIconContent = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"></path></svg>';
      } else if (step.status === 'failed') {
        stepClass += ' failed';
        stepIconContent = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"></path></svg>';
      }
      
      return `
        <div class="${stepClass}" data-step-id="${step.id}">
          <div class="deployment-step-icon">${stepIconContent}</div>
          <div class="deployment-step-content">
            <div class="deployment-step-title">${step.title}</div>
            <div class="deployment-step-description">${step.description}</div>
            <div class="deployment-step-details">${step.details || ''}</div>
          </div>
        </div>
      `;
    }).join('');
    
    // Generate HTML for the overall tracker
    const html = `
      <div class="deployment-tracker-header">
        <div class="deployment-tracker-title">Deployment Progress</div>
        <div class="deployment-tracker-status ${statusClass}">
          ${statusIcon}
          ${statusText}
        </div>
      </div>
      
      <div class="deployment-progress-bar">
        <div class="deployment-progress-bar-inner" style="width: ${progressPercentage}%"></div>
      </div>
      
      <div class="deployment-timer" id="deployment-timer">
        ${this.formatElapsedTime()}
      </div>
      
      <div class="deployment-tracker-steps">
        ${stepsHtml}
      </div>
      
      <div class="deployment-logs-toggle" id="deployment-logs-toggle">
        <svg viewBox="0 0 24 24" width="16" height="16" style="margin-right: 4px;">
          <path fill="currentColor" d="M7,10L12,15L17,10H7Z"></path>
        </svg>
        Show deployment logs
      </div>
      
      <div class="deployment-logs" id="deployment-logs">
        <div class="deployment-logs-content" id="deployment-logs-content">
          ${this.state.logs.join('\n')}
        </div>
      </div>
      
      <div class="deployment-actions">
        <button class="deployment-action-button" id="deployment-cancel-button" ${status !== 'in-progress' ? 'disabled' : ''}>Cancel</button>
        <button class="deployment-action-button primary" id="deployment-start-button" ${status === 'in-progress' ? 'disabled' : ''}>
          ${status === 'completed' || status === 'failed' ? 'Redeploy' : 'Start Deployment'}
        </button>
      </div>
    `;
    
    this.element.innerHTML = html;
  }

  attachEventListeners() {
    const startButton = document.getElementById('deployment-start-button');
    const cancelButton = document.getElementById('deployment-cancel-button');
    const logsToggle = document.getElementById('deployment-logs-toggle');
    const logsContainer = document.getElementById('deployment-logs');
    
    if (startButton) {
      startButton.addEventListener('click', () => this.start());
    }
    
    if (cancelButton) {
      cancelButton.addEventListener('click', () => this.cancel());
    }
    
    if (logsToggle && logsContainer) {
      logsToggle.addEventListener('click', () => {
        logsContainer.classList.toggle('expanded');
        logsToggle.innerHTML = logsContainer.classList.contains('expanded') 
          ? '<svg viewBox="0 0 24 24" width="16" height="16" style="margin-right: 4px;"><path fill="currentColor" d="M7,15L12,10L17,15H7Z"></path></svg> Hide deployment logs'
          : '<svg viewBox="0 0 24 24" width="16" height="16" style="margin-right: 4px;"><path fill="currentColor" d="M7,10L12,15L17,10H7Z"></path></svg> Show deployment logs';
      });
    }
  }

  start() {
    if (this.state.status === 'in-progress') {
      return;
    }
    
    this.state.status = 'in-progress';
    this.state.progress = 0;
    this.state.startTime = new Date();
    this.state.endTime = null;
    this.state.logs = ['[INFO] Starting deployment process...'];
    this.state.currentStep = 0;
    
    // Reset all steps to pending
    this.state.steps.forEach(step => {
      step.status = 'pending';
    });
    
    // Set first step to active
    this.state.steps[0].status = 'active';
    
    this.renderTracker();
    
    // Start tracking elapsed time
    this.startElapsedTimeCounter();
    
    // Start polling for status updates
    this.startPolling();
    
    // For demo/simulation, we'll advance the steps automatically
    this.simulateDeployment();
  }

  cancel() {
    if (this.state.status !== 'in-progress') {
      return;
    }
    
    // Stop polling and timers
    this.stopPolling();
    this.stopElapsedTimeCounter();
    
    // Set state to failed
    this.state.status = 'failed';
    this.state.progress = this.state.currentStep / this.state.steps.length;
    this.state.endTime = new Date();
    
    // Mark current step as failed
    if (this.state.currentStep < this.state.steps.length) {
      this.state.steps[this.state.currentStep].status = 'failed';
    }
    
    // Add log entry
    this.addLogEntry('[WARNING] Deployment cancelled by user');
    
    this.renderTracker();
    
    // Call the onFailed callback if provided
    if (typeof this.options.onFailed === 'function') {
      this.options.onFailed('cancelled');
    }
  }

  complete() {
    this.stopPolling();
    this.stopElapsedTimeCounter();
    
    this.state.status = 'completed';
    this.state.progress = 1;
    this.state.endTime = new Date();
    
    // Mark all steps as completed
    this.state.steps.forEach(step => {
      step.status = 'completed';
    });
    
    this.addLogEntry('[INFO] Deployment completed successfully');
    
    this.renderTracker();
    
    // Call the onComplete callback if provided
    if (typeof this.options.onComplete === 'function') {
      this.options.onComplete();
    }
  }

  fail(step, reason) {
    this.stopPolling();
    this.stopElapsedTimeCounter();
    
    this.state.status = 'failed';
    this.state.endTime = new Date();
    
    // Mark the current step as failed
    if (step < this.state.steps.length) {
      this.state.steps[step].status = 'failed';
    }
    
    this.addLogEntry(`[ERROR] Deployment failed at step '${this.state.steps[step].title}': ${reason}`);
    
    this.renderTracker();
    
    // Call the onFailed callback if provided
    if (typeof this.options.onFailed === 'function') {
      this.options.onFailed(reason);
    }
  }

  advanceToNextStep() {
    if (this.state.currentStep < this.state.steps.length - 1) {
      // Mark current step as completed
      this.state.steps[this.state.currentStep].status = 'completed';
      
      // Move to next step
      this.state.currentStep++;
      
      // Mark new step as active
      this.state.steps[this.state.currentStep].status = 'active';
      
      // Update progress
      this.state.progress = this.state.currentStep / this.state.steps.length;
      
      this.addLogEntry(`[INFO] Moving to step: ${this.state.steps[this.state.currentStep].title}`);
      
      this.renderTracker();
      
      return true;
    } else if (this.state.currentStep === this.state.steps.length - 1) {
      // Mark last step as completed
      this.state.steps[this.state.currentStep].status = 'completed';
      
      // Complete the deployment
      this.complete();
      
      return false;
    }
    
    return false;
  }

  startPolling() {
    if (this.timerId) {
      clearInterval(this.timerId);
    }
    
    this.timerId = setInterval(() => {
      this.pollStatus();
    }, this.options.pollingInterval);
  }

  stopPolling() {
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }

  startElapsedTimeCounter() {
    if (this.elapsedTimerId) {
      clearInterval(this.elapsedTimerId);
    }
    
    const timerElement = document.getElementById('deployment-timer');
    
    this.elapsedTimerId = setInterval(() => {
      if (timerElement) {
        timerElement.textContent = this.formatElapsedTime();
      }
    }, 1000);
  }

  stopElapsedTimeCounter() {
    if (this.elapsedTimerId) {
      clearInterval(this.elapsedTimerId);
      this.elapsedTimerId = null;
    }
  }

  formatElapsedTime() {
    if (!this.state.startTime) {
      return 'Not started';
    }
    
    const endTime = this.state.endTime || new Date();
    const elapsedMs = endTime - this.state.startTime;
    
    const seconds = Math.floor(elapsedMs / 1000) % 60;
    const minutes = Math.floor(elapsedMs / (1000 * 60)) % 60;
    const hours = Math.floor(elapsedMs / (1000 * 60 * 60));
    
    const formattedTime = [
      hours.toString().padStart(2, '0'),
      minutes.toString().padStart(2, '0'),
      seconds.toString().padStart(2, '0')
    ].join(':');
    
    return `Elapsed time: ${formattedTime}`;
  }

  addLogEntry(message) {
    const timestamp = new Date().toISOString().substring(11, 19);
    const logEntry = `[${timestamp}] ${message}`;
    
    this.state.logs.push(logEntry);
    
    // Update logs container if it exists
    const logsContent = document.getElementById('deployment-logs-content');
    if (logsContent) {
      logsContent.textContent = this.state.logs.join('\n');
      logsContent.scrollTop = logsContent.scrollHeight;
    }
  }

  async pollStatus() {
    try {
      const response = await fetch(this.options.apiEndpoint);
      
      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }
      
      const data = await response.json();
      
      // Update state based on API response
      this.updateState(data);
      
    } catch (error) {
      console.error('Error polling deployment status:', error);
      
      // For demo/development, don't fail on API errors
      // this.fail(this.state.currentStep, 'Failed to fetch deployment status');
    }
  }
  
  async checkStatus() {
    try {
      const response = await fetch(this.options.apiEndpoint);
      
      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }
      
      const data = await response.json();
      
      // Update state based on API response
      this.updateState(data);
      
      // Check if deployment is in progress and start polling if it is
      if (data.status === 'in-progress') {
        this.startPolling();
      }
      
    } catch (error) {
      console.error('Error checking deployment status:', error);
    }
  }

  updateState(data) {
    // Update state based on API response
    if (!data) return;
    
    // Update basic state properties
    this.state.status = data.status;
    this.state.currentStep = data.current_step;
    this.state.progress = data.progress;
    
    // Update dates if provided
    if (data.start_time) {
      this.state.startTime = new Date(data.start_time);
    }
    
    if (data.end_time) {
      this.state.endTime = new Date(data.end_time);
    }
    
    // Update logs if provided
    if (Array.isArray(data.logs)) {
      this.state.logs = data.logs;
    }
    
    // Update steps if provided
    if (Array.isArray(data.steps) && data.steps.length > 0) {
      this.state.steps = data.steps;
    }
    
    // Re-render the tracker with the updated state
    this.renderTracker();
    
    // Notify about status change if callback is provided
    if (typeof this.options.onStatusChange === 'function') {
      this.options.onStatusChange(this.state.status);
    }
    
    // If deployment completed or failed, stop polling
    if (this.state.status === 'completed') {
      this.stopPolling();
      this.stopElapsedTimeCounter();
      
      if (typeof this.options.onComplete === 'function') {
        this.options.onComplete();
      }
    } else if (this.state.status === 'failed') {
      this.stopPolling();
      this.stopElapsedTimeCounter();
      
      if (typeof this.options.onFailed === 'function') {
        const currentStep = this.state.currentStep < this.state.steps.length 
          ? this.state.steps[this.state.currentStep].title 
          : 'Unknown';
        
        this.options.onFailed(`Failed at step: ${currentStep}`);
      }
    }
  }

  // This method is for demonstration/development purposes
  // In a real implementation, you would use the pollStatus method instead
  simulateDeployment() {
    // Simulate deployment steps with realistic timing
    const stepDurations = [3000, 5000, 4000, 7000, 3000];
    
    const simulateStep = (stepIndex) => {
      if (stepIndex >= this.state.steps.length) {
        return;
      }
      
      const step = this.state.steps[stepIndex];
      
      // Add log entries for current step
      this.addLogEntry(`[INFO] Executing step: ${step.title}`);
      
      // Random simulation logs for each step
      setTimeout(() => {
        switch (stepIndex) {
          case 0: // Init
            this.addLogEntry('[INFO] Loading deployment configuration...');
            break;
          case 1: // Build
            this.addLogEntry('[INFO] Starting build process...');
            setTimeout(() => {
              this.addLogEntry('[INFO] Compiling assets...');
            }, 1500);
            break;
          case 2: // Database
            this.addLogEntry('[INFO] Connecting to database...');
            setTimeout(() => {
              this.addLogEntry('[INFO] Running migrations...');
            }, 1500);
            break;
          case 3: // Deploy
            this.addLogEntry('[INFO] Preparing Replit environment...');
            setTimeout(() => {
              this.addLogEntry('[INFO] Setting up Gunicorn server...');
            }, 2000);
            setTimeout(() => {
              this.addLogEntry('[INFO] Configuring port 5000...');
            }, 4000);
            break;
          case 4: // Verify
            this.addLogEntry('[INFO] Starting verification...');
            setTimeout(() => {
              this.addLogEntry('[INFO] Checking application health...');
            }, 1000);
            break;
        }
        
        // Simulate step completion
        setTimeout(() => {
          // Small chance of failure for demo purposes
          const shouldFail = Math.random() < 0.1 && stepIndex < this.state.steps.length - 1;
          
          if (shouldFail) {
            this.fail(stepIndex, 'Simulated random failure');
          } else {
            if (this.advanceToNextStep()) {
              simulateStep(stepIndex + 1);
            }
          }
        }, stepDurations[stepIndex]);
      }, 500);
    };
    
    // Start simulation with the first step
    simulateStep(0);
  }
}

// Factory function to create deployment tracker instances
function createDeploymentTracker(elementId, options = {}) {
  return new DeploymentTracker(elementId, options);
}

// If loaded in a browser environment, attach to window
if (typeof window !== 'undefined') {
  window.createDeploymentTracker = createDeploymentTracker;
}