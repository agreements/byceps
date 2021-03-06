"""
:Copyright: 2006-2017 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

from nose2.tools import params

from byceps.services.ticketing.models.ticket import Ticket

from testfixtures.user import create_user


user1 = create_user(1)
user2 = create_user(2)
user3 = create_user(3)


@params(
    (user1.id, None    , None    , user1.id, True ),
    (user1.id, user1.id, None    , user1.id, True ),
    (user1.id, None    , user1.id, user1.id, True ),
    (user1.id, user1.id, user1.id, user1.id, True ),

    (user1.id, user2.id, None    , user1.id, True ),
    (user1.id, None    , user2.id, user1.id, True ),
    (user1.id, user2.id, user2.id, user1.id, False),  # all management rights waived

    (user2.id, None    , None    , user1.id, False),
    (user2.id, user1.id, None    , user1.id, True ),
    (user2.id, None    , user1.id, user1.id, True ),
    (user2.id, user1.id, user1.id, user1.id, True ),
)
def test_is_managed_by(owned_by_id, seat_managed_by_id, user_managed_by_id, user_id, expected):
    ticket = create_ticket(owned_by_id,
                           seat_managed_by_id=seat_managed_by_id,
                           user_managed_by_id=user_managed_by_id)

    assert ticket.is_managed_by(user_id) == expected


@params(
    (user1.id, None    , user1.id, True ),
    (user1.id, user1.id, user1.id, True ),

    (user1.id, None    , user1.id, True ),
    (user1.id, user2.id, user1.id, False),  # management right waived

    (user2.id, None    , user1.id, False),
    (user2.id, user1.id, user1.id, True ),
)
def test_is_seat_managed_by(owned_by_id, seat_managed_by_id, user_id, expected):
    ticket = create_ticket(owned_by_id,
                           seat_managed_by_id=seat_managed_by_id)

    assert ticket.is_seat_managed_by(user_id) == expected


@params(
    (user1.id, None    , user1.id, True ),
    (user1.id, user1.id, user1.id, True ),

    (user1.id, None    , user1.id, True ),
    (user1.id, user2.id, user1.id, False),  # management right waived

    (user2.id, None    , user1.id, False),
    (user2.id, user1.id, user1.id, True ),
)
def test_is_user_managed_by(owned_by_id, user_managed_by_id, user_id, expected):
    ticket = create_ticket(owned_by_id,
                           user_managed_by_id=user_managed_by_id)

    assert ticket.is_user_managed_by(user_id) == expected


def create_ticket(owned_by_id, *, seat_managed_by_id=None,
                  user_managed_by_id=None):
    category_id = None

    ticket = Ticket(category_id, owned_by_id)
    ticket.seat_managed_by_id = seat_managed_by_id
    ticket.user_managed_by_id = user_managed_by_id

    return ticket
