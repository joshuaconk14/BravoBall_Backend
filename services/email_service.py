"""
Email service for sending password reset emails using SendGrid
"""

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@bravoball.com')
        self.app_name = os.getenv('APP_NAME', 'BravoBall')
        
        if not self.api_key:
            logger.warning("SENDGRID_API_KEY not found in environment variables")
    
    
    def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """
        Send a welcome email to new users
        
        Args:
            to_email: The recipient's email address
            user_name: The user's name
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not self.api_key:
                logger.error("SendGrid API key not configured")
                return False
            
            subject = f"Welcome to {self.app_name}!"
            
            html_content = f"""
            <html>
            <body>
                <h2>Welcome to {self.app_name}!</h2>
                <p>Hello {user_name},</p>
                <p>Thank you for joining {self.app_name}! We're excited to help you improve your soccer skills.</p>
                <p>You can now:</p>
                <ul>
                    <li>Generate personalized training sessions</li>
                    <li>Track your progress</li>
                    <li>Access a library of drills</li>
                </ul>
                <p>Start your training journey today!</p>
                <br>
                <p>Best regards,</p>
                <p>The {self.app_name} Team</p>
            </body>
            </html>
            """
            
            from_email = Email(self.from_email)
            to_email_obj = To(to_email)
            content = Content("text/html", html_content)
            mail = Mail(from_email, to_email_obj, subject, content)
            
            sg = SendGridAPIClient(api_key=self.api_key)
            response = sg.send(mail)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Welcome email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send welcome email. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            return False

    def _send_verification_code_email(self, to_email: str, code: str, code_type: str) -> bool:
        """
        ✅ UNIFIED METHOD: Send verification code email (used by both password reset and email verification)
        This ensures both systems use IDENTICAL email templates that go to inbox, not spam.
        
        Args:
            to_email: The recipient's email address
            code: The 6-digit verification code
            code_type: Either "Password Reset" or "Email Verification" for the subject
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not self.api_key:
                logger.error("SendGrid API key not configured")
                return False
            
            # ✅ UNIFIED: Same subject pattern that works for password reset
            subject = f"Your {self.app_name} {code_type} Code"
            
            # ✅ UNIFIED: Exact same template as password reset (proven to work)
            html_content = f"""
            <html><body>
            <h2>{code_type} Code</h2>
            <p>Your {code_type.lower()} code is:</p>
            <h1 style='letter-spacing: 0.2em;'>{code}</h1>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this, you can ignore this email.</p>
            <br><p>The {self.app_name} Team</p>
            </body></html>
            """
            
            text_content = f"Your {self.app_name} {code_type.lower()} code is: {code}\nThis code will expire in 10 minutes."
            
            from_email = Email(self.from_email)
            to_email_obj = To(to_email)
            content = Content("text/html", html_content)
            mail = Mail(from_email, to_email_obj, subject, content)
            mail.add_content(Content("text/plain", text_content))
            
            sg = SendGridAPIClient(api_key=self.api_key)
            response = sg.send(mail)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"{code_type} code email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send {code_type.lower()} code email. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending {code_type.lower()} code email: {str(e)}")
            return False

    def send_password_reset_code_email(self, to_email: str, code: str) -> bool:
        """
        ✅ REFACTORED: Now uses unified method to ensure consistency
        """
        return self._send_verification_code_email(to_email, code, "Password Reset")

    def send_email_verification_code(self, to_email: str, code: str) -> bool:
        """
        ✅ REFACTORED: Now uses unified method to ensure consistency with password reset
        """
        return self._send_verification_code_email(to_email, code, "Email Verification") 