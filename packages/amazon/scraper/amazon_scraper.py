from packages.my_pyppeteer.ctrls import MyPyppeteer
from packages.core.utils.app_loop import AppLoop
from aiohttp import web
import asyncio
import os 


dir_path = os.path.dirname(os.path.realpath(__file__))
class AmazonScraper:
    """
        Controlador para obtener los datos de los productos
    """

    def __init__(self):
        self.PATH_LOGIN = 'https://www.amazon.com/gp/yourstore'
        self._product_url_ = None
        self.sem = asyncio.Semaphore(4)

    @property
    def product_url(self):
        return self._product_url_

    @product_url.setter
    def product_url(self, url):
        self.product_url = url

    async def login(self, email: str, password: str) -> None:
        """
            Logueo en Amazon, recibe el email y la contraseña del usuario
        """

        browser, page = await MyPyppeteer('amazon').connect_browser()
        page = await browser.newPage()
        await page.goto(self.PATH_LOGIN)

        await page.focus('#ap_email')
        await page.keyboard.type(email)
        await page.keyboard.press('Enter')

        await page.focus('#ap_password')
        await page.keyboard.type(password)
        await page.keyboard.press('Enter')

    async def get_title(self, page: MyPyppeteer.page) -> str:
        """
            Retorna el titulo de la Publicacion
        """

        return await MyPyppeteer().get_property_for_selector(
            '#productTitle', 'innerText', page)

    async def get_desc(self, page: MyPyppeteer.page) -> str:
        """
            Retorna La descripcion del producto
            (en caso de poseerla)
        """

        with open(f'{dir_path}/amazon_scraper.getDesc.js') as file:
            script_js = file.read()

        return await page.evaluate(script_js)

    async def get_info(self, page: MyPyppeteer.page) -> dict:
        """
            Retorna atributos importantes para el negocio, tales como
            SKU, dimensiones, peso del producto y del envio, numero del modelo, entro otros
        """
    
        with open(f'{dir_path}/amazon_scraper.getInfo.js') as file:
            script_js = file.read()
        return await page.evaluate(script_js)

    async def get_feature(self, page:MyPyppeteer.page) -> dict:
        """
            Retorna las caracteristicas del producto, Estas son las que estan situaldas al
            lado de las variaciones en el WebSite de Amazon.
        """

        with open(f'{dir_path}/amazon_scraper.getFeatures.js') as file:
            script_js = file.read()
        return await page.evaluate(script_js)

    async def get_variations(self, page:MyPyppeteer.page) -> dict:
        """
            Retorna las Variaciones del producto con su respectivos precios
            e imagenes.
        """

        with open(f'{dir_path}amazon_scraper.getVariations.js') as file:
            script_js = file.read()
        return await page.evaluate(script_js)
        