from .commands import AllCommands
from cleo import Command
from .ctrls import CtrlsEbayProduct

class setup():
    """setup del modulo demo"""

    def router(self, app):
        ctrl = CtrlsEbayProduct()
        app.router.add_post('/ebay/hi', ctrl.get_products_rq)
        """
            description:
            tag:
        """


    def commands(self, app):
        all_commands = [v for v in AllCommands.__dict__.values() if isinstance(v, type) and issubclass(v, Command)]
        for command in all_commands:
            app.add(command())