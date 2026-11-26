# 关键矿产资源知识图谱 · 云端部署镜像

本仓库是课程项目《关键矿产资源知识图谱》的**云端部署镜像**：只包含运行 Web 应用所需的最小文件集合。
完整课程交付（原始材料、审计、PPT、脚本）保存在 Gitee 仓库；这里仅用于 Streamlit Community Cloud 部署。

## 入口与依赖

| 项目 | 位置 |
|---|---|
| 应用入口 | `app.py` |
| Python 依赖 | `requirements.txt` |
| 主题配置 | `.streamlit/config.toml` |
| 图谱快照 | `data/graph.json` |

本机运行：

```powershell
pip install -r requirements.txt
python serve.py            # Windows 推荐（已处理 asyncio 事件循环问题）
# 或： streamlit run app.py
```

## 云端配置（Streamlit Cloud → Settings → Secrets）

```toml
KG_ACCESS_CODE = "你的访问码"

# AI 问答（可选但推荐）：配置后「智能问答」会做 AI 意图识别与回答润色
DEEPSEEK_API_KEY = "sk-..."
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-flash"
```

说明：

- **只配 `KG_ACCESS_CODE`**：未输入访问码的访客只能看到验证页。
- **配了 `DEEPSEEK_API_KEY`**：侧栏显示「AI辅助回答：已配置」，开放类问题会走 DeepSeek（每条问题消耗你的额度）；规则模板类问题仍然确定性回答，不花钱。
- 不配密钥也**不影响**其它功能：自动降级为纯图谱检索，侧栏显示「未配置」。
- Secrets 会在启动时注入进程环境变量，因此 `d_app/rag.py`、`d_app/service.py` 里原有的 `os.getenv(...)` 逻辑无需修改即可生效。

## 数据说明

- 默认使用本地快照 `data/graph.json`，**不需要 Neo4j**。
- `构建与审核`、`查询与验收` 页面会读取 `A/`、`originals/`、`reports/` 中的审计材料，因此这些目录一并保留。
- 云端展示的是本次推送时的数据快照；本地更新图谱后需重新推送才会生效。

## 目录

```
app.py                 Streamlit 入口
kg.py                  图谱核心与查询（标准库）
d_adapter.py           D 模块数据接口
d_app/                 页面视图、可视化、问答与展示逻辑
data/                  图谱快照
A/ B/ C/               原始材料、抽取结果与入库脚本
reports/               执行与审计记录
originals/             保留的原始交付材料（含抽检样本）
D_handoff/             前端交接样例
.streamlit/config.toml 主题与浏览器设置
```
