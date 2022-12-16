from app.crud import CRUDBase
from app.models.product import Product
from app.schemas.product import ProductCreateIn, ProductUpdateIn


class CRUDProduct(CRUDBase[Product, ProductCreateIn, ProductUpdateIn]):
    pass


product = CRUDProduct(Product)
