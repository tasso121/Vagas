# Job Automation System — Design Doc
**Data:** 2026-05-07  
**Autor:** Tasso Marcel  
**Status:** Aprovado

---

## Visão Geral

Sistema local de automação de busca e candidatura a vagas de emprego remotas na área de tecnologia. Combina scraping automático de múltiplas plataformas com avaliação por IA (Claude Code) e candidatura semi-automática via Playwright, com confirmação pelo Telegram antes de cada envio.

**Princípio central:** a IA avalia e preenche, o usuário sempre confirma antes de submeter.

---

## Arquitetura

```
[Scheduler Python] a cada 30min
        ↓
[Scrapers] Gupy API + Indeed MCP + LinkedIn Playwright
        ↓
[SQLite] dedup por platform+job_id
        ↓
[Telegram Bot] notifica nova vaga com botões inline
        ↓
  Usuário clica "Avaliar"
        ↓
[claude -p subprocess] skill /avaliar-vaga → nota A-F + análise
        ↓
[Telegram] mostra nota + análise → "Candidatar?"
        ↓
  Usuário clica "Sim"
        ↓
[claude -p subprocess] skill /adaptar-cv + /gerar-pdf
        ↓
[Playwright] preenche formulário, pausa antes de submeter
        ↓
[Telegram] "Formulário preenchido. Confirmar envio?"
        ↓
  Usuário clica "Confirmar"
        ↓
[Playwright] submit → [SQLite] status = applied
```

---

## Componentes

| Componente | Tecnologia | Responsabilidade |
|---|---|---|
| Scraper | Python (requests + Playwright) | Buscar vagas novas nas plataformas |
| Dedup | SQLite (embutido) | Garantir que cada vaga é processada uma vez |
| Notificações | python-telegram-bot (async) | Comunicação com o usuário |
| IA | `claude -p` (Claude Code CLI) | Avaliação, adaptação de CV, geração de PDF |
| Forms | Playwright | Preenchimento automático de candidaturas |
| Agendamento | `schedule` lib Python | Loop de 30 em 30 minutos |

---

## Scrapers

### Gupy (API interna)
- Endpoint JSON direto, sem navegador, baseado no projeto do Lucas Nunes
- Filtro: `workplaceTypes=remote`
- Mais estável das três plataformas

### Indeed (Playwright headless)
- Busca via Playwright na página de resultados do Indeed com filtro `remotejobs=1`
- Extrai título, empresa, descrição e URL de cada resultado
- Fallback: se a vaga redirecionar para ATS externo (Gupy, Greenhouse), usa o apply daquela plataforma

### LinkedIn Easy Apply (Playwright headless)
- Filtros: `f_WT=2` (remote) + `f_LF=f_AL` (Easy Apply only)
- Só coleta vagas com candidatura simplificada
- Sessão salva em cookies para evitar login repetido
- Mais frágil — LinkedIn muda layout com frequência

### Schema de vaga (comum a todos os scrapers)
```python
{
  "platform": "gupy",        # gupy | indeed | linkedin
  "job_id": "abc123",        # ID único na plataforma
  "title": "Desenvolvedor Backend",
  "company": "Empresa X",
  "url": "https://...",
  "description": "...",      # texto completo da vaga
  "scraped_at": "2026-05-07T15:30:00"
}
```

---

## Telegram Bot — Fluxo de Mensagens

### 1. Nova vaga detectada
```
🆕 Nova vaga remota

💼 Desenvolvedor Backend Laravel
🏢 Empresa X
📍 100% Remoto
🔗 [Ver vaga completa]

[✅ Avaliar com IA]  [❌ Ignorar]
```

### 2. Após avaliação do Claude
```
📊 Avaliação: B+ (4.2/5)

✅ Pontos fortes:
• Laravel + Vue.js — match perfeito
• Experiência com SaaS próprio

⚠️ Gaps:
• Pedem AWS (experiência parcial)

[🚀 Candidatar]  [❌ Descartar]
```

### 3. Antes de submeter
```
📝 Formulário preenchido!

• Currículo adaptado: ✅
• Carta de apresentação: ✅
• Campos do form: ✅

[✅ Confirmar envio]  [✏️ Revisar primeiro]  [❌ Cancelar]
```
"Revisar primeiro" envia a URL da vaga como mensagem separada no Telegram para você abrir manualmente, e aguarda `/confirmar` ou `/cancelar` como resposta.

### 4. Após envio
```
✅ Candidatura enviada!
💼 Desenvolvedor Backend Laravel @ Empresa X
📅 07/05/2026 às 15:32
```

---

## Claude Code Skills

Localizadas em `.claude/skills/`:

### `/avaliar-vaga`
- **Input:** descrição da vaga + `cv.md`
- **Output JSON:** `{ "score": 4.2, "grade": "B+", "strengths": [...], "gaps": [...], "recommend": true }`

### `/adaptar-cv`
- **Input:** descrição da vaga + `cv.md`
- **Output:** CV em Markdown reescrito para a vaga, com palavras-chave da JD injetadas naturalmente

### `/gerar-pdf`
- **Input:** CV adaptado em Markdown
- **Output:** PDF salvo em `output/cv-{empresa}-{data}.pdf` usando Playwright + template HTML

O bot Python invoca cada skill via:
```python
result = subprocess.run(
    ["claude", "-p", prompt, "--output-format", "json"],
    capture_output=True, text=True
)
```

---

## Preenchimento de Formulários (Playwright)

### Gupy
- Login com credenciais do `.env`
- Upload do PDF do currículo adaptado
- Preenchimento de campos padrão (nome, email, telefone, LinkedIn)
- Respostas de perguntas customizadas geradas pelo Claude
- Para antes de submeter — aguarda confirmação Telegram

### LinkedIn Easy Apply
- Sessão mantida via cookies salvos no primeiro setup
- Preenche etapas do wizard
- Anexa currículo adaptado se campo disponível
- Para antes de submeter — aguarda confirmação Telegram

### Indeed
- Detecta plataforma de destino (geralmente Gupy ou Greenhouse)
- Aplica lógica da plataforma de destino
- Fallback: envia link + PDF no Telegram para candidatura manual

---

## Estrutura de Pastas

```
vagas/
├── main.py                    # ponto de entrada, loop principal
├── scrapers/
│   ├── gupy.py
│   ├── indeed.py
│   └── linkedin.py
├── bot/
│   └── telegram_bot.py        # handlers, botões inline, estado em memória (dict job_id → estado)
├── apply/
│   ├── gupy_apply.py
│   ├── linkedin_apply.py
│   └── indeed_apply.py          # detecta ATS destino e delega
├── .claude/
│   └── skills/
│       ├── avaliar-vaga.md
│       ├── adaptar-cv.md
│       └── gerar-pdf.md
├── cv.md                      # CV base do Tasso em Markdown
├── output/                    # PDFs gerados (gitignored)
├── data/
│   └── jobs.db                # SQLite (gitignored)
├── .env                       # credenciais (gitignored)
├── .env.example
└── requirements.txt
```

---

## Variáveis de Ambiente (.env)

```
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
GUPY_EMAIL=
GUPY_PASSWORD=
LINKEDIN_SESSION_COOKIES=    # gerado automaticamente no setup
```

---

## SQLite Schema

```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    job_id TEXT NOT NULL,
    title TEXT,
    company TEXT,
    url TEXT,
    description TEXT,
    status TEXT DEFAULT 'pending',  -- pending | notified | evaluated | applied | rejected | ignored
    score REAL,
    grade TEXT,
    scraped_at TEXT,
    applied_at TEXT,
    UNIQUE(platform, job_id)
);
```

---

## Fora do Escopo (v1)

- Glassdoor, Vagas.com, Infojobs — bloqueiam bots ativamente
- Dashboard web ou TUI
- Rastreamento de respostas/follow-up
- Múltiplos perfis de usuário
