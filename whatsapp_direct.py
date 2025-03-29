import os
import logging
import json
from datetime import datetime

from evolution_connector import get_evolution_connector

logger = logging.getLogger(__name__)

class WhatsAppSession:
    """Classe para gerenciar uma sessão de WhatsApp usando a Evolution API"""
    
    def __init__(self, session_id='default'):
        self.session_id = session_id
        self.status = 'disconnected'
        self.connected_at = None
        self.messages_history = []
        self.session_file = f'config/whatsapp_session_{session_id}.json'
        
        # Inicializar conector da Evolution API
        self.evolution = get_evolution_connector()
        
        # Carregar dados da sessão se existirem
        self._load_session()
    
    def _load_session(self):
        """Carrega dados da sessão de um arquivo, se existir"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self.status = data.get('status', 'disconnected')
                    self.connected_at = data.get('connected_at')
                    if 'messages_history' in data:
                        self.messages_history = data.get('messages_history', [])
        except Exception as e:
            logger.error(f"Erro ao carregar sessão: {str(e)}")
    
    def _save_session(self):
        """Salva dados da sessão em um arquivo"""
        try:
            os.makedirs('config', exist_ok=True)
            data = {
                'status': self.status,
                'connected_at': self.connected_at,
                'messages_history': self.messages_history[:100],  # Manter apenas as 100 mensagens mais recentes
                'last_updated': datetime.now().isoformat()
            }
            with open(self.session_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Erro ao salvar sessão: {str(e)}")
    
    def generate_qr_code(self):
        """Obtém um QR code para conexão com o WhatsApp"""
        try:
            # Usar a Evolution API para gerar o QR code
            result = self.evolution.get_qr_code()
            if result.get('success'):
                return {
                    'success': True,
                    'qrcode': result.get('qrcode'),
                    'message': result.get('message', 'Escaneie este QR code com seu WhatsApp')
                }
            else:
                logger.error(f"Erro ao obter QR code: {result.get('error', 'Erro desconhecido')}")
                return result
        except Exception as e:
            logger.error(f"Erro ao gerar QR code: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def connect(self):
        """Inicia a conexão com o WhatsApp (via Evolution API)"""
        try:
            result = self.evolution.start()
            if result.get('success'):
                # Atualizar status apenas se obteve sucesso
                self.status = 'connecting'
                self._save_session()
                logger.info(f"Iniciando conexão com WhatsApp para sessão {self.session_id}")
            return result
        except Exception as e:
            logger.error(f"Erro ao iniciar conexão: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def disconnect(self):
        """Desconecta a sessão de WhatsApp"""
        try:
            result = self.evolution.disconnect()
            if result.get('success'):
                self.status = 'disconnected'
                self.connected_at = None
                self._save_session()
            return result
        except Exception as e:
            logger.error(f"Erro ao desconectar: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_status(self):
        """Verifica o status da conexão"""
        try:
            result = self.evolution.check_status()
            if result.get('success'):
                connected = result.get('connected', False)
                status = result.get('status', 'unknown')
                
                # Atualizar status da sessão
                if self.status != status:
                    self.status = status
                    if connected and not self.connected_at:
                        self.connected_at = datetime.now().isoformat()
                    elif not connected:
                        self.connected_at = None
                    self._save_session()
                
                return {
                    'success': True,
                    'connected': connected,
                    'status': status,
                    'connected_at': self.connected_at
                }
            return result
        except Exception as e:
            logger.error(f"Erro ao verificar status: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_message(self, phone, message):
        """Envia uma mensagem via WhatsApp"""
        try:
            # Verificar o status atual da conexão
            status_check = self.check_status()
            if not status_check.get('connected', False):
                return {
                    'success': False, 
                    'error': f"WhatsApp não conectado. Status: {status_check.get('status', 'desconhecido')}"
                }
            
            # Preparar número de telefone (formatar se necessário)
            if not phone.startswith('+'):
                # Se não começar com +, assume Brasil
                if len(phone) <= 11:  # número local
                    phone = '+55' + phone
                else:
                    phone = '+' + phone
            
            # Gerar ID único para a mensagem (temporário)
            temp_message_id = f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(phone + message) % 1000000}"
            
            # Registrar a mensagem no histórico como pendente
            msg_data = {
                'id': temp_message_id,
                'phone': phone,
                'message': message,
                'status': 'sending',
                'timestamp': datetime.now().isoformat()
            }
            self.messages_history.append(msg_data)
            
            # Enviar a mensagem via Evolution API
            logger.info(f"Enviando mensagem via Evolution API para {phone}")
            result = self.evolution.send_message(phone, message)
            
            # Atualizar o histórico com o resultado
            for idx, msg in enumerate(self.messages_history):
                if msg['id'] == temp_message_id:
                    if result.get('success'):
                        # Substituir o ID temporário pelo ID real retornado pela API
                        real_message_id = result.get('message_id', temp_message_id)
                        msg['id'] = real_message_id
                        msg['status'] = 'sent'
                        msg['evolution_message_id'] = real_message_id
                    else:
                        msg['status'] = 'failed'
                        msg['error'] = result.get('error', 'Falha no envio')
                    
                    # Atualizar o histórico
                    self.messages_history[idx] = msg
                    break
            
            # Salvar a sessão atualizada
            self._save_session()
            
            return result
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_message_status(self, message_id):
        """Verifica o status de uma mensagem enviada"""
        try:
            # Primeiro verifica no histórico local
            for msg in self.messages_history:
                if msg['id'] == message_id:
                    if msg['status'] in ['failed', 'pending', 'sending']:
                        return {
                            'success': True,
                            'status': msg['status'],
                            'data': msg
                        }
                    
                    # Se não estiver em um estado final, consultar a API para atualização
                    break
            
            # Consultar status via Evolution API
            result = self.evolution.check_message_status(message_id)
            
            # Atualizar o histórico com o resultado
            if result.get('success'):
                for idx, msg in enumerate(self.messages_history):
                    if msg['id'] == message_id:
                        msg['status'] = result.get('status', msg['status'])
                        msg['updated_at'] = datetime.now().isoformat()
                        self.messages_history[idx] = msg
                        self._save_session()
                        break
            
            return result
        except Exception as e:
            logger.error(f"Erro ao verificar status da mensagem: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def restart(self):
        """Reinicia a sessão do WhatsApp"""
        try:
            return self.evolution.restart()
        except Exception as e:
            logger.error(f"Erro ao reiniciar sessão: {str(e)}")
            return {'success': False, 'error': str(e)}

class WhatsAppManager:
    """Gerenciador de sessões de WhatsApp"""
    _instance = None
    _sessions = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WhatsAppManager, cls).__new__(cls)
        return cls._instance
    
    def get_session(self, session_id='default'):
        """Obtém ou cria uma sessão de WhatsApp"""
        if session_id not in self._sessions:
            self._sessions[session_id] = WhatsAppSession(session_id)
        return self._sessions[session_id]
    
    def remove_session(self, session_id):
        """Remove uma sessão"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False