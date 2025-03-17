from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError, Decimal.InvalidOperation):
        return 0

@register.filter
def total_price(items):
    """Calculate total price for a list of cart items"""
    try:
        return sum(item.total_price for item in items)
    except (AttributeError, TypeError):
        return Decimal('0.00')

@register.filter
def items_by_farmer(cart_items):
    """Group cart items by farmer and calculate subtotals"""
    farmers = {}
    try:
        for item in cart_items:
            farmer = item.product.farmer
            if farmer not in farmers:
                farmers[farmer] = {
                    'items': [],
                    'subtotal': Decimal('0.00')
                }
            farmers[farmer]['items'].append(item)
            farmers[farmer]['subtotal'] += item.total_price
    except (AttributeError, TypeError):
        pass
    return farmers
