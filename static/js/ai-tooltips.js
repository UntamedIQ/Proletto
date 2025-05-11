/**
 * AI Feature Tooltips
 * Enhances the user experience by providing informative tooltips for AI features
 * with playful animations.
 */

class AITooltips {
  constructor() {
    this.init();
    this.tooltipData = {
      'opportunity-match': {
        title: 'AI Opportunity Matching',
        description: 'Our AI analyzes your portfolio and preferences to find the most relevant opportunities just for you.',
        animation: 'sparks',
        theme: 'match'
      },
      'portfolio-optimize': {
        title: 'Portfolio Optimization',
        description: 'AI reviews your portfolio to suggest improvements and tailor it for specific opportunities.',
        animation: 'brain',
        theme: 'optimize'
      },
      'application-autofill': {
        title: 'Smart Application Filling',
        description: 'Let AI help you complete applications faster by generating tailored responses based on your profile and the opportunity.',
        animation: 'sparks',
        theme: 'autofill'
      },
      'portfolio-analysis': {
        title: 'Portfolio Analysis',
        description: 'AI examines your artwork to provide insights on style, themes, and potential improvements.',
        animation: 'brain',
        theme: 'analyze' 
      },
      'application-tips': {
        title: 'Application Tips',
        description: 'Get AI-powered suggestions to improve your applications based on successful submissions.',
        animation: 'sparks',
        theme: 'match'
      }
    };
  }

  /**
   * Initialize tooltips on page load
   */
  init() {
    document.addEventListener('DOMContentLoaded', () => {
      this.findAndAttachTooltips();
      
      // Re-attach tooltips when page content changes (for SPAs or dynamic content)
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'childList' && mutation.addedNodes.length) {
            this.findAndAttachTooltips();
          }
        });
      });
      
      observer.observe(document.body, { childList: true, subtree: true });
    });
  }

  /**
   * Find elements with data-ai-tooltip attribute and attach tooltips
   */
  findAndAttachTooltips() {
    const elements = document.querySelectorAll('[data-ai-tooltip]');
    elements.forEach(element => {
      if (!element.querySelector('.ai-tooltip-icon')) {
        this.attachTooltip(element);
      }
    });
  }

  /**
   * Attach tooltip to an element
   * @param {HTMLElement} element - Element to attach tooltip to
   */
  attachTooltip(element) {
    const tooltipType = element.getAttribute('data-ai-tooltip');
    const position = element.getAttribute('data-tooltip-position') || 'top';
    
    if (!this.tooltipData[tooltipType]) {
      console.warn(`Tooltip data not found for type: ${tooltipType}`);
      return;
    }
    
    const data = this.tooltipData[tooltipType];
    
    // Create tooltip wrapper
    const tooltipWrapper = document.createElement('span');
    tooltipWrapper.className = `ai-tooltip ${position}`;
    
    // Create tooltip icon
    const tooltipIcon = document.createElement('span');
    tooltipIcon.className = 'ai-tooltip-icon';
    tooltipIcon.innerHTML = 'AI';
    
    // Create tooltip content
    const tooltipContent = document.createElement('div');
    tooltipContent.className = `ai-tooltip-content ai-theme-${data.theme}`;
    
    // Create animation
    const animation = document.createElement('div');
    animation.className = 'ai-animation';
    
    if (data.animation === 'sparks') {
      for (let i = 0; i < 5; i++) {
        const spark = document.createElement('div');
        spark.className = 'ai-spark';
        animation.appendChild(spark);
      }
    } else if (data.animation === 'brain') {
      const brain = document.createElement('div');
      brain.className = 'ai-brain';
      animation.appendChild(brain);
    }
    
    // Create title
    const title = document.createElement('div');
    title.className = 'ai-tooltip-title';
    title.textContent = data.title;
    
    // Add Premium tag if needed
    if (element.hasAttribute('data-premium')) {
      const tag = document.createElement('span');
      tag.className = 'ai-tooltip-tag';
      tag.textContent = 'PREMIUM';
      title.appendChild(tag);
    }
    
    // Create description
    const description = document.createElement('div');
    description.textContent = data.description;
    
    // Assemble tooltip
    tooltipContent.appendChild(animation);
    tooltipContent.appendChild(title);
    tooltipContent.appendChild(description);
    
    tooltipWrapper.appendChild(tooltipIcon);
    tooltipWrapper.appendChild(tooltipContent);
    
    // Add to element
    element.appendChild(tooltipWrapper);
  }
}

// Initialize tooltips
const aiTooltips = new AITooltips();