from cleo import Command
from packages.core.utils.app_loop import AppLoop
from .ctrls import CtrlsScraper

class AllCommands:
    class Test(Command):
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