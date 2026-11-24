from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def clp(valor):
    """Formatea un monto en pesos chilenos: 6500 -> "$6.500"."""
    try:
        numero = int(round(Decimal(str(valor))))
    except (InvalidOperation, TypeError, ValueError):
        return f"${valor}"
    signo = "-" if numero < 0 else ""
    return f"{signo}${abs(numero):,}".replace(",", ".")
