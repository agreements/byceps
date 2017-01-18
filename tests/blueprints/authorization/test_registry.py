# -*- coding: utf-8 -*-

"""
:Copyright: 2006-2017 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

from nose2.tools import params

from byceps.blueprints.authorization.registry import PermissionRegistry
from byceps.util.authorization import create_permission_enum


ItemPermission = create_permission_enum('item', ['view', 'create', 'update'])


@params(
    ('item.create'   , ItemPermission.create),  # enum member exists
    ('item.delete'   , None                 ),  # enum exists, but member does not
    ('article.create', None                 ),  # enum does not exist
)
def test_get_enum_member(permission_id, expected):
    registry = create_registry_with_registered_enum()

    assert registry.get_enum_member(permission_id) == expected


@params(
    ({'item.create', 'item.create'   }, {ItemPermission.create                       }),  # duplicates are ignored
    ({'item.create', 'item.update'   }, {ItemPermission.create, ItemPermission.update}),  # multiple different enums are returned
    ({'item.create', 'article.create'}, {ItemPermission.create                       }),  # unknown IDs are ignored
    ({'article.create'               }, frozenset()                                   ),  # unknown IDs are ignored
)
def test_get_enum_members(permission_ids, expected):
    registry = create_registry_with_registered_enum()

    assert registry.get_enum_members(permission_ids) == expected


def create_registry_with_registered_enum():
    registry = PermissionRegistry()
    registry.register_enum(ItemPermission)
    return registry
