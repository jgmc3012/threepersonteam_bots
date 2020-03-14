from packages.core.utils.web_client import WebClient
from .models import AnicamModel
import asyncio
import logging

class CtrlAnicam():
    """Anicam obj"""
    uri_api = 'https://api.anicamenterprises.com/v1/'
    sem = asyncio.Semaphore(20)

    async def price_shipping(self, product:dict):
        payload = {
            "shipper_country": "US",
            "delivery_country": "MX",
            "city_code": "04530",
            "city_name": "Coyoacan",
            "items": [
                {
                    "quantity": 1,
                    "length": product["length"],
                    "height": product["height"],
                    "width": product["width"],
                    "weight": product["weight"],
                    "declare_Value": product["cost_price"]
                }
            ]
        }
        async with self.sem:
            res = await WebClient().post(
                uri=f'{self.uri_api}delivery/dhl/quote',
                payload=payload,
                params=None,
                return_data="json",
                headers={
                    "Content-Type":"application/json",
                }
            )
            if res.get('status') == 200:
                return {'package_id':product['id'], 'price':res['data']['price']}
            else:
                breakpoint()
                print('hello')

    async def shipping_by_product(self):
        while True:
            anicam_model = AnicamModel()
            logging.getLogger('log_print').info('Cargando 200 productos para calcular el envio')
            product_outwhit_price = await anicam_model.select_products()
            if not product_outwhit_price:
                break
            shippings_coros = [self.price_shipping(p) for p in product_outwhit_price]
            shippings_draw = await asyncio.gather(*shippings_coros)
            shippings = [i for i in shippings_draw if i]
            await anicam_model.insert_shippings(shippings)