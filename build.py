#!/usr/bin/env python3
"""Morning View Letter 웹 아카이브 생성기.

content/*.md (front matter + 본문)를 읽어 issues/*.html 과 index.html 을 만든다.
외부 패키지 없이 python3 build.py 로 실행한다.
"""
import html
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
ISSUES = ROOT / "issues"

SECTIONS = {
    "AI": ("Morning AI Radar", "#5d8a85", "월"),
    "K-Wave": ("Morning K-Wave Radar", "#f37021", "화"),
    "Wellness": ("Morning Wellness Radar", "#5d7a5a", "수"),
    "Business": ("Morning Business Radar", "#6b5c4d", "목"),
    "Market": ("Morning Market Radar", "#8c7b6b", "금"),
    "Trend Note": ("Deep View · TREND NOTE", "#2c2b28", ""),
    "Seminar Note": ("Deep View · SEMINAR NOTE", "#35544f", ""),
}
WEEKDAYS = "월화수목금토일"


# ---------- 작은 마크다운 변환기 ----------

def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2))}" target="_blank" rel="noopener">{m.group(1)}</a>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    return text


def render_table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], [r for r in cells[1:] if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
    out = ['<div class="table-wrap"><table><thead><tr>']
    out += [f"<th>{inline(c)}</th>" for c in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def render_quote(lines):
    paras = [inline(l) for l in lines if l.strip()]
    body = "".join(f"<p>{p}</p>" for p in paras)
    plain = re.sub(r"<[^>]+>", "", paras[0]) if paras else ""
    cls = "why" if plain.startswith("왜 중요하냐") else "notice" if plain.startswith("알림") else "quote"
    return f'<blockquote class="{cls}">{body}</blockquote>'


def markdown(md):
    blocks, para = [], []
    lines = md.splitlines()
    i = 0

    def flush():
        if para:
            body = "<br>".join(inline(l) for l in para)
            plain = re.sub(r"<[^>]+>", "", body)
            if plain.startswith("왜 중요하냐"):
                blocks.append(f'<blockquote class="why"><p>{body}</p></blockquote>')
            else:
                blocks.append(f"<p>{body}</p>")
            para.clear()

    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()
        if not s:
            flush()
            i += 1
            continue
        m = re.match(r"(#{1,3})\s+(.*)", s)
        if m:
            flush()
            level = len(m.group(1)) + 1  # 문서 제목이 h1 이므로 한 단계씩 내린다
            blocks.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue
        if re.fullmatch(r"-{3,}|\*{3,}", s):
            flush()
            blocks.append("<hr>")
            i += 1
            continue
        if s.startswith(">"):
            flush()
            group = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                group.append(lines[i].strip()[1:].strip())
                i += 1
            # 연속된 인용 블록 사이의 빈 줄은 같은 인용으로 묶는다 (예: 오늘의 문장 + 출처)
            blocks.append(render_quote(group))
            continue
        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            blocks.append(render_table(rows))
            continue
        lm = re.match(r"(-|\d+\.)\s+(.*)", s)
        if lm:
            flush()
            tag = "ol" if lm.group(1)[0].isdigit() else "ul"
            items = []
            while i < len(lines):
                im = re.match(r"\s*(-|\d+\.)\s+(.*)", lines[i])
                if not im:
                    break
                items.append(f"<li>{inline(im.group(2))}</li>")
                i += 1
            blocks.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue
        para.append(s)
        i += 1
    flush()
    return "\n".join(closing_quote(merge_quotes(blocks)))


def merge_quotes(blocks):
    """'오늘의 문장' 인용과 바로 뒤의 출처(— 로 시작) 인용을 하나로 합친다."""
    out = []
    for b in blocks:
        if out and b.startswith('<blockquote class="quote"><p>— ') and out[-1].startswith('<blockquote class="quote">'):
            out[-1] = out[-1][: -len("</blockquote>")] + b.replace('<blockquote class="quote"><p>', '<p class="cite">', 1)
        else:
            out.append(b)
    return out


def closing_quote(blocks):
    """'오늘의 문장' 제목 아래 일반 문단들을 인용 스타일로 묶는다 (마지막 문단은 출처)."""
    for i, b in enumerate(blocks):
        if re.match(r"<h[23]>", b) and "오늘의 문장" in b:
            paras = []
            j = i + 1
            while j < len(blocks) and blocks[j].startswith("<p>"):
                paras.append(blocks[j][3:-4])
                j += 1
            q = '<blockquote class="quote">'
            if not paras and j + 1 < len(blocks) and blocks[j].startswith(q) and blocks[j + 1].startswith(q):
                cite = re.sub(r"</?p>", "", blocks[j + 1][len(q):-len("</blockquote>")])
                blocks[j:j + 2] = [blocks[j][: -len("</blockquote>")] + f'<p class="cite">{cite}</p></blockquote>']
            if paras:
                inner = "".join(f"<p>{p}</p>" for p in paras[:-1]) if len(paras) > 1 else f"<p>{paras[0]}</p>"
                cite = f'<p class="cite">{paras[-1]}</p>' if len(paras) > 1 else ""
                blocks[i + 1:j] = [f'<blockquote class="quote">{inner}{cite}</blockquote>']
            break
    return blocks


# ---------- 원고 읽기 ----------

def load(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = re.sub(r"\s+#.*$", "", v).strip()
    meta["body"] = m.group(2).strip()
    meta["date_obj"] = date.fromisoformat(meta["date"])
    if not meta.get("weekday"):
        meta["weekday"] = WEEKDAYS[meta["date_obj"].weekday()]
    meta["label"] = label(meta["id"])
    # 목차 카드에 쓸 한 줄: lead 가 없으면 본문 첫 굵은 제목을 쓴다
    first_bold = re.search(r"^\*\*(.+?)\*\*", meta["body"], re.M)
    meta["teaser"] = meta.get("lead") or (first_bold.group(1) if first_bold else "")
    return meta


def label(issue_id):
    kind, num = issue_id.split("-")
    return f"Vol.{num}" if kind == "vol" else f"No.{num}"


def fmt_date(meta):
    return f'{meta["date_obj"].strftime("%Y.%m.%d")}({meta["weekday"]})'


# ---------- 페이지 템플릿 ----------

HEAD = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=Noto+Serif+KR:wght@500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/style.css">
</head>
<body>
"""

FOOT = """<footer class="site-foot">
  <p><strong>Morning View Letter</strong> · 발행인 IM YOUNG HA · 에디터 MONET</p>
  <p>공개 출처 기사를 바탕으로 정리·큐레이션한 인사이트 뉴스레터입니다. 각 카드의 출처 링크에서 원문을 확인할 수 있어요.</p>
</footer>
</body>
</html>
"""


def issue_page(meta, prev, nxt):
    name, color, _ = SECTIONS[meta["section"]]
    read = f' · 읽는 시간 {meta["read_time"]}' if meta.get("read_time") else ""
    nav = ['<nav class="issue-nav">']
    nav.append(f'<a class="prev" href="{prev["id"]}.html"><span>이전 호</span>{prev["label"]} · {html.escape(prev["title"])}</a>' if prev else "<span></span>")
    nav.append(f'<a class="next" href="{nxt["id"]}.html"><span>다음 호</span>{nxt["label"]} · {html.escape(nxt["title"])}</a>' if nxt else "<span></span>")
    nav.append("</nav>")
    lead = f'<p class="lead">{inline(meta["lead"])}</p>' if meta.get("lead") else ""
    return (
        HEAD.format(title=f'{meta["label"]} · {html.escape(meta["title"])} — Morning View Letter',
                    desc=html.escape(meta.get("lead") or meta["title"]), root="../")
        + f"""<header class="topbar"><a href="../index.html">← Morning View Letter</a></header>
<main class="issue" style="--accent:{color}">
  <div class="issue-head">
    <p class="kicker"><span class="tag">{name}</span>{meta["label"]}</p>
    <h1>{html.escape(meta["title"])}</h1>
    <p class="meta">{fmt_date(meta)}{read}</p>
    {lead}
  </div>
  <article class="prose">
{markdown(meta["body"])}
  </article>
  {"".join(nav)}
</main>
"""
        + FOOT
    )


def index_page(issues):
    daily = [m for m in issues if m["id"].startswith("vol")]
    deep = [m for m in issues if m["id"].startswith("no")]
    latest = daily[0]

    def row(m):
        name, color, _ = SECTIONS[m["section"]]
        return (
            f'<li data-section="{m["section"]}" style="--accent:{color}"><a href="issues/{m["id"]}.html">'
            f'<span class="num">{m["label"]}</span>'
            f'<span class="sec">{m["section"]}</span>'
            f'<span class="ttl">{html.escape(m["title"])}</span>'
            f'<span class="dt">{m["date_obj"].strftime("%Y.%m.%d")}</span></a></li>'
        )

    chips = ['<button class="chip on" data-filter="all">전체</button>']
    sched = []
    for key, (name, color, day) in SECTIONS.items():
        if day:
            chips.append(f'<button class="chip" data-filter="{key}" style="--accent:{color}">{day} · {key}</button>')
            sched.append(f'<li style="--accent:{color}"><b>{day}</b>{name}</li>')
    lname, lcolor, _ = SECTIONS[latest["section"]]

    return (
        HEAD.format(title="Morning View Letter", desc="매일 아침 발행하는 트렌드 뉴스레터 Morning View Letter의 전체 아카이브", root="")
        + f"""<main class="archive">
  <header class="masthead">
    <p class="eyebrow">Daily Trend Letter · Archive</p>
    <h1>Morning View Letter</h1>
    <p class="tagline">매일 아침, 오늘 알아야 할 흐름 하나를 골라 드려요.</p>
    <ul class="schedule">{"".join(sched)}<li class="off"><b>토·일</b>휴무</li></ul>
  </header>

  <a class="latest" href="issues/{latest["id"]}.html" style="--accent:{lcolor}">
    <span class="kicker"><span class="tag">{lname}</span>최신호 · {latest["label"]}</span>
    <span class="latest-title">{html.escape(latest["title"])}</span>
    <span class="latest-lead">{html.escape(latest["teaser"])}</span>
    <span class="meta">{fmt_date(latest)} · 읽으러 가기 →</span>
  </a>

  <section>
    <h2 class="sec-title">Daily <small>{len(daily)}개 호</small></h2>
    <div class="chips">{"".join(chips)}</div>
    <ul class="list" id="daily">{"".join(row(m) for m in daily)}</ul>
  </section>

  <section>
    <h2 class="sec-title">Deep View <small>비정기 심층판</small></h2>
    <ul class="list">{"".join(row(m) for m in deep)}</ul>
  </section>
</main>
<script>
document.querySelectorAll('.chip').forEach(function (chip) {{
  chip.addEventListener('click', function () {{
    var f = chip.dataset.filter;
    document.querySelectorAll('.chip').forEach(function (c) {{ c.classList.toggle('on', c === chip); }});
    document.querySelectorAll('#daily li').forEach(function (li) {{
      li.hidden = f !== 'all' && li.dataset.section !== f;
    }});
  }});
}});
</script>
"""
        + FOOT
    )


def main():
    issues = sorted((load(p) for p in CONTENT.glob("*.md")), key=lambda m: (m["date_obj"], m["id"]), reverse=True)
    ISSUES.mkdir(exist_ok=True)
    for old in ISSUES.glob("*.html"):
        old.unlink()
    for kind in ("vol", "no"):
        series = [m for m in issues if m["id"].startswith(kind)]
        for i, m in enumerate(series):
            nxt = series[i - 1] if i > 0 else None
            prev = series[i + 1] if i + 1 < len(series) else None
            (ISSUES / f'{m["id"]}.html').write_text(issue_page(m, prev, nxt), encoding="utf-8")
    (ROOT / "index.html").write_text(index_page(issues), encoding="utf-8")
    print(f"{len(issues)}개 호를 만들었어요.")


if __name__ == "__main__":
    main()
