from app.memory_extractor import (
    extract_direct_memories,
    should_extract_memory
)


def find_memory(
    memories: list,
    memory_type: str,
    memory_key: str
):

    for memory in memories:

        if (
            memory["type"]
            == memory_type
            and
            memory["key"]
            == memory_key
        ):

            return memory

    return None


def test_non_memory_requests():

    messages = [
        (
            "What's the weather "
            "in Karachi?"
        ),
        (
            "Search online for "
            "the latest Python release."
        ),
        (
            "Calculate 20 divided by 4."
        ),
        (
            "Explain machine learning "
            "in simple words."
        )
    ]

    for message in messages:

        assert (
            should_extract_memory(
                message
            )
            is False
        )

    print(
        "PASS: temporary requests "
        "skip memory extraction"
    )


def test_name():

    memories = (
        extract_direct_memories(
            "My name is Anus Khalil."
        )
    )

    memory = find_memory(
        memories,
        "identity",
        "name"
    )

    assert memory is not None

    assert (
        memory["value"]
        == "Anus Khalil"
    )

    print(
        "PASS: name uses direct memory"
    )


def test_location():

    memories = (
        extract_direct_memories(
            "I live in Karachi."
        )
    )

    memory = find_memory(
        memories,
        "identity",
        "location"
    )

    assert memory is not None

    assert (
        memory["value"]
        == "Karachi"
    )

    print(
        "PASS: location uses direct memory"
    )


def test_learning():

    memories = (
        extract_direct_memories(
            "I am learning AI Engineering."
        )
    )

    memory = find_memory(
        memories,
        "learning",
        "subject"
    )

    assert memory is not None

    assert (
        memory["value"]
        == "AI Engineering"
    )

    print(
        "PASS: learning uses direct memory"
    )


def test_project():

    memories = (
        extract_direct_memories(
            (
                "I am building NexusAI, "
                "a WhatsApp AI Agent."
            )
        )
    )

    memory = find_memory(
        memories,
        "project",
        "current_project"
    )

    assert memory is not None

    print(
        "PASS: project uses direct memory"
    )


def main():

    test_non_memory_requests()

    test_name()

    test_location()

    test_learning()

    test_project()

    print()
    print(
        "All memory performance "
        "tests passed."
    )


if __name__ == "__main__":

    main()