from datetime import datetime

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

    async def select(self, fields:list=list(), offset=None, limit=None):
        query = "SELECT\n"
        if fields:
            query += '\n,'.join(fields)
        else:
            query += ' *'
        query += " FROM store_product"
        query +=' ORDER BY last_update'
        if offset!=None or limit:
            query += ' LIMIT'
            if offset!=None:
                query += f' {offset},'
            if limit:
                query += f' {limit}'
        query += ';'
        return await(await ConnectionsDB().get_connection(self.name_connection)).select(query)

    async def skus_in_database(self):
        skus_in_database_raw = await self.select(fields=['provider_sku'])
        return {i['provider_sku'] for i in skus_in_database_raw}

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
                if len(attributes_draw[sku][attr].strip()) > 100 or len(attr) > 50:
                    continue
                attribute = {
                    "id_meli" : attr,
                    "value" : attributes_draw[sku][attr].strip(),
                    "product_id" : id
                }
                attributes.append(attribute)
        return await (
            await ConnectionsDB().get_connection(self.name_connection)
        ).insert(attributes, 'store_attribute', self.keys)

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

async def insert_items_in_database(products_draw:list):
    products = list()
    attributes = dict()
    pictures = dict()
    for product in products_draw:
        if not product['title'] or len(product['images'])<1:
            continue
        products.append({
            'available': 1,
            'modifiable':1,
            'title':product['title'][:300], # :str, (max_length=60)
            'cost_price':product['price']['product'], # :float, (null=True)
            'ship_price':product['price']['shipping'], # :float,(null=True)
            'currency': product['price']['currency'],  # :str,(null=True)
            'provider_sku':product['sku'], # :str, (max_length=50, unique=True)
            'provider_link':product['link'], # :str, (max_length=255, unique=True)
            'image':product['images'][0].replace('.jpg', '._AC_UY150_ML3_.jpg'), # :liststr, (max_length=255)
            'category_name':product['category']['child'] if product['category']['child'] else '', # models.CharField(max_length=60) #"Temporal." Para el scraper de amazon
            'description':product['description'], # :str, (null=True, default=None)
            'quantity':product['quantity'], # :int,
            'last_update': datetime.now(), # DateTimeField(default=timezone.localtime)
            'height': product['dimensions'].get("x"), # models.FloatField(default=None, null=True)
            'width': product['dimensions'].get("y"), # models.FloatField(default=None, null=True)
            'length': product['dimensions'].get("z"), # models.FloatField(default=None, null=True)
            'weight': product['weight'] if product['weight'] else None, # models.FloatField(default=None, null=True)
        })
        attributes[product['sku']] = product['attributes']
        pictures[product['sku']] = product['images']

    await ProductModel().insert(products)
    await AttributeModel().insert(attributes)
    await PictureModel().insert(pictures)