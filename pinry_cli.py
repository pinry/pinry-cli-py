import json
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import click
import requests


DEFAULT_CONFIG_PATH = os.path.join(Path.home(), ".pinry-cli.config.json")


class PinryClient:
    def __init__(self, pinry_url, token):
        """
        @:param: pinry_url, like https://pin.xxx.com/
        """
        self.pinry_url = pinry_url
        self._profile_url = urljoin(pinry_url, "/api/v2/profile/users/")
        self._api_prefix = urljoin(pinry_url, '/api/v2/')
        self._pin_creation_url = urljoin(self._api_prefix, 'pins/')
        self._image_creation_url = urljoin(self._api_prefix, 'images/')
        self._board_add_url = urljoin(self._api_prefix, 'boards/')
        self._board_list_url = urljoin(self._api_prefix, 'boards-auto-complete/')
        self._cached_boards = None
        self._token = token

        self.session = requests.session()
        self.session.headers.update({"Authorization": "Token %s" % token})

    def _get_board_url(self, board_name):
        board_id = self._get_board_id(board_name)
        return f'{self._board_add_url}{board_id}/'

    def _get_board_id(self, board_name):
        return self.boards[board_name]

    def create_boards(self, board_names: set):
        for name in board_names:
            self.session.post(self._board_add_url, json={"name": name})
        self._update_board_caches()

    def _update_board_caches(self):
        data = self.session.get(self._board_list_url).json()
        self._cached_boards = {}
        for board in data:
            self._cached_boards[board['name']] = board['id']

    @property
    def boards(self):
        if self._cached_boards is not None:
            return self._cached_boards
        self._update_board_caches()
        return self._cached_boards

    def is_token_valid(self):
        resp = self.session.get(url=self._profile_url)
        if resp.status_code != 200:
            return False
        return not (resp.json() == [])

    def _upload_image(self, file_path):
        if not os.path.exists(file_path):
            raise ValueError(
                "Failed to upload image [%s]: not found" % file_path
            )
        resp = self.session.post(
            self._image_creation_url,
            files={"image": open(file_path, "rb")},
        )
        if resp.status_code != 201:
            raise ValueError(
                "Failed to upload image [%s]: %s" % (
                    file_path,
                    resp.json(),
                )
            )
        return resp.json()['id']

    def _create_pin(self, data, board_name=None):
        resp = self.session.post(
            url=self._pin_creation_url,
            json=data,
        )
        if resp.status_code != 201:
            raise ValueError("Failed to create pin %s, %s" % (data, resp.content))
        pin = resp.json()
        pin_id = pin['id']
        if board_name is not None:
            board_url = self._get_board_url(board_name)
            resp = self.session.patch(
                url=board_url,
                json={'pins_to_add': [pin_id, ]}
            )
            if resp.status_code != 200:
                raise ValueError(
                    "Failed to add pin to board: %s, %s" % (board_name, pin),
                )
        link = pin['resource_link']
        return link

    def create_with_file_upload(self, description, referer, file_path, tags, board_name=None):
        image_id = self._upload_image(file_path)
        data = dict(
            description=description,
            referer=referer,
            tags=tags,
            image_by_id=image_id,
        )
        return self._create_pin(
            data,
            board_name,
        )

    def create(self, description, referer, url, board_name, tags):
        data = dict(
            description=description,
            referer=referer,
            url=url,
            tags=tags,
        )
        return self._create_pin(
            data,
            board_name,
        )


def get_config(config_file_path=None) -> Optional[dict]:
    config_file_path = config_file_path or DEFAULT_CONFIG_PATH

    if not os.path.exists(config_file_path):
        return None
    with open(config_file_path, "r") as fp:
        config = json.load(fp)
    if "token" not in config:
        return
    if "pinry_url" not in config:
        return
    return config


def from_config(config: dict):
    return PinryClient(
        **config
    )


@click.group("pinry-commands")
@click.option("--config", "-c", "config", default=None, type=click.STRING, help="config file path")
@click.pass_context
def cmd_group(ctx, config):
    ctx.ensure_object(dict)
    config = config or DEFAULT_CONFIG_PATH
    ctx.obj['config'] = config


@cmd_group.command('config', help="add host and token for pinry")
@click.option("--pinry_url", prompt="Your pinry-instance host like 'https://pin.xxx.com'", type=click.STRING)
@click.option("--token", prompt="Your token in My -> Profile page", type=click.STRING)
@click.pass_context
def create_config(ctx, token, pinry_url):
    with open(ctx.obj['config'], "w") as fp:
        json.dump({"token": token, "pinry_url": pinry_url}, fp)


@cmd_group.command("add", help="add file or url to pinry instance")
@click.option("--board", "-b", "board", default=None, type=click.STRING, help="board name")
@click.option("--tags", "-t", "tags", default="", type=click.STRING, help="tags seperated by comma ','")
@click.option("--description", "-d", "description", default="", type=click.STRING, help="description text")
@click.option("--referer", "-r", "referer", default="", type=click.STRING, help="referer of pin")
@click.argument("file_or_url", type=click.STRING)
@click.pass_context
def create_pin(ctx, board, tags, description, referer, file_or_url):
    config = ctx.obj['config']
    config_data = get_config(config)
    if config_data is None:
        click.echo("config file invalid or doesn't exist, use 'pinry config' to create new", err=True)
        exit(1)
    client = from_config(config_data)
    if board not in client.boards:
        client.create_boards({board})
    if file_or_url.startswith("http"):
        link = client.create(
            description,
            referer=referer,
            board_name=board,
            url=file_or_url,
            tags=tags.split(","),
        )
    else:
        link = client.create_with_file_upload(
            description,
            referer=referer,
            board_name=board,
            file_path=file_or_url,
            tags=tags.split(","),
        )

    click.echo("pin created: %s" % link)


if __name__ == '__main__':
    cmd_group()
