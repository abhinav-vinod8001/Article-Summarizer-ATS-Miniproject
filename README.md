# AI-Powered Article Summarizer (Groq API)

A clean, minimalist command-line Python application that summarizes articles using the Groq API (`openai/gpt-oss-120b`).

---

## Requirements & Features

- Summarize article text from a local file or direct terminal input.
- Clear, well-structured summaries printed to the command line.
- Basic error handling for file reading, empty inputs, network errors, and API key authentication.
- Zero hardcoded API keys: supports `.env` and environment variables.

---

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/abhinav-vinod8001/Article-Summarizer-ATS-Miniproject.git
   cd Article-Summarizer-ATS-Miniproject
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key:**
   Get a free API key from [Groq Console](https://console.groq.com/keys) and set it in a `.env` file:
   ```bash
   cp .env.example .env
   # Add your key to .env: GROQ_API_KEY=your_key_here
   ```
   *(Or just run the script; it will prompt you if no key is found).*

---

## Usage

### Interactive Mode
Run the script without arguments:
```bash
python3 summarizer.py
```

Output:
```text
Article Summarizer
------------------
1. Summarize text from file
2. Enter text directly
3. Exit

Select an option (1-3):
```

### Command-Line Arguments
```bash
# Summarize from file
python3 summarizer.py -f sample_article.txt

# Summarize and save output to a file
python3 summarizer.py -f sample_article.txt -o summary.txt

# Summarize directly from a text string
python3 summarizer.py -t "Your article text goes here..."
```

---

## Web Frontend & Vercel Hosting

The project includes a lightweight static frontend (`public/`) paired with a Vercel Python Serverless Function (`api/summarize.py`) that reuses the core summarization logic in `summarizer.py` while keeping `GROQ_API_KEY` safely on the server.

### Run the Web UI Locally
```bash
python3 dev_server.py
```
Then open `http://127.0.0.1:3000` in your browser.

### Deploy to Vercel
1. Push this repository to GitHub (or install Vercel CLI with `npm i -g vercel`).
2. Import the project in [Vercel](https://vercel.com/new) (Framework Preset: **Other**) or run `vercel` in the project root.
3. In Vercel **Project Settings → Environment Variables**, add:
   - `GROQ_API_KEY` = your Groq API key
4. Deploy. Vercel serves `public/index.html` at `/` and runs `api/summarize.py` at `/api/summarize`.

---

## File Structure

```text
├── api/
│   └── summarize.py    # Vercel Python serverless endpoint (POST /api/summarize)
├── public/
│   ├── index.html      # Web frontend
│   ├── styles.css      # Responsive light-themed styling
│   └── app.js          # Client logic (upload, validation, copy/download)
├── dev_server.py       # Local dev server for previewing the web UI
├── summarizer.py       # Core summarization logic + CLI application
├── requirements.txt    # Dependencies (groq, python-dotenv)
├── sample_article.txt  # Sample article for testing
├── .env.example        # Environment variable template
├── .gitignore          # Excludes .env, cache, and summary outputs
├── .vercelignore       # Excludes local-only files from Vercel deployments
├── LICENSE             # MIT License
└── README.md           # Documentation
```

---

## License
MIT License
