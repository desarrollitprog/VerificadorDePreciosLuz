"""
Modelos SQLAlchemy para el sistema de verificación de precios.

Importa todos los modelos aquí para facilitar su uso en otras partes de la aplicación.
"""

from .producto import Producto
from .producto_precio import ProductoPrecio
from .producto_oferta import ProductoOferta
from .ofertas_x_productos_sucursal import OfertasxProductosxSucursal
from .ofertas_x_productos import OfertasxProductos
from .ofertas_x_productos_sucursal_detalles import OfertasxProductosxSucursalesDetalles
from .productos_x_impuestos import ProductosXImpuestos
from .tasa_impuesto import TasaImpuesto
from .publicidad import Publicidad
from .barras_asociadas import BarrasAsociadas

# Exportar todos los modelos
__all__ = [
    "Producto",
    "ProductoPrecio",
    "ProductoOferta",
    "OfertasxProductosxSucursal",
    "OfertasxProductos",
    "OfertasxProductosxSucursalesDetalles",
    "ProductosXImpuestos",
    "TasaImpuesto",
    "Publicidad",
    "BarrasAsociadas",
]
