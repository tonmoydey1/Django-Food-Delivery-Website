import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import escape
from django.utils import timezone

from .models import Order


logger = logging.getLogger(__name__)


def send_order_confirmation_email(order, request=None):
    subject = f'Your Tonmoy Eats order {order.tracking_code} has been placed'
    context = {'order': order, 'tracking_url': absolute_tracking_url(order, request)}
    text_body = render_to_string('emails/order_confirmation.txt', context)
    html_body = render_to_string('emails/order_confirmation.html', context)
    email = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [order.email])
    email.attach_alternative(html_body, 'text/html')
    email.attach(
        invoice_filename(order),
        render_invoice_pdf(order),
        'application/pdf',
    )
    return send_email_safely(email)


def send_login_otp_email(user, otp_code):
    if not user.email:
        return False
    subject = 'Your Tonmoy Eats login OTP'
    text_body = (
        f'Hi {user.first_name or user.username},\n\n'
        f'Your Tonmoy Eats login OTP is: {otp_code}\n\n'
        'This OTP is valid for 10 minutes. If you did not request this, you can ignore this email.'
    )
    html_body = (
        '<div style="font-family: Arial, sans-serif; color: #1c1c1c;">'
        '<h2 style="color: #e23744;">Tonmoy Eats login OTP</h2>'
        f'<p>Hi {user.first_name or user.username},</p>'
        '<p>Use this OTP to login to your Tonmoy Eats account:</p>'
        f'<p style="font-size: 28px; font-weight: 800; letter-spacing: 4px;">{otp_code}</p>'
        '<p>This OTP is valid for 10 minutes.</p>'
        '</div>'
    )
    email = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [user.email])
    email.attach_alternative(html_body, 'text/html')
    return send_email_safely(email)


def send_register_otp_email(email_address, name, otp_code):
    subject = 'Verify your Tonmoy Eats account'
    display_name = name or 'there'
    text_body = (
        f'Hi {display_name},\n\n'
        f'Your Tonmoy Eats registration OTP is: {otp_code}\n\n'
        'This OTP is valid for 10 minutes. Enter it on the register page to create your account.'
    )
    html_body = (
        '<div style="font-family: Arial, sans-serif; color: #1c1c1c;">'
        '<h2 style="color: #e23744;">Verify your Tonmoy Eats account</h2>'
        f'<p>Hi {display_name},</p>'
        '<p>Use this OTP to finish creating your Tonmoy Eats account:</p>'
        f'<p style="font-size: 28px; font-weight: 800; letter-spacing: 4px;">{otp_code}</p>'
        '<p>This OTP is valid for 10 minutes.</p>'
        '</div>'
    )
    email = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [email_address])
    email.attach_alternative(html_body, 'text/html')
    return send_email_safely(email)


def send_username_reminder_email(email_address, users):
    usernames = [user.username for user in users]
    if not usernames:
        return True

    subject = 'Your Tonmoy Eats username reminder'
    joined_usernames = '\n'.join(f'- {username}' for username in usernames)
    html_usernames = ''.join(f'<li>{escape(username)}</li>' for username in usernames)
    text_body = (
        'Hi,\n\n'
        'You asked us to remind you of the Tonmoy Eats username linked to this email address.\n\n'
        f'{joined_usernames}\n\n'
        'You can now return to the login page and continue with password + OTP login.\n\n'
        'If you did not request this, you can ignore this email.'
    )
    html_body = (
        '<div style="font-family: Arial, sans-serif; color: #1c1c1c;">'
        '<h2 style="color: #e23744;">Tonmoy Eats username reminder</h2>'
        '<p>You asked us to remind you of the username linked to this email address.</p>'
        f'<ul style="font-size: 18px; font-weight: 800;">{html_usernames}</ul>'
        '<p>You can now return to the login page and continue with password + OTP login.</p>'
        '<p>If you did not request this, you can ignore this email.</p>'
        '</div>'
    )
    email = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [email_address])
    email.attach_alternative(html_body, 'text/html')
    return send_email_safely(email)


def send_order_status_email(order, request=None):
    subject = f'Order {order.tracking_code}: {order.get_status_display()}'
    context = {'order': order, 'tracking_url': absolute_tracking_url(order, request)}
    text_body = render_to_string('emails/order_status.txt', context)
    email = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [order.email])
    return send_email_safely(email)


def send_email_safely(email):
    try:
        sent = email.send(fail_silently=False)
    except Exception:
        logger.exception('Email could not be sent to %s', ', '.join(email.to))
        return False
    if sent and settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
        logger.warning('Console email backend is active; email was printed in the terminal instead of sent to inbox.')
        return False
    return sent > 0


def absolute_tracking_url(order, request=None):
    path = reverse('order_tracking', kwargs={'tracking_code': order.tracking_code})
    if request:
        return request.build_absolute_uri(path)
    if settings.SITE_URL:
        return f'{settings.SITE_URL}{path}'
    return path


def tracking_payload(order):
    steps = [
        Order.STATUS_PLACED,
        Order.STATUS_CONFIRMED,
        Order.STATUS_PREPARING,
        Order.STATUS_OUT_FOR_DELIVERY,
        Order.STATUS_DELIVERED,
    ]
    status = order.status
    if order.status not in [Order.STATUS_CANCELLED, Order.STATUS_DELIVERED]:
        elapsed_minutes = (timezone.now() - order.created_at).total_seconds() / 60
        if elapsed_minutes >= 18:
            status = Order.STATUS_DELIVERED
        elif elapsed_minutes >= 10:
            status = Order.STATUS_OUT_FOR_DELIVERY
        elif elapsed_minutes >= 5:
            status = Order.STATUS_PREPARING
        elif elapsed_minutes >= 2:
            status = Order.STATUS_CONFIRMED

    active_index = steps.index(status) if status in steps else 0
    progress = int((active_index / (len(steps) - 1)) * 100)
    return {
        'tracking_code': order.tracking_code,
        'status': status,
        'status_label': dict(Order.STATUS_CHOICES).get(status, status.title()),
        'progress': progress,
        'steps': [
            {
                'key': step,
                'label': dict(Order.STATUS_CHOICES).get(step),
                'complete': index <= active_index,
            }
            for index, step in enumerate(steps)
        ],
        'courier': {
            'name': 'Aman Verma',
            'phone': '+91 90000 12345',
            'lat': str(Decimal('22.5726') + (Decimal(progress) / Decimal('10000'))),
            'lng': str(Decimal('88.3639') + (Decimal(progress) / Decimal('10000'))),
        },
    }


def render_invoice_pdf(order):
    return build_invoice_pdf(order)


def invoice_filename(order):
    return f'tonmoy-eats-invoice-{order.tracking_code}.pdf'


def build_invoice_pdf(order):
    items = list(order.items.all())
    pages = []
    chunk_size = 6
    chunks = [items[index:index + chunk_size] for index in range(0, len(items), chunk_size)] or [[]]
    total_pages = len(chunks)
    for page_index, chunk in enumerate(chunks):
        pages.append(invoice_page_commands(order, chunk, page_index + 1, total_pages, page_index == total_pages - 1))
    return build_pdf(pages)


def invoice_page_commands(order, items, page_number, total_pages, include_totals):
    commands = []
    page_w = 612
    page_h = 842
    margin = 34
    panel_x = 34
    panel_y = 34
    panel_w = 544
    panel_h = 774

    rect(commands, 0, 0, page_w, page_h, '#fff7f8')
    rect(commands, panel_x, panel_y, panel_w, panel_h, '#ffffff')
    rect(commands, panel_x, 700, panel_w, 108, '#e23744')
    rect(commands, panel_x, 700, panel_w, 8, '#ffc107')
    rect(commands, 52, 731, 52, 52, '#1c1c1c')
    text(commands, 'T', 67, 748, 30, 'F2', '#ffffff')
    text(commands, 'Tonmoy Eats', 118, 764, 24, 'F2', '#ffffff')
    text(commands, 'Assam premium food delivery', 118, 744, 10, 'F1', '#ffe7e9')
    text(commands, 'INVOICE', 465, 764, 20, 'F2', '#ffffff')
    text_right(commands, f'Order {order.tracking_code}', 558, 744, 10, 'F1', '#ffe7e9')
    text_right(commands, f'Page {page_number} of {total_pages}', 558, 728, 9, 'F1', '#ffe7e9')

    invoice_date = timezone.localtime(order.created_at).strftime('%d %b %Y, %I:%M %p')
    card(commands, 52, 586, 246, 86)
    text(commands, 'Bill to', 68, 650, 9, 'F2', '#e23744')
    text(commands, order.customer_name or 'Guest customer', 68, 631, 14, 'F2', '#1c1c1c')
    wrapped_text(commands, order.email, 68, 614, 30, 9, 'F1', '#696969')
    wrapped_text(commands, order.phone, 68, 600, 30, 9, 'F1', '#696969')

    card(commands, 314, 586, 244, 86)
    text(commands, 'Deliver to', 330, 650, 9, 'F2', '#e23744')
    wrapped_text(commands, order.address, 330, 631, 34, 10, 'F2', '#1c1c1c')
    wrapped_text(commands, f'{order.city} {order.postcode}'.strip(), 330, 602, 34, 9, 'F1', '#696969')

    card(commands, 52, 508, 246, 58)
    text(commands, 'Restaurant', 68, 544, 9, 'F2', '#e23744')
    wrapped_text(commands, order.restaurant.name, 68, 526, 31, 12, 'F2', '#1c1c1c')
    wrapped_text(commands, order.restaurant.address, 68, 510, 35, 8, 'F1', '#696969')

    card(commands, 314, 508, 244, 58)
    text(commands, 'Payment', 330, 544, 9, 'F2', '#e23744')
    payment_color = '#267e3e' if order.is_paid else '#f4b400'
    if order.payment_status == Order.PAYMENT_FAILED:
        payment_color = '#d32f2f'
    pill(commands, 330, 520, 82, 22, payment_color)
    text(commands, order.get_payment_status_display(), 342, 526, 9, 'F2', '#ffffff')
    text(commands, order.get_payment_method_display(), 424, 526, 10, 'F1', '#4f4f4f')
    text_right(commands, invoice_date, 544, 526, 8, 'F1', '#696969')

    table_top = 470
    rect(commands, 52, table_top, 506, 30, '#1c1c1c')
    text(commands, 'Item', 68, table_top + 10, 10, 'F2', '#ffffff')
    text(commands, 'Qty', 330, table_top + 10, 10, 'F2', '#ffffff')
    text(commands, 'Rate', 388, table_top + 10, 10, 'F2', '#ffffff')
    text_right(commands, 'Amount', 542, table_top + 10, 10, 'F2', '#ffffff')

    y = table_top - 34
    for index, item in enumerate(items):
        if index % 2 == 0:
            rect(commands, 52, y - 10, 506, 32, '#fff7f8')
        text(commands, truncate(item.name, 38), 68, y, 10, 'F2', '#1c1c1c')
        text(commands, str(item.quantity), 336, y, 10, 'F1', '#4f4f4f')
        text_right(commands, money(item.price), 455, y, 10, 'F1', '#4f4f4f')
        text_right(commands, money(item.line_total), 542, y, 10, 'F2', '#1c1c1c')
        line(commands, 52, y - 15, 558, y - 15, '#eeeeee', 0.8)
        y -= 36

    if not include_totals:
        text(commands, 'Continued on next page', 52, 92, 10, 'F2', '#e23744')
        return commands

    totals_y = 86
    card(commands, 342, totals_y, 216, 140)
    summary_line(commands, 'Subtotal', order.subtotal, 360, totals_y + 110, 540)
    summary_line(commands, 'Delivery', order.delivery_fee, 360, totals_y + 88, 540)
    summary_line(commands, 'Tax', order.tax, 360, totals_y + 66, 540)
    summary_line(commands, 'Discount', order.discount, 360, totals_y + 44, 540)
    line(commands, 358, totals_y + 34, 542, totals_y + 34, '#ececec', 1)
    text(commands, 'Total', 360, totals_y + 14, 13, 'F2', '#1c1c1c')
    text_right(commands, money(order.total), 540, totals_y + 14, 14, 'F2', '#e23744')

    text(commands, 'Thank you for ordering with Tonmoy Eats.', 52, 184, 14, 'F2', '#1c1c1c')
    wrapped_text(
        commands,
        'Your invoice is ready for records. Track this order any time using your tracking code.',
        52,
        164,
        50,
        10,
        'F1',
        '#696969',
    )
    rect(commands, 52, 82, 246, 64, '#1c1c1c')
    text(commands, 'Tracking code', 68, 122, 9, 'F1', '#d8d8d8')
    text(commands, order.tracking_code, 68, 100, 18, 'F2', '#ffffff')
    rect(commands, 250, 96, 24, 24, '#ffc107')
    text(commands, 'TE', 254, 104, 9, 'F2', '#1c1c1c')
    return commands


def card(commands, x, y, w, h):
    rect(commands, x, y, w, h, '#ffffff')
    line(commands, x, y, x + w, y, '#eeeeee', 1)
    line(commands, x, y + h, x + w, y + h, '#eeeeee', 1)
    line(commands, x, y, x, y + h, '#eeeeee', 1)
    line(commands, x + w, y, x + w, y + h, '#eeeeee', 1)


def pill(commands, x, y, w, h, color):
    rect(commands, x, y, w, h, color)


def summary_line(commands, label, amount, x, y, right_x):
    text(commands, label, x, y, 10, 'F1', '#696969')
    text_right(commands, money(amount), right_x, y, 10, 'F2', '#1c1c1c')


def rect(commands, x, y, w, h, fill):
    r, g, b = rgb(fill)
    commands.append(f'{r} {g} {b} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f')


def line(commands, x1, y1, x2, y2, color, width=1):
    r, g, b = rgb(color)
    commands.append(f'{width:.2f} w {r} {g} {b} RG {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S')


def text(commands, value, x, y, size=10, font='F1', color='#1c1c1c'):
    r, g, b = rgb(color)
    commands.append(
        f'BT /{font} {size:.2f} Tf {r} {g} {b} rg 1 0 0 1 {x:.2f} {y:.2f} Tm ({pdf_escape(value)}) Tj ET'
    )


def text_right(commands, value, right_x, y, size=10, font='F1', color='#1c1c1c'):
    value = str(value)
    x = right_x - approximate_text_width(value, size)
    text(commands, value, x, y, size, font, color)


def wrapped_text(commands, value, x, y, width_chars, size=10, font='F1', color='#1c1c1c', line_gap=12, max_lines=2):
    lines = wrap_words(value, width_chars)[:max_lines]
    for index, line_text in enumerate(lines):
        text(commands, line_text, x, y - (index * line_gap), size, font, color)


def wrap_words(value, width_chars):
    words = str(value or '').split()
    if not words:
        return ['']
    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if len(candidate) <= width_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def truncate(value, max_chars):
    value = str(value or '')
    if len(value) <= max_chars:
        return value
    return f'{value[:max_chars - 3]}...'


def money(value):
    return f'Rs. {Decimal(value):,.2f}'


def approximate_text_width(value, size):
    return len(str(value)) * size * 0.52


def rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    red = int(hex_color[0:2], 16) / 255
    green = int(hex_color[2:4], 16) / 255
    blue = int(hex_color[4:6], 16) / 255
    return f'{red:.3f}', f'{green:.3f}', f'{blue:.3f}'


def build_pdf(pages):
    page_count = len(pages)
    font_object_id = 3 + (page_count * 2)
    objects = [
        b'1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n',
        f'2 0 obj << /Type /Pages /Kids [{" ".join(f"{3 + index * 2} 0 R" for index in range(page_count))}] /Count {page_count} >> endobj\n'.encode(),
    ]
    for index, commands in enumerate(pages):
        page_object_id = 3 + index * 2
        content_object_id = page_object_id + 1
        stream = '\n'.join(commands).encode('latin-1', errors='replace')
        resources = (
            f'/Resources << /Font << /F1 {font_object_id} 0 R /F2 {font_object_id + 1} 0 R '
            f'/F3 {font_object_id + 2} 0 R >> >>'
        )
        objects.append(
            f'{page_object_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] {resources} /Contents {content_object_id} 0 R >> endobj\n'.encode()
        )
        objects.append(
            f'{content_object_id} 0 obj << /Length {len(stream)} >> stream\n'.encode()
            + stream
            + b'\nendstream endobj\n'
        )
    objects.extend([
        f'{font_object_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n'.encode(),
        f'{font_object_id + 1} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n'.encode(),
        f'{font_object_id + 2} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >> endobj\n'.encode(),
    ])

    pdf = b'%PDF-1.4\n'
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj
    xref_start = len(pdf)
    pdf += f'xref\n0 {len(objects) + 1}\n'.encode()
    pdf += b'0000000000 65535 f \n'
    for offset in offsets[1:]:
        pdf += f'{offset:010d} 00000 n \n'.encode()
    pdf += f'trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF'.encode()
    return pdf


def pdf_escape(text):
    return str(text).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)').replace('\r', ' ').replace('\n', ' ')
