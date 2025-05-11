/**
 * Feedback Widget
 * Provides "Was this helpful?" feedback functionality for opportunities
 */

class FeedbackWidget {
  constructor(elementId = 'feedback-widget') {
    this.elementId = elementId;
    this.initialized = false;
    this.element = null;
    this.opportunityId = null;
    this.token = null;
  }

  /**
   * Initialize the feedback widget
   * @param {string} opportunityId - ID of the current opportunity
   * @param {string} token - JWT token for authentication
   */
  init(opportunityId, token) {
    // Store opportunity ID and token
    this.opportunityId = opportunityId;
    this.token = token;

    // Get widget element
    this.element = document.getElementById(this.elementId);
    if (!this.element) {
      console.error(`Feedback widget element with ID "${this.elementId}" not found`);
      return;
    }

    // Create feedback widget HTML
    this.element.innerHTML = `
      <div class="feedback-question">
        <p>Was this opportunity helpful?</p>
        <div class="feedback-buttons">
          <button class="feedback-button like" aria-label="Yes, this was helpful">
            <span class="feedback-emoji">👍</span>
          </button>
          <button class="feedback-button dislike" aria-label="No, this wasn't helpful">
            <span class="feedback-emoji">👎</span>
          </button>
        </div>
      </div>
      <div class="feedback-success hidden">
        <p>Thanks for your feedback!</p>
      </div>
      <div class="feedback-error hidden">
        <p>Error sending feedback. Please try again.</p>
      </div>
    `;

    // Add event listeners to buttons
    const likeButton = this.element.querySelector('.feedback-button.like');
    const dislikeButton = this.element.querySelector('.feedback-button.dislike');

    likeButton.addEventListener('click', () => this.sendFeedback(true));
    dislikeButton.addEventListener('click', () => this.sendFeedback(false));

    this.initialized = true;
  }

  /**
   * Send feedback to the API
   * @param {boolean} rating - true for like, false for dislike
   */
  async sendFeedback(rating) {
    if (!this.initialized || !this.opportunityId) {
      console.error('Feedback widget not properly initialized');
      return;
    }

    // Get elements
    const questionElement = this.element.querySelector('.feedback-question');
    const successElement = this.element.querySelector('.feedback-success');
    const errorElement = this.element.querySelector('.feedback-error');

    try {
      // Call API to submit feedback
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({
          opp_id: this.opportunityId,
          rating: rating
        })
      });

      // Handle response
      if (response.ok) {
        // Show success message
        questionElement.classList.add('hidden');
        successElement.classList.remove('hidden');
        
        // Track with Google Analytics if available
        if (typeof gtag !== 'undefined') {
          gtag('event', 'opportunity_feedback', {
            'opportunity_id': this.opportunityId,
            'rating': rating ? 'positive' : 'negative'
          });
        }
      } else {
        // Show error message
        questionElement.classList.add('hidden');
        errorElement.classList.remove('hidden');
        console.error('Error submitting feedback:', await response.text());
      }
    } catch (error) {
      // Show error message
      questionElement.classList.add('hidden');
      errorElement.classList.remove('hidden');
      console.error('Error submitting feedback:', error);
    }
  }
}

// Create singleton instance
const feedbackWidget = new FeedbackWidget();

// Export for usage in other modules
if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
  module.exports = feedbackWidget;
}