
"""Phase 1–4 CLI chat with SQLite memory and optional Langfuse tracing."""

import argparse

from agent_factory import open_agent
from agent_runner import ask
from trace_helpers import flush_traces


def main():
    # Step 1: Configure command-line arguments
    parser = argparse.ArgumentParser(
        description="AI Study Assistant - Single Agent"
    )

    parser.add_argument(
        "--thread-id",
        default="study-001",
        help="Conversation thread ID"
    )

    parser.add_argument(
        "--user-id",
        default="local-demo",
        help="Demo user identity"
    )

    args = parser.parse_args()

    # Step 2: Display application details
    print("AI Study Assistant")
    print("Type 'exit' or 'quit' to stop.")
    print(f"User ID: {args.user_id}")
    print(f"Thread ID: {args.thread_id}")

    # Step 3: Create the agent with user-specific memory
    try:
        with open_agent(user_id=args.user_id) as agent:

            # Step 4: Start interactive conversation
            while True:
                try:
                    question = input("\nYou: ").strip()

                except (KeyboardInterrupt, EOFError):
                    print("\nExiting AI Study Assistant.")
                    break

                if question.lower() in {"exit", "quit"}:
                    print("Goodbye!")
                    break

                if not question:
                    continue

                # Step 5: Send question to the agent
                try:
                    result = ask(
                        agent,
                        question,
                        thread_id=args.thread_id,
                        user_id=args.user_id
                    )

                    # Step 6: Display any tool calls
                    for call in result.get("tools", []):
                        print(
                            f"  [Tool] {call['name']}: "
                            f"{call['args']}"
                        )

                    # Step 7: Display the agent response
                    print(
                        "\nAgent:",
                        result.get("answer", "No answer returned.")
                    )

                    # Step 8: Display execution time
                    print(
                        f"({result.get('latency_ms', 0)} ms)"
                    )

                except Exception as exc:
                    print(f"\nError while processing request: {exc}")

    finally:
        # Step 9: Flush Langfuse traces when enabled
        flush_traces()


if __name__ == "__main__":
    main()
