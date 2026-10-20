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

建议先建**私有 GitHub 仓库**。这是主播使用的内容生成工作台，持有付费 API 配置并可访问咨询档案；不要把它当作 TikTok 订阅用户的自动登录页面。应用还要求 `[app_access]` 访问口令作为额外保护。共享口令适合小范围工作台使用，不替代正式的账号登录系统。

在 Streamlit Community Cloud 新建应用时，选择这个独立仓库的 `main` 分支，入口填 `streamlit_app.py`。在高级设置的 Secrets 中填写与示例文件相同的配置项和真实值；不要把真实密钥写进 GitHub 文件。部署成功后，先检查访问口令，再做一次生成测试。

本地 SQLite 档案文件 `fortunes.db` 不随项目发布。Cloud 的本地文件可能因重启或重新部署而丢失。若要保存咨询档案，请配置 Google Sheets 服务账号，把对应 Google Sheet 的 `records` 工作表首行设为：

```text
id | name | birth_info | report | history | date | ptype
```

并把服务账号的 `client_email` 加为该表格的编辑者。未配置 Google Sheets 时，请勿把 Cloud 上生成的档案视为永久保存。

## 项目内容

- `streamlit_app.py`：会员版界面、五行测算、案例故事和订阅话术生成。
- `requirements.txt`：部署所需 Python 依赖。
- `.streamlit/config.toml`：会员版深色主题。
- `.streamlit/secrets.example.toml`：无真实密钥的配置模板。
- `.gitignore`：排除密钥、档案、日志和本地环境。

本项目目前没有接入 TikTok 订阅状态校验。代码中的“订阅权益”只用于生成直播话术，不会自动核验观众是否已购买订阅。
