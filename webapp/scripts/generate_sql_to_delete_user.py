#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Generate the SQL statements to remove a user and his/her various
traces from the database.

:Copyright: 2006-2015 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

import click

from bootstrap.util import app_context, get_config_name_from_env
from bootstrap.validators import validate_user_screen_name


@click.command()
@click.argument('user', callback=validate_user_screen_name)
def execute(user):
    click.echo('Generating SQL statements to delete user "{}" ...'.format(user.screen_name))

    statements = generate_delete_statements(user.id)
    for statement in statements:
        click.secho(statement, fg='red')


def generate_delete_statements(user_id):
    for table, user_id_column in [
        ('auth_user_roles', 'user_id'),
        ('board_categories_lastviews', 'user_id'),
        ('board_topics_lastviews', 'user_id'),
        ('newsletter_subscriptions', 'user_id'),
        ('terms_consents', 'user_id'),
        ('verification_tokens', 'user_id'),
        ('user_details', 'user_id'),
        ('users', 'id'),
    ]:
        yield "DELETE FROM {} WHERE {} = '{}';".format(
            table, user_id_column, user_id)


if __name__ == '__main__':
    config_name = get_config_name_from_env()
    with app_context(config_name):
        execute()