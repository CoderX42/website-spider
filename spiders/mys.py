"""CONEXPO-CON/AGG 2026 参展商爬虫 (Map Your Show 平台)

列表: /8_0/ajax/remote-proxy.cfm?action=search&searchtype=exhibitorgallery
详情: /8_0/exhibitor/exhibitor-details.cfm?exhid=<id>  (联系方式内嵌在页面 JS 中)
"""
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

log = logging.getLogger(__name__)

BASE = "https://directory.conexpoconagg.com"
API = BASE + "/8_0/ajax/remote-proxy.cfm"
DETAIL = BASE + "/8_0/exhibitor/exhibitor-details.cfm?exhid={}"
APIKEY = "mwskxdxctb"
PAGE_SIZE = 100  # 该接口 searchsize 最大有效值约为 100

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE + "/8_0/explore/exhibitor-gallery.cfm?featured=false",
}
# 详情页不能带 X-Requested-With, 否则服务端返回 JS 转义后的页面
DETAIL_HEADERS = {"User-Agent": UA}


def _get(url, params=None, retries=4, timeout=30, headers=None):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers or HEADERS, timeout=timeout)
            if r.status_code == 200 and r.text.strip():
                return r
            log.warning("HTTP %s / 空响应: %s (第%d次)", r.status_code, r.url, attempt + 1)
        except requests.RequestException as e:
            log.warning("请求异常: %s %s (第%d次)", url, e, attempt + 1)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError("请求失败(重试%d次): %s" % (retries, url))


def fetch_list():
    """抓取全部展商列表, 返回 [{exhid, name, description, booths, hall}]"""
    params = {
        "action": "search",
        "searchtype": "exhibitorgallery",
        "searchsize": PAGE_SIZE,
        "start": 0,
        "apikey": APIKEY,
    }
    d = _get(API, params).json()
    total = int(d["DATA"]["totalhits"])
    log.info("列表总数: %d", total)

    exhibitors = []
    for start in range(0, total, PAGE_SIZE):
        params["start"] = start
        d = _get(API, params).json()
        hits = d["DATA"]["results"]["exhibitor"]["hit"]
        for h in hits:
            f = h["fields"]
            booths = [b.replace("randomstring", "") for b in f.get("boothsdisplay_la", [])]
            exhibitors.append({
                "exhid": f["exhid_l"],
                "name": f.get("exhname_t", "").strip(),
                "description": (f.get("exhdesc_t") or "").strip(),
                "booth": ", ".join(booths),
                "featured": f.get("exhfeatured_t") == "1",
            })
        log.info("列表进度: %d/%d", min(start + PAGE_SIZE, total), total)
        time.sleep(0.3)
    return exhibitors


def _extract_json_obj(text, key):
    """从 JS 源码中提取 `key: {...}` 的对象字面量 (按花括号配平)"""
    m = re.search(re.escape(key) + r"\s*:\s*\{", text)
    if not m:
        return {}
    i = m.end() - 1
    depth = 0
    for j in range(i, len(text)):
        c = text[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[i:j + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


def _extract_js_str(text, key):
    m = re.search(re.escape(key) + r'\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if not m:
        return ""
    return m.group(1).replace('\\/', '/').replace('\\"', '"')


def fetch_detail(exh):
    """抓取单个展商详情页的联系方式"""
    r = _get(DETAIL.format(exh["exhid"]), headers=DETAIL_HEADERS)
    html = r.text

    addr = _extract_json_obj(html, "addressValues")
    contacts = []
    m = re.search(r"onlinecontactsdata\s*[:=]\s*(\[[^\n]*?\])", html)
    if m:
        try:
            contacts = json.loads(m.group(1))
        except json.JSONDecodeError:
            contacts = []

    cats = re.findall(
        r'<a href="/8_0/#/searchtype/category/[^"]*">([^<]+)</a>', html)

    exh.update({
        "website": _extract_js_str(html, "websiteValue"),
        "phone": _extract_js_str(html, "phoneValue"),
        "fax": _extract_js_str(html, "faxValue"),
        "facebook": _extract_js_str(html, "facebookValue"),
        "twitter": _extract_js_str(html, "twitterValue"),
        "linkedin": _extract_js_str(html, "linkedInValue"),
        "instagram": _extract_js_str(html, "instagramValue"),
        "address": ", ".join(filter(None, [addr.get("ADDRESS1", "").strip(),
                                           addr.get("ADDRESS2", "").strip(),
                                           addr.get("ADDRESS3", "").strip()])),
        "city": addr.get("CITY", ""),
        "state": addr.get("STATE", ""),
        "zip": addr.get("ZIP", ""),
        "country": addr.get("COUNTRY", ""),
        "categories": "; ".join(c.strip() for c in cats),
        "contacts": [
            {k: c.get(k, "") for k in ("FIRSTNAME", "LASTNAME", "TITLE", "EMAIL")}
            for c in contacts if isinstance(c, dict)
        ],
        "detail_url": DETAIL.format(exh["exhid"]),
    })
    return exh


def run(workers=8, cache_path=None):
    """完整抓取: 列表 + 所有详情页。支持 cache_path 断点续抓。"""
    if cache_path:
        os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
    done = {}
    if cache_path:
        try:
            done = {e["exhid"]: e for e in json.load(open(cache_path))}
            log.info("从缓存恢复 %d 条详情", len(done))
        except (OSError, json.JSONDecodeError):
            pass

    exhibitors = fetch_list()
    todo = [e for e in exhibitors if e["exhid"] not in done]
    log.info("待抓详情: %d 家 (共 %d 家)", len(todo), len(exhibitors))

    def job(e):
        time.sleep(0.1)
        return fetch_detail(e)

    results = dict(done)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(job, e): e for e in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            e = futs[fut]
            try:
                results[e["exhid"]] = fut.result()
            except Exception as ex:
                log.error("详情失败 %s %s: %s", e["exhid"], e["name"], ex)
                results[e["exhid"]] = e  # 保留列表数据
            if i % 100 == 0:
                log.info("详情进度: %d/%d", i, len(todo))
                if cache_path:
                    json.dump(list(results.values()), open(cache_path, "w"),
                              ensure_ascii=False, indent=1)

    out = [results[e["exhid"]] for e in exhibitors]
    if cache_path:
        json.dump(out, open(cache_path, "w"), ensure_ascii=False, indent=1)
    return out
