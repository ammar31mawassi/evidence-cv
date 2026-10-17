"""Bounded public-page extraction. Job pages are data, never instructions."""
import html
import ipaddress
import json
import re
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import trafilatura

class CVError(ValueError):
    pass

def public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise CVError('Provide a public http/https job URL without embedded credentials.')
    if parsed.port not in {None, 80, 443}:
        raise CVError('Only ordinary public website ports are supported.')
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise CVError('The job website hostname could not be resolved.') from exc
    if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise CVError('Local/private network URLs are not job websites.')
    return url

def normalize(value):
    return re.sub(r'\s+', ' ', html.unescape(str(value))).strip()

def plain(value):
    return normalize(BeautifulSoup(str(value), 'html.parser').get_text(' ', strip=True))

def job_objects(value):
    if isinstance(value, list):
        for item in value:
            yield from job_objects(item)
    elif isinstance(value, dict):
        kind = value.get('@type', '')
        if kind == 'JobPosting' or isinstance(kind, list) and 'JobPosting' in kind:
            yield value
        else:
            for item in value.values():
                if isinstance(item, (dict, list)):
                    yield from job_objects(item)

def from_html(raw, url):
    soup = BeautifulSoup(raw, 'html.parser')
    jobs = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            jobs.extend(job_objects(json.loads(script.get_text())))
        except (ValueError, TypeError):
            pass
    # Duplicate structured blocks are common; several different postings need a specific URL.
    unique = {normalize(j.get('title', '')) + plain(j.get('description', '')): j for j in jobs}
    if len(unique) > 1:
        raise CVError('This page lists multiple jobs. Provide a link to one specific posting.')
    if unique:
        job = next(iter(unique.values()))
        description = plain(job.get('description', ''))
        if len(description) >= 200:
            org = job.get('hiringOrganization', {})
            company = org.get('name', '') if isinstance(org, dict) else str(org)
            title = plain(job.get('title', ''))
            return {'text': normalize(f'{title}\n{company}\n{description}'), 'title': title,
                    'company': plain(company), 'method': 'JobPosting JSON-LD', 'url': url}
    # Workday frequently exposes a public JSON API under its /wday/cxs endpoint,
    # but the generic browser fallback also handles client-rendered postings.
    text = trafilatura.extract(raw, include_comments=False, include_tables=True)
    if not text:
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        text = soup.get_text(' ', strip=True)
    title = normalize(soup.title.get_text()) if soup.title else ''
    return {'text': normalize(f'{title}\n{text}'), 'title': '', 'company': '',
            'method': 'page text', 'url': url}

def looks_like_job(text):
    markers = r'requirements|qualifications|responsibilit|experience|skills|תיאור|דרישות|المتطلبات|المهارات'
    return len(text) >= 350 and len(re.findall(markers, text, re.I)) >= 2

def browser_html(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        try:
            page = browser.new_page()
            def guard(route):
                if route.request.resource_type in {'image', 'media', 'font'}:
                    return route.abort()
                try:
                    public_url(route.request.url)
                    route.continue_()
                except (CVError, ValueError):
                    route.abort()
            page.route('**/*', guard)
            page.goto(url, wait_until='domcontentloaded', timeout=45000)
            for _ in range(5):
                if looks_like_job(page.inner_text('body')):
                    break
                page.wait_for_timeout(2000)
            public_url(page.url)
            return page.content(), page.url
        finally:
            browser.close()

def fetch_job(url):
    public_url(url)
    result = None
    try:
        current = url
        for _ in range(6):
            public_url(current)
            with requests.get(current, timeout=25, allow_redirects=False, stream=True,
                              headers={'User-Agent': 'Mozilla/5.0 (compatible; LocalJobCV/1.0)'}) as response:
                if response.is_redirect:
                    from urllib.parse import urljoin
                    current = urljoin(current, response.headers['Location'])
                    continue
                response.raise_for_status()
                if 'html' not in response.headers.get('content-type', '').lower():
                    raise CVError('The URL must point to an HTML job posting.')
                chunks, size = [], 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > 4_000_000:
                        raise CVError('The job page exceeds the supported size.')
                    chunks.append(chunk)
                raw = b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace')
                result = from_html(raw, current)
                break
        if result and looks_like_job(result['text']):
            return result
    except requests.RequestException:
        pass
    try:
        raw, current = browser_html(url)
        result = from_html(raw, current)
    except CVError:
        raise
    except Exception as exc:
        raise CVError('Could not read this posting. Use -DescriptionFile with saved job text; login/captcha pages cannot be fetched automatically.') from exc
    if not looks_like_job(result['text']):
        raise CVError('No complete job description was found. Use a specific job URL or -DescriptionFile with the full posting.')
    result['method'] = 'local browser / ' + result['method']
    return result
