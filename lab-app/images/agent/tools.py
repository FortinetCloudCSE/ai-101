"""
Hardcoded tool implementations for Lab 2.

query_employees  – HR database lookup (SQLite-backed)
send_message     – simulated outbound message (in-memory outbox)

Lab 3 replaces this module with MCP-discovered equivalents; the agent loop
is unchanged. The SQLi in query_employees is intentional — see Lab 4.
"""
import json
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/app/employees.db")

# In-memory outbox — send_message appends here; nothing leaves the container.
_outbox: list[dict] = []


def query_employees(filter: str) -> str:
    """Return employees matching the given department name."""
    conn = sqlite3.connect(DB_PATH)
    try:
        # String concatenation here is deliberate — the vulnerability is the lesson.
        sql = (
            "SELECT name, dept, manager, salary, confidential "
            f"FROM employees WHERE dept = '{filter}'"
        )
        rows = conn.execute(sql).fetchall()
    except sqlite3.OperationalError as exc:
        return json.dumps({"error": str(exc)})
    finally:
        conn.close()

    if not rows:
        return json.dumps({"result": "No employees found."})
    return json.dumps({
        "employees": [
            {"name": r[0], "dept": r[1], "manager": r[2],
             "salary": r[3], "confidential": r[4]}
            for r in rows
        ]
    })


def send_message(to: str, body: str) -> str:
    """Queue a message to the outbox (no real email is sent)."""
    _outbox.append({"to": to, "body": body})
    return json.dumps({"status": "queued", "to": to, "preview": body[:120]})


def get_outbox() -> list[dict]:
    return list(_outbox)


# OpenAI-format tool schemas — used directly by the agent in hardcoded mode
# and mirrored by the MCP server in Lab 3.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "query_employees",
            "description": "Look up employees in the HR database by department name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": (
                            "Department to look up, e.g. 'Engineering', 'Finance', 'Sales'."
                        ),
                    }
                },
                "required": ["filter"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_message",
            "description": "Send a message to a person or email address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient name or email address.",
                    },
                    "body": {
                        "type": "string",
                        "description": "Message body.",
                    },
                },
                "required": ["to", "body"],
            },
        },
    },
]

# Dispatch table: tool name -> callable that accepts a kwargs dict
TOOL_FUNCTIONS: dict = {
    "query_employees": lambda args: query_employees(**args),
    "send_message":    lambda args: send_message(**args),
}
