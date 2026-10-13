# ClientLab Remodeler Leads Rota

Decide who will answer new kitchen and bathroom leads when your office is closed.

This free tool makes a monthly duty list for your team. It shows who should reply to new leads in the evenings and at weekends. The aim is to give each homeowner a real reply within 60 minutes during those hours.

Print the rota and share it with your team. Then check how soon leads get a reply and how many suitable enquiries turn into booked appointments.

## How shifts are shared

We've tested several versions with different team sizes and days people can work.

The rota fills as many shifts as it can. It then aims to give each person the same number of shifts, or as close as possible. It plans around people who can only work on certain days. Next, it shares weekend cover as evenly as it can. Then it shares early and late weekend shifts and spreads the work across the weeks.

Some limits can prevent an even split. If nobody can cover a shift, it shows as unfilled.

## Make your rota in ChatGPT

If you have a paid version of ChatGPT, follow these steps:

1. Open [ChatGPT](https://chatgpt.com) and sign in.
2. Click "New chat".
3. At the top, before you type anything, choose "Work".
4. Copy the prompt below, paste it into the chat and press send.

Here is the prompt to copy and paste into ChatGPT Work:

```text
Create my team's ClientLab after-hours lead response rota using version 1.1.2.

Use the installed skill if it matches version 1.1.2 and the source commit below. Otherwise, install or update it using this package:
https://github.com/alan-clark-git/clientlab-remodeler-rota/archive/74bdcd55735780e7278559c9aa988281ded35986.zip

Read the package's SKILL.md and use its included scheduling engine. Verify version 1.1.2 and the source commit in the download link before running it. If you cannot retrieve or verify the package, stop and tell me.

Guide me through setup one question at a time: team count, full names, then availability and day assignments. Wait for each answer.

Create the rota for the current month, starting today in my business's local timezone, unless I request another month. Deliver only the branded, one-page printable PDF. Report any unfilled shifts and the version used.

After delivery, offer next month's rota using the same installation, team and restrictions. Apply any changes I give you. Download again only if the installation is missing or needs updating.
```

## Do you use ChatGPT Codex?

If yes, here is the prompt to paste directly into Codex. Codex will set everything up for you automatically.

```text
Use ClientLab Remodeler Leads Rota version 1.1.2 to create my team's after-hours lead response rota.

Use the installed skill if it matches version 1.1.2 and the source commit below. Otherwise, install or update it using this package:
https://github.com/alan-clark-git/clientlab-remodeler-rota/archive/74bdcd55735780e7278559c9aa988281ded35986.zip

Read the package's SKILL.md and use its included scheduling engine. Verify version 1.1.2 and the source commit in the download link before running it. If you cannot retrieve or verify the package, stop and tell me.

Guide me through setup one question at a time: team count, full names, then availability and day assignments. Wait for each answer.

Create the rota for the current month, starting today in my business's local timezone, unless I request another month. Deliver only the branded, one-page printable PDF. Report any unfilled shifts and the version used.

After delivery, offer next month's rota using the same installation, team and restrictions. Apply any changes I give you. Download again only if the installation is missing or needs updating.
```

## Use and copyright

You may use, copy and change the software under the [MIT licence](LICENSE). ClientLab's name, logo and artwork stay protected. You may use them with this rota and share the PDFs. Other uses need written permission. See the [brand terms](skills/after-hours-rota/assets/LICENSE).

Copyright 2026 Alan Clark.
