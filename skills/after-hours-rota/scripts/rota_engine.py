#!/usr/bin/env python3
"""ClientLab calendar-month after-hours lead response rota.

One calendar month per US Letter landscape page, with a fixed 41-row shift list,
colour-matched calendar assignments, and a branded promotional header.
No external API calls. Accepts {"staff": [...]}, optionally month/year or
month "YYYY-MM"; defaults to the current calendar month. For the current
month, assignments begin on the day the rota is generated; earlier dates
remain visible but unassigned in the calendar, while the left shift list still
shows date/time placeholders from the 1st.
"""
import argparse
import base64
import calendar
import colorsys
import html
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

VERSION = '1.1.2'
SOLVER_TIME_LIMIT_SECONDS = 60.0

ASSETS = Path(__file__).resolve().parents[1] / 'assets'

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
SHIFTS = {
    **{d: [('16:30', '23:00')] for d in range(5)},
    5: [('08:00', '15:30'), ('15:30', '23:00')],
    6: [('08:00', '15:30'), ('15:30', '23:00')],
}
CTA = "Scan The QR Code To Take The FREE Remodeler's Diagnostic Assessment & Get Your 7 Business Performance Scores"


def minutes(t):
    h, m = map(int, t.split(':'))
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError('Bad HH:MM: ' + t)
    return h * 60 + m


def person_colors(names):
    colors = {}
    for i, name in enumerate(names):
        hue = ((i * 0.61803398875) + 0.32) % 1
        rgb = colorsys.hls_to_rgb(hue, .84, .45)
        colors[name] = '#' + ''.join(f'{int(x * 255):02X}' for x in rgb)
    return colors


def parse_month(data, today=None):
    today = today or date.today()
    value = data.get('month')
    if isinstance(value, str) and len(value) == 7 and value[4] == '-':
        yyyy, mm = map(int, value.split('-'))
    else:
        yyyy = int(data.get('year', today.year))
        mm = int(value) if value is not None else today.month
    if not (1 <= mm <= 12 and 1 <= yyyy <= 9999):
        raise ValueError('Invalid month/year')
    return yyyy, mm


def blocked(person, day, begin, finish):
    for item in person.get('unavailable', []):
        recurring = [int(x) for x in item.get('days', [])]
        dates = item.get('dates', [])
        if day.weekday() not in recurring and day.isoformat() not in dates:
            continue
        a, b = item.get('start', '00:00'), item.get('end', '23:59')
        a = '00:00' if a == 'all' else a
        b = '23:59' if b == 'all' else b
        if minutes(a) >= minutes(b):
            raise ValueError('Unavailable time range must end later than it starts')
        if minutes(begin) < minutes(b) and minutes(a) < minutes(finish):
            return True
    return False


def name_parts(full_name):
    parts = [p for p in str(full_name).strip().split() if p]
    if not parts:
        return '', ''
    first = parts[0]
    surname = parts[-1] if len(parts) > 1 else ''
    return first, surname


def display_names(names):
    firsts = [name_parts(n)[0] for n in names]
    counts = Counter(f.casefold() for f in firsts if f)
    calendar_names = {}
    list_names = {}
    for full in names:
        first, surname = name_parts(full)
        if counts[first.casefold()] > 1 and surname:
            cal = f'{first} {surname[0].upper()}.'
        elif counts[first.casefold()] > 1:
            cal = full
        else:
            cal = first or full
        calendar_names[full] = cal
        list_names[full] = full
    # Same surname initials need a longer label to identify the person.
    labels = Counter(label.casefold() for label in calendar_names.values())
    for full, label in list(calendar_names.items()):
        if labels[label.casefold()] > 1:
            calendar_names[full] = full
    return calendar_names, list_names


def fixed_shift_label(weekday, shift_index):
    if weekday < 5:
        return '4:30-11'
    return '8-3:30' if shift_index == 0 else '3:30-11'


def fit_text(text, max_chars):
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    return text[:max_chars - 1] + '…'


class OptimizationError(RuntimeError):
    """No proven optimal schedule was obtained; do not deliver a heuristic."""


def analyze_period(staff, period):
    """Eligibility and attainable capacities for only the remaining dates.

    Weekend capacity counts distinct days, since a person cannot cover both
    shifts on one date. These capacities inform variable domains; the global
    constraints resolve competition for scarce opportunities.
    """
    eligibility = [[not blocked(p, date.fromisoformat(s['date']), s['start'], s['end'])
                    for s in period] for p in staff]
    weekend = [i for i, s in enumerate(period) if s['weekday'] >= 5]
    days = {s['date'] for s in period}
    n = len(staff)
    capacities = []
    for flags in eligibility:
        available = [s for s, yes in zip(period, flags) if yes]
        weekdays = sum(s['weekday'] < 5 for s in available)
        weekends = len({s['date'] for s in available if s['weekday'] >= 5})
        capacities.append({'eligible_shifts': len(available),
                           'distinct_days': len({s['date'] for s in available}),
                           'weekday_capacity': weekdays, 'weekend_capacity': weekends,
                           'minimum_weekends_for_floor_target': max(0, len(period)//n-weekdays)})
    eligible_weekend_staff = [e for e in range(n) if any(eligibility[e][i] for i in weekend)]
    return {'eligibility': eligibility, 'capacities': capacities,
            'remaining_days': len(days), 'remaining_weekdays': len(period)-len(weekend),
            'remaining_saturdays': len({s['date'] for s in period if s['weekday'] == 5}),
            'remaining_sundays': len({s['date'] for s in period if s['weekday'] == 6}),
            'weekday_shifts': len(period)-len(weekend),
            'weekend_days': len({period[i]['date'] for i in weekend}),
            'weekend_shifts': len(weekend), 'remaining_shifts': len(period),
            'staff_count': n, 'ideal_shifts': len(period)/n,
            'weekend_eligible_staff': eligible_weekend_staff,
            'ideal_weekend_shifts': len(weekend)/len(eligible_weekend_staff) if eligible_weekend_staff else 0}


def _solve_optimal(model, objective, label):
    from ortools.sat.python import cp_model
    model.minimize(objective)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    status = solver.solve(model)
    if status != cp_model.OPTIMAL:
        raise OptimizationError(f'{label}: solver returned {solver.status_name(status)}; '
                                'a global optimum was not proven. No PDF was generated.')
    value = solver.value(objective) if not isinstance(objective, int) else objective
    model.add(objective == value)
    # A hint accelerates the next pass without fixing individual assignments.
    model.clear_hints()
    for i in range(len(model.proto.variables)):
        var = model.get_int_var_from_proto_index(i)
        model.add_hint(var, solver.value(var))
    return solver, value


def _protect_equal_share_if_feasible(model, totals, covered):
    """Prove the floor/ceiling allocation feasible before hinting later passes.

    This is a global feasibility solve, not a locked assignment pass. If equal
    shares are impossible, the unconstrained range objective still finds and
    proves the closest achievable totals. It avoids unlucky improving-solution
    search on unrestricted teams where the mathematical lower bound is known.
    """
    from ortools.sat.python import cp_model
    q, r = divmod(covered, len(totals))
    trial = model.clone()
    trial.clear_objective(); trial.clear_hints()
    for total in totals:
        var = trial.get_int_var_from_proto_index(total.index)
        trial.add(var >= q); trial.add(var <= q+int(bool(r)))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    status = solver.solve(trial)
    if status == cp_model.INFEASIBLE:
        return
    if status != cp_model.OPTIMAL:
        raise OptimizationError('Equal-share feasibility: a global optimum was not proven. No PDF was generated.')
    for total in totals:
        model.add(total >= q); model.add(total <= q+int(bool(r)))
    model.clear_hints()
    for i in range(len(model.proto.variables)):
        var = model.get_int_var_from_proto_index(i)
        model.add_hint(var, solver.value(trial.get_int_var_from_proto_index(i)))


def optimize_period(staff, period):
    """Exact lexicographic CP-SAT model, returning choices and proof metadata.

    Every pass fixes its proven objective value, never its assignments. Later
    passes may rearrange all dates while preserving every higher priority.
    """
    from ortools.sat.python import cp_model
    analysis = analyze_period(staff, period)
    model = cp_model.CpModel()
    n, k = len(staff), len(period)
    x = {(e, i): model.new_bool_var(f'x_{e}_{i}')
         for e in range(n) for i in range(k) if analysis['eligibility'][e][i]}
    gaps = [model.new_bool_var(f'gap_{i}') for i in range(k)]
    by_date = defaultdict(list)
    for i, sl in enumerate(period):
        by_date[sl['date']].append(i)
        model.add(sum(x[e, i] for e in range(n) if (e, i) in x) + gaps[i] == 1)
    daily = {}
    for e in range(n):
        for day, indices in by_date.items():
            worked = model.new_bool_var(f'day_{e}_{day}')
            model.add(sum(x[e, i] for i in indices if (e, i) in x) == worked)
            daily[e, day] = worked

    totals, weekends, positions = [], [], []
    for e in range(n):
        total = model.new_int_var(0, analysis['capacities'][e]['distinct_days'], f'total_{e}')
        weekend = model.new_int_var(0, analysis['capacities'][e]['weekend_capacity'], f'weekend_{e}')
        model.add(total == sum(v for (person, i), v in x.items() if person == e))
        model.add(weekend == sum(v for (person, i), v in x.items() if person == e and period[i]['weekday'] >= 5))
        totals.append(total); weekends.append(weekend)
        early = sum(v for (person, i), v in x.items() if person == e and period[i]['weekday'] >= 5 and period[i]['shift'] == 0)
        late = sum(v for (person, i), v in x.items() if person == e and period[i]['weekday'] >= 5 and period[i]['shift'] == 1)
        imbalance = model.new_int_var(0, k, f'position_{e}')
        model.add_abs_equality(imbalance, early-late)
        positions.append(imbalance)

    # Interchangeable employees can be ordered without losing any objective
    # optimum. This removes equivalent permutations of named schedules.
    groups = defaultdict(list)
    for e, flags in enumerate(analysis['eligibility']):
        groups[tuple(flags)].append(e)
    for group in groups.values():
        for a, b in zip(group, group[1:]):
            model.add(totals[a] >= totals[b])
            equal_totals = model.new_bool_var(f'equal_totals_{a}_{b}')
            model.add(totals[a] == totals[b]).only_enforce_if(equal_totals)
            model.add(totals[a] != totals[b]).only_enforce_if(equal_totals.Not())
            model.add(weekends[a] >= weekends[b]).only_enforce_if(equal_totals)

    def spread(values, bound, prefix):
        if not values:
            return 0
        low = model.new_int_var(0, bound, prefix+'_min')
        high = model.new_int_var(0, bound, prefix+'_max')
        model.add_min_equality(low, values); model.add_max_equality(high, values)
        return high-low

    def deviation(values, count, prefix):
        terms = []
        for i, value in enumerate(values):
            term = model.new_int_var(0, n*k, f'{prefix}_{i}')
            model.add_abs_equality(term, len(values)*value-count)
            terms.append(term)
        return sum(terms)

    covered = k-sum(gaps)
    total_range = spread(totals, k, 'total')
    total_deviation = deviation(totals, covered, 'total_deviation')
    candidates = analysis['weekend_eligible_staff']
    weekend_values = [weekends[e] for e in candidates]
    weekend_range = spread(weekend_values, k, 'weekend')
    weekend_deviation = deviation(weekend_values, sum(weekend_values), 'weekend_deviation')

    consecutive = []
    consecutive_by_date = defaultdict(list)
    for e in range(n):
        for day in by_date:
            next_day = (date.fromisoformat(day)+timedelta(days=1)).isoformat()
            if next_day in by_date:
                pair = model.new_bool_var(f'consecutive_{e}_{day}')
                model.add(pair >= daily[e, day]+daily[e, next_day]-1)
                model.add(pair <= daily[e, day])
                model.add(pair <= daily[e, next_day])
                consecutive.append(pair)
                consecutive_by_date[day].append(pair)
    # A pair of dates needing more workers than their eligible union
    # necessarily repeats someone. This redundant bound proves unavoidable
    # consecutive-day counts quickly without changing any legal schedule.
    for day in by_date:
        next_day = (date.fromisoformat(day)+timedelta(days=1)).isoformat()
        if next_day in by_date:
            union = [e for e in range(n) if any((e, i) in x for i in by_date[day]+by_date[next_day])]
            model.add(sum(consecutive_by_date[day]) >= sum(daily[e, day]+daily[e, next_day] for e in union)-len(union))
    # Minimize the busiest employee-week after the preceding priorities.
    # The weekly pigeonhole bound ceil(covered/M) is exact as a lower bound,
    # even when restrictions require a higher optimal maximum.
    weeks = defaultdict(list)
    for day in by_date:
        dt = date.fromisoformat(day)
        weeks[dt-timedelta(days=dt.weekday())].append(day)
    weekly_loads, weekly_bounds = [], []
    for monday, days in weeks.items():
        active = [e for e in range(n) if any((e, i) in x and period[i]['date'] in days for i in range(k))]
        for e in active:
            load = model.new_int_var(0, len(days), f'weekly_{e}_{monday}')
            model.add(load == sum(daily[e, day] for day in days))
            weekly_loads.append(load)
        capacity = sum(sl['date'] in days for sl in period)
        if active:
            count = model.new_int_var(0, capacity, f'weekly_count_{monday}')
            model.add(count == capacity-sum(gaps[i] for i, sl in enumerate(period) if sl['date'] in days))
            bounds = [(c+len(active)-1)//len(active) for c in range(capacity+1)]
            bound = model.new_int_var(0, max(bounds), f'weekly_bound_{monday}')
            model.add_element(count, bounds, bound)
            weekly_bounds.append(bound)
    busiest_week = model.new_int_var(0, 7, 'busiest_week')
    model.add_max_equality(busiest_week, weekly_loads or [0])
    for bound in weekly_bounds:
        model.add(busiest_week >= bound)

    objectives = [('unfilled', sum(gaps)), ('total_range', total_range),
                  ('total_deviation', total_deviation), ('weekend_range', weekend_range),
                  ('weekend_deviation', weekend_deviation),
                  ('early_late_imbalance', sum(positions)),
                  ('consecutive_days', sum(consecutive)),
                  ('busiest_week', busiest_week)]
    model.add(sum(totals) == covered)
    proof = {}
    for label, objective in objectives:
        solver, optimum = _solve_optimal(model, objective, label)
        proof[label] = optimum
        if label == 'unfilled':
            c = k-optimum
            remainder = c % n
            model.add(total_range >= int(bool(remainder)))
            model.add(total_deviation >= 2*remainder*(n-remainder))
            _protect_equal_share_if_feasible(model, totals, c)
            if optimum == 0 and candidates:
                remainder = analysis['weekend_shifts'] % len(candidates)
                model.add(weekend_range >= int(bool(remainder)))
                model.add(weekend_deviation >= 2*remainder*(len(candidates)-remainder))
        if label == 'weekend_range' and optimum <= 1 and proof['unfilled'] == 0 and candidates:
            q, remainder = divmod(analysis['weekend_shifts'], len(candidates))
            odd = len(candidates)-remainder if q % 2 else remainder
            model.add(sum(positions) >= odd)
    chosen = [next((e for e in range(n) if (e, i) in x and solver.value(x[e, i])), None) for i in range(k)]
    return chosen, {'status': 'OPTIMAL', 'objectives': proof, 'analysis': analysis}


def generate(data, today=None):
    # A supplied business-local start date also resolves the default month.
    today = today or (date.fromisoformat(data['start_date']) if 'start_date' in data else date.today())
    year, month = parse_month(data, today)
    if 'start_date' in data:
        starts_on = date.fromisoformat(data['start_date'])
    else:
        starts_on = date(year, month, 1) if (year, month) != (today.year, today.month) else today
    if starts_on.year != year or starts_on.month != month:
        raise ValueError('start_date must be inside the selected month')

    raw_staff = data.get('staff', [])
    if not isinstance(raw_staff, list):
        raise ValueError('staff must be a list')
    staff = []
    for entry in raw_staff:
        if isinstance(entry, str):
            staff.append({'name': entry.strip(), 'unavailable': []})
        elif isinstance(entry, dict) and isinstance(entry.get('name'), str):
            staff.append({'name': entry['name'].strip(), 'unavailable': entry.get('unavailable', [])})
        else:
            raise ValueError('Each team member needs a name')
    names = [x['name'] for x in staff]
    if any(not n or n.casefold() == 'unfilled' for n in names):
        raise ValueError('Staff names must be nonblank and cannot be UNFILLED')
    for person in staff:
        rules = person['unavailable']
        if not isinstance(rules, list):
            raise ValueError('unavailable must be a list')
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError('Each exclusion must be an object')
            days, dates = rule.get('days', []), rule.get('dates', [])
            if not isinstance(days, list) or any(type(d) is not int or not 0 <= d <= 6 for d in days):
                raise ValueError('Exclusion days must be integers 0 (Monday) through 6 (Sunday)')
            if not isinstance(dates, list):
                raise ValueError('Exclusion dates must be a list of YYYY-MM-DD strings')
            for value in dates:
                if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                    raise ValueError('Exclusion dates must use YYYY-MM-DD')
            a, b = rule.get('start', '00:00'), rule.get('end', '23:59')
            if minutes('00:00' if a == 'all' else a) >= minutes('23:59' if b == 'all' else b):
                raise ValueError('Unavailable time range must end later than it starts')
    if len(names) != len(set(n.casefold() for n in names)):
        raise ValueError('Staff names must be unique')
    if not names:
        raise ValueError('Provide at least one team member')
    cal_labels, list_labels = display_names(names)

    month_days = calendar.monthrange(year, month)[1]
    cal = calendar.Calendar(firstweekday=0)
    month_grid = cal.monthdatescalendar(year, month)

    period = []
    for day_number in range(starts_on.day, month_days + 1):
        dt = date(year, month, day_number)
        for shift_index, (start, end) in enumerate(SHIFTS[dt.weekday()]):
            period.append({'date': dt.isoformat(), 'weekday': dt.weekday(),
                           'start': start, 'end': end, 'shift': shift_index})

    choices, _ = optimize_period(staff, period)
    totals = [0] * len(staff)
    weekends = [0] * len(staff)
    slots = []
    for sl, chosen in zip(period, choices):
        name = 'UNFILLED' if chosen is None else names[chosen]
        if chosen is not None:
            duration = minutes(sl['end']) - minutes(sl['start'])
            totals[chosen] += duration
            if sl['weekday'] >= 5:
                weekends[chosen] += duration
        slots.append({**sl, 'person': name,
                      'calendar_name': 'UNFILLED' if chosen is None else cal_labels[name],
                      'list_name': 'UNFILLED' if chosen is None else list_labels[name],
                      'time_label': fixed_shift_label(sl['weekday'], sl['shift'])})

    colors = person_colors(names)
    gaps = [x for x in slots if x['person'] == 'UNFILLED']

    shift_list_days = []
    slots_by_date = defaultdict(list)
    for sl in slots:
        slots_by_date[sl['date']].append(sl)

    for day_number in range(1, 32):
        if day_number > month_days:
            shift_list_days.append({'day': day_number, 'date': None, 'weekday': None, 'slots': []})
            continue
        dt = date(year, month, day_number)
        weekday = dt.weekday()
        if day_number < starts_on.day:
            day_slots = []
            for shift_index, (start, end) in enumerate(SHIFTS[weekday]):
                day_slots.append({
                    'date': dt.isoformat(),
                    'weekday': weekday,
                    'start': start,
                    'end': end,
                    'shift': shift_index,
                    'person': '',
                    'calendar_name': '',
                    'list_name': '',
                    'time_label': fixed_shift_label(weekday, shift_index),
                })
        else:
            day_slots = sorted(slots_by_date.get(dt.isoformat(), []), key=lambda x: x['shift'])
        shift_list_days.append({'day': day_number, 'date': dt.isoformat(), 'weekday': weekday, 'slots': day_slots})

    return {
        'title': f'After-Hours Lead Response Rota {calendar.month_name[month]} {year}',
        'year': year,
        'month': month,
        'month_label': f'{calendar.month_name[month]} {year}',
        'first_date': f'{year:04d}-{month:02d}-01',
        'starts_on': starts_on.isoformat(),
        'slots': slots,
        'week_rows': [[d.isoformat() if d.month == month else None for d in week] for week in month_grid],
        'colors': colors,
        'staff_order': names,
        'calendar_names': cal_labels,
        'list_names': list_labels,
        'shift_list_days': shift_list_days,
        'staff': {names[j]: {'total_hours': round(totals[j] / 60, 1), 'weekend_hours': round(weekends[j] / 60, 1), 'shifts': sum(s['person'] == names[j] for s in slots)} for j in range(len(names))},
        'gaps': len(gaps),
        'unfilled': gaps,
        'schedule_rules': {'weekday': ['16:30', '23:00'], 'weekend_early': ['08:00', '15:30'], 'weekend_late': ['15:30', '23:00']},
    }


def _asset_uri(name):
    path = ASSETS / name
    mime = 'image/png' if path.suffix.lower() == '.png' else 'image/webp'
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


def flat_shift_rows(res):
    """Chronological flat shift-list rows, including empty pre-start entries.

    At most 41 shifts can occur in any 31-day calendar month:
    31 weekdays/weekend days plus one additional shift for each of up to
    ten weekend days. The display always reserves this capacity.
    """
    flat = [sl for day in res['shift_list_days'] for sl in day['slots']]
    assert len(flat) <= 41, 'Monthly flat list exceeds its 41-row capacity'
    return flat


def list_shift_time(sl):
    return ('4:30-11p' if sl['weekday'] < 5 else
            ('8-3:30p' if sl['shift'] == 0 else '3:30-11p'))


def render_html(res):
    banner = ASSETS / 'header.png'
    header_html = f'<img class="combined-header" src="{_asset_uri("header.png")}" alt="ClientLab free diagnostic and QR code">' if banner.exists() else ''
    colors = res['colors']
    indexed = defaultdict(list)
    for sl in res['slots']:
        indexed[sl['date']].append(sl)

    # Flat rows: one date/name/time line for each shift (weekends have two).
    # Past dates retain white lines with date/time and an empty name.
    shift_rows = []
    for sl in flat_shift_rows(res):
        day = date.fromisoformat(sl['date'])
        name = sl['person']
        bg = colors.get(name, '#FFFFFF') if name and name != 'UNFILLED' else ('#FDE7E2' if name == 'UNFILLED' else '#FFFFFF')
        label = html.escape(sl.get('list_name', ''))
        shift_rows.append(
            f'<div class="shift-line" style="background:{bg}">'
            f'<span class="date-label">{day:%d %a}</span>'
            f'<strong class="person-label">{label}</strong>'
            f'<span class="time-label">{list_shift_time(sl)}</span></div>'
        )
    # Same row height for every month, regardless of the number of shifts.
    shift_rows.extend('<div class="shift-line blank"></div>' for _ in range(41-len(shift_rows)))

    calendar_rows = []
    for week in res['week_rows']:
        tds = []
        for day_str in week:
            if day_str is None:
                tds.append('<td class="outside"></td>')
                continue
            d = date.fromisoformat(day_str)
            weekday_class = 'weekend' if d.weekday() >= 5 else 'weekday'
            past = day_str < res['starts_on']
            cell_slots = sorted(indexed.get(day_str, []), key=lambda x: x['shift'])
            boxes = []
            if not past:
                for sl in cell_slots:
                    bg = colors.get(sl['person'], '#FDE7E2') if sl['person'] != 'UNFILLED' else '#FDE7E2'
                    extra = ' unfilled' if sl['person'] == 'UNFILLED' else ''
                    boxes.append(
                        f'<div class="day-slot {weekday_class}{extra}" style="background:{bg}">' \
                        f'<span class="time">{html.escape(sl["time_label"])}</span>' \
                        f'<span class="name">{html.escape(sl["calendar_name"] or "")}</span></div>'
                    )
            past_class = 'past' if past else ''
            tds.append(
                f'<td class="{past_class}"><div class="day-num">{d.day}</div>'
                f'<div class="day-slot-wrap {weekday_class}">{"".join(boxes)}</div></td>'
            )
        calendar_rows.append('<tr>' + ''.join(tds) + '</tr>')

    note = f'<p class="warning">WARNING: {res["gaps"]} UNFILLED shift(s). Confirm coverage before using.</p>' if res['gaps'] else ''
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#eef2f3;font-family:Arial,sans-serif;color:#1a2722}}
.toolbar{{text-align:center;padding:10px;background:#10211d}} button{{background:white;border:0;border-radius:4px;padding:8px 18px;cursor:pointer}}
.page{{width:11in;height:8.5in;background:#fff;margin:16px auto;padding:.5in;overflow:hidden}}
.header-wrap{{height:1.42in;padding:0 0 12px 0}} .combined-header{{display:block;width:10in;height:1.25in;object-fit:fill}}
.title{{font-family:'Space Grotesk',Arial,sans-serif;font-size:22px;font-weight:700;letter-spacing:-.5px;line-height:1.05;margin:0 0 10px 0;white-space:nowrap}}
.layout{{height:5.55in;display:grid;grid-template-columns:2.28in 1fr;gap:.12in}}
.sidebar{{border:1px solid #b6c8c1;display:flex;flex-direction:column;overflow:hidden}} .sidebar h2{{font-size:13px;line-height:1;margin:0;padding:6px 0;text-align:center;background:#eff4f2;border-bottom:1px solid #d3ddd8}}
.rows41{{display:grid;grid-template-rows:repeat(41,minmax(0,1fr));height:100%;min-height:0}}
.shift-line{{min-height:0;display:grid;grid-template-columns:38px minmax(0,1fr) 46px;align-items:center;gap:2px;padding:0 3px;border-bottom:1px solid #f2f4f3;font-size:8.2px;line-height:1}}
.shift-line .date-label{{font-size:7.2px;white-space:nowrap}}
.shift-line .person-label{{font-size:7.8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.shift-line .time-label{{font-size:7px;text-align:right;white-space:nowrap}}
.shift-line.blank{{background:white}}
.calendar{{border-collapse:collapse;width:100%;height:100%;table-layout:fixed}} .calendar thead th{{height:.27in;font-size:10px;background:#eef4f1;border:1px solid #b7c9c2}} .calendar td{{border:1px solid #b7c9c2;vertical-align:top;padding:2px 2px 3px 2px}} .calendar td.outside{{background:#f5f7f7}} .calendar td.past{{background:#fafbfb}}
.day-num{{text-align:right;font-size:10px;font-weight:700;line-height:1;padding:0 2px 3px 0}} .day-slot-wrap{{height:calc(100% - 13px);min-height:0;display:flex;flex-direction:column;gap:3px}} .day-slot-wrap.weekday{{justify-content:center}} .day-slot{{border-radius:3px;border:1px solid #dfe8e4;padding:2px 3px;display:flex;flex-direction:column;justify-content:center;align-items:center;line-height:1;min-height:0}} .day-slot.weekday,.day-slot.weekend{{width:100%;height:calc((100% - 3px)/2);flex-shrink:0}} .day-slot .time{{font-size:7px;color:#31423b}} .day-slot .name{{font-size:10px;font-weight:700;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}} .day-slot.unfilled{{background:#fde7e2 !important}}
footer{{font-size:9px;display:flex;justify-content:space-between;margin-top:10px;border-top:1px solid #d9e0dc;padding-top:7px}} .warning{{color:#a00;text-align:center;font-weight:bold;margin:0 0 8px}}
@page{{size:letter landscape;margin:0}} @media print{{body{{background:white}} .toolbar{{display:none}} .page{{margin:0}}}}
</style></head><body><div class="toolbar"><button onclick="window.print()">Print or Save as PDF</button></div>{note}
<section class="page"><div class="header-wrap">{header_html}</div><h1 class="title">{html.escape(res['title'])}</h1><div class="layout"><aside class="sidebar"><h2>Shift List</h2><div class="rows41">{''.join(shift_rows)}</div></aside><table class="calendar"><thead><tr>{''.join('<th>' + d[:3] + '</th>' for d in DAYS)}</tr></thead><tbody>{''.join(calendar_rows)}</tbody></table></div><footer><b>Response target: within 60 minutes during covered hours.</b><span>clientlab.io</span></footer></section></body></html>'''


def render_pdf(res, dest):
    from PIL import Image
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    banner = ASSETS / 'header.png'
    if not banner.is_file():
        raise ValueError('Required ClientLab header asset is missing')
    for name in res['staff_order']:
        if pdfmetrics.stringWidth(name, 'Helvetica-Bold', 5.4) > 310 - 96:
            raise ValueError(f'Name is too long for the one-page shift list: {name}. Use a shorter display name.')
    pw, ph = landscape(letter)
    c = canvas.Canvas(str(dest), pagesize=(pw, ph), invariant=1)
    c.setTitle(res['title'])
    assets = ASSETS
    ink = HexColor('#182822')
    muted = HexColor('#51645a')
    line = HexColor('#c8d8d1')
    light = HexColor('#eff4f2')
    empty_line = HexColor('#e7eeeb')

    title_font = 'Helvetica-Bold'
    font_candidates = [assets / 'SpaceGrotesk-Bold.ttf', Path('/usr/local/share/fonts/SpaceGrotesk-Bold.ttf')]
    for path in font_candidates:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont('SpaceGroteskClientLab', str(path)))
                title_font = 'SpaceGroteskClientLab'
                break
            except Exception:
                pass

    margin = 36
    header_area_h = 100
    header_y = ph - margin - header_area_h
    banner = assets / 'header.png'
    c.setFillColor(HexColor('#ffffff'))
    c.rect(margin, header_y, pw - margin * 2, header_area_h, stroke=0, fill=1)
    if banner.exists():
        img = ImageReader(Image.open(banner))
        c.drawImage(img, margin, header_y + 8, pw - margin * 2, 90, mask='auto')

    title = res['title']
    fs = 19.5
    while fs > 15 and pdfmetrics.stringWidth(title, title_font, fs) > (pw - margin * 2):
        fs -= 0.25
    c.setFillColor(ink)
    c.setFont(title_font, fs)
    title_y = header_y - 24
    c.drawString(margin, title_y, title)

    content_top = title_y - 10
    content_bottom = 44
    body_h = content_top - content_bottom

    sidebar_x = margin
    # Keep the original width for ordinary names. Longer full names get
    # only the extra width they need, preserving the flat 41-row design.
    longest = max(pdfmetrics.stringWidth(n, 'Helvetica-Bold', 6.85) for n in res['staff_order'])
    sidebar_w = min(310, max(182, longest + 96))
    gap = 12
    cal_x = sidebar_x + sidebar_w + gap
    cal_w = pw - margin - cal_x

    c.setStrokeColor(line)
    c.setLineWidth(0.8)
    c.rect(sidebar_x, content_bottom, sidebar_w, body_h, stroke=1, fill=0)
    side_head_h = 18
    c.setFillColor(light)
    c.rect(sidebar_x, content_top - side_head_h, sidebar_w, side_head_h, stroke=0, fill=1)
    c.setFillColor(ink)
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(sidebar_x + sidebar_w / 2, content_top - 12.5, 'Shift List')
    side_rows_top = content_top - side_head_h
    # Reserve exactly 41 flat rows (worst-case 31-day month with 10
    # Saturday/Sunday dates). Preserve old design: date | name | time.
    row_h = (side_rows_top - content_bottom) / 41.0
    for i, sl in enumerate(flat_shift_rows(res)):
        y = side_rows_top - (i+1)*row_h
        name = sl['person']
        bg = res['colors'].get(name, '#FFFFFF') if name and name != 'UNFILLED' else ('#FDE7E2' if name == 'UNFILLED' else '#FFFFFF')
        c.setFillColor(HexColor(bg))
        c.rect(sidebar_x+1,y+0.18,sidebar_w-2,row_h-0.35,fill=1,stroke=0)
        dt = date.fromisoformat(sl['date'])
        baseline = y + (row_h-6.7)/2 + 1.1
        c.setFillColor(ink)
        c.setFont('Helvetica',6.7)
        c.drawString(sidebar_x+4,baseline,dt.strftime('%d %a'))
        full_name = sl.get('list_name','')
        if full_name:
            font_size=6.85
            max_name_width=sidebar_w-38-49-9
            while font_size>5.4 and pdfmetrics.stringWidth(full_name,'Helvetica-Bold',font_size)>max_name_width:
                font_size=max(5.4, font_size-0.2)
            c.setFont('Helvetica-Bold',font_size)
            c.setFillColor(HexColor('#9E1C1C') if name=='UNFILLED' else ink)
            c.drawString(sidebar_x+40,baseline,full_name)
        c.setFillColor(muted)
        c.setFont('Helvetica',6.5)
        c.drawRightString(sidebar_x+sidebar_w-4,baseline,list_shift_time(sl))
    # Unused rows at the bottom are deliberately left white, with unchanged
    # row height for shorter months.

    c.setStrokeColor(line)
    c.setLineWidth(0.8)
    c.rect(cal_x, content_bottom, cal_w, body_h, stroke=1, fill=0)
    head_h = 19
    c.setFillColor(light)
    c.rect(cal_x, content_top - head_h, cal_w, head_h, stroke=0, fill=1)
    cellw = cal_w / 7.0
    c.setFillColor(ink)
    c.setFont('Helvetica-Bold', 9)
    for j, day_name in enumerate(DAYS):
        c.drawCentredString(cal_x + (j + 0.5) * cellw, content_top - 12.5, day_name[:3])

    weeks = res['week_rows']
    grid_top = content_top - head_h
    cellh = (grid_top - content_bottom) / len(weeks)
    lookup = defaultdict(list)
    for sl in res['slots']:
        lookup[sl['date']].append(sl)

    for row_i, week in enumerate(weeks):
        y = grid_top - (row_i + 1) * cellh
        for col_i, day_str in enumerate(week):
            x = cal_x + col_i * cellw
            if day_str is None:
                c.setFillColor(HexColor('#f5f7f7'))
                c.rect(x, y, cellw, cellh, stroke=0, fill=1)
                continue
            past = day_str < res['starts_on']
            if past:
                c.setFillColor(HexColor('#fafbfb'))
                c.rect(x, y, cellw, cellh, stroke=0, fill=1)
            d = date.fromisoformat(day_str)
            c.setFillColor(muted if past else ink)
            c.setFont('Helvetica-Bold', 8.5)
            c.drawRightString(x + cellw - 4, y + cellh - 10, str(d.day))
            if past:
                continue
            day_slots = sorted(lookup.get(day_str, []), key=lambda s: s['shift'])
            top_pad = 3
            bottom_pad = 3
            date_band = 12
            avail_top = y + cellh - date_band - top_pad
            avail_bottom = y + bottom_pad
            slot_gap = 3
            box_h = max(12, (avail_top - avail_bottom - slot_gap) / 2)
            box_w = cellw - 4
            ys = [avail_bottom + box_h + slot_gap, avail_bottom] if d.weekday() >= 5 else [avail_bottom + ((avail_top - avail_bottom) - box_h) / 2]
            for i, sl in enumerate(day_slots):
                if i >= len(ys):
                    break
                box_y = ys[i]
                bg = HexColor(res['colors'].get(sl['person'], '#FDE7E2')) if sl['person'] != 'UNFILLED' else HexColor('#FDE7E2')
                c.setFillColor(bg)
                c.setStrokeColor(empty_line)
                c.roundRect(x + 2, box_y, box_w, box_h, 2, stroke=1, fill=1)
                time_size = min(6.8, max(5.4, box_h * 0.24))
                name_size = min(8.8, max(6.4, box_h * 0.34))
                c.setFillColor(muted)
                c.setFont('Helvetica', time_size)
                c.drawCentredString(x + cellw / 2, box_y + box_h * 0.60, sl['time_label'])
                c.setFillColor(ink if sl['person'] != 'UNFILLED' else HexColor('#9E1C1C'))
                name = sl['calendar_name']
                while name_size > 6.4 and pdfmetrics.stringWidth(name, 'Helvetica-Bold', name_size) > box_w - 6:
                    name_size = max(6.4, name_size - 0.2)
                if pdfmetrics.stringWidth(name, 'Helvetica-Bold', name_size) > box_w - 6:
                    while name and pdfmetrics.stringWidth(name + '…', 'Helvetica-Bold', name_size) > box_w - 6:
                        name = name[:-1]
                    name += '…'
                c.setFont('Helvetica-Bold', name_size)
                c.drawCentredString(x + cellw / 2, box_y + box_h * 0.22, name)

    c.setStrokeColor(line)
    c.setLineWidth(0.45)
    for j in range(8):
        c.line(cal_x + j * cellw, content_bottom, cal_x + j * cellw, content_top)
    c.line(cal_x, content_top - head_h, cal_x + cal_w, content_top - head_h)
    for i in range(len(weeks) + 1):
        yy = grid_top - i * cellh
        c.line(cal_x, yy, cal_x + cal_w, yy)

    c.setStrokeColor(line)
    c.line(margin, 37, pw - margin, 37)
    c.setFillColor(ink)
    c.setFont('Helvetica-Bold', 7.6)
    c.drawString(margin, 25, 'Response target: within 60 minutes during covered hours.')
    c.setFillColor(muted)
    c.setFont('Helvetica', 7.6)
    c.drawRightString(pw - margin, 25, 'clientlab.io')
    if res['gaps']:
        c.setFillColor(HexColor('#B42318'))
        c.setFont('Helvetica-Bold', 9)
        c.drawRightString(pw - margin, title_y + 1, f'{res["gaps"]} UNFILLED shift(s)')
    c.showPage()
    c.save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', nargs='?')
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--out', default='.')
    args = parser.parse_args()
    if args.input is None:
        parser.error('input is required')
    dest = Path(args.out)
    dest.mkdir(exist_ok=True, parents=True)
    res = generate(json.loads(Path(args.input).read_text()))
    # The schedule remains in memory; the user receives only a printable PDF.
    render_pdf(res, dest / 'rota.pdf')
    print(f'MONTH={res["month_label"]} SHIFTS={len(res["slots"])} GAPS={res["gaps"]} PAGES=1')
    print(f'VERSION={VERSION} OPTIMIZATION=OPTIMAL')

if __name__ == '__main__':
    main()
