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
from rich.progress import Progress
from typer import Typer, Option
from mastodon import Mastodon

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
            raise typer.Exit(0)
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
        raise typer.Exit(2)
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
    with Status(f"fetching [green]{profile['followers_count']}[/] followers"):
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
    config: Annotated[
        Path,
        Option(
            "--config", "-c",
            metavar="PATH",
            help="PATH to configuration file")] = NFTOOT_INI):
    readme = metadata.metadata("nftoot")["Description"]
    _, faqtext, _ = (t.strip() for t in re.split("^## .*$", readme, 2, re.M))
    last = None
    _, masto, _ = connect(account, config)
    faqitems = [f.strip().replace("NFToot", "#NFToot")
                for f in re.split("^##### ", faqtext, 0, re.M)]
    for num, faq in enumerate(faqitems, start=1):
        faq += f"\n#faq #thread {num}/..."
        if not dryrun:
            post = masto.status_post(faq,
                                     visibility=("public" if last is None
                                                 else "unlisted"),
                                     in_reply_to_id=last)
            if last is None:
                masto.status_pin(post["id"])
            last = post["id"]
        elif last is None:
            last = 0
        else:
            last += 1
        if verbose:
            con.log(f"posted [green]#{last}[/] [dim]({num}/{len(faqitems)})[/]"
                    + (f"\n[dim]{faq}[/]" if verbose else ""))


if __name__ == "__main__":
    app()
