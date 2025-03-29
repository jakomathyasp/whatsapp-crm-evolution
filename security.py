import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self):
        # Get encryption key from environment or generate one
        self.encryption_key = os.environ.get('ENCRYPTION_KEY')
        
        if not self.encryption_key:
            logger.warning("Encryption key not found in environment, using default (insecure)")
            self.encryption_key = "default-whatsapp-crm-encryption-key-change-me"
        
        # Derive a key using PBKDF2
        salt = b'whatsapp-crm-salt'  # In production, use a secure random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
        self.cipher = Fernet(key)
    
    def encrypt(self, data):
        """Encrypt sensitive data"""
        if data is None:
            return None
            
        try:
            if isinstance(data, str):
                data = data.encode()
            
            encrypted = self.cipher.encrypt(data)
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            return None
    
    def decrypt(self, encrypted_data):
        """Decrypt encrypted data"""
        if encrypted_data is None:
            return None
            
        try:
            if isinstance(encrypted_data, str):
                encrypted_data = encrypted_data.encode()
            
            decrypted = self.cipher.decrypt(encrypted_data)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            return None

# Global function for encrypting phone numbers
def encrypt_phone(phone):
    return SecurityManager().encrypt(phone)

# Global function for decrypting phone numbers
def decrypt_phone(encrypted_phone):
    return SecurityManager().decrypt(encrypted_phone)

# Function to securely store API keys and credentials
def store_credential(key, value):
    encrypted = SecurityManager().encrypt(value)
    
    # In a real application, you would store this in a secure database
    # For now, we're using environment variables
    os.environ[f"{key}_ENCRYPTED"] = encrypted
    
    return True

# Function to retrieve stored credentials
def get_credential(key):
    encrypted = os.environ.get(f"{key}_ENCRYPTED")
    
    if not encrypted:
        return None
    
    return SecurityManager().decrypt(encrypted)
