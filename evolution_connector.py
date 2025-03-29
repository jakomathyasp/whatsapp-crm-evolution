import os
import logging
import threading
import json
import time
import qrcode
import base64
import io
from datetime import datetime

from evolution_api import EvolutionAPI

logger = logging.getLogger(__name__)

class EvolutionWhatsAppConnector:
    """Conector para a Evolution API (WhatsApp)"""
    
    def __init__(self, instance_name="whatsapp_crm"):
        # Carregar configurações da Evolution API
        self.instance_name = instance_name
        self.api_url = os.environ.get("EVOLUTION_API_URL", "")
        self.api_key = os.environ.get("EVOLUTION_API_KEY", "")
        
        # Inicializar a API da Evolution (se houver configuração)
        self.evolution = None
        self.connection_status = "disconnected"
        self.qr_code_base64 = None
        self.last_check = None
        
        # Tentar inicializar a API
        self._init_api()
        
        # Verificar status a cada 1 minuto
        self._start_status_check()
    
    def _init_api(self):
        """Inicializa a conexão com a Evolution API se as credenciais estiverem disponíveis"""
        if self.api_url and self.api_key:
            logger.info(f"Inicializando Evolution API: {self.api_url}")
            self.evolution = EvolutionAPI(
                instance_name=self.instance_name,
                base_url=self.api_url,
                api_key=self.api_key
            )
            return True
        else:
            logger.warning("Credenciais da Evolution API não configuradas")
            return False
    
    def set_credentials(self, api_url, api_key):
        """Define as credenciais da Evolution API"""
        self.api_url = api_url
        self.api_key = api_key
        
        # Atualizar as variáveis de ambiente
        os.environ["EVOLUTION_API_URL"] = api_url
        os.environ["EVOLUTION_API_KEY"] = api_key
        
        # Salvar as credenciais em arquivo de configuração
        os.makedirs('config', exist_ok=True)
        with open('config/evolution_config.json', 'w') as f:
            json.dump({
                'api_url': api_url,
                'api_key': api_key,
                'instance_name': self.instance_name
            }, f)
        
        # Reinicializar a API
        return self._init_api()
    
    def _start_status_check(self):
        """Inicia verificação periódica de status em background"""
        def check_status_periodically():
            while True:
                try:
                    if self.evolution:
                        result = self.evolution.connection_status()
                        if result.get('success'):
                            self.connection_status = result.get('state', 'DISCONNECTED').lower()
                            self.last_check = datetime.now()
                            logger.debug(f"Status WhatsApp Evolution: {self.connection_status}")
                except Exception as e:
                    logger.error(f"Erro na verificação de status da Evolution API: {e}")
                
                # Verificar a cada 60 segundos
                time.sleep(60)
        
        # Iniciar thread em background
        thread = threading.Thread(target=check_status_periodically, daemon=True)
        thread.start()
    
    def start(self):
        """Inicia a instância do WhatsApp"""
        if not self.evolution:
            return {"success": False, "error": "Evolution API não configurada"}
        
        try:
            result = self.evolution.start_instance()
            if result.get('success'):
                return {"success": True, "message": "Instância iniciada com sucesso"}
            return result
        except Exception as e:
            logger.error(f"Erro ao iniciar instância: {e}")
            return {"success": False, "error": str(e)}
    
    def get_qr_code(self):
        """Obtém o QR code para conexão"""
        if not self.evolution:
            # Se a Evolution API não estiver configurada, geramos um QR code informativo
            img = qrcode.make("https://evolution-api.com/connect")
            buffered = io.BytesIO()
            img.save(buffered)
            self.qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return {
                "success": True,
                "qrcode": self.qr_code_base64,
                "message": "QR code demonstrativo - Configure a Evolution API"
            }
            
        try:
            result = self.evolution.get_qr_code()
            if result.get('success'):
                self.qr_code_base64 = result.get('qrcode')
                return {
                    "success": True,
                    "qrcode": self.qr_code_base64
                }
            return result
        except Exception as e:
            logger.error(f"Erro ao obter QR code: {e}")
            return {"success": False, "error": str(e)}
    
    def check_status(self):
        """Verifica o status da conexão"""
        if not self.evolution:
            return {
                "success": False, 
                "connected": False,
                "status": "not_configured",
                "message": "Evolution API não configurada"
            }
            
        try:
            result = self.evolution.connection_status()
            if result.get('success'):
                self.connection_status = result.get('state', 'DISCONNECTED').lower()
                return {
                    "success": True,
                    "connected": result.get('connected', False),
                    "status": self.connection_status
                }
            return result
        except Exception as e:
            logger.error(f"Erro ao verificar status: {e}")
            return {"success": False, "error": str(e)}
    
    def send_message(self, phone, message):
        """Envia uma mensagem para um número"""
        if not self.evolution:
            return {
                "success": False, 
                "error": "Evolution API não configurada"
            }
        
        # Verificar se está conectado
        status_result = self.check_status()
        if not status_result.get('connected'):
            return {
                "success": False,
                "error": f"WhatsApp não conectado. Status: {status_result.get('status')}"
            }
            
        try:
            # Formatar número
            if not phone.startswith('+'):
                # Se não tem o +, assumimos Brasil e adicionamos +55
                if len(phone) <= 11:
                    phone = '+55' + phone
                else:
                    phone = '+' + phone
            
            logger.info(f"Enviando mensagem via Evolution API para {phone}")
            result = self.evolution.send_message(phone, message)
            if result.get('success'):
                return {
                    "success": True,
                    "message_id": result.get('message_id'),
                    "status": "sent",
                    "provider": "evolution_api"
                }
            return result
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return {"success": False, "error": str(e)}
    
    def check_message_status(self, message_id):
        """Verifica o status de uma mensagem enviada"""
        if not self.evolution:
            return {"success": False, "error": "Evolution API não configurada"}
            
        try:
            result = self.evolution.check_message_status(message_id)
            return result
        except Exception as e:
            logger.error(f"Erro ao verificar status da mensagem: {e}")
            return {"success": False, "error": str(e)}
    
    def disconnect(self):
        """Desconecta o WhatsApp"""
        if not self.evolution:
            return {"success": False, "error": "Evolution API não configurada"}
            
        try:
            result = self.evolution.logout()
            if result.get('success'):
                self.connection_status = "disconnected"
                return {"success": True, "message": "Desconectado com sucesso"}
            return result
        except Exception as e:
            logger.error(f"Erro ao desconectar: {e}")
            return {"success": False, "error": str(e)}
    
    def restart(self):
        """Reinicia a instância do WhatsApp"""
        if not self.evolution:
            return {"success": False, "error": "Evolution API não configurada"}
            
        try:
            result = self.evolution.restart()
            if result.get('success'):
                return {"success": True, "message": "Instância reiniciada com sucesso"}
            return result
        except Exception as e:
            logger.error(f"Erro ao reiniciar instância: {e}")
            return {"success": False, "error": str(e)}

# Singleton para manter uma única instância do conector
_evolution_connector = None

def get_evolution_connector():
    """Obtém a instância singleton do conector Evolution API"""
    global _evolution_connector
    if _evolution_connector is None:
        _evolution_connector = EvolutionWhatsAppConnector()
    return _evolution_connector