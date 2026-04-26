#!/usr/bin/env python3
"""Regenerate the neofetch-style jsoniq header block in README.md with fresh stats."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date

# ---- CONFIG ----
DOB = date(2006, 11, 1)  # update if needed
USER = "Arsh-S"
W = 69          # info column visible width
GAP = "   "
ASCII_ART = [
    "                                ,---,    ",
    "                              ,--.' |    ",
    "             __  ,-.          |  |  :    ",
    "           ,' ,'/ /| .--.--.  :  :  :    ",
    "   ,--.--. '  | |' |/  /    ' :  |  |,--.",
    "  /       \\|  |   ,|  :  /`./ |  :  '   |",
    " .--.  .-. '  :  / |  :  ;_   |  |   /' :",
    "  \\__\\/: . |  | '   \\  \\    `.'  :  | | |",
    "  ,″ .--.; ;  : |    `----.   |  |  ' | :",
    " /  /  ,.  |  , ;   /  /`--'  |  :  :_:,'",
    ";  :   .'   ---'   '--'.     /|  | ,'    ",
    "|  ,     .-./        `--'---' `--''      ",
    " `--`---'                                ",
]

# ---- helpers ----
def gh(args):
    out = subprocess.check_output(["gh", "api"] + args, text=True)
    return out.strip()

def field(label, value, width=W):
    p = f". {label}: "
    s = f" {value}"
    dots = "." * (width - len(p) - len(s))
    return p + dots + s

def stats_line(l1, v1, l2, v2, f1w=39, f2w=27):
    lp = f". {l1}: "; ls = f" {v1}"
    f1 = lp + "." * (f1w - len(lp) - len(ls)) + ls
    rp = f"{l2}: "; rs = f" {v2}"
    f2 = rp + "." * (f2w - len(rp) - len(rs)) + rs
    return f1 + " | " + f2

def hdr(text, width=W):
    return text + "—" * (width - len(text))

def fmt_int(n):
    return f"{n:,}"

def uptime_str(dob, today):
    years = today.year - dob.year
    months = today.month - dob.month
    if today.day < dob.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    return f"{years} years, {months} months"

# ---- gather data ----
print("fetching user info...", file=sys.stderr)
user = json.loads(gh([f"users/{USER}"]))
followers = user["followers"]
public_repos = user["public_repos"]

print("fetching owned repos...", file=sys.stderr)
repos = json.loads(gh([f"users/{USER}/repos?per_page=100&type=owner"]))
stars = sum(r["stargazers_count"] for r in repos)
clone_urls = [r["clone_url"] for r in repos]

print("counting commits...", file=sys.stderr)
commits_search = json.loads(gh([
    "search/commits", "-X", "GET",
    "-H", "Accept: application/vnd.github.cloak-preview+json",
    "-f", f"q=author:{USER}",
]))
commits = commits_search["total_count"]

print("counting contributed...", file=sys.stderr)
prs_search = json.loads(gh(["search/issues", "-X", "GET", "-f", f"q=author:{USER} type:pr"]))
contributed = prs_search["total_count"]

print("aggregating LOC across repos...", file=sys.stderr)
tmp = tempfile.mkdtemp(prefix="arsh-loc-")
add = del_ = 0
for url in clone_urls:
    name = url.rsplit("/", 1)[-1].removesuffix(".git")
    dest = os.path.join(tmp, name)
    subprocess.run(["git", "clone", "--quiet", url, dest], check=False, stderr=subprocess.DEVNULL)
    if not os.path.isdir(os.path.join(dest, ".git")):
        continue
    p = subprocess.run(
        ["git", "-C", dest, "log", "--author=Arsh", "--pretty=tformat:", "--numstat"],
        capture_output=True, text=True,
    )
    for line in p.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            add += int(parts[0])
            del_ += int(parts[1])
shutil.rmtree(tmp, ignore_errors=True)
loc_net = add - del_

today = date.today()
print(f"data: repos={public_repos} contributed={contributed} stars={stars} commits={commits} followers={followers} loc={loc_net} (+{add}/-{del_})", file=sys.stderr)

# ---- build info column ----
info = [
    hdr("arsh singh -"),
    field("OS", "macOS, Windows, Ubuntu"),
    field("Uptime", uptime_str(DOB, today)),
    field("Host", "Cornell University"),
    field("IDE", "Neovim, Cursor, Zed"),
    field("Experience", "Python, TypeScript, Java, C, C#, Swift"),
    field("Stack", "React, Next.js, Express, Flask, PostgreSQL"),
    field("Infra", "Docker, GCP, Cloudflare, Linux"),
    field("Hobbies", "Full-Stack, Hardware, Homelab, Tennis"),
    None,
    hdr("-— Contact "),
    field("Email", "mail@arshsingh.net"),
    field("LinkedIn", "linkedin.com/in/arshsingh5"),
    field("Website", "arshsingh.net"),
    None,
    hdr("-— GitHub Stats "),
    stats_line("Repos", f"{public_repos} {{Contributed: {contributed}}}", "Stars", str(stars)),
    stats_line("Commits", fmt_int(commits), "Followers", str(followers)),
    f". Lines of Code on GitHub: {fmt_int(loc_net)} ( {fmt_int(add)}++, {fmt_int(del_)}-- )",
]

# ---- compose block ----
out = []
ascii_w = len(ASCII_ART[0])
for i in range(max(len(ASCII_ART), len(info))):
    a = ASCII_ART[i] if i < len(ASCII_ART) else " " * ascii_w
    t = info[i] if i < len(info) else None
    if t is None:
        out.append(a.rstrip())
    else:
        out.append(a + GAP + t)
new_block = "```jsoniq\n" + "\n".join(out) + "\n```"

# ---- splice into README ----
readme_path = "README.md"
with open(readme_path) as f:
    src = f.read()
new_src = re.sub(r"```jsoniq\n.*?\n```", lambda m: new_block, src, count=1, flags=re.DOTALL)
if new_src == src:
    print("no change", file=sys.stderr)
    sys.exit(0)
with open(readme_path, "w") as f:
    f.write(new_src)
print("updated", file=sys.stderr)
