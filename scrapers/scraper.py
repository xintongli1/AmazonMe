from tools.tool import TryExcept, flat, static_connection, yaml_load, randomTime, userAgents, verify_amazon, export_sheet, filter
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import pandas as pd
import asyncio
import re


class Amazon:
    """
    The Amazon class provides methods for scraping data from Amazon.com.

    Attributes:
        headers (dict): A dictionary containing the user agent to be used in the request headers.
        catch (TryExcept): An instance of TryExcept class, used for catchig exceptions.
        scrape (yaml_load): An instance of the yaml_load class, used for selecting page elements to be scraped.
    """

    def __init__(self, base_url):
        """
        Initializes an instance of the Amazon class.
        """
        self.rand_time = 10 * 60
        self.base_url = base_url
        self.headers = {'User-Agent': userAgents()}
        self.catch = TryExcept()
        self.scrape = yaml_load('selector')


    async def num_of_pages(self):
        """
        Returns the number of pages of search results for the given URL.

        Args:
            url (str): The URL to determine the number of search result pages for.

        Returns:
            int: The number of pages of search results.
        """
        content = await static_connection(self.base_url)
        soup = BeautifulSoup(content, 'lxml')

        # Try except clause for index error, this happens if there are only one page:
        try:
            pages = await self.catch.text(soup.select(self.scrape['pages'])[-1])
        except IndexError:
            pages = '1'

        # the current pages returns "Previous" instead of number, this only happens there only two pages, that's why I have returned the value 2.
        try:
            return int(pages)
        except ValueError:
            return 2


    async def split_url(self):
        """
        Splits a given Amazon URL into multiple URLs, with each URL pointing to a different page of search results.

        Args:
            -url (str): The Amazon URL to be split.

        Returns:
            -list: A list of URLs, with each URL pointing to a different page of search results.
        """

        # Create a list to store the split URLs, and add the orignal URL to it:
        split_url = [self.base_url]

        # Use the 'num_of_pages' method to get the total number of search result pages for the given URL:
        total_pages = await self.num_of_pages()

        # Use the 'static_connection' method to make a static connection to the given URL and get its HTML content:
        content = await static_connection(self.base_url)

        # Making a soup:
        soup = BeautifulSoup(content, 'lxml')

        # Get the URL of the next button on the search result page and costruct the URL of the next search result page:
        next_link = f"""https://www.amazon.com{await self.catch.attributes(soup.select_one(self.scrape['next_button']), 'href')}"""

        for num in range(1, total_pages):
            # Replace the 'page' number in the URL with curren tpage number increment by 1:
            next_url = re.sub(r'page=\d+', f'page={num+1}' , next_link)

            # Replace the 'sr_pg_' parameter in the URL with current page number:
            next_url = re.sub(r'sr_pg_\d+', f'sr_pg_{num}', next_url)

            split_url.append(next_url)

        return split_url


    async def getASIN(self, url):
        """
        Extracts the ASIN (Amazon Standard Identification Number) from the given URL.

        Args:
            url (str): The URL to extract the ASIN from.

        Return:
            str: The ASIN extracted from the URL.

        Raises:
            IndexError: If the ASIN cannot be extracted from the URL.
        """
        pattern = r"(?<=dp\/)[A-Za-z|0-9]+"
        try:
            asin = (re.search(pattern, url)).group(0)
        except Exception as e:
            asin = "N/A"
        return asin


    async def category_name(self):
        """
        Retrieves the category name of search results on the given Amazon search page URL.

        Args:
            -url (str): The Amazon search page URL to retrive category name.

        Raises:
            -None.
        """
        content = await static_connection(self.base_url)
        soup = BeautifulSoup(content, 'lxml')

        try:
            searches_results = soup.select_one(self.scrape['searches_I']).text.strip()
        except AttributeError:
            searches_results = re.sub(r'["]', '', soup.select_one(self.scrape['searches_II']).text.strip())
        return searches_results


    async def product_urls(self, url, max_retries = 13):
        """
        Scrapes product data from the Amazon search results page for the given URL.

        Args:
            -list: A list of dictionaries, with each dictionary containing product data for single product.

        Raises:
            -Expecation: If there is an error while loading the content of the Amazon search results page.
        """

        # Use the 'static_connection' method to download the HTML content of the search results bage
        for retry in range(max_retries):
            try:
                await asyncio.sleep(5)
                content = await static_connection(url)
                soup = BeautifulSoup(content, 'lxml')

                # Check if main content element exists on page:
                try:
                    soup.select_one(self.scrape['main_content'])
                except Exception as e:
                    return f"Content loading error. Please try again in few minutes. Error message: {e}"

                # Get product card contents from current page:
                card_contents = [f"""https://www.amazon.com{prod.select_one(self.scrape['hyperlink']).get('href')}""" for prod in soup.select(self.scrape['main_content'])]
                return card_contents
            except ConnectionResetError as se:
                print(f"Connection lost: {str(se)}. Retrying... ({retry + 1}/{max_retries})")
                if retry < max_retries - 1:
                    await asyncio.sleep(5)  # Delay before retrying
            except Exception as e:
                print(f"Retry {retry+1} failed: {str(e)}")
                if retry < max_retries - 1:
                    await asyncio.sleep(5)  # Delay before retrying

        raise Exception(f"Failed to retrieve valid data after {max_retries} retries.")


    async def crawl_url(self):
        page_lists = await self.split_url()
        coroutines = [self.product_urls(url) for url in page_lists]
        results = await asyncio.gather(*coroutines)
        return flat(results)

    async def scrape_product_info(self, url, max_retries = 13):
        amazon_dicts = []
        for retry in range(max_retries):
            try:
                # Retrieve the page content using 'static_connection' method:
                content = await static_connection(url)
                soup = BeautifulSoup(content, 'lxml')

                product = soup.select_one(self.scrape['name']).text.strip()
                print(product)
                if product == "N/A":
                    raise Exception("Product is 'N/A' retrying...")

                try:
                    # Try to extract the image link using the second first selector.
                    image_link = soup.select_one(self.scrape['image_link_i']).get('src')
                except Exception as e:
                    image_link = await self.catch.attributes(soup.select_one(self.scrape['image_link_ii']), 'src')
                # finally:
                #     # If the image link cannot be extracted, return an error message:
                #     return f'Content loading error. Please try again in few minutes. Error message || {str(e)}.'

                try:
                    availabilities = soup.select_one(self.scrape['availability']).text.strip()
                except AttributeError:
                    availabilities = 'In stock'
                price = await self.catch.text(soup.select_one(self.scrape['price_us']))
                if 'Page' in price.split():
                    price = await self.catch.text(soup.select_one(self.scrape['price_us_i']))
                # return price
                if price != "N/A":
                    price = float(re.sub(r'[$,%()]', '', price))
                try:
                    deal_price = await self.catch.text(soup.select(self.scrape['deal_price'])[0])
                    if 'Page' in deal_price.split():
                        deal_price = "N/A"
                except Exception as e:
                    deal_price = "N/A"
                if deal_price != "N/A":
                    deal_price = float(re.sub(r'[$,%()]', '', deal_price))
                try:
                    savings = await self.catch.text(soup.select(self.scrape['savings'])[-1])
                except IndexError:
                    savings = "N/A"

                store = await self.catch.text(soup.select_one(self.scrape['store']))
                store_link = f"""https://www.amazon.com{await self.catch.attributes(soup.select_one(self.scrape['store']), 'href')}"""

                # Construct the data dictionary containing product information:
                datas = {
                    'Product': product,
                    'Asin': await self.getASIN(url),
                    'Description': ' '.join([des.text.strip() for des in soup.select(self.scrape['description'])]),
                    'Breakdown': ' '.join([br.text.strip() for br in soup.select(self.scrape['prod_des'])]),
                    'Price': price,
                    'Deal Price': deal_price,
                    'You saved': savings,
                    'Rating': await self.catch.text(soup.select_one(self.scrape['review'])),
                    'Rating count': await self.catch.text(soup.select_one(self.scrape['rating_count'])),
                    'Availability': availabilities,
                    'Hyperlink': url,
                    'Image': image_link,
                    'Images': [imgs.get('src') for imgs in soup.select(self.scrape['image_lists'])],
                    'Store': store.replace("Visit the ", ""),
                    'Store link': store_link,
                }

                amazon_dicts.append(datas)
                return amazon_dicts
            except ConnectionResetError as se:
                print(f"Connection lost: {str(e)}. Retrying... ({retry + 1} / {max_retries})")
                if retry < max_retries - 1:
                    await asyncio.sleep(5)  # Delay before retrying.
            except Exception as e:
                print(f"Retry {retry + 1} failed: {str(e)}")
                if retry < max_retries - 1:
                    await asyncio.sleep(4)  # Delay before retrying.

        raise Exception(f"Failed to retrieve valid data after {max_retries} retries.")


    async def scrape_and_save(self, url):
        """
        Scrapes data from a given URL, saves it to a file, and returns the scarped data as a Pandas Dataframe.

        Args:
            -interval (int): Time interval in seconds to sleep before scraping the data.
            -url (str): The URL to scrape data from.

        Returns:
            -pd.DataFrame: A Pandas DataFrame containing the scraped data.

        Raises:
            -HTTPError: If the HTTP request to the URL returns an error status code.
            -Exception: If there is an error while scraping the data.
        """

        random_sleep = await randomTime(self.rand_time)
        await asyncio.sleep(random_sleep)
        datas = await self.scrape_product_info(url)
        return datas


    async def concurrent_scraping(self):
        if await verify_amazon(self.base_url):
            return "I'm sorry, the link you provided is invalid. Could you please provide a valid Amazon link for the product category of your choice?"

        print(f"-----------------------Welcome to Amazon crawler---------------------------------")

        searches = await self.category_name()
        print(f"Scraping category || {searches}.")

        # Pull the number of pages of the category
        number_pages = await self.num_of_pages()
        print(f"Total pages || {number_pages}.")

         # Split the pagination and convert it list of urls
        product_urls = await self.crawl_url()

        print(f"The extraction process has begun and is currently in progress. The web scraper is scanning through all the links and collecting relevant information. Please be patient while the data is being gathered.")
        coroutines = [self.scrape_and_save(url) for url in product_urls]
        dfs = await asyncio.gather(*coroutines)
        return dfs

    async def dataByAsin(self, asin):
        """
        Extracts product information from the Amazon product page by ASIN (Amazon Standard Identification Number).

        Args:
            -asin (str): The ASIN of the product to extract informatio from.

        Returns:
            -dict: A dictionary containing product information, including name, price, rating, rating count, availability,
                   hyperlink, image link, store, and store link.

        Raises:
            -AttributeError: If the product information cannot be extracted from the page.
        """

        # Construct the URL using the ASIN:
        url = f"https://www.amazon.com/dp/{asin}"

        # Retrieve the page content using 'static_connection' method:
        content = await static_connection(url)
        soup = BeautifulSoup(content, 'lxml')

        try:
            # Try to extract the image link using the second first selector.
            image_link = soup.select_one(self.scrape['image_link_i']).get('src')
        except Exception as e:
            image_link = soup.select_one(self.scrape['image_link_ii']).get('src')
        # finally:
        #     # If the image link cannot be extracted, return an error message:
        #     return f'Content loading error. Please try again in few minutes. Error message || {str(e)}.'

        try:
            availabilities = soup.select_one(self.scrape['availability']).text.strip()
        except AttributeError:
            availabilities = 'In stock'

        store = await self.catch.text(soup.select_one(self.scrape['store']))
        store_link = f"""https://www.amazon.com{await self.catch.attributes(soup.select_one(self.scrape['store']), 'href')}"""

        # Construct the data dictionary containing product information:
        datas = {
            'Name': await self.catch.text(soup.select_one(self.scrape['name'])),
            'Price': await self.catch.text(soup.select_one(self.scrape['price_us'])),
            'Rating': await self.catch.text(soup.select_one(self.scrape['review'])),
            'Rating count': await self.catch.text(soup.select_one(self.scrape['rating_count'])),
            'Availability': availabilities,
            'Hyperlink': url,
            'Image': image_link,
            'Store': store,
            'Store link': store_link,

        }
        return datas


    async def goldbox(self, url):
        print(f"Crawling Amazon deal products. Please be patient.")
        gold_dicts = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless = True)
            context = await browser.new_context(user_agent = userAgents())
            page = await context.new_page()

            await page.goto(url)

            await page.wait_for_selector(self.scrape['gold_pages'])
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')

            pages = soup.select(self.scrape['gold_pages'])[-1].text.strip()
            print(f"Total pages {pages}.\n-------------------")
            await asyncio.sleep(2)
            goldboxes = soup.select(self.scrape['gold_links'])
            for num in range(int(pages)):
                print(f"Crawling page | {num + 1}.")
                await page.wait_for_selector(self.scrape['next_page'])
                next_link = await page.query_selector(self.scrape['next_page'])
                for gold in goldboxes:
                    prod = gold.get('href')
                    if prod.startswith('https://www.amazon.com/deal'):
                        pass
                    else:
                        gold_dicts.append(prod)

                await asyncio.sleep(3)
                try:
                    await next_link.click()
                except Exception as e:
                    print(f"Content loading error beyond this page. Error message | {str(e)}.")
                    break

            await browser.close()
            return filter(gold_dicts)


    async def scrape_goldbox_info(self, url):
        gold_dicts = []
        if await verify_amazon(url):
            return "I'm sorry, the link you provided is invalid. Could you please provide a valid Amazon link for the product category of your choice?"

        content = await self.static_connection(url)
        soup = BeautifulSoup(content, 'lxml')
        product = await self.catch.text(soup.select_one(self.scrape['name']))
        try:
            deal_price = await self.catch.text(soup.select(self.scrape['deal_price'])[0])
        except IndexError:
            deal_price = "N/A"
        try:
            savings = await self.catch.text(soup.select(self.scrape['savings'])[-1])
        except IndexError:
            savings = "N/A"

        print(product)

        datas = {
            'Product': product,
            'Description': ' '.join([des.text.strip() for des in soup.select(self.scrape['description'])]),
            'Breakdown': ' '.join([br.text.strip() for br in soup.select(self.scrape['prod_des'])]),
            'Original Price': await self.catch.text(soup.select_one(self.scrape['price_us'])),
            'Deal Price': deal_price,
            'You saved': savings,
            'Rating': await self.catch.text(soup.select_one(self.scrape['review'])),
            'Rating count': await self.catch.text(soup.select_one(self.scrape['rating_count'])),
            'Store': (await self.catch.text(soup.select_one(self.scrape['store']))).replace("Visit the ", ""),
            'Store link': f"""https://www.amazon.com{await self.catch.attributes(soup.select_one(self.scrape['store']), 'href')}""",
            'Images': [imgs.get('src') for imgs in soup.select(self.scrape['image_lists'])],
            'Image': await self.catch.attributes(soup.select_one(self.scrape['image_link_i']), 'src'),
            'URL': url,
        }
        gold_dicts.append(datas)
        return gold_dicts


    async def scrape_and_save_gb(self, url):
        # random_sleep = await randomTime(interval)
        await asyncio.sleep(5)
        datas = await self.scrape_goldbox_info(url)
        return pd.DataFrame(datas)


    async def concurrent_scraping_gb(self, url_lists):
        print(f"The extraction process has begun and is currently in progress. The web scraper is scanning through all the links and collecting relevant information. Please be patient while the data is being gathered.")
        coroutines = [self.scrape_and_save_gb(url) for url in url_lists]
        dfs = await asyncio.gather(*coroutines)
        results = pd.concat(dfs)
        await export_sheet(results, "Today's deals")

