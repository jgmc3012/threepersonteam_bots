from .models import BusinessModel
from math import ceil

class CtrlBusiness():
    """Contiene el modelo de negocio para cada tienda en particular que se abra"""

    def alfredo_form(self, products_draw:list, seller_id:int)->list:
        products = list()
        for _product_ in products_draw:
            cost_price = _product_['cost_price'] + _product_['ship_price'] + _product_['ship_international']
            miami_in_out = 3.4 #USD
            mexico_in_out = 2 #USD
            anicam_ticket = 1.104 #PORCENTAJE
            last_mile = 15 #USD
            credit_card = 1.04 #PORCENTAJE
            meli = 1.16 #PORCENTAJE
            utility = 1.28 #PORCENTAJE
            product = {
                'sale_price': ceil(
                    (cost_price+miami_in_out+mexico_in_out+last_mile)*utility*anicam_ticket*credit_card*meli),
                'seller_id':seller_id,
                'product_id': _product_['package_id'],
                'no_problem':False,
                'sku':None,
                'status':0,
            }
            if _product_.get('id'):
                product['id'] = _product_.get('id')
            products.append(product)
        return products

    async def mx_alfredo(self, seller_id:int):
        rank = 0
        while True:
            rank += 1
            products_draw = await BusinessModel(seller_id).select_exist(
                offset=(rank-1)*400,
                limit=(rank)*400
            )
            if not products_draw:
                break
            products = self.alfredo_form(products_draw,seller_id)
            await BusinessModel(seller_id).insert_products(products)

        products_draw = await BusinessModel(seller_id).select()
        if products_draw:
            products = self.alfredo_form(products_draw,seller_id)
            await BusinessModel(seller_id).insert_products(products)