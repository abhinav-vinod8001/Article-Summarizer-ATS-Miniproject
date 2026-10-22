#!/usr/bin/env python3
"""
AI-Powered Article Summarizer using Groq API
============================================
A command-line tool to summarize articles from direct input or files
using Groq's high-speed Large Language Model inference.
"""

import os
import sys
import argparse
import getpass
from pathlib import Path
from typing import Optional, Tuple

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Groq client import
try:
    from groq import Groq, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError
except ImportError:
    print("\n[ERROR] The 'groq' Python package is not installed.")
    print("Please install it with: pip install groq python-dotenv\n")
    sys.exit(1)


# Terminal color formatting (ANSI)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


DEFAULT_MODEL = "llama-3.3-70b-versatile"
BACKUP_MODEL = "llama-3.1-8b-instant"

SUMMARY_STYLES = {
    "concise": "A concise, coherent 2-3 paragraph summary capturing the core ideas without unnecessary fluff.",
    "bullet-points": "A structured summary with a brief 1-sentence intro followed by key takeaways as formatted bullet points.",
    "detailed": "A thorough, section-by-section breakdown highlighting main arguments, supporting evidence, and conclusions.",
    "executive": "An executive briefing format: 'TL;DR' (1-2 sentences), 'Core Findings' (bullet points), and 'Actionable Insights/Implications'."
}


def print_banner():
    """Prints the application header banner."""
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║            AI-POWERED ARTICLE SUMMARIZER                  ║")
    print("║             Powered by Groq Cloud & LLMs                  ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")


def get_api_key(cli_key: Optional[str] = None, interactive: bool = True) -> str:
    """
    Retrieves the Groq API key securely.
    Order of precedence:
      1. Explicit command-line argument (--api-key)
      2. Environment variable GROQ_API_KEY (or loaded from .env)
      3. Interactive prompt (masked password input)
    """
    if cli_key and cli_key.strip():
        return cli_key.strip()

    env_key = os.environ.get("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key

    if not interactive:
        print(f"{Colors.RED}[Error]{Colors.RESET} GROQ_API_KEY environment variable is not set.", file=sys.stderr)
        print("Set it using: export GROQ_API_KEY='your_key_here'", file=sys.stderr)
        print("Or pass it via the --api-key argument.", file=sys.stderr)
        sys.exit(1)

    print(f"{Colors.YELLOW}[Notice]{Colors.RESET} No Groq API key detected in environment or .env file.")
    print("Get your free key from: https://console.groq.com/keys\n")

    try:
        key = getpass.getpass("Enter your Groq API Key (input hidden for security): ").strip()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Colors.RED}Operation cancelled.{Colors.RESET}")
        sys.exit(1)

    if not key:
        print(f"{Colors.RED}[Error]{Colors.RESET} API key cannot be empty.")
        sys.exit(1)

    # Offer to persist into .env for convenience
    env_file = Path(".env")
    if not env_file.exists():
        try:
            save_pref = input("Would you like to save this key to a local .env file? (y/N): ").strip().lower()
            if save_pref in ('y', 'yes'):
                with open(env_file, "w", encoding="utf-8") as f:
                    f.write(f"GROQ_API_KEY={key}\n")
                print(f"{Colors.GREEN}[Success]{Colors.RESET} Key saved to .env (Make sure .env is in .gitignore!)")
        except Exception as e:
            print(f"{Colors.DIM}Could not save .env: {e}{Colors.RESET}")

    # Set in current runtime environment
    os.environ["GROQ_API_KEY"] = key
    return key


def read_article_from_file(file_path: str) -> str:
    """
    Reads and validates article text from a local file.
    Includes basic error handling for existence, permissions, and encoding.
    """
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: '{file_path}'")

    if not path.is_file():
        raise IsADirectoryError(f"Path is a directory, not a file: '{file_path}'")

    if path.stat().st_size == 0:
        raise ValueError(f"The file '{file_path}' is empty.")

    # Try utf-8 first, fallback to latin-1
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1") as f:
            content = f.read().strip()

    if not content:
        raise ValueError(f"No readable text found in '{file_path}'.")

    return content


def read_article_from_stdin() -> str:
    """
    Collects multi-line text input directly from the user in the terminal.
    Terminates when user presses Ctrl+D (Unix) / Ctrl+Z (Windows) or types 'EOF'.
    """
    print(f"\n{Colors.CYAN}{Colors.BOLD}--- Direct Text Input Mode ---{Colors.RESET}")
    print(f"{Colors.DIM}Paste your article text below. When finished:{Colors.RESET}")
    print(f"{Colors.DIM}  • Type 'EOF' on a new line and press Enter, OR{Colors.RESET}")
    print(f"{Colors.DIM}  • Press Ctrl+D (Mac/Linux) or Ctrl+Z (Windows){Colors.RESET}\n")

    lines = []
    try:
        while True:
            line = input()
            if line.strip() == "EOF":
                break
            lines.append(line)
    except (KeyboardInterrupt, EOFError):
        pass

    text = "\n".join(lines).strip()
    if not text:
        raise ValueError("No text was entered.")

    return text


def summarize_article(
    client: Groq,
    text: str,
    style: str = "bullet-points",
    model: str = DEFAULT_MODEL
) -> Tuple[str, dict]:
    """
    Sends the article to Groq LLM API and generates the summary.
    Returns the summary text and execution metadata (token counts, model used).
    """
    style_instruction = SUMMARY_STYLES.get(style, SUMMARY_STYLES["bullet-points"])

    system_prompt = (
        "You are an expert article analyst and summarizer. "
        "Your task is to extract the most important information, core arguments, "
        "and key findings accurately from the provided article without hallucination. "
        "Keep the tone objective, clear, and well-structured.\n\n"
        f"Format Requirement: {style_instruction}"
    )

    user_prompt = f"Please summarize the following article:\n\n{text}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=1500
        )
    except AuthenticationError:
        raise RuntimeError("Invalid Groq API Key. Please verify your key at https://console.groq.com/keys")
    except RateLimitError:
        raise RuntimeError("Groq API rate limit reached. Please wait a moment before trying again.")
    except APIConnectionError:
        raise RuntimeError("Network connection failed. Please check your internet connection.")
    except APIStatusError as e:
        raise RuntimeError(f"Groq API error (HTTP {e.status_code}): {e.message}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while communicating with Groq: {str(e)}")

    summary = response.choices[0].message.content
    metadata = {
        "model": model,
        "style": style,
        "input_words": len(text.split()),
        "summary_words": len(summary.split()),
        "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
        "completion_tokens": getattr(response.usage, "completion_tokens", None),
    }

    return summary, metadata


def display_summary(summary: str, metadata: dict):
    """Prints the formatted summary and metadata to stdout."""
    print(f"\n{Colors.GREEN}{Colors.BOLD}╔═══════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}║                     ARTICLE SUMMARY                       ║{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}╚═══════════════════════════════════════════════════════════╝{Colors.RESET}\n")

    print(summary)
    print("\n" + "─" * 60)

    in_words = metadata.get("input_words", 0)
    out_words = metadata.get("summary_words", 0)
    compression = round((1 - (out_words / max(in_words, 1))) * 100, 1) if in_words else 0

    print(f"{Colors.DIM}Model: {metadata.get('model')} | Style: {metadata.get('style')}")
    print(f"Original: ~{in_words} words | Summary: ~{out_words} words | Reduction: ~{compression}%{Colors.RESET}")
    print("─" * 60 + "\n")


def save_summary(summary: str, output_path: str):
    """Saves the generated summary to a specified file."""
    try:
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(summary + "\n")
        print(f"{Colors.GREEN}[Saved]{Colors.RESET} Summary successfully saved to: {path}")
    except Exception as e:
        print(f"{Colors.RED}[Error]{Colors.RESET} Failed to save summary to file: {e}")


def interactive_menu(client: Groq, current_model: str, current_style: str):
    """Interactive CLI menu when the script is run without explicit file/text flags."""
    model = current_model
    style = current_style

    while True:
        print(f"\n{Colors.BOLD}Main Menu:{Colors.RESET}")
        print("  [1] Summarize text from a File")
        print("  [2] Summarize text via Direct Input (paste text)")
        print("  [3] Test with Sample Article (sample_article.txt)")
        print(f"  [4] Change Summary Style  {Colors.DIM}(Current: {style}){Colors.RESET}")
        print(f"  [5] Change LLM Model      {Colors.DIM}(Current: {model}){Colors.RESET}")
        print("  [6] Exit")

        try:
            choice = input(f"\n{Colors.CYAN}Select an option (1-6): {Colors.RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if choice == "1":
            file_path = input(f"Enter file path: ").strip()
            if not file_path:
                print(f"{Colors.YELLOW}No path entered.{Colors.RESET}")
                continue
            try:
                text = read_article_from_file(file_path)
                print(f"{Colors.BLUE}[Info]{Colors.RESET} Read {len(text.split())} words from '{file_path}'.")
                print(f"{Colors.YELLOW}Summarizing with Groq ({model})...{Colors.RESET}")
                summary, meta = summarize_article(client, text, style=style, model=model)
                display_summary(summary, meta)

                save_opt = input("Save summary to a text file? (y/N): ").strip().lower()
                if save_opt in ('y', 'yes'):
                    out_path = input("Enter output filename (default: summary.txt): ").strip() or "summary.txt"
                    save_summary(summary, out_path)
            except Exception as e:
                print(f"{Colors.RED}[Error]{Colors.RESET} {e}")

        elif choice == "2":
            try:
                text = read_article_from_stdin()
                print(f"\n{Colors.BLUE}[Info]{Colors.RESET} Received {len(text.split())} words.")
                print(f"{Colors.YELLOW}Summarizing with Groq ({model})...{Colors.RESET}")
                summary, meta = summarize_article(client, text, style=style, model=model)
                display_summary(summary, meta)

                save_opt = input("Save summary to a text file? (y/N): ").strip().lower()
                if save_opt in ('y', 'yes'):
                    out_path = input("Enter output filename (default: summary.txt): ").strip() or "summary.txt"
                    save_summary(summary, out_path)
            except Exception as e:
                print(f"{Colors.RED}[Error]{Colors.RESET} {e}")

        elif choice == "3":
            sample_path = Path("sample_article.txt")
            if not sample_path.exists():
                print(f"{Colors.RED}[Error]{Colors.RESET} sample_article.txt not found in current directory.")
                continue
            try:
                text = read_article_from_file(str(sample_path))
                print(f"{Colors.BLUE}[Info]{Colors.RESET} Loaded sample article ({len(text.split())} words).")
                print(f"{Colors.YELLOW}Summarizing with Groq ({model})...{Colors.RESET}")
                summary, meta = summarize_article(client, text, style=style, model=model)
                display_summary(summary, meta)
            except Exception as e:
                print(f"{Colors.RED}[Error]{Colors.RESET} {e}")

        elif choice == "4":
            print("\nAvailable Summary Styles:")
            styles = list(SUMMARY_STYLES.keys())
            for idx, s in enumerate(styles, start=1):
                print(f"  [{idx}] {s.capitalize()}: {SUMMARY_STYLES[s]}")
            style_choice = input(f"Select style (1-{len(styles)}): ").strip()
            try:
                idx = int(style_choice) - 1
                if 0 <= idx < len(styles):
                    style = styles[idx]
                    print(f"{Colors.GREEN}[Updated]{Colors.RESET} Summary style set to: {style}")
                else:
                    print(f"{Colors.RED}Invalid selection.{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")

        elif choice == "5":
            print("\nAvailable Groq Models:")
            models = [
                ("llama-3.3-70b-versatile", "Meta Llama 3.3 70B (High accuracy & reasoning, Recommended)"),
                ("llama-3.1-8b-instant", "Meta Llama 3.1 8B (Ultra fast, lightweight)"),
                ("mixtral-8x7b-32768", "Mistral Mixtral 8x7B (Large context window)"),
                ("gemma2-9b-it", "Google Gemma 2 9B (Efficient & balanced)")
            ]
            for idx, (m_id, desc) in enumerate(models, start=1):
                print(f"  [{idx}] {m_id} - {desc}")
            model_choice = input(f"Select model (1-{len(models)}): ").strip()
            try:
                idx = int(model_choice) - 1
                if 0 <= idx < len(models):
                    model = models[idx][0]
                    print(f"{Colors.GREEN}[Updated]{Colors.RESET} Model set to: {model}")
                else:
                    print(f"{Colors.RED}Invalid selection.{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")

        elif choice == "6":
            print("\nExiting. Thank you for using Article Summarizer!\n")
            break

        else:
            print(f"{Colors.RED}Invalid option. Please choose between 1 and 6.{Colors.RESET}")


def parse_arguments():
    """Configures command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Article Summarizer using Groq API",
        epilog="Examples:\n"
               "  python summarizer.py                              # Interactive mode\n"
               "  python summarizer.py --file article.txt          # Summarize from file\n"
               "  python summarizer.py --text 'Long article...'     # Summarize direct text\n"
               "  python summarizer.py --file article.txt --style detailed --output summary.txt\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "-f", "--file",
        help="Path to the article text file"
    )
    input_group.add_argument(
        "-t", "--text",
        help="Direct article text string to summarize"
    )

    parser.add_argument(
        "-s", "--style",
        choices=list(SUMMARY_STYLES.keys()),
        default="bullet-points",
        help="Summary format style (default: bullet-points)"
    )

    parser.add_argument(
        "-m", "--model",
        default=DEFAULT_MODEL,
        help=f"Groq LLM model to use (default: {DEFAULT_MODEL})"
    )

    parser.add_argument(
        "-o", "--output",
        help="File path to save the generated summary"
    )

    parser.add_argument(
        "-k", "--api-key",
        help="Groq API key (optional, can also be set via GROQ_API_KEY environment variable or .env)"
    )

    return parser.parse_args()


def main():
    args = parse_arguments()
    is_non_interactive = bool(args.file or args.text)

    # In interactive mode, print the header
    if not is_non_interactive:
        print_banner()

    # Retrieve API key
    api_key = get_api_key(cli_key=args.api_key, interactive=not is_non_interactive)

    # Initialize Groq client
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        print(f"{Colors.RED}[Initialization Error]{Colors.RESET} Could not initialize Groq client: {e}")
        sys.exit(1)

    # CLI Direct Execution Mode
    if args.file:
        try:
            text = read_article_from_file(args.file)
            print(f"{Colors.BLUE}[Info]{Colors.RESET} Reading '{args.file}' ({len(text.split())} words)...")
            print(f"{Colors.YELLOW}Generating summary with Groq ({args.model})...{Colors.RESET}")
            summary, meta = summarize_article(client, text, style=args.style, model=args.model)
            display_summary(summary, meta)

            if args.output:
                save_summary(summary, args.output)
        except Exception as e:
            print(f"{Colors.RED}[Error]{Colors.RESET} {e}", file=sys.stderr)
            sys.exit(1)

    elif args.text:
        try:
            text = args.text.strip()
            if not text:
                raise ValueError("Provided --text string is empty.")
            print(f"{Colors.BLUE}[Info]{Colors.RESET} Processing input text ({len(text.split())} words)...")
            print(f"{Colors.YELLOW}Generating summary with Groq ({args.model})...{Colors.RESET}")
            summary, meta = summarize_article(client, text, style=args.style, model=args.model)
            display_summary(summary, meta)

            if args.output:
                save_summary(summary, args.output)
        except Exception as e:
            print(f"{Colors.RED}[Error]{Colors.RESET} {e}", file=sys.stderr)
            sys.exit(1)

    else:
        # Launch interactive menu
        interactive_menu(client, current_model=args.model, current_style=args.style)


if __name__ == "__main__":
    main()
