# -*- coding: utf-8 -*-

"""
byceps.blueprints.shop_order_admin.views
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2006-2016 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

from datetime import datetime
from itertools import chain

from flask import abort, current_app, g, render_template, request, Response, \
    url_for

from ...services.party import service as party_service
from ...services.shop.order.models import PaymentState
from ...services.shop.order import service as order_service
from ...services.shop.sequence import service as sequence_service
from ...util.framework.blueprint import create_blueprint
from ...util.framework.flash import flash_error, flash_success
from ...util.money import to_two_places
from ...util.templating import templated
from ...util.views import redirect_to, respond_no_content_with_location

from ..authorization.decorators import permission_required
from ..authorization.registry import permission_registry
from ..shop_order.signals import order_canceled, order_paid

from .authorization import ShopOrderPermission
from .forms import CancelForm


blueprint = create_blueprint('shop_order_admin', __name__)


permission_registry.register_enum(ShopOrderPermission)


@blueprint.route('/parties/<party_id>', defaults={'page': 1})
@blueprint.route('/parties/<party_id>/pages/<int:page>')
@permission_required(ShopOrderPermission.list)
@templated
def index_for_party(party_id, page):
    """List orders for that party."""
    party = _get_party_or_404(party_id)

    order_number_prefix = sequence_service.get_order_number_prefix(party.id)

    per_page = request.args.get('per_page', type=int, default=15)
    only = request.args.get('only', type=PaymentState.__getitem__)

    orders = order_service \
        .get_orders_for_party_paginated(party.id, page, per_page,
                                        only_payment_state=only)

    return {
        'party': party,
        'order_number_prefix': order_number_prefix,
        'PaymentState': PaymentState,
        'only': only,
        'orders': orders,
    }


@blueprint.route('/<uuid:order_id>')
@permission_required(ShopOrderPermission.view)
@templated
def view(order_id):
    """Show a single order."""
    order = order_service.find_order_with_details(order_id)
    if order is None:
        abort(404)

    updates = _get_updates(order)

    return {
        'order': order,
        'updates': updates,
        'PaymentState': PaymentState,
    }


def _get_updates(order):
    return chain(
        _get_invoice_updates(order),
        _get_payment_updates(order),
        _get_shipment_updates(order)
    )


def _get_invoice_updates(order):
    if order.invoice_created_at:
        yield {
            'event': 'invoice_created',
            'created_at': order.invoice_created_at,
        }


def _get_payment_updates(order):
    updates = order_service.get_updates_for_order(order.order_number)

    for update in updates:
        update.event = 'payment_updated'

    yield from updates


def _get_shipment_updates(order):
    if order.shipped_at:
        yield {
            'event': 'shipped',
            'created_at': order.shipped_at,
        }


@blueprint.route('/<uuid:order_id>/export')
@permission_required(ShopOrderPermission.view)
def export(order_id):
    """Export the order as an XML document."""
    order = order_service.find_order_with_details(order_id)
    if order is None:
        abort(404)

    now = datetime.now()

    context = {
        'order': order,
        'now': now,
        'format_export_amount': _format_export_amount,
        'format_export_datetime': _format_export_datetime,
    }

    xml = render_template('shop_order_admin/export.xml', **context)

    return Response(xml, content_type='application/xml; charset=iso-8859-1')


def _format_export_amount(amount):
    """Format the monetary amount as required by the export format
    specification.
    """
    quantized = to_two_places(amount)
    return '{:.2f}'.format(quantized)


def _format_export_datetime(dt):
    """Format date and time as required by the export format specification."""
    timezone = current_app.config['SHOP_ORDER_EXPORT_TIMEZONE']
    localized_dt = timezone.localize(dt)

    date_time, utc_offset = localized_dt.strftime('%Y-%m-%dT%H:%M:%S|%z') \
                                        .split('|', 1)

    if len(utc_offset) == 5:
        # Insert colon between hours and minutes.
        utc_offset = utc_offset[:3] + ':' + utc_offset[3:]

    return date_time + utc_offset


@blueprint.route('/<uuid:order_id>/flags/invoiced', methods=['POST'])
@permission_required(ShopOrderPermission.update)
@respond_no_content_with_location
def flag_invoiced(order_id):
    """Flag the order as invoiced."""
    order = _get_order_or_404(order_id)

    order_service.record_invoice_creation(order)

    flash_success(
        'Bestellung {} wurde als in Rechnung gestellt markiert.',
        order.order_number)

    return url_for('.view', order_id=order.id)


@blueprint.route('/<uuid:order_id>/flags/invoiced', methods=['DELETE'])
@permission_required(ShopOrderPermission.update)
@respond_no_content_with_location
def unflag_invoiced(order_id):
    """Unflag the order as invoiced."""
    order = _get_order_or_404(order_id)

    order_service.withdraw_invoice_creation(order)

    flash_success(
        'Bestellung {} wurde als nicht in Rechnung gestellt markiert.',
        order.order_number)

    return url_for('.view', order_id=order.id)


@blueprint.route('/<uuid:order_id>/flags/shipped', methods=['POST'])
@permission_required(ShopOrderPermission.update)
@respond_no_content_with_location
def set_shipped_flag(order_id):
    """Mark the order as shipped."""
    order = _get_order_or_404(order_id)

    order_service.set_shipped_flag(order)

    flash_success('Bestellung {} wurde als verschickt markiert.',
                  order.order_number)

    return url_for('.view', order_id=order.id)


@blueprint.route('/<uuid:order_id>/flags/shipped', methods=['DELETE'])
@permission_required(ShopOrderPermission.update)
@respond_no_content_with_location
def unset_shipped_flag(order_id):
    """Mark the order as not shipped."""
    order = _get_order_or_404(order_id)

    order_service.unset_shipped_flag(order)

    flash_success('Bestellung {} wurde als nicht verschickt markiert.',
                  order.order_number)

    return url_for('.view', order_id=order.id)


@blueprint.route('/<uuid:order_id>/cancel')
@permission_required(ShopOrderPermission.update)
@templated
def cancel_form(order_id, erroneous_form=None):
    """Show form to cancel an order."""
    order = _get_order_or_404(order_id)

    cancel_form = erroneous_form if erroneous_form else CancelForm()

    if order.payment_state == PaymentState.canceled:
        flash_error(
            'Die Bestellung ist bereits storniert worden; '
            'der Bezahlstatus kann nicht mehr geändert werden.')
        return redirect_to('.view', order_id=order.id)

    return {
        'order': order,
        'cancel_form': cancel_form,
    }


@blueprint.route('/<uuid:order_id>/cancel', methods=['POST'])
@permission_required(ShopOrderPermission.update)
def cancel(order_id):
    """Set the payment status of a single order to 'canceled' and
    release the respective article quantities.
    """
    order = _get_order_or_404(order_id)

    form = CancelForm(request.form)
    if not form.validate():
        return cancel_form(order_id, form)

    reason = form.reason.data.strip()

    try:
        order_service.cancel_order(order, g.current_user.id, reason)
    except order_service.OrderAlreadyCanceled:
        flash_error(
            'Die Bestellung ist bereits storniert worden; '
            'der Bezahlstatus kann nicht mehr geändert werden.')
        return redirect_to('.view', order_id=order.id)

    flash_success(
        'Die Bestellung wurde als storniert markiert und die betroffenen '
        'Artikel in den entsprechenden Stückzahlen wieder zur Bestellung '
        'freigegeben.')

    order_canceled.send(None, order=order)

    return redirect_to('.view', order_id=order.id)


@blueprint.route('/<uuid:order_id>/mark_as_paid')
@permission_required(ShopOrderPermission.update)
@templated
def mark_as_paid_form(order_id):
    """Show form to mark an order as paid."""
    order = _get_order_or_404(order_id)

    if order.payment_state == PaymentState.paid:
        flash_error('Die Bestellung ist bereits als bezahlt markiert worden.')
        return redirect_to('.view', order_id=order.id)

    return {
        'order': order,
    }


@blueprint.route('/<uuid:order_id>/mark_as_paid', methods=['POST'])
@permission_required(ShopOrderPermission.update)
def mark_as_paid(order_id):
    """Set the payment status of a single order to 'paid'."""
    order = _get_order_or_404(order_id)

    try:
        order_service.mark_order_as_paid(order, g.current_user.id)
    except order_service.OrderAlreadyMarkedAsPaid:
        flash_error('Die Bestellung ist bereits als bezahlt markiert worden.')
        return redirect_to('.view', order_id=order.id)

    flash_success('Die Bestellung wurde als bezahlt markiert.')

    order_paid.send(None, order=order)

    return redirect_to('.view', order_id=order.id)


def _get_party_or_404(party_id):
    party = party_service.find_party(party_id)

    if party is None:
        abort(404)

    return party


def _get_order_or_404(order_id):
    order = order_service.find_order(order_id)

    if order is None:
        abort(404)

    return order
