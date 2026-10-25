"""Interactive CLI: AI Code Reviewer, DSA Mentor & Interview Coach.

Usage:
    export ANTHROPIC_API_KEY=...
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

import anthropic

PROMPT_PATH = Path(__file__).with_name("system_prompt.md")
DEFAULT_MODEL = os.environ.get("REVIEWER_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 16000

# Server-side web search, used for the company/interview research section.
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}


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


def stream_reply(client, model, system, messages, tools):
    """Stream one assistant turn, print text live, return content blocks."""
    kwargs = dict(model=model, max_tokens=MAX_TOKENS, system=system, messages=messages)
    if tools:
        kwargs["tools"] = tools
    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        final = stream.get_final_message()
    print("\n")
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", help="source file to review in the first message")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--no-search", action="store_true", help="disable web search")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY first.", file=sys.stderr)
        return 1

    system = PROMPT_PATH.read_text(encoding="utf-8")
    tools = [] if args.no_search else [WEB_SEARCH_TOOL]
    client = anthropic.Anthropic()
    messages: list[dict] = []

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
                messages.clear()
                print("(conversation cleared)\n")
                pending = None
                continue
            if not pending.strip():
                pending = None
                continue
        messages.append({"role": "user", "content": pending})
        pending = None
        try:
            final = stream_reply(client, args.model, system, messages, tools)
        except anthropic.APIError as e:
            print(f"\nAPI error: {e}", file=sys.stderr)
            messages.pop()
            continue
        messages.append({"role": "assistant", "content": final.content})


if __name__ == "__main__":
    sys.exit(main())
