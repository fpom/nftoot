import re

from importlib import metadata
from typing import Optional
from rich.status import Status
from rich.progress import track
from bs4 import BeautifulSoup

from . import con


def clean_faq(text: str) -> str:
    return "".join(text.strip()
                   .replace("NFToot", "#NFToot")
                   .split("\n```\n")[::2])


def get_faq_readme() -> list[str]:
    "get FAQ items from README.md as a list of strings"
    readme = metadata.metadata("nftoot")["Description"]
    _, faqtext, _ = (t.strip() for t in re.split("^## .*$", readme, 2, re.M))
    return [clean_faq(f) + f"\n#faq #thread {n}/..."
            for n, f in enumerate(re.split("^##### ", faqtext, 0, re.M),
                                  start=1)]


def get_faq_online(userid: int, masto) -> list[dict]:
    "get FAQ items online as a list of statuses"
    with Status("fetching [green]#faq[/] toots"):
        first_page = masto.account_statuses(userid, tagged="faq")
        toots = masto.fetch_remaining(first_page)
    return list(sorted(toots, key=lambda t: t["id"]))


def clean_text(text: str) -> str:
    "clean and normalise text FAQ item"
    return " ".join(text.strip().replace("#NFToot", "NFToot").split())


def clean_html(html: str) -> str:
    "clean and normalise HTML FAQ item"
    bs = BeautifulSoup(html, "lxml")
    for br in bs.find_all("br"):
        br.replace_with("\n")
    return clean_text(" ".join(p.text for p in bs.find_all("p")))


def toot_faq(masto, faq: str, last: Optional[int], old: Optional[dict] = None):
    "post a FAQ item"
    if old is None:
        post = masto.status_post(faq,
                                 # only first FAQ item is public
                                 visibility=("public" if last is None
                                             else "unlisted"),
                                 in_reply_to_id=last)
        if last is None:
            # first FAQ item is pinned to profile
            masto.status_pin(post["id"])
    else:
        medias = [m["id"] for m in old["media_attachments"]]
        post = masto.status_update(old["id"], faq, media_ids=medias)
    return post["id"]


def update_faq(masto,
               old_faq: list[dict], new_faq: list[str],
               dryrun: bool, verbose: bool):
    "update FAQ online using items from README.md"
    # delete online items if new FAQ is shorter
    for old in track(old_faq[len(new_faq):],
                     console=con,
                     transient=True,
                     description="deleting FAQ"):
        if not dryrun:
            masto.status_delete(old["id"])
        if verbose:
            bs = BeautifulSoup(old["content"], "lxml")
            faq = "\n\n".join(p.text for p in bs.find_all("p"))
            con.log(f"deleted [red]#{old['id']}[/]"
                    + (f"\n[dim]{faq}[/]" if verbose else ""))
    # update common items
    last = None
    for old, new in track(zip(old_faq, new_faq),
                          console=con,
                          transient=True,
                          description="updating FAQ"):
        if clean_html(old["content"]) != clean_text(new):
            # only update if content has changed
            if not dryrun:
                last = toot_faq(masto, new, last, old)
            if verbose:
                con.log(f"updated [yellow]#{last or 0}[/]"
                        + (f"\n[dim]{new}[/]" if verbose else ""))
    # post additional items
    for new in track(new_faq[len(old_faq):],
                     console=con,
                     transient=True,
                     description="extending FAQ"):
        if not dryrun:
            last = toot_faq(masto, new, last)
        if verbose:
            con.log(f"posted [green]#{last}[/]"
                    + (f"\n[dim]{new}[/]" if verbose else ""))
