# 🧠 KnowAgent — Phase 1

> Share any link on Telegram → Get instant AI-powered insights, security check, auto-categorized and saved forever.

---

## What This Does

Send any URL to your Telegram bot and get back:

```
✅ Saved to your Pocket!

▶️ Vector Databases simply explained! (Embeddings & Indexes)

🎬 Video Tutorial  |  ⏱ 4 minutes 23 seconds  |  🟡 Intermediate
🔒 Security: 🟢 Safe (5/5) — Trusted platform

💡 Summary:
Explains vector databases, embeddings and indexes, covering use cases
and different options available. Great concise intro to the topic.

🎯 Why save this:
Concise introduction to vector databases and their role in modern AI.

📚 Learn first:
  • Basic machine learning concepts
  • Familiarity with databases

🔗 Links in description:
  🔵 https://pinecone.io/learn/vector-database — Likely Safe
  🔵 https://frankzliu.com/blog/... — Likely Safe

🏷 Tags: #machine_learning #vector_databases #embeddings #ai
```

---

## Features

- **Multi-platform** — YouTube, GitHub, Instagram, articles, any URL
- **AI analysis** — summary, difficulty, time estimate, prerequisites (powered by Groq / Llama 3)
- **Security scoring** — every URL scored 1–5 for safety; description links checked too
- **Persistent library** — SQLite database, search and browse anytime
- **Always-on** — runs as a systemd service, auto-restarts on crash

---

## Setup (Local)

### Step 1: Get your API keys

**Telegram Bot Token:**
1. Open Telegram → search `@BotFather`
2. Send `/newbot` → follow prompts → copy the token

**Groq API Key (FREE):**
1. Go to https://console.groq.com
2. Create an account → API Keys → Create
3. Copy the key (free tier is generous)

### Step 2: Clone and install

```bash
git clone https://github.com/devsamaAI/Knowagent.git
cd Knowagent

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure secrets

```bash
cp .env.example .env
nano .env   # fill in TELEGRAM_BOT_TOKEN and GROQ_API_KEY
```

### Step 4: Run the bot

```bash
python bot.py
```

You should see:
```
INFO | ✅ Database initialized
INFO | 🤖 Pocket Agent is running... Send a link to your bot!
```

### Step 5 (optional): Run as background service

```bash
mkdir -p ~/.config/systemd/user
# Create service file (see deploy.sh for the full template)
systemctl --user enable pocket-agent
systemctl --user start pocket-agent
```

---

## Deploy to Oracle Cloud (Free Server)

Oracle Cloud Free Tier gives you a permanent free ARM VM (4 CPU, 24GB RAM) — no credit card needed after signup.

```bash
# 1. SSH into your VM
ssh -i your-key.pem ubuntu@YOUR_VM_IP

# 2. Run the deploy script
curl -sO https://raw.githubusercontent.com/devsamaAI/Knowagent/main/deploy.sh
chmod +x deploy.sh && ./deploy.sh

# 3. Add your secrets
nano ~/pocket-agent/.env

# 4. Start the bot
systemctl --user start pocket-agent
```

**Update after code changes:**
```bash
git -C ~/pocket-agent pull && systemctl --user restart pocket-agent
```

---

## Project Structure

```
Knowagent/
├── bot.py                    ← Entry point, registers all handlers
├── requirements.txt          ← Python dependencies
├── .env.example              ← Copy to .env and fill secrets
├── deploy.sh                 ← One-command Oracle Cloud setup
│
├── config/
│   └── settings.py           ← All config loaded from .env
│
├── handlers/
│   ├── link_handler.py       ← Main pipeline: detect→fetch→analyze→security→save→reply
│   └── command_handler.py    ← /start /help /search /recent /stats /topics /list
│
├── tools/
│   ├── link_detector.py      ← Detects link type (YouTube/GitHub/Instagram/article)
│   ├── fetcher.py            ← Fetches content per platform (yt-dlp, GitHub API, scraping)
│   ├── analyzer.py           ← Groq/Llama AI analysis → structured JSON output
│   └── security_checker.py   ← URL security scoring (1–5) + description link extraction
│
└── db/
    └── database.py           ← SQLite storage layer
```

---

## Bot Commands

| Command | What it does |
|---|---|
| `/topics` | Browse your library by topic/category |
| `/list <topic>` | Show all items in a topic (e.g. `/list Tutorial`) |
| `/search <keyword>` | Keyword search across all saved items |
| `/recent` | Show last 10 saved items |
| `/stats` | Library breakdown by platform |
| `/help` | Show all commands |

---

## Security Scoring

Every URL (and links found in descriptions) is scored:

| Score | Label | Meaning |
|---|---|---|
| 🟢 5/5 | Safe | Trusted platform (YouTube, GitHub, etc.) |
| 🔵 4/5 | Likely Safe | HTTPS, no red flags |
| ⚪ 3/5 | Unknown | Can't verify, proceed with caution |
| 🟡 2/5 | Suspicious | Suspicious TLD, missing HTTPS, etc. |
| 🔴 1/5 | Dangerous | IP-based URL, phishing pattern detected |

---

## What You're Learning (Concepts by File)

| File | Concepts |
|---|---|
| `bot.py` | Application entry point, handler registration, polling |
| `link_detector.py` | Regex, URL parsing, enums, dataclasses, routing |
| `fetcher.py` | yt-dlp, requests, BeautifulSoup, platform-specific APIs |
| `analyzer.py` | Prompt engineering, structured LLM output, JSON parsing, Groq API |
| `security_checker.py` | Heuristic scoring, redirect following, URL pattern analysis |
| `database.py` | SQLite, SQL basics, JSON in DB, context managers |
| `link_handler.py` | async/await, Telegram API, pipeline pattern |
| `command_handler.py` | Command parsing, formatted Telegram messages |

---

## Troubleshooting

**Bot doesn't respond?**
- Check it's running: `systemctl --user status pocket-agent`
- View logs: `journalctl --user -u pocket-agent -f`
- Verify `TELEGRAM_BOT_TOKEN` in `.env`

**"Could not fetch" for YouTube?**
- Upgrade yt-dlp: `pip install yt-dlp --upgrade`
- Then restart: `systemctl --user restart pocket-agent`

**Groq API errors?**
- Check your key at https://console.groq.com
- Free tier has rate limits — wait a moment and retry

**Instagram not working?**
- Instagram blocks most scrapers for private/login-required content
- Public posts should work; private accounts will always fail

---

## Roadmap

- **Phase 1** (now) ✅ — Telegram bot + Groq AI + security checks + SQLite
- **Phase 2** — ChromaDB vector search ("show me ML videos under 30 mins")
- **Phase 3** — LangChain tools + true agent reasoning
- **Phase 4** — Run locally on Raspberry Pi with Ollama (zero API cost)
