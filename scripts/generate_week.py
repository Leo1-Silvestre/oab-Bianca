#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de semanas para a Tutoria OAB da Bianca.

Uso:
    python3 scripts/generate_week.py <numero_da_semana>

O que faz:
  1. Lê content/state.json (matérias, blocos, conteúdo já escrito por bloco,
     progresso/revisão espaçada acumulado).
  2. Decide, para a semana pedida, o que cada matéria estuda em cada dia da
     grade fixa (conteúdo novo e/ou revisão vencida), sem gravar nada ainda.
  3. Se algum bloco necessário ainda não tem conteúdo escrito em
     subjects.<materia>.blockContent, PARA e avisa quais blocos faltam
     escrever antes de gerar a semana (teoria + lei seca daquele bloco,
     seguindo o roteiro em subjects.<materia>.blocks).
  4. Se todo o conteúdo necessário já existe, grava o progresso atualizado
     em content/state.json, gera docs/semana-NN.html e atualiza docs/index.html.

Este script SÓ decide a grade (o que estuda quando) e SÓ renderiza HTML a
partir de conteúdo já escrito. Ele nunca inventa teoria/lei seca sozinho —
isso é sempre trabalho de leitura dos PDFs no Google Drive, feito por uma
sessão do Claude Code antes de rodar este script (ver CLAUDE.md).
"""
import copy
import datetime
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "content" / "state.json"
DOCS_DIR = ROOT / "docs"

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
WEEKDAY_LABELS = {
    "monday": "Segunda-feira",
    "tuesday": "Terça-feira",
    "wednesday": "Quarta-feira",
    "thursday": "Quinta-feira",
    "friday": "Sexta-feira",
    "saturday": "Sábado",
    "sunday": "Domingo",
}


def load_state():
    with open(STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def week_monday(state, week_num):
    start = datetime.date.fromisoformat(state["startDate"])
    return start + datetime.timedelta(days=(week_num - 1) * 7)


def esc(s):
    return html.escape(s or "", quote=False)


def interval_for(n_reviews_done, state):
    intervals = state["reviewIntervals"]
    if n_reviews_done < len(intervals):
        return intervals[n_reviews_done]
    return state["reviewFixedInterval"]


def decide_week(state, week_num, progress_store):
    """Pure-ish planning pass. Mutates `progress_store` (caller decides
    whether that's a scratch copy or the real state['progress'])."""
    subjects = state["subjects"]
    schedule = state["schedule"]
    pure_review = week_num >= state["pureReviewFromWeek"]

    plan = {"week": week_num, "days": {}, "saturday": {"mode": "consolidate", "items": []}}
    used_this_week = {slug: set() for slug in subjects}
    reviewed_this_week = set()

    for day in WEEKDAYS:
        entries = []
        for slug in schedule[day]:
            blocks = subjects[slug]["blocks"]
            prog = progress_store.setdefault(slug, {})

            due = [
                (int(bid), info)
                for bid, info in prog.items()
                if info["nextReviewWeek"] <= week_num and int(bid) not in used_this_week[slug]
            ]
            due.sort(key=lambda x: x[1]["nextReviewWeek"])

            entry = {"slug": slug, "isReview": False, "block_id": None, "review_of": None}

            new_block_id = None
            if not pure_review:
                studied_ids = {int(b) for b in prog.keys()}
                remaining = [b["id"] for b in blocks if b["id"] not in studied_ids]
                if remaining:
                    new_block_id = remaining[0]

            if new_block_id is not None:
                entry["block_id"] = new_block_id
                used_this_week[slug].add(new_block_id)
                prog[str(new_block_id)] = {
                    "firstStudiedWeek": week_num,
                    "reviews": [],
                    "nextReviewWeek": week_num + state["reviewIntervals"][0],
                }
                if due:
                    rb_id, rb_info = due[0]
                    entry["review_of"] = rb_id
                    used_this_week[slug].add(rb_id)
                    n_done = len(rb_info["reviews"])
                    rb_info["reviews"].append(week_num)
                    rb_info["nextReviewWeek"] = week_num + interval_for(n_done, state)
                    reviewed_this_week.add((slug, rb_id))
            elif due:
                rb_id, rb_info = due[0]
                entry["block_id"] = rb_id
                entry["isReview"] = True
                used_this_week[slug].add(rb_id)
                n_done = len(rb_info["reviews"])
                rb_info["reviews"].append(week_num)
                rb_info["nextReviewWeek"] = week_num + interval_for(n_done, state)
                reviewed_this_week.add((slug, rb_id))

            entries.append(entry)
        plan["days"][day] = entries

    # Sábado: tudo que ainda estiver vencido após a grade da semana
    saturday_items = []
    for slug in subjects:
        prog = progress_store.setdefault(slug, {})
        for bid_str, info in list(prog.items()):
            bid = int(bid_str)
            if info["nextReviewWeek"] <= week_num and (slug, bid) not in reviewed_this_week and bid not in used_this_week[slug]:
                saturday_items.append({"slug": slug, "block_id": bid})
                n_done = len(info["reviews"])
                info["reviews"].append(week_num)
                info["nextReviewWeek"] = week_num + interval_for(n_done, state)
                used_this_week[slug].add(bid)

    if saturday_items:
        plan["saturday"] = {"mode": "review", "items": saturday_items}
    else:
        consolidate_items = []
        for day, entries in plan["days"].items():
            for e in entries:
                if not e["isReview"] and e["block_id"] is not None:
                    consolidate_items.append({"slug": e["slug"], "block_id": e["block_id"]})
        plan["saturday"] = {"mode": "consolidate", "items": consolidate_items}

    return plan


def required_content_keys(plan):
    keys = set()
    for entries in plan["days"].values():
        for e in entries:
            if e["block_id"] is not None:
                keys.add((e["slug"], e["block_id"]))
            if e["review_of"] is not None:
                keys.add((e["slug"], e["review_of"]))
    for item in plan["saturday"]["items"]:
        keys.add((item["slug"], item["block_id"]))
    return keys


def find_missing_content(state, keys):
    missing = []
    for slug, bid in sorted(keys):
        bc = state["subjects"][slug].get("blockContent", {})
        if str(bid) not in bc:
            block = next(b for b in state["subjects"][slug]["blocks"] if b["id"] == bid)
            missing.append((slug, bid, block["title"]))
    return missing


# ------------------------------------------------------------------ RENDER

def render_lei_seca(items):
    lis = []
    for ref, desc in items:
        lis.append(
            '<li><span class="ref">{}</span><span class="desc">{}</span></li>'.format(esc(ref), esc(desc))
        )
    return "\n".join(lis)


def check_id(week_num, day, slug, kind, block_id):
    return "s{:02d}:{}:{}:{}:{}".format(week_num, day, slug, kind, block_id)


def render_subject_card(state, plan_week_num, day, entry):
    slug = entry["slug"]
    subj = state["subjects"][slug]
    block_id = entry["block_id"]
    block = next(b for b in subj["blocks"] if b["id"] == block_id)
    content = subj["blockContent"][str(block_id)]

    parts = []
    parts.append('<div class="subject-card" style="--subj-color:{}">'.format(subj["color"]))
    parts.append(
        '<div class="subject-header"><span class="subject-icon">{}</span>'
        '<span class="subject-name">{}</span></div>'.format(subj["icon"], esc(subj["name"]))
    )
    parts.append('<div class="block-title">Bloco {}: {}</div>'.format(block_id, esc(block["title"])))

    tid = check_id(plan_week_num, day, slug, "teoria", block_id)
    parts.append('<div class="section-block">')
    parts.append("<h4>📘 Teoria do dia</h4>")
    parts.append('<div class="body-text">{}</div>'.format(esc(content["teoria"]).replace("\n", "<br><br>")))
    parts.append(
        '<p style="font-size:0.82rem;color:var(--text-faint);margin-top:8px;margin-bottom:10px;">'
        "📚 Para aprofundar: {}</p>".format(esc(content["referencia"]))
    )
    parts.append(
        '<label class="check-row"><input type="checkbox" data-check-id="{}"> Teoria concluída</label>'.format(tid)
    )
    parts.append("</div>")

    lid = check_id(plan_week_num, day, slug, "leiseca", block_id)
    parts.append('<div class="section-block">')
    parts.append("<h4>📖 Lei Seca do dia</h4>")
    parts.append('<ul class="lei-seca-list">{}</ul>'.format(render_lei_seca(content["lei_seca"])))
    parts.append(
        '<label class="check-row" style="margin-top:10px;"><input type="checkbox" data-check-id="{}"> '
        "Lei seca revisada</label>".format(lid)
    )
    parts.append("</div>")

    if entry.get("review_of") is not None:
        rblock = next(b for b in subj["blocks"] if b["id"] == entry["review_of"])
        rcontent = subj["blockContent"].get(str(entry["review_of"]))
        rid = check_id(plan_week_num, day, slug, "revisao", entry["review_of"])
        parts.append('<div class="review-block">')
        parts.append("<h4>🔁 Revisão rápida — Bloco {}: {}</h4>".format(entry["review_of"], esc(rblock["title"])))
        if rcontent:
            top_refs = rcontent["lei_seca"][:3]
            bullets = "".join("<li>{}: {}</li>".format(esc(r), esc(d)) for r, d in top_refs)
            parts.append(
                '<p class="body-text" style="font-size:0.86rem;">{}</p>'
                '<ul style="margin:6px 0 0;padding-left:18px;font-size:0.84rem;color:var(--text-soft);">{}</ul>'.format(
                    esc(rblock["desc"]), bullets
                )
            )
        parts.append(
            '<label class="check-row" style="margin-top:8px;"><input type="checkbox" data-check-id="{}"> '
            "Revisão feita (15-20 min)</label>".format(rid)
        )
        parts.append("</div>")

    qid = check_id(plan_week_num, day, slug, "questoes", block_id)
    placeholder = "LINK_TECCONCURSOS_{}_SEMANA{:02d}".format(slug.upper(), plan_week_num)
    parts.append('<div class="questions-box">')
    parts.append("✍️ <strong>Questões desta semana no TecConcursos</strong>")
    parts.append('<span class="link-placeholder">&lt;!-- {} --&gt;</span>'.format(placeholder))
    parts.append(
        '<label class="check-row" style="margin-top:10px;"><input type="checkbox" data-check-id="{}"> '
        "Questões feitas</label>".format(qid)
    )
    parts.append("</div>")

    parts.append("</div>")  # .subject-card
    return "\n".join(parts)


def render_day_section(state, plan_week_num, day, date_obj, entries, is_first):
    label = WEEKDAY_LABELS[day]
    date_str = date_obj.strftime("%d/%m")
    cols = "two-col" if len(entries) == 2 else ""
    chips = "".join(
        '<span class="subj-chip" style="background:{}">{} {}</span>'.format(
            state["subjects"][e["slug"]]["color"], state["subjects"][e["slug"]]["icon"], state["subjects"][e["slug"]]["name"]
        )
        for e in entries
    )
    cards = "\n".join(render_subject_card(state, plan_week_num, day, e) for e in entries)
    open_attr = " open" if is_first else ""
    return """<details class="day" data-date="{date_iso}"{open_attr}>
  <summary>
    <div class="day-title">
      <span class="day-name">{label}</span>
      <span class="day-date">{date_str}</span>
    </div>
    <div class="day-subjects-preview">
      <span class="today-badge" style="display:none;">HOJE</span>
      {chips}
      <span class="chevron">▾</span>
    </div>
  </summary>
  <div class="day-body">
    <div class="subject-grid {cols}">
      {cards}
    </div>
  </div>
</details>""".format(
        date_iso=date_obj.isoformat(),
        open_attr=open_attr,
        label=label,
        date_str=date_str,
        chips=chips,
        cols=cols,
        cards=cards,
    )


def render_saturday_section(state, plan_week_num, date_obj, sat_plan):
    mode = sat_plan["mode"]
    items = sat_plan["items"]
    title = "Revisão geral da semana" if mode == "review" else "Consolidação da semana"
    if not items:
        body = '<p class="consolidation-empty">Nada vencendo esta semana — dia livre para descansar ou adiantar questões.</p>'
    else:
        cards = []
        for item in items:
            slug = item["slug"]
            subj = state["subjects"][slug]
            block = next(b for b in subj["blocks"] if b["id"] == item["block_id"])
            content = subj["blockContent"].get(str(item["block_id"]))
            cid = check_id(plan_week_num, "saturday", slug, "revisao", item["block_id"])
            refs_html = ""
            if content:
                top = content["lei_seca"][:3]
                refs_html = "".join("<li>{}: {}</li>".format(esc(r), esc(d)) for r, d in top)
            cards.append(
                """<div class="consolidation-item" style="--subj-color:{color}">
  <div class="subj-line">{icon} {name}</div>
  <div class="block-name">Bloco {bid}: {btitle}</div>
  <p class="body-text" style="font-size:0.86rem;">{bdesc}</p>
  <ul style="margin:6px 0 0;padding-left:18px;font-size:0.84rem;color:var(--text-soft);">{refs}</ul>
  <label class="check-row" style="margin-top:8px;"><input type="checkbox" data-check-id="{cid}"> Revisado</label>
</div>""".format(
                    color=subj["color"],
                    icon=subj["icon"],
                    name=esc(subj["name"]),
                    bid=item["block_id"],
                    btitle=esc(block["title"]),
                    bdesc=esc(block["desc"]),
                    refs=refs_html,
                    cid=cid,
                )
            )
        body = '<div class="consolidation-list">{}</div>'.format("\n".join(cards))

    date_str = date_obj.strftime("%d/%m")
    return """<details class="day" data-date="{date_iso}">
  <summary>
    <div class="day-title">
      <span class="day-name">Sábado</span>
      <span class="day-date">{date_str}</span>
    </div>
    <div class="day-subjects-preview">
      <span class="today-badge" style="display:none;">HOJE</span>
      <span class="subj-chip" style="background:#78716c">🔁 {title}</span>
      <span class="chevron">▾</span>
    </div>
  </summary>
  <div class="day-body">
    {body}
  </div>
</details>""".format(date_iso=date_obj.isoformat(), date_str=date_str, title=title, body=body)


def render_sunday_section(date_obj):
    date_str = date_obj.strftime("%d/%m")
    return """<details class="day" data-date="{date_iso}">
  <summary>
    <div class="day-title">
      <span class="day-name">Domingo</span>
      <span class="day-date">{date_str}</span>
    </div>
    <div class="day-subjects-preview">
      <span class="today-badge" style="display:none;">HOJE</span>
      <span class="subj-chip" style="background:#a8a29e">☕ Livre</span>
      <span class="chevron">▾</span>
    </div>
  </summary>
  <div class="day-rest">Dia livre — sem conteúdo novo. Descanse, ou aproveite para adiantar questões do TecConcursos se estiver com vontade.</div>
</details>""".format(date_iso=date_obj.isoformat(), date_str=date_str)


def render_overview(state, plan):
    rows = []
    for day in WEEKDAYS:
        entries = plan["days"][day]
        chips = "".join(
            '<span class="subj-chip" style="background:{}">{} {}</span>'.format(
                state["subjects"][e["slug"]]["color"], state["subjects"][e["slug"]]["icon"], state["subjects"][e["slug"]]["name"]
            )
            for e in entries
        )
        rows.append(
            '<div class="overview-row"><span class="day-name">{}</span>{}</div>'.format(WEEKDAY_LABELS[day], chips)
        )
    sat_label = "Revisão geral" if plan["saturday"]["mode"] == "review" else "Consolidação da semana"
    rows.append(
        '<div class="overview-row"><span class="day-name">Sábado</span>'
        '<span class="subj-chip" style="background:#78716c">🔁 {}</span></div>'.format(sat_label)
    )
    rows.append('<div class="overview-row rest"><span class="day-name">Domingo</span>Livre / descanso</div>')
    return "\n".join(rows)


def render_week_html(state, plan, week_num):
    monday = week_monday(state, week_num)
    dates = {day: monday + datetime.timedelta(days=i) for i, day in enumerate(WEEKDAYS)}
    saturday_date = monday + datetime.timedelta(days=5)
    sunday_date = monday + datetime.timedelta(days=6)
    sunday_iso = sunday_date.isoformat()

    day_sections = []
    first_done = False
    for day in WEEKDAYS:
        day_sections.append(render_day_section(state, week_num, day, dates[day], plan["days"][day], not first_done))
        first_done = True
    day_sections.append(render_saturday_section(state, week_num, saturday_date, plan["saturday"]))
    day_sections.append(render_sunday_section(sunday_date))

    date_range = "{} a {} de {}".format(
        monday.day, sunday_date.day, monday.strftime("%B de %Y").replace("January", "janeiro")
    )
    # Simple PT-BR month names (avoid locale dependency)
    months_pt = {
        1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
        7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
    }
    date_range = "{} a {} de {} de {}".format(monday.day, sunday_date.day, months_pt[sunday_date.month], sunday_date.year)

    nav_prev = ""
    if week_num > 1:
        nav_prev = '<a class="nav-link" href="semana-{:02d}.html">← Semana {}</a>'.format(week_num - 1, week_num - 1)

    overview_rows = render_overview(state, plan)
    asset_v = state.get("assetVersion", 1)

    return """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Semana {week_num} — Tutoria OAB da Bianca</title>
<link rel="stylesheet" href="style.css?v={asset_v}">
</head>
<body>
  <div class="topbar">
    <div class="brand"><span class="logo">📚</span> Tutoria OAB da Bianca</div>
    <a class="nav-link" href="index.html">Semanas anteriores</a>
  </div>

  <div class="hero">
    <h1>Semana {week_num}</h1>
    <p class="subtitle">{date_range}</p>
    <div class="countdown">
      <span class="days" data-countdown-days>—</span>
      <span class="label">dias até a prova da OAB<br>(faltam <span data-countdown-weeks>—</span> semanas)</span>
    </div>
    <div class="progress-wrap">
      <div class="progress-label">
        <span>Progresso da semana</span>
        <span data-progress-text>0 de 0 concluídos (0%)</span>
      </div>
      <div class="progress-track"><div class="progress-fill"></div></div>
    </div>
    <div class="flag-behind" data-flag-behind></div>
  </div>

  <div class="overview">
    <h2>Visão geral da semana</h2>
    <div class="overview-grid">
      {overview_rows}
    </div>
  </div>

  {day_sections}

  <div class="site-footer">
    {nav_prev}
    <p style="margin-top:10px;">Feito com carinho para a Bianca passar na OAB. 💜</p>
  </div>

  <script src="app.js?v={asset_v}"></script>
  <script>
    OAB.initCountdown("{exam_date}");
    OAB.initToday();
    OAB.initChecklist("oab-bianca-s{week_num:02d}");
  </script>
</body>
</html>
""".format(
        week_num=week_num,
        date_range=date_range,
        overview_rows=overview_rows,
        day_sections="\n\n".join(day_sections),
        nav_prev=nav_prev,
        exam_date=state["examDate"],
        asset_v=asset_v,
    )


def render_index_html(state, all_weeks):
    items = []
    for w in sorted(all_weeks, reverse=True):
        monday = week_monday(state, w)
        sunday = monday + datetime.timedelta(days=6)
        current = " current" if w == state["currentWeek"] else ""
        items.append(
            '<a class="week-item{current}" href="semana-{w:02d}.html">'
            '<span><span class="week-num">Semana {w}</span><br>'
            '<span class="week-range">{d1:02d}/{m1:02d} a {d2:02d}/{m2:02d}</span></span>'
            '<span class="week-go">Abrir →</span></a>'.format(
                current=current, w=w, d1=monday.day, m1=monday.month, d2=sunday.day, m2=sunday.month
            )
        )
    latest = max(all_weeks)
    asset_v = state.get("assetVersion", 1)
    return """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tutoria OAB da Bianca</title>
<link rel="stylesheet" href="style.css?v={asset_v}">
<meta http-equiv="refresh" content="0; url=semana-{latest:02d}.html">
</head>
<body>
  <div class="topbar">
    <div class="brand"><span class="logo">📚</span> Tutoria OAB da Bianca</div>
  </div>
  <div class="hero">
    <h1>Bem-vinda de volta!</h1>
    <p class="subtitle">Redirecionando para a semana mais recente (Semana {latest})…</p>
    <div class="countdown">
      <span class="days" data-countdown-days>—</span>
      <span class="label">dias até a prova da OAB<br>(faltam <span data-countdown-weeks>—</span> semanas)</span>
    </div>
  </div>
  <div class="overview">
    <h2>Todas as semanas</h2>
    <div class="week-list">
      {items}
    </div>
  </div>
  <div class="site-footer"><p>Feito com carinho para a Bianca passar na OAB. 💜</p></div>
  <script src="app.js?v={asset_v}"></script>
  <script>OAB.initCountdown("{exam_date}");</script>
</body>
</html>
""".format(items="\n".join(items), latest=latest, exam_date=state["examDate"], asset_v=asset_v)


def main():
    if len(sys.argv) != 2:
        print("Uso: python3 scripts/generate_week.py <numero_da_semana>")
        sys.exit(1)
    week_num = int(sys.argv[1])

    state = load_state()

    # Passo 1: dry run numa cópia de progress para descobrir conteúdo necessário
    scratch_progress = copy.deepcopy(state["progress"])
    dry_plan = decide_week(state, week_num, scratch_progress)
    missing = find_missing_content(state, required_content_keys(dry_plan))
    if missing:
        print("Faltam blocos de conteúdo para gerar a Semana {}:\n".format(week_num))
        for slug, bid, title in missing:
            print("  - {} / bloco {}: {}".format(slug, bid, title))
        print(
            "\nLeia os PDFs no Google Drive (pasta Bianca/OAB/<matéria>/) e adicione "
            "teoria + referência + lei seca para esses blocos em "
            "subjects.<materia>.blockContent na chave do id do bloco, dentro de "
            "content/state.json. Depois rode este script de novo."
        )
        sys.exit(2)

    # Passo 2: aplica de verdade no progress real e grava
    real_plan = decide_week(state, week_num, state["progress"])
    state["currentWeek"] = week_num
    save_state(state)

    html_out = render_week_html(state, real_plan, week_num)
    week_file = DOCS_DIR / "semana-{:02d}.html".format(week_num)
    week_file.write_text(html_out, encoding="utf-8")
    print("Gerado: {}".format(week_file))

    existing_weeks = sorted(
        int(p.stem.split("-")[1]) for p in DOCS_DIR.glob("semana-*.html")
    )
    index_html = render_index_html(state, existing_weeks)
    (DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("Atualizado: {}".format(DOCS_DIR / "index.html"))


if __name__ == "__main__":
    main()
