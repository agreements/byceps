"""
:Copyright: 2006-2017 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

from decimal import Decimal

from nose2.tools import params

from byceps.util.l10n import set_locale
from byceps.util.money import format_euro_amount, to_two_places


@params(
    (Decimal(      '0.00' ),         '0,00 €'),
    (Decimal(      '0.01' ),         '0,01 €'),
    (Decimal(      '0.5'  ),         '0,50 €'),
    (Decimal(      '1.23' ),         '1,23 €'),
    (Decimal(    '123.45' ),       '123,45 €'),
    (Decimal(    '123.456'),       '123,46 €'),
    (Decimal('1234567'    ), '1.234.567,00 €'),
    (Decimal('1234567.89' ), '1.234.567,89 €'),
)
def test_format_euro_amount(value, expected):
    set_locale('de_DE.UTF-8')

    assert format_euro_amount(value) == expected


@params(
    (Decimal(       '0'), Decimal(  '0.00')),
    (Decimal(     '0.1'), Decimal(  '0.10')),
    (Decimal(    '0.01'), Decimal(  '0.01')),
    (Decimal(  '0.1234'), Decimal(  '0.12')),
    (Decimal(   '0.009'), Decimal(  '0.01')),
    (Decimal('123.4500'), Decimal('123.45')),
    (Decimal('123.4567'), Decimal('123.46')),
)
def test_to_two_places(value, expected):
    assert to_two_places(value) == expected
