# Automations & Rules Engine

CloudDesk's automations let you auto-assign, escalate, tag, and respond to tickets based on conditions — no code needed.

## Creating an Automation
1. Settings → Automations → New Rule.
2. Set a **Trigger**: When a ticket is created / updated / SLA breached / tag added.
3. Set **Conditions**: Filter by priority, category, customer email domain, subject keyword, etc.
4. Set **Actions**: Assign to agent/team, change status, add tag, send email, post Slack message.
5. Name and save the rule.

## Example Rules
**Auto-assign billing tickets to the Billing team:**
- Trigger: Ticket created
- Condition: Category = "Billing"
- Action: Assign to Team = "Billing Team"

**Auto-close stale tickets:**
- Trigger: Ticket not updated for 7 days
- Condition: Status = "Pending Customer"
- Action: Set status = "Closed", send closure email

## Rule Priority
Rules execute in priority order (1 = first). Drag to reorder. A ticket can match multiple rules — all matching rules execute unless 'Stop processing' is checked.

## Testing Rules
Use the 'Test Rule' button and paste a sample ticket payload to preview which actions would fire.
