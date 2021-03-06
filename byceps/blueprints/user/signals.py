"""
byceps.blueprints.user.signals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2006-2017 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

from blinker import Namespace


user_signals = Namespace()


email_address_confirmed = user_signals.signal('email-address-confirmed')
user_created = user_signals.signal('user-created')
