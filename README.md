# Vagas Bot

Sistema local de automação de busca e candidatura a vagas remotas de tecnologia.
Busca vagas no Gupy, Indeed e LinkedIn — avalia fit com Claude AI — e preenche formulários via Playwright. Tudo controlado pelo Telegram.

## Pré-requisitos

- Python 3.11+
- Claude Code CLI instalado e configurado
- Conta no Telegram

## Setup

**1. Instale dependências:**
```bash
pip install -r requirements.txt
playwright install chromium
```

**2. Configure variáveis de ambiente:**
```bash
cp .env.example .env
# edite .env com seu token do Telegram, chat_id, email/senha do Gupy
```

Para obter o `TELEGRAM_TOKEN`: crie um bot em @BotFather no Telegram.  
Para obter o `TELEGRAM_CHAT_ID`: envie uma mensagem para @userinfobot.

**3. Salve a sessão do LinkedIn (necessário uma vez):**
```bash
python setup_linkedin.py
```
Um navegador vai abrir — faça login manualmente e pressione ENTER no terminal.

**4. Adicione seu currículo:**

Edite `cv.md` com seu currículo em Markdown. Este arquivo é a base para todas as adaptações.

**5. Execute:**
```bash
python main.py
```

## Fluxo de uso

1. A cada 30 minutos, vagas remotas novas aparecem no seu Telegram
2. Clique **Avaliar com IA** → Claude analisa o fit com seu CV e dá nota A-F
3. Clique **Candidatar** → CV adaptado gerado, formulário preenchido pelo Playwright
4. Clique **Confirmar envio** → candidatura enviada
5. Ou **Revisar primeiro** → recebe o link para conferir antes de confirmar
