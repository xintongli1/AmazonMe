from fake_useragent import UserAgent
from urllib.parse import urlparse
import pandas as pd
import itertools
import aiohttp
import secrets
import yaml
import re
import os
from amazoncaptcha import AmazonCaptcha
from arsenic import get_session, browsers, services
from arsenic.session import *
from arsenic.errors import ArsenicError
from dotenv import load_dotenv, find_dotenv
from http import HTTPStatus
from PIL import Image


class Response:
    def __init__(self, base_url, proxy):
        """
        Initializes the Response class with a base URL.

        Parameters:
        - base_url (str): The base URL for the HTTP requests.
        """
        self.base_url = base_url
        self.proxy = proxy


    async def solve_captcha(self, content: str = None):
        """
        Asynchronously solves CAPTCHA if present on the page.
        :param content (CSS selector): The content to retrieve from the page via CSS selector. If None, a screenshot is saved.
        """
        _ = load_dotenv(find_dotenv())
        service = services.Chromedriver(binary=os.environ.get('CHROMEDRIVER_PATH'))
        browser = browsers.Chrome()
        # Start an Arsenic session
        async with get_session(service, browser) as session:
            try:
                await session.get(self.base_url)

                # Locate the captcha image and retrieve the src attribute
                captcha_img = await session.get_element('div.a-row.a-text-center img') # CSS selector
                captcha_url = await captcha_img.get_attribute('src')

                # Assuming AmazonCaptcha is a synchronous function
                captcha = AmazonCaptcha.fromlink(captcha_url)
                captcha_value = AmazonCaptcha.solve(captcha)

                # Input the captcha solution
                input_field = await session.get_element('#captchacharacters')
                await input_field.send_keys(captcha_value)

                # Locate and click the 'Continue shopping' button
                continue_shopping_btn = await session.wait_for_element(2, 'button.a-button-text')
                await continue_shopping_btn.click()

                if not content or content.endswith('.png'):
                    # save screenshot for debugging purposes
                    bytesIO_data = await session.get_screenshot()
                    image = Image.open(bytesIO_data)
                    image.save('captcha_solved.png' if not content else content)
                    # return status code for success
                    return HTTPStatus.OK  
                if content == 'html':
                    html_data = await session.execute_async_script("return document.documentElement.outerHTML;")
                elif content == 'page_source':
                    html_data = await session.get_page_source()
                else:
                    # get a list of child elements matching the CSS selector
                    html_data = await session.get_elements(content)
                return html_data
                    
            except ArsenicError as e:
                print(f"Captcha failed to be solved: {e}\n Please use other methods to scrape the contents you want...")
                # save screenshot for debugging purposes
                bytesIO_data = await session.get_screenshot()
                image = Image.open(bytesIO_data)
                image.save('captcha_solved.png' if not content else content)
                # return status code for failure
                return HTTPStatus.BAD_REQUEST



    async def content(self):
        """
        Asynchronously retrieves the content of the response from the specified URL.

        Returns:
        - bytes: The content of the HTTP response.
        """
        async with aiohttp.ClientSession() as session:
            headers = { 'User-Agent': ( 'Mozilla/5.0 (X11; Linux x86_64)' 
                                        'AppleWebKit/537.36 (KHTML, like Gecko)'
                                        'Chrome/44.0.2403.157 Safari/537.36' ),
                        'Accept-Language': 'en-US, en;q=0.5'}
            async with session.get(self.base_url, headers = headers) as resp:
                cont = await resp.read()
                return cont


    async def response(self):
        """
        Asynchronously retrieves the HTTP status code of the response from the specified URL.

        Returns:
        - int: The HTTP status code of the response.
        """
        async with aiohttp.ClientSession() as session:
            headers = {'User-Agent': userAgents()}
            async with session.get(self.base_url, headers = headers) as resp:
                cont = resp.status
                return cont


class TryExcept:
    """
    A class containing method for safely extracting information from HTML elements.
    """
    async def text(self, element):
        """
        Returns the text content of an HTML element, or "N/A" if the element is not found.

        Args:
            -element: An HTML element object.

        Returns:
            -A string representing the text content of the element, or "N/A" if the element is not found.
        """
        try:
            elements = element.text.strip()
        except AttributeError:
            elements = "N/A"
        return elements


    async def attributes(self, element, attr):
        """
        Returns the value fo an attribute of an HTML element, of "N/A" if the attribute or element is not found.

        Args:
            -element: An HTML element object.
            -attr: A string representing the name of the attribute to extract.

        Returns:
             A string representing the value of the attribute, or "N/A" if the attribute or element is not found.
        """
        try:
            elements = element.get(attr)
        except AttributeError:
            elements = "N/A"
        return elements


def filter_duplicates(raw_lists):
    """
    Removes duplicate elements from a list while preserving the original order.

    Parameters:
    - raw_lists (list): The input list containing elements, possibly with duplicates.

    Returns:
    - list: A new list with duplicate elements removed, preserving the original order.
    """
    filtered_lists = []

    # Iterate through each element in the input list:
    for file in raw_lists:

        # Check if the element is not already in the filtered list:
        if not file in filtered_lists:

            # Append the element to the filtered list:
            filtered_lists.append(file)
    return filtered_lists


def domain(url):
    """
    Extract the domain from a given URL.

    Args:
    - url (str): The URL from which to extract the domain.

    Returns:
    - str: The extracted domain.
    """
    dom = ""

    # Parse the URL using urlparse from the urllib library:
    parsed_url = urlparse(url)

    # Split the network location (netloc) into parts using dot as a separator:
    raw_domain = parsed_url.netloc.split(".")

    # Check the length of the raw domain parts:
    if len(raw_domain) == 3:

        # If there are three parts, consider the last part as the domain:
        dom += raw_domain[-1]
    elif len(raw_domain) == 4:

        # If there are four parts, consider the last two parts as the domain:
        dom += ".".join(raw_domain[-2:])
    return dom


def flat(d_lists):
    """
    Flatten a multi-dimensional list.

    Args:
    - d_lists (list): A multi-dimensional list.

    Returns:
    - list: A flattened version of the input list.
    """
    # Use itertools.chain to flatten the multi-dimensional list
    return list(itertools.chain(*d_lists))


async def verify_amazon(url):
    """
    Verifies if the input URL is a valid Amazon URL.

    Args:
        -url: A string representing the URL to verify.

    Returns:
        -True if the URL is invalid or False if it is valid.
    """
    # Define a regular expression pattern for Amazon URLs:
    amazon_pattern = re.search("""^(https://|www.)|amazon\.(com|in|co\.uk|fr|com\.mx|com\.br|com\.au|co\.jp|se|ca|de|it|ae|com\.be)(/s\?.|/b/.)+""", url)

    # Check if the pattern is not found in the URL:
    if amazon_pattern == None:
        return True
    else:
        pass


def region(url):
    """
    Check the domain of a URL and return the country it belongs to.

    Args:
    - url (str): The URL to check.

    Returns:
    - str: The name of the country the domain belongs to (USA, UK, Mexico, Brazil, Australia, Belgium, India, France, Sweden, Germany, Italy).

    """
    # Parse the URL using urlparse from the urllib library:
    parsed_url = urlparse(url)

    # Extract the last part of the netloc, which represents the raw domain:
    raw_domain = parsed_url.netloc.split(".")[-1]

    # Define a dictionary mapping raw domains to countries:
    domain_lists = {
        'com': 'USA',
        'ca': 'Canada',
        'uk': 'UK',
        'mx': 'Mexico',
        'br': 'Brazil',
        'au': 'Australia',
        'jp': 'Japan',
        'be': 'Belgium',
        'in': 'India',
        'fr': 'France',
        'se': 'Sweden',
        'de': 'Germany',
        'it': 'Italy',
        'ae': 'UAE',
    }

    # Return the country associated with the raw domain:
    return domain_lists[raw_domain]


def random_values(d_lists):
    """
    Returns a random value from a list.

    Args
    """
    # Generate a random index within the range of the input list:
    idx = secrets.randbelow(len(d_lists))

    # Return the value at the randomly generated index:
    return d_lists[idx]


async def create_path(dir_name):
    """
    Creates a directory with the specified name if i doesn't already exist.

    Args:
        -dir_name: A string representing the name of the directory to create.

    Return:
        -None
    """
    # Create the full path by joining the current working directory with the specified directory name:
    path_dir = os.path.join(os.getcwd(), dir_name)

    # Check if the directory already exists:
    if os.path.exists(path_dir):
        # If it exists, do nothing:
        pass
    else:
        # If it doesn't exist, create the directory:
        os.mkdir(path_dir)


async def export_sheet(dicts, name):
    """
    Exports a list of dictionaries to an Excel file with the specified name and saves it to a directory called 'Amazon database':

    Args:
        -dicts (List[Dict]): A list of dictionaries to export to an Excel file.
        -name (str): The name to use for the Excel file (without the file extension).

    Returns:
        -None
    """
    # Define the directory name to store the Excel file:
    directory_name = 'Amazon database'

    # Create the directory if it doesn't exist:
    await create_path(directory_name)

    # Convert the list of dictionaries to a pandas DataFrame:
    df = pd.DataFrame(dicts)

    # Save the DataFrame to a CSV file in the specified directory and with the given name:
    df.to_csv(f"""{os.getcwd()}//{directory_name}//{name}.csv""", index = False)

    # Print a message indicating that the file has been saved:
    print(f"{name} saved.")


async def randomTime(val):
    """
    Generates a random time interval between requests to avoid overloading the server. Scrape responsibly.

    Args:
        -val: An integer representing the maximum time interval in seconds.

    Returns:
        -A random integer between 2 and the input value. So, the default time interval is 2 seconds.
    """
    # Create a list of integers from 0 to the specified maximum value:
    ranges = [i for i in range(0, val+1)]

    # Use the random_values function to select a random value from the created list
    return random_values(ranges)


def userAgents():
    """
    Returns a random user agent string from a file containing a list of user agents.

    Args:
        -None

    Returns:
        -A string representing a random user agent.
    """
    agents = UserAgent()
    return agents.random


def rand_proxies():
    """
    Returns a random proxy from a file containing a list of proxies.

    Args:
        - None

    Returns:
        - str: A string representing a random proxy.
    """
    with open('tools//proxies.txt') as f:

        # Read the contents of the file containing proxies and split them into a list:
        proxies = f.read().split("\n")

        # Use the random_values function to select a random proxy from the list:
        return random_values(proxies)


def yaml_load(selectors):
    """
    Loads a YAML file containing selectors for web scraping.

    Args:
        -selectors: A string representing the name of the YAML file containing the selectors.

    Returns:
        -A dictionary containing the selectors.
    """
    # Open the specified YAML file and load its content using the yaml module:
    with open(f"scrapers//{selectors}.yaml") as file:
        sel = yaml.load(file, Loader=yaml.SafeLoader)

        # Return the loaded selectors as a dictionary:
        return sel

