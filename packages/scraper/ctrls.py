import asyncio
import re
import logging
import json
import argparse
import os
import demjson

from more_itertools import grouper

from random import shuffle
from random import random

from datetime import datetime
from datetime import timedelta

from selectorlib import Extractor

from packages.my_pyppeteer.ctrls import MyPyppeteer
from packages.core.utils.web_client import WebClient

from .models import ProductModel
from .models import AttributeModel
from .models import PictureModel
from .models import insert_items_in_database
from .utils import price_shipping_or_err
from .utils import price_or_err
from .utils import weight_converter
from .utils import distance_converter
from .utils import get_yaml


class CtrlsScraper:
    PRODUCT_NOT_AVAILABLE = "-1"
    PRICE_NOT_FOUND = "-2"
    PRODUCT_NOT_FOUNT = "-3"
    PRODUCT_NOT_SHIP = "-4"
    CRITICAL_ERROR = "-5"
    message = {
        "-1": "PRODUCT_NOT_AVAILABLE",
        "-2": "PRICE_NOT_FOUND",
        "-3": "PRODUCT_NOT_FOUNT",
        "-4": "PRODUCT_NOT_SHIP",
        "-5": "CRITICAL_ERROR",
    }
    sem = asyncio.Semaphore(1)
    _sem_web_client_ = None
    sleep_avg = 5

    my_pypperteer = None
    url_origin = "https://www.amazon.com.mx/-/es/dp/sku?psc=1"
    parent_description = re.compile(r'((\w*://)?\w+\.\w+\.\w+)|([\w\-_\d\.]+@[\w\-_\d]+(\.\w+)+)')
    pattern_price = re.compile(r'(\d+\.?\d*)')
    pattern_price_shipping = re.compile(r'(\d+\.?\d*) [Ee]nvío')

    cookies = {
        "session-id":"132-4528637-2870205",
        "ubid-main":"130-0267183-0060640",
        "lc-main":"es_US",
        "i18n-prefs":"USD",
    }
    _extractor_ = None
    _web_client_ = None
    _selectors_new_ = None

    def __init__(self, country:str='usa'):
        self.country = country

    @property
    def extractor(self):
        if not self._extractor_:
            # Create an Extractor by reading from the YAML file
            self._extractor_ = Extractor.from_yaml_file(f'{os.path.dirname(os.path.realpath(__file__))}/storage/selectors.yaml')
        return self._extractor_

    @property
    def sem_web_client(self):
        if not self._web_client_:
            self.init_web_client()
        return self._sem_web_client_

    @property
    def web_client(self):
        if not self._web_client_:
            self.init_web_client()
        return self._web_client_

    @property
    def selectors_new(self):
        if not self._selectors_new_:
            self._selectors_new_ = get_yaml(
                f'{os.path.dirname(os.path.realpath(__file__))}/storage/selectors_new.yaml'
            )
        return self._selectors_new_

    async def init_my_pypperteer(self):
        profile = f'scraper_{self.country}'
        if not self.my_pypperteer:
            self.my_pypperteer = MyPyppeteer(profile)
            await self.my_pypperteer.connect_browser()
            await self.my_pypperteer.init_pool_pages(self.sem._value)

    def init_web_client(self):
        self._web_client_ = WebClient()
        self._sem_web_client_ = asyncio.Semaphore(len(self.web_client.ip_publics))

    def get_price_cost(self,price_str)->float:
        """
        Recibe un texto y retorna un precio que se encuentre en este
        """
        price_str = price_str.replace(',','')
        sale_price_regex = price_or_err(
            self.pattern_price, price_str, self.PRICE_NOT_FOUND
        )
        logging.getLogger("log_print_full").debug(
            f'Price scraper: {price_str}. Price regex: {sale_price_regex}')
        return float(sale_price_regex)

    def _get_price_ship(self, price_str)->str:
        price_shipping_str = price_shipping_or_err(
                price_str, self.PRICE_NOT_FOUND
            )

        if price_shipping_str != self.PRICE_NOT_FOUND:
            return price_shipping_str

        return  price_or_err(self.pattern_price_shipping,
                            price_str, self.PRICE_NOT_FOUND)

    def get_price_ship(self,price_str_1, price_str_2)->float:
        """
        Recibe dos string con informacion referente al costo de envio
        Retorna el precio de envio. si el mismo esta disponible
        """
        if not price_str_1 or not price_str_2:
            return float(self.PRODUCT_NOT_AVAILABLE)
        if ' no se envía ' in price_str_2:
            return float(self.PRODUCT_NOT_SHIP)
        
        price_shipping_str = self._get_price_ship(price_str_1)
        if price_shipping_str != self.PRICE_NOT_FOUND:
            return float(price_shipping_str)

        return float(self._get_price_ship(price_str_2))

    def get_quantity(self, quantity_str)->int:
        """
        Recibe un numero en string y lo retorna en flotante
        Si sucede un error retorna 0
        """
        try:
            return int(quantity_str)
        except (TypeError,ValueError):
            return 0

    def get_description(self, description_raw:str)->str:
        if not description_raw:
            return ''
        return re.sub(self.parent_description, '',
                    description_raw.replace('"','').replace("'",'')
                )

    def get_categories(self, categories_raw:str)->tuple:
        """
        Recibe un string con todas las categorias
        Retorna la categoria raiz y hoja del arbol
        """
        categories_raw = categories_raw.split('›')
        if len(categories_raw) < 2:
            return None, None

        category_root = categories_raw[0].strip()
        category_child = categories_raw[-1].strip()

        return category_root, category_child

    def get_dimensions(self, dimensions_str:str, old_dimensions=dict())->dict:
        dimensions = dict()
        # Las dimensiones vienen en este formato "7.1 x 4 x 1.9 inches"
        dimensions_draw = dimensions_str.replace(',','').split(';')
        dimensions_draw = dimensions_draw[0].split('x')
        if len(dimensions_draw) < 3:
            return dict()
        dimensions['x'] = float(dimensions_draw[0])
        dimensions['y'] = float(dimensions_draw[1])
        dimensions_draw = dimensions_draw[2].strip().split(' ')
        dimensions['z'] = float(dimensions_draw[0])
        unit = dimensions_draw[1].lower()

        dimensions['x'] = distance_converter(dimensions['x'], unit)
        dimensions['y'] = distance_converter(dimensions['y'], unit)
        dimensions['z'] = distance_converter(dimensions['z'], unit)
        if not old_dimensions:
            return dimensions
        if (old_dimensions['x']*old_dimensions['y']*old_dimensions['z']) < (dimensions['x']*dimensions['y']*dimensions['z']):
            return dimensions

    def get_weight(self, weight_str:str, old_weight=0):
        weight_raw = weight_str.strip().replace(',','').split(' ')
        weight = weight_converter(weight_raw[0], weight_raw[1])

        if old_weight < weight:
            return weight
        return old_weight

    def get_attributes_from_a_list(self,attr_list):
        """
        Dado una serie de atributos en una lista, donde cada item es un string
        de clave:valor separados por in ":"
        
        Se retorna un diccionario con dichos items
        """
        attributes = dict()
        for row in attr_list:
            item = row.split(':')
            if len(item) > 1:
                key = item[0].strip().replace(' ', '_').lower()
                value = item[1].strip()
                if key and value:
                    attributes[key] = value
        return attributes
    
    def get_attributes_from_a_table(self, attr_table):
        """
        Dado una serie de atributos en una lista, donde cada dos nodos de la lista
         representan las clave y valor de un item respectivamente.
        
        Se retorna un diccionario con dichos items
        """
        attributes = dict()
        for col in grouper(attr_table,2,''):
            key = col[0].strip().replace(' ', '_').lower()
            value = col[1].strip()
            if key and value:
                attributes[key] = value
        return attributes      

    def get_attributes(self, attr_list:list, attr_table:list, attr_var:list)->dict:
        attributes = self.get_attributes_from_a_list(attr_var)

        attributes_raw = self.get_attributes_from_a_list(attr_list)
        attributes_raw.update(self.get_attributes_from_a_table(attr_table))

        attributes['dimensions'] = dict()
        attributes['weight'] = 0
        for attribute_key in attributes_raw:
            if 'dimensiones' in attribute_key:
                dimensions = self.get_dimensions(attributes_raw[attribute_key])
                if dimensions:
                    attributes['dimensions'] = dimensions

            elif 'peso_' in attribute_key:
                attributes['weight'] = self.get_weight(attributes_raw[attribute_key],
                                                        old_weight=attributes['weight'])

            elif 'asin' in attribute_key:
                attributes['sku'] = attributes_raw[attribute_key].strip()

            elif attribute_key not in (
                'opinión_media_de_los_clientes',
                'clasificación_en_los_más_vendidos_de_amazon',
                'producto_en_amazon.com_desde',
                'envío_nacional',
                ) and attributes_raw[attribute_key] not in ('clic', 'aquí') :
                attributes[attribute_key] = attributes_raw[attribute_key]

        return attributes

    def get_title(self, title_str)->str:
        return title_str.replace('"','').replace("'",'') if title_str else ""

    def get_images(self, bodyHTML:str)->list:
        images = list()
        for line in bodyHTML.split('\n'):
            if "'colorImages':" in line:
                line = line.strip()
                start = line.index("'colorImages':") + len("'colorImages':")
                js_obj = line[start:-1]
                py_obj = demjson.decode(js_obj) 
                for image in py_obj.get('initial', []):
                    if image.get('hiRes'):
                        images.append(re.sub(r'\._.+_','',image['hiRes']))
                    elif image.get('large'):
                        images.append(re.sub(r'\._.+_','',image['large']))
                return images
        return images

    def get_skus_data(self, bodyHTML:str)->list:
        """
        Obtiene los skus de las variones de un item si este tiene variaciones.
        """
        read_JSON = False
        dataToReturn = False
        js_obj = '{'
        for line in bodyHTML.split('\n'):
            if dataToReturn:
                if not read_JSON and 'dataToReturn' in line:
                    read_JSON = True
                elif not ';' in line:
                    js_obj += line
                else:
                    js_obj += '}'
                    break
            elif 'twister-js-init-dpx-data' in line:
                dataToReturn = True
        try:
            py_obj = demjson.decode(js_obj)
            variations_data = py_obj['asinVariationValues']
        except Exception:
            logging.getLogger('log_print').error(f'Error extrayendo los datos de las variacion en del dataToReturn : {Exception}.')
            variations_data = dict()

        return list(variations_data.keys())

    def get_info_product(self, elements:dict, sku:str, bodyHTML:str)->dict:
        """
        Retorn la informacion completa de un producto si este existe. de lo contrario
        retorna un diccionario vacio
        """
        title = self.get_title(elements['title'])
        if not title.strip():
            return dict()

        price_product = self.get_price_cost(elements['cost_price1'])
        price_shipping = self.get_price_ship(elements['ship_price1'],
                                            elements['ship_price1'])

        description = self.get_description(elements['description'])

        category_root, category_child = self.get_categories(elements['categories'])

        quantity = self.get_quantity(elements['quantity'])

        attributes = self.get_attributes(attr_list=elements['attributes_list'],
                                        attr_table=elements['attributes_table'],
                                        attr_var=elements['attributes_variations'])
        dimensions = attributes.pop('dimensions')
        weight = attributes.pop('weight')
        sku = attributes.pop('sku') if attributes.get('sku') else sku

        images = self.get_images(bodyHTML)

        product = {
            "sku": sku,
            "title": title,
            "description": description,
            "attributes": attributes,
            "images": images,
            "category": {"root": category_root, "child": category_child},
            "price": {"product": price_product, "shipping": price_shipping},
            "dimensions": dimensions,
            "weight":weight,
            "quantity": quantity,
        }
        logging.getLogger("log_print_full").debug(f"{product['title']} {product['price']} {product['sku']}")
        return product

    async def go_to_amazon(self, url:str, func, *args, **kwargs):
        await self.init_my_pypperteer()
        async with self.sem:
            id_page, page = self.my_pypperteer.get_page_pool()

            while True:
                logging.getLogger("log_print_full").debug(f"URL: {url}")
                input_chatpcha = await page.querySelector('[id="captchacharacters"]')
                if not input_chatpcha:
                    break
                img_draw = await page.querySelector('form img')
                img = await self.my_pypperteer.get_attribute(img_draw,'src',page)
                await page.click(input_chatpcha)
                value_chatpcha = input(f'Ingrese la solucion del chatpcha {img} :')
                await page.keyboard.type(value_chatpcha)
                page = await self.my_pypperteer.change_page(page)
                await page.goto(url)

            response = await func(page, *args, **kwargs)
            self.my_pypperteer.close_page_pool(id_page)
        return response

    async def get_product_and_variations_with_pyppeteer(self, sku:str):
        url = self.url_origin.replace('sku',sku)

        elements, bodyHTML = await self.go_to_amazon(url,func=self.get_data_with_pyppeteer)
        skus = self.get_skus_data(bodyHTML)

        if sku in skus:
            skus.remove(sku)
        
        product = self.get_info_product(elements, sku, bodyHTML)

        products = [product] if product else []
        products_coros = [self.get_product_with_pyppeteer(sku) for sku in skus]
        if products_coros:
            products += await asyncio.gather(*products_coros)
        return [product for product in products if product]

    async def get_product_with_pyppeteer(self, sku:str):
        url = self.url_origin.replace('sku',sku)
        elements, bodyHTML = await self.go_to_amazon(url, func=self.get_data_with_pyppeteer)

        product = self.get_info_product(elements=elements, sku=sku,
                                            bodyHTML=bodyHTML)
        return product

    async def get_data_with_pyppeteer(self, page):
        """
        Retorna los elementos predefinidos por los selectores
        en el respectivo fichero .yaml y el cuerpo HTMl de la pagina
        """
        elements = dict()
        for item in self.selectors_new:
            if not self.selectors_new[item]['all']:
                element = await self.my_pypperteer.get_property_from_querySelector(
                    selector=self.selectors_new[item]['css'],
                    attr=self.selectors_new[item]['pyppeteer'],
                    page=page
                )
                elements[item] = element if element else ''
            else:
                elements[item] = await self.my_pypperteer.get_property_from_querySelectorAll(
                    selector=self.selectors_new[item]['css'],
                    attr=self.selectors_new[item]['pyppeteer'],
                    page=page
                )

        bodyHTML = await page.evaluate("() => document.body.innerHTML")
        return elements, bodyHTML

    async def new_product_with_pyppeteer(self, sku:str):
        """
        Scrapea un producto y sus variaciones desde la pagina de amazon y lo
        inserta en la base de datos
        """
        products_draw = await self.get_product_and_variations_with_pyppeteer(sku)
        products = list()
        for _products_ in products_draw:
            for p in _products_:
                if p['title']:
                    products.append(p)

        logging.getLogger('log_print').info(f'Inserting {len(products)} products in the database')
        await insert_items_in_database(products)

    async def get_skus_from_page(self, page):
        skus_draw = await page.evaluate("""
            () => {
                skus_elements = document.querySelectorAll('.s-result-list > div')
                return Array.from(skus_elements).map( sku => sku.getAttribute('data-asin'))
            }
        """)
        return [sku for sku in skus_draw if sku]

    async def get_news_skus_in_page(self, skus:list):
        skus = set(skus)
        logging.getLogger('log_print').info(f'Products found on the page: {len(skus)}')
        skus_in_database = await ProductModel().skus_in_database()
        return [sku for sku in skus if sku not in skus_in_database]

    async def scraper_pages_with_pyppeteer(self, uri:str, number_page:int=0):
        """
        - Entra a una pagina de busqueda en Amazon.com
        - Selecciona todos sku.
        - Va de pagina en pagina scrapeando dicho producto
        - Los inserta en la base de datos
        """
        while True:
            number_page += 1
            logging.getLogger('log_print').info(f'Scraping page number {number_page}')
            url = f'{uri}&page={number_page}'

            all_the_skus = await self.go_to_amazon(url, func=self.get_skus_from_page)

            if not all_the_skus:
                logging.getLogger('log_print').info(f'Finish Scraping in page number {number_page-1}')
                break
            skus = self.get_news_skus_in_page(all_the_skus)
            logging.getLogger('log_print').info(f'New products for scrape in page: {len(skus)}')
            if not skus:
                continue

            products_coros = [self.new_product_with_pyppeteer(sku) for sku in skus]
            await asyncio.gather(*products_coros)

    async def get_data_fast(self, sku:str):
        """
        Realiza una peticion en texto plano y se parsea el body para obtener los datos
        deseados

        Retorna la data obtenida de la pagina por medio de los selectores
        """
        async with self.sem_web_client:
            url = self.url_origin.replace('sku',sku)

            logging.getLogger("log_print_full").debug(f'realizando la peticion a {url}')
            bodyHTML = await self.web_client.get(uri=url,
                cookies=self.cookies,
                return_data='text'
                )
            bodyHTML = bodyHTML if bodyHTML else ''
            sleep = 2 + random()*(2*self.sleep_avg - 2*2)
            data = self.extractor.extract(bodyHTML)
            data['sku'] = sku
            logging.getLogger("log_print_full").info(f'Analizando la data de {sku}. Luego de {sleep} seg se libera el loop')
            logging.getLogger("log_print_full").debug(json.dumps(data, indent=True))
            if data['captcha'] or not data['title']:
                logging.getLogger("log_print_full").warning(f"APARECIO EL CAPTCHA. Fecha: {datetime.now()}. ¿O el producto {sku} no existe?")
                breakpoint()
            else:
                await asyncio.sleep(sleep)

        return data

    async def update_product(self, product):
        product_data = await self.get_data_fast(product['provider_sku'])
        product['cost_price'] = self.get_price_cost(product_data['cost_price'])
        product['ship_price'] = self.get_price_ship(product_data['ship_price1'],
                                                    product_data['ship_price2'])
        product['quantity'] = self.get_quantity(product_data['quantity']) if (
                                                product['cost_price'] > 0) else 0
        product['last_update'] = datetime.now()
        
        message = {
            'cost_price': product_data['cost_price'],
            'ship_price': product['ship_price'],
            'quantity': product['quantity'],
            'link': product['provider_link'],
        }
        logging.getLogger('log_print_full').debug(json.dumps(message, indent=True))

        return product

    async def update_products(self, chunk:int=100, sleep_end=60):
        """
        Actualiza los producto en la base de datos. Desde el más viejo hasta el más actualizado.
        """
        count = 0
        while True:
            logging.getLogger("log_print_full").info(f"Obteniendo {chunk} registros de la DB.")
            start = datetime.now()
            products = await ProductModel().select(limit=chunk)
            shuffle(products)
            if products[0]['last_update'] > (
                datetime.now() - timedelta(days=5)):
                break
            updates_coros = [self.update_product(product) for product in products]
            await asyncio.gather(*updates_coros)
            await ProductModel().insert(products)
            count += 1
            logging.getLogger("log_print_full").info(f"Fin de la ronda N° {count}. Tiempo de actualizacion de los {chunk} productos:{(datetime.now()-start).total_seconds()}")
            if count % 5 == 0:
                sleep = sleep_end
            else:
                sleep = sleep_end/6
            logging.getLogger("log_print_full").info(f"Durmiendo {sleep} seg.")
            await asyncio.sleep(sleep)