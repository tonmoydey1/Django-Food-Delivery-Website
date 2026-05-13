from decimal import Decimal, ROUND_HALF_UP

from .models import MenuItem, Restaurant

CART_SESSION_ID = 'taste_trail_cart'
TAX_RATE = Decimal('0.05')


class CartRestaurantMismatch(Exception):
    pass


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.user = getattr(request, 'user', None)
        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {'restaurant_id': None, 'items': {}}
        self.cart = cart

    def add(self, item, quantity=1, override_quantity=False, replace=False):
        quantity = max(1, int(quantity))
        current_restaurant_id = self.cart.get('restaurant_id')
        if current_restaurant_id and current_restaurant_id != item.restaurant_id:
            if not replace:
                raise CartRestaurantMismatch
            self.clear()

        self.cart['restaurant_id'] = item.restaurant_id
        item_id = str(item.id)
        current = self.cart['items'].get(item_id, {'quantity': 0})
        current['quantity'] = quantity if override_quantity else current['quantity'] + quantity
        self.cart['items'][item_id] = current
        self.save()

    def update(self, item_id, quantity):
        item_id = str(item_id)
        if item_id in self.cart['items']:
            quantity = int(quantity)
            if quantity <= 0:
                self.remove(item_id)
            else:
                self.cart['items'][item_id]['quantity'] = quantity
                self.save()

    def remove(self, item_id):
        item_id = str(item_id)
        if item_id in self.cart['items']:
            del self.cart['items'][item_id]
            if not self.cart['items']:
                self.cart['restaurant_id'] = None
            self.save()

    def clear(self):
        self.session[CART_SESSION_ID] = {'restaurant_id': None, 'items': {}}
        self.cart = self.session[CART_SESSION_ID]
        self.save()

    def save(self):
        self.session.modified = True

    @property
    def restaurant(self):
        restaurant_id = self.cart.get('restaurant_id')
        if not restaurant_id:
            return None
        return Restaurant.objects.filter(id=restaurant_id).first()

    @property
    def count(self):
        return sum(item['quantity'] for item in self.cart['items'].values())

    def __len__(self):
        return self.count

    def items(self):
        item_ids = self.cart['items'].keys()
        menu_items = MenuItem.objects.select_related('restaurant', 'category').filter(id__in=item_ids)
        item_map = {str(item.id): item for item in menu_items}
        rows = []
        for item_id, data in self.cart['items'].items():
            item = item_map.get(item_id)
            if not item:
                continue
            quantity = int(data['quantity'])
            line_total = item.price * quantity
            rows.append({
                'item': item,
                'quantity': quantity,
                'line_total': money(line_total),
            })
        return rows

    @property
    def subtotal(self):
        return money(sum(row['line_total'] for row in self.items()))

    @property
    def delivery_fee(self):
        restaurant = self.restaurant
        if not restaurant or not self.count:
            return Decimal('0.00')
        if self.premium_active:
            return Decimal('0.00')
        return money(restaurant.delivery_fee)

    @property
    def discount(self):
        if not self.premium_active:
            return Decimal('0.00')
        return money(self.subtotal * self.premium_discount_rate)

    @property
    def tax(self):
        taxable_amount = max(self.subtotal - self.discount, Decimal('0.00'))
        return money(taxable_amount * TAX_RATE)

    @property
    def total(self):
        return money(self.subtotal - self.discount + self.delivery_fee + self.tax)

    @property
    def premium_active(self):
        if not self.user or not getattr(self.user, 'is_authenticated', False):
            return False
        try:
            return self.user.profile.premium_active
        except AttributeError:
            return False

    @property
    def premium_discount_rate(self):
        if not self.premium_active:
            return Decimal('0.00')
        try:
            return self.user.profile.premium_discount_rate
        except AttributeError:
            return Decimal('0.00')

    @property
    def premium_discount_percent(self):
        return int(self.premium_discount_rate * 100)

    @property
    def premium_savings(self):
        restaurant = self.restaurant
        free_delivery = restaurant.delivery_fee if restaurant and self.count and self.premium_active else Decimal('0.00')
        return money(self.discount + free_delivery)

    def as_dict(self):
        return {
            'count': self.count,
            'subtotal': currency(self.subtotal),
            'delivery_fee': currency(self.delivery_fee),
            'discount': currency(self.discount),
            'tax': currency(self.tax),
            'total': currency(self.total),
            'premium_active': self.premium_active,
            'premium_savings': currency(self.premium_savings),
            'premium_discount_percent': self.premium_discount_percent,
            'restaurant': self.restaurant.name if self.restaurant else '',
            'items': [
                {
                    'id': row['item'].id,
                    'name': row['item'].name,
                    'quantity': row['quantity'],
                    'line_total': currency(row['line_total']),
                    'price': currency(row['item'].price),
                }
                for row in self.items()
            ],
        }


def money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def currency(value):
    return f'{money(value):.2f}'
