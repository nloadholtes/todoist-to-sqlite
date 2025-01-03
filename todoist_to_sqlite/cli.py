import time
import click
import pathlib
import json
import sqlite_utils
import http.client
import urllib.parse
from tqdm import tqdm
from todoist_to_sqlite import utils


@click.group()
@click.version_option()
def cli():
    "Save data from Todoist to a SQLite database"


@cli.command()
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to save tokens to, defaults to ./auth.json.",
)
def auth(auth):
    "Save authentication credentials to a JSON file"
    auth_data = {}
    if pathlib.Path(auth).exists():
        auth_data = json.load(open(auth))
    click.echo(
        "In Todoist, navigate to Settings > Integrations > API Token and paste it here:"
    )
    personal_token = click.prompt("API Token")
    auth_data["todoist_api_token"] = personal_token
    open(auth, "w").write(json.dumps(auth_data, indent=4) + "\n")
    click.echo()
    click.echo(
        "Your authentication credentials have been saved to {}. You can now import tasks by running:".format(
            auth
        )
    )
    click.echo()
    click.echo("    $ todoist-to-sqlite sync todoist.db")
    click.echo()
    click.echo("    # (Requires Todoist Premium)")
    click.echo()


def make_request(method, url, headers=None, params=None):
    parsed_url = urllib.parse.urlparse(url)
    conn = http.client.HTTPSConnection(parsed_url.netloc)
    path = parsed_url.path
    if params:
        path += '?' + urllib.parse.urlencode(params)
    conn.request(method, path, headers=headers)
    response = conn.getresponse()
    if response.status != 200:
        raise Exception(f"HTTP request failed with status {response.status}")
    return json.loads(response.read().decode())


@cli.command()
@click.argument("db_path", type=click.Path(file_okay=True, dir_okay=False))
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to the authentication JSON file, defaults to ./auth.json.",
)
def sync(db_path, auth):
    "Sync tasks from Todoist to a SQLite database"
    if not pathlib.Path(auth).exists():
        click.echo("Authentication file not found. Please run 'todoist-to-sqlite auth' first.")
        return

    auth_data = json.load(open(auth))
    api_token = auth_data.get("todoist_api_token")
    if not api_token:
        click.echo("API token not found in the authentication file.")
        return

    headers = {
        "Authorization": f"Bearer {api_token}"
    }

    try:
        tasks = make_request("GET", "https://api.todoist.com/rest/v2/tasks", headers=headers)
    except Exception as e:
        click.echo(f"Error fetching tasks: {e}")
        return

    db = sqlite_utils.Database(db_path)
    tasks_table = db["tasks"]
    tasks_table.insert_all(
        (task for task in tasks),
        pk="id",
        replace=True
    )

    click.echo(f"Successfully synced {len(tasks)} tasks to {db_path}.")


@cli.command()
@click.argument("db_path", type=click.Path(file_okay=True, dir_okay=False))
@click.option(
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to save tokens to, defaults to auth.json",
)
@click.option(
    "--from_date",
    type=click.DateTime(),
    help="Saves tasks with a completion date on or older than from_date.",
)
@click.option(
    "--to_date",
    type=click.DateTime(),
    help="Saves tasks with a completion date on or newer than to_date.",
)
def completed_tasks(db_path, auth, from_date, to_date):
    """Save all completed tasks for the authenticated user (requires Todoist premium)"""
    db = sqlite_utils.Database(db_path)
    try:
        data = json.load(open(auth))
        api_token = data["todoist_api_token"]
    except (KeyError, FileNotFoundError):
        utils.error(
            "Cannot find authentication data, please run `todoist_to_sqlite auth`!"
        )
        return

    headers = {
        "Authorization": f"Bearer {api_token}"
    }

    progress_bar = tqdm(desc="Fetching completed tasks", unit="tasks")

    PAGE_SIZE = 200
    cursor = None

    while True:
        params = {"limit": PAGE_SIZE}
        if cursor:
            params["offset"] = cursor
        if from_date:
            params["since"] = from_date.isoformat()
        if to_date:
            params["until"] = to_date.isoformat()

        try:
            data = make_request("GET", "https://api.todoist.com/sync/v9/completed/get_all", headers=headers, params=params)
            tasks = data['items']
            # Cursor does not exist in this world
            # cursor = data['next_cursor']
        except Exception as e:
            utils.error(f"Error fetching completed tasks: {e}")
            return

        if not tasks:
            break

        db["completed_tasks"].insert_all(
            (task for task in tasks),
            pk="id",
            replace=True
        )

        progress_bar.update(len(tasks))

        if not cursor:
            break

    progress_bar.close()
    click.echo(f"Successfully synced completed tasks to {db_path}.")


if __name__ == "__main__":
    cli()
