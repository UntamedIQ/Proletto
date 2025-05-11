"""
Test script for email service functionality
This script verifies that the SendGrid integration is working correctly.
"""
import os
from email_service import EmailService

def test_email_availability():
    """Test if the email service is available with proper credentials"""
    email_service = EmailService()
    print(f"Email service availability: {email_service.is_available}")
    print(f"Using sender email: {email_service.from_email}")
    return email_service.is_available

def test_send_email(recipient_email="test@example.com"):
    """Test sending a simple email through SendGrid"""
    email_service = EmailService()
    
    if not email_service.is_available:
        print("Email service not available. Please check SendGrid API key.")
        return False
    
    # Send a test email
    subject = "Proletto Email Service Test"
    text_content = "This is a test email from Proletto platform to verify SendGrid integration."
    html_content = """
    <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { text-align: center; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Proletto Email Service Test</h2>
                </div>
                <p>This is a test email from the Proletto platform.</p>
                <p>If you're seeing this, the SendGrid integration is working correctly!</p>
                <p>Thanks,<br>The Proletto Team</p>
            </div>
        </body>
    </html>
    """
    
    result = email_service.send_email(
        to_email=recipient_email,
        subject=subject,
        text_content=text_content,
        html_content=html_content
    )
    
    if result:
        print(f"Test email successfully sent to {recipient_email}")
    else:
        print(f"Failed to send test email to {recipient_email}")
    
    return result

if __name__ == "__main__":
    # First verify the email service is available
    if test_email_availability():
        # For automated testing, just print the successful configuration
        print("Email service is properly configured and ready to use.")
        print("To test sending an email, modify this script with a recipient email.")
        # Uncomment and replace with a real email to test sending
        # test_send_email("your-email@example.com") 
    else:
        print("Email service test failed. Please check SENDGRID_API_KEY and SENDGRID_FROM_EMAIL environment variables.")