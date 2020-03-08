from packages.core.db import ConnectionsDB
from packages.core.utils.config import Config

class ProductModel():
    """
        Modelo de abtraccion para los productos en la base de datos.
        Solo los campos que para el scraper son relevantes.
    """

    def __init__(self):
        self.name_connection = 'threepersonteam'
        self.fields = [
        # seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
        'title', # :str, (max_length=60)
        'cost_price', # :float, (null=True)
        'sale_price', # :float,(null=True)
        'provider_sku', # :str, (max_length=50, unique=True)
        'provider_link', # :str, (max_length=255, unique=True)
        'image', # :str, (max_length=255)
        'category', # models.ForeignKey(Category, on_delete=models.CASCADE)
        'description' # :str, (null=True, default=None)
        'quantity' # :int,
        'last_update', # DateTimeField(default=timezone.localtime)
        ]
        self.keys = ['provider_sku']

    async def insert(self, product:list):
        return await (
            await ConnectionsDB().get_connection(self.name_connection)
        ).insert(product, 'store_product', self.keys)

    