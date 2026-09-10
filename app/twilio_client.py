import asyncio

from twilio.base.exceptions import (
    TwilioRestException
)

from twilio.rest import (
    Client
)

from app.config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
    TWILIO_OUTBOUND_ENABLED,
    TWILIO_MAX_OUTBOUND_CHARACTERS
)

from app.logging_config import (
    get_logger
)


logger = get_logger(
    "twilio"
)


def prepare_whatsapp_body(
    message: str
) -> str:

    message = (
        message.strip()
    )

    if not message:

        return (
            "I couldn't generate a response. "
            "Please try again."
        )

    if (
        len(message)
        <= TWILIO_MAX_OUTBOUND_CHARACTERS
    ):

        return message

    suffix = (
        "\n\n[Response shortened for WhatsApp]"
    )

    available = (
        TWILIO_MAX_OUTBOUND_CHARACTERS
        - len(suffix)
    )

    return (
        message[:available].rstrip()
        + suffix
    )


def send_whatsapp_message_sync(
    to: str,
    body: str
):

    client = Client(
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN
    )

    return client.messages.create(
        body=prepare_whatsapp_body(
            body
        ),
        from_=TWILIO_WHATSAPP_FROM,
        to=to
    )


async def send_whatsapp_message(
    to: str,
    body: str
) -> dict:

    if not TWILIO_OUTBOUND_ENABLED:

        logger.warning(
            "whatsapp_outbound_skipped "
            "reason=disabled "
            "to_suffix=%s",
            to[-4:]
        )

        return {
            "ok": False,
            "reason": "disabled"
        }

    if not to.startswith(
        "whatsapp:+"
    ):

        logger.error(
            "whatsapp_outbound_failed "
            "reason=invalid_recipient"
        )

        return {
            "ok": False,
            "reason": "invalid_recipient"
        }

    try:

        sent_message = await asyncio.to_thread(
            send_whatsapp_message_sync,
            to,
            body
        )

        message_sid = str(
            getattr(
                sent_message,
                "sid",
                ""
            )
        )

        logger.info(
            "whatsapp_outbound_sent "
            "to_suffix=%s "
            "message_sid_suffix=%s",
            to[-4:],
            (
                message_sid[-6:]
                if message_sid
                else "-"
            )
        )

        return {
            "ok": True
        }

    except TwilioRestException as e:

        logger.error(
            "whatsapp_outbound_failed "
            "error_type=TwilioRestException "
            "status=%s "
            "code=%s "
            "to_suffix=%s",
            getattr(
                e,
                "status",
                None
            ),
            getattr(
                e,
                "code",
                None
            ),
            to[-4:]
        )

        return {
            "ok": False,
            "reason": "twilio_error"
        }

    except Exception:

        logger.exception(
            "whatsapp_outbound_failed "
            "error_type=unexpected "
            "to_suffix=%s",
            to[-4:]
        )

        return {
            "ok": False,
            "reason": "unexpected_error"
        }