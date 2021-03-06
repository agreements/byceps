"""
:Copyright: 2006-2017 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

import json

from byceps.services.newsletter.models import Subscription
from byceps.services.newsletter.types import SubscriptionState

from tests.base import AbstractAppTestCase, CONFIG_FILENAME_TEST_ADMIN
from tests.helpers import assign_permissions_to_user

from testfixtures.user import create_user


class NewsletterAdminTestCase(AbstractAppTestCase):

    def setUp(self):
        super().setUp(config_filename=CONFIG_FILENAME_TEST_ADMIN)

        self.setup_admin()
        self.setup_subscribers()

    def setup_admin(self):
        permission_ids = {'admin.access', 'newsletter.export_subscribers'}
        assign_permissions_to_user(self.admin.id, 'admin', permission_ids)

    def setup_subscribers(self):
        for user_number, enabled, states in [
            (1, True,  [SubscriptionState.requested                             ]),
            (2, True,  [SubscriptionState.declined                              ]),
            (3, False, [SubscriptionState.requested                             ]),
            (4, True,  [SubscriptionState.declined,  SubscriptionState.requested]),
            (5, True,  [SubscriptionState.requested, SubscriptionState.declined ]),
            (6, True,  [SubscriptionState.requested                             ]),
        ]:
            user = self.create_user(user_number, enabled=enabled)
            self.add_subscriptions(user, states)

    def test_export_subscribers(self):
        expected_data = {
            'subscribers': [
                {
                    'screen_name': 'User-1',
                    'email_address': 'user001@example.com',
                },
                # User #2 has declined a subscription.
                # User #3 is not enabled.
                # User #4 has initially declined, but later requested a subscription.
                {
                    'screen_name': 'User-4',
                    'email_address': 'user004@example.com',
                },
                # User #5 has initially requested, but later declined a subscription.
                {
                    'screen_name': 'User-6',
                    'email_address': 'user006@example.com',
                },
            ],
        }

        url = '/admin/newsletter/subscriptions/{}/export'.format(self.brand.id)
        response = self.get_as_admin(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.get_data().decode('utf-8'))
        self.assertEqual(data, expected_data)

    def test_export_subscriber_email_addresses(self):
        expected_data = '\n'.join([
            'user001@example.com',
            # User #2 has declined a subscription.
            # User #3 is not enabled.
            # User #4 has initially declined, but later requested a subscription.
            'user004@example.com',
            # User #5 has initially requested, but later declined a subscription.
            'user006@example.com',
        ]).encode('utf-8')

        url = '/admin/newsletter/subscriptions/{}/export_email_addresses'.format(self.brand.id)
        response = self.get_as_admin(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/plain; charset=utf-8')
        self.assertEqual(response.mimetype, 'text/plain')
        self.assertEqual(response.get_data(), expected_data)

    def create_user(self, number, *, enabled=True):
        user = create_user(number, enabled=enabled)

        self.db.session.add(user)
        self.db.session.commit()

        return user

    def add_subscriptions(self, user, states):
        for state in states:
            self.add_subscription(user, state)

        self.db.session.commit()

    def add_subscription(self, user, state):
        subscription = Subscription(user.id, self.brand.id, state)
        self.db.session.add(subscription)

    def get_as_admin(self, url):
        """Make a GET request as the admin and return the response."""
        with self.client(user=self.admin) as client:
            return client.get(url)
