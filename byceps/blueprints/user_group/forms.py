# -*- coding: utf-8 -*-

"""
byceps.blueprints.user_group.forms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2006-2017 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

from wtforms import StringField, TextAreaField

from ...util.l10n import LocalizedForm


class CreateForm(LocalizedForm):
    title = StringField('Titel')
    description = TextAreaField('Beschreibung')
