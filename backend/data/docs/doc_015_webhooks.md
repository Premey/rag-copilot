# Webhooks Guide

Webhooks allow CloudDesk to send real-time HTTP POST requests to your server when events occur.

## Setting Up Webhooks
1. Settings → Developer → Webhooks → Add Webhook.
2. Enter your endpoint URL (must be HTTPS).
3. Select events to subscribe to (see list below).
4. Optionally add a Secret Key for payload signature verification.
5. Click Save. CloudDesk sends a test ping to verify the endpoint.

## Supported Events
- `ticket.created` — New ticket submitted
- `ticket.updated` — Ticket fields changed
- `ticket.resolved` — Ticket marked resolved
- `ticket.closed` — Ticket closed
- `comment.added` — New comment on a ticket
- `sla.breached` — SLA timer expired

## Payload Format
```json
{
  "event": "ticket.created",
  "timestamp": "2026-03-02T14:00:00Z",
  "data": {
    "ticket_id": "CD-1042",
    "title": "Login page not loading",
    "priority": "high"
  }
}
```

## Verifying Signatures
Each request includes an `X-CloudDesk-Signature` header (HMAC-SHA256 of the payload using your Secret Key). Verify this on your server to ensure requests are from CloudDesk.

## Retry Policy
Failed deliveries (non-2xx response) are retried 3 times with exponential backoff: 1 min, 5 min, 30 min. After 3 failures the webhook is disabled and you are notified.
