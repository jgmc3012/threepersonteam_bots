from packages.core.db import ConnectionsDB
from packages.core.utils.config import Config

class ProductModel():
    """
        Modelo de abstraccion para los productos en la base de datos.
        Solo los campos que para el scraper son relevantes.
    """

    def __init__(self):
        self.name_connection = 'threepersonteam'
        self.fields = [
        'title', # :str, (max_length=60)
        'cost_price', # :float, (null=True)
        'ship_price', # :float,(null=True)
        'provider_sku', # :str, (max_length=50, unique=True)
        'provider_link', # :str, (max_length=255, unique=True)
        'image', # :str, (max_length=255)
        'category_name', # models.CharField(max_length=60) #"Temporal." Para el scraper de amazon
        'description' # :str, (null=True, default=None)
        'quantity' # :int,
        'last_update', # DateTimeField(default=timezone.localtime)
        'height', # models.FloatField(default=None, null=True)
        'width', # models.FloatField(default=None, null=True)
        'length', # models.FloatField(default=None, null=True)
        'weight', # models.FloatField(default=None, null=True)
        ]
        self.keys = ['cost_price', 'ship_price', 'quantity', 'last_update']


    async def insert(self, products:list):
        return await (
            await ConnectionsDB().get_connection(self.name_connection)
        ).insert(products, f'store_product', self.keys)

class AttributeModel():
    """
        Modelo de abstraccion para los atributos en la base de datos.
    """

    def __init__(self):
        self.name_connection = 'threepersonteam'
        self.keys = ['id']
    async def insert(self, attributes_draw:dict):
        skus = [f'"{sku}"' for sku in attributes_draw.keys()]
        query = f"SELECT provider_sku AS sku,id from store_product WHERE provider_sku IN ({','.join(skus)})"
        skus_and_ids = await(await ConnectionsDB().get_connection(self.name_connection)).select(query)
        attributes = list()
        for sku_and_id in skus_and_ids:
            sku = sku_and_id['sku']
            id = sku_and_id['id']
            for attr in attributes_draw[sku]:
                attribute = {
                    "id_meli" : attr,
                    "value" : attributes_draw[sku][attr],
                    "product_id" : id
                }
                attributes.append(attribute)
        return await (
            await ConnectionsDB().get_connection(self.name_connection)
        ).insert(attributes, 'store_attribute', self.keys)

    async def select(self):
        query = f"SELECT * from store_product"
        await(await ConnectionsDB().get_connection(self.name_connection)).select(query)

class PictureModel():
    """
        Modelo de abstraccion para los atributos en la base de datos.
    """

    def __init__(self):
        self.name_connection = 'threepersonteam'
        self.keys = ['id']
    async def insert(self, pictures_draw:dict):
        skus = [f'"{sku}"' for sku in pictures_draw.keys()]
        query = f"SELECT provider_sku AS sku,id from store_product WHERE provider_sku IN ({','.join(skus)})"
        skus_and_ids = await(await ConnectionsDB().get_connection(self.name_connection)).select(query)
        pictures = list()
        for sku_and_id in skus_and_ids:
            sku = sku_and_id['sku']
            id = sku_and_id['id']
            for image in pictures_draw[sku]:
                picture = {
                    "src" : image,
                    "product_id" : id
                }
                pictures.append(picture)
        return await (
            await ConnectionsDB().get_connection(self.name_connection)
        ).insert(pictures, 'store_picture', self.keys)