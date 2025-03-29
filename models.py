from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Relationships
    campaigns = relationship("Campaign", backref="creator", lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    group = db.Column(db.String(50), default='default')
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", backref="contact", lazy=True)
    interactions = relationship("LeadInteraction", backref="contact", lazy=True)
    tags = relationship("ContactTag", backref="contact", lazy=True)
    
    def __repr__(self):
        return f'<Contact {self.phone}>'

class ContactTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    tag = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ContactTag {self.tag}>'

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    target_group = db.Column(db.String(50), default='all')
    status = db.Column(db.String(20), default='draft')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    executed_at = db.Column(db.DateTime)
    
    # Stats fields
    total_contacts = db.Column(db.Integer, default=0)
    sent_messages = db.Column(db.Integer, default=0)
    delivered_messages = db.Column(db.Integer, default=0)
    failed_messages = db.Column(db.Integer, default=0)
    
    # Relationships
    messages = relationship("Message", backref="campaign", lazy=True)
    
    def __repr__(self):
        return f'<Campaign {self.name}>'

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    message_id = db.Column(db.String(100))  # ID returned from Evolution API
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Message {self.id}>'

class LeadInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # 'in' or 'out'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LeadInteraction {self.id}>'

class ChatbotContext(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_phone = db.Column(db.String(20), nullable=False)
    context = db.Column(db.Text, nullable=False)  # JSON data with context
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatbotContext {self.contact_phone}>'
