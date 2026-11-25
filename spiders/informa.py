"""CICSEA 2025 (Informa Markets) 参展商爬虫

列表接口一次返回全部展商, 已包含名称/简介/国家/展位/地址/官网等字段。
该站不公开电话和邮箱。
"""
import logging

import requests

log = logging.getLogger(__name__)

BASE = "https://exhibitors.informamarkets-info.com"
API = BASE + "/api"
EVENT_URL = BASE + "/event/CICSEA2025"

PARAMS = {
    "fn": "getExhibitor",
    "orderfields": '["FeaturedExhibitor","ExhibitorNameEn","StandNoStr","CountryEn"]',
    "HideEmptyProducts": 0,
    "order[0][column]": 0,
    "order[0][dir]": "desc",
    "order[1][column]": 1,
    "order[1][dir]": "asc",
    "start": 0,
    "length": 10000,
    "draw": 1,
    "dt": 1,
    "SearchLog": 1,
    "FairID": "0UaU9QCY4NOkrty9Y0KnJg==",
    "FairCode": "OSa78W5dhB4LtKBJfjMKEg==",
    "UseOldCountry": "False",
    "MyList": 0,
    "Email": "",
    "Url": EVENT_URL,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": EVENT_URL,
}


def run():
    r = requests.get(API, params=PARAMS, headers=HEADERS, timeout=60)
    r.raise_for_status()
    d = r.json()
    rows = d["data"]
    log.info("获取展商 %d 家 (recordsTotal=%s)", len(rows), d.get("recordsTotal"))

    out = []
    for r in rows:
        booths = [b for b in r.get("StandNoStr", "").split("~") if b]
        out.append({
            "exhid": r.get("ExhibitorID", ""),
            "name": r.get("ExhibitorNameEn", "").strip(),
            "description": (r.get("DescEn") or "").strip(),
            "country": r.get("CountryEn", "").strip(),
            "booth": ", ".join(booths),
            "address": r.get("Field01", "").strip(),
            "website": r.get("LinkEn", "").strip(),
            "categories": r.get("ProductCategoryEn", "").strip(),
            "logo": r.get("PhotoURL", "").strip(),
            "detail_url": "%s/en-US/exhibitor/%s/" % (EVENT_URL, r.get("ExhibitorID", "")),
        })
    return out
