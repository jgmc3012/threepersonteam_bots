from cleo import Command
from packages.core.utils.app_loop import AppLoop
from .ctrls import CtrlsScraper

class AllCommands:
    class Test(Command):
        """
        Scrapear producto de amazon

        scraper:amazon_scan_product
        {--sku= : sku}
        """

        def handle(self):
            sku = self.option('sku')
            AppLoop().get_loop().run_until_complete(CtrlsScraper().get_product(sku))