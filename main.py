from mongo_database.mongo import export_to_mong
from tools.tool import rand_proxies
from scrapers.scraper import Amazon
import asyncio
import time


if __name__ == '__main__':


    async def main():
        base_url = "https://www.amazon.ae/b/ref=sv_sl_mm_en_5_4_1_6/b/?_encoding=UTF8&node=11995864031&ref=sr_nr_n_1&pd_rd_w=ULvh4&content-id=amzn1.sym.a7286ae0-0314-49ff-8182-f95ea0dbfa34&pf_rd_p=a7286ae0-0314-49ff-8182-f95ea0dbfa34&pf_rd_r=BDMYA61G3Z69H9ATC5BG&pd_rd_wg=NsD6b&pd_rd_r=3fc3f3bb-0ddc-4bd9-96a4-cc1dd7a3c859&ref_=pd_gw_unk"
        status = await Amazon(base_url, None).status()

        if status == 503:
            return "503 response. Please try again in few minutes."

        # Type True if you want to export to CSV and avoid MongoDB
        csv = True
        # Type True if you want to use proxy:
        proxy = False
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
    results = asyncio.run(main())
    end_time = time.time()
    print(results)
    # Calculate and print the total time taken to scrape the data:D
    execution_time = round(end_time - start_time, 2)
    print(f"Took {execution_time} seconds | {round(execution_time / 60, 2)} minutes.")

