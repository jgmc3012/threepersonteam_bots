from cleo import Command
from packages.core.utils.app_loop import AppLoop
from .ctrls import CtrlAnicam

class AllCommands:
    class Shiping_prices(Command):
        """
        Test

        anicam:shipping_prices
        """

        def handle(self):
            AppLoop().get_loop().run_until_complete(CtrlAnicam().shipping_by_product())