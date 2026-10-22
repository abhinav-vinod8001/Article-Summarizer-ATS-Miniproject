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
   git clone https://github.com/abhinav-vinod8001/ai-article-summarizer.git
   cd ai-article-summarizer
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

## File Structure

```text
├── summarizer.py       # Main CLI application
├── requirements.txt    # Dependencies (groq, python-dotenv)
├── sample_article.txt  # Sample article for testing
├── .env.example        # Environment variable template
├── .gitignore          # Excludes .env, cache, and summary outputs
├── LICENSE             # MIT License
└── README.md           # Documentation
```

---

## License
MIT License
