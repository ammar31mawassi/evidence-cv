"""Optional local Crawl4AI fallback; no LLM/provider calls or authentication bypass."""
import asyncio
from extract import public_url, CVError

async def _crawl(url):
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    public_url(url)
    async def guard(route):
        if route.request.resource_type in {'image','media','font'}:
            return await route.abort()
        try:
            await asyncio.to_thread(public_url,route.request.url)
            await route.continue_()
        except (CVError,ValueError):await route.abort()
    async def created(page,context,**kwargs):
        await context.route('**/*',guard)
        return page
    async with AsyncWebCrawler(config=BrowserConfig(headless=True,extra_args=['--no-sandbox'])) as crawler:
        crawler.crawler_strategy.set_hook('on_page_context_created',created)
        result=await crawler.arun(url=url,config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS,page_timeout=45000,
            wait_until='domcontentloaded',word_count_threshold=5))
        if not result.success:raise CVError('Local crawler could not read the posting')
        public_url(result.url)
        if len(result.html)>4_000_000:raise CVError('Crawled page exceeds size limit')
        return result.html,result.url

def crawl_html(url):return asyncio.run(_crawl(url))
