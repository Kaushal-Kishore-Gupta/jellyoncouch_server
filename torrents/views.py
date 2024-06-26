# torrents/views.py
import os
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.conf import settings

EMPTY_LIST = []

BASE_URL = os.getenv('BASE_URL', 'https://thepiratebay.org/')
sort_filters = {
    'title_asc': 1,
    'title_desc': 2,
    'time_desc': 3,
    'time_asc': 4,
    'size_desc': 5,
    'size_asc': 6,
    'seeds_desc': 7,
    'seeds_asc': 8,
    'leeches_desc': 9,
    'leeches_asc': 10,
    'uploader_asc': 11,
    'uploader_desc': 12,
    'category_asc': 13,
    'category_desc': 14
}

def index(request):
    return render(request, 'index.html')

def default_top(request):
    return render(request, 'top.html')

def top_torrents(request, cat=0):
    sort = request.GET.get('sort')
    sort_arg = sort if sort in sort_filters else ''
    url = f"{BASE_URL}top/{cat}/" if cat != 0 else f"{BASE_URL}top/all/{sort_arg}"
    return JsonResponse(parse_page(url, sort=sort_arg), safe=False)

def top48h_torrents(request, cat=0):
    sort = request.GET.get('sort')
    sort_arg = sort if sort in sort_filters else ''
    url = f"{BASE_URL}top/48h{cat}/" if cat != 0 else f"{BASE_URL}top/48h/all/"
    return JsonResponse(parse_page(url, sort=sort_arg), safe=False)

def recent_torrents(request, page=0):
    sort = request.GET.get('sort')
    sort_arg = sort if sort in sort_filters else ''
    url = f"{BASE_URL}recent/{page}"
    return JsonResponse(parse_page(url, sort=sort_arg), safe=False)

def api_search(request):
    url = f"{BASE_URL}s/?{request.GET.urlencode()}"
    return JsonResponse(parse_page(url), safe=False)

def default_search(request):
    return HttpResponse('No search term entered<br/>Format for search: /search/search_term/page_no(optional)/')

def search_torrents(request, term=None, page=0):
    sort = request.GET.get('sort')
    sort_arg = sort_filters.get(sort, '')
    url = f"{BASE_URL}search/{term}/{page}/{sort_arg}"
    return JsonResponse(parse_page(url), safe=False)

def parse_page(url, sort=None):
    data = requests.get(url).text
    soup = BeautifulSoup(data, 'lxml')
    table_present = soup.find('table', {'id': 'searchResult'})
    if table_present is None:
        return EMPTY_LIST
    titles = parse_titles(soup)
    links = parse_links(soup)
    magnets = parse_magnet_links(soup)
    times, sizes, uploaders = parse_description(soup)
    seeders, leechers = parse_seed_leech(soup)
    cat, subcat = parse_cat(soup)
    torrents = []
    for torrent in zip(titles, magnets, times, sizes, uploaders, seeders, leechers, cat, subcat, links):
        torrents.append({
            'title': torrent[0],
            'magnet': torrent[1],
            'time': convert_to_date(torrent[2]),
            'size': convert_to_bytes(torrent[3]),
            'uploader': torrent[4],
            'seeds': int(torrent[5]),
            'leeches': int(torrent[6]),
            'category': torrent[7],
            'subcat': torrent[8],
            'id': torrent[9],
        })

    if sort:
        sort_params = sort.split('_')
        torrents = sorted(torrents, key=lambda k: k.get(sort_params[0]), reverse=sort_params[1].upper() == 'DESC')

    return torrents

def parse_magnet_links(soup):
    magnets = soup.find('table', {'id': 'searchResult'}).find_all('a', href=True)
    magnets = [magnet['href'] for magnet in magnets if 'magnet' in magnet['href']]
    return magnets

def parse_titles(soup):
    titles = soup.find_all(class_='detLink')
    titles[:] = [title.get_text() for title in titles]
    return titles

def parse_links(soup):
    links = soup.find_all('a', class_='detLink', href=True)
    links[:] = [link['href'] for link in links]
    return links

def parse_description(soup):
    description = soup.find_all('font', class_='detDesc')
    description[:] = [desc.get_text().split(',') for desc in description]
    times, sizes, uploaders = map(list, zip(*description))
    times[:] = [time.replace(u'\xa0', u' ').replace('Uploaded ', '') for time in times]
    sizes[:] = [size.replace(u'\xa0', u' ').replace(' Size ', '') for size in sizes]
    uploaders[:] = [uploader.replace(' ULed by ', '') for uploader in uploaders]
    return times, sizes, uploaders

def parse_seed_leech(soup):
    slinfo = soup.find_all('td', {'align': 'right'})
    seeders = slinfo[::2]
    leechers = slinfo[1::2]
    seeders[:] = [seeder.get_text() for seeder in seeders]
    leechers[:] = [leecher.get_text() for leecher in leechers]
    return seeders, leechers

def parse_cat(soup):
    cat_subcat = soup.find_all('center')
    cat_subcat[:] = [c.get_text().replace('(', '').replace(')', '').split() for c in cat_subcat]
    cat = [cs[0] for cs in cat_subcat]
    subcat = [' '.join(cs[1:]) for cs in cat_subcat]
    return cat, subcat

def convert_to_bytes(size_str):
    size_data = size_str.split()
    multipliers = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB']
    size_magnitude = float(size_data[0])
    multiplier_exp = multipliers.index(size_data[1])
    size_multiplier = 1024 ** multiplier_exp if multiplier_exp > 0 else 1
    return size_magnitude * size_multiplier

def convert_to_date(date_str):
    date_format = None
    if re.search('^[0-9]+ min(s)? ago$', date_str.strip()):
        minutes_delta = int(date_str.split()[0])
        torrent_dt = datetime.now() - timedelta(minutes=minutes_delta)
        date_str = f'{torrent_dt.year}-{torrent_dt.month}-{torrent_dt.day} {torrent_dt.hour}:{torrent_dt.minute}'
        date_format = '%Y-%m-%d %H:%M'
    elif re.search('^[0-9]*-[0-9]*\s[0-9]+:[0-9]+$', date_str.strip()):
        today = datetime.today()
        date_str = f'{today.year}-' + date_str
        date_format = '%Y-%m-%d %H:%M'
    elif re.search('^Today\s[0-9]+\:[0-9]+$', date_str):
        today = datetime.today()
        date_str = date_str.replace('Today', f'{today.year}-{today.month}-{today.day}')
        date_format = '%Y-%m-%d %H:%M'
    elif re.search('^Y-day\s[0-9]+\:[0-9]+$', date_str):
        today = datetime.today() - timedelta(days=1)
        date_str = date_str.replace('Y-day', f'{today.year}-{today.month}-{today.day}')
        date_format = '%Y-%m-%d %H:%M'
    else:
        date_format = '%m-%d %Y'
    return datetime.strptime(date_str, date_format)
