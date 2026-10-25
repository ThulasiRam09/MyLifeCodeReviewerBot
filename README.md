# MyLifeCodeReviewerBot

CLI agent: AI Code Reviewer, DSA Mentor & Interview Coach (Gemini API).

```
pip install -r reviewer_bot/requirements.txt
export GEMINI_API_KEY=...
python reviewer_bot/bot.py                    # interactive
python reviewer_bot/bot.py --file Sol.java    # review a file
python reviewer_bot/bot.py --no-search        # no web search
```

Paste a problem and code, then enter `/send` on its own line. `/reset` clears history; `/quit` exits.
The behaviour lives in `reviewer_bot/system_prompt.md`; edit it to tune the agent.
Set `REVIEWER_MODEL` to change the model (default `gemini-2.5-flash`).
