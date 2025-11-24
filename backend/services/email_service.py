"""
Email Service
Sends transactional emails (verification, password reset, notifications)
"""
import logging
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from backend.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for transactional emails"""
    
    # Logo em base64 (otimizada para 150x150px) - Carrega do arquivo
    LOGO_BASE64 = None
    
    @classmethod
    def get_logo_base64(cls):
        """Carrega a logo em base64 uma única vez"""
        if cls.LOGO_BASE64 is None:
            import os
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logo_base64.txt')
            try:
                with open(logo_path, 'r') as f:
                    cls.LOGO_BASE64 = f"data:image/png;base64,{f.read().strip()}"
            except FileNotFoundError:
                # Fallback para emoji se o arquivo não existir
                cls.LOGO_BASE64 = None
        return cls.LOGO_BASE64
    
    def __init__(self):
        self.smtp_host = getattr(settings, 'smtp_host', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'smtp_port', 587)
        self.smtp_user = getattr(settings, 'smtp_user', None)
        self.smtp_password = getattr(settings, 'smtp_password', None)
        self.from_email = getattr(settings, 'from_email', 'noreply@orbis.app')
        self.from_name = getattr(settings, 'from_name', 'Orbis')
        self.frontend_url = getattr(settings, 'frontend_url', 'http://localhost:3000')
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ):
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text and HTML parts
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            if self.smtp_user and self.smtp_password:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
                
                logger.info(f"Email sent to {to_email}: {subject}")
            else:
                # In development, just log
                logger.warning(f"Email service not configured. Would send to {to_email}: {subject}")
                logger.debug(f"Email content: {html_content}")
        
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
    
    async def send_verification_email(self, email: str, username: str, token: str):
        """Send email verification"""
        verify_url = f"{self.frontend_url}/verify-email?token={token}"
        
        # Get logo HTML
        logo_base64 = self.get_logo_base64()
        logo_html = f'<img src="{logo_base64}" alt="Orbis" style="width: 80px; height: 80px; margin: 0 auto 15px; display: block; border-radius: 15px;" />' if logo_base64 else '<div style="font-size: 64px; margin-bottom: 10px;">🌍</div>'
        
        subject = "Verify your Orbis account"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #e5e5e5; background: #0a0a0a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #000000 0%, #1a1a1a 50%, #0a0a0a 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; border: 1px solid rgba(239, 68, 68, 0.2); }}
                .content {{ background: #0f0f0f; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid rgba(255, 255, 255, 0.1); border-top: none; }}
                .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; text-decoration: none; border-radius: 8px; margin: 20px 0; box-shadow: 0 0 20px rgba(220, 38, 38, 0.3); font-weight: 600; }}
                .button:hover {{ background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }}
                .footer {{ text-align: center; margin-top: 30px; color: #888; font-size: 12px; }}
                code {{ background: rgba(255, 255, 255, 0.05); padding: 8px 12px; border-radius: 6px; color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); display: inline-block; margin: 10px 0; }}
                p {{ color: #d1d5db; }}
                strong {{ color: #ef4444; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    {logo_html}
                    <h1 style="margin: 0; color: white;">Welcome to Orbis!</h1>
                </div>
                <div class="content">
                    <p>Hi <strong>{username}</strong>,</p>
                    <p>Thank you for joining Orbis! To get started, please verify your email address by clicking the button below:</p>
                    <center>
                        <a href="{verify_url}" class="button">Verify Email Address</a>
                    </center>
                    <p>Or copy and paste this link into your browser:</p>
                    <p><code>{verify_url}</code></p>
                    <p>This link will expire in 24 hours.</p>
                    <p>If you didn't create an account with Orbis, you can safely ignore this email.</p>
                    <p>Best regards,<br>The Orbis Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 Orbis - Breaking language barriers</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Orbis!
        
        Hi {username},
        
        Thank you for joining Orbis! To get started, please verify your email address by visiting:
        {verify_url}
        
        This link will expire in 24 hours.
        
        If you didn't create an account with Orbis, you can safely ignore this email.
        
        Best regards,
        The Orbis Team
        """
        
        await self._send_email(email, subject, html_content, text_content)
    
    async def send_password_reset_email(self, email: str, username: str, token: str):
        """Send password reset email"""
        reset_url = f"{self.frontend_url}/reset-password?token={token}"
        
        # Get logo HTML
        logo_base64 = self.get_logo_base64()
        logo_html = f'<img src="{logo_base64}" alt="Orbis" style="width: 80px; height: 80px; margin: 0 auto 15px; display: block; border-radius: 15px;" />' if logo_base64 else '<div style="font-size: 64px; margin-bottom: 10px;">🔒</div>'
        
        subject = "Reset your Orbis password"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #e5e5e5; background: #0a0a0a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #000000 0%, #1a1a1a 50%, #0a0a0a 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; border: 1px solid rgba(239, 68, 68, 0.2); }}
                .content {{ background: #0f0f0f; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid rgba(255, 255, 255, 0.1); border-top: none; }}
                .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; text-decoration: none; border-radius: 8px; margin: 20px 0; box-shadow: 0 0 20px rgba(220, 38, 38, 0.3); font-weight: 600; }}
                .button:hover {{ background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }}
                .warning {{ background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0; border-radius: 6px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #888; font-size: 12px; }}
                code {{ background: rgba(255, 255, 255, 0.05); padding: 8px 12px; border-radius: 6px; color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); display: inline-block; margin: 10px 0; }}
                p {{ color: #d1d5db; }}
                strong {{ color: #ef4444; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    {logo_html}
                    <h1 style="margin: 0; color: white;">Password Reset</h1>
                </div>
                <div class="content">
                    <p>Hi <strong>{username}</strong>,</p>
                    <p>We received a request to reset your Orbis password. Click the button below to create a new password:</p>
                    <center>
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </center>
                    <p>Or copy and paste this link into your browser:</p>
                    <p><code>{reset_url}</code></p>
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong> This link will expire in 1 hour. If you didn't request a password reset, please ignore this email or contact support if you're concerned about your account security.
                    </div>
                    <p>Best regards,<br>The Orbis Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 Orbis - Breaking language barriers</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset
        
        Hi {username},
        
        We received a request to reset your Orbis password. Visit the link below to create a new password:
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you didn't request a password reset, please ignore this email.
        
        Best regards,
        The Orbis Team
        """
        
        await self._send_email(email, subject, html_content, text_content)
    
    async def send_welcome_email(self, email: str, username: str):
        """Send welcome email after email verification"""
        # Get logo HTML
        logo_base64 = self.get_logo_base64()
        logo_html = f'<img src="{logo_base64}" alt="Orbis" style="width: 80px; height: 80px; margin: 0 auto 15px; display: block; border-radius: 15px;" />' if logo_base64 else '<div style="font-size: 64px; margin-bottom: 10px;">🎉</div>'
        
        subject = "Welcome to Orbis!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #e5e5e5; background: #0a0a0a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #000000 0%, #1a1a1a 50%, #0a0a0a 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; border: 1px solid rgba(239, 68, 68, 0.2); }}
                .content {{ background: #0f0f0f; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid rgba(255, 255, 255, 0.1); border-top: none; }}
                .feature {{ background: rgba(255, 255, 255, 0.03); padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #ef4444; }}
                .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; text-decoration: none; border-radius: 8px; margin: 20px 0; box-shadow: 0 0 20px rgba(220, 38, 38, 0.3); font-weight: 600; }}
                .footer {{ text-align: center; margin-top: 30px; color: #888; font-size: 12px; }}
                p {{ color: #d1d5db; }}
                h3 {{ color: #ef4444; margin-top: 30px; }}
                strong {{ color: #ef4444; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    {logo_html}
                    <h1 style="margin: 0; color: white;">Welcome to Orbis, {username}!</h1>
                </div>
                <div class="content">
                    <p>Your email has been verified and your account is ready to go!</p>
                    
                    <h3>What you can do with Orbis:</h3>
                    
                    <div class="feature">
                        <strong>🎙️ Voice Cloning</strong><br>
                        Clone your voice in minutes and use it in 20+ languages
                    </div>
                    
                    <div class="feature">
                        <strong>⚡ Real-time Translation</strong><br>
                        Speak naturally and be understood instantly in any language
                    </div>
                    
                    <div class="feature">
                        <strong>🎥 HD Video Meetings</strong><br>
                        Crystal clear video with up to 25 participants (Pro plan)
                    </div>
                    
                    <div class="feature">
                        <strong>📝 Transcriptions</strong><br>
                        Automatic meeting transcripts in multiple languages
                    </div>
                    
                    <p style="margin-top: 30px;">Best regards,<br>The Orbis Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 Orbis - Breaking language barriers</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        await self._send_email(email, subject, html_content)
    
    async def send_subscription_confirmation(self, email: str, username: str, tier: str):
        """Send subscription confirmation email"""
        # Get logo HTML
        logo_base64 = self.get_logo_base64()
        logo_html = f'<img src="{logo_base64}" alt="Orbis" style="width: 80px; height: 80px; margin: 0 auto 15px; display: block; border-radius: 15px;" />' if logo_base64 else '<div style="font-size: 64px; margin-bottom: 10px;">🚀</div>'
        
        subject = f"Welcome to Orbis {tier.capitalize()}!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #e5e5e5; background: #0a0a0a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #000000 0%, #1a1a1a 50%, #0a0a0a 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; border: 1px solid rgba(239, 68, 68, 0.2); }}
                .content {{ background: #0f0f0f; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid rgba(255, 255, 255, 0.1); border-top: none; }}
                .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; text-decoration: none; border-radius: 8px; margin: 20px 0; box-shadow: 0 0 20px rgba(220, 38, 38, 0.3); font-weight: 600; }}
                .button:hover {{ background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }}
                .footer {{ text-align: center; margin-top: 30px; color: #888; font-size: 12px; }}
                p {{ color: #d1d5db; }}
                strong {{ color: #ef4444; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    {logo_html}
                    <h1 style="margin: 0; color: white;">Welcome to {tier.capitalize()}!</h1>
                </div>
                <div class="content">
                    <p>Hi <strong>{username}</strong>,</p>
                    <p>Thank you for upgrading to Orbis {tier.capitalize()}! Your subscription is now active.</p>
                    <p>You now have access to all {tier.capitalize()} features including extended meeting duration, more participants, and priority support.</p>
                    <center>
                        <a href="{self.frontend_url}/dashboard" class="button">View Dashboard</a>
                    </center>
                    <p>Questions? Our support team is here to help!</p>
                    <p>Best regards,<br>The Orbis Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 Orbis - Breaking language barriers</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        await self._send_email(email, subject, html_content)


email_service = EmailService()