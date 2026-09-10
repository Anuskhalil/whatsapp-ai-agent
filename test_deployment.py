from twilio.request_validator import (
    RequestValidator
)

import app.twilio_security as twilio_security

from app.config import (
    safe_config_snapshot,
    TAVILY_API_KEY,
    TWILIO_AUTH_TOKEN
)


def test_safe_snapshot():

    snapshot = (
        safe_config_snapshot()
    )

    snapshot_text = str(
        snapshot
    )

    if TAVILY_API_KEY:

        assert (
            TAVILY_API_KEY
            not in snapshot_text
        )

    if TWILIO_AUTH_TOKEN:

        assert (
            TWILIO_AUTH_TOKEN
            not in snapshot_text
        )

    print(
        "PASS: secrets not exposed "
        "in config snapshot"
    )


def test_twilio_signature():

    original_verify = (
        twilio_security
        .VERIFY_TWILIO_SIGNATURE
    )

    original_token = (
        twilio_security
        .TWILIO_AUTH_TOKEN
    )

    original_base_url = (
        twilio_security
        .PUBLIC_BASE_URL
    )

    try:

        test_token = (
            "test_auth_token"
        )

        test_base_url = (
            "https://example.com"
        )

        test_path = (
            "/webhook/whatsapp"
        )

        params = {
            "From": (
                "whatsapp:+1234567890"
            ),
            "Body": "Hello"
        }

        url = (
            test_base_url
            + test_path
        )

        validator = (
            RequestValidator(
                test_token
            )
        )

        valid_signature = (
            validator.compute_signature(
                url,
                params
            )
        )

        twilio_security.VERIFY_TWILIO_SIGNATURE = (
            True
        )

        twilio_security.TWILIO_AUTH_TOKEN = (
            test_token
        )

        twilio_security.PUBLIC_BASE_URL = (
            test_base_url
        )

        assert (
            twilio_security
            .verify_twilio_signature(
                signature=valid_signature,
                form_data=params,
                path=test_path
            )
            is True
        )

        assert (
            twilio_security
            .verify_twilio_signature(
                signature="invalid",
                form_data=params,
                path=test_path
            )
            is False
        )

    finally:

        twilio_security.VERIFY_TWILIO_SIGNATURE = (
            original_verify
        )

        twilio_security.TWILIO_AUTH_TOKEN = (
            original_token
        )

        twilio_security.PUBLIC_BASE_URL = (
            original_base_url
        )

    print(
        "PASS: Twilio signature "
        "verification"
    )


def main():

    test_safe_snapshot()

    test_twilio_signature()

    print()

    print(
        "All deployment security "
        "tests passed."
    )


if __name__ == "__main__":

    main()