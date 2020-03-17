from packages.core.db import ConnectionsDB
from packages.core.utils.config import Config

class BusinessModel():
    def __init__(self, seller_id:int):
        self.seller_id = seller_id
        self.name_connection = 'threepersonteam'

    async def select(self):
        query = f"SELECT product_id FROM store_product_for_store WHERE seller = {self.seller_id};"
        product_exits_draw = await(await ConnectionsDB().get_connection(self.name_connection)).select(query)
        product_exits = ', '.join([str(i['product_id']) for i in product_exits_draw])
        query = "SELECT id FROM shipping_shipperinternational WHERE nickname='anicam'"
        shipper = await(await ConnectionsDB().get_connection(self.name_connection)).select(query)
        id = shipper[0]['id']
        query = f"""
            SELECT ssi.package_id, sp.cost_price, sp.ship, ssi.price AS ship_international
            FROM store_product AS sp
            INNER JOIN shipping_shippinginternational AS ssi ON
                sp.id = ssi.package_id
            WHERE
                id NOT IN ({product_exits}) AND
                ssi.shipper_id = {id} AND
                ssi.price > 0;
            """
        return await(await ConnectionsDB().get_connection(self.name_connection)).select(query)
    async def insert_products(self, products:list):
        return await (
            await ConnectionsDB().get_connection(self.name_connection)
        ).insert(products, 'store_productforstore', ['sale_price'])