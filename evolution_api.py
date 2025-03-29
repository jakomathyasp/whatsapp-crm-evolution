import requests
import json
import os
import logging
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)

class EvolutionAPI:
    def __init__(self, instance_name, base_url=None, api_key=None):
        # Get from parameters or from environment
        self.base_url = base_url or os.environ.get("EVOLUTION_API_URL", "http://localhost:8080")
        self.instance = instance_name
        self.api_key = api_key or os.environ.get("EVOLUTION_API_KEY", "your-api-key")
        
        self.session = requests.Session()
        self.headers = {
            'Content-Type': 'application/json',
            'apikey': self.api_key
        }
        logger.debug(f"Initialized Evolution API with instance: {self.instance}")
    
    def start_instance(self):
        """Inicia uma instância no Evolution API"""
        url = f"{self.base_url}/instance/start"
        payload = {
            "instanceName": self.instance
        }
        
        try:
            response = self.session.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error starting instance: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_qr_code(self):
        """Obtém o QR code para conexão"""
        url = f"{self.base_url}/instance/qrcode"
        params = {"instanceName": self.instance}
        
        try:
            response = self.session.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting QR code: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def connection_status(self):
        """Verifica status de conexão da instância"""
        url = f"{self.base_url}/instance/connectionState"
        params = {"instanceName": self.instance}
        
        try:
            response = self.session.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "state": data.get("state", "DISCONNECTED"),
                "connected": data.get("state") == "CONNECTED"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking connection status: {str(e)}")
            return {"success": False, "connected": False, "error": str(e)}
    
    def send_message(self, number, message):
        """Envia mensagem de texto para um número"""
        url = f"{self.base_url}/message/text/send"
        
        # Format number (remove any non-numeric characters except for the "+" prefix)
        number = ''.join(c for c in number if c.isdigit() or c == '+')
        if not number.startswith('+'):
            # Assume it's a Brazilian number if no country code
            number = f"+55{number}"
            
        payload = {
            "number": number,
            "textMessage": message,
            "options": {
                "delay": 1200,
                "presence": "composing"
            }
        }
        
        params = {"instanceName": self.instance}
        
        try:
            logger.debug(f"Sending message to {number}: {message[:30]}...")
            response = self.session.post(url, json=payload, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Message sent response: {data}")
            return {
                "success": True, 
                "message_id": data.get("key", {}).get("id", "unknown"),
                "data": data
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_message_status(self, message_id):
        """Verifica status de uma mensagem enviada"""
        url = f"{self.base_url}/message/getStatus"
        params = {
            "instanceName": self.instance,
            "id": message_id
        }
        
        try:
            response = self.session.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "status": data.get("status", "unknown"),
                "data": data
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking message status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def setup_webhooks(self, base_url):
        """Configura webhooks para receber eventos do WhatsApp"""
        events = ["onMessage", "onAck", "onPresenceUpdated"]
        results = {}
        
        for event in events:
            url = f"{self.base_url}/webhook/set"
            
            payload = {
                "instanceName": self.instance,
                "webhookUrl": f"{base_url}/webhook/{event}",
                "webhook": event
            }
            
            try:
                response = self.session.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                results[event] = True
            except requests.exceptions.RequestException as e:
                logger.error(f"Error setting up webhook for {event}: {str(e)}")
                results[event] = False
        
        return results
    
    def logout(self):
        """Desconecta a instância do WhatsApp"""
        url = f"{self.base_url}/instance/logout"
        params = {"instanceName": self.instance}
        
        try:
            response = self.session.post(url, params=params, headers=self.headers)
            response.raise_for_status()
            return {"success": True}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error logging out: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def restart(self):
        """Reinicia a instância"""
        url = f"{self.base_url}/instance/restart"
        params = {"instanceName": self.instance}
        
        try:
            response = self.session.post(url, params=params, headers=self.headers)
            response.raise_for_status()
            return {"success": True}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error restarting instance: {str(e)}")
            return {"success": False, "error": str(e)}
