from packages.my_pyppeteer.ctrls import MyPyppeteer
import re
import logging
import json
import asyncio

class CtrlsScraper:
    """
    - Title #Done
    - Images #Done
    - Description #Done_ENG
    - Attribute
    - sku
    - variations
    - color
    - brand
    - dimesions
    - weight
    """
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
    sem = asyncio.Semaphore(3)
    url_origin = {
        # "Ebay": f"https://www.ebay.com/itm/{sku}",
        "Amazon": f"https://www.amazon.com/dp/sku",
    }
    async def get_product(self, sku:str, country='usa', provider='Amazon'):
        profile_scraper = 'scraper'
        profile_scraper = f'{profile_scraper}_{country}'
        async with self.sem:
            browser, page = await MyPyppeteer(profile_scraper).connect_browser()
            page = await browser.newPage()

            cost_product = await self.switch(provider, sku, page)
            await page.close()
            return cost_product

    async def switch(self, provider, sku:str, page):
        if provider in self.url_origin:
            url = self.url_origin[provider].replace('sku',sku)
            logging.getLogger("log_print_full").debug(f"URL: {url}")
            await page.goto(url)
            while await page.querySelector('[id="captchacharacters"]'):
                page.setDefaultNavigationTimeout(0)
                breakpoint()
                await page.goto(url)

            if (provider == 'Amazon'):
                res = await self.get_product_amazon(page, sku)

            return self.wrap_contex(res)

        else:
            logging.getLogger("log_print_full").error(
                f"La URL no corresponde con ninguno de los scraper de tiendas({self.url_origin})"
            )

    async def get_info_product(self, page):
        """
        Esta funcion obtenie los datos del producto de la interfaz del usuario, si
        el elemento con el precio no existe, asumimos que el producto
        no se encuentra disponible.
        """
        # PRICE PRODUCT AND PRICE SHIPPING
        pattern_price = r'(\d+\.?\d*)'
        pattern_price_shipping = r'(\d+\.?\d*) [Ss]hipping'

        price_element = await page.querySelector("#priceblock_ourprice")
        price_draw = await MyPyppeteer().get_property(
            price_element, "innerText", page
        )
        price_draw = price_draw if price_draw else ''
        match = re.findall(pattern_price, price_draw)
        if not match:
            price_product_str = self.PRICE_NOT_FOUND
        else:
            price_product_str = match[len(match) - 1]

        price_shipping_element = await page.querySelector(
            "#ourprice_shippingmessage"
        )
        price_shipping_draw = await MyPyppeteer().get_property(
            price_shipping_element, "innerText", page
        )
        price_shipping_draw = price_shipping_draw if price_shipping_draw else ''
        price_shipping_str = self.price_or_err(
            pattern_price_shipping, price_shipping_draw, self.PRICE_NOT_FOUND
        )
        if price_shipping_str == self.PRICE_NOT_FOUND:
            price_shipping_str = self.price_shipping_or_err(
                price_shipping_draw, "0"
            )
        if re.match(' no ship ', price_shipping_draw):
            price_shipping_str = self.PRICE_NOT_FOUND 

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
        images = [re.sub(r'\._.+_','',image) for image in images_draw]
        # IMAGES #END

        # DESCRIPTION
        description_element = await page.querySelector('#productDescription p')
        description = await MyPyppeteer().get_property(
            description_element, "innerText", page
        )
        # DESCRIPTION #END
        # ATTRIBUTES
        attributes_draw = await page.evaluate(
            """
                () => {
                    let attributes = {}

                    const getAttributeBySelector = (selector, attributes) => {
                        rows = document.querySelectorAll(selector)
                        rows.forEach(row => {
                        key = row.children[0].innerText.replace(/ /g, '_').toLowerCase()
                        value = row.children[1].innerText
                        attributes[key] = value
                        });
                        return attributes
                    }

                    attributes = getAttributeBySelector('#prodDetails tr', attributes)

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
            if 'dimensions' in attribute_key:
                _dimensions_ = dict()
                # Las dimensiones vienen en este formato "7.1 x 4 x 1.9 inches"
                dimensions_draw = attributes_draw[attribute_key].split(';')
                dimensions_draw = dimensions_draw[0].split('x')
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

            elif 'weight' in attribute_key:
                weight_draw = attributes_draw[attribute_key].split(' ')
                _weight_ = self.weight_converter(float(weight_draw[0]), weight_draw[1].lower())

                if weight < _weight_:
                    weight = _weight_

            elif 'asin' in attribute_key:
                sku = attributes_draw[attribute_key]

            elif attribute_key not in ('customer_reviews', 'best_sellers_rank'):
                attributes[attribute_key] = attributes_draw[attribute_key]
        # ATTRIBUTES #END
        product = {
            "sku": sku,
            "title": title,
            "description": description,
            "attributes": attributes,
            "images": images,
            "price": {"product": price_product, "shipping": price_shipping},
        }
        return product

    async def get_product_amazon(self, page, sku):
        variations_element = await page.querySelectorAll('[id^="variation_"]')
        products = list()
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
            
            variations_draw = await page.evaluate(
                '() => {\n'+json_string+'\nreturn dataToReturn.dimensionToAsinMap\n'+'}'
            )
        
        if variations_draw:
            variations = list(variations_draw.values())
            variations.remove(sku)
        else:
            variations = list()

        product = await self.get_info_product(page)
        products.append(product)
        for variation in variations:
            await page.goto(self.url_origin['Amazon'].replace('sku',variation))
            product = await self.get_info_product(page)
            products.append(product)
        print(len(products))
        return products

    def price_or_err(self, pattern: str, string, value_default, pos=0) -> str:
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
            print(e)
            return self.CRITICAL_ERROR

    def price_shipping_or_err(self, string, value_default) -> str:
        """
        Esta funcion recibe un string donde se buscara el texto 'FREE Shipping,\
        si lo encuentra retorna 0, de lo contrario retorna value_default.
        """
        match = re.search("FREE Shipping", string)
        if match:
            return "0"
        else:
            return value_default

    def wrap_contex(self, products: list) -> dict:
        if products:
            for product in products:
                price_product = int(product.get("price").get("product"))
                price_shipping = int(product.get("price").get("shipping"))
                if (price_product < 0) or (price_shipping < 0):
                    price_product_str = str(price_product)
                    price_shipping_str = str(price_shipping)

                    level = (
                        price_product_str
                        if price_product < price_shipping
                        else price_shipping_str
                    )
                    msg = f'PRODUCTO {product.get("sku")} {self.message[level]}.'
                    if level == self.CRITICAL_ERROR:
                        logging.getLogger("log_print").error(msg)
                    else:
                        logging.getLogger("log_print").warning(msg)

                    with open("storage/products_review_amazon.log", "a") as f:
                        f.write(
                            f'{self.message[level]} - item: {product["price"]} - URL: https://www.amazon.com/dp/{product.get("sku")}\n'
                        )
                    print(product)
                    return {"ok": False, "msg": msg, "data":product}
            return {"ok": True, "data": products}
        else:
            return {"ok": False, "msg": self.PRODUCT_NOT_FOUNT}

    def weight_converter(self, count, unit):
        converter = {
            'ounces': 28.3495,
            'ounce': 28.3495,
            'oz': 28.3495,
            'pounds': 453.59237,
            'pound': 453.59237,
        }
        return converter[unit]*count

    def distance_converter(self, count, unit):
        converter = {
            'inches': 2.54,
            'inche': 2.54,
            'in': 2.54,
        }
        return converter[unit]*count

    def get_skus_from_page(self, page):
        pass
