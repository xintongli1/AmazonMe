from mongo_database.mongo import export_to_mong
from tools.tool import rand_proxies
from scrapers.scraper import Amazon
import asyncio
import time


if __name__ == '__main__':

    async def solve_captcha(url:str, content: str = None, file_name: str = None):
        return await Amazon(url, None).bypass_captcha_and_get_elements(content, file_name)


    async def get_product_info_by_url(url: str):
        amazon = Amazon(url, None)
        return await amazon.scrape_product_info()


    async def export_search_results(base_url: str, csv: bool = True, proxy: bool = False):
        """
        :param url: The URL of the search results page
        :param csv: If true then export to CSV else to MongoDB
        :param proxy: Toggle proxy rotation
        :return:
        """
        status = await Amazon(base_url, None).status()

        if status == 503:
            return "503 response. Please try again in few minutes."

        if csv:
            if proxy:
                amazon = Amazon(base_url, None)
                return await amazon.export_csv()
            else:
                amazon = Amazon(base_url, f"http://{rand_proxies()}")
                return await amazon.export_csv()
        else:
            if proxy:
                mongo_to_db = await export_to_mong(base_url, f"http://{rand_proxies()}")
            else:
                mongo_to_db = await export_to_mong(base_url, None)
            return mongo_to_db


    # Start the timer to measure how long the wb scraping process takes
    start_time = time.time()
    # Run the async main function and run the scraper:
    # results = asyncio.run(export_search_results("https://www.amazon.ca/s?k=deep+learning&ref=nb_sb_noss_2", csv=True, proxy=False))
    results = asyncio.run(solve_captcha("https://www.amazon.ca/Deep-Learning-Ian-Goodfellow/dp/0262035618/ref=sr_1_2?crid=2WNCXG6ZUMS6S&dib=eyJ2IjoiMSJ9.XlOY_4EzkkbmP1JnvaZd2g6PqAIKXnKtbDq30_nsmpDaG7NkUENTzpZIaiEsqjbCNRCFixX4CUZnj5H-Nl5rdc2EyjuTdCofgPMb21i-oA4DbnhchKb6B4-KiFNndVuwTgeyB6YEZkW7Ay6VhqYVMaOp2Wi06Js91bBjDCFVQaRGwv97naNFlkZRMJ75A8D72Bma2KjkIBxxcB6anuD9VKUjeh43UdzPk_ZzDMW-fyeoHXs554qUohfm4fbpiL7nfhgiSdFI3ys5FGu30OaxgSzXrqRfKLYgzwi5Wb6VRhY._A0h6lRV13uDOZuWErvRgCygTMZhDEZptHN1S-XS5gg&dib_tag=se&keywords=deep+learning&qid=1714493706&sprefix=%2Caps%2C106&sr=8-2"))
    end_time = time.time()
    print(results)
    # Calculate and print the total time taken to scrape the data:D
    execution_time = round(end_time - start_time, 2)
    print(f"Took {execution_time} seconds | {round(execution_time / 60, 2)} minutes.")

