"""Interactive CLI: AI Code Reviewer, DSA Mentor & Interview Coach.

Usage:
    export GEMINI_API_KEY=...
    python bot.py                 # interactive chat
    python bot.py --file Sol.java # review a file, then continue chatting
    python bot.py --no-search     # disable web search

Multi-line input: type your message, then enter a line containing only
`/send`. Other commands: /reset, /quit.
"""
import argparse
import os
import sys
from pathlib import Path

from google import genai
from google.genai import types

PROMPT_PATH = Path(__file__).with_name("system_prompt.md")
DEFAULT_MODEL = os.environ.get("REVIEWER_MODEL", "gemini-2.5-flash")


def read_multiline() -> str | None:
    """Read lines until `/send`. Returns None on quit/EOF."""
    lines = []
    while True:
        try:
            line = input("you> " if not lines else "...> ")
        except EOFError:
            return None
        stripped = line.strip()
        if not lines and stripped in ("/quit", "/exit"):
            return None
        if not lines and stripped == "/reset":
            return "/reset"
        if stripped == "/send":
            return "\n".join(lines)
        lines.append(line)


def stream_reply(chat, text):
    """Stream one assistant turn and print text live."""
    for chunk in chat.send_message_stream(text):
        if chunk.text:
            print(chunk.text, end="", flush=True)
    print("\n")


def new_chat(client, model, system, search):
    tools = [types.Tool(google_search=types.GoogleSearch())] if search else None
    config = types.GenerateContentConfig(system_instruction=system, tools=tools)
    return client.chats.create(model=model, config=config)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", help="source file to review in the first message")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--no-search", action="store_true", help="disable web search")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Set GEMINI_API_KEY first.", file=sys.stderr)
        return 1

    system = PROMPT_PATH.read_text(encoding="utf-8")
    client = genai.Client(api_key=api_key)
    search = not args.no_search
    chat = new_chat(client, args.model, system, search)

    pending = None
    if args.file:
        code = Path(args.file).read_text(encoding="utf-8")
        pending = (
            f"Please review this code from `{args.file}`. "
            "The problem statement is not provided; infer it and state assumptions.\n\n"
            f"```\n{code}\n```"
        )

    print("Code Reviewer Bot. Paste problem/code, then `/send`. /reset clears, /quit exits.\n")
    while True:
        if pending is None:
            pending = read_multiline()
            if pending is None:
                return 0
            if pending == "/reset":
                chat = new_chat(client, args.model, system, search)
                print("(conversation cleared)\n")
                pending = None
                continue
            if not pending.strip():
                pending = None
                continue
        text, pending = pending, None
        try:
            stream_reply(chat, text)
        except Exception as e:  # API/network errors
            print(f"\nAPI error: {e}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
