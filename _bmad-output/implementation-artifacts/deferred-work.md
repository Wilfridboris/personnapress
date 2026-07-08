# Deferred Work

## Deferred from: code review of 10-1-legal-pages-bot-protection-polish (2026-07-08)

- Privacy Policy section 4 retention trigger description is vague — the policy states a 30-day inactivity flag then deletion at 37 days total but does not define what constitutes "inactivity"; if implementation uses account creation date or last login differently, the stated policy will be factually wrong. Legal text accuracy concern; verify against actual deletion scheduler behavior before launch.
