import logging
import threading
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from app import db

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CampaignManager:
    def __init__(self):
        pass
        
    def execute_campaign(self, campaign, contact_ids):
        """Execute a campaign by sending messages to all contacts
        
        Args:
            campaign: Objeto Campaign com os dados da campanha
            contact_ids: Lista de IDs de contatos (não objetos Contact)
        """
        try:
            # Update campaign status
            campaign.status = 'running'
            campaign.executed_at = datetime.utcnow()
            campaign.total_contacts = len(contact_ids)
            db.session.commit()
            
            # Start background thread to process messages
            thread = threading.Thread(
                target=self._process_campaign,
                args=(campaign.id, contact_ids),
                daemon=True
            )
            thread.start()
            
            return {"success": True, "sent": len(contact_ids)}
        except Exception as e:
            logger.error(f"Erro ao executar campanha: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def _process_campaign(self, campaign_id, contact_ids):
        """Process campaign messages in background"""
        from models import Campaign, Message, Contact
        from whatsapp_direct import WhatsAppManager
        import time
        from app import app  # Import app para usar app_context
        
        # Usar o contexto da aplicação para operações de banco de dados em threads
        with app.app_context():
            try:
                # Get campaign
                campaign = Campaign.query.get(campaign_id)
                if not campaign:
                    logger.error(f"Campaign {campaign_id} not found")
                    return
                
                # Initialize WhatsApp Direct
                # Não podemos usar session em uma thread em background, usar sessão padrão
                session_id = 'default'
                whatsapp = WhatsAppManager().get_session(session_id)
                
                logger.info(f"Iniciando processamento da campanha {campaign_id} para {len(contact_ids)} contatos")
                
                # Process each contact
                for index, contact_id in enumerate(contact_ids):
                    try:
                        # Obter contato fresco do banco de dados para evitar erro de sessão
                        contact = Contact.query.get(contact_id)
                        if not contact:
                            logger.error(f"Contato {contact_id} não encontrado")
                            continue
                            
                        # Verificar número de telefone
                        if not contact.phone:
                            logger.error(f"Contato {contact_id} sem número de telefone")
                            continue
                            
                        logger.info(f"Processando contato {index+1}/{len(contact_ids)}: {contact.phone}")
                            
                        # Create message record
                        message = Message(
                            campaign_id=campaign.id,
                            contact_id=contact.id,
                            message=campaign.message,
                            status='pending'
                        )
                        db.session.add(message)
                        db.session.commit()
                        
                        # Send message via WhatsApp Direct
                        result = whatsapp.send_message(contact.phone, campaign.message)
                        logger.info(f"Resultado do envio para {contact.phone}: {result}")
                        
                        if result.get('success'):
                            # Update message with API response
                            message.message_id = result.get('message_id')
                            message.status = 'sent'
                            message.sent_at = datetime.utcnow()
                            
                            # Update campaign stats
                            campaign.sent_messages += 1
                        else:
                            # Update message as failed
                            message.status = 'failed'
                            
                            # Update campaign stats
                            campaign.failed_messages += 1
                        
                        db.session.commit()
                        
                        # Sleep to avoid rate limiting (adjust based on API limits)
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Erro ao enviar mensagem: {str(e)}")
                        continue
                
                # Update campaign as completed
                campaign.status = 'completed'
                db.session.commit()
                
                logger.info(f"Campanha {campaign_id} concluída")
                
            except SQLAlchemyError as e:
                logger.error(f"Erro de banco de dados no processamento da campanha: {str(e)}")
                db.session.rollback()
                
                # Try to mark campaign as failed
                try:
                    campaign = Campaign.query.get(campaign_id)
                    if campaign:
                        campaign.status = 'failed'
                        db.session.commit()
                except Exception as ex:
                    logger.error(f"Erro ao marcar campanha como falha: {str(ex)}")
                    pass
    
    def check_message_statuses(self, campaign_id):
        """Check delivery status of all messages in a campaign"""
        from models import Campaign, Message
        from whatsapp_direct import WhatsAppManager
        
        try:
            # Get all sent messages for this campaign
            messages = Message.query.filter_by(
                campaign_id=campaign_id,
                status='sent'
            ).all()
            
            if not messages:
                logger.info(f"No sent messages to check for campaign {campaign_id}")
                return {"success": True, "checked": 0, "updated": 0}
            
            # Initialize WhatsApp Direct
            # Em uma aplicação real, use um ID de sessão ou configuração global
            session_id = 'default'
            whatsapp = WhatsAppManager().get_session(session_id)
            
            updated_count = 0
            
            # Check each message
            for message in messages:
                if not message.message_id:
                    continue
                    
                # Check status via WhatsApp Direct
                result = whatsapp.check_message_status(message.message_id)
                
                if result['success']:
                    new_status = result['status']
                    
                    if new_status != message.status:
                        # Update message status
                        message.status = new_status
                        
                        if new_status == 'delivered':
                            message.delivered_at = datetime.utcnow()
                            
                            # Update campaign stats
                            campaign = Campaign.query.get(campaign_id)
                            campaign.delivered_messages += 1
                        
                        db.session.commit()
                        updated_count += 1
                
                # Sleep to avoid rate limiting
                time.sleep(0.2)
            
            return {"success": True, "checked": len(messages), "updated": updated_count}
            
        except Exception as e:
            logger.error(f"Error checking message statuses: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_campaign_stats(self, campaign_id):
        """Get statistics for a campaign"""
        from models import Campaign, Message
        
        try:
            campaign = Campaign.query.get(campaign_id)
            
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            # Get message counts by status
            pending = Message.query.filter_by(campaign_id=campaign_id, status='pending').count()
            sent = Message.query.filter_by(campaign_id=campaign_id, status='sent').count()
            delivered = Message.query.filter_by(campaign_id=campaign_id, status='delivered').count()
            failed = Message.query.filter_by(campaign_id=campaign_id, status='failed').count()
            
            # Calculate delivery rate
            total = pending + sent + delivered + failed
            delivery_rate = (delivered / total) * 100 if total > 0 else 0
            
            return {
                "success": True,
                "stats": {
                    "name": campaign.name,
                    "status": campaign.status,
                    "total_contacts": campaign.total_contacts,
                    "pending": pending,
                    "sent": sent,
                    "delivered": delivered,
                    "failed": failed,
                    "delivery_rate": round(delivery_rate, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting campaign stats: {str(e)}")
            return {"success": False, "error": str(e)}