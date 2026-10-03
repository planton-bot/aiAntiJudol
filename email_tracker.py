#!/usr/bin/env python3
# email_presence_scanner_full_input.py
# Author: Rafael Edition (expanded)
# Mode: input() only, many platforms, log-style output

import requests
import random
import re
import time
import json
from datetime import datetime
from typing import List, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from colorama import Fore, Style, init

init(autoreset=True)

# ------------- CONFIG -------------
TIMEOUT = 10
BASE_DELAY = 0.25    # base delay between requests
RETRIES = 2
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)",
    "Mozilla/5.0 (iPad; CPU OS 13_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko)",
]

# ------------- PLATFORMS (expanded) -------------
PLATFORMS = {
    "Instagram": ["https://www.instagram.com/{u}/"],
    "Facebook": ["https://www.facebook.com/{u}", "https://m.facebook.com/{u}"],
    "Twitter/X": ["https://twitter.com/{u}", "https://x.com/{u}"],
    "TikTok": ["https://www.tiktok.com/@{u}"],
    "Threads": ["https://www.threads.net/@{u}"],
    "YouTube": ["https://www.youtube.com/@{u}", "https://www.youtube.com/c/{u}"],
    "Reddit": ["https://www.reddit.com/user/{u}"],
    "Pinterest": ["https://www.pinterest.com/{u}/"],
    "Snapchat": ["https://www.snapchat.com/add/{u}"],
    "Spotify": ["https://open.spotify.com/user/{u}"],
    "SoundCloud": ["https://soundcloud.com/{u}"],
    "DeviantArt": ["https://www.deviantart.com/{u}"],
    "Tumblr": ["https://{u}.tumblr.com"],
    "Medium": ["https://medium.com/@{u}"],
    "GitHub": ["https://github.com/{u}"],
    "GitLab": ["https://gitlab.com/{u}"],
    "Bitbucket": ["https://bitbucket.org/{u}"],
    "StackOverflow": ["https://stackoverflow.com/users/{u}"],
    "Twitch": ["https://www.twitch.tv/{u}"],
    "Vimeo": ["https://vimeo.com/{u}"],
    "Imgur": ["https://imgur.com/user/{u}"],
    "Patreon": ["https://www.patreon.com/{u}"],
    "Ko-fi": ["https://ko-fi.com/{u}"],
    "OnlyFans": ["https://onlyfans.com/{u}"],
    "Fansly": ["https://fansly.com/{u}"],
    "Tumblr_Blog": ["https://{u}.tumblr.com/"],
    "Pinterest_Profile": ["https://www.pinterest.com/{u}/"],
    "Flickr": ["https://www.flickr.com/people/{u}/"],
    "Archive.org": ["https://archive.org/details/{u}"],
    "Last.fm": ["https://www.last.fm/user/{u}"],
    "Steam": ["https://steamcommunity.com/id/{u}", "https://steamcommunity.com/profiles/{u}"],
    "Blogger": ["https://{u}.blogspot.com"],
    "Wordpress": ["https://{u}.wordpress.com"],
    "Telegram": ["https://t.me/{u}"],
    "DiscordInvite": ["https://discord.gg/{u}"],
    "OK.ru": ["https://ok.ru/{u}"],
    "VK": ["https://vk.com/{u}"],
    # adult (user responsibility)
    "PornHub": ["https://www.pornhub.com/users/{u}", "https://www.pornhub.com/model/{u}"],
    "XVideos": ["https://www.xvideos.com/profiles/{u}", "https://www.xvideos.com/members/{u}"],
    "Xnxx": ["https://www.xnxx.com/profiles/{u}"],
    "RedTube": ["https://www.redtube.com/users/{u}"],
    "ManyVids": ["https://www.manyvids.com/Profile/{u}/"],
    # addons / tools
    "Firefox_Addons_User": ["https://addons.mozilla.org/en-US/firefox/user/{u}/"],
    "Chrome_Webstore_User": ["https://chrome.google.com/webstore/search/{u}"],
    "ProductHunt": ["https://www.producthunt.com/@{u}"],
    "Behance": ["https://www.behance.net/{u}"],
    "Dribbble": ["https://dribbble.com/{u}"],
}

# ------------- HELPERS -------------
def ts():
    return datetime.now().strftime("[%H:%M:%S]")

def choose_ua() -> str:
    return random.choice(USER_AGENTS)

def username_variants(local: str) -> List[str]:
    base = local.lower()
    v = [
        base,
        base.replace(".", ""),
        base.replace(".", "_"),
        re.sub(r'[^a-z0-9_]', '', base),
        re.sub(r'\d+$', '', base),
        base + "1",
        base + "_official",
        base + "_real",
        base + "123",
    ]
    # keep unique & limit
    out = []
    for x in v:
        if x and x not in out:
            out.append(x)
    return out[:20]

NOT_FOUND_MARKERS = [
    "page not found", "user not found", "not found", "404", "doesn't exist",
    "unavailable", "no such user", "sorry, this page", "profile isn't available",
    "we couldn't find that page", "this page isn't available", "no results found"
]

def is_not_found_text(content: str) -> bool:
    if not content:
        return False
    low = content.lower()
    return any(m in low for m in NOT_FOUND_MARKERS)

def make_session(timeout: int = TIMEOUT, retries: int = RETRIES) -> requests.Session:
    s = requests.Session()
    retry = Retry(total=retries, backoff_factor=0.3, status_forcelist=[429,500,502,503,504], allowed_methods=["HEAD","GET","OPTIONS"])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    # monkey-patch default timeout into session.request
    s.request = _wrap_request_with_timeout(s.request, timeout)
    return s

def _wrap_request_with_timeout(orig_request, timeout):
    def new_request(method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout
        return orig_request(method, url, **kwargs)
    return new_request

def head_then_get(url: str, session: requests.Session) -> Tuple[int, str]:
    """
    Try HEAD first; fallback to GET when appropriate. Return (status_code, text_or_empty)
    """
    headers = {"User-Agent": choose_ua()}
    try:
        resp = session.head(url, headers=headers, allow_redirects=True)
        code = resp.status_code
        if code == 200:
            # GET body for textual checks
            r2 = session.get(url, headers=headers)
            return r2.status_code, (r2.text or "")[:20000]
        if code in (301,302):
            return code, ""
        if code == 405:
            # HEAD not allowed
            r2 = session.get(url, headers=headers)
            return r2.status_code, (r2.text or "")[:20000]
        # other codes: return code without body
        return code, ""
    except Exception:
        try:
            r = session.get(url, headers=headers)
            return r.status_code, (r.text or "")[:20000]
        except Exception as e:
            return -1, str(type(e).__name__)

def check_url_found(url: str, session: requests.Session) -> Tuple[bool, str]:
    status, text = head_then_get(url, session)
    # small jitter
    time.sleep(BASE_DELAY * random.uniform(0.8, 1.4))
    if status == 200:
        if is_not_found_text(text):
            return False, "NotFoundText"
        return True, "OK"
    if status in (301,302):
        return True, f"Redirect({status})"
    if status in (401,403):
        return True, f"HTTP{status}"
    if status == 404:
        return False, "404"
    if status == -1:
        return False, f"Err:{text}"
    return False, f"HTTP{status}"

# ------------- MAIN -------------
def main():
    print(Fore.CYAN + "\n╔═════════════════════════════════════════════════════════╗")
    print("║              EMAIL PRESENCE SCANNER — FULL               ║")
    print("╚═════════════════════════════════════════════════════════╝\n" + Style.RESET_ALL)

    email = input("Masukkan email: ").strip()
    if not email:
        print(Fore.RED + "Email tidak boleh kosong. Keluar.")
        return

    # optional: allow user to choose more aggressive delay
    try:
        d_in = input("Delay per-request detik (enter=0.25): ").strip()
        if d_in:
            global BASE_DELAY
            BASE_DELAY = float(d_in)
    except Exception:
        pass

    local = email.split("@", 1)[0]
    variants = username_variants(local)
    session = make_session()

    results = {}
    print(Fore.YELLOW + f"{ts()} [~] | Scanning.." + Style.RESET_ALL)

    for plat, patterns in PLATFORMS.items():
        found = False
        reason = ""
        for u in variants:
            for patt in patterns:
                url = patt.format(u=u)
                ok, reason = check_url_found(url, session)
                if ok:
                    print(Fore.GREEN + f"{ts()} [+] | {plat}: Found")
                    results[plat] = {"found": True, "url": url, "username_checked": u, "reason": reason}
                    found = True
                    break
                # keep trying other variants
            if found:
                break
        if not found:
            print(Fore.RED + f"{ts()} [x] | {plat}: Not Found")
            results[plat] = {"found": False, "reason": reason or "NoMatch"}

    # Save results (json + txt)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = f"scan_result_{stamp}.json"
    txt_file = f"scan_result_{stamp}.txt"

    with open(json_file, "w", encoding="utf-8") as jf:
        json.dump({"email": email, "variants": variants, "results": results}, jf, indent=2, ensure_ascii=False)

    with open(txt_file, "w", encoding="utf-8") as tf:
        tf.write(f"Scan result for {email} @ {datetime.now().isoformat()}\n\n")
        for k, v in results.items():
            if v.get("found"):
                tf.write(f"[+] {k}: {v.get('url')} ({v.get('reason')}) username={v.get('username_checked')}\n")
            else:
                tf.write(f"[x] {k}: Not Found ({v.get('reason')})\n")

    print(Fore.CYAN + f"\n{ts()} [✓] Scan selesai. Hasil disimpan di:\n - {json_file}\n - {txt_file}\n" + Style.RESET_ALL)

if __name__ == "__main__":
    main()
