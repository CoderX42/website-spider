# website-spider

参展企业信息抓取工具，目前支持两个展会网站：

| 站点 | 展会 | 数据量 | 可得字段 |
|---|---|---|---|
| `mys` | [CONEXPO-CON/AGG 2026](https://directory.conexpoconagg.com/8_0/explore/exhibitor-gallery.cfm?featured=false) | ~2474 家 | 名称、简介、展位、官网、电话、传真、地址、社媒、产品分类 |
| `informa` | [CICSEA 2025](https://exhibitors.informamarkets-info.com/event/CICSEA2025) | ~404 家 | 名称、简介、国家、展位、地址、官网、产品分类（该站不公开电话/邮箱） |

## 安装

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 使用

```bash
.venv/bin/python main.py                  # 抓取全部站点
.venv/bin/python main.py --site mys       # 只抓 CONEXPO-CON/AGG
.venv/bin/python main.py --site informa   # 只抓 CICSEA
.venv/bin/python main.py --workers 12     # 调整 mys 详情页并发(默认8)
```

结果输出到 `output/`：

- `conexpoconagg_2026.csv` / `cicsea_2025.csv` — Excel 可直接打开（utf-8-sig）
- 同名 `.json` — 全部字段（含联系人结构化数据）

CONEXPO 详情页抓取带断点续传：中断后重跑会从 `output/.mys_cache.json` 恢复。

## 说明

- 两个站点的展商邮箱均不公开（CONEXPO 需登录后通过站内表单联系），因此无法抓取邮箱。
- 请控制抓取频率，仅用于合法合规用途。
