# Maestro Qi 会员咨询工作台

这是从原项目的 `app_subscription.py` 独立整理出的 Streamlit 应用。入口是根目录的 `streamlit_app.py`；普通版 `app.py`、历史数据库、日志和真实密钥均不在此项目中。

## 本地运行

建议使用 Python 3.12。安装依赖后，在本目录运行：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
streamlit run streamlit_app.py
```

先把 `.streamlit/secrets.toml` 中的访问口令、API Key、Base URL 和模型名称替换为真实值。完整报告与直播口播可以使用同一供应商，也可以分别配置。程序通过兼容 OpenAI 的接口调用模型；示例域名不能直接使用。真实 `secrets.toml` 已被 `.gitignore` 排除。

若只想在本机预览界面，可先配置 `[app_access]` 的口令；未配置模型时，页面会打开，但生成操作会提示缺少 API 配置。

## 发布到 GitHub 和 Streamlit Community Cloud

本项目的 GitHub 仓库是**公开的**，源代码和生成规则对所有人可见。真实 API Key、访问口令和咨询档案不得提交到仓库。这是主播使用的内容生成工作台，持有付费 API 配置并可访问咨询档案；不要把它当作 TikTok 订阅用户的自动登录页面。应用要求 `[app_access]` 访问口令作为额外保护。共享口令适合小范围工作台使用，不替代正式的账号登录系统。

在 Streamlit Community Cloud 新建应用时，选择这个独立仓库的 `main` 分支，入口填 `streamlit_app.py`。在高级设置的 Secrets 中填写与示例文件相同的配置项和真实值；不要把真实密钥写进 GitHub 文件。部署成功后，先检查访问口令，再做一次生成测试。

本地 SQLite 档案文件 `fortunes.db` 不随项目发布。Cloud 的本地文件可能因重启或重新部署而丢失，因此需要配置一个云端档案库。程序支持三种后端，由 Secrets 里的 `[storage] backend` 决定（留空则自动探测）：`supabase`、`gsheets`、`sqlite`。

### 方案 A（推荐）：Supabase Postgres

不需要任何 Google 服务账号，也就不会撞上 `iam.disableServiceAccountKeyCreation` 这类组织策略。

1. 在 [supabase.com](https://supabase.com) 新建项目（免费额度足够单机咨询工作台）。
2. 打开 SQL Editor，整段执行仓库根目录的 `supabase_schema.sql`。其中的唯一约束 `(name, birth_info, ptype)` 是覆盖更新所必需的，不能省略。
3. 到 Project Settings → API Keys，复制 **Project URL** 和 **secret key**（新界面是 `sb_secret_...`；旧界面在 Legacy API keys 里的 `service_role` JWT 同样可用）。
4. 在 Streamlit Cloud 的 Secrets 中填写：

```toml
[storage]
backend = "supabase"

[supabase]
url = "https://your-project-ref.supabase.co"
service_role_key = "your-service-role-key"
```

`secret key` / `service_role` key 相当于数据库管理员权限，只放在 Secrets 里，不要提交、不要贴到聊天工具。`supabase_schema.sql` 已开启 RLS 并撤销了 `anon` 权限，因此数据库不会被公开 key 读写。

5. 部署后回到「咨询档案」，标题下方应显示「当前档案存储：Supabase Postgres 云端持久化」。若仍显示本地 SQLite 或出现连接警告，说明 Secrets 没被读到。

已有本地档案需要搬上云时，运行迁移脚本（可重复执行，按姓名+生日+测算类型覆盖）：

```bash
python scripts/migrate_sqlite_to_supabase.py --dry-run   # 先看条数
python scripts/migrate_sqlite_to_supabase.py             # 真正上传
```

脚本会依次从 `--url/--key`、环境变量 `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`、`.streamlit/secrets.toml` 读取配置。

### 方案 B（可选）：Google Sheets

需要 Google Cloud 服务账号 JSON 密钥。如果你的组织启用了 `iam.disableServiceAccountKeyCreation`，将无法创建密钥，请改用方案 A。配置时把对应 Google Sheet 的 `records` 工作表首行设为：

```text
id | name | birth_info | report | history | date | ptype
```

并把服务账号的 `client_email` 加为该表格的编辑者。注意 Sheets 单个单元格上限为 50,000 字符，长篇报告可能写不进去，Supabase 没有这个限制。

### 兜底行为

云端写入失败时，程序会自动把报告存进本地 SQLite，并在界面上提示「已临时保存到本地」。这只保证当前不丢内容，Cloud 容器重启后本地记录仍会消失，请尽快修复云端配置后重新保存。

## 项目内容

- `streamlit_app.py`：会员版界面、五行测算、案例故事和订阅话术生成。
- `requirements.txt`：部署所需 Python 依赖。
- `supabase_schema.sql`：Supabase 档案表建表脚本（含唯一约束与权限设置）。
- `scripts/migrate_sqlite_to_supabase.py`：本地 SQLite 档案迁移到 Supabase。
- `.streamlit/config.toml`：会员版深色主题。
- `.streamlit/secrets.example.toml`：无真实密钥的配置模板。
- `.gitignore`：排除密钥、档案、日志和本地环境。

本项目目前没有接入 TikTok 订阅状态校验。代码中的“订阅权益”只用于生成直播话术，不会自动核验观众是否已购买订阅。
