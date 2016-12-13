#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Promote a user to organizer status.

:Copyright: 2006-2016 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

import click

from byceps.services.orga import service as orga_service

from bootstrap.util import app_context, get_config_filename_from_env
from bootstrap.validators import validate_brand, validate_user_screen_name


@click.command()
@click.argument('brand', callback=validate_brand)
@click.argument('user', callback=validate_user_screen_name)
def execute(brand, user):
    click.echo('Promoting user "{}" to orga for brand "{}" ... '
               .format(user.screen_name, brand.title), nl=False)

    orga_service.create_orga_flag(brand.id, user.id)

    click.secho('done.', fg='green')


if __name__ == '__main__':
    config_filename = get_config_filename_from_env()
    with app_context(config_filename):
        execute()
