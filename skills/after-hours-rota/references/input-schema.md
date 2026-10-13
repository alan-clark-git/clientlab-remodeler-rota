# Engine input

The assistant translates the conversation into a private UTF-8 JSON file. Users do not need to write JSON.

```json
{
  "month": "2027-05",
  "staff": [
    {"name": "Frank Jones", "unavailable": [{"days": [0, 1, 2, 3, 4]}]},
    {"name": "Jane Adams", "unavailable": [{"days": [0, 1, 2, 3, 4]}]},
    {"name": "John Smith", "unavailable": [{"days": [5, 6]}]},
    {"name": "Mary Wilson", "unavailable": [{"days": [5, 6], "dates": ["2027-05-12"]}]},
    {"name": "Bill Brown", "unavailable": [{"days": [5, 6]}]}
  ]
}
```

This assigns Frank and Jane to weekends, with John, Mary and Bill covering weekdays. Mary also cannot cover May 12.

- `staff`: a nonempty list of full-name strings or objects with `name` and an optional `unavailable` list. Names must be unique ignoring case. Blank names and the reserved name `UNFILLED` are rejected.
- `month`: optional `YYYY-MM`, or an integer from 1 through 12 with an optional `year`. Omit for the current month.
- `start_date`: optional `YYYY-MM-DD` within the selected month. For the current month, pass the business-local date known to the host. If no month is supplied, this date also determines the month. For a future month, omit it or use that month's first day.
- `unavailable`: exclusions by recurring weekdays, specific dates, or both. Days and dates in one rule are combined with OR. Multiple rules are also combined with OR.
- `days`: integers `0` through `6`, Monday through Sunday.
- `dates`: valid ISO dates. They remain date-specific when reusing the team next month.
- `start`, `end`: optional 24-hour `HH:MM` strings; defaults are `00:00` and `23:59`. `all` uses the corresponding default. The end must be later than the start. Any overlap blocks the entire fixed shift; touching endpoints do not overlap.

To express "John cannot do Tuesday evenings", use `{"days": [1]}`. To block only the late weekend shift, use `{"days": [5, 6], "start": "15:30", "end": "23:00"}`.

Positive assignments are constraints. For "Frank and Jane cover weekends, everyone else weekdays", exclude weekdays for Frank and Jane and weekends for everyone else. To reserve a particular fixed shift for one person, block that shift for all other people. Keep any existing exclusions. If the designated person is unavailable, the shift stays `UNFILLED`; do not override the restriction. Clarify instructions that conflict or do not identify a unique team member.

The engine constructs every fixed shift from `start_date` through the end of the selected month before assigning anyone. It builds an employee-by-shift eligibility matrix and calculates distinct-day, weekday and weekend capacities. A person can cover at most one shift per date.

OR-Tools CP-SAT solves the complete remaining period using sequential exact integer objectives:

1. Minimize UNFILLED shifts.
2. Minimize the maximum minus minimum total shift count across **all** named staff, then the sum of absolute deviations from the equal share. The latter is represented exactly as `sum(abs(n * total[e] - covered_shifts))`.
3. Preserve those optima and minimize weekend count range among staff eligible for at least one remaining weekend shift, then their aggregate deviation from the assigned weekend share.
4. Preserve all prior optima and minimize early/late count imbalance, consecutive working days and the busiest week, in that order. The final pass minimizes the maximum number of shifts assigned to any employee within one calendar week. Partial weeks include only remaining dates.

After each pass the optimum value is fixed, but individual assignments remain movable. This protects scarce opportunities without permanently assigning restricted employees first. Necessary weekend work for a constrained employee takes precedence over equal weekend duties. Total fairness is measured in shifts, not hours; existing hour summaries remain available.

Every pass must return `OPTIMAL`. A single worker and fixed seed make results reproducible with the pinned solver. Each pass has a 60-second limit. A merely feasible or timed-out result raises `OptimizationError`; the CLI does not create a new PDF. Mathematically valid analytic lower bounds and ordering of interchangeable staff speed up proofs without changing the objective hierarchy.

Colours follow the supplied staff order and remain consistent when that order is reused. Duplicate first names normally use surname initials. If those initials also collide, calendar labels use full names. Long calendar labels can be shortened with an ellipsis; the flat shift list carries the full name. If an exceptionally long full name cannot fit at the minimum readable size, PDF generation raises a clear error instead of silently truncating it. Ask for a shorter display name only in that case.

The CLI prints the month, scheduled shift count and gaps. It writes only `rota.pdf`. Python callers can use `generate(data, today=...)` to inspect the in-memory assignments, summary, colours and gaps, followed by `render_pdf(result, destination)`.
