from cleo import Command
from packages.core.utils.app_loop import AppLoop
from packages.core.utils.config import Config
from .ctrls import CtrlsScraper
from .models import AttributeModel

class AllCommands:
    class ScraperProduct(Command):
        """
        Scrapear producto de amazon

        scraper:amazon_scan_product
        {--sku= : sku}
        {--country= : country}
        """

        def handle(self):
            sku = self.option('sku')
            country = self.option('country') if self.option('country') else 'usa'
            AppLoop().get_loop().run_until_complete(CtrlsScraper().get_product(sku, country))

    class ScraperPage(Command):
        """
        Scrapear todos los productos de una busqueda en amazon

        scraper:amazon_scan_pages
        {--country= : country}
        {--uri= : uri}
        {--init-page= : init-page}
        """

        def handle(self):
            country = self.option('country') if self.option('country') else 'usa'
            init_page = int(self.option('init-page'))-1 if self.option('init-page') else 0
            uri = self.option('uri')
            AppLoop().get_loop().run_until_complete(CtrlsScraper().scraper_pages(uri, country, init_page))