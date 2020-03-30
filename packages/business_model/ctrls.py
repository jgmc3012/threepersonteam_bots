from .models import BusinessModel
from math import ceil

class CtrlBusiness():
    """Contiene el modelo de negocio para cada tienda en particular que se abra"""

    def alfredo_form(self, products_draw:list, store_id:int)->list:
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
                'store_id':store_id,
                'product_id': _product_['item_id'],
                'no_problem':False,
                'sku':None,
                'status':0,
            }
            if _product_.get('id'):
                product['id'] = _product_.get('id')
            products.append(product)
        return products

    async def calculate_price(self, store_id:int, func):
        rank = 0
        while True:
            rank += 1
            products_draw = await BusinessModel(store_id).select_exist(
                offset=(rank-1)*400,
                limit=(rank)*400
            )
            if not products_draw:
                break
            products = func(products_draw,store_id)
            await BusinessModel(store_id).insert_products(products)

        products_draw = await BusinessModel(store_id).select(
            shipper='anicam' if func.__func__.__name__ == 'alfredo_form' else None
        )
        if products_draw:
            products = func(products_draw,store_id)
            await BusinessModel(store_id).insert_products(products)

    def dominicana_form(self, products_draw:list, store_id:int)->list:
        products = list()
        for _product_ in products_draw:
            price_for_lb = 5 #USD 
            price = _product_['cost_price'] + _product_['ship_price'] + ceil(_product_['weight']) * price_for_lb
            meli = 1.16 #PORCENTAJE
            utility = 1.28 #PORCENTAJE
            survey = 1.18 #IMPUESTOS ADUANALES
            if _product_['cost_price'] > 199:
                price += _product_['cost_price']*survey
            price = price*utility*meli
            product = {
                'sale_price': ceil(price),
                'store_id':store_id,
                'product_id': _product_['item_id'],
                'no_problem':False,
                'sku':None,
                'status':0,
            }
            if _product_.get('id'):
                product['id'] = _product_.get('id')
            products.append(product)
        return products