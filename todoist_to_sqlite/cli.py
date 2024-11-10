import time
import click
import pathlib
import json
import sqlite_utils
from tqdm import tqdm
from todoist_to_sqlite import utils
from todoist_api_python.api import TodoistAPI


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

    api = TodoistAPI(api_token)
    try:
        tasks = api.get_tasks()
    except Exception as e:
        click.echo(f"Error fetching tasks: {e}")
        return

    db = sqlite_utils.Database(db_path)
    tasks_table = db["tasks"]
    tasks_table.insert_all(
        (task.to_dict() for task in tasks),
        pk="id",
        replace=True
    )

    click.echo(f"Successfully synced {len(tasks)} tasks to {db_path}.")


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.option(
    "-a",
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
    api = TodoistAPI(api_token)

    total = None
    if not from_date and not to_date:
        total = api.get_completed_items()

    progress_bar = tqdm(desc="Fetching completed tasks", total=total, unit="tasks")

    PAGE_SIZE = 200
    offset = 0
    while True:
        resp = api.get_all_completed_tasks(
            api_token=api_token,
            limit=PAGE_SIZE,
            offset=offset,
            from_date=from_date and from_date.isoformat(),
            to_date=to_date and to_date.isoformat(),
        )
        resp.raise_for_status()
        data = resp.json()

        db["items"].upsert_all(
            data["items"],
            pk="id",
            alter=True,
            foreign_keys=utils.foreign_keys_for("items"),
        )
        db["projects"].upsert_all(
            data["projects"].values(),
            pk="id",
            alter=True,
            foreign_keys=utils.foreign_keys_for("projects"),
        )

        num_items = len(data["items"])
        if num_items == 0:
            break

        progress_bar.update(num_items)
        offset += num_items
        time.sleep(1)

    progress_bar.close()


if __name__ == "__main__":
    cli()
