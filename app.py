import os
import logging
import json
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import sqlite3

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-whatsapp-evolution-secret")

# Add this for Replit compatibility
@app.before_request
def before_request():
    # Comentando temporariamente o redirecionamento para debug
    # Force HTTPS for Replit environment
    # if os.environ.get('REPL_SLUG') and request.url.startswith('http://'):
    #     https_url = request.url.replace('http://', 'https://', 1)
    #     return redirect(https_url)
    pass

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///whatsapp_crm.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Configure login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models after initializing db
with app.app_context():
    from models import User, Contact, Campaign, Message, LeadInteraction
    db.create_all()
    
    # Create default admin user if not exists
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@example.com", 
            password_hash=generate_password_hash("admin123")
        )
        db.session.add(admin)
        db.session.commit()
        logger.info("Created default admin user")

# Import other modules
from evolution_api import EvolutionAPI
from crm_manager import CRMManager
from google_sheets import GoogleSheetsManager
from chatbot_engine import ChatbotEngine
from campaign_manager import CampaignManager

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Route imports
from flask_login import login_required, login_user, logout_user, current_user
from flask import render_template, redirect, url_for, request, flash, jsonify

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        from models import User
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Credenciais inválidas. Tente novamente.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Main routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/health')
def health():
    """Rota para verificar a saúde da aplicação - útil para diagnóstico no Replit"""
    return jsonify({
        "status": "ok",
        "version": "1.0.0",
        "server": "running",
        "database": "connected"
    })

@app.route('/dashboard')
@login_required
def dashboard():
    # Get stats for dashboard
    from models import Contact, Campaign, Message
    
    stats = {
        'total_contacts': Contact.query.count(),
        'total_campaigns': Campaign.query.count(),
        'total_messages': Message.query.count(),
        'delivered_messages': Message.query.filter_by(status='delivered').count()
    }
    
    # Get recent campaigns
    recent_campaigns = Campaign.query.order_by(Campaign.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', stats=stats, recent_campaigns=recent_campaigns)

# Campaigns routes
@app.route('/campaigns')
@login_required
def campaigns():
    from models import Campaign
    campaigns_list = Campaign.query.order_by(Campaign.created_at.desc()).all()
    return render_template('campaigns.html', campaigns=campaigns_list)

@app.route('/campaigns/new', methods=['GET', 'POST'])
@login_required
def new_campaign():
    if request.method == 'POST':
        name = request.form.get('name')
        message = request.form.get('message')
        target_group = request.form.get('target_group')
        
        if not name or not message:
            flash('Nome e mensagem são obrigatórios', 'danger')
            return redirect(url_for('new_campaign'))
            
        from models import Campaign
        campaign = Campaign(
            name=name,
            message=message,
            target_group=target_group,
            user_id=current_user.id
        )
        
        db.session.add(campaign)
        db.session.commit()
        
        flash('Campanha criada com sucesso!', 'success')
        return redirect(url_for('campaigns'))
        
    return render_template('campaigns.html', form=True)

@app.route('/campaigns/<int:campaign_id>/execute', methods=['POST'])
@login_required
def execute_campaign(campaign_id):
    from models import Campaign, Contact
    from campaign_manager import CampaignManager
    
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Get contacts for this campaign
    if campaign.target_group == 'all':
        contacts = Contact.query.all()
    else:
        contacts = Contact.query.filter_by(group=campaign.target_group).all()
    
    if not contacts:
        flash('Nenhum contato encontrado para esta campanha', 'warning')
        return redirect(url_for('campaigns'))
    
    # Execute campaign using CampaignManager
    # Importante: Somente passar os IDs dos contatos, não os objetos
    contact_ids = [contact.id for contact in contacts]
    
    # Log para debug
    logging.info(f"Executando campanha {campaign_id} para {len(contact_ids)} contatos")
    
    campaign_manager = CampaignManager()
    result = campaign_manager.execute_campaign(campaign, contact_ids)
    
    if result['success']:
        flash(f'Campanha iniciada! {result["sent"]} mensagens em fila', 'success')
    else:
        flash(f'Erro ao executar campanha: {result["message"]}', 'danger')
    
    return redirect(url_for('campaigns'))

# Contacts routes
@app.route('/contacts')
@login_required
def contacts():
    from models import Contact
    contacts_list = Contact.query.all()
    return render_template('contacts.html', contacts=contacts_list)
    
@app.route('/api/contacts/new', methods=['POST'])
@login_required
def add_contact():
    try:
        data = request.get_json()
        
        name = data.get('name', '')
        phone = data.get('phone', '')
        email = data.get('email', '')
        group = data.get('group', 'default')
        
        # Validação básica
        if not phone:
            return jsonify({'success': False, 'error': 'Telefone é obrigatório'})
            
        # Limpar número de telefone (remover caracteres especiais)
        phone = ''.join(filter(str.isdigit, phone))
        
        # Verificar se já existe um contato com este telefone
        from models import Contact
        existing = Contact.query.filter_by(phone=phone).first()
        
        if existing:
            return jsonify({'success': False, 'error': 'Já existe um contato com este telefone'})
            
        # Criar novo contato
        new_contact = Contact(
            name=name,
            phone=phone,
            email=email,
            group=group,
            status='new'  # Novo contato
        )
        
        db.session.add(new_contact)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Contato adicionado com sucesso!',
            'contact': {
                'id': new_contact.id,
                'name': new_contact.name,
                'phone': new_contact.phone,
                'email': new_contact.email,
                'group': new_contact.group
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao adicionar contato: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/contacts/import/sheets', methods=['POST'])
@login_required
def import_from_sheets():
    from google_sheets import GoogleSheetsManager
    
    spreadsheet_id = request.form.get('spreadsheet_id')
    worksheet_name = request.form.get('worksheet_name')
    
    if not spreadsheet_id or not worksheet_name:
        flash('ID da planilha e nome da aba são obrigatórios', 'danger')
        return redirect(url_for('contacts'))
    
    try:
        sheets_manager = GoogleSheetsManager()
        imported_count = sheets_manager.import_contacts(spreadsheet_id, worksheet_name)
        
        flash(f'{imported_count} contatos importados com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao importar contatos: {str(e)}', 'danger')
    
    return redirect(url_for('contacts'))

# Chatbot routes
@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/chatbot/responses', methods=['GET', 'POST'])
@login_required
def chatbot_responses():
    from chatbot_engine import ChatbotEngine
    
    if request.method == 'POST':
        # Save updated responses
        responses_data = request.json
        chatbot = ChatbotEngine()
        chatbot.save_responses(responses_data)
        return jsonify({'success': True})
    
    # Get current responses
    chatbot = ChatbotEngine()
    responses = chatbot.get_responses()
    return jsonify(responses)

# Settings route
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Update Evolution API settings
        evolution_url = request.form.get('evolution_url')
        evolution_instance = request.form.get('evolution_instance')
        evolution_key = request.form.get('evolution_key')
        
        # Save to session for now (in production would encrypt and save to database)
        session['evolution_url'] = evolution_url
        session['evolution_instance'] = evolution_instance
        if evolution_key:  # Only update if provided
            session['evolution_key'] = evolution_key
        
        flash('Configurações salvas com sucesso!', 'success')
        return redirect(url_for('settings'))
    
    # Verificar se já temos credenciais do Twilio configuradas
    twilio_config = {
        'account_sid': os.environ.get('TWILIO_ACCOUNT_SID', ''),
        'auth_token': os.environ.get('TWILIO_AUTH_TOKEN', ''),
        'phone_number': os.environ.get('TWILIO_PHONE_NUMBER', '')
    }
    
    twilio_configured = all([
        twilio_config['account_sid'], 
        twilio_config['auth_token'], 
        twilio_config['phone_number']
    ])
    
    # Verificar as configurações de envio ativas
    use_twilio = os.environ.get('USE_TWILIO', 'false').lower() == 'true'
    use_whatsapp_link = os.environ.get('USE_WHATSAPP_LINK', 'true').lower() == 'true'
    
    return render_template(
        'settings.html',
        twilio_config=twilio_config,
        twilio_configured=twilio_configured,
        use_twilio=use_twilio,
        use_whatsapp_link=use_whatsapp_link
    )

# API routes for WhatsApp - Implementação Direta
from whatsapp_direct import WhatsAppManager

@app.route('/api/whatsapp/status')
@login_required
def whatsapp_status():
    try:
        session_id = session.get('whatsapp_session', 'default')
        whatsapp = WhatsAppManager().get_session(session_id)
        status = whatsapp.check_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Erro ao verificar status do WhatsApp: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/whatsapp/qrcode')
@login_required
def whatsapp_qrcode():
    try:
        session_id = session.get('whatsapp_session', 'default')
        whatsapp = WhatsAppManager().get_session(session_id)
        qr_code = whatsapp.generate_qr_code()
        
        if qr_code:
            return jsonify({"success": True, "qrcode": qr_code})
        else:
            return jsonify({"success": False, "error": "Não foi possível gerar o QR code"})
    except Exception as e:
        logger.error(f"Erro ao gerar QR code: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/whatsapp/connect', methods=['POST'])
@login_required
def whatsapp_connect():
    try:
        session_id = session.get('whatsapp_session', 'default')
        whatsapp = WhatsAppManager().get_session(session_id)
        result = whatsapp.connect()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Erro ao conectar WhatsApp: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/whatsapp/logout', methods=['POST'])
@login_required
def whatsapp_logout():
    try:
        session_id = session.get('whatsapp_session', 'default')
        whatsapp = WhatsAppManager().get_session(session_id)
        result = whatsapp.disconnect()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Erro ao desconectar WhatsApp: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/whatsapp/restart', methods=['POST'])
@login_required
def whatsapp_restart():
    try:
        session_id = session.get('whatsapp_session', 'default')
        # Remover e recriar a sessão
        WhatsAppManager().remove_session(session_id)
        whatsapp = WhatsAppManager().get_session(session_id)
        return jsonify({"success": True, "status": whatsapp.check_status()})
    except Exception as e:
        logger.error(f"Erro ao reiniciar WhatsApp: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
        
@app.route('/api/whatsapp/set-connection-mode', methods=['POST'])
@login_required
def whatsapp_set_connection_mode():
    try:
        data = request.json
        real_connection = data.get('real_connection', False)
        
        # Configurando variável de ambiente para o modo de conexão
        if real_connection:
            os.environ['WHATSAPP_REAL_CONNECTION'] = 'true'
            logger.info("Modo de conexão WhatsApp: REAL")
        else:
            os.environ['WHATSAPP_REAL_CONNECTION'] = 'false'
            logger.info("Modo de conexão WhatsApp: DEMO")
        
        return jsonify({
            'success': True,
            'real_connection': real_connection,
            'message': 'Modo de conexão atualizado com sucesso'
        })
    except Exception as e:
        logger.error(f"Erro ao configurar modo de conexão: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/whatsapp/setup-webhooks', methods=['POST'])
@login_required
def setup_webhooks():
    # Como estamos usando uma implementação direta, não precisamos de webhooks
    # Mantemos a rota por compatibilidade com a interface
    return jsonify({"success": True, "message": "Integração direta não requer webhooks"})

@app.route('/api/gsheets/save-credentials', methods=['POST'])
@login_required
def save_gsheets_credentials():
    try:
        data = request.json
        credentials = data.get('credentials')
        
        if not credentials:
            return jsonify({"success": False, "error": "Credenciais não fornecidas"})
        
        # In a production app, would securely store in database or env vars
        # For demo, just store in a file
        os.makedirs('config', exist_ok=True)
        with open('config/google_credentials.json', 'w') as f:
            f.write(credentials)
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error saving Google credentials: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
        
@app.route('/api/twilio/save-config', methods=['POST'])
@login_required
def save_twilio_config():
    try:
        data = request.json
        account_sid = data.get('account_sid')
        auth_token = data.get('auth_token')
        phone_number = data.get('phone_number')
        
        # Validar se todos os campos obrigatórios foram fornecidos
        if not all([account_sid, auth_token, phone_number]):
            return jsonify({
                "success": False, 
                "error": "Todas as informações do Twilio são obrigatórias"
            })
        
        # Para o ambiente do Replit, armazenamos nas variáveis de ambiente da sessão
        os.environ['TWILIO_ACCOUNT_SID'] = account_sid
        os.environ['TWILIO_AUTH_TOKEN'] = auth_token
        os.environ['TWILIO_PHONE_NUMBER'] = phone_number
        
        # Opcionalmente, armazene em arquivo para persistência entre reinicializações
        # (Em produção, usaria banco de dados ou variáveis de ambiente do sistema)
        os.makedirs('config', exist_ok=True)
        with open('config/twilio_config.json', 'w') as f:
            json.dump({
                'account_sid': account_sid,
                'auth_token': auth_token,
                'phone_number': phone_number
            }, f)
        
        # Ativar ou desativar o uso do Twilio
        use_twilio = data.get('use_twilio', True)  # Ativar por padrão
        os.environ['USE_TWILIO'] = 'true' if use_twilio else 'false'
        
        # Ativar conexão real para WhatsApp
        os.environ['WHATSAPP_REAL_CONNECTION'] = 'true'
        
        # Log para debug
        logger.info(f"Configuração Twilio atualizada: SID={account_sid[:5]}..., WhatsApp={use_twilio}")
        logger.info(f"Número Twilio configurado: {phone_number}")
        
        # Ativar ou desativar o uso de links diretos
        use_whatsapp_link = data.get('use_whatsapp_link', True)
        os.environ['USE_WHATSAPP_LINK'] = 'true' if use_whatsapp_link else 'false'
        
        return jsonify({
            "success": True,
            "message": "Configuração do Twilio salva com sucesso"
        })
    except Exception as e:
        logger.error(f"Erro ao salvar configuração do Twilio: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
        
@app.route('/api/save_evolution_config', methods=['POST'])
def save_evolution_config():
    """API para salvar configurações da Evolution API"""
    try:
        data = request.json
        
        # Obter os dados do formulário
        api_url = data.get('api_url', '')
        api_key = data.get('api_key', '')
        
        # Validar os dados (básico)
        if not api_url or not api_key:
            return jsonify({"success": False, "error": "Todos os campos são obrigatórios"})
        
        # Inicializar o conector da Evolution API
        from evolution_connector import get_evolution_connector
        evolution = get_evolution_connector()
        
        # Configurar as credenciais
        result = evolution.set_credentials(api_url, api_key)
        
        if not result:
            return jsonify({"success": False, "error": "Falha ao configurar credenciais da Evolution API"})
        
        # Log para debug
        logger.info(f"Configuração Evolution API atualizada: URL={api_url}")
        
        return jsonify({
            "success": True,
            "message": "Configuração da Evolution API salva com sucesso"
        })
    except Exception as e:
        logger.error(f"Erro ao salvar configuração da Evolution API: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

# Webhook for incoming messages
@app.route('/webhook/<event_type>', methods=['POST'])
def webhook(event_type):
    data = request.json
    logger.debug(f"Webhook received {event_type}: {data}")
    
    if event_type == 'onMessage':
        # Process incoming message with chatbot
        try:
            from chatbot_engine import ChatbotEngine
            from crm_manager import CRMManager
            
            # Extract message data
            message = data.get('message', {})
            from_number = message.get('from', '')
            body = message.get('body', '')
            
            # Skip if not a text message or from a group
            if not body or '@g.us' in from_number:
                return jsonify({'success': True})
            
            # Process with chatbot
            chatbot = ChatbotEngine()
            response = chatbot.process_message(from_number, body)
            
            # Send response via implementação direta
            session_id = session.get('whatsapp_session', 'default')
            whatsapp = WhatsAppManager().get_session(session_id)
            whatsapp.send_message(from_number, response)
            
            # Log interaction in CRM
            crm = CRMManager()
            crm.log_interaction(from_number, body, 'in')
            crm.log_interaction(from_number, response, 'out')
            
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})
    
    # Default response for other webhook types
    return jsonify({'success': True})

# API routes for AJAX
@app.route('/api/campaign_stats')
@login_required
def campaign_stats():
    from models import Campaign, Message
    from sqlalchemy import func
    
    # Get message delivery stats for last 7 campaigns
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).limit(7).all()
    
    stats = []
    for campaign in campaigns:
        delivered = Message.query.filter_by(campaign_id=campaign.id, status='delivered').count()
        failed = Message.query.filter_by(campaign_id=campaign.id, status='failed').count()
        pending = Message.query.filter_by(campaign_id=campaign.id, status='pending').count()
        
        stats.append({
            'name': campaign.name,
            'delivered': delivered,
            'failed': failed,
            'pending': pending
        })
    
    return jsonify(stats)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
