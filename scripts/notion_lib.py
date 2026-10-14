"""Shared helpers for the Notion All Courses database.

Notion is the source of truth for courses. This module reads and writes the
"All Courses" database through the Notion API and maps its rows to the shape
sync_notion.py and add_course.py use. Python 3.11 stdlib only.

The API key comes from the NOTION_TOKEN environment variable (a GitHub Actions
secret). It is never written to disk or printed.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

DATABASE_ID = "a90327089bbb44819a61a5419a4dc1c6"
API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

STATUS_FROM_NOTION = {"Not started": "to-do", "In progress": "in-progress", "Done": "done"}

# Notion Domain option name -> site domain id (domains.json + domains-extra.json).
DOMAIN_IDS = {
    "Data & Analytics": "data", "Data Science": "ds", "Data Engineering & Infra": "deng",
    "AI & LLMs": "ai", "Applied AI": "aiap", "Visual Thinking & Storytelling": "viz",
    "Data Ops & Security": "dsec", "Data & AI Governance": "gov", "Let's Ship It End to End": "ship",
    "Programming & Dev Tools": "prog", "System & Product Design": "sys", "Emerging Tech": "emrg",
    "Markup / Docs & Diagrams": "docs", "Leadership & Decision-making": "lead",
    "Entrepreneurship & Business": "biz", "Communications": "comm",
    "Productivity & Knowledge Systems": "prod", "Mind & Movement": "move",
    "Finance & Economics": "fin", "Marketing & Branding": "mkt", "Thinking & Reasoning": "think",
    "Languages": "lang", "Teaching & Training": "teach", "Career & Exams": "career",
}

# Notion Platform option -> site platform (the site has always called Coursera "Coursera Plus").
PLATFORM_TO_SITE = {"Coursera": "Coursera Plus"}

# URL host -> Notion Platform option, for courses added by link.
HOST_PLATFORMS = [
    ("coursera.org", "Coursera"), ("udemy.com", "Udemy"), ("365datascience.com", "365 Data Science"),
    ("linkedin.com", "LinkedIn Learning"), ("datacamp.com", "DataCamp"),
    ("deeplearning.ai", "DeepLearning.AI"), ("skilljar.com", "Anthropic"), ("anthropic.com", "Anthropic"),
    ("skills.google", "Google"), ("cloudskillsboost.google", "Google"), ("cloud.google.com", "Google"),
    ("aws.amazon.com", "AWS"), ("skillbuilder.aws", "AWS"), ("nvidia.com", "NVIDIA"),
    ("microsoft.com", "Microsoft"), ("ibm.com", "IBM"), ("databricks.com", "Databricks"),
    ("youtube.com", "YouTube"), ("youtu.be", "YouTube"), ("dedao.cn", "得到"),
    ("luffycity.com", "路飞学城"), ("brilliant.org", "Brilliant"), ("algoexpert.io", "AlgoExpert"),
    ("insead.edu", "INSEAD"),
]

# First keyword hit picks a Domain for a course added by link. No hit leaves Domain empty,
# and the course waits in Notion until Phoebe picks one.
DOMAIN_KEYWORDS = [
    (r"\b(governance|responsible ai|ethic|gdpr|privacy|eu ai act|compliance)\b", "Data & AI Governance"),
    (r"\b(security|cyber|devsecops)\b", "Data Ops & Security"),
    (r"\b(agent|agentic|llm|gpt|claude|gemini|prompt|generative|gen ?ai|rag|hugging ?face)\b", "AI & LLMs"),
    (r"\b(mlops|deploy|production|devops)\b", "Let's Ship It End to End"),
    (r"\b(machine learning|deep learning|data science|statistic|probability|neural)\b", "Data Science"),
    (r"\b(data engineering|warehouse|lakehouse|spark|databricks|cloud|aws|azure|kubernetes|etl|pipeline)\b",
     "Data Engineering & Infra"),
    (r"\b(tableau|power bi|visuali[sz]ation|storytelling|dashboard)\b", "Visual Thinking & Storytelling"),
    (r"\b(analytics|analysis|analyst|sql|excel|bi)\b", "Data & Analytics"),
    (r"\b(python|javascript|coding|programming|git|algorithm)\b", "Programming & Dev Tools"),
    (r"\b(product management|product owner|system design|ux|design)\b", "System & Product Design"),
    (r"\b(blockchain|web3|crypto|quantum)\b", "Emerging Tech"),
    (r"\b(leader|leadership|management|manager|team|decision|strategy|change)\b",
     "Leadership & Decision-making"),
    (r"\b(marketing|brand|social media|seo)\b", "Marketing & Branding"),
    (r"\b(finance|financial|accounting|economic|investing)\b", "Finance & Economics"),
    (r"\b(startup|entrepreneur|business|consulting)\b", "Entrepreneurship & Business"),
    (r"\b(communication|presentation|public speaking|negotiation|writing)\b", "Communications"),
    (r"\b(english|chinese|language)\b", "Languages"),
    (r"\b(teaching|training|instructional)\b", "Teaching & Training"),
    (r"\b(interview|exam|certification prep|career)\b", "Career & Exams"),
    (r"\b(critical thinking|logic|thinking|creativity|innovation)\b", "Thinking & Reasoning"),
    (r"\b(productivity|notion|obsidian|knowledge)\b", "Productivity & Knowledge Systems"),
    (r"\b(yoga|meditation|fitness|wellbeing)\b", "Mind & Movement"),
]


class NotionError(RuntimeError):
    pass


def _token() -> str:
    tok = os.environ.get("NOTION_TOKEN", "").strip()
    if not tok:
        raise NotionError("NOTION_TOKEN is not set. Add it as a repository secret (see README, 'Notion sync').")
    return tok


def _call(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{API}{path}", method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Authorization": f"Bearer {_token()}", "Notion-Version": NOTION_VERSION,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        hint = ""
        if exc.code in (401, 403, 404):
            hint = (" Check that the integration is connected to the All Courses database "
                    "(Notion: ... menu > Connections) and that NOTION_TOKEN is current.")
        raise NotionError(f"Notion API {method} {path} failed: HTTP {exc.code} {detail}{hint}") from None


def _text(prop: dict | None) -> str:
    if not prop:
        return ""
    items = prop.get("title") or prop.get("rich_text") or []
    return "".join(i.get("plain_text", "") for i in items).strip()


def _select(prop: dict | None) -> str | None:
    if not prop:
        return None
    v = prop.get("select") or prop.get("status")
    return v.get("name") if v else None


def row_from_page(page: dict) -> dict:
    """Flatten one Notion page into the row shape used by sync_notion.py."""
    p = page.get("properties", {})
    rating = _select(p.get("Rating")) or ""
    end = (p.get("End Date") or {}).get("date") or {}
    return {
        "id": page["id"].replace("-", ""),
        "title": _text(p.get("Course")),
        "domain": _select(p.get("Domain")),
        "platform": _select(p.get("Platform")),
        "status": _select(p.get("Status")),
        "rating": max(1, min(5, rating.count("⭐"))) if rating else 1,
        "tags": [o["name"] for o in (p.get("Tags") or {}).get("multi_select", [])],
        "url": (p.get("URL") or {}).get("url") or "",
        "end_date": (end.get("start") or "")[:10] or None,
        "added": (page.get("created_time") or "")[:10],
        "pick": bool((p.get("Today's pick") or {}).get("checkbox")),
    }


def fetch_all_rows() -> list[dict]:
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        res = _call("POST", f"/databases/{DATABASE_ID}/query", body)
        rows += [row_from_page(pg) for pg in res.get("results", []) if not pg.get("archived")]
        if not res.get("has_more"):
            return rows
        cursor = res.get("next_cursor")


def set_pick(page_id: str, on: bool) -> None:
    _call("PATCH", f"/pages/{page_id}", {"properties": {"Today's pick": {"checkbox": on}}})


def find_by_url(url: str) -> dict | None:
    res = _call("POST", f"/databases/{DATABASE_ID}/query",
                {"page_size": 5, "filter": {"property": "URL", "url": {"equals": url}}})
    hits = res.get("results", [])
    return row_from_page(hits[0]) if hits else None


def create_course(title: str, url: str, platform: str | None, domain: str | None) -> dict:
    props = {
        "Course": {"title": [{"text": {"content": title[:1900]}}]},
        "URL": {"url": url},
        "Status": {"status": {"name": "Not started"}},
        "Rating": {"select": {"name": "⭐"}},
    }
    if platform:
        props["Platform"] = {"select": {"name": platform}}
    if domain:
        props["Domain"] = {"select": {"name": domain}}
    page = _call("POST", "/pages", {"parent": {"database_id": DATABASE_ID}, "properties": props})
    return {"id": page["id"].replace("-", ""), "url": page.get("url", "")}


def platform_for_url(url: str) -> str:
    host = re.sub(r"^www\.", "", (re.match(r"^https?://([^/:?#]+)", url) or [None, ""])[1].lower())
    for suffix, name in HOST_PLATFORMS:
        if host == suffix or host.endswith("." + suffix):
            return name
    return "Other"


def guess_domain(title: str, url: str) -> str | None:
    text = f"{title} {url}".lower().replace("-", " ").replace("_", " ")
    for pattern, name in DOMAIN_KEYWORDS:
        # Allow plurals: "agents", "pipelines", "leaders".
        if re.search(pattern[:-2] + r"s?\b" if pattern.endswith(r"\b") else pattern, text):
            return name
    return None
