"""
byceps.services.user.service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2006-2017 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

from datetime import date, datetime, timedelta
from typing import Dict, Iterator, Optional, Set

from flask import current_app, url_for

from ...database import db
from ...typing import BrandID, PartyID, UserID

from ..authentication.password import service as password_service
from ..authorization.models import RoleID
from ..authorization import service as authorization_service
from ..email import service as email_service
from ..newsletter import service as newsletter_service
from ..orga_team.models import OrgaTeam, Membership as OrgaTeamMembership
from ..terms.models import VersionID as TermsVersionID
from ..terms import service as terms_service
from ..user_avatar.models import Avatar, AvatarSelection
from ..verification_token.models import Token
from ..verification_token import service as verification_token_service

from .models.detail import UserDetail
from .models.user import AnonymousUser, User, UserTuple


def count_users() -> int:
    """Return the number of users."""
    return User.query \
        .count()


def count_users_created_since(delta: timedelta) -> int:
    """Return the number of user accounts created since `delta` ago."""
    filter_starts_at = datetime.now() - delta

    return User.query \
        .filter(User.created_at >= filter_starts_at) \
        .count()


def count_enabled_users() -> int:
    """Return the number of enabled user accounts."""
    return User.query \
        .filter_by(enabled=True) \
        .count()


def count_disabled_users() -> int:
    """Return the number of disabled user accounts."""
    return User.query \
        .filter_by(enabled=False) \
        .count()


def find_user(user_id: UserID, *, with_orga_teams: bool=False) -> Optional[User]:
    """Return the user with that ID, or `None` if not found."""
    query = User.query

    if with_orga_teams:
        query = query.options(
            db.joinedload('orga_team_memberships').joinedload('orga_team').joinedload('party')
        )

    return query.get(user_id)


def find_users(user_ids: Set[UserID], *, party_id: PartyID=None) -> Set[UserTuple]:
    """Return the users and their current avatars' URLs with those IDs."""
    if not user_ids:
        return set()

    rows = db.session \
        .query(User.id, User.screen_name, User.deleted, Avatar) \
        .outerjoin(AvatarSelection) \
        .outerjoin(Avatar) \
        .filter(User.id.in_(frozenset(user_ids))) \
        .all()

    if party_id is not None:
        orga_id_rows = db.session \
            .query(OrgaTeamMembership.user_id) \
            .join(OrgaTeam) \
            .filter(OrgaTeam.party_id == party_id) \
            .filter(OrgaTeamMembership.user_id.in_(frozenset(user_ids))) \
            .group_by(OrgaTeamMembership.user_id) \
            .having(db.func.count(OrgaTeamMembership.user_id) > 0) \
            .all()
        orga_team_members = {row[0] for row in orga_id_rows}
    else:
        orga_team_members = frozenset()

    def to_tuples() -> Iterator[UserTuple]:
        for user_id, screen_name, is_deleted, avatar in rows:
            avatar_url = avatar.url if avatar else None
            is_orga = user_id in orga_team_members

            yield UserTuple(
                user_id,
                screen_name,
                is_deleted,
                avatar_url,
                is_orga
            )

    return set(to_tuples())


def find_user_by_screen_name(screen_name: str) -> Optional[User]:
    """Return the user with that screen name, or `None` if not found."""
    return User.query \
        .filter_by(screen_name=screen_name) \
        .one_or_none()


def get_anonymous_user() -> AnonymousUser:
    """Return the anonymous user."""
    return AnonymousUser()


def index_users_by_id(users: Set[UserTuple]) -> Dict[UserID, UserTuple]:
    """Map the users' IDs to the corresponding user objects."""
    return {user.id: user for user in users}


def is_screen_name_already_assigned(screen_name: str) -> bool:
    """Return `True` if a user with that screen name exists."""
    return _do_users_matching_filter_exist(User.screen_name, screen_name)


def is_email_address_already_assigned(email_address: str) -> bool:
    """Return `True` if a user with that email address exists."""
    return _do_users_matching_filter_exist(User.email_address, email_address)


def _do_users_matching_filter_exist(model_attribute: str, search_value: str) -> bool:
    """Return `True` if any users match the filter.

    Comparison is done case-insensitively.
    """
    user_count = User.query \
        .filter(db.func.lower(model_attribute) == search_value.lower()) \
        .count()
    return user_count > 0


class UserCreationFailed(Exception):
    pass


def create_user(screen_name: str, email_address: str, password: str,
                first_names: str, last_name: str, brand_id: BrandID,
                terms_version_id: TermsVersionID,
                subscribe_to_newsletter: bool) -> User:
    """Create a user account and related records."""
    # user with details
    user = build_user(screen_name, email_address)
    user.detail.first_names = first_names
    user.detail.last_name = last_name
    db.session.add(user)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error('User creation failed: %s', e)
        db.session.rollback()
        raise UserCreationFailed()

    # password
    password_service.create_password_hash(user.id, password)

    # roles
    board_user_role = authorization_service.find_role(RoleID('board_user'))
    authorization_service.assign_role_to_user(user.id, board_user_role.id)

    # consent to terms of service (required)
    terms_consent = terms_service.build_consent_on_account_creation(user.id,
                                                                    terms_version_id)
    db.session.add(terms_consent)
    db.session.commit()

    # newsletter subscription (optional)
    _create_newsletter_subscription(user.id, brand_id, subscribe_to_newsletter)

    # verification_token for email address confirmation
    verification_token = verification_token_service \
        .build_for_email_address_confirmation(user.id)
    db.session.add(verification_token)
    db.session.commit()

    send_email_address_confirmation_email(user, verification_token)

    return user


def build_user(screen_name: str, email_address: str) -> User:
    normalized_screen_name = _normalize_screen_name(screen_name)
    normalized_email_address = _normalize_email_address(email_address)

    user = User(normalized_screen_name, normalized_email_address)

    detail = UserDetail(user=user)

    return user


def _normalize_screen_name(screen_name: str) -> str:
    """Normalize the screen name, or raise an exception if invalid."""
    normalized = screen_name.strip()
    if not normalized or (' ' in normalized) or ('@' in normalized):
        raise ValueError('Invalid screen name: \'{}\''.format(screen_name))
    return normalized


def _normalize_email_address(email_address: str) -> str:
    """Normalize the e-mail address, or raise an exception if invalid."""
    normalized = email_address.strip()
    if not normalized or (' ' in normalized) or ('@' not in normalized):
        raise ValueError('Invalid email address: \'{}\''.format(email_address))
    return normalized


def _create_newsletter_subscription(user_id: UserID, brand_id: BrandID,
                                    subscribe_to_newsletter: bool) -> None:
    if subscribe_to_newsletter:
        newsletter_service.subscribe(user_id, brand_id)
    else:
        newsletter_service.unsubscribe(user_id, brand_id)


def send_email_address_confirmation_email(user: User, verification_token: Token
                                         ) -> None:
    confirmation_url = url_for('.confirm_email_address',
                               token=verification_token.token,
                               _external=True)

    subject = '{0.screen_name}, bitte bestätige deine E-Mail-Adresse'.format(user)
    body = (
        'Hallo {0.screen_name},\n\n'
        'bitte bestätige deine E-Mail-Adresse indem du diese URL abrufst: {1}'
    ).format(user, confirmation_url)
    recipients = [user.email_address]

    email_service.send_email(subject=subject, body=body, recipients=recipients)


def confirm_email_address(verification_token: Token) -> None:
    """Confirm the email address of the user assigned with that
    verification token.
    """
    user = verification_token.user

    user.enabled = True
    db.session.delete(verification_token)
    db.session.commit()


def update_user_details(user: User, first_names: str, last_name: str,
                        date_of_birth: date, country: str, zip_code, city: str,
                        street: str, phone_number: str) -> None:
    """Update the user's details."""
    user.detail.first_names = first_names
    user.detail.last_name = last_name
    user.detail.date_of_birth = date_of_birth
    user.detail.country = country
    user.detail.zip_code = zip_code
    user.detail.city = city
    user.detail.street = street
    user.detail.phone_number = phone_number

    db.session.commit()
