---
name: after-hours-rota
description: Create or revise a printable, colour-coded ClientLab calendar-month after-hours homeowner lead response rota for US remodelers. Collect staff names and any unavailable weekdays or dates, assign one 4:30 PM-11 PM weekday shift and two weekend shifts (8 AM-3:30 PM, 3:30 PM-11 PM) with different people, and export a one-page US Letter landscape PDF.
---

# ClientLab Remodeler Leads Rota

Create a straightforward one-page **monthly** lead response rota for remodelers. The user gets a US Letter landscape calendar with one full month, coloured staff assignments, a matching flat, fixed-capacity 41-row shift list on the left, and a branded header.

## Simple conversation - one question at a time

Begin a new setup with this message, then STOP and wait for the answer:

> Hi! You've made a smart decision to have your team respond to new homeowner enquiries within 60 minutes, seven days a week.
>
> Responding promptly can help you turn more of your existing leads into qualified appointments.
>
> Let's get your rota organised. How many team members would you like to include?

1. **Names.** Ask: "Great! Please enter the first name and surname of each team member." Accept names in any clear format, including comma-separated names; do not require one name per line. Validate the number.
2. **Availability and assignments.** Ask:

   > Are there any days you'd like assigned to specific team members, or days when certain people aren't available?
   >
   > For example, "Frank and Jane cover weekends, and everyone else covers weekdays" or "John can't do Tuesdays or Wednesdays."
   >
   > If there are no restrictions or preferences, just type "none."

   Interpret positive day assignments as actual scheduling constraints, as well as exclusions. For instance, if "Frank and Jane cover weekends and everyone else covers weekdays," make Frank and Jane eligible only on Saturday/Sunday, and the remaining team eligible only Monday-Friday. Accept natural language and match staff to their previously supplied names. Clarify only genuine ambiguity affecting assignments. Respect fixed shifts and never silently assign an unavailable person.
3. **Generate.** By default, use **the current calendar month and year** in the business's local timezone. **Begin assignments on today's business-local date**, never backfill earlier dates in the current month. Show the full calendar month with earlier dates visible but blank in the calendar. In the left shift list, always start from the **1st** of the month and reserve **41 equal shift rows**. For dates earlier than the start date, show the date and shift time(s) but leave the person area blank with a white background. If the user specifies a future month, begin on the first day of that month. Do not ask a separate month question in normal setup.

Do not ask about coverage hours, shift durations, employee contact information, a date to start, or formatting preferences. Fixed shifts are below. The **calendar view shows the entire selected calendar month** from the 1st to the final day, but the **schedule contains assignments only from the day the tool is used onward** (or the beginning of a future month). The month grid must align each date with its actual weekday, including empty lead/trailing cells and months spanning six calendar rows.

## Fixed shifts (never subdivide)

| Day | Time | People |
| --- | --- | --- |
| Monday-Friday | 4:30 PM-11:00 PM | One person per day |
| Saturday | 8:00 AM-3:30 PM | One person |
| Saturday | 3:30 PM-11:00 PM | A DIFFERENT person |
| Sunday | 8:00 AM-3:30 PM | One person |
| Sunday | 3:30 PM-11:00 PM | A DIFFERENT person |

No coverage after 11 PM and no overnight shifts. Staff are on call, not continuously seated at a desk. Target a meaningful response to homeowners within 60 minutes during scheduled hours.

## Scheduling

- Assign only current/future dates within the selected month, including weekends. Earlier dates in the month stay visible and blank in the calendar.
- Respect unavailability by recurring weekday and/or explicit date, including hours that overlap a fixed shift. Do not change the stated restrictions.
- Saturday's shifts must be worked by different people. Likewise Sunday. If insufficient eligible staff, mark the gap **UNFILLED**, never assign both shifts to the same person.
- Optimize only the remaining scheduling period, in this order: maximum coverage, total shift-count fairness across every named employee, weekend fairness among eligible staff, then early/late rotation, consecutive-day distribution and weekly spread. Earlier blank dates never count toward fairness.
- Use the bundled exact CP-SAT optimizer. Protect constrained employees' scarce opportunities through the global eligibility model; allow unequal weekend duties when needed for optimal total workloads. Each proven objective is fixed before optimizing the next. If any pass cannot prove optimality, report the error and do not deliver a heuristic PDF.
- Every staff member receives a distinct, consistently applied pastel colour in the supplied team order. The exact same colour must appear in the left-hand shift list and in each matching calendar-day assignment. **UNFILLED** must be highlighted distinctly.
- Use full names in the left-hand shift list. In the calendar, if two or more people share the same first name, show **first name + surname initial** such as **John S.** and **John B.**. When these labels also collide, use the full name to distinguish them. If the first name is unique, show the first name only.

## Layout rules that must be followed exactly

### Calendar cells

- First establish the **weekend cell** layout.
- Reserve the top strip for the date number.
- Use the remaining space below it.
- Saturday and Sunday each contain **two equal stacked coloured shift boxes** with a small consistent gap between them.
- Those two stacked weekend boxes determine the standard shift-box size.
- Every Monday-Friday cell contains **one coloured shift box with exactly the same height and width as one weekend shift box**.
- The weekday box is **not** stretched to fill the cell. It must be vertically centred so its midpoint aligns with the midpoint between the weekend's upper and lower boxes.
- This gives larger, easier-to-read names and times when printed.

### Left-hand shift list (original flat-row design; no stacked boxes)

- **Preserve the original flat full-width coloured-line shift list.** Each line is a single horizontal bar containing **date and weekday on the left, full staff name in the middle, shift time on the right**. NO new rounded inner bars, NO separate date-number column or stacked date labels.
- **Each shift gets its own line**. Weekdays have one line; Saturday and Sunday have TWO consecutive full-width lines, repeating the date on each line.
- Determine row height once from **available shift-list height divided by 41**, the largest possible number of shifts in a 31-day month (31 dates plus a maximum of 10 weekend days, each requiring a second shift). It must never be recalculated based on how many shifts remain after the rota start date.
- The flat list **always starts on the 1st of the month**, including pre-start dates. Every pre-start shift line shows its date, weekday and shift time, but has NO person's name and a WHITE background.
- Days in shorter months may leave a few unused blank rows at the bottom. Do NOT resize the rows to stretch to the bottom for a shorter month.
- Restore the original flat full-width pastel shading for assigned staff and maintain exactly the same assigned colour as the main calendar.
- Print full first and last names on assigned shift lines. Never switch the sidebar to the calendar's short first-name labels.

## PDF and HTML output

- **ONE US Letter landscape sheet/page for ONE COMPLETE MONTH**, not A4 and not weekly pages.
- Use the supplied combined banner `assets/header.png` (latest v2 with green-highlighted words), without altering it.
- Give the header area **more bottom padding** so the QR/diagnostic message does not sit hard against the divider area.
- Directly beneath the header, show the dynamic title: **"After-Hours Lead Response Rota {Month} {Year}"**.
- Use **Space Grotesk Bold** where the runtime can load it. For HTML, specify Space Grotesk with a sans-serif fallback. For PDF, use a safe sans-serif fallback if the font file is unavailable.
- Make the dynamic rota title **smaller than the diagnostic header message**, so the QR headline remains the primary visual headline.
- Left side: original flat-style shift list, fixed 41-row maximum capacity.
- Right side: Monday-Sunday month grid with correct weekday alignment.
- Footer: 60-minute response target and `clientlab.io` only.
- **Deliver only `rota.pdf` to the user.** Do not produce or attach `rota.html` or `schedule.json` as separate files. The scheduling engine may keep schedule data internally. PDF must stay one page, with no text clipping, even in six-row months. The flat list may widen for long full names. Calendar labels may use an ellipsis to fit; the full name stays in the shift list.

## Runtime

Retrieve the complete skill directory, including `scripts/`, `assets/` and `references/`. Paths are relative to this `SKILL.md`. Use the same engine in Codex, ChatGPT Work and ordinary ChatGPT where file retrieval and Python execution are available. Do not recreate the scheduling logic or substitute a newly designed PDF.

Read [references/input-schema.md](references/input-schema.md) when translating the user's names, assignments and exclusions into engine input. It also covers business-local dates and fixed individual assignments.

Install Python dependencies from this skill's `requirements.txt` if needed. Run from the skill directory:

```sh
python3 scripts/rota_engine.py /path/to/input.json --out /path/to/output
```

Keep the input private and deliver only `/path/to/output/rota.pdf`. The engine makes no network calls. If retrieval or execution is unavailable, explain the limitation and ask for the downloaded GitHub package or a session with Python execution. Do not claim that a PDF was generated.

For a version-pinned request, verify the installed package against the requested release version, full source commit and engine checksum. Reuse it only when it matches. Otherwise, retrieve and verify that release before continuing. Read this `SKILL.md` and execute `scripts/rota_engine.py` from the same verified package. Stop if verification fails. For later months, reuse the verified installation, staff information and restrictions.

Run bundled `scripts/rota_engine.py` if accessible. By default the engine uses the current execution date, but if the host knows the **business-local** date, pass `start_date: "YYYY-MM-DD"` to avoid a server-timezone mismatch. Do not ask the user to provide a start date.

## Generating and delivering the finished rota

- Before launching PDF generation, tell the user: "I'm creating your personalised monthly rota now. Please allow approximately 2–3 minutes. Your printable PDF will be ready shortly." Do not guarantee a fixed processing time.
- Create and attach **only the PDF**. Never present or link an HTML or JSON file.
- When the PDF is ready, write a short, tailored completion message. Example:

  > Your After-Hours Lead Response Rota for October 2026 is ready!
  >
  > As requested, Frank and Jane have been assigned weekend coverage, with the remaining team members rotating through weekdays.
  >
  > **Download your PDF below.** You can print it for your office or email it directly to your team.
  >
  > Would you like me to create next month's rota using the same team and availability preferences?

- Derive the month and the assignment summary from the actual generated rota. Never invent a person's name, imply restrictions were honoured if they were not, or claim complete coverage where any shift is `UNFILLED`. If gaps exist, clearly state how many shifts remain unfilled and offer to adjust the restrictions.
- Do **not** add a setup question about generating several future months. Keep the simple optional next-month question *after* delivery only. For repeated monthly use, reuse the team and recurring rules already supplied, apply any requested changes, and generate the requested next month from its first day. Retain explicit date exclusions as dates, never convert them into recurring restrictions.
