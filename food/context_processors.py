from .cart import Cart


def cart_context(request):
    try:
        cart = Cart(request)
    except Exception:
        return {'cart_count': 0}
    return {
        'cart_count': cart.count,
        'cart_preview': cart.as_dict(),
    }
