# Troubleshooting Common Issues

A quick reference for the most common problems CloudDesk users encounter.

## Login Issues

**Can't log in / password not working**
→ Use Forgot Password to reset. Ensure Caps Lock is off. If using SSO, contact your IT admin.

**Account locked after failed attempts**
→ Accounts lock after 10 failed login attempts. Wait 30 minutes or contact support@clouddesk.io.

**2FA code not accepted**
→ Ensure your device clock is accurate (TOTP is time-based). If out of sync, adjust your device time or use a backup code.

## Ticket & Workflow Issues

**Ticket not assigning to the right team**
→ Check your automation rules under Settings → Automations. Verify rule conditions and priority order.

**SLA timer not pausing outside business hours**
→ Verify business hours are configured: Settings → SLA → Business Hours. Check the timezone is correct.

**Canned response variables not filling in**
→ Ensure the ticket has the required fields populated (e.g., {{customer_name}} requires the contact to have a full name set).

## Integration Issues

**Slack notifications stopped arriving**
→ Re-authorize the Slack integration at Settings → Integrations → Slack. Check if the bot was removed from the notification channel.

**Jira sync failing**
→ Atlassian OAuth tokens expire every 90 days. Re-connect at Settings → Integrations → Jira.

## Still Need Help?
- **In-app chat:** Live support (Mon–Fri, 9am–6pm UTC)
- **Email:** support@clouddesk.io
- **Status page:** status.clouddesk.io
