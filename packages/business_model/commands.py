from cleo import Command
from packages.core.utils.app_loop import AppLoop
from .ctrls import CtrlBusiness

class AllCommands:
    class Business(Command):
        """
        Business

        business:get_price_products

        {--seller-id=:seller-id}
        {--business=:business}
        """

        def handle(self):
            seller_id = int(self.option('seller-id'))
            business = self.option('business').lower().strip()
            switch = {
                'alfredo':CtrlBusiness().alfredo_form,
                'dominicana':CtrlBusiness().dominicana_form
            }
            AppLoop().get_loop().run_until_complete(CtrlBusiness().calculate_price(
                seller_id=seller_id,
                func=switch[business]
                ))

    class CleanDescriptions(Command):
        """
        Business

        business:clean_descriptions

        """

        def handle(self):
            AppLoop().get_loop().run_until_complete(CtrlBusiness().clean_descriptions())