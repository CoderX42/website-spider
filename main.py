#!/usr/bin/env python3
"""参展商信息抓取工具

用法:
    python main.py                    # 抓取全部站点
    python main.py --site mys         # 只抓 CONEXPO-CON/AGG 2026
    python main.py --site informa     # 只抓 CICSEA 2025
    python main.py --workers 12       # 调整详情页并发数(仅 mys)

结果输出到 output/ 目录 (CSV 可用 Excel 直接打开, JSON 保留全部字段含联系人)。
"""
import argparse
import csv
import json
import logging
import os

from spiders import informa, mys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("main")

OUT_DIR = "output"

SITES = {
    "mys": {
        "name": "conexpoconagg_2026",
        "label": "CONEXPO-CON/AGG 2026",
    },
    "informa": {
        "name": "cicsea_2025",
        "label": "CICSEA 2025",
    },
}

CSV_FIELDS = [
    ("name", "公司名称"),
    ("description", "简介"),
    ("country", "国家/地区"),
    ("booth", "展位号"),
    ("website", "官网"),
    ("phone", "电话"),
    ("fax", "传真"),
    ("facebook", "Facebook"),
    ("linkedin", "LinkedIn"),
    ("address", "地址"),
    ("city", "城市"),
    ("state", "州/省"),
    ("zip", "邮编"),
    ("categories", "产品分类"),
    ("contacts_text", "联系人"),
    ("detail_url", "详情页"),
]


def export(site_key, exhibitors):
    os.makedirs(OUT_DIR, exist_ok=True)
    base = os.path.join(OUT_DIR, SITES[site_key]["name"])

    for e in exhibitors:
        contacts = e.get("contacts") or []
        e["contacts_text"] = "; ".join(
            " ".join(filter(None, [c.get("FIRSTNAME", ""), c.get("LASTNAME", "")])).strip()
            + (" (%s)" % c["TITLE"] if c.get("TITLE") else "")
            + (" <%s>" % c["EMAIL"] if c.get("EMAIL") else "")
            for c in contacts
        )

    with open(base + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([label for _, label in CSV_FIELDS])
        for e in exhibitors:
            w.writerow([e.get(k, "") for k, _ in CSV_FIELDS])

    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(exhibitors, f, ensure_ascii=False, indent=1)

    log.info("%s: 导出 %d 条 -> %s.csv / .json",
             SITES[site_key]["label"], len(exhibitors), base)


def main():
    ap = argparse.ArgumentParser(description="参展企业信息抓取")
    ap.add_argument("--site", choices=["all"] + list(SITES), default="all")
    ap.add_argument("--workers", type=int, default=8, help="mys 详情页并发数")
    args = ap.parse_args()

    sites = list(SITES) if args.site == "all" else [args.site]
    for key in sites:
        log.info("=== 开始抓取 %s ===", SITES[key]["label"])
        if key == "mys":
            data = mys.run(workers=args.workers,
                           cache_path=os.path.join(OUT_DIR, ".mys_cache.json"))
        else:
            data = informa.run()
        export(key, data)
    log.info("全部完成")


if __name__ == "__main__":
    main()
