from cleo import Command
from packages.core.utils.app_loop import AppLoop
from .ctrls import CtrlBusiness

class AllCommands:
    class Business(Command):
        """
        Business

        business:get_price_products
        {--seller-id=:seller-id}
        """

        def handle(self):
            seller_id = int(self.option('seller-id'))
            AppLoop().get_loop().run_until_complete((CtrlBusiness().mx_alfredo(seller_id)))