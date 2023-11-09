import configparser

from pathlib import Path

from rich.console import Console
from typer import Exit
from mastodon import Mastodon


# constants and defaults
NFTOOT_LOG = Path("~/.config/nftoot/done.txt").expanduser()
NFTOOT_INI = Path("~/.config/nftoot/nftoot.ini").expanduser()
NFTOOT_TXT = """This non-fungible toot is owned by {owner} and by nobody else.
#NFT #NFToot #crypto #blockchain
{nonce}/{digest}"""


# to print messages
con = Console()


def read_config(path: Path):
    "load and return configuration"
    conf = configparser.ConfigParser()
    conf.read(path)
    return conf


def write_config(conf: configparser.ConfigParser, path: Path):
    "write updated configuration"
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open("w") as out:
        conf.write(out)
    con.log(f"saved [yellow]{path}[/]")


def connect(profile: str, config_path: Path):
    "connect to a profile defined in config"
    conf = read_config(config_path)
    if profile not in conf:
        con.print("[red]missing profile[/] run [blue]nftoot setup[/] first")
        raise Exit(2)
    cfg = conf[profile]
    instance = cfg["api_base_url"][8:]
    masto = Mastodon(api_base_url=cfg["api_base_url"],
                     client_id=cfg["client_id"],
                     client_secret=cfg["client_secret"],
                     access_token=cfg["access_token"])
    user = masto.me()  # also checks if login is OK
    con.log(f"logged in as [blue]{user['acct']}@{instance}[/]")
    return instance, masto, user
