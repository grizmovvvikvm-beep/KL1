import smtplib
import requests
import json
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.providers = {}
        self.load_config()
    
    def load_config(self):
        """Load notification configuration"""
        try:
            # In production, load from database or config file
            self.config = {
                "email": {
                    "enabled": True,
                    "smtp_server": "localhost",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "from_addr": "noreply@kurslight.vpn",
                    "to_addrs": ["admin@kurslight.vpn"]
                },
                "slack": {
                    "enabled": False,
                    "webhook_url": "",
                    "channel": "#alerts"
                },
                "telegram": {
                    "enabled": False,
                    "bot_token": "",
                    "chat_id": ""
                },
                "webhook": {
                    "enabled": False,
                    "url": "",
                    "headers": {"Content-Type": "application/json"}
                }
            }
        except Exception as e:
            logger.error(f"Failed to load notification config: {e}")
            self.config = {}
    
    def send_notification(self, 
                         title: str, 
                         message: str, 
                         level: str = "info",
                         channels: List[str] = None):
        """Send notification through configured channels"""
        if channels is None:
            channels = ["email"]  # Default channel
        
        for channel in channels:
            try:
                if channel == "email" and self.config.get("email", {}).get("enabled"):
                    self._send_email(title, message, level)
                elif channel == "slack" and self.config.get("slack", {}).get("enabled"):
                    self._send_slack(title, message, level)
                elif channel == "telegram" and self.config.get("telegram", {}).get("enabled"):
                    self._send_telegram(title, message, level)
                elif channel == "webhook" and self.config.get("webhook", {}).get("enabled"):
                    self._send_webhook(title, message, level)
            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
    
    def _send_email(self, title: str, message: str, level: str):
        """Send email notification"""
        config = self.config["email"]
        
        msg = MimeMultipart()
        msg['From'] = config['from_addr']
        msg['To'] = ", ".join(config['to_addrs'])
        msg['Subject'] = f"[KursLight-{level.upper()}] {title}"
        
        # Create HTML email
        html = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: {"#e74c3c" if level == "error" else "#f39c12" if level == "warning" else "#3498db"}; 
                              color: white; padding: 10px; border-radius: 5px; }}
                    .content {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
                    .footer {{ margin-top: 20px; font-size: 12px; color: #7f8c8d; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>KursLight VPN Notification</h2>
                    </div>
                    <div class="content">
                        <h3>{title}</h3>
                        <p>{message}</p>
                        <p><strong>Level:</strong> {level.upper()}</p>
                        <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated message from KursLight VPN Management System.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MimeText(html, 'html'))
        
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            if config.get('username') and config.get('password'):
                server.login(config['username'], config['password'])
            server.send_message(msg)
        
        logger.info(f"Email notification sent: {title}")
    
    def _send_slack(self, title: str, message: str, level: str):
        """Send Slack notification"""
        config = self.config["slack"]
        
        color = {
            "info": "#3498db",
            "warning": "#f39c12", 
            "error": "#e74c3c",
            "success": "#27ae60"
        }.get(level, "#3498db")
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message,
                    "fields": [
                        {
                            "title": "Level",
                            "value": level.upper(),
                            "short": True
                        },
                        {
                            "title": "Time", 
                            "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "short": True
                        }
                    ],
                    "footer": "KursLight VPN",
                    "ts": datetime.now().timestamp()
                }
            ]
        }
        
        response = requests.post(config['webhook_url'], json=payload)
        response.raise_for_status()
        
        logger.info(f"Slack notification sent: {title}")
    
    def _send_telegram(self, title: str, message: str, level: str):
        """Send Telegram notification"""
        config = self.config["telegram"]
        
        text = f"*{title}*\n\n{message}\n\nLevel: {level.upper()}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
        payload = {
            "chat_id": config['chat_id'],
            "text": text,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        logger.info(f"Telegram notification sent: {title}")
    
    def _send_webhook(self, title: str, message: str, level: str):
        """Send webhook notification"""
        config = self.config["webhook"]
        
        payload = {
            "source": "kurslight",
            "level": level,
            "title": title,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        response = requests.post(
            config['url'], 
            json=payload,
            headers=config.get('headers', {})
        )
        response.raise_for_status()
        
        logger.info(f"Webhook notification sent: {title}")
    
    def test_notifications(self):
        """Test all enabled notification channels"""
        test_message = "This is a test notification from KursLight VPN Management System."
        
        for channel, config in self.config.items():
            if config.get('enabled'):
                try:
                    self.send_notification(
                        "Test Notification", 
                        test_message,
                        "info",
                        channels=[channel]
                    )
                    logger.info(f"Test notification sent via {channel}")
                except Exception as e:
                    logger.error(f"Test notification failed for {channel}: {e}")

# Global notification manager
notification_manager = NotificationManager()