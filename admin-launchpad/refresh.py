#!/usr/bin/env python3
"""Refresh admin launchpad inventory from repos the supplied GitHub token can see."""
import datetime, json, os, pathlib, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / "inventory.json"
TOKEN = os.environ["INVENTORY_GITHUB_TOKEN"]
OWNER = os.getenv("INVENTORY_OWNER", "JoS727")
API = "https://api.github.com"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "calitoy-private-launchpad"}
def get(path):
    req = urllib.request.Request(API + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=40) as response:
        return json.load(response)
def all_repos():
    page = 1
    while True:
        chunk = get(f"/user/repos?affiliation=owner&per_page=100&page={page}&sort=full_name")
        for repo in chunk:
            if repo["owner"]["login"].lower() == OWNER.lower():
                yield repo
        if len(chunk) < 100: break
        page += 1
def infer_stage(r):
    if r.get("archived"): return "Archived"
    return "Unknown"
old = json.loads(DEST.read_text()) if DEST.exists() else {"repos":[]}
previous = {r["repo"]:r for r in old.get("repos",[])}
items = []
for r in all_repos():
    full = r["full_name"]
    prior = previous.get(full,{})
    verified = prior.get("verified", False)
    # Don't promote site/admin links automatically, even if repo homepage is set.
    items.append({
        "name":r["name"], "repo":full, "visibility":"private" if r["private"] else "public",
        "archived":r["archived"], "default_branch":r["default_branch"],
        "stage":prior.get("stage",infer_stage(r)) if verified else infer_stage(r),
        "site":prior.get("site","") if verified else "",
        "admin":prior.get("admin","") if verified else "",
        "host":prior.get("host","") if verified else "",
        "verified":verified,
        "note":prior.get("note","Deployment has not been verified"),
        "updated_at":r.get("pushed_at"), "repo_homepage_unverified":r.get("homepage") or ""
    })
items.sort(key=lambda x:x["name"].lower())
payload={"generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source":"GitHub authenticated repository API","verification":"Deployment and admin URLs require manual confirmation","repos":items}
DEST.write_text(json.dumps(payload,indent=2)+"\n")
print(f"Refreshed {len(items)} repositories (private inventory; do not deploy publicly)")
