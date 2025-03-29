import json
import os
import re
import logging
from datetime import datetime
from difflib import SequenceMatcher
import random

logger = logging.getLogger(__name__)

class ChatbotEngine:
    def __init__(self):
        self.responses = self._load_responses()
        self.contexts = {}
    
    def _load_responses(self):
        """Carrega as respostas do arquivo de configuração JSON"""
        try:
            # Ensure directory exists
            os.makedirs('config', exist_ok=True)
            
            if not os.path.exists('config/chatbot_responses.json'):
                # Create default responses file if it doesn't exist
                self._save_default_responses()
                
            with open('config/chatbot_responses.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading responses: {str(e)}")
            return self._default_responses()
    
    def _default_responses(self):
        """Define respostas padrão para o chatbot"""
        return {
            "greetings": {
                "patterns": ["oi", "olá", "bom dia", "boa tarde", "boa noite", "tudo bem"],
                "responses": [
                    "Olá! Como posso ajudar você hoje?",
                    "Oi! Em que posso ser útil?"
                ],
                "tags": ["saudação"]
            },
            "about": {
                "patterns": ["quem é você", "o que você faz", "sobre você", "como funciona"],
                "responses": [
                    "Sou um assistente virtual pronto para ajudar com informações sobre nossos produtos e serviços!"
                ],
                "tags": ["informação"]
            },
            "price_request": {
                "patterns": ["preço", "quanto custa", "valor", "preços", "planos"],
                "responses": [
                    "Temos opções a partir de R$99,90. Posso enviar nosso catálogo completo?",
                    "Nossos valores variam de acordo com o plano escolhido. Gostaria de receber mais informações?"
                ],
                "tags": ["interesse", "preço"]
            },
            "contact": {
                "patterns": ["falar com atendente", "atendimento humano", "pessoa real", "consultor"],
                "responses": [
                    "Certo! Vou encaminhar você para um de nossos atendentes. Por favor, aguarde um momento."
                ],
                "tags": ["atendimento"]
            },
            "thanks": {
                "patterns": ["obrigado", "obrigada", "grato", "valeu", "agradeço"],
                "responses": [
                    "Por nada! Estou aqui para ajudar.",
                    "Disponha! Se precisar de mais alguma coisa, é só chamar."
                ],
                "tags": ["satisfação"]
            },
            "fallback": {
                "patterns": [],
                "responses": [
                    "Desculpe, não entendi. Poderia reformular sua pergunta?",
                    "Não compreendi sua mensagem. Poderia explicar de outra forma?"
                ],
                "tags": ["confusão"]
            }
        }
    
    def _save_default_responses(self):
        """Salva as respostas padrão no arquivo de configuração"""
        try:
            os.makedirs('config', exist_ok=True)
            with open('config/chatbot_responses.json', 'w', encoding='utf-8') as f:
                json.dump(self._default_responses(), f, indent=4, ensure_ascii=False)
            logger.info("Default responses saved to config file")
            return True
        except Exception as e:
            logger.error(f"Error saving default responses: {str(e)}")
            return False
    
    def save_responses(self, responses):
        """Salva as respostas atualizadas no arquivo de configuração"""
        try:
            os.makedirs('config', exist_ok=True)
            with open('config/chatbot_responses.json', 'w', encoding='utf-8') as f:
                json.dump(responses, f, indent=4, ensure_ascii=False)
            self.responses = responses
            logger.info("Updated responses saved to config file")
            return True
        except Exception as e:
            logger.error(f"Error saving responses: {str(e)}")
            return False
    
    def get_responses(self):
        """Retorna todas as respostas configuradas"""
        return self.responses
    
    def _similarity(self, a, b):
        """Calcula a similaridade entre duas strings"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def process_message(self, contact_number, message, context=None):
        """Processa uma mensagem recebida e retorna uma resposta apropriada"""
        # Normalize message
        message = message.lower().strip()
        
        logger.debug(f"Processing message from {contact_number}: {message}")
        
        # Check if there's an active context for this contact
        if contact_number in self.contexts:
            ctx = self.contexts[contact_number]
            if datetime.now().timestamp() - ctx.get('timestamp', 0) < 3600:  # Context valid for 1 hour
                return self._handle_context_response(contact_number, message, ctx)
            else:
                # Context expired
                del self.contexts[contact_number]
        
        # Find best matching intent
        best_match = None
        highest_score = 0
        
        for intent_name, intent_data in self.responses.items():
            for pattern in intent_data['patterns']:
                score = self._similarity(message, pattern)
                if score > 0.7 and score > highest_score:  # Threshold for matching
                    highest_score = score
                    best_match = (intent_name, intent_data)
        
        # Process the best match
        if best_match:
            intent_name, intent_data = best_match
            response = random.choice(intent_data['responses'])
            
            # Log interaction and update CRM (in a real app)
            logger.info(f"Matched intent '{intent_name}' for message: {message}")
            
            # Set context if needed
            if intent_name in ['price_request', 'contact']:
                self.contexts[contact_number] = {
                    'intent': intent_name,
                    'timestamp': datetime.now().timestamp()
                }
            
            return response
        
        # No match found, return fallback response
        fallback = self.responses.get('fallback', {})
        fallback_responses = fallback.get('responses', ["Desculpe, não entendi."])
        return random.choice(fallback_responses)
    
    def _handle_context_response(self, contact_number, message, context):
        """Handle responses within a conversational context"""
        intent = context.get('intent')
        
        if intent == 'price_request':
            positive_words = ['sim', 'quero', 'claro', 'envie', 'enviar', 'pode', 'manda']
            negative_words = ['não', 'nao', 'agora não', 'depois', 'talvez']
            
            if any(word in message for word in positive_words):
                # User wants price information
                self.contexts[contact_number] = {
                    'intent': 'catalog_sent',
                    'timestamp': datetime.now().timestamp()
                }
                return ("Ótimo! Aqui está nosso catálogo de preços:\n\n"
                        "Plano Básico: R$99,90/mês\n"
                        "Plano Profissional: R$199,90/mês\n"
                        "Plano Enterprise: R$499,90/mês\n\n"
                        "Gostaria de falar com um consultor para mais detalhes?")
            
            elif any(word in message for word in negative_words):
                # User doesn't want price information now
                del self.contexts[contact_number]
                return "Sem problemas! Se precisar de informações no futuro, estou à disposição."
            
            else:
                # Unclear response
                return "Desculpe, não entendi. Você gostaria de receber nosso catálogo de preços?"
        
        elif intent == 'contact':
            # This would actually trigger a notification to a human agent
            # For this demo, we'll just simulate the handoff
            del self.contexts[contact_number]
            return "Um de nossos consultores entrará em contato em breve. Obrigado pela sua paciência!"
        
        elif intent == 'catalog_sent':
            positive_words = ['sim', 'quero', 'claro', 'gostaria', 'pode', 'vamos']
            negative_words = ['não', 'nao', 'agora não', 'depois', 'talvez']
            
            if any(word in message for word in positive_words):
                del self.contexts[contact_number]
                return "Perfeito! Estou encaminhando seu contato para um de nossos consultores especializados. Em breve ele entrará em contato com você."
            
            elif any(word in message for word in negative_words):
                del self.contexts[contact_number]
                return "Entendi! Se tiver mais dúvidas ou quiser falar com um consultor mais tarde, é só avisar."
            
            else:
                return "Gostaria de conversar com um de nossos consultores para obter mais detalhes sobre os planos?"
        
        # Default context response if we don't have specific handling
        del self.contexts[contact_number]
        return "Como posso ajudar você agora?"
