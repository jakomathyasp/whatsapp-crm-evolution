# Sistema Completo de Disparo WhatsApp com Evolution API

## Descrição
Sistema de comunicação automatizada via WhatsApp com recursos como:
- Disparo em massa de mensagens
- Chatbot inteligente com respostas contextualizadas
- Integração com planilhas Google Sheets
- CRM completo com etiquetagem automática
- Dashboard analítico

## Requisitos do Sistema

### Requisitos para uso com Evolution API (Recomendado)
1. **Instalação local** - Este sistema deve ser executado no mesmo ambiente (localhost) onde a Evolution API está instalada
2. Evolution API configurada e funcionando
3. Python 3.8+ ou Docker

## Instalação e Configuração

### Opção 1: Instalação com Docker (Recomendado se você já usa Docker Desktop)

Se você já tem a Evolution API rodando no Docker Desktop, esta é a maneira mais fácil de configurar:

1. Clone este repositório:
```bash
git clone https://github.com/seu-usuario/whatsapp-crm-evolution.git
cd whatsapp-crm-evolution
```

2. Crie um arquivo `Dockerfile` na raiz do projeto:
```Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

ENV FLASK_APP=main.py
ENV SECRET_KEY=chave-secreta-para-sessoes
ENV EVOLUTION_API_URL=http://host.docker.internal:8080
ENV EVOLUTION_API_KEY=sua-chave-da-api

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"]
```

3. Crie um arquivo `docker-compose.yml`:
```yaml
version: '3'

services:
  whatsapp_crm:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - .:/app
    environment:
      - EVOLUTION_API_URL=http://host.docker.internal:8080
      - EVOLUTION_API_KEY=sua-chave-da-api
      - SECRET_KEY=chave-secreta-para-sessoes
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

4. Construa e inicie o contêiner:
```bash
docker-compose up --build
```

5. Acesse o sistema em: http://localhost:5000

> **Notas para o Docker:**
> - `host.docker.internal` é uma DNS especial dentro do Docker que aponta para o host local (seu computador)
> - O parâmetro `extra_hosts` garante que o contêiner possa se comunicar com o host
> - Se sua Evolution API estiver em um contêiner Docker com nome personalizado, use esse nome no lugar de `host.docker.internal`

### Opção 2: Instalação tradicional (Python local)

1. Clone este repositório:
```bash
git clone https://github.com/seu-usuario/whatsapp-crm-evolution.git
cd whatsapp-crm-evolution
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente no arquivo `.env`:
```
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=sua-chave-da-api
SECRET_KEY=chave-secreta-para-sessoes
```

4. Inicie o sistema:
```bash
python main.py
```

5. Acesse o sistema em: http://localhost:5000

## Configuração da Evolution API

A Evolution API precisa estar instalada e rodando no mesmo ambiente (localhost) onde este sistema está sendo executado.

### Usando a Evolution API no Docker Desktop

Se você já tem a Evolution API rodando no Docker Desktop, você só precisa saber:

1. O nome do contêiner ou a porta mapeada
2. Chave de API configurada (se houver)

Para verificar, execute:
```bash
docker ps | grep evolution
```

A URL para colocar no `.env` ou no `docker-compose.yml` será:
- Se estiver rodando em `localhost:8080`: use `http://host.docker.internal:8080` (para Docker) ou `http://localhost:8080` (para instalação Python)
- Se estiver em um contêiner chamado "evolution-api": use `http://evolution-api:8080` (se ambos os contêineres estiverem na mesma rede Docker)

## Observações Importantes

**Conexão com a Evolution API:**
- A Evolution API precisa estar rodando no mesmo ambiente (rede local) onde este sistema está sendo executado
- Não é possível conectar diretamente a uma Evolution API local a partir de um sistema hospedado em nuvem
- Para desenvolvimento e testes, recomendamos executar ambos os sistemas localmente
- Em ambientes Docker, use a rede do Docker ou `host.docker.internal` para a comunicação

## Solução de Problemas

### Erro de conexão com a Evolution API no Docker
Se você encontrar erros de conexão ao usar Docker, verifique:

1. A Evolution API está rodando? Verifique com `docker ps`
2. Rede do Docker está configurada corretamente
3. Tente usar o IP da sua máquina ao invés de `host.docker.internal`
4. Adicione ambos os contêineres à mesma rede Docker:
```bash
docker network create whatsapp-net
docker network connect whatsapp-net evolution-api
docker network connect whatsapp-net whatsapp_crm
```

Para informações mais detalhadas, consulte as páginas `/static/docs/local_setup.html` e `/static/docs/troubleshooting.html` após iniciar o sistema.

## Licença
Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para mais detalhes.