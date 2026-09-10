from twilio.request_validator import (
    RequestValidator
)

from app.config import (
    PUBLIC_BASE_URL,
    TWILIO_AUTH_TOKEN,
    VERIFY_TWILIO_SIGNATURE
)


def build_public_url(
    path: str
) -> str:

    return (
        f"{PUBLIC_BASE_URL}"
        f"{path}"
    )


def verify_twilio_signature(
    signature: str,
    form_data: dict,
    path: str
) -> bool:

    # Development mode can explicitly
    # disable verification.
    if not VERIFY_TWILIO_SIGNATURE:

        return True

    if not signature:

        return False

    if not TWILIO_AUTH_TOKEN:

        return False

    if not PUBLIC_BASE_URL:

        return False

    validator = RequestValidator(
        TWILIO_AUTH_TOKEN
    )

    webhook_url = (
        build_public_url(
            path
        )
    )

    return validator.validate(
        webhook_url,
        form_data,
        signature
    )