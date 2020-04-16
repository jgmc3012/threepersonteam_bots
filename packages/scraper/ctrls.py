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
    path_update = f'{os.path.dirname(os.path.realpath(__file__))}/storage/selectors_update.yaml'
    path_new = f'{os.path.dirname(os.path.realpath(__file__))}/storage/selectors_new.yaml'
    path_skus = f'{os.path.dirname(os.path.realpath(__file__))}/storage/selectors_skus.yaml'

    my_pyppeteer = None
    url_origin = "https://www.amazon.com/-/es/dp/sku?psc=1"
    parent_description = re.compile(r'((\w*://)?\w+\.\w+\.\w+)|([\w\-_\d\.]+@[\w\-_\d]+(\.\w+)+)')
    pattern_price = re.compile(r'(?P<currency>\w*\$)\s*(?P<price>\d+([,.]?\d*)*)') 
    pattern_price_shipping = re.compile(r'(?P<price>\d+\.?\d*) [Ee]nvío')

    def _get_price_cost(self,price_str)->float:
        """
        Recibe un texto y retorna un precio que se encuentre en este
        """
        price_str = price_str.replace(',','')
        sale_price_regex = price_or_err(
            self.pattern_price, price_str, self.PRICE_NOT_FOUND
        )
        logging.getLogger("log_print_full").debug(
            f'Price scraper: {price_str}. Price regex: {sale_price_regex}')
        return sale_price_regex

    def get_price_cost(self,price_str_1, price_str_2)->float:
        """
        Recibe dos string con informacion referente al costo de l producto
        Retorna el precio del mismo. si el mismo esta disponible
        """
        price_str = self._get_price_cost(price_str_1)
        if price_str == self.PRICE_NOT_FOUND:
            price_str = self._get_price_cost(price_str_2)
        return float(price_str)

    def _get_price_ship(self, price_str)->str:
        return price_shipping_or_err(price_str,
                                    self.PRICE_NOT_FOUND,
                                    self.pattern_price_shipping)

    def get_price_ship(self,price_str_1:str, price_str_2:str)->float:
        """
        Recibe dos string con informacion referente al costo de envio
        Retorna el precio de envio. si el mismo esta disponible
        """
        if not price_str_1 and not price_str_2:
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

        variations_data = dict()
        if js_obj != '{':
            try:
                py_obj = demjson.decode(js_obj)
                variations_data = py_obj['asinVariationValues']
            except Exception:
                logging.getLogger('log_print').error(f'Error extrayendo los datos de las variacion en del dataToReturn.')
                logging.getLogger('log').error(f'Error extrayendo los datos de las variacion en del dataToReturn en el objecto {js_obj}.')

        return list(variations_data.keys())

    def get_info_product(self, elements:dict, sku:str, bodyHTML:str)->dict:
        """
        Retorn la informacion completa de un producto si este existe. de lo contrario
        retorna un diccionario vacio
        """
        title = self.get_title(elements['title'])
        if not title.strip():
            return dict()

        price_product = self.get_price_cost(elements['cost_price1'],
                                            elements['cost_price2'])
        currency = elements['currency']
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
            "price": {"product": price_product, "shipping": price_shipping, "currency":currency},
            "dimensions": dimensions,
            "weight":weight,
            "quantity": quantity,
            "link": self.url_origin.replace('sku',sku)
        }
        logging.getLogger("log_print_full").debug(f"{product['title']} {product['price']} {product['sku']}")
        return product

    async def get_data(self, *args, **kwargs)->tuple:
        """
        Retorna los elementos predefinidos por los selectores
        en el respectivo fichero .yaml y el cuerpo HTMl de la pagina
        Return elements:dict, bodyHTML:str
        """
        pass

    async def get_product(self, sku:str)->dict:
        url = self.url_origin.replace('sku',sku)
        elements, bodyHTML = await self.go_to_amazon(url, func=self.get_data,
                                                    selectors='new')

        product = self.get_info_product(elements=elements, sku=sku,
                                            bodyHTML=bodyHTML)
        return product

    async def get_product_and_variations(self, sku:str)->list:
        """
        Recibe el sku y retorna una lista de dictionarios de
        self.get_info_product
        """
        pass

    async def new_product(self, sku:str):
        """
        Scrapea un producto y sus variaciones desde la pagina de amazon y lo
        inserta en la base de datos
        """
        products = await self.get_product_and_variations(sku)
        logging.getLogger('log_print').info(f'Inserting {len(products)} products in the database')
        # await insert_items_in_database(products)

    async def get_news_skus_in_page(self, skus:list):
        skus = set(skus)
        logging.getLogger('log_print').info(f'Products found on the page: {len(skus)}')
        skus_in_database = await ProductModel().skus_in_database()
        return [sku for sku in skus if sku not in skus_in_database]

    async def update_product(self, product):
        elements, _ = await self.go_to_amazon(url=product['provider_link'],
                                            func=self.get_data, selectors='update')

        cost_price = self.get_price_cost(elements['cost_price1'],
                                                elements['cost_price2'])
        product['currency'] = elements['currency']
        product['cost_price'] = cost_price if elements['title'] else float(self.PRICE_NOT_FOUND)
        product['ship_price'] = self.get_price_ship(elements['ship_price1'],
                                                    elements['ship_price2'])
        product['quantity'] = self.get_quantity(elements['quantity']) if (
                                                product['cost_price'] > 0) else 0
        product['last_update'] = datetime.now()

        message = {
            'cost_price': product['cost_price'],
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

    async def go_to_amazon(self, url:str, func, *args, **kwargs):
        pass

    def get_skus(self)->list:
        pass

    async def scraper_pages(self, uri:str, number_page:int=0):
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

            all_the_skus = await self.go_to_amazon(url, func=self.get_skus)

            if not all_the_skus:
                logging.getLogger('log_print').info(f'Finish Scraping in page number {number_page-1}')
                break
            # skus = self.get_news_skus_in_page(all_the_skus)
            skus = all_the_skus
            logging.getLogger('log_print').info(f'New products for scrape in page: {len(skus)}')
            if not skus:
                continue

            products_coros = [self.new_product(sku) for sku in skus]
            await asyncio.gather(*products_coros)


class PyppeteerScraper(CtrlsScraper):
    _sem_ = asyncio.Semaphore(1)

    _selectors_new_ = None
    _selectors_update_ = None

    def __init__(self, country:str='usa'):
        super().__init__()
        self.country = country

    @property
    def selectors_new(self):
        if not self._selectors_new_:
            self._selectors_new_ = get_yaml(self.path_new)
        return self._selectors_new_

    @property
    def selectors_update(self):
        if not self._selectors_update_:
            self._selectors_update_ = get_yaml(self.path_update)
        return self._selectors_update_

    def get_selectors(self, _type_:str):
        if _type_ == 'new':
            return self.selectors_new
        elif _type_ == 'update':
            return self.selectors_new

    async def init_my_pyppeteer(self):
        profile = f'scraper_{self.country}'
        if not self.my_pyppeteer:
            self.my_pyppeteer = MyPyppeteer(profile)
            await self.my_pyppeteer.connect_browser()
            await self.my_pyppeteer.init_pool_pages(self.sem._value)

    async def go_to_amazon(self, url:str, func, *args, **kwargs):
        await self.init_my_pyppeteer()
        async with self.sem:
            id_page, page = self.my_pyppeteer.get_page_pool()

            while True:
                logging.getLogger("log_print_full").debug(f"URL: {url}")
                await page.goto(url)
                input_chatpcha = await page.querySelector('[id="captchacharacters"]')
                if not input_chatpcha:
                    break
                img_draw = await page.querySelector('form img')
                img = await self.my_pyppeteer.get_attribute(img_draw,'src',page)
                await page.click(input_chatpcha)
                value_chatpcha = input(f'Ingrese la solucion del chatpcha {img} :')
                await page.keyboard.type(value_chatpcha)
                page = await self.my_pyppeteer.change_page(page)

            response = await func(page, *args, **kwargs)
            self.my_pyppeteer.close_page_pool(id_page)
        return response

    async def get_data(self, page, *args, **kwargs)->tuple:
        selectors = self.get_selectors(kwargs['selectors'])
        elements = dict()
        for item in selectors:
            if selectors[item]['multiple']:
                elements[item] = await self.my_pyppeteer.get_property_from_querySelectorAll(
                    selector=selectors[item]['css'],
                    attr=selectors[item]['pyppeteer'],
                    page=page
                )
            else:
                element = await self.my_pyppeteer.get_property_from_querySelector(
                    selector=selectors[item]['css'],
                    attr=selectors[item]['pyppeteer'],
                    page=page
                )
                elements[item] = element if element else ''

        bodyHTML = await page.evaluate("() => document.body.innerHTML")
        return elements, bodyHTML

    async def get_skus(self, page):
        skus_draw = await page.evaluate("""
            () => {
                skus_elements = document.querySelectorAll('.s-result-list > div')
                return Array.from(skus_elements).map( sku => sku.getAttribute('data-asin'))
            }
        """)
        return [sku for sku in skus_draw if sku]

    async def get_product_and_variations(self, sku:str):
        url = self.url_origin.replace('sku',sku)

        elements, bodyHTML = await self.go_to_amazon(url,func=self.get_data,
                                                    selectors='new')
        skus = self.get_skus_data(bodyHTML)

        if sku in skus:
            skus.remove(sku)
        
        product = self.get_info_product(elements, sku, bodyHTML)

        products = [product] if product else []
        products_coros = [self.get_product(sku) for sku in skus]
        if products_coros:
            products += await asyncio.gather(*products_coros)
        return [product for product in products if product]


class CurlScraper(CtrlsScraper):
    _sem_ = asyncio.Semaphore(1)
    sleep_avg = 5
    cookies = {
        "session-id":"132-4528637-2870205",
        "ubid-main":"130-0267183-0060640",
        "lc-main":"es_US",
        "i18n-prefs":"USD",
    }
    _extractor_skus_ = None
    _extractor_new_ = None
    _extractor_update_ = None
    _web_client_ = WebClient()

    def __init__(self, country):
        super().__init__()
        self.country = country
        if country == 'mx':
            self.url_origin = self.url_origin.replace('.com', '.com.mx')
            self.cookies = {"lc-main":"es_US"}
   
    @property
    def extractor_skus(self):
        if not self._extractor_skus_:
            self._extractor_skus_ = Extractor.from_yaml_file(self.path_skus)
        return self._extractor_skus_

    @property
    def extractor_new(self):
        if not self._extractor_new_:
            self._extractor_new_ = Extractor.from_yaml_file(self.path_new)
        return self._extractor_new_

    @property
    def extractor_update(self):
        if not self._extractor_update_:
            self._extractor_update_ = Extractor.from_yaml_file(self.path_update)
        return self._extractor_update_

    def get_extractor(self, _type_):
        if _type_ == 'new':
            return self.extractor_new
        elif _type_ == 'update':
            return self.extractor_update

    @property
    def web_client(self):
        return self._web_client_

    @property
    def sem(self):
        return self._sem_

    async def go_to_amazon(self, url:str, func, *args, **kwargs):
        bodyHTML = ''
        async with self.sem:
            while True:
                logging.getLogger("log_print_full").debug(f"URL: {url}")
                while not bodyHTML:
                    sleep = 2 + random()*(2*self.sleep_avg - 2*2)
                    bodyHTML = await self.web_client.get(uri=url,
                                                        cookies=self.cookies,
                                                        return_data='text')
                    if not bodyHTML:
                        logging.getLogger("log_print_full").warning(f"No hubo un error en la respuesta, reintentando peticion en {sleep}seg")
                        await asyncio.sleep(sleep)
                if ('alt="Dogs of Amazon"' in bodyHTML or 'ref=cs_404_logo' in bodyHTML):
                    logging.getLogger("log_print_full").warning(f"ERROR 404 {url} ")
                if (not 'captchacharacters' in bodyHTML):
                    logging.getLogger("log_print_full").info(f"Peticion a {url} Realizada con exito.\n Luego de {sleep} se liberara el loop")
                    await asyncio.sleep(sleep)
                    break
                sleep = 900
                logging.getLogger("log_print_full").warning(f"APARECIO EL CAPTCHA. Fecha: {datetime.now()}. esperando {900}seg")
                await asyncio.sleep(sleep)
            response = func(bodyHTML,*args, **kwargs)
        return response

    def get_data(self, bodyHTML, *args, **kwargs)->tuple:
        _type_ = kwargs['selectors']
        extractor = self.get_extractor(_type_)
        elements =  extractor.extract(bodyHTML)
        for key in elements:
            if not elements[key]:
                elements[key] = ''

        return elements, bodyHTML

    def get_skus(self, bodyHTML):
        result = self.extractor_skus.extract(bodyHTML)
        return [sku for sku in result['skus'] if sku]

    async def get_product_and_variations(self, sku:str):
        url = self.url_origin.replace('sku',sku)

        elements, bodyHTML = await self.go_to_amazon(url,func=self.get_data,
                                                    selectors='new')
        skus = self.get_skus_data(bodyHTML)

        if sku in skus:
            skus.remove(sku)

        product = self.get_info_product(elements, sku, bodyHTML)

        products = [product] if product else []
        products_coros = [self.get_product(sku) for sku in skus]
        if products_coros:
            products += await asyncio.gather(*products_coros)
        return [product for product in products if product]
