import asyncio

from app.agent import run_agent

from app.memory import (
    clear_history,
    get_summary,
    get_user_memories
)


async def main():

    current_user = "user_1"

    print(
        "NexusAI Multi-User Conversation Test"
    )
    print()
    print("Commands:")
    print("  /user user_1   - Switch user")
    print("  /clear         - Clear current user memory")
    print("  /summary       - Show conversation summary")
    print("  /memories      - Show structured memories")
    print("  /exit          - Exit program")
    print()
    print(
        f"Current user: {current_user}"
    )
    print()

    while True:

        user_input = input(
            f"{current_user} > "
        ).strip()

        if not user_input:
            continue

        normalized_input = (
            user_input.lower()
        )

        if normalized_input in [
            "/exit",
            "exit"
        ]:

            print("Goodbye!")
            break

        if (
            normalized_input.startswith(
                "/user "
            )
            or
            normalized_input.startswith(
                "user "
            )
        ):

            new_user = user_input.split(
                " ",
                1
            )[1].strip()

            if not new_user:

                print(
                    "Please provide a user ID."
                )

                continue

            current_user = new_user

            print()
            print(
                f"Switched to user: "
                f"{current_user}"
            )
            print()

            continue

        if normalized_input in [
            "/clear",
            "clear"
        ]:

            clear_history(
                current_user
            )

            print()
            print(
                f"Memory cleared for "
                f"{current_user}."
            )
            print()

            continue

        if normalized_input == "/summary":

            summary = get_summary(
                current_user
            )

            print()

            if summary:

                print(
                    "Conversation summary:"
                )
                print()
                print(summary)

            else:

                print(
                    "No summary exists."
                )

            print()

            continue

        if normalized_input == "/memories":

            memories = (
                get_user_memories(
                    current_user
                )
            )

            print()

            if not memories:

                print(
                    "No structured memories exist."
                )

            else:

                print(
                    "Structured memories:"
                )

                print()

                for memory in memories:

                    print(
                        f"- [{memory['type']}] "
                        f"{memory['key']} = "
                        f"{memory['value']} "
                        f"(importance: "
                        f"{memory['importance']})"
                    )

            print()

            continue

        answer = await run_agent(
            user_id=current_user,
            user_message=user_input
        )

        print()
        print(
            f"AI: {answer}"
        )
        print()

if __name__ == "__main__":

    asyncio.run(
        main()
    )