"""
Email Templates for Proletto Platform

This module provides structured email templates for various user events in the Proletto platform.
Templates use placeholders in the format {{placeholder_name}} which are replaced with actual
values when emails are sent.
"""

class EmailTemplates:
    """Collection of email templates for the Proletto platform"""
    
    # Welcome Email (Free Tier Signup)
    WELCOME_EMAIL = {
        'subject': "Welcome to Proletto – You're in",
        'text_content': """
Hi {{name}},

Welcome to Proletto — a smarter way for artists to find real opportunities.

Here's what you can do right now:
- Track your art pieces with QR labels
- Access curated artist calls updated weekly
- Preview features like AI matching and portfolio tools

Upgrade to the Supporter Tier to unlock full benefits during beta for just $5/month.

Visit https://myproletto.com/upgrade to upgrade now.

— The Proletto Team
        """,
        'html_content': """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <p>Hi {{name}},</p>

        <p>Welcome to <strong>Proletto</strong> — a smarter way for artists to find real opportunities.</p>

        <p>Here's what you can do right now:</p>
        <ul>
          <li>Track your art pieces with QR labels</li>
          <li>Access curated artist calls updated weekly</li>
          <li>Preview features like AI matching and portfolio tools</li>
        </ul>

        <p>Upgrade to the Supporter Tier to unlock full benefits during beta for just $5/month.</p>

        <p><a href="https://myproletto.com/upgrade" style="padding:10px 20px; background:#8A634A; color:#fff; text-decoration:none; border-radius: 4px;">Upgrade Now</a></p>

        <p>— The Proletto Team</p>
    </div>
</body>
</html>
        """
    }
    
    # Referral Credit Earned
    REFERRAL_CREDIT_EARNED = {
        'subject': "You just earned a referral credit on Proletto",
        'text_content': """
Hi {{name}},

Someone signed up using your referral code — nice work!

You've earned 1 free month of the Supporter Tier. It will be automatically applied at your next billing cycle.

Keep sharing your code to unlock more perks:
{{referral_code}}

Visit https://myproletto.com/dashboard to go to your dashboard.

— The Proletto Team
        """,
        'html_content': """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <p>Hi {{name}},</p>

        <p>Someone signed up using your referral code — nice work!</p>

        <p>You've earned <strong>1 free month</strong> of the Supporter Tier. It will be automatically applied at your next billing cycle.</p>

        <p>Keep sharing your code to unlock more perks:</p>
        <p style="background: #f5f5f5; padding: 10px; border-radius: 4px; text-align: center;"><strong>{{referral_code}}</strong></p>

        <p><a href="https://myproletto.com/dashboard" style="padding:10px 20px; background:#8A634A; color:#fff; text-decoration:none; border-radius: 4px;">Go to Dashboard</a></p>

        <p>— The Proletto Team</p>
    </div>
</body>
</html>
        """
    }
    
    # Supporter Upgrade Confirmation
    SUPPORTER_UPGRADE_CONFIRMATION = {
        'subject': "Thank you for upgrading to Supporter",
        'text_content': """
Hi {{name}},

Thanks for supporting the mission. You've officially unlocked:
- Early access to new opportunities
- Weekly email + SMS digests
- Access to 3 state-specific AI engines
- Your "Supporter" badge

Let's go build something great.

Visit https://myproletto.com/dashboard to view your dashboard.

— The Proletto Team
        """,
        'html_content': """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <p>Hi {{name}},</p>

        <p>Thanks for supporting the mission. You've officially unlocked:</p>
        <ul>
          <li>Early access to new opportunities</li>
          <li>Weekly email + SMS digests</li>
          <li>Access to 3 state-specific AI engines</li>
          <li>Your "Supporter" badge</li>
        </ul>

        <p>Let's go build something great.</p>

        <p><a href="https://myproletto.com/dashboard" style="padding:10px 20px; background:#8A634A; color:#fff; text-decoration:none; border-radius: 4px;">View Your Dashboard</a></p>

        <p>— The Proletto Team</p>
    </div>
</body>
</html>
        """
    }

    # Email Test Template
    EMAIL_TEST = {
        'subject': "Proletto Email Service Test",
        'text_content': """
This is a test email from Proletto platform.

If you're receiving this email, it means the SendGrid integration is working correctly!

Timestamp: {{timestamp}}

Thanks,
The Proletto Team
        """,
        'html_content': """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h2>Proletto Email Service Test</h2>
        </div>
        <p>This is a test email from the Proletto platform.</p>
        <p>If you're seeing this, the SendGrid integration is working correctly!</p>
        <p>Timestamp: {{timestamp}}</p>
        <p>Thanks,<br>The Proletto Team</p>
    </div>
</body>
</html>
        """
    }
    
    # Weekly Digest Email
    WEEKLY_DIGEST = {
        'subject': "Your Weekly Art Opportunities Digest",
        'text_content': """
Hi {{name}},

Here are your personalized art opportunities for this week:

{{#each opportunities}}
- {{title}}
  Deadline: {{deadline}}
  Location: {{location}}
  {{description}}
  Learn more: {{url}}

{{/each}}

Log in to view all {{total_count}} opportunities at https://www.myproletto.com/opportunities.

— The Proletto Team
        """,
        'html_content': """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f8f3e6;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff; border-radius: 8px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="https://assets.myproletto.com/logos/proletto-logo.png" alt="Proletto Logo" style="max-width: 150px;">
        </div>
        
        <p>Hi {{name}},</p>
        
        <p>Here are your personalized art opportunities for this week:</p>
        
        {{#each opportunities}}
        <div style="margin-bottom: 25px; padding: 15px; border-left: 4px solid #8A634A; background-color: #f9f9f9;">
            <h3 style="margin-top: 0; color: #8A634A;">{{title}}</h3>
            <p><strong>Deadline:</strong> {{deadline}}</p>
            <p><strong>Location:</strong> {{location}}</p>
            <p>{{description}}</p>
            <p><a href="{{url}}" style="padding: 8px 15px; background: #8A634A; color: #fff; text-decoration: none; border-radius: 4px; display: inline-block;">Learn More</a></p>
        </div>
        {{/each}}
        
        <p style="margin-top: 30px;">
            <a href="https://www.myproletto.com/opportunities" style="padding: 10px 20px; background: #8A634A; color: #fff; text-decoration: none; border-radius: 4px; display: inline-block;">View All {{total_count}} Opportunities</a>
        </p>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        
        <p style="font-size: 0.9em; color: #666;">
            This email was sent to {{email}} because you're a Pro subscriber to Proletto.
            <br>
            To manage your email preferences, visit your <a href="https://www.myproletto.com/settings" style="color: #8A634A;">account settings</a>.
        </p>
        
        <p>— The Proletto Team</p>
    </div>
</body>
</html>
        """
    }