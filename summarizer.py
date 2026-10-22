#!/usr/bin/env python3
"""
Article Summarizer
==================
A clean, efficient command-line application to summarize articles from files
or user input using the Groq API with high compression efficiency.
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
    from groq import (
        Groq,
        AuthenticationError,
        RateLimitError,
        APIConnectionError,
        APIStatusError,
        NotFoundError
    )
except ImportError:
    print("Error: The 'groq' package is not installed.")
    print("Run: pip install groq python-dotenv")
    sys.exit(1)


MODEL_NAME = "openai/gpt-oss-120b"
FALLBACK_MODEL = "openai/gpt-oss-20b"


def save_key_to_env(key: str):
    """Saves or updates GROQ_API_KEY in the local .env file."""
    env_path = Path(".env")
    lines = []
    key_found = False

    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                if line.strip().startswith("GROQ_API_KEY="):
                    new_lines.append(f"GROQ_API_KEY={key}\n")
                    key_found = True
                else:
                    new_lines.append(line)
            if not key_found:
                new_lines.append(f"GROQ_API_KEY={key}\n")
            lines = new_lines
        except Exception:
            lines = [f"GROQ_API_KEY={key}\n"]
    else:
        lines = [f"GROQ_API_KEY={key}\n"]

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("API key successfully saved to .env")
    except Exception as e:
        print(f"Warning: Could not save key to .env: {e}")


def get_api_key(cli_key: Optional[str] = None, interactive: bool = True) -> str:
    """
    Retrieves the Groq API key from CLI argument, environment, .env file,
    or prompts the user if missing.
    """
    if cli_key and cli_key.strip():
        return cli_key.strip()

    env_key = os.environ.get("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key

    if not interactive:
        print("Error: GROQ_API_KEY environment variable is not set.", file=sys.stderr)
        print("Set it using: export GROQ_API_KEY='your_api_key'", file=sys.stderr)
        sys.exit(1)

    print("No Groq API key found in environment or .env file.")
    try:
        key = getpass.getpass("Enter your Groq API key: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        sys.exit(1)

    if not key:
        print("Error: API key cannot be empty.")
        sys.exit(1)

    # Save to local .env file so the user doesn't have to re-enter it
    try:
        save_pref = input("Save key to .env file for future use? (Y/n): ").strip().lower()
        if save_pref not in ('n', 'no'):
            save_key_to_env(key)
    except Exception:
        pass

    os.environ["GROQ_API_KEY"] = key
    return key


def read_file(file_path: str) -> str:
    """Reads article text from a file with error handling."""
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"File '{file_path}' does not exist.")

    if not path.is_file():
        raise IsADirectoryError(f"'{file_path}' is a directory, not a file.")

    if path.stat().st_size == 0:
        raise ValueError(f"The file '{file_path}' is empty.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1") as f:
            content = f.read().strip()

    if not content:
        raise ValueError(f"No readable text found in '{file_path}'.")

    return content


def read_user_input() -> str:
    """Reads multi-line text input directly from the user in the terminal."""
    print("\nEnter or paste your article below.")
    print("(Type 'EOF' on an empty line or press Ctrl+D / Ctrl+Z when done):\n")

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
        raise ValueError("No text was provided.")

    return text


def build_prompt(text: str) -> Tuple[str, str]:
    """
    Builds a high-compression system prompt enforcing strict formatting
    and at least 45% to 60% length reduction.
    """
    words = len(text.split())
    target_max = max(35, int(words * 0.50))

    if words < 120:
        system_prompt = (
            "You are an expert executive editor specializing in dense, high-impact summarization.\n"
            f"STRICT REQUIREMENT: The original text is {words} words. Your summary MUST be concise and "
            f"under {target_max} words (at least 45% reduction).\n\n"
            "FORMAT:\n"
            "Core Thesis:\n"
            "[1 concise sentence capturing the main point]\n\n"
            "Key Takeaways:\n"
            "• [First key insight]\n"
            "• [Second key insight]\n\n"
            "RULES:\n"
            "- Eliminate all filler words, repeated background, and conversational commentary.\n"
            "- Do not add greeting or meta-talk like 'Here is your summary'.\n"
            "- Synthesize concepts tightly."
        )
    else:
        system_prompt = (
            "You are an expert executive editor specializing in dense, high-impact summarization.\n"
            f"STRICT REQUIREMENT: The original text is {words} words. Your summary MUST achieve "
            f"at least a 45% to 60% reduction in length (target under {target_max} words).\n\n"
            "FORMAT:\n"
            "Executive Overview:\n"
            "[1 clear sentence stating the core thesis and significance]\n\n"
            "Key Findings:\n"
            "• [Concise, high-impact point detailing key evidence or mechanism]\n"
            "• [Concise, high-impact point detailing key evidence or mechanism]\n"
            "• [Concise, high-impact point detailing key evidence or mechanism]\n\n"
            "The Bottom Line:\n"
            "[1-2 sentences capturing the ultimate conclusion and future impact]\n\n"
            "RULES:\n"
            "- Strip out all redundant examples, side notes, and conversational filler.\n"
            "- Do not generate markdown tables, nested sub-bullets, or meta-comments.\n"
            "- Prioritize information density over exhaustive rewriting."
        )

    user_prompt = f"Article to summarize:\n\n{text}"
    return system_prompt, user_prompt


def summarize(client: Groq, text: str, model: str = MODEL_NAME) -> str:
    """
    Sends the article to Groq and returns a properly formatted,
    highly reduced executive summary.
    """
    system_prompt, user_prompt = build_prompt(text)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=1500
        )
        content = response.choices[0].message.content
        if not content:
            # Fallback in case of unexpected empty response
            reasoning = getattr(response.choices[0].message, 'reasoning', '')
            if reasoning:
                content = reasoning
        return content.strip() if content else "Summary generation completed with empty content."
    except NotFoundError:
        if model != FALLBACK_MODEL:
            return summarize(client, text, model=FALLBACK_MODEL)
        raise RuntimeError("Selected model is not available on Groq.")
    except AuthenticationError:
        raise RuntimeError("Invalid Groq API key. Check your key in .env")
    except RateLimitError:
        raise RuntimeError("Groq API rate limit reached. Please wait a moment and try again.")
    except APIConnectionError:
        raise RuntimeError("Connection failed. Please check your internet connectivity.")
    except APIStatusError as e:
        raise RuntimeError(f"Groq API error ({e.status_code}): {e.message}")
    except Exception as e:
        raise RuntimeError(f"Error during summarization: {str(e)}")


def display_summary(summary: str, original_words: int):
    """Prints the structured summary and clear word reduction statistics."""
    summary_words = len(summary.split())
    reduction = max(0.0, round((1.0 - (summary_words / max(original_words, 1))) * 100, 1))

    print("\n" + "=" * 62)
    print("                      ARTICLE SUMMARY")
    print("=" * 62)
    print(summary)
    print("-" * 62)
    print(f"Original: {original_words} words | Summary: {summary_words} words | Reduction: {reduction}%")
    print("=" * 62 + "\n")


def save_to_file(summary: str, original_words: int, output_path: str):
    """Saves the summary text and reduction stats to a file."""
    try:
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        summary_words = len(summary.split())
        reduction = max(0.0, round((1.0 - (summary_words / max(original_words, 1))) * 100, 1))

        output_content = (
            f"ARTICLE SUMMARY\n"
            f"{'=' * 62}\n"
            f"{summary}\n"
            f"{'-' * 62}\n"
            f"Original: {original_words} words | Summary: {summary_words} words | Reduction: {reduction}%\n"
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(output_content)
        print(f"Summary saved to: {output_path}")
    except Exception as e:
        print(f"Failed to save file: {e}")


def interactive_menu(client: Groq):
    """Clean and straightforward 3-option interactive CLI menu."""
    while True:
        print("\nArticle Summarizer")
        print("------------------")
        print("1. Summarize text from file")
        print("2. Enter text directly")
        print("3. Exit")

        try:
            choice = input("\nSelect an option (1-3): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if choice == "1":
            file_path = input("Enter file path: ").strip()
            if not file_path:
                print("Error: No file path provided.")
                continue
            try:
                text = read_file(file_path)
                orig_words = len(text.split())
                print(f"Processing '{file_path}' ({orig_words} words)...")
                summary = summarize(client, text)
                display_summary(summary, orig_words)

                save_opt = input("Save summary to a file? (y/n): ").strip().lower()
                if save_opt in ('y', 'yes'):
                    out_path = input("Enter output filename (default: summary.txt): ").strip() or "summary.txt"
                    save_to_file(summary, orig_words, out_path)
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "2":
            try:
                text = read_user_input()
                orig_words = len(text.split())
                print(f"Processing input text ({orig_words} words)...")
                summary = summarize(client, text)
                display_summary(summary, orig_words)

                save_opt = input("Save summary to a file? (y/n): ").strip().lower()
                if save_opt in ('y', 'yes'):
                    out_path = input("Enter output filename (default: summary.txt): ").strip() or "summary.txt"
                    save_to_file(summary, orig_words, out_path)
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "3":
            print("Goodbye.")
            break

        else:
            print("Invalid option. Please enter 1, 2, or 3.")


def parse_arguments():
    """Configures command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Summarize articles from a file or direct text input using Groq API."
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "-f", "--file",
        help="Path to article text file"
    )
    input_group.add_argument(
        "-t", "--text",
        help="Article text string"
    )

    parser.add_argument(
        "-o", "--output",
        help="File path to save the generated summary"
    )

    parser.add_argument(
        "-k", "--api-key",
        help="Groq API key (optional, can also use GROQ_API_KEY environment variable)"
    )

    return parser.parse_args()


def main():
    args = parse_arguments()
    is_non_interactive = bool(args.file or args.text)

    api_key = get_api_key(cli_key=args.api_key, interactive=not is_non_interactive)

    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        print(f"Initialization error: {e}")
        sys.exit(1)

    if args.file:
        try:
            text = read_file(args.file)
            orig_words = len(text.split())
            print(f"Processing '{args.file}' ({orig_words} words)...")
            summary = summarize(client, text)
            display_summary(summary, orig_words)

            if args.output:
                save_to_file(summary, orig_words, args.output)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.text:
        try:
            text = args.text.strip()
            if not text:
                raise ValueError("Text string cannot be empty.")
            orig_words = len(text.split())
            print(f"Processing text ({orig_words} words)...")
            summary = summarize(client, text)
            display_summary(summary, orig_words)

            if args.output:
                save_to_file(summary, orig_words, args.output)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        interactive_menu(client)


if __name__ == "__main__":
    main()
