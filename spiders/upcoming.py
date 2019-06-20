import re
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider
from scrapy.selector import Selector
from movie_wiki_crawler.items import MovieWikiCrawlerItem


class UpcomingSpider(CrawlSpider):
    name = 'upcoming'
    # allow only wikipedia pages
    allowed_domains = ['en.wikipedia.org']
    # delay scraping for niceness
    download_delay = 2.0
    custom_settings = {
    # specifies exported fields and order
        'FEED_EXPORT_FIELDS': ['title', 'imdb_id', 'directed_by', 'starring_cast', 'release_date', 'poster', 'imdb_link'],
    }


    def __init__(self, *args, **kwargs):
        """
        Initiate with option to pass in the start url (Current scraping starts at *2019 - 2021* in Film page)
        
        List of start pages: ['https://en.wikipedia.org/wiki/2019_in_film', 'https://en.wikipedia.org/wiki/2020_in_film', 'https://en.wikipedia.org/wiki/2021_in_film']
        Provide one as keyword argument at runtime or add to start_url under allowed_domains
        """
        urls = kwargs.pop('urls', [])
        if urls:
            self.start_urls = urls.split(',')
        self.logger.info(self.start_urls)
        super(UpcomingSpider, self).__init__(*args, **kwargs)


    def parse_start_url(self, response):
        return self.parse_movie_links(response)

    def parse_movie_links(self, response):
        sel = Selector(response)
        # Looks for tables listing movies that have a Wikipedia page
        movie_links = sel.xpath('//th[contains(text(), "Opening")]/../../tr/td[not(@style)][1]/i/a/@href')

        for movie in movie_links:
            movie_link = f'https://en.wikipedia.org{movie.get()}'
            yield scrapy.Request(movie_link, callback=self.parse_movie_details)


    def parse_movie_details(self, response):
        sel = Selector(response)
        movie_page = sel.xpath('//div[contains(@class, "mw-parser-output")]')

        # Looks for the IMDb url by href
        imdb_url = movie_page.xpath('//a[starts-with(@href, "https://www.imdb.com/title/tt")]/@href').get()
        # Regex to select just the id out of the full IMDb url
        imdb_url_id = str((re.match(r"^(?:[^\/]*\/){4}([^\/]*)", imdb_url).groups()[0])) if imdb_url else None
        
        # Looks for a link to the poster img by href
        poster_link = movie_page.xpath('//img[starts-with(@src, "//upload.wikimedia.org/wikipedia/en/")]/@src').get()
        # Removes citation element from lists
        rmv_citation = '[not(ancestor::*[@class="reference"])]'
        
        item = MovieWikiCrawlerItem()
        if movie_page.xpath('//table[contains(@class, "infobox")]'):
            item['title'] = movie_page.xpath('//th[@class="summary"]/text() | //th[@class="summary"]/i/text()').get()
            # Joins poster to full url if poster_link exists
            item['poster'] = f'https:{poster_link}' if poster_link else None
            # Finds the following td element after "Directed by" th, it will select one or multiple href(s) text value or select the value of td if no href(s)
            item['directed_by'] = movie_page.xpath('//th[text()="Directed by"]/following::td[1]').xpath(
                f'.//a/text(){rmv_citation} | ./text(){rmv_citation}').getall()
            # Finds the following td element after "Starring" th, it will select one or multiple href(s) text value or select the value of li text if no href(s)
            item['starring_cast'] = movie_page.xpath('//th[text()="Starring"]/following::td[1]').xpath(
                f'.//a/text(){rmv_citation} | .//li/text(){rmv_citation}').getall()
            # Finds the release date based on "United States" then selects the "bday" span text value or if no match will select the first span with class "bday"
            item['release_date'] = movie_page.xpath('//li[contains(text()[2], " (United States)")]/span/span/text() | //span[contains(@class, "bday")]/text()').get()
            item['imdb_link'] = imdb_url if imdb_url else None
            item['imdb_id'] = imdb_url_id

        yield item