"CLI to nftoot"

import webbrowser
import secrets
import hashlib

from pathlib import Path
from typing import Annotated
from rich.prompt import Confirm, Prompt
from rich.status import Status
from rich.progress import Progress
from typer import Typer, Option, Exit
from mastodon import Mastodon

from . import con, connect, read_config, write_config, \
    NFTOOT_LOG, NFTOOT_INI, NFTOOT_TXT
from .faq import get_faq_readme, get_faq_online, update_faq


app = Typer(context_settings={"help_option_names": ["-h", "--help"]})


@app.command(help="connect to the Mastodon account")
def setup(
        profile: Annotated[
            str,
            Option(
                "--profile", "-p",
                help="identifier for the profile to be created")] = "default",
        config: Annotated[
            Path,
            Option(
                "--config", "-c",
                metavar="PATH",
                help="PATH to configuration file")] = NFTOOT_INI):
    # read config and check if profile exists
    conf = read_config(config)
    if profile in conf:
        if not Confirm.ask(f"Profile [yellow]{profile}[/] exists, overwrite?"):
            raise Exit(0)
    # get instance name and create app identity
    instance = Prompt.ask("instance name").strip()
    cfg = {"api_base_url": f"https://{instance}"}
    cfg["client_id"], cfg["client_secret"] = \
        Mastodon.create_app("nftoot", api_base_url=cfg["api_base_url"])
    # authenticate on the web and get API token
    masto = Mastodon(api_base_url=cfg["api_base_url"],
                     client_id=cfg["client_id"],
                     client_secret=cfg["client_secret"],
                     access_token=cfg["access_token"])
    url = masto.auth_request_url()
    con.log(f"opening page [green]{url}[/]")
    webbrowser.open(url)
    code = Prompt.ask(f"type the code you received").strip()
    cfg["access_token"] = masto.log_in(code=code)
    # save config
    conf[profile] = cfg
    write_config(conf, config)


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
    # get the list of followers using paginated responses
    with Status(f"fetching [green]{profile['followers_count']}[/] followers",
                console=con):
        first_page = masto.account_followers(profile["id"])
        followers = masto.fetch_remaining(first_page)
    # load previously known followers
    NFTOOT_LOG.touch()
    done = set(at.strip() for at in NFTOOT_LOG.open())
    # build the list of new followers
    new = [at if "@" in at else at + f"@{instance}"
           for user in followers
           if (at := user["acct"]) and at not in done]
    # generate nftoots for new followers
    with NFTOOT_LOG.open("a") as log, \
            Progress(transient=True, console=con) as progress:
        for at in progress.track(new, description="posting NFToots"):
            # fill all but digest
            txt = NFTOOT_TXT.format(owner=f"@{at}",
                                    nonce=secrets.token_hex(4),
                                    digest="{}")
            # add digest
            sha = hashlib.sha1(txt.encode("utf-8", errors="ignore"))
            txt = txt.format(sha.hexdigest())
            # post nftoot and log it
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
    _, masto, profile = connect(account, config)
    # get already posted FAQ items
    old = get_faq_online(profile["id"], masto)
    if old and not update:
        con.print("[red]FAQ exists[/], use [blue]--update[/] to update")
        raise Exit(3)
    # update items wrt those in README
    update_faq(masto, old, get_faq_readme(), dryrun, verbose)


if __name__ == "__main__":
    app()
