"""
byceps.blueprints.orga_admin.forms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2006-2017 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

from wtforms import StringField

from ...util.l10n import LocalizedForm


class OrgaFlagCreateForm(LocalizedForm):
    user_id = StringField('Benutzer-ID')
