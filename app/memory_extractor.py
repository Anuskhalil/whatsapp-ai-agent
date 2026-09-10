import asyncio
import json
import re

from app.llm import ask_llm

from app.memory import (
    save_user_memory
)

from app.logging_config import (
    get_logger
)
from app.config import (
    MEMORY_LLM_TIMEOUT_SECONDS
)


logger = get_logger(
    "memory"
)



# ---------------------------------
# CANONICAL MEMORY SCHEMA
# ---------------------------------

ALLOWED_MEMORY_KEYS = {
    "identity": {
        "name",
        "location",
        "occupation"
    },
    "preference": {
        "response_style",
        "language",
        "technical_preference"
    },
    "goal": {
        "current_goal"
    },
    "project": {
        "current_project"
    },
    "learning": {
        "subject"
    },
    "constraint": {
        "continuing_constraint"
    }
}


# ---------------------------------
# HIGH-CONFIDENCE DIRECT PATTERNS
# ---------------------------------

DIRECT_PATTERNS = [
    (
        "identity",
        "name",
        9,
        re.compile(
            (
                r"\bmy name is\s+"
                r"(.+?)"
                r"(?=\s+and\s+(?:i|my)\b|[.!?]|$)"
            ),
            re.IGNORECASE
        )
    ),
    (
        "identity",
        "location",
        8,
        re.compile(
            (
                r"\bi live in\s+"
                r"(.+?)"
                r"(?=\s+and\s+(?:i|my)\b|[.!?]|$)"
            ),
            re.IGNORECASE
        )
    ),
    (
        "identity",
        "location",
        8,
        re.compile(
            (
                r"\bi(?:\s+am|'m)\s+"
                r"(?:based|located)\s+in\s+"
                r"(.+?)"
                r"(?=\s+and\s+(?:i|my)\b|[.!?]|$)"
            ),
            re.IGNORECASE
        )
    ),
    (
        "identity",
        "occupation",
        8,
        re.compile(
            (
                r"\bi work as\s+"
                r"(.+?)"
                r"(?=\s+and\s+(?:i|my)\b|[.!?]|$)"
            ),
            re.IGNORECASE
        )
    ),
    (
        "learning",
        "subject",
        8,
        re.compile(
            (
                r"\bi(?:\s+am|'m)\s+learning\s+"
                r"(.+?)"
                r"(?=\s+and\s+(?:i|my)\b|[.!?]|$)"
            ),
            re.IGNORECASE
        )
    ),
    (
        "learning",
        "subject",
        8,
        re.compile(
            (
                r"\bi(?:\s+am|'m)\s+studying\s+"
                r"(.+?)"
                r"(?=\s+and\s+(?:i|my)\b|[.!?]|$)"
            ),
            re.IGNORECASE
        )
    ),
    (
        "project",
        "current_project",
        8,
        re.compile(
            (
                r"\bi(?:\s+am|'m)\s+building\s+"
                r"(.+?)"
                r"(?=\s+and\s+(?:i|my)\b|[.!?]|$)"
            ),
            re.IGNORECASE
        )
    ),
    (
        "project",
        "current_project",
        8,
        re.compile(
            (
                r"\bi(?:\s+am|'m)\s+working on\s+"
                r"(.+?)"
                r"(?=\s+and\s+(?:i|my)\b|[.!?]|$)"
            ),
            re.IGNORECASE
        )
    ),
    (
        "goal",
        "current_goal",
        8,
        re.compile(
            (
                r"\bmy goal is\s+"
                r"(.+?)"
                r"(?=\s+and\s+(?:i|my)\b|[.!?]|$)"
            ),
            re.IGNORECASE
        )
    ),
    (
        "preference",
        "response_style",
        7,
        re.compile(
            (
                r"\bmy preferred response style is\s+"
                r"(.+?)"
                r"(?=\s+and\s+(?:i|my)\b|[.!?]|$)"
            ),
            re.IGNORECASE
        )
    )
]


# ---------------------------------
# POSSIBLE MEMORY SIGNALS
# ---------------------------------

CANDIDATE_PATTERNS = [
    re.compile(
        r"\bi prefer\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\bmy preference is\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\bi want to\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\bi plan to\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\bmy long[- ]term goal is\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\bmy job is\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\bi(?:\s+am|'m)\s+from\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\bi need to\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\bi cannot\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\bi can't\b",
        re.IGNORECASE
    )
]


# ---------------------------------
# OBVIOUS REQUEST PREFIXES
# ---------------------------------

REQUEST_PREFIXES = (
    "calculate ",
    "search ",
    "search online",
    "search the web",
    "look up ",
    "find ",
    "explain ",
    "tell me ",
    "show me ",
    "give me ",
    "write ",
    "create ",
    "summarize ",
    "translate ",
    "what ",
    "what's ",
    "whats ",
    "how ",
    "why ",
    "when ",
    "where ",
    "who ",
    "is ",
    "are ",
    "can ",
    "could ",
    "would ",
    "should ",
    "do ",
    "does "
)


TRANSIENT_SELF_REQUEST_PREFIXES = (
    "i want to know ",
    "i want you to ",
    "i need you to ",
    "i need help with "
)


LLM_FAILURE_PREFIXES = (
    "AI is taking too long",
    "AI service is currently unavailable",
    "AI service returned an error",
    "Could not communicate with the AI service",
    "Something went wrong while generating"
)


# ---------------------------------
# HELPERS
# ---------------------------------

def clean_memory_value(
    value: str
) -> str:

    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    value = value.strip(
        " \t\r\n.,!?;:"
    )

    return value[:300]


def deduplicate_memories(
    memories: list
) -> list:

    unique = {}

    for memory in memories:

        key = (
            memory["type"],
            memory["key"]
        )

        unique[key] = memory

    return list(
        unique.values()
    )


# ---------------------------------
# FAST DIRECT EXTRACTION
# ---------------------------------

def extract_direct_memories(
    user_message: str
) -> list:

    memories = []

    for (
        memory_type,
        memory_key,
        importance,
        pattern
    ) in DIRECT_PATTERNS:

        match = pattern.search(
            user_message
        )

        if not match:
            continue

        value = clean_memory_value(
            match.group(1)
        )

        if not value:
            continue

        memories.append({
            "type": memory_type,
            "key": memory_key,
            "value": value,
            "importance": importance
        })

    # ---------------------------------
    # RESPONSE-STYLE PREFERENCE
    # ---------------------------------

    preference_match = re.search(
        (
            r"\bi prefer\s+"
            r"(.+?)"
            r"(?=\s+and\s+(?:i|my)\b|[.!?]|$)"
        ),
        user_message,
        re.IGNORECASE
    )

    if preference_match:

        preference_value = (
            clean_memory_value(
                preference_match.group(1)
            )
        )

        style_terms = {
            "concise",
            "short",
            "brief",
            "detailed",
            "simple",
            "technical",
            "explanation",
            "explanations",
            "answer",
            "answers",
            "response",
            "responses"
        }

        normalized_words = set(
            re.findall(
                r"[a-zA-Z]+",
                preference_value.lower()
            )
        )

        if (
            preference_value
            and
            normalized_words.intersection(
                style_terms
            )
        ):

            memories.append({
                "type": "preference",
                "key": "response_style",
                "value": preference_value,
                "importance": 7
            })

    return deduplicate_memories(
        memories
    )


# ---------------------------------
# SHOULD WE CALL THE MEMORY LLM?
# ---------------------------------

def should_extract_memory(
    user_message: str
) -> bool:

    message = user_message.strip()

    if not message:
        return False

    # High-confidence facts should
    # always be processed.
    if extract_direct_memories(
        message
    ):

        return True

    normalized = " ".join(
        message.lower().split()
    )

    # Questions are normally not
    # durable user facts.
    if "?" in normalized:

        return False

    if normalized.startswith(
        REQUEST_PREFIXES
    ):

        return False

    if normalized.startswith(
        TRANSIENT_SELF_REQUEST_PREFIXES
    ):

        return False

    return any(
        pattern.search(
            normalized
        )
        for pattern in CANDIDATE_PATTERNS
    )


# ---------------------------------
# ROBUST JSON PARSING
# ---------------------------------

def parse_memory_json(
    result: str
) -> list:

    text = result.strip()

    if not text:

        return []

    if text.startswith(
        LLM_FAILURE_PREFIXES
    ):

        logger.warning(
            "memory_extraction_llm_failed"
        )

        return []

    # Remove common Markdown fences.
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    start = text.find(
        "["
    )

    end = text.rfind(
        "]"
    )

    if (
        start == -1
        or
        end == -1
        or
        end < start
    ):

        logger.warning(
            "memory_extraction_invalid_json"
        )

        return []

    json_text = text[
        start:end + 1
    ]

    try:

        parsed = json.loads(
            json_text
        )

    except json.JSONDecodeError:

        logger.warning(
            "memory_extraction_invalid_json"
        )

        return []

    if not isinstance(
        parsed,
        list
    ):

        return []

    return parsed


# ---------------------------------
# LLM FALLBACK EXTRACTION
# ---------------------------------

async def extract_memories(
    user_message: str
) -> list:

    prompt = f"""
You extract stable long-term facts explicitly stated ABOUT the user.

User message:
{user_message}

Only save durable information that may be useful in future conversations.

Use ONLY these type/key combinations:

identity:
- name
- location
- occupation

preference:
- response_style
- language
- technical_preference

goal:
- current_goal

project:
- current_project

learning:
- subject

constraint:
- continuing_constraint

Examples:

"My name is Anus Khalil."
→ identity / name / Anus Khalil

"I live in Karachi."
→ identity / location / Karachi

"I am learning AI Engineering."
→ learning / subject / AI Engineering

"I am building NexusAI."
→ project / current_project / NexusAI

"I prefer concise technical explanations."
→ preference / response_style / concise technical explanations

"My goal is to deploy NexusAI."
→ goal / current_goal / deploy NexusAI

Do NOT infer facts from ordinary requests.

These must return []:

"Explain machine learning."
"What's the weather in Karachi?"
"Search online for the latest Python release."
"Calculate 20 divided by 4."
"Tell me about London."
"Give me a simple explanation of neural networks."

A location mentioned in a weather or search request is NOT the user's
location unless the user explicitly says they live there.

A topic mentioned in a question is NOT automatically the user's goal,
occupation, preference, project, or learning subject.

Do not store:
- greetings
- casual conversation
- temporary requests
- calculations
- weather queries
- search queries
- current news queries
- passwords
- API keys
- OTPs
- tokens
- financial secrets
- assistant guesses

If there is no explicit durable user fact, return exactly:

[]

Otherwise return ONLY valid JSON:

[
  {{
    "type": "goal",
    "key": "current_goal",
    "value": "Example goal",
    "importance": 8
  }}
]

Importance must be an integer from 1 to 10.

Return no Markdown and no explanation.
"""

    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]

    try:

        result = await asyncio.wait_for(
            ask_llm(
                messages,
                use_tools=False
            ),
            timeout=(
                MEMORY_LLM_TIMEOUT_SECONDS
            )
        )

    except TimeoutError:

        logger.warning(
            "memory_extraction_timeout "
            "timeout_s=%.1f",
            MEMORY_LLM_TIMEOUT_SECONDS
        )

        return []

    parsed_memories = (
        parse_memory_json(
            result
        )
    )

    valid_memories = []

    for memory in parsed_memories:

        if not isinstance(
            memory,
            dict
        ):

            continue

        memory_type = memory.get(
            "type"
        )

        memory_key = memory.get(
            "key"
        )

        value = memory.get(
            "value"
        )

        importance = memory.get(
            "importance",
            5
        )

        allowed_keys = (
            ALLOWED_MEMORY_KEYS.get(
                memory_type
            )
        )

        if not allowed_keys:

            continue

        if (
            memory_key
            not in allowed_keys
        ):

            continue

        if not value:

            continue

        value = clean_memory_value(
            str(value)
        )

        if not value:

            continue

        try:

            importance = int(
                importance
            )

        except (
            TypeError,
            ValueError
        ):

            importance = 5

        importance = max(
            1,
            min(
                importance,
                10
            )
        )

        valid_memories.append({
            "type": memory_type,
            "key": memory_key,
            "value": value,
            "importance": importance
        })

    return deduplicate_memories(
        valid_memories
    )


# ---------------------------------
# COMPLETE MEMORY EXTRACTION FLOW
# ---------------------------------

async def extract_and_store_memories(
    user_id: str,
    user_message: str
):

    # ---------------------------------
    # FAST PATH
    # ---------------------------------

    memories = (
        extract_direct_memories(
            user_message
        )
    )

    source = "direct"

    # ---------------------------------
    # NO MEMORY CANDIDATE
    # ---------------------------------

    if not memories:

        if not should_extract_memory(
            user_message
        ):

            logger.info(
                "memory_extraction_skipped "
                "reason=no_candidate"
            )

            return []

        # ---------------------------------
        # LLM FALLBACK
        # ---------------------------------

        source = "llm"

        logger.info(
            "memory_extraction_llm_started"
        )

        memories = await extract_memories(
            user_message
        )

    # ---------------------------------
    # SAVE
    # ---------------------------------

    for memory in memories:

        save_user_memory(
            user_id=user_id,
            memory_type=memory["type"],
            memory_key=memory["key"],
            memory_value=memory["value"],
            importance=memory[
                "importance"
            ]
        )

        logger.info(
            "memory_saved "
            "source=%s "
            "type=%s "
            "key=%s",
            source,
            memory["type"],
            memory["key"]
        )

    return memories