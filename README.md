# Home in Berlin Wedding 双人房监控

这个项目每 30 分钟检查一次 [Home in Berlin 房源列表](https://home-in-berlin.de/en/immobilien/)，只在新出现的房源同时满足“适合两个人共同居住”和“明确位于 Berlin-Wedding”时，通过 ntfy 给手机推送通知。

当前网站可以用 `requests + BeautifulSoup4` 解析，不需要 Playwright。解析器会先读取 JSON-LD，再使用页面中的 `estate-card`、详情页 `estate-pre-title`、`maximum occupancy`、租金和押金文本兜底。

## 筛选逻辑

双人房判断在 `src/matcher.py` 的 `is_suitable_for_two()`。优先看 `maximum occupancy`、`occupancy`、`persons`、`tenants`、`residents` 等字段；人数大于等于 2 即匹配。没有人数字段时，`2 Room`、`2 Zimmer` 或 Couple、Friends、Doppelzimmer、Zweibettzimmer 等明确关键词可匹配。单独出现 `Apartment` 或 `Studio` 不算双人房证据。

Wedding 判断在 `src/matcher.py` 的 `is_in_wedding()`。优先匹配 `Wedding`、`Berlin-Wedding`、`Ortsteil Wedding`。邮编 `13347`、`13349`、`13351`、`13353`、`13355`、`13357`、`13359` 只作辅助依据。只写 Mitte、Moabit、Tiergarten、Prenzlauer Berg、Friedrichshain、Lichtenberg 等不会匹配。

## 本地安装

macOS / Linux:

```bash
cd homeinberlin
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
cd homeinberlin
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 本地运行

未配置 `NTFY_TOPIC` 时会自动进入 dry-run，只打印通知内容，不发送请求，也不修改已通知状态。

```bash
python -m src.main
python -m src.main --dry-run
python -m src.main --dry-run --show-all
pytest
```

发送一条测试通知:

```bash
export NTFY_TOPIC="你的随机主题"
python -m src.main --test-notification
```

Windows PowerShell:

```powershell
$env:NTFY_TOPIC="你的随机主题"
python -m src.main --test-notification
```

清空历史状态并重新接收通知:

```bash
python -m src.main --reset-state
```

需要在交互终端输入 `RESET`。GitHub Actions 等非交互环境不会自动清空。

## ntfy 设置

安装 ntfy 手机 App，然后创建一个足够长的随机主题名。公共 ntfy 主题本质上类似密码，不要放进公开仓库，建议至少包含 24 个随机字符。

生成示例:

```bash
python -c "import secrets; print('shaokun-wedding-' + secrets.token_urlsafe(24))"
```

在手机 ntfy App 中订阅这个主题。项目默认服务器是 `https://ntfy.sh`，也可以设置 `NTFY_SERVER` 使用自建服务器。

## 环境变量

支持以下环境变量:

```bash
NTFY_TOPIC=随机主题
NTFY_SERVER=https://ntfy.sh
DRY_RUN=false
LOG_LEVEL=INFO
REQUEST_TIMEOUT=30
```

日志不会完整打印 `NTFY_TOPIC`。

## GitHub Actions 部署

1. 在 GitHub 创建一个新仓库。
2. 本地初始化并推送:

```bash
git init
git add .
git commit -m "feat: add Home in Berlin monitor"
git branch -M main
git remote add origin git@github.com:你的用户名/home-in-berlin-monitor.git
git push -u origin main
```

3. 打开仓库 Settings -> Secrets and variables -> Actions -> New repository secret。
4. Secret 名称必须是 `NTFY_TOPIC`，值填随机主题名。
5. 打开 Actions 页面，启用 workflow。
6. 也可以进入 `Home in Berlin monitor` workflow 后点击 `Run workflow` 手动运行。
7. Action 日志在每次 run 的 job 页面查看。

工作流文件是 `.github/workflows/monitor.yml`，cron 为 `*/30 * * * *`。GitHub Actions 的 cron 使用 UTC，每 30 分钟调度一次，但 GitHub 可能延迟几分钟执行。

工作流会先运行 `pytest`，测试通过后运行监控程序。如果 `data/seen_listings.json`、`data/active_listings.json` 或 `data/error_state.json` 变化，会自动提交 `chore: update housing monitor state` 并推送。推送前会执行 `git pull --rebase`，尽量避开运行期间的新提交冲突。

## 状态文件

`data/active_listings.json` 保存上一次仍在线的匹配房源，用来判断下架后重新上线。

`data/seen_listings.json` 保存历史通知和最后通知时间。只有通知成功后才写入。

`data/error_state.json` 保存错误通知节流状态，同类错误 24 小时内最多推送一次。

如果 JSON 文件不存在或损坏，程序会安全恢复为空数据。

## 修改规则

双人房关键词在 `src/matcher.py` 的 `TWO_PERSON_KEYWORDS`。Wedding 邮编在 `WEDDING_POSTAL_CODES`，排除区域在 `NEGATIVE_AREAS`。

修改后运行:

```bash
pytest
python -m src.main --dry-run --show-all
```

## 排查没收到通知

先在本地运行 `python -m src.main --dry-run --show-all`，确认有匹配房源。再运行 `python -m src.main --test-notification`，确认 ntfy 主题可用。检查 GitHub Actions Secret 是否叫 `NTFY_TOPIC`，不要把真实主题写进代码或 README。最后查看 Actions 日志中的抓取数量、匹配数量和通知失败信息。
