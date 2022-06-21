
"""
Debug tools shell

$ python -m src.tools.node_shell
"""

import click

from src.modules.database.mongodb_client import MongodbClient

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('user_did')
@click.argument('app_did')
def database_name(user_did, app_did):
    """ show user's database name by user_did and app_did """
    print(f'database_name: {MongodbClient.get_user_database_name(user_did, app_did)}')


@click.group(context_settings=CONTEXT_SETTINGS)
def group_command():
    """ debug tools shell for hive node """


if __name__ == '__main__':
    group_command.add_command(database_name)
    group_command()
