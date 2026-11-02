import os, json, re, requests

BLOG_ID = os.environ["BLOG_ID"]
CLIENT_ID = os.environ["G_CLIENT_ID"]
CLIENT_SECRET = os.environ["G_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["G_REFRESH_TOKEN"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.environ.get("MODEL", "claude-sonnet-5-5")
# "true" = draft (pehle review karo), "false" = seedha live
IS_DRAFT = os.environ.get("IS_DRAFT", "true").lower()

TOPICS_FILE = "topics.txt"
DONE_FILE = "done.txt"


def next_topic():
    topics = [t.strip() for t in open(TOPICS_FILE, encoding="utf-8") if t.strip()]
    done = set()
    if os.path.exists(DONE_FILE):
        done = {t.strip() for t in open(DONE_FILE, encoding="utf-8")}
    for t in topics:
        if t not in done:
            return t
    return None


def write_article(topic):
    prompt = f"""Topic: {topic}

Is topic par ek original, helpful blog article Hinglish mein likho (Roman script mein Hindi+English mix, natural bolchaal wali style).
Rules:
- 800-1200 words, practical tips aur examples ke saath
- Facts ya numbers tabhi do jab pakka pata ho, warna mat banao
- Clear H2/H3 headings, short paragraphs
- Output sirf JSON: {{"title": "...", "labels": ["a","b","c"], "html": "<p>...</p>"}}
- "html" mein sirf body HTML (h2, h3, p, ul, li), <h1> mat daalo
- JSON ke bahar kuch mat likho, markdown fences bhi nahi"""
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": MODEL, "max_tokens": 4000,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    r.raise_for_status()
    text = r.json()["content"][0]["text"]
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def access_token():
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def post_to_blogger(article, token):
    r = requests.post(
        f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts",
        params={"isDraft": IS_DRAFT},
        headers={"Authorization": f"Bearer {token}"},
        json={
            "kind": "blogger#post",
            "title": article["title"],
            "content": article["html"],
            "labels": article.get("labels", []),
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("url", "(draft)")


if __name__ == "__main__":
    topic = next_topic()
    if not topic:
        print("topics.txt khatam ho gayi, naye topics add karo.")
        raise SystemExit(0)
    article = write_article(topic)
    url = post_to_blogger(article, access_token())
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(topic + "\n")
    print("Posted:", article["title"], url)
