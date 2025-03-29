import logging
from datetime import datetime
from app import db
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class CRMManager:
    def __init__(self):
        pass
    
    def get_contact_by_phone(self, phone):
        """Get a contact by phone number, create if not exists"""
        from models import Contact
        
        # Clean phone number - remove non-digit characters except '+' prefix
        cleaned_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        try:
            # Try to find existing contact
            contact = Contact.query.filter_by(phone=cleaned_phone).first()
            
            if not contact:
                # Create new contact
                contact = Contact(
                    phone=cleaned_phone,
                    name="Unknown",
                    status="new"
                )
                db.session.add(contact)
                db.session.commit()
                logger.info(f"Created new contact: {cleaned_phone}")
            
            return contact
        except SQLAlchemyError as e:
            logger.error(f"Database error getting contact: {str(e)}")
            db.session.rollback()
            return None
    
    def log_interaction(self, phone, message, direction):
        """Log an interaction with a contact"""
        from models import LeadInteraction
        
        try:
            # Get or create contact
            contact = self.get_contact_by_phone(phone)
            
            if not contact:
                logger.error(f"Could not get or create contact for {phone}")
                return False
            
            # Create interaction record
            interaction = LeadInteraction(
                contact_id=contact.id,
                message=message,
                direction=direction
            )
            
            db.session.add(interaction)
            db.session.commit()
            
            logger.debug(f"Logged {direction} interaction for {phone}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error logging interaction: {str(e)}")
            db.session.rollback()
            return False
    
    def add_tag_to_contact(self, phone, tag):
        """Add a tag to a contact"""
        from models import ContactTag
        
        try:
            contact = self.get_contact_by_phone(phone)
            
            if not contact:
                logger.error(f"Could not get or create contact for {phone}")
                return False
            
            # Check if tag already exists
            existing_tag = ContactTag.query.filter_by(
                contact_id=contact.id, 
                tag=tag
            ).first()
            
            if not existing_tag:
                # Create new tag
                tag_record = ContactTag(
                    contact_id=contact.id,
                    tag=tag
                )
                db.session.add(tag_record)
                db.session.commit()
                logger.debug(f"Added tag '{tag}' to contact {phone}")
            
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error adding tag: {str(e)}")
            db.session.rollback()
            return False
    
    def update_contact_status(self, phone, status):
        """Update a contact's status"""
        try:
            contact = self.get_contact_by_phone(phone)
            
            if not contact:
                logger.error(f"Could not get or create contact for {phone}")
                return False
            
            contact.status = status
            contact.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.debug(f"Updated status to '{status}' for contact {phone}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error updating contact status: {str(e)}")
            db.session.rollback()
            return False
    
    def get_contact_history(self, phone):
        """Get interaction history for a contact"""
        try:
            contact = self.get_contact_by_phone(phone)
            
            if not contact:
                logger.error(f"Could not get or create contact for {phone}")
                return []
            
            # Get all interactions for this contact
            from models import LeadInteraction
            interactions = LeadInteraction.query.filter_by(
                contact_id=contact.id
            ).order_by(LeadInteraction.created_at.desc()).all()
            
            # Get all tags for this contact
            from models import ContactTag
            tags = ContactTag.query.filter_by(
                contact_id=contact.id
            ).all()
            
            return {
                "contact": {
                    "id": contact.id,
                    "phone": contact.phone,
                    "name": contact.name,
                    "email": contact.email,
                    "status": contact.status,
                    "created_at": contact.created_at.isoformat() if contact.created_at else None,
                    "updated_at": contact.updated_at.isoformat() if contact.updated_at else None
                },
                "interactions": [
                    {
                        "id": interaction.id,
                        "message": interaction.message,
                        "direction": interaction.direction,
                        "created_at": interaction.created_at.isoformat() if interaction.created_at else None
                    }
                    for interaction in interactions
                ],
                "tags": [tag.tag for tag in tags]
            }
        except SQLAlchemyError as e:
            logger.error(f"Database error getting contact history: {str(e)}")
            return {"error": str(e)}
    
    def get_contacts_by_tag(self, tag):
        """Get all contacts with a specific tag"""
        try:
            from models import Contact, ContactTag
            
            # Query contacts that have this tag
            contacts = db.session.query(Contact).join(
                ContactTag, Contact.id == ContactTag.contact_id
            ).filter(ContactTag.tag == tag).all()
            
            return contacts
        except SQLAlchemyError as e:
            logger.error(f"Database error getting contacts by tag: {str(e)}")
            return []
    
    def get_contacts_by_status(self, status):
        """Get all contacts with a specific status"""
        try:
            from models import Contact
            
            contacts = Contact.query.filter_by(status=status).all()
            return contacts
        except SQLAlchemyError as e:
            logger.error(f"Database error getting contacts by status: {str(e)}")
            return []
    
    def update_message_status(self, message_id, status):
        """Update status of a sent message"""
        try:
            from models import Message
            
            message = Message.query.filter_by(message_id=message_id).first()
            
            if message:
                message.status = status
                
                if status == 'delivered':
                    message.delivered_at = datetime.utcnow()
                
                db.session.commit()
                logger.debug(f"Updated message {message_id} status to {status}")
                return True
            else:
                logger.warning(f"Message {message_id} not found")
                return False
        except SQLAlchemyError as e:
            logger.error(f"Database error updating message status: {str(e)}")
            db.session.rollback()
            return False
