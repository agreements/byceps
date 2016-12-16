# -*- coding: utf-8 -*-

"""
byceps.config_defaults
~~~~~~~~~~~~~~~~~~~~~~

Default configuration values

:Copyright: 2006-2016 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

from datetime import timedelta


DEBUG = False

# database connection
SQLALCHEMY_ECHO = False

# job queue
JOBS_ASYNC = True

# RQ dashboard (for job queue)
RQ_DASHBOARD_ENABLED = False
RQ_POLL_INTERVAL = 2500

# user accounts
USER_REGISTRATION_ENABLED = True

# login sessions
PERMANENT_SESSION_LIFETIME = timedelta(14)

# localization
LOCALE = 'de_DE.UTF-8'
LOCALES_FORMS = ['de']

# news item pagination
NEWS_ITEMS_PER_PAGE = 4

# message board pagination
BOARD_TOPICS_PER_PAGE = 10
BOARD_POSTINGS_PER_PAGE = 10

# ticketing
TICKET_MANAGEMENT_ENABLED = True
