# from packages.core.db import ConnectionsDB
# from packages.core.utils.config import Config

# class DemoModel():
#     """docstring for CtrlMod1"""

    # def __init__(self):
    #     self.name_connection = 'dbcontrolcenter_yaxa_co'
    #     self.conn_config = Config().config_yaml()["db"]["connections"][self.name_connection]

    # async def test(self):
    #     query = "SELECT * FROM keywords_aws limit 10"
    #     return await(await ConnectionsDB().get_connection("database")).select(query, 'all')

    # async def insert(self, items:list, table:str, updates:list):
    #     fields = ', '.join(items[0].keys())
    #     query = f"INSERT INTO {table} ({fields}) VALUES"
    #     query = query + ' {} ON DUPLICATE KEY UPDATE'
    #     for column in updates:
    #         query +=  f' `{column}` = VALUES({column}),'
    #     query = f'{query[:-1]};'
    #     values = [tuple(item.values()) for item in items]
    #     return await (
    #         await ConnectionsDB().get_connection(database)
    #     ).execute_big_insert(arr_values, query_schema)

    # async def get_products_for_publish(self):
    #     query = 'SELECT v.item_id AS item_id, c.mco AS category_mco\
    #             FROM variations_6pm AS v\
    #                 INNER JOIN products_6pm AS p ON\
    #                     p.productId = v.productId\
    #                 INNER JOIN categories_6pm AS c ON\
    #                     c.eng_name = p.category;'
    #     return await(await ConnectionsDB().get_connection(self.name_connection)).select(query)

    # async def insert_brands(self, brands:list):
    #     return await (
    #         await ConnectionsDB().get_connection(database)
    #     ).insert(brands, 'brands_6pm', ['id'])

    # async def update_products(self, products:list):
    #     fields = [f'{field}' for field in products[0].keys() if (
    #         not field in ['productId']
    #     )]
    #     await (await ConnectionsDB().get_connection(database)
    #         ).insert(products, 'products_6pm', fields)