from .models import BusinessModel


class CtrlBusiness():
    """Contiene el modelo de negocio para cada tienda en particular que se abra"""

    def mx_alfredo(self, seller_id:int):
        products_draw = await BusinessModel(seller_id).select()

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
                'sale_price': (
                    cost_price+miami_in_out+mexico_in_out+last_mile)*utility*anicam_ticket*credit_card*meli,
                'seller_id':seller_id,
                'product_id': product['package_id'],
                'no_problem':False,
                'sku':None,
                'status':0,
            }
            products.append(product)
        await BusinessModel(seller_id).insert_products(products)