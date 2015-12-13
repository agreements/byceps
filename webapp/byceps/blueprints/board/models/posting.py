# -*- coding: utf-8 -*-

"""
byceps.blueprints.board.models.posting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2006-2015 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

from datetime import datetime

from flask import current_app, g, url_for

from ....database import BaseQuery, db, generate_uuid
from ....util.instances import ReprBuilder
from ....util.iterables import index_of

from ...user.models import User

from ..authorization import BoardPostingPermission

from .topic import Topic


class PostingQuery(BaseQuery):

    def for_topic(self, topic):
        return self.filter_by(topic=topic)

    def only_visible_for_current_user(self):
        """Only return postings the current user may see."""
        if not g.current_user.has_permission(BoardPostingPermission.view_hidden):
            return self.without_hidden()

        return self

    def without_hidden(self):
        """Only return postings every user may see."""
        return self.filter(Posting.hidden == False)

    def earliest_to_latest(self):
        return self.order_by(Posting.created_at.asc())

    def latest_to_earliest(self):
        return self.order_by(Posting.created_at.desc())


class Posting(db.Model):
    """A posting."""
    __tablename__ = 'board_postings'
    query_class = PostingQuery

    id = db.Column(db.Uuid, default=generate_uuid, primary_key=True)
    topic_id = db.Column(db.Uuid, db.ForeignKey('board_topics.id'), index=True, nullable=False)
    topic = db.relationship(Topic, backref='postings')
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    creator_id = db.Column(db.Uuid, db.ForeignKey('users.id'), nullable=False)
    creator = db.relationship(User, foreign_keys=[creator_id])
    body = db.Column(db.UnicodeText, nullable=False)
    last_edited_at = db.Column(db.DateTime)
    last_edited_by_id = db.Column(db.Uuid, db.ForeignKey('users.id'))
    last_edited_by = db.relationship(User, foreign_keys=[last_edited_by_id])
    edit_count = db.Column(db.Integer, default=0, nullable=False)
    hidden = db.Column(db.Boolean, default=False, nullable=False)
    hidden_at = db.Column(db.DateTime)
    hidden_by_id = db.Column(db.Uuid, db.ForeignKey('users.id'))
    hidden_by = db.relationship(User, foreign_keys=[hidden_by_id])

    def __init__(self, topic, creator, body):
        self.topic = topic
        self.creator = creator
        self.body = body

    def may_be_updated_by_user(self, user):
        return not self.topic.locked and (
            (
                user == self.creator and \
                user.has_permission(BoardPostingPermission.update)
            ) or \
            user.has_permission(BoardPostingPermission.update_of_others)
        )

    def hide(self, user):
        self.hidden = True
        self.hidden_at = datetime.now()
        self.hidden_by = user

    def unhide(self):
        self.hidden = False
        self.hidden_at = None
        self.hidden_by = None

    def calculate_page_number(self):
        """Return the number of the page this posting should appear on."""
        topic_postings = Posting.query \
            .for_topic(self.topic) \
            .only_visible_for_current_user() \
            .earliest_to_latest() \
            .all()

        index = index_of(lambda p: p == self, topic_postings)
        if index is None:
            return  # Shouldn't happen.

        per_page = int(current_app.config['BOARD_POSTINGS_PER_PAGE'])
        return divmod(index, per_page)[0] + 1

    @property
    def anchor(self):
        """Return the URL anchor for this posting."""
        return 'posting-{}'.format(self.id)

    @property
    def external_url(self):
        """Return the absolute URL of this posting (in its topic)."""
        return url_for('board.posting_view', id=self.id, _external=True)

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        builder = ReprBuilder(self) \
            .add_with_lookup('id') \
            .add('topic', self.topic.title) \
            .add('creator', self.creator.screen_name)

        if self.hidden:
            builder.add_custom('hidden by {}'.format(self.hidden_by.screen_name))

        return builder.build()