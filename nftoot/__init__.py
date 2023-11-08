import configparser
import webbrowser
import secrets
import hashlib
import re

from pathlib import Path
from typing import Annotated
from importlib import metadata
from rich.prompt import Confirm, Prompt
from rich.console import Console
from rich.status import Status
from rich.progress import Progress, track
from typer import Typer, Option, Exit
from mastodon import Mastodon
from bs4 import BeautifulSoup

NFTOOT_LOG = Path("~/.config/nftoot/done.txt").expanduser()
NFTOOT_INI = Path("~/.config/nftoot/nftoot.ini").expanduser()
NFTOOT_TXT = """This non-fungible toot is owned by {owner} and by nobody else.
#NFT #NFToot #crypto #blockchain
{nonce}/{digest}"""

app = Typer(context_settings={"help_option_names": ["-h", "--help"]})
con = Console()


@app.command(help="connect to the Mastodon account")
def setup(
        account: Annotated[
            str,
            Option(
                "--account", "-a",
                help="identifier for the account to be created")] = "default",
        config: Annotated[
            Path,
            Option(
                "--config", "-c",
                metavar="PATH",
                help="PATH to configuration file")] = NFTOOT_INI):
    conf = configparser.ConfigParser()
    conf.read(config)
    if account in conf:
        if not Confirm.ask(f"Account [blue]{account}[/] exists, overwrite?"):
            raise Exit(0)
    instance = Prompt.ask("instance name").strip()
    cfg = {"api_base_url": f"https://{instance}"}
    cfg["client_id"], cfg["client_secret"] = Mastodon.create_app("nftoot", **cfg)
    masto = Mastodon(**cfg)
    url = masto.auth_request_url()
    con.log(f"opening page [yellow]{url}[/]")
    webbrowser.open(url)
    code = Prompt.ask(f"type the code you received").strip()
    cfg["access_token"] = masto.log_in(code=code)
    conf[account] = cfg
    config.parent.mkdir(exist_ok=True, parents=True)
    with config.open("w") as out:
        conf.write(out)
    con.log(f"saved [yellow]{config}[/]")


def connect(profile, config):
    conf = configparser.ConfigParser()
    conf.read(config)
    if profile not in conf:
        con.print("[red]missing account[/] run [blue]nftoot setup[/] first")
        raise Exit(2)
    cfg = conf[profile]
    instance = cfg["api_base_url"][8:]
    masto = Mastodon(**cfg)
    profile = masto.me()
    con.log(f"logged in as [blue]{profile['acct']}@{instance}[/]")
    return instance, masto, profile


@app.command(help="generate NFToots for new followers")
def update(
        account: Annotated[
            str,
            Option(
                "--account", "-a",
                help="account to be used")] = "default",
        dryrun: Annotated[
            bool,
            Option(
                "-d/-n", "--dry/--no-dry",
                help="no not post NFToots")] = False,
        verbose: Annotated[
            bool,
            Option(
                "-v/-q", "--verbose/--quiet",
                help="print NFToots as they are posted")] = True,
        config: Annotated[
            Path,
            Option(
                "--config", "-c",
                metavar="PATH",
                help="PATH to configuration file")] = NFTOOT_INI):
    instance, masto, profile = connect(account, config)
    with Status(f"fetching [green]{profile['followers_count']}[/] followers",
                console=con):
        first_page = masto.account_followers(profile["id"])
        followers = masto.fetch_remaining(first_page)
    NFTOOT_LOG.touch()
    done = set(at.strip() for at in NFTOOT_LOG.open())
    new = [at if "@" in at else at + f"@{instance}"
           for user in followers
           if (at := user["acct"]) and at not in done]
    with NFTOOT_LOG.open("a") as log, \
            Progress(transient=True, console=con) as progress:
        for at in progress.track(new, description="posting NFToots"):
            txt = NFTOOT_TXT.format(owner=f"@{at}",
                                    nonce=secrets.token_hex(4),
                                    digest="{}")
            sha = hashlib.sha1(txt.encode("utf-8", errors="ignore"))
            txt = txt.format(sha.hexdigest())
            if not dryrun:
                masto.status_post(txt, visibility="unlisted")
                log.write(f"{at}\n")
            progress.log(f"posted NFT for [green]{at}[/]"
                         + (f"\n[dim]{txt}[/]" if verbose else ""))


def get_faq(profile, masto):
    with Status("fetching [green]#faq[/] toots"):
        first_page = masto.account_statuses(profile["id"], tagged="faq")
        toots = masto.fetch_remaining(first_page)
    return list(sorted(toots, key=lambda t: t["id"]))


def clean_faq(text):
    return "".join(text.strip()
                   .replace("NFToot", "#NFToot")
                   .split("\n```\n")[::2])


def clean_text(text):
    return " ".join(text.strip().replace("#NFToot", "NFToot").split())


def clean_html(html):
    bs = BeautifulSoup(html, "lxml")
    for br in bs.find_all("br"):
        br.replace_with("\n")
    return clean_text(" ".join(p.text for p in bs.find_all("p")))


def toot_faq(masto, faq, last, old=None):
    if old is None:
        post = masto.status_post(faq,
                                 visibility=("public" if last is None
                                             else "unlisted"),
                                 in_reply_to_id=last)
        if last is None:
            masto.status_pin(post["id"])
    else:
        medias = [m["id"] for m in old["media_attachments"]]
        post = masto.status_update(old["id"], faq, media_ids=medias)
    return post["id"]


def update_faq(old_faq, new_faq, masto, dryrun, verbose):
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
    last = None
    for old, new in track(zip(old_faq, new_faq),
                          console=con,
                          transient=True,
                          description="updating FAQ"):
        if clean_html(old["content"]) != clean_text(new):
            if not dryrun:
                last = toot_faq(masto, new, last, old)
            if verbose:
                con.log(f"updated [yellow]#{last or 0}[/]"
                        + (f"\n[dim]{new}[/]" if verbose else ""))
    for new in track(new_faq[len(old_faq):],
                     console=con,
                     transient=True,
                     description="extending FAQ"):
        if not dryrun:
            last = toot_faq(masto, new, last)
        if verbose:
            con.log(f"posted [green]#{last}[/]"
                    + (f"\n[dim]{new}[/]" if verbose else ""))


@app.command(help="publish #faq toots")
def faq(
    account: Annotated[
        str,
        Option(
            "--account", "-a",
            help="account to be used")] = "default",
    dryrun: Annotated[
        bool,
        Option(
            "-d/-n", "--dry/--no-dry",
            help="no not post NFToots")] = False,
    verbose: Annotated[
        bool,
        Option(
            "-v/-q", "--verbose/--quiet",
            help="print NFToots as they are posted")] = True,
    update: Annotated[
        bool,
        Option(
            "-u/-r", "--update/--replace",
            help="print NFToots as they are posted")] = False,
    config: Annotated[
        Path,
        Option(
            "--config", "-c",
            metavar="PATH",
            help="PATH to configuration file")] = NFTOOT_INI):
    readme = metadata.metadata("nftoot")["Description"]
    _, faqtext, _ = (t.strip() for t in re.split("^## .*$", readme, 2, re.M))
    faqitems = [clean_faq(f) + f"\n#faq #thread {n}/..."
                for n, f in enumerate(re.split("^##### ", faqtext, 0, re.M),
                                      start=1)]
    _, masto, profile = connect(account, config)
    if old := get_faq(profile, masto):
        if update:
            return update_faq(old, faqitems, masto, dryrun, verbose)
        else:
            con.print("[red]FAQ exists[/], use [blue]--update[/] to update")
            raise Exit(3)
    last = None
    for faq in faqitems:
        if not dryrun:
            last = toot_faq(masto, faq, last)
        elif last is None:
            last = 0
        else:
            last += 1
        if verbose:
            con.log(f"posted [green]#{last}[/]"
                    + (f"\n[dim]{faq}[/]" if verbose else ""))


if __name__ == "__main__":
    app()
