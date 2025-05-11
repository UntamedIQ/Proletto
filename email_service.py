"""
Proletto Email Service

This module handles email sending functionality for the platform,
including password reset emails, email confirmations, and notifications.
"""
import os
import logging
import re
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from email_templates import EmailTemplates

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails through SendGrid"""
    
    def __init__(self):
        """Initialize the email service with SendGrid credentials"""
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        self.from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@proletto.com')
        self.is_available = self.check_availability()
        self.templates = EmailTemplates()
    
    def check_availability(self):
        """Check if the email service is available"""
        return bool(self.api_key)
    
    def send_email(self, to_email, subject, text_content=None, html_content=None):
        """
        Send an email using SendGrid
        
        Args:
            to_email (str): Recipient email address
            subject (str): Email subject
            text_content (str, optional): Plain text content
            html_content (str, optional): HTML content
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.is_available:
            logger.warning("Cannot send email: SendGrid API key not configured")
            return False
            
        message = Mail(
            from_email=Email(self.from_email),
            to_emails=To(to_email),
            subject=subject
        )
        
        if html_content:
            message.content = Content("text/html", html_content)
        elif text_content:
            message.content = Content("text/plain", text_content)
        else:
            logger.error("Cannot send email: No content provided")
            return False
            
        try:
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            # Log success or error based on status code
            if 200 <= response.status_code < 300:
                logger.info(f"Email sent to {to_email} successfully")
                return True
            else:
                logger.error(f"Failed to send email. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def send_password_reset_email(self, user, token, base_url):
        """
        Send a password reset email
        
        Args:
            user (User): User object
            token (str): Password reset token
            base_url (str): Base URL for reset link
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        reset_url = f"{base_url}/auth/reset-password/{token}"
        
        subject = "Proletto - Reset Your Password"
        
        html_content = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ text-align: center; margin-bottom: 20px; }}
                    .button {{ background-color: #d35400; color: white; padding: 12px 20px; 
                              text-decoration: none; border-radius: 4px; display: inline-block; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #888; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Password Reset Request</h2>
                    </div>
                    <p>Hello {user.name or 'there'},</p>
                    <p>You recently requested to reset your password for your Proletto account. 
                       Click the button below to reset it.</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Your Password</a>
                    </p>
                    <p>If you did not request a password reset, please ignore this email or contact 
                       support if you have questions.</p>
                    <p>This password reset link is only valid for 24 hours.</p>
                    <p>Thanks,<br>The Proletto Team</p>
                    <div class="footer">
                        <p>If you're having trouble clicking the button, copy and paste this URL 
                           into your web browser: {reset_url}</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Hello {user.name or 'there'},
        
        You recently requested to reset your password for your Proletto account.
        Please visit the following link to reset your password:
        
        {reset_url}
        
        This password reset link is only valid for 24 hours.
        
        If you did not request a password reset, please ignore this email or contact support.
        
        Thanks,
        The Proletto Team
        """
        
        return self.send_email(user.email, subject, text_content, html_content)
    
    def send_email_confirmation(self, user, token, base_url):
        """
        Send an email confirmation email
        
        Args:
            user (User): User object
            token (str): Email confirmation token
            base_url (str): Base URL for confirmation link
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        confirm_url = f"{base_url}/auth/confirm-email/{token}"
        
        subject = "Proletto - Confirm Your Email"
        
        html_content = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ text-align: center; margin-bottom: 20px; }}
                    .button {{ background-color: #d35400; color: white; padding: 12px 20px; 
                              text-decoration: none; border-radius: 4px; display: inline-block; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #888; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Welcome to Proletto!</h2>
                    </div>
                    <p>Hello {user.name or 'there'},</p>
                    <p>Thank you for signing up with Proletto. To complete your registration, 
                       please confirm your email address.</p>
                    <p style="text-align: center;">
                        <a href="{confirm_url}" class="button">Confirm Email</a>
                    </p>
                    <p>If you did not create an account, please ignore this email.</p>
                    <p>Thanks,<br>The Proletto Team</p>
                    <div class="footer">
                        <p>If you're having trouble clicking the button, copy and paste this URL 
                           into your web browser: {confirm_url}</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Hello {user.name or 'there'},
        
        Thank you for signing up with Proletto. To complete your registration, 
        please confirm your email address by visiting:
        
        {confirm_url}
        
        If you did not create an account, please ignore this email.
        
        Thanks,
        The Proletto Team
        """
        
        return self.send_email(user.email, subject, text_content, html_content)
        
    def replace_placeholders(self, template, replacements):
        """
        Replace placeholders in a template with actual values.
        
        Args:
            template (str): Template string with {{placeholder}} format
            replacements (dict): Dictionary of replacements {placeholder: value}
            
        Returns:
            str: Template with placeholders replaced
        """
        result = template
        for key, value in replacements.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result
        
    def send_template_email(self, to_email, template_name, replacements=None):
        """
        Send an email using a predefined template
        
        Args:
            to_email (str): Recipient email address
            template_name (str): Name of the template to use (attribute in EmailTemplates)
            replacements (dict, optional): Dictionary of replacements for template placeholders
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Default replacements if none provided
            replacements = replacements or {}
                
            # Add timestamp if not already provided
            if 'timestamp' not in replacements:
                replacements['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            # Check if the template exists
            if not hasattr(self.templates, template_name):
                logger.error(f"Template {template_name} not found")
                return False
                
            # Get the template
            template = getattr(self.templates, template_name)
            
            # Replace placeholders in the template
            subject = template['subject']
            html_content = self.replace_placeholders(template['html_content'], replacements)
            text_content = self.replace_placeholders(template['text_content'], replacements)
            
            # Send the email
            return self.send_email(
                to_email=to_email,
                subject=subject,
                text_content=text_content,
                html_content=html_content
            )
        except Exception as e:
            logger.error(f"Error sending template email: {e}")
            return False
        
    def send_welcome_email(self, user, base_url):
        """
        Send a welcome email after successful registration
        
        Args:
            user (User): User object
            base_url (str): Base URL for links
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Use the template-based approach
        replacements = {
            'name': user.name or 'there'
        }
        
        return self.send_template_email(user.email, 'WELCOME_EMAIL', replacements)
        
    def send_supporter_onboarding_email(self, user, base_url):
        """
        Send a thank you email after upgrading to Supporter
        
        Args:
            user (User): User object
            base_url (str): Base URL for links
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Use the template-based approach
        replacements = {
            'name': user.name or 'there'
        }
        
        return self.send_template_email(user.email, 'SUPPORTER_UPGRADE_CONFIRMATION', replacements)
        
    def send_referral_credited_email(self, referrer, new_user, base_url):
        """
        Send email to a user who earned a referral credit when someone they referred upgraded
        
        Args:
            referrer (User): The user who referred the new paying user
            new_user (User): The user who upgraded to a paid tier
            base_url (str): Base URL for links
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Use the template-based approach
        replacements = {
            'name': referrer.name or 'there',
            'referral_code': referrer.referral_code
        }
        
        return self.send_template_email(referrer.email, 'REFERRAL_CREDIT_EARNED', replacements)

# Create a singleton instance
_email_service = None

def get_email_service():
    """Get the singleton email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service