######################################################
#   by: Mohammed Alraddadi
#        - LinkedIn: [https://www.linkedin.com/in/raddadi/]
#        - Email: [r@ddadi.me]
######################################################
import re
import json
import asyncio
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright
import aiosqlite
import playwright_stealth
import argparse
import time
from rich.console import Console
from rich.logging import RichHandler
import logging
# Configure Rich for logging
console = Console()
logging.basicConfig(level=logging.INFO, handlers=[RichHandler(console=console)])

overall_start_time = time.time()
total_pages_processed = 0
total_ads_processed = 0
total_insertions = 0
total_updates = 0

async def process_category_page(initial_category_page_url, save_to_sqlite=False, save_to_json=False):
    global total_pages_processed

    console.log(f"[bold green]Processing Category Page:[/] {initial_category_page_url}")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, timeout=30000)
        page = await browser.new_page()
        await playwright_stealth.stealth_async(page)

        try:
            await page.goto(initial_category_page_url)
            await page.evaluate('() => window.scrollTo(0, document.body.scrollHeight);')

            ads_links = await page.query_selector_all('xpath=//div[2]/div[2]/div[2]/div[*]/a')
            ads_urls = [await link.get_attribute('href') for link in ads_links]

            for ad_url in ads_urls:
                full_ad_url = urljoin('https://sa.aqar.fm', ad_url)
                #console.log(f"[bold green]Processing ad URL:[/] {full_ad_url}")

                ad_start_time = time.time()
                await parse_item(full_ad_url, save_to_sqlite, save_to_json)
                console.log(f"[bold green]Processed ad ID in[/] {time.time() - ad_start_time:.2f} seconds.")

        except Exception as e:
            console.print_exception()
            console.log(f"[bold red]Error while processing URL:[/] {initial_category_page_url}\n{str(e)}")
        finally:
           await browser.close()

        current_page_number = int(initial_category_page_url.split('/')[-1])
        next_page_number = current_page_number + 1
        next_page_url = urljoin('https://sa.aqar.fm/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA/', str(next_page_number))

        total_pages_processed += 1
        elapsed_time = time.time() - overall_start_time
        console.log(f"[bold green]Processed {total_pages_processed} category pages in[/] {elapsed_time:.2f} seconds.")

        console.log(f"[bold green]Next Category Page URL:[/] {next_page_url}")
        await process_category_page(next_page_url, save_to_sqlite=save_to_sqlite, save_to_json=save_to_json)

async def parse_item(full_ad_url, save_to_sqlite=False, save_to_json=False):
    global total_ads_processed, total_insertions, total_updates

    console.log(f"[bold green]Processing ad URL:[/] {full_ad_url}")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, timeout=5000)
        page = await browser.new_page()
        await playwright_stealth.stealth_async(page)
        await page.evaluate('() => window.scrollTo(0, document.body.scrollHeight);')

        try:
            await page.goto(full_ad_url)
            split_parts = full_ad_url.split("-")
            last_part = split_parts[-1]
            adid = re.sub(r'\D', '', last_part)

            # Extracting data from the ad page
            title_elem = await page.query_selector('xpath=/html/body/div[1]/main/div/div[2]/div/div/div[2]/div[2]/div[1]/h1')
            title = await title_elem.inner_text()

            description_elem = await page.query_selector('xpath=/html/body/div[1]/main/div/div[2]/div/div/div[2]/div[2]/div[4]/p')
            description = await description_elem.inner_text()

            cat_elem = await page.query_selector('xpath=/html/body/div[1]/main/div/div[2]/div/div/div[2]/div[2]/ul/li[2]/a')
            cat = await cat_elem.inner_text()

            city_elem = await page.query_selector('xpath=/html/body/div[1]/main/div/div[2]/div/div/div[2]/div[2]/ul/li[3]/a')
            city = await city_elem.inner_text()

            citydir_elem = await page.query_selector('xpath=/html/body/div[1]/main/div/div[2]/div/div/div[2]/div[2]/ul/li[4]/a')
            citydir = await citydir_elem.inner_text()

            dist_elem = await page.query_selector('xpath=/html/body/div[1]/main/div/div[2]/div/div/div[2]/div[2]/ul/li[5]/a')
            if 'حي' in citydir:
                dist = citydir
            else:
                dist = await dist_elem.inner_text()

            img_sources = await page.evaluate('''(xpath) => {
                const imgElements = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                return Array.from({ length: imgElements.snapshotLength }, (_, i) => imgElements.snapshotItem(i).src);
            }''', '//div[2]/div[*]/div[*]/div[*]/img')

            # Logging the extracted image sources
            imgs = [img_source for img_source in img_sources]

            # Extracting price and other details
            author_name_elem = await page.query_selector('xpath=//div/a/h2[@class="_name__Xc3Tb"]')
            author_name = await author_name_elem.inner_text() if author_name_elem else None

            author_url_elem = await page.query_selector('xpath=//div/a[@class="_userName__vwCcT"]')
            author_url = urljoin('https://sa.aqar.fm', await author_url_elem.get_attribute('href')) if author_url_elem else None

            price_text = None
            price_elem = await page.query_selector('xpath=/html/body/div[1]/main/div/div[2]/div/div/div[2]/div[2]/div[3]/h2')
            if price_elem:
                price_text = re.sub(r'\D', '', await price_elem.inner_text())

            values_elems = await page.query_selector_all('xpath=/html/body/div[1]/main/div/div[2]/div/div/div[2]/div[2]/div[5]/div[*]/*[2]')
            filters_elems = await page.query_selector_all('xpath=/html/body/div[1]/main/div/div[2]/div/div/div[2]/div[2]/div[5]/div[*]/*[1]/p')

            filters, generic_values = [], []

            # Extracting filters and values
            for filter_elem, value_elem in zip(filters_elems, values_elems):
                filter_text = await filter_elem.inner_text()
                value_text = await value_elem.inner_html()

                if "<img" in value_text:
                    img_elem = await value_elem.query_selector('img')
                    if img_elem:
                        img_src = await img_elem.get_attribute('src')
                        if img_src == 'https://assets.aqar.fm/icons/Available-colored.svg':
                            generic_values.append('1')
                            filters.append(filter_text)
                else:
                    generic_values.append(value_text)
                    filters.append(filter_text)

            # Extracting image and map URLs
            image_xpath = 'xpath=/html/body/div[1]/main/div/div[2]/div/div/div[2]/div[2]/div[6]/div/div[1]/div[4]/img'
            map_xpath = 'xpath=/html/body/div[1]/main/div/div[2]/div/div/div[2]/div[2]/div[6]/div/div[1]/div[6]/div/div[1]/div/a'

            await page.click(image_xpath)
            mapsco = await page.query_selector(map_xpath)

            map_url = await mapsco.get_attribute('href') if mapsco else None
            if description:
                console.log(f"[bold yellow]ID#:[/] {adid}")
                console.log(f"[bold yellow]Title:[/] {title}")
                console.log(f"[bold yellow]Author Name:[/] {author_name}")
                console.log(f"[bold yellow]Price:[/] {price_text}")
                console.log(f"[bold yellow]Map URL:[/] {map_url}")
                console.log(f"[bold yellow]Category:[/] {cat}")
                console.log(f"[bold yellow]City:[/] {city}")
                console.log(f"[bold yellow]City Part:[/] {citydir}")
                console.log(f"[bold yellow]Filters:[/] {filters}")
                console.log(f"[bold yellow]Values:[/] {generic_values}")
            if save_to_sqlite:
                is_update = await is_ad_in_database(adid)
                if is_update:
                    total_updates += 1
                else:
                    total_insertions += 1

                await save_to_sqlitedb(adid, title, description, author_name, price_text, str(filters), str(generic_values), cat, author_url, city, citydir, dist, str(imgs), map_url)
            elif save_to_json:
                await save_to_json_file(adid, title, description, author_name, price_text, filters, generic_values, cat, author_url, city, citydir , dist, imgs, map_url)

            # ... (existing code)

            console.log(f"[bold yellow]Processed ad ID {adid} in[/] {time.time() - overall_start_time:.2f} seconds.")
            console.log(f"[bold yellow]Inserted:[/] {total_insertions} | [bold yellow]Updated:[/] {total_updates}")

        except Exception as e:
            console.print_exception()
            console.log(f"[bold red]Error while processing URL:[/] {full_ad_url}\n{str(e)}")

async def is_ad_in_database(adid):
    try:
        async with aiosqlite.connect('aqar.db') as connection:
            cursor = await connection.cursor()
            result = await cursor.execute("SELECT adid FROM Aqarat WHERE adid=?", (adid,))
            return await result.fetchone() is not None
    except Exception as e:
        console.log(f"[bold red]Error while checking ad in SQLite:[/] {str(e)}")
        return False

async def save_to_sqlitedb(adid, title, description, author_name, price_text, filters, generic_values, cat, author_url, city, citydir, dist, imgs, map_url):
    try:
        async with aiosqlite.connect('aqar.db') as connection:
            cursor = await connection.cursor()

            await cursor.execute("CREATE TABLE IF NOT EXISTS Aqarat (adid TEXT PRIMARY KEY, title TEXT, description TEXT, author_name TEXT, price TEXT, filters TEXT, generic_values TEXT, cat TEXT, author_url TEXT, city TEXT, citydir TEXT, dist TEXT, imgs TEXT, map_url TEXT)")

            await cursor.execute("INSERT OR REPLACE INTO Aqarat (adid, title, description, author_name, price, filters, generic_values, cat, author_url, city, citydir, dist, imgs, map_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (adid, title, description, author_name, price_text, filters, generic_values, cat, author_url, city, citydir, dist, imgs, map_url))

            await connection.commit()

    except Exception as e:
        console.print_exception()
        console.log(f"[bold red]Error while saving to SQLite:[/] {str(e)}")

async def save_to_json_file(adid, title, description, author_name, price_text, filters, generic_values, cat, author_url, city, citydir, dist, imgs, map_url):
    try:
        data = {
            "adid": adid,
            "title": title,
            "description": description,
            "author_name": author_name,
            "price": price_text,
            "filters": filters,
            "generic_values": generic_values,
            "cat": cat,
            "author_url": author_url,
            "city": city,
            "citydir": citydir,
            "dist": dist,
            "imgs": imgs,
            "map_url": map_url
        }

        with open('your_file.json', 'a') as json_file:
            json.dump(data, json_file, indent=2)
            json_file.write('\n')

    except Exception as e:
        console.print_exception()
        console.log(f"[bold red]Error while saving to JSON:[/] {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawler for processing category pages")
    parser.add_argument("--sqlite", action="store_true", help="Save data to SQLite database")
    parser.add_argument("--json", action="store_true", help="Save data to JSON file")
    parser.add_argument("--st", type=int, default=1, help="Starting page number")
    args = parser.parse_args()

    initial_category_page_url = urljoin("https://sa.aqar.fm/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA/", str(args.st))
    asyncio.run(process_category_page(initial_category_page_url, save_to_sqlite=args.sqlite, save_to_json=args.json))