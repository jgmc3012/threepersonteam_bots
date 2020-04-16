from cleo import Command
from packages.core.utils.app_loop import AppLoop
from packages.core.utils.config import Config
from .ctrls import PyppeteerScraper
from .ctrls import CurlScraper
from .models import AttributeModel

import json

class AllCommands:
    class ScraperPyppeteerProduct(Command):
        """
        Scrapear producto de amazon

        scraper:pyppeteer_scan_product
        {--sku= : sku}
        {--country= : country}
        """

        def handle(self):
            sku = self.option('sku')
            country = self.option('country') if self.option('country') else 'usa'
            AppLoop().get_loop().run_until_complete(
                PyppeteerScraper(country).get_product(sku))

    class ScraperPyppeteerPage(Command):
        """
        Scrapear todos los productos de una busqueda en amazon

        scraper:pyppeteer_scan_pages
        {--country= : country}
        {--uri= : uri}
        {--init-page= : init-page}
        """

        def handle(self):
            country = self.option('country') if self.option('country') else 'usa'
            init_page = int(self.option('init-page'))-1 if self.option('init-page') else 0
            uri = self.option('uri')
            AppLoop().get_loop().run_until_complete(
                PyppeteerScraper(country).scraper_pages(uri, init_page))

    class ScraperCurlUpdateProduct(Command):
        """
        Scrapear y actualizar los productos de la base de datos.

        scraper:curl_update_products
        """

        def handle(self):
            AppLoop().get_loop().run_until_complete(CurlScraper().update_products())

    class ScraperCurlUpdateProductTest(Command):
        """
        Imprimir los datos scrapeador del actulizador. Solo para testear

        scraper:curl_print_product
        {--sku= : sku}
        {--country= : country}
        """

        def handle(self):
            sku = self.option('sku')
            country = self.option('country') if self.option('country') else 'usa'
            AppLoop().get_loop().run_until_complete(CurlScraper(country).update_product({
                'provider_sku':sku,
                'provider_link': f'https://amazon.com.mx/-/es/dp/{sku}'
            }))

    class ScraperCurlPage(Command):
        """
        Scrapear todos los productos de una busqueda en amazon

        scraper:curl_scan_pages
        {--uri= : uri}
        {--init-page= : init-page}
        {--country= : country}
        """

        def handle(self):
            country = self.option('country') if self.option('country') else 'usa'
            init_page = int(self.option('init-page'))-1 if self.option('init-page') else 0
            uri = self.option('uri')
            AppLoop().get_loop().run_until_complete(
                CurlScraper(country).scraper_pages(uri, init_page))
