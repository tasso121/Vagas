EVALUATE_JOB_PROMPT = """Você é um avaliador especializado em vagas de tecnologia.

CURRÍCULO DO CANDIDATO:
{cv_content}

DESCRIÇÃO DA VAGA:
{job_description}

Analise o fit entre o candidato e a vaga. Retorne APENAS um JSON válido no formato:
{{
  "score": <número de 0.0 a 5.0>,
  "grade": "<A|B+|B|C|D|F>",
  "strengths": ["<ponto forte>", "<ponto forte>"],
  "gaps": ["<gap>", "<gap>"],
  "recommend": <true|false>,
  "summary": "<resumo em 2-3 frases>"
}}

Critérios:
- A (4.5-5.0): match excelente
- B+ (4.0-4.4): bom match, vale candidatura
- B (3.5-3.9): match razoável
- C (3.0-3.4): gaps significativos
- D/F (<3.0): não recomendado

Responda SOMENTE com o JSON, sem markdown."""

ADAPT_CV_PROMPT = """Você é um especialista em reescrita de currículos para ATS.

CURRÍCULO BASE:
{cv_content}

DESCRIÇÃO DA VAGA:
{job_description}

Reescreva o currículo em Markdown para maximizar o match com esta vaga:
1. Injete palavras-chave da vaga de forma natural
2. Reordene experiências para destacar as mais relevantes
3. Adapte bullet points para espelhar a linguagem da JD
4. Mantenha tudo verdadeiro — não invente nada

Retorne APENAS o currículo em Markdown, sem explicações."""

GENERATE_COVER_LETTER_PROMPT = """Você é um especialista em cartas de apresentação.

CURRÍCULO:
{cv_content}

VAGA:
{job_description}
EMPRESA: {company}

Escreva uma carta de apresentação concisa (3-4 parágrafos) em português que:
1. Abre com entusiasmo genuíno pela empresa/papel
2. Conecta experiência do currículo com necessidades da vaga
3. Fecha com chamada para ação

Retorne APENAS o texto da carta, sem cabeçalho, sem markdown."""
