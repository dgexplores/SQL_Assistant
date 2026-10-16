"""Slack bot: mention the bot with a data question, get rows back.

Mention @dbbot in any channel it belongs to:
    @dbbot unpaid orders from Berlin?

The question goes through SQLAssistant.ask(), so the same guards apply:
single read-only statement, row caps, one failure shape. Text it cannot
answer comes back as a plain error message, never a traceback.

Setup (all free):
  1. Create an app at https://api.slack.com/apps, enable Socket Mode,
     subscribe to the app_mention event, add scopes
     app_mentions:read and chat:write, install it to your workspace.
  2. export SLACK_BOT_TOKEN=xoxb-... SLACK_APP_TOKEN=xoxa-...
     export DB_URL=sqlite:///shop.db
     # optional: LLM_MODEL, OPENAI_BASE_URL, OPENAI_API_KEY (defaults to OpenAI gpt-4o-mini)
  3. pip install -r slack-requirements.txt
     python slack_bot.py
"""

import os

from assistant import SQLAssistant

MAX_CHARS = 2500

_assistant = None


def get_assistant():
    # Built on first use so importing this module never needs env vars.
    global _assistant
    if _assistant is None:
        _assistant = SQLAssistant(
            os.environ["DB_URL"],
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )
    return _assistant


def strip_mention(text):
    # Slack formats mentions as <@U12345>; the question is whatever follows.
    return text.split(">", 1)[-1].strip()


def format_rows(result):
    if "error" in result:
        return f"Could not answer that: {result['error']}"
    rows = result["rows"]
    if not rows:
        return "No rows matched."
    cols = list(rows[0].keys())
    lines = [" | ".join(cols)]
    lines += [" | ".join(str(r.get(c, "")) for c in cols) for r in rows]
    text = "\n".join(lines)
    if result.get("truncated"):
        text += "\n(showing first rows only)"
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n... (cut off, too long for Slack)"
    return f"```\n{text}\n```"


def build_app():
    from slack_bolt import App

    app = App(token=os.environ["SLACK_BOT_TOKEN"])

    @app.event("app_mention")
    def handle_mention(body, say):
        question = strip_mention(body["event"].get("text", ""))
        if not question:
            say("Ask me about the database, e.g. `unpaid orders from Berlin?`")
            return
        say(format_rows(get_assistant().ask(question)))

    return app


def main():
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    get_assistant()  # fail fast on a bad DB_URL before connecting to Slack
    SocketModeHandler(build_app(), os.environ["SLACK_APP_TOKEN"]).run()


if __name__ == "__main__":
    main()
