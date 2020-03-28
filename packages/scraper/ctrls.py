from packages.my_pyppeteer.ctrls import MyPyppeteer
import re
import logging
import json
import asyncio
from datetime import datetime
from .models import ProductModel, AttributeModel, PictureModel

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
    sem = asyncio.Semaphore(8)
    my_pypperteer = None
    url_origin = "https://www.amazon.com/-/es/dp/sku?psc=1"
    parent_description = re.compile(r'((\w*://)?\w+\.\w+\.\w+)|([\w\-_\d\.]+@[\w\-_\d]+(\.\w+)+)')

    async def init_my_pypperteer(self, profile:str):
        if not self.my_pypperteer:
            self.my_pypperteer = MyPyppeteer(profile)
            await self.my_pypperteer.connect_browser()
            await self.my_pypperteer.init_pool_pages(self.sem._value)
        
    async def get_product(self, sku:str, country='usa'):
        profile_scraper = 'scraper'
        profile_scraper = f'{profile_scraper}_{country}'
        await self.init_my_pypperteer(profile_scraper)
        async with self.sem:
            id_page, page = self.my_pypperteer.get_page_pool()

            url = self.url_origin.replace('sku',sku)
            await self.goto(url,page)
            data = await self.get_product_amazon(page, sku)
            self.my_pypperteer.close_page_pool(id_page)
        products = data['products']
        products_coros = [self.get_products(sku) for sku in data['skus']]
        if products_coros:
            products += await asyncio.gather(*products_coros)
        return products

    async def get_products(self, sku):
        async with self.sem:
            id_page, page = self.my_pypperteer.get_page_pool()

            url = self.url_origin.replace('sku',sku)
            await self.goto(url,page)
            product = await self.get_info_product(page, sku)
            self.my_pypperteer.close_page_pool(id_page)
        return product

    async def get_info_product(self, page, sku):
        """
        Esta funcion obtenie los datos del producto de la interfaz del usuario, si
        el elemento con el precio no existe, asumimos que el producto
        no se encuentra disponible.
        """
        # PRICE PRODUCT AND PRICE SHIPPING
        pattern_price = r'(\d+\.?\d*)'
        pattern_price_shipping = r'(\d+\.?\d*) [Ee]nvío'

        price_product_element = await page.querySelector("#priceblock_ourprice")
        if price_product_element:
            price_shipping_element = await page.querySelector(
                "#ourprice_shippingmessage"
            )
            if not price_shipping_element: 
                price_shipping_element = await page.querySelector(
                    '[data-feature-name="desktop_qualifiedBuyBox"]'
                )
        else:
            price_product_element = await page.querySelector('[data-feature-name="priceInsideBuyBox"]')
            # Este elemento contine MUCHA mas informacion que el precio de envio
            # es la unica manera que haya, puede que conlleve a Bugs
            price_shipping_element = await page.querySelector(
                '[data-feature-name="desktop_qualifiedBuyBox"]'
            )
        price_product_draw = await MyPyppeteer().get_property(
            price_product_element, "innerText", page
        )
        price_shipping_draw = await MyPyppeteer().get_property(
            price_shipping_element, "innerText", page
        )

        price_shipping_draw = price_shipping_draw.replace(',','') if price_shipping_draw else ''
        price_product_draw = price_product_draw.replace(',','') if price_product_draw else ''

        price_product_str = self.price_or_err(
            pattern_price, price_product_draw, self.PRICE_NOT_FOUND
        )
        if ' no se envía ' in price_shipping_draw:
            price_shipping_str = self.PRODUCT_NOT_SHIP
        else:
            price_shipping_str = self.price_or_err(
            pattern_price_shipping, price_shipping_draw, self.PRICE_NOT_FOUND
            )
            if price_shipping_str == self.PRICE_NOT_FOUND:
                price_shipping_str = self.price_shipping_or_err(
                    price_shipping_draw, self.PRICE_NOT_FOUND
                )

        price_product = float(price_product_str)
        price_shipping = float(price_shipping_str)
        # PRICE PRODUCT AND PRICE SHIPPING #END
        # TITLE
        title_element = await page.querySelector("#title")
        title = await MyPyppeteer().get_property(
            title_element, "innerText", page
        )
        # TITLE #END
        # IMAGES
        await page.evaluate("""
        () => {
            const event = new MouseEvent('mouseover', {
            'view': window,
            'bubbles': true,
            'cancelable': true
            });

            buttons = document.querySelectorAll('#altImages .item')
            buttons.forEach( btn => {btn.dispatchEvent(event)})
        }
        """)
        images_element = await page.querySelectorAll('#main-image-container img')
        images_coros = [MyPyppeteer().get_property(
            image, "src", page
        ) for image in images_element]
    
        images_draw = await asyncio.gather(*images_coros)
        images = [re.sub(r'\._.+_','',image) for image in images_draw if len(image)<255]
        # IMAGES #END

        # DESCRIPTION
        description_element = await page.querySelector('#productDescription p')
        description = await MyPyppeteer().get_property(
            description_element, "innerText", page
        )
        if description:
            description = re.sub(self.parent_description, '', description)
        # DESCRIPTION #END
        # ATTRIBUTES
        attributes_draw = await page.evaluate(
            """
                () => {
                    const getAttributesByList = (attributes, selector) => {
                        let rows = document.querySelectorAll(selector)
                        rows.forEach(row => {
                            row = row.innerText.split(':')
                            if (row.length>1) {
                                let key = row[0].replace(/ /g, '_').toLowerCase()
                                let value = row[1]
                                attributes[key] = value
                            }
                        });
                        return attributes
                    }
                    const getAttributesByTable = (attributes) => {
                        let rows = document.querySelectorAll('#prodDetails tr')
                        rows.forEach(row => {
                            let key = row.children[0].innerText.replace(/ /g, '_').toLowerCase()
                            let value = row.children[1].innerText
                            attributes[key] = value
                        });
                        return attributes
                    }

                    let attributes = {}
                    attributes = getAttributesByTable(attributes)
                    attributes = getAttributesByList(attributes, '#detail-bullets li')
                    attributes = getAttributesByList(attributes, '#detailBullets li')
                    return attributes
                }
            """
        )
        dimensions = dict()
        weight = 0
        attributes_elements = await page.querySelectorAll('[id^=variation_] .a-row')
        attributes_coros = [MyPyppeteer().get_property(
                attribute, "innerText", page
            ) for attribute in attributes_elements]
        attributes_string = await asyncio.gather(*attributes_coros)
        attributes = dict()
        for attribute_str in attributes_string:
            attribute = attribute_str.split(':')
            name = attribute[0].lower()
            value = attribute[1].lower()
            attributes[name] = value

        for attribute_key in attributes_draw:
            if 'dimensiones' in attribute_key:
                _dimensions_ = dict()
                # Las dimensiones vienen en este formato "7.1 x 4 x 1.9 inches"
                dimensions_draw = attributes_draw[attribute_key].replace(',','').split(';')
                dimensions_draw = dimensions_draw[0].split('x')
                if len(dimensions_draw) < 3:
                    continue
                _dimensions_['x'] = float(dimensions_draw[0])
                _dimensions_['y'] = float(dimensions_draw[1])
                dimensions_draw = dimensions_draw[2].strip().split(' ')
                _dimensions_['z'] = float(dimensions_draw[0])
                unit = dimensions_draw[1].lower()

                _dimensions_['x'] = self.distance_converter(_dimensions_['x'], unit)
                _dimensions_['y'] = self.distance_converter(_dimensions_['y'], unit)
                _dimensions_['z'] = self.distance_converter(_dimensions_['z'], unit)
                if dimensions:
                    if (dimensions['x']*dimensions['y']*dimensions['z']) < (_dimensions_['x']*_dimensions_['y']*_dimensions_['z']):
                        dimensions = _dimensions_
                else:
                    dimensions = _dimensions_

            elif 'peso_' in attribute_key:
                weight_draw = attributes_draw[attribute_key].strip().replace(',','').split(' ')
                _weight_ = self.weight_converter(float(weight_draw[0]), weight_draw[1].lower())

                if weight < _weight_:
                    weight = _weight_

            elif 'asin' in attribute_key:
                sku = attributes_draw[attribute_key].strip()

            elif attribute_key not in (
                'opinión_media_de_los_clientes',
                'clasificación_en_los_más_vendidos_de_amazon',
                'producto_en_amazon.com_desde',
                'envío_nacional',
                ) and attributes_draw[attribute_key] not in ('clic', 'aquí') :
                attributes[attribute_key] = attributes_draw[attribute_key]
        # ATTRIBUTES #END
        # CATEGORY
        categories = await page.evaluate("""
            _ => {
                category = document.querySelector('#wayfinding-breadcrumbs_feature_div')
                if (category) {
                    return category.innerText.split('›')
                }
            }
        """)
        if categories:
            category_root = categories[0].strip()
            category_child = categories[-1].strip()
        else:
            category_root = None
            category_child = None
        # CATEGORY #END
        # QUANTITY
        quantity = await page.evaluate("""
            () => {
                quantity_elemet = document.querySelector("#quantity")
                if (quantity_elemet) {
                    return quantity_elemet.children[quantity_elemet.childElementCount-1].value
                }
            }
        """)
        if  quantity:
            quantity = int(quantity)
        else:
            quantity = 1
        # QUANTITY #END
        product = {
            "sku": sku,
            "title": title.replace('"','').replace("'",'') if title else "",
            "description": description.replace('"','').replace("'",'') if description else "",
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

    async def goto(self, url:str, page):
        await page.goto(url)
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

    async def get_product_amazon(self, page, sku):
        variations_element = await page.evaluate("""
        () => {
            let variationsElement = document.querySelectorAll('[id^="variation_"]')
            return Array.from(variationsElement).map( variation =>{
                name = variation.getAttribute('id').replace('variation_', '')
                select = variation.querySelector('select')
                return {
                    name,
                    select
                }
            })
        }
        """)
        products = list()
        skus = list()
        if variations_element:
            read_JSON = False
            json_string = ''
            bodyHTML = bodyHTML = await page.evaluate("() => document.body.innerHTML")
            for line in bodyHTML.split('\n'):
                if read_JSON:
                    if not ';' in line:
                        json_string += line
                    else:
                        json_string += '}'
                        break
                elif 'twister-js-init-dpx-data' in line:
                    read_JSON = True
            variations_data = await page.evaluate(
                '() => {\n'+json_string+'\n try {\n return dataToReturn.asinVariationValues} \n catch (error) {console.error(error)} \n'+'}'
            )
            if variations_data:
                skus += variations_data.keys()
            if sku in skus:
                skus.remove(sku)
                product = await self.get_info_product(page, sku)
                products.append(product)
            return {
                'products':products,
                'skus':skus
            }
        else:
            product = await self.get_info_product(page, sku)
            products.append(product)
            return {
                'products':products,
                'skus':skus
            }

    def price_or_err(self, pattern: str, string, value_default, pos=-1) -> str:
        """
        Este funcion recibe un patron con AL MENOS un grupo, una cadena de
        caracteres y una posicion del grupo que se desea retornar.

        En caso que el patron no se encuentre en la cadena retornara un value_default.
        """
        if string is None:
            return 0

        try:
            match = re.search(pattern, string)
            if match:
                return match.groups()[pos]
            else:
                return value_default
        except Exception as e:
            logging.getLogger("log_print_full").error(e)
            return self.CRITICAL_ERROR

    def price_shipping_or_err(self, string, value_default) -> str:
        """
        Esta funcion recibe un string donde se buscara el texto 'FREE Shipping,\
        si lo encuentra retorna 0, de lo contrario retorna value_default.
        """
        if 'FREE Shipping' in string or 'Envío GRATIS' in string:
            return "0"
        else:
            return value_default

    def weight_converter(self, count, unit):
        converter = {
            'ounces': 0.0625,
            'ounce': 0.0625,
            'onzas': 0.0625,
            'onza': 0.0625,
            'oz': 0.0625,
            'pounds': 1,
            'pound': 1,
            'libras': 1,
            'libra': 1,
            'kilograms':2.20462,
            'kilogram':2.20462,
            'kilogramos':2.20462,
            'kilogramo':2.20462,
            'gramos':2204.62,
            'gramo':2204.62,
        }
        return converter[unit]*count

    def distance_converter(self, count, unit):
        converter = {
            'inches': 1,
            'inche': 1,
            'pulgadas': 1,
            'pulgada': 1,
            'in': 1,
            'centimeters':0.393701,
            'centimeter':0.393701,
            'centimetros':0.393701,
            'centimetro':0.393701,
            'cm':0.393701,
        }
        return converter[unit]*count

    async def get_skus_from_page(self, page):
        skus_draw = await page.evaluate("""
            () => {
                skus_elements = document.querySelectorAll('.s-result-list > div')
                return Array.from(skus_elements).map( sku => sku.getAttribute('data-asin'))
            }
        """)
        return [sku for sku in skus_draw if sku]

    async def scraper_pages(self, uri, country, number_page:int=0):
        time_start = datetime.now()
        profile_scraper = 'scraper'
        profile_scraper = f'{profile_scraper}_{country}'
        products_length = 0
        while True:
            number_page += 1
            logging.getLogger('log_print').info(f'Scraping page number {number_page}')
            await self.init_my_pypperteer(profile_scraper)
            async with self.sem:
                id_page, page = self.my_pypperteer.get_page_pool()
                await self.goto(f'{uri}&page={number_page}', page)
                skus = await self.get_skus_from_page(page)
                self.my_pypperteer.close_page_pool(id_page)

            if not skus:
                logging.getLogger('log_print').info(f'finish Scraping in page number {number_page-1}')
                break
            products_coros = [self.get_product(sku, country) for sku in skus]
            skus_in_database = set(await ProductModel().select())
            skus = [sku for sku in skus if sku not in skus_in_database]
            if not skus:    
                continue
            products_draw = await asyncio.gather(*products_coros)
            products = list()
            for _products_ in products_draw:
                for p in _products_:
                    if p['title']:
                        products.append(p)

            await self.insert_database(products)
            products_length += len(products)

        logging.getLogger("log_print_full").info(f'{datetime.now()-time_start}')
        logging.getLogger("log_print_full").info(f'{datetime.now()}')
        logging.getLogger("log_print_full").info(f'Total de productos Scrapeados {products_length}')

    async def insert_database(self, products_draw:list):
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
                'provider_sku':product['sku'], # :str, (max_length=50, unique=True)
                'provider_link':self.url_origin.replace('sku',product['sku']), # :str, (max_length=255, unique=True)
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
