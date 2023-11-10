# A bot to generate Non-Fungible Toots

`nftoot` is a Mastodon bot that posts a NFToot for each new follower.
Beyond this useful feature, `nftoot` is a simple Mastodon bot that was developed to play with `Mastodon.py` API.

## FAQ

A NFToot is a non-fungible toot owned by some mastodon account.
It includes:
 - the claim that the NFToot is owned by one account
 - hashtags
 - the hexadecimal representation of a genuine 4-bytes strong nonce
 - the hexadecimal SHA1 digest of the informations above

All together this makes a cryptographically validated proof of ownership.

##### I have a NFToot claiming to be owned by my, do I really own it?

Yes, it's literally written in the toot.

##### What can I do with my NFToot?
 
Mainly, own it.
But be imaginative, after all it's your NFToot.

##### Somebody boosted my NFToot, is it still mine?
  
Yes: it's still written in the toot.

##### What does non-fungible mean?

This means that your NFToot cannot be broken into smaller parts.
Obviously, doing so would result in fragments of texts that are not your NFToots, but only parts of it.

##### Is a 4-byte nonce enough to guarantee my NFToot uniqueness?

There's your account also, the nonce is mainly there because its a nice ornament.

##### Is SHA1 strong enough to guarantee my NFToot?

SHA1 is a real and serious cryptographic tool.
May it be broken in the future, your name is still written on the toot.

##### May my NFToot be lost?

If the account that generated it is closes, your NFToot will not be published anymore.
But you may copy its content to your own computer or republish it somewhere else.
This copies are also your NFToot, or if you prefer, they are distinct instances of the same NFToot.

##### Are you serious?

No.

##### How long does it take to get my NFToot once I follow the bot?

It depends, generating a NFToot is not that long, but getting it tooted may take some time because, you know, blockchains...

##### Are NFToots stored on a blockchain?

Technically, each NFToot is a block a bytes, and they are arranged as a chain of toots in the bot's timeline.
So, yes, this is actually a blockchain.

##### Can I sell my NFToot?

You can try.
But remember that, even sold, it will still claim to be owned by you.

##### Isn't NFToots a waste of natural resources?

Somehow yes.
But we use an advanced green technology that consumes very few energy to generate the NFToots.
All in all, one NFToot consumes less energy than a lolcat post as shown by this chart and much less than an IA generated text:

```
NFToot   #
LOLcat   ###
ChatGPT  ###########################################
```

## Install

Just `pip install nftoot`.
Dependencies:
 - [`typer[all]`](https://typer.tiangolo.com/)
 - [`Mastodon.py`](https://github.com/halcy/Mastodon.py)
 - [`bs4`](https://www.crummy.com/software/BeautifulSoup/)
 - [`lxml`](https://lxml.de/)
 - Python (developed with 3.12, run with 3.9.2)

Then run `nftoot setup` to log into you bot's account.
Finally run `nftoot update` to check for new followers and generate the corresponding NFToots.
The latter may run in a cron tab.
Rate limits may cause the command to crash, but you may just rerun it later on as new followers are only recorded when their NFToot has been successfully posted.
`nftoot update` may be run from cron, just consider that it downloads the whole list of followers each time it is run, so:
 - if run too often, it will work for nothing and consume your requests limit
 - if run too sparsely, it will have to generate more NFToots and may also hit rate limit

## Licence

NFToot software is (C) 2023 Franck Pommereau <franck.pommereau@univ-evry.fr> and released under the terms of the MIT licence, see `LICENCE.md`.
