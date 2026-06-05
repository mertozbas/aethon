"""Webhook endpoint support.

External trigger points for SOPs and messages via HTTP POST.
Supports optional HMAC-SHA256 secret verification.
"""

import hashlib
import hmac
import json
import logging

from fastapi import Request, HTTPException

from aethon.channels.base import InboundMessage


logger = logging.getLogger("aethon.webhooks")


def setup_webhooks(app, router, secret: str = ""):
    """Register webhook endpoints on the FastAPI app.

    Args:
        app: FastAPI application instance.
        router: MessageRouter for handling messages.
        secret: Optional HMAC-SHA256 secret for verification.
    """

    def _verify_secret(request: Request, body: bytes) -> bool:
        if not secret:
            return True
        signature = request.headers.get("X-Aethon-Signature", "")
        expected = hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    # NOTE: /webhook/trigger MUST be defined BEFORE /webhook/{channel}
    # so FastAPI matches the specific route first.

    @app.post("/webhook/trigger")
    async def webhook_trigger(request: Request):
        """Generic SOP trigger endpoint."""
        body_bytes = await request.body()
        if not _verify_secret(request, body_bytes):
            raise HTTPException(status_code=403, detail="Invalid signature")

        body = json.loads(body_bytes)
        text = body.get("text", "")
        sop_name = body.get("sop_name", "")

        if sop_name:
            text = f"/{sop_name} {text}".strip()

        inbound = InboundMessage(
            channel="webhook:trigger",
            sender_id="webhook",
            sender_name="Webhook",
            text=text,
            raw=body,
        )
        response = await router.handle(inbound)

        result_channel = body.get("channel", "")
        recipient = body.get("recipient", "")
        if result_channel and response:
            try:
                from aethon.tools.messaging import get_gateway
                from aethon.channels.base import OutboundMessage

                gw = get_gateway()
                if gw and result_channel in gw.adapters:
                    msg = OutboundMessage(
                        channel=result_channel,
                        recipient_id=recipient or "default",
                        text=response.text,
                    )
                    await gw.adapters[result_channel].send(msg)
            except Exception as e:
                logger.warning(f"Webhook result delivery error: {e}")

        return {
            "status": "ok",
            "response": response.text if response else None,
        }

    @app.post("/webhook/{channel}")
    async def webhook_channel(channel: str, request: Request):
        """Channel-specific webhook endpoint."""
        body_bytes = await request.body()
        if not _verify_secret(request, body_bytes):
            raise HTTPException(status_code=403, detail="Invalid signature")

        body = json.loads(body_bytes)
        inbound = InboundMessage(
            channel=f"webhook:{channel}",
            sender_id="webhook",
            sender_name="Webhook",
            text=body.get("text", ""),
            raw=body,
        )
        response = await router.handle(inbound)
        return {
            "status": "ok",
            "response": response.text if response else None,
        }
