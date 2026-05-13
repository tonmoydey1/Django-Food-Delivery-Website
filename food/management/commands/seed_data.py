from datetime import time
from decimal import Decimal

from django.core.management.base import BaseCommand

from food.models import Category, MenuItem, Restaurant


class Command(BaseCommand):
    help = 'Create sample restaurants, categories, and menu items.'

    def handle(self, *args, **options):
        categories = {
            'Burgers': {
                'icon': 'Burger',
                'description': 'Stacked, grilled, and sauced classics.',
                'image_url': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=600&q=80',
            },
            'Pizza': {
                'icon': 'Pizza',
                'description': 'Oven-fired pies and slices.',
                'image_url': 'https://images.unsplash.com/photo-1604382354936-07c5d9983bd3?auto=format&fit=crop&w=600&q=80',
            },
            'Indian': {
                'icon': 'Curry',
                'description': 'Curries, biryani, tandoor, and breads.',
                'image_url': 'https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=600&q=80',
            },
            'Sushi': {
                'icon': 'Sushi',
                'description': 'Rolls, bowls, and fresh seafood.',
                'image_url': 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?auto=format&fit=crop&w=600&q=80',
            },
            'Healthy': {
                'icon': 'Leaf',
                'description': 'Bowls, salads, and balanced meals.',
                'image_url': 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80',
            },
            'Dessert': {
                'icon': 'Sweet',
                'description': 'Cakes, ice cream, and baked treats.',
                'image_url': 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?auto=format&fit=crop&w=600&q=80',
            },
            'Drinks': {
                'icon': 'Drink',
                'description': 'Coffee, coolers, and smoothies.',
                'image_url': 'https://images.unsplash.com/photo-1505252585461-04db1eb84625?auto=format&fit=crop&w=600&q=80',
            },
            'Breakfast': {
                'icon': 'Brunch',
                'description': 'Morning plates and all-day brunch.',
                'image_url': 'https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=600&q=80',
            },
        }
        category_objects = {}
        for name, data in categories.items():
            category, _ = Category.objects.update_or_create(
                name=name,
                defaults={
                    'description': data['description'],
                    'icon': data['icon'],
                    'image_url': data['image_url'],
                },
            )
            category_objects[name] = category

        restaurants = [
            {
                'name': 'Firehouse Burgers',
                'tagline': 'Smash burgers, loaded fries, thick shakes.',
                'description': 'A fast casual burger kitchen with charred patties, house pickles, and crisp fries.',
                'cuisine': 'American',
                'city': 'Assam',
                'address': '18 GS Road, Guwahati',
                'phone': '+91 90000 11111',
                'opening_time': time(10, 0),
                'closing_time': time(23, 30),
                'rating': Decimal('4.7'),
                'delivery_time': 28,
                'delivery_fee': Decimal('49.00'),
                'minimum_order': Decimal('299.00'),
                'cover_image': 'https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=1200&q=80',
                'logo_image': 'https://images.unsplash.com/photo-1586816001966-79b736744398?auto=format&fit=crop&w=400&q=80',
                'is_featured': True,
                'items': [
                    ('Burgers', 'Classic Smash Burger', 'Double patty, cheddar, onions, pickles, house sauce.', '329.00', 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80', 720, 'Best seller'),
                    ('Burgers', 'Hot Honey Chicken Burger', 'Crispy chicken, hot honey glaze, slaw, brioche bun.', '359.00', 'https://images.unsplash.com/photo-1606755962773-d324e2dabd94?auto=format&fit=crop&w=900&q=80', 650, 'Spicy'),
                    ('Drinks', 'Vanilla Bean Shake', 'Creamy vanilla shake with whipped cream.', '179.00', 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&w=900&q=80', 420, 'Cold'),
                ],
            },
            {
                'name': 'Naan Stop Curry',
                'tagline': 'Comfort curries, biryani, and tandoor breads.',
                'description': 'Fresh spice blends, slow cooked gravies, and rice bowls packed for delivery.',
                'cuisine': 'Indian',
                'city': 'Assam',
                'address': '7 Fancy Bazar, Guwahati',
                'phone': '+91 90000 22222',
                'opening_time': time(9, 30),
                'closing_time': time(23, 0),
                'rating': Decimal('4.8'),
                'delivery_time': 34,
                'delivery_fee': Decimal('39.00'),
                'minimum_order': Decimal('249.00'),
                'cover_image': 'https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=1200&q=80',
                'logo_image': 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=400&q=80',
                'is_featured': True,
                'items': [
                    ('Indian', 'Butter Chicken Bowl', 'Creamy tomato gravy, grilled chicken, basmati rice.', '389.00', 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=900&q=80', 760, 'Best seller'),
                    ('Indian', 'Paneer Tikka Masala', 'Charred paneer, rich masala sauce, coriander.', '349.00', 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=900&q=80', 690, 'Vegetarian'),
                    ('Indian', 'Garlic Naan Basket', 'Three soft naan breads with garlic butter.', '149.00', 'https://images.unsplash.com/photo-1626074353765-517a681e40be?auto=format&fit=crop&w=900&q=80', 360, 'Shareable'),
                ],
            },
            {
                'name': 'Slice Society',
                'tagline': 'Wood-fired pizzas with bright seasonal toppings.',
                'description': 'Hand-stretched dough, blistered crusts, and fresh sauces fired hot.',
                'cuisine': 'Italian',
                'city': 'Assam',
                'address': '29 Zoo Road, Guwahati',
                'phone': '+91 90000 33333',
                'opening_time': time(11, 0),
                'closing_time': time(23, 45),
                'rating': Decimal('4.6'),
                'delivery_time': 31,
                'delivery_fee': Decimal('59.00'),
                'minimum_order': Decimal('399.00'),
                'cover_image': 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=1200&q=80',
                'logo_image': 'https://images.unsplash.com/photo-1601924582970-9238bcb495d9?auto=format&fit=crop&w=400&q=80',
                'is_featured': False,
                'items': [
                    ('Pizza', 'Margherita DOP', 'Tomato, mozzarella, basil, olive oil.', '429.00', 'https://images.unsplash.com/photo-1604382354936-07c5d9983bd3?auto=format&fit=crop&w=900&q=80', 820, 'Vegetarian'),
                    ('Pizza', 'Pepperoni Heat', 'Pepperoni, chilli oil, mozzarella, oregano.', '479.00', 'https://images.unsplash.com/photo-1628840042765-356cda07504e?auto=format&fit=crop&w=900&q=80', 910, 'Spicy'),
                    ('Dessert', 'Tiramisu Cup', 'Espresso-soaked sponge, mascarpone cream, cocoa.', '229.00', 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?auto=format&fit=crop&w=900&q=80', 430, 'Sweet'),
                ],
            },
            {
                'name': 'Tokyo Bento Bar',
                'tagline': 'Sushi rolls, rice bowls, and crisp tempura.',
                'description': 'A compact Japanese kitchen built around fresh rolls and balanced bento boxes.',
                'cuisine': 'Japanese',
                'city': 'Assam',
                'address': '11 MG Road, Guwahati',
                'phone': '+91 90000 44444',
                'opening_time': time(12, 0),
                'closing_time': time(22, 30),
                'rating': Decimal('4.5'),
                'delivery_time': 38,
                'delivery_fee': Decimal('69.00'),
                'minimum_order': Decimal('449.00'),
                'cover_image': 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?auto=format&fit=crop&w=1200&q=80',
                'logo_image': 'https://images.unsplash.com/photo-1611143669185-af224c5e3252?auto=format&fit=crop&w=400&q=80',
                'is_featured': False,
                'items': [
                    ('Sushi', 'Salmon Avocado Roll', 'Eight pieces with salmon, avocado, sesame.', '549.00', 'https://images.unsplash.com/photo-1617196034796-73dfa7b1fd56?auto=format&fit=crop&w=900&q=80', 520, 'Fresh'),
                    ('Sushi', 'Chicken Katsu Bento', 'Katsu, rice, salad, pickles, tonkatsu sauce.', '449.00', 'https://images.unsplash.com/photo-1617196035154-1e7e6e28b0db?auto=format&fit=crop&w=900&q=80', 780, 'Crispy'),
                    ('Drinks', 'Yuzu Iced Tea', 'Citrus tea with yuzu and mint.', '169.00', 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?auto=format&fit=crop&w=900&q=80', 120, 'Cold'),
                ],
            },
            {
                'name': 'Green Bowl Studio',
                'tagline': 'Colorful bowls, salads, and smoothie fuel.',
                'description': 'Vegetable-forward food with whole grains, lean proteins, and bright sauces.',
                'cuisine': 'Healthy',
                'city': 'Assam',
                'address': '4 Beltola Road, Guwahati',
                'phone': '+91 90000 55555',
                'opening_time': time(8, 0),
                'closing_time': time(21, 30),
                'rating': Decimal('4.4'),
                'delivery_time': 24,
                'delivery_fee': Decimal('35.00'),
                'minimum_order': Decimal('249.00'),
                'cover_image': 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=1200&q=80',
                'logo_image': 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=400&q=80',
                'is_featured': True,
                'items': [
                    ('Healthy', 'Falafel Grain Bowl', 'Falafel, quinoa, cucumber, hummus, tahini.', '319.00', 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80', 590, 'Vegan'),
                    ('Healthy', 'Grilled Chicken Caesar', 'Romaine, grilled chicken, parmesan, herb croutons.', '369.00', 'https://images.unsplash.com/photo-1550304943-4f24f54ddde9?auto=format&fit=crop&w=900&q=80', 610, 'Protein'),
                    ('Drinks', 'Mango Spinach Smoothie', 'Mango, spinach, yogurt, chia.', '199.00', 'https://images.unsplash.com/photo-1505252585461-04db1eb84625?auto=format&fit=crop&w=900&q=80', 260, 'Fresh'),
                ],
            },
            {
                'name': 'Morning Market',
                'tagline': 'Breakfast sandwiches, pancakes, and strong coffee.',
                'description': 'All-day breakfast with warm bakes, egg plates, and cafe drinks.',
                'cuisine': 'Cafe',
                'city': 'Assam',
                'address': '16 Uzan Bazar, Guwahati',
                'phone': '+91 90000 66666',
                'opening_time': time(7, 0),
                'closing_time': time(18, 0),
                'rating': Decimal('4.3'),
                'delivery_time': 22,
                'delivery_fee': Decimal('29.00'),
                'minimum_order': Decimal('199.00'),
                'cover_image': 'https://images.unsplash.com/photo-1495147466023-ac5c588e2e94?auto=format&fit=crop&w=1200&q=80',
                'logo_image': 'https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=400&q=80',
                'is_featured': False,
                'items': [
                    ('Breakfast', 'Egg and Cheese Croissant', 'Buttery croissant, egg, cheddar, tomato jam.', '249.00', 'https://images.unsplash.com/photo-1546549032-9571cd6b27df?auto=format&fit=crop&w=900&q=80', 520, 'Breakfast'),
                    ('Breakfast', 'Blueberry Pancakes', 'Three pancakes, berries, maple butter.', '299.00', 'https://images.unsplash.com/photo-1528207776546-365bb710ee93?auto=format&fit=crop&w=900&q=80', 700, 'Sweet'),
                    ('Drinks', 'Cold Brew Coffee', 'Slow-steeped coffee over ice.', '169.00', 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=900&q=80', 40, 'Cold'),
                ],
            },
        ]

        restaurant_count = 0
        item_count = 0
        for data in restaurants:
            item_rows = data.pop('items')
            restaurant, _ = Restaurant.objects.update_or_create(
                name=data['name'],
                defaults=data,
            )
            restaurant_count += 1
            for category_name, name, description, price, image_url, calories, labels in item_rows:
                MenuItem.objects.update_or_create(
                    restaurant=restaurant,
                    name=name,
                    defaults={
                        'category': category_objects[category_name],
                        'description': description,
                        'price': Decimal(price),
                        'image_url': image_url,
                        'calories': calories,
                        'labels': labels,
                        'is_available': True,
                        'is_featured': 'Best seller' in labels or name in ['Margherita DOP', 'Falafel Grain Bowl'],
                    },
                )
                item_count += 1

        self.stdout.write(self.style.SUCCESS(f'Created or updated {restaurant_count} restaurants and {item_count} menu items.'))
