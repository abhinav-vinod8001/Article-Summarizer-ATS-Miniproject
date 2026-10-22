#!/usr/bin/env python3
"""
Article Summarizer
==================
A simple command-line application to summarize articles from files
or user input using the Groq API.
"""

import os
import sys
import argparse
import getpass
from pathlib import Path
from typing import Optional

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

    # Save to local .env file if requested
    env_file = Path(".env")
    if not env_file.exists():
        try:
            save_pref = input("Save key to .env file for future use? (y/n): ").strip().lower()
            if save_pref in ('y', 'yes'):
                with open(env_file, "w", encoding="utf-8") as f:
                    f.write(f"GROQ_API_KEY={key}\n")
                print("Key saved to .env")
        except Exception:
            pass

    os.environ["GROQ_API_KEY"] = key
    return key


def read_file(file_path: str) -> str:
    """Reads article text from a file with basic error handling."""
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


def summarize(client: Groq, text: str, model: str = MODEL_NAME) -> str:
    """Sends the article to the Groq API and returns a concise, structured summary."""
    system_prompt = (
        "You are an article summarization assistant. "
        "Summarize the provided article clearly and objectively. "
        "Capture the main points and key takeaways in a concise, well-structured format."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please summarize this article:\n\n{text}"}
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=1200
        )
        return response.choices[0].message.content
    except NotFoundError:
        # If the primary model is unavailable, try the fallback
        if model != FALLBACK_MODEL:
            return summarize(client, text, model=FALLBACK_MODEL)
        raise RuntimeError("Selected model is not available on Groq.")
    except AuthenticationError:
        raise RuntimeError("Invalid Groq API key.")
    except RateLimitError:
        raise RuntimeError("Groq API rate limit exceeded. Please wait a moment and try again.")
    except APIConnectionError:
        raise RuntimeError("Connection error. Please check your internet connection.")
    except APIStatusError as e:
        raise RuntimeError(f"Groq API error ({e.status_code}): {e.message}")
    except Exception as e:
        raise RuntimeError(f"Error during summarization: {str(e)}")


def save_to_file(summary: str, output_path: str):
    """Saves the summary text to a file."""
    try:
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(summary + "\n")
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
                print("\nGenerating summary...")
                summary = summarize(client, text)
                print("\nSummary:")
                print("----------------------------------------")
                print(summary)
                print("----------------------------------------")

                save_opt = input("\nSave summary to a file? (y/n): ").strip().lower()
                if save_opt in ('y', 'yes'):
                    out_path = input("Enter output filename (default: summary.txt): ").strip() or "summary.txt"
                    save_to_file(summary, out_path)
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "2":
            try:
                text = read_user_input()
                print("\nGenerating summary...")
                summary = summarize(client, text)
                print("\nSummary:")
                print("----------------------------------------")
                print(summary)
                print("----------------------------------------")

                save_opt = input("\nSave summary to a file? (y/n): ").strip().lower()
                if save_opt in ('y', 'yes'):
                    out_path = input("Enter output filename (default: summary.txt): ").strip() or "summary.txt"
                    save_to_file(summary, out_path)
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
        description="Summarize articles from a file or text input using Groq API."
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
            print("Generating summary...")
            summary = summarize(client, text)
            print("\nSummary:")
            print("----------------------------------------")
            print(summary)
            print("----------------------------------------")
            if args.output:
                save_to_file(summary, args.output)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.text:
        try:
            text = args.text.strip()
            if not text:
                raise ValueError("Text string cannot be empty.")
            print("Generating summary...")
            summary = summarize(client, text)
            print("\nSummary:")
            print("----------------------------------------")
            print(summary)
            print("----------------------------------------")
            if args.output:
                save_to_file(summary, args.output)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        interactive_menu(client)


if __name__ == "__main__":
    main()
