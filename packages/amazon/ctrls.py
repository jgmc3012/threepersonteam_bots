from packages.amazon.scraper.amazon_scraper import AmazonScraper

class CtrlAmazon():
    """Controlador de Amazon"""

    def login(self, email, password):
        AmazonScraper().login(email, password)