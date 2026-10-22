# ⚡ AI-Powered Article Summarizer (Groq LLM)

An ultra-fast, command-line AI application that generates structured, high-quality summaries of long articles, essays, and text documents using the **Groq API** and state-of-the-art open-source LLMs (Meta Llama 3.3 70B & Llama 3.1 8B).

---

## 📌 Features

- **High-Speed Inference**: Powered by Groq's LPU™ (Language Processing Unit) architecture for near-instant responses.
- **Dual Input Modes**:
  - **File Mode**: Summarize `.txt`, `.md`, or raw article files directly from disk.
  - **Direct Input Mode**: Paste or type multi-line articles straight into the terminal.
- **Interactive CLI & Command-Line Arguments**:
  - Run interactively with a guided menu.
  - Or automate via CLI flags (`--file`, `--text`, `--style`, `--output`).
- **Customizable Summary Formats**:
  - `bullet-points` (default): Crisp, structured key takeaways.
  - `concise`: A coherent 2-3 paragraph synthesis.
  - `detailed`: Section-by-section analytical breakdown.
  - `executive`: TL;DR briefing with key findings and actionable insights.
- **Robust Error Handling**:
  - Handles missing/empty files, encoding quirks, invalid API keys, rate limits, and network errors gracefully.
- **Security & Best Practices**:
  - Zero hardcoded keys. Supports `.env`, environment variables, CLI parameters, and secure interactive masked prompts.
  - Automatic `.gitignore` prevents accidental secret leaks to GitHub.

---

## 🔐 API Key Handling: Best Practice

> **Why you should NOT hardcode API keys in source code:**
> 1. **Public Repository Exposure**: If your code is pushed to GitHub, automated bots scrape repositories for API keys within seconds, leading to key revocation, quota exhaustion, or unexpected billing.
> 2. **Security & Portability**: Hardcoding credentials ties the code to one person's account. Using environment variables lets anyone clone and use their own key safely.

### How this project handles API keys securely:
The application checks for credentials in the following order:
1. **Command-line flag**: `--api-key <YOUR_KEY>`
2. **Environment variable or `.env` file**: `GROQ_API_KEY`
3. **Interactive fallback**: Prompts you securely (with masked password input via `getpass`), and asks if you'd like to save it to your local `.env` (which is git-ignored).

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.8 or higher installed on your system.
- A free Groq API key: [Get one from Groq Console](https://console.groq.com/keys).

### 2. Installation

Clone this repository and navigate to the project directory:
```bash
git clone https://github.com/YOUR_USERNAME/ai-article-summarizer.git
cd ai-article-summarizer
```

Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure API Key (Optional but Recommended)
Copy the example `.env` file and insert your API key:
```bash
cp .env.example .env
```
Edit `.env` and set:
```ini
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
```

*(If you skip this step, the script will simply ask for your key when you first run it).*

---

## 💻 Usage

### Mode A: Interactive Menu (Recommended for Beginners)
Simply run the script with no arguments:
```bash
python summarizer.py
```

You will see an interactive menu:
```text
╔═══════════════════════════════════════════════════════════╗
║            AI-POWERED ARTICLE SUMMARIZER                  ║
║             Powered by Groq Cloud & LLMs                  ║
╚═══════════════════════════════════════════════════════════╝

Main Menu:
  [1] Summarize text from a File
  [2] Summarize text via Direct Input (paste text)
  [3] Test with Sample Article (sample_article.txt)
  [4] Change Summary Style  (Current: bullet-points)
  [5] Change LLM Model      (Current: llama-3.3-70b-versatile)
  [6] Exit
```

---

### Mode B: Direct Command-Line Arguments (Fast & Scriptable)

#### 1. Summarize a local file:
```bash
python summarizer.py --file sample_article.txt
```

#### 2. Summarize direct text:
```bash
python summarizer.py --text "Artificial intelligence inference has advanced rapidly..."
```

#### 3. Choose a summary style and save output:
```bash
python summarizer.py --file sample_article.txt --style executive --output my_summary.txt
```

#### 4. Specify a different model (e.g., ultra-fast 8B model):
```bash
python summarizer.py --file sample_article.txt --model llama-3.1-8b-instant
```

---

## 🛠️ CLI Options Reference

| Flag | Short | Description | Default |
|---|---|---|---|
| `--file` | `-f` | Path to text file to summarize | None |
| `--text` | `-t` | Direct text string to summarize | None |
| `--style` | `-s` | `bullet-points`, `concise`, `detailed`, `executive` | `bullet-points` |
| `--model` | `-m` | Groq model (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) | `llama-3.3-70b-versatile` |
| `--output` | `-o` | Output file path to save summary | Terminal only |
| `--api-key` | `-k` | Pass API key directly | Loads from `.env` / env var |

---

## 📂 Project Structure

```text
├── summarizer.py         # Main CLI application script
├── requirements.txt      # Python package dependencies (groq, python-dotenv)
├── sample_article.txt    # Ready-to-test sample article on AI & Inference
├── .env.example          # Environment variable template
├── .gitignore            # Ignores .env, virtual environments, and caches
└── README.md             # Project documentation and guide
```

---

## 📤 Sharing to GitHub

To push this project to your GitHub account:

1. **Initialize git repository (if not already done)**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: AI-Powered Article Summarizer using Groq"
   ```

2. **Create a new repository on GitHub**:
   - Go to [GitHub New Repository](https://github.com/new).
   - Name it `ai-article-summarizer` (or your preferred name).
   - Leave "Initialize with README" **unchecked**.

3. **Link and push**:
   ```bash
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/ai-article-summarizer.git
   git push -u origin main
   ```

4. Share your repository link!

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
