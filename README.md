# 🧠 Pocket AI Agent — Phase 1

> Share any link on Telegram → Get instant AI-powered insights, auto-categorized and saved forever.

---

## What This Does

Send any URL to your Telegram bot and get back:

```
✅ Saved to your Pocket!

▶️ How I Built a Production RAG System

🎬 Video Tutorial  |  ⏱ 45 minutes  |  🟠 Advanced

💡 Summary:
A deep-dive into building retrieval-augmented generation systems 
for production. Covers chunking strategies, embedding models, 
reranking, and evaluation.

🎯 Why save this:
Shows real production pitfalls that tutorials skip over.

📚 Learn first:
  • Python async programming
  • Basic LLM API usage
  • Vector database concepts

🏷 Tags: #rag #llm #production #python #embeddings
```

---

## Setup (30 minutes)

### Step 1: Get your API keys

**Telegram Bot Token:**
1. Open Telegram → search `@BotFather`
2. Send `/newbot`
3. Follow instructions → copy the token

**Gemini API Key (FREE):**
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy it (free tier = 1 million tokens/day)

### Step 2: Install Python dependencies

```bash
# Make sure Python 3.10+ is installed
python --version

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure your secrets

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your tokens
nano .env   # or use any text editor
```

### Step 4: Run the bot

```bash
python bot.py
```

You should see:
```
2024-01-01 | INFO | root | ✅ Database initialized
2024-01-01 | INFO | root | 🤖 Pocket Agent is running...
```

Now open your Telegram bot and send any URL!

---

## Project Structure

```
pocket-agent/
├── bot.py                    ← Entry point, registers all handlers
├── requirements.txt          ← Python dependencies
├── .env.example              ← Copy to .env and fill secrets
│
├── config/
│   └── settings.py           ← All config loaded from .env
│
├── handlers/
│   ├── link_handler.py       ← Main pipeline: detect→fetch→analyze→save→reply
│   └── command_handler.py    ← /start /help /search /recent /stats
│
├── tools/
│   ├── link_detector.py      ← Figures out link type (YouTube/GitHub/article)
│   ├── fetcher.py            ← Fetches content from URLs
│   └── analyzer.py           ← Gemini AI analysis → structured output
│
└── db/
    └── database.py           ← SQLite storage layer
```

---

## Commands

| Command | What it does |
|---|---|
| `/start` | Introduction and help |
| `/search python` | Search your saved links |
| `/recent` | Show last 10 saved items |
| `/stats` | Your library breakdown |

---

## What You're Learning (Concepts by File)

| File | Concepts |
|---|---|
| `bot.py` | Application entry point, handler registration, polling |
| `link_detector.py` | Regex, URL parsing, enums, dataclasses, routing logic |
| `fetcher.py` | yt-dlp, requests, BeautifulSoup, web scraping, error handling |
| `analyzer.py` | Prompt engineering, structured LLM output, JSON parsing, Gemini API |
| `database.py` | SQLite, SQL basics, JSON in DB, context managers |
| `link_handler.py` | async/await, Telegram API, pipeline pattern |
| `command_handler.py` | Command parsing, formatted messages |

---

## Troubleshooting

**Bot doesn't respond?**
- Make sure `bot.py` is running (check terminal)
- Verify your `TELEGRAM_BOT_TOKEN` in `.env`

**"Could not fetch" for YouTube?**
- Try: `pip install yt-dlp --upgrade`
- YouTube changes their API frequently, yt-dlp updates to match

**Gemini API errors?**
- Check your API key at https://aistudio.google.com
- Free tier has rate limits — wait a minute and retry

**Scraping fails for articles?**
- Many sites block scrapers — the AI will still analyze based on URL/title
- This is normal — Phase 2 adds better content extraction

---

## Roadmap

- **Phase 1** (now) ✅ — Telegram bot + AI analysis + SQLite storage
- **Phase 2** — ChromaDB vector search ("show me ML videos under 30 mins")
- **Phase 3** — LangChain tools + true agent reasoning
- **Phase 4** — Run locally on Raspberry Pi with Ollama (zero API cost)
