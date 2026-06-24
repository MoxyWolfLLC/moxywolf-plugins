#!/usr/bin/env python3
"""Flatten an Apify harvestapi posts dataset (saved JSON) to a compact, scorable list.

The Apify get-dataset-items result can be too large for context. Save it to disk, then:
    python3 flatten_posts.py --file <saved.json> [--exclude a,b,c] [--limit 0]
Prints one line per post: idx | publicIdentifier | name | likes/comments | postedAgo | url
followed by the content (truncated). Designed to be read by a scoring subagent.

Accepts either the raw actor dataset (a list) or the get-dataset-items wrapper
({"items": [...]}). Dedupe by linkedinUrl; drop excluded publicIdentifiers.
"""
import argparse, json, sys

def get(d, path):
    cur = d
    for k in path.split("."):
        if isinstance(cur, dict) and k in cur: cur = cur[k]
        else: return None
    return cur

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--exclude", default="", help="comma-separated publicIdentifiers to drop")
    ap.add_argument("--limit", type=int, default=0, help="max posts to print (0 = all)")
    ap.add_argument("--truncate", type=int, default=600, help="chars of content per post")
    a = ap.parse_args()
    raw = json.load(open(a.file, encoding="utf-8"))
    items = raw.get("items", raw) if isinstance(raw, dict) else raw
    excl = {x.strip().lower() for x in a.exclude.split(",") if x.strip()}
    seen, out = set(), []
    for it in items:
        url = it.get("linkedinUrl") or get(it, "linkedinUrl")
        if url in seen: continue
        seen.add(url)
        pid = (get(it, "author.publicIdentifier") or "").lower()
        if pid in excl: continue
        content = it.get("content") or get(it, "repost.content") or ""
        if not content or len(content.strip()) < 40: continue
        out.append({
            "pid": pid,
            "name": get(it, "author.name") or "",
            "info": (get(it, "author.info") or "")[:120],
            "likes": get(it, "engagement.likes") or 0,
            "comments": get(it, "engagement.comments") or 0,
            "ago": get(it, "postedAt.postedAgoText") or "",
            "url": url or "",
            "content": content.strip().replace("\n", " ")[:a.truncate],
        })
    if a.limit: out = out[:a.limit]
    print(f"# {len(out)} posts (deduped, excluded {len(excl)} authors)\n")
    for i, p in enumerate(out, 1):
        print(f"[{i}] {p['pid']} | {p['name']} | {p['info']}")
        print(f"    {p['likes']} likes / {p['comments']} comments | {p['ago']} | {p['url']}")
        print(f"    {p['content']}\n")

if __name__ == "__main__":
    main()
