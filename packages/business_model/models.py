from packages.core.db import ConnectionsDB
from packages.core.utils.config import Config

class BusinessModel():
    def __init__(self, seller_id:int):
        self.seller_id = seller_id
        self.name_connection = 'threepersonteam'

    async def select(self, shipper=None):
        query = f"SELECT product_id FROM store_productforstore WHERE seller_id = {self.seller_id};"
        product_exits_draw = await(await ConnectionsDB().get_connection(self.name_connection)).select(query)
        product_exits = ', '.join([str(i['product_id']) for i in product_exits_draw])
        if shipper:
            query = "SELECT id FROM shipping_shipperinternational WHERE nickname='anicam'"
            shipper = await(await ConnectionsDB().get_connection(self.name_connection)).select(query)
            id = shipper[0]['id']
        query = "SELECT sp.id AS item_id, sp.cost_price, sp.ship_price, sp.weight"
        if shipper:
            query += ' ,ssi.price AS ship_international'
        query += '\n FROM store_product AS sp\n '
        if shipper:
            query += """INNER JOIN shipping_shippinginternational AS ssi ON
                sp.id = ssi.package_id \n"""
        query += 'WHERE \n'
        if shipper:
            query += """ssi.shipper_id={id} AND
                ssi.price > 0 AND"""
        if product_exits:
            query += f" sp.id NOT IN ({product_exits}) AND "
        query += 'sp.cost_price > 0 AND sp.ship_price >= 0 AND sp.weight > 0;'

        return await(await ConnectionsDB().get_connection(self.name_connection)).select(query)
    async def insert_products(self, products:list):
        return await (
            await ConnectionsDB().get_connection(self.name_connection)
        ).insert(products, 'store_productforstore', ['sale_price'])

    async def select_exist(self, offset:int, limit:int):
        query = f"SELECT id, product_id FROM store_productforstore WHERE seller_id = {self.seller_id};"
        product_exits_draw = await(await ConnectionsDB().get_connection(self.name_connection)).select(query)
        product_macth_id = {i['product_id']:i['id'] for i in product_exits_draw}
        product_exits = ', '.join([str(i['product_id']) for i in product_exits_draw])
        if not product_exits:
            return []
        query = f"""
            SELECT sp.id AS item_id, sp.cost_price, sp.ship_price, ssi.price AS ship_international, sp.weight
            FROM store_product AS sp
            LEFT JOIN shipping_shippinginternational AS ssi ON
                sp.id = ssi.package_id
            WHERE
                sp.id IN ({product_exits})
            LIMIT {offset},{limit};
            """
        product_exits = await(await ConnectionsDB().get_connection(self.name_connection)).select(query)
        for product in product_exits:
            product['id'] = product_macth_id[product['item_id']]
        return product_exits