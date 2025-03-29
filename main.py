from app import app

# Make sure app is imported and available
print("Iniciando a aplicação de CRM WhatsApp...")

# Configuração da aplicação para funcionar no Replit
if __name__ == "__main__":
    # Use debug=True for development
    print("Servidor iniciado na porta 5000")
    print("Acesse: https://[seu-replit].replit.dev/")
    app.run(host="0.0.0.0", port=5000, debug=True)
