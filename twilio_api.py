import os
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

# Verificar se as credenciais do Twilio estão configuradas
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
TWILIO_AVAILABLE = all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER])

if not TWILIO_AVAILABLE:
    logger.warning("Credenciais do Twilio não encontradas. A funcionalidade de SMS direto estará indisponível.")
else:
    logger.info("Twilio configurado com sucesso!")


def send_twilio_message(to_phone_number: str, message: str) -> dict:
    """
    Envia uma mensagem SMS ou WhatsApp usando o Twilio.
    
    Args:
        to_phone_number (str): Número de telefone de destino (com código do país)
        message (str): Texto da mensagem a ser enviada
        
    Returns:
        dict: Resultado da operação com status e identificador da mensagem
    """
    if not TWILIO_AVAILABLE:
        return {
            "success": False, 
            "error": "Credenciais do Twilio não configuradas",
            "status": "error"
        }
    
    try:
        # Formatar o número de telefone (remover caracteres não numéricos)
        clean_phone = ''.join(filter(str.isdigit, to_phone_number))
        
        # Adicionar o "+" se não estiver presente
        if not clean_phone.startswith('+'):
            clean_phone = '+' + clean_phone
        
        # Inicializar o cliente Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Verificar se é uma mensagem WhatsApp ou SMS 
        # Para WhatsApp, o número de destino precisa ter o prefixo "whatsapp:"
        use_whatsapp = False  # Vamos usar SMS por padrão (WhatsApp requer registro)
        
        # Log detalhado dos parâmetros
        logger.info(f"Enviando mensagem Twilio - Modo: {'WhatsApp' if use_whatsapp else 'SMS'}")
        logger.info(f"Número de origem: {TWILIO_PHONE_NUMBER}")
        logger.info(f"Número de destino: {clean_phone}")
        
        if use_whatsapp:
            # Formatando para o formato exigido pelo Twilio WhatsApp
            # Garantir que os números existem antes de concatenar
            if TWILIO_PHONE_NUMBER and clean_phone:
                from_number = 'whatsapp:' + TWILIO_PHONE_NUMBER
                to_number = 'whatsapp:' + clean_phone
            else:
                return {
                    "success": False,
                    "error": "Número de telefone inválido ou não configurado",
                    "status": "error"
                }
        else:
            # Para SMS normal
            from_number = TWILIO_PHONE_NUMBER
            to_number = clean_phone
            
        # Log final dos números formatados
        logger.info(f"Número formatado (origem): {from_number}")
        logger.info(f"Número formatado (destino): {to_number}")
        
        # Enviar a mensagem
        message_obj = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )
        
        logger.info(f"Mensagem Twilio enviada com sucesso via {'WhatsApp' if use_whatsapp else 'SMS'}. SID: {message_obj.sid}")
        
        return {
            "success": True,
            "message_id": message_obj.sid,
            "status": "sent",
            "provider": "twilio_whatsapp" if use_whatsapp else "twilio_sms"
        }
    
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem via Twilio: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "status": "error",
            "provider": "twilio"
        }


def check_twilio_message_status(message_sid: str) -> dict:
    """
    Verifica o status de uma mensagem enviada pelo Twilio.
    
    Args:
        message_sid (str): ID da mensagem Twilio
        
    Returns:
        dict: Status atualizado da mensagem
    """
    if not TWILIO_AVAILABLE:
        return {
            "success": False,
            "error": "Credenciais do Twilio não configuradas",
            "status": "unknown"
        }
        
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages(message_sid).fetch()
        
        # Mapeando os status do Twilio para nossos status
        status_map = {
            'queued': 'pending',
            'sending': 'processing',
            'sent': 'sent',
            'delivered': 'delivered',
            'undelivered': 'failed',
            'failed': 'failed'
        }
        
        mapped_status = status_map.get(message.status, message.status)
        
        return {
            "success": True,
            "message_id": message_sid,
            "status": mapped_status,
            "twilio_status": message.status,
            "provider": "twilio"
        }
    
    except Exception as e:
        logger.error(f"Erro ao verificar status da mensagem Twilio: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "status": "unknown",
            "provider": "twilio"
        }