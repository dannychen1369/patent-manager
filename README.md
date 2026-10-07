# 专利案件全生命周期管理系统

> 一款面向专利代理人和企业知识产权管理的 **Windows 桌面应用**，覆盖专利从交底书、撰写、提交、审查到授权、结案的全过程。上传国知局官方文书后，系统会自动识别文书类型、提取关键信息、推进案件阶段并计算答复期限。**全部数据只在本地处理，不依赖任何云服务。**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Ant Design](https://img.shields.io/badge/Ant%20Design-6-1677FF?logo=antdesign&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Platform](https://img.shields.io/badge/平台-Windows-0078D6?logo=windows&logoColor=white)

---

## 项目背景

专利代理工作中，一件专利从申请到授权往往要经历受理、初审、多轮审查意见答复、补正、复审等环节，每个环节都有严格的法定期限。一旦错过期限，专利可能被**视为撤回**或丧失权利。

传统做法依赖人工阅读官文、手动登记期限、在 Excel 中追踪案件状态，效率低而且容易出错。本项目把这条流程自动化：

**上传官文 → 自动识别 → 人工确认 → 案件阶段推进 + 期限生成 → 看板集中提醒**

## 核心功能

| 模块 | 说明 |
| --- | --- |
| 📊 **期限看板** | 集中展示所有案件的待处理、已完成、已超期期限，按到期日排序，临近期限一目了然 |
| 📁 **案件管理** | 案件新建、编辑、确认、删除；记录委托人、专利类型、申请号、代理人等信息；完整保留阶段变更历史 |
| 📤 **官文智能识别** | 上传 PDF 或图片格式的官文，自动识别 **14 类**国知局官方文书（另含交底书、其他），提取申请号、发文日、申请人、专利名称等字段 |
| ⏱️ **期限规则引擎** | 可配置的期限规则，按「文书类型 × 审查轮次 × 专利类型」匹配，自动计算答复截止日 |
| 🔄 **阶段自动流转** | 根据官文类型自动推进案件阶段（共 **18 个阶段**），审查意见按「第 N 次」区分一审、二审、三审及以后 |
| 📎 **附件归档** | 交底材料、CAD 图纸、答复文件等按案件分文件夹存储，可在资源管理器中一键打开 |
| ⚙️ **数据目录设置** | 可自定义数据存放位置，方便备份和迁移 |

## 系统架构

```mermaid
flowchart LR
    subgraph Desktop["桌面应用 (PatentManager.exe)"]
        direction LR
        WV["pywebview 原生窗口"] --> FE["React 19 + Ant Design<br/>前端界面"]
        FE -- "REST API" --> BE["FastAPI 后端"]
        BE --> DB[("SQLite")]
        BE --> FS["本地文件存储<br/>案件附件 / 官文"]
        BE --> OCR["文本提取<br/>PyMuPDF + RapidOCR"]
        OCR --> PARSER["规则解析引擎<br/>文书分类 + 字段提取"]
        PARSER --> RULE["期限规则引擎"]
        PARSER --> STAGE["阶段映射"]
    end
```

### 官文处理流程

```mermaid
flowchart TD
    A["上传官文<br/>PDF / 图片"] --> B{"PDF 有文本层？"}
    B -- 是 --> C["PyMuPDF 直接读取文本<br/>快速、精确"]
    B -- "否（扫描件 / 图片）" --> D["RapidOCR 本地识别"]
    C --> E["文书类型识别<br/>优先匹配标题区域"]
    D --> E
    E --> F["正则提取关键字段<br/>申请号 / 发文日 / 审查轮次…"]
    F --> G["前端展示识别结果<br/>用户核对确认"]
    G --> H["关联案件 + 推进阶段"]
    G --> I["匹配期限规则 → 生成期限"]
```

## 技术亮点

### 1. 混合式文本提取：文本层优先，OCR 兜底
逐页检查 PDF 是否有可用的文本层（每页至少 20 个字符）。有文本层的页面直接用 PyMuPDF 读取，速度快且零误差；扫描件或图片则自动切换到 **RapidOCR（ONNX Runtime）** 本地识别。整个过程不调用任何云端接口，保证客户案件信息不外泄。

### 2. 抗干扰的文书分类
官文正文中经常出现其他文书的名称，例如驳回决定会引用此前的「审查意见通知书」，几乎所有通知书都有「将被视为撤回」这类格式化提醒。为此设计了两条策略：
- **按确定性排序匹配**：先匹配驳回决定、无效决定等终局类文书，再匹配程序性通知；
- **限定标题区域**：只在文档开头的标题区域查找关键词，并使用完整标题短语（如「视为撤回通知书」而不是「视为撤回」），避免正文里的格式化文字造成误判。

### 3. 「最具体优先」的期限规则匹配
期限规则支持对审查轮次和专利类型设置通配（留空即为通用规则）。匹配时，指定了审查轮次的规则优先于通用规则，同一层级内再优先选用指定了专利类型的规则。按月计算期限时正确处理月末（例如 1 月 31 日加 1 个月得到 2 月 28 日或 29 日）。

### 4. 人机协同，安全优先
- 识别结果**必须经用户确认后才会入库**，不盲目信任自动识别；
- 预置的期限规则默认标记为「未核验」，提醒用户对照官方规定逐条确认后再用于真实案件；
- 期限计算只按日历日推算，未计入法定节假日顺延，最终期限请以官文为准。

### 5. 一键安装的桌面化交付
- **pywebview** 把 Web 界面嵌入原生窗口，用户无需打开浏览器；
- 启动时自动选取空闲端口，在后台线程运行 FastAPI，生产环境由同一进程托管前端静态资源；
- **PyInstaller** 打包为独立 exe，**Inno Setup** 制作安装程序，无需管理员权限，并自动检测、静默安装 VC++ 运行库；
- 内置轻量级数据库迁移，升级版本后自动补齐新增字段，旧数据不丢失。

## 支持的官文类型

<details>
<summary>点击展开（14 类官方文书 + 交底书 + 其他）</summary>

交底书 · 受理通知书 · 初步审查合格通知书 · 审查意见通知书（第一次 / 第二次 / 后续）· 补正通知书 · 视为撤回通知书 · 驳回决定 · 复审请求受理通知书 · 复审通知书 · 无效宣告请求受理通知书 · 无效宣告审查决定 · 授权通知书 · 办理登记手续通知书 · 年费缴纳通知书 · 权利恢复相关通知书 · 其他

</details>

## 案件阶段模型

```
待确认 → 待撰写 → 撰写中 → 已提交申请 → 已受理 → 初审阶段 → 一审 → 二审 → 三审及以后 → 授权 → 缴费登记 → 已结案
                                                   ↘ 补正    ↘ 复审    ↘ 无效宣告
                                                   ↘ 驳回    ↘ 视为撤回  ↘ 放弃
```

## 项目结构

```
├── backend/                     # Python 后端
│   ├── app/
│   │   ├── main.py              # FastAPI 入口，托管 SPA 静态资源
│   │   ├── models.py            # SQLAlchemy 数据模型（案件 / 文书 / 期限 / 规则 / 附件）
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── migrations.py        # 轻量级自动迁移
│   │   ├── seed_data.py         # 预置期限规则
│   │   ├── routers/             # RESTful 接口（案件、文书、期限、规则、附件、设置）
│   │   └── services/
│   │       ├── ocr_extract.py   # 文本层提取 + OCR 兜底
│   │       ├── doc_parser.py    # 文书分类与字段提取
│   │       ├── deadline_calc.py # 期限规则匹配与日期计算
│   │       └── stage_mapping.py # 文书 → 案件阶段映射
│   ├── launcher.py              # 桌面入口（pywebview + uvicorn）
│   └── PatentManager.spec       # PyInstaller 打包配置
├── frontend/                    # React + TypeScript 前端
│   └── src/pages/               # 期限看板、案件列表/详情、新建案件、上传文书、规则管理、设置
└── installer.iss                # Inno Setup 安装程序脚本
```

## 本地运行

**环境要求**：Python 3.10+、Node.js 20+

```bash
# 1. 启动后端（端口 8000）
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. 启动前端（端口 5173）
cd frontend
npm install
npm run dev
```

浏览器访问 http://localhost:5173 即可使用。

### 打包为桌面安装程序

```bash
cd frontend && npm run build          # 构建前端
cd ../backend
pip install pyinstaller pywebview
pyinstaller PatentManager.spec        # 生成 dist/PatentManager/
# 然后用 Inno Setup 编译根目录下的 installer.iss，生成 installer_output/PatentManagerSetup.exe
```

## 免责声明

系统自动识别的文书信息和计算出的期限仅供参考，法定期限请以国家知识产权局官方文书载明的内容为准。
