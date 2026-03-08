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
- **AI analysis** — summary, difficulty, time estimate, prerequisites (Groq / Llama 3)
- **Security scoring** — every URL scored 1–5; description links checked too
- **Persistent library** — PostgreSQL on Neon (cloud), browse and search anytime
- **Always-on** — runs as a systemd service, auto-restarts on crash

---

## Architecture

```
Telegram ──► Bot (laptop / Raspberry Pi) ──► Groq AI
                        │
                        ▼
                  Neon PostgreSQL (cloud)
```

Your **bot** runs locally (laptop or Pi). Your **data** lives in Neon (cloud) — safe even if the device restarts.

---

## Local Setup

### Step 1: Get API keys

**Telegram Bot Token** — message `@BotFather` on Telegram → `/newbot`

**Groq API Key** — [console.groq.com](https://console.groq.com) → API Keys → Create (free)

**Neon Database** — [neon.tech](https://neon.tech) → Create Project → copy Connection String (free, no card)

### Step 2: Clone and install

```bash
git clone https://github.com/devsamaAI/Knowagent.git
cd Knowagent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure

```bash
cp .env.example .env
nano .env   # fill in TELEGRAM_BOT_TOKEN, GROQ_API_KEY, DATABASE_URL
```

### Step 4: Run

```bash
python bot.py
```

### Step 5: Run as background service (stays alive after terminal close)

```bash
mkdir -p ~/.config/systemd/user
# Copy the service file from deploy.sh (or run deploy.sh directly)
systemctl --user enable pocket-agent
systemctl --user start pocket-agent
```

---

## Deploy on Raspberry Pi (Recommended for 24/7)

**Recommended hardware:** Raspberry Pi Zero 2 W (`SC0510`) — ~₹1,300
Runs 24/7 at home on WiFi, costs ~₹15/month in electricity.

### Setup (one command after Pi is running):

```bash
# SSH into your Pi
ssh pi@raspberrypi.local

# Run the deploy script
curl -sO https://raw.githubusercontent.com/devsamaAI/Knowagent/main/deploy.sh
chmod +x deploy.sh && ./deploy.sh
```

The script will:
1. Install all system dependencies (including PostgreSQL client libs for ARM)
2. Clone the repo
3. Set up Python virtualenv
4. Prompt you to fill in `.env`
5. Create and start the systemd service
6. Enable lingering (stays alive after SSH disconnect)

### Update after code changes:

```bash
ssh pi@raspberrypi.local
git -C ~/pocket-agent pull && systemctl --user restart pocket-agent
```

---

## Project Structure

```
Knowagent/
├── bot.py                    ← Entry point, registers all handlers
├── requirements.txt          ← Python dependencies
├── .env.example              ← Copy to .env and fill secrets
├── deploy.sh                 ← One-command Pi/Linux setup script
├── Dockerfile                ← Docker support (for cloud deployment)
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
│   ├── fetcher.py            ← Fetches content per platform
│   ├── analyzer.py           ← Groq/Llama AI analysis → structured JSON output
│   └── security_checker.py   ← URL security scoring (1–5) + description link extraction
│
└── db/
    └── database.py           ← PostgreSQL (production) + SQLite (local fallback)
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
| `database.py` | PostgreSQL + SQLite, SQL basics, JSON in DB, context managers |
| `link_handler.py` | async/await, Telegram API, pipeline pattern |
| `command_handler.py` | Command parsing, formatted Telegram messages |

---

## Troubleshooting

**Bot doesn't respond?**
```bash
systemctl --user status pocket-agent
journalctl --user -u pocket-agent -f
```

**"Could not fetch" for YouTube?**
```bash
pip install yt-dlp --upgrade
systemctl --user restart pocket-agent
```

**Groq API errors?**
- Check key at [console.groq.com](https://console.groq.com)
- Free tier has rate limits — wait and retry

**Instagram not working?**
- Instagram blocks scrapers for private/login-required content
- Public posts work; private accounts always fail

**Database errors on Pi?**
```bash
# Make sure libpq-dev is installed (deploy.sh does this automatically)
sudo apt-get install -y libpq-dev
pip install psycopg2-binary --force-reinstall
```

---

## Roadmap

- **Phase 1** (now) ✅ — Telegram bot + Groq AI + security checks + Neon PostgreSQL
- **Phase 2** — ChromaDB vector search ("show me ML videos under 30 mins")
- **Phase 3** — LangChain tools + true agent reasoning
- **Phase 4** — Run models locally on Pi with Ollama (zero API cost)
