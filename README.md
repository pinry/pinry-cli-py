# pinry-cli

CLI tools comes to Pinry!

# Feature

+ Add pin from local image file
+ Add pin from image url
+ Save pinry instance and token locally

About [Get the Token](https://docs.getpinry.com/api/)

# Install

`pip install pinry-cli`

# Usage

Get help:

```
-> pinry
 
Usage: pinry [OPTIONS] COMMAND [ARGS]...

Options:
  -c, --config TEXT  config file path
  --help             Show this message and exit.

Commands:
  add     add file or url to pinry instance
  config  add host and token for pinry

```

Add config (pinry host url and token):

```
pinry config
```

Add a Pin:

```
pinry add "https://pin.37soloist.com/media/c/a/caff442c3f9a0cd73c50272d40771b76/FL-kQgyXIAEQuTz
" --board "any-board" --tags tag1,tag2
```
