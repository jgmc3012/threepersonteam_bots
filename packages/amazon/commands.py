from cleo import Command
from packages.core.utils.app_loop import AppLoop
from .ctrls import CtrlAmazon


class AllCommands:

    class Login(Command):
        """
        Logueo en Amazon

        amazon:login
        {--email= : email}
        {--password= : password}
        """
        
        def handle(self):
            email = self.option('email')
            password = self.option('password')
            loop = AppLoop().get_loop()
            res = loop.run_until_complete(self.handleAsync(email, password)) 
            

        async def handleAsync(self, email, password):
            await CtrlAmazon().login(email,password)