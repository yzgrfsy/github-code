# 简历优化小工具 MVP 设计文档（V1）

## 1. MVP 详细 PRD

### 1.1 产品定位
- 产品名（暂定）：`ResumeBoost`
- 核心价值：将原始简历在 3-10 分钟内优化为可投递版本，提升 ATS 通过率与招聘方可读性。
- 目标人群：应届生、1-5 年经验求职者、转岗求职者。

### 1.2 MVP 目标（首月）
- 用户可完成完整链路：上传简历 -> 选择岗位/JD -> 获得诊断 -> 接受改写 -> 导出 PDF。
- 支持基础商业闭环：免费试用 + 订阅解锁。
- 指标目标：
  - 上传到导出完成率 >= 35%
  - 新用户首日付费转化 >= 3%
  - 单份简历平均处理时长 <= 30 秒（不含用户编辑时间）

### 1.3 功能范围（MVP In Scope）
- 账号体系：邮箱验证码登录（免密码）
- 简历输入：PDF/DOCX 上传、纯文本粘贴
- 结构化解析：教育/经历/项目/技能
- 诊断评分：ATS 兼容度、内容完整度、岗位匹配度
- 智能改写：按岗位方向改写工作经历与项目经历
- JD 定制：支持粘贴 JD，提取关键词并给缺失建议
- 对比编辑：原文/改写并排，支持逐段接受/回退
- 导出：PDF（MVP 必做），Markdown（可选）
- 支付订阅：月付 Pro（Stripe 或国内支付网关二选一）

### 1.4 非范围（MVP Out Scope）
- 多语言完整本地化（仅支持中文主流程）
- AI 模拟面试
- 多人协作与团队空间
- 多模板商城

### 1.5 关键用户故事（User Stories）
1. 作为用户，我希望上传一份旧简历，系统自动识别出各模块，减少手工整理成本。
2. 作为用户，我希望指定目标岗位（如 Python 后端），系统给出匹配度和关键词缺失项。
3. 作为用户，我希望一键改写经历描述，让内容更结果导向并保留真实性。
4. 作为用户，我希望看到每处改写原因，避免“黑盒”输出。
5. 作为用户，我希望下载为 PDF 并可直接投递。

### 1.6 规则与约束
- 单文件大小限制：10MB
- 支持格式：`.pdf`, `.docx`, `.txt`
- 免费用户额度：每月 3 次完整优化
- Pro 用户额度：每月 200 次完整优化（MVP 简化）
- 数据保留策略：
  - 免费用户项目保留 30 天
  - Pro 用户项目保留 180 天

### 1.7 验收标准（MVP Definition of Done）
- 上传解析成功率 >= 95%（针对正常简历样本）
- 评分接口 99 分位响应时间 <= 5 秒
- 改写任务平均耗时 <= 20 秒
- 导出 PDF 成功率 >= 99%
- 支付成功后 10 秒内权益生效

## 2. 页面原型清单

### 2.1 页面列表
1. `P01 登录页`
- 模块：邮箱输入、验证码输入、登录按钮
- 状态：验证码发送中、倒计时、错误提示

2. `P02 工作台/Dashboard`
- 模块：新建项目、最近简历列表、额度显示、订阅入口
- 状态：空状态、列表状态、额度不足提示

3. `P03 新建简历项目`
- 模块：上传文件/粘贴文本、目标岗位、工作年限、目标城市（可选）
- 交互：提交后进入解析页

4. `P04 解析与诊断页`
- 模块：结构化预览（教育/经历/项目/技能）、三维评分卡、问题清单
- 交互：进入“智能改写”

5. `P05 JD 定制页`
- 模块：JD 输入、关键词提取、缺失词清单
- 交互：勾选关键词策略（保守/平衡/激进）

6. `P06 智能改写编辑器`
- 模块：左侧原文、右侧改写、逐段接受/拒绝、全局语气选择
- 状态：改写中、改写完成、改写失败重试

7. `P07 导出页`
- 模块：模板选择（MVP 1 套 ATS 模板）、PDF 预览、下载
- 状态：导出中、导出成功、失败重试

8. `P08 订阅支付页`
- 模块：套餐卡片、权益对比、支付按钮、订单状态

9. `P09 账户设置页`
- 模块：个人信息、数据删除、退出登录

### 2.2 关键交互原型（文字线框）
- 上传后立即解析：`上传成功 -> 解析进度条 -> 结构化结果`
- 改写模式切换：`保守（轻改）/平衡/激进（重写）`
- Diff 交互：每段支持 `接受`、`恢复原文`、`手动编辑`
- 导出前检查：缺少必填模块时提示（如无项目经历）

## 3. 数据库表设计（PostgreSQL）

### 3.1 用户与鉴权

#### `users`
- `id` BIGSERIAL PK
- `email` VARCHAR(255) UNIQUE NOT NULL
- `display_name` VARCHAR(100)
- `status` SMALLINT NOT NULL DEFAULT 1  -- 1=active, 0=disabled
- `created_at` TIMESTAMP NOT NULL DEFAULT now()
- `updated_at` TIMESTAMP NOT NULL DEFAULT now()

索引：`uniq_users_email(email)`

#### `auth_otps`
- `id` BIGSERIAL PK
- `email` VARCHAR(255) NOT NULL
- `code_hash` VARCHAR(255) NOT NULL
- `expired_at` TIMESTAMP NOT NULL
- `used_at` TIMESTAMP
- `created_at` TIMESTAMP NOT NULL DEFAULT now()

索引：`idx_auth_otps_email(email)`, `idx_auth_otps_expired_at(expired_at)`

### 3.2 简历项目主表

#### `resume_projects`
- `id` BIGSERIAL PK
- `user_id` BIGINT NOT NULL REFERENCES users(id)
- `title` VARCHAR(200) NOT NULL
- `target_role` VARCHAR(100) NOT NULL
- `target_city` VARCHAR(100)
- `years_experience` SMALLINT
- `source_type` SMALLINT NOT NULL -- 1=file, 2=text
- `source_file_url` TEXT
- `source_text` TEXT
- `parse_status` SMALLINT NOT NULL DEFAULT 0 -- 0=pending,1=done,2=failed
- `created_at` TIMESTAMP NOT NULL DEFAULT now()
- `updated_at` TIMESTAMP NOT NULL DEFAULT now()

索引：`idx_resume_projects_user_id(user_id)`, `idx_resume_projects_created_at(created_at DESC)`

#### `resume_sections`
- `id` BIGSERIAL PK
- `project_id` BIGINT NOT NULL REFERENCES resume_projects(id)
- `section_type` SMALLINT NOT NULL -- 1=profile,2=education,3=experience,4=project,5=skills
- `origin_text` TEXT NOT NULL
- `optimized_text` TEXT
- `sort_order` INT NOT NULL DEFAULT 0
- `is_accepted` BOOLEAN NOT NULL DEFAULT FALSE
- `created_at` TIMESTAMP NOT NULL DEFAULT now()
- `updated_at` TIMESTAMP NOT NULL DEFAULT now()

索引：`idx_resume_sections_project_id(project_id)`

### 3.3 评分与改写

#### `resume_scores`
- `id` BIGSERIAL PK
- `project_id` BIGINT UNIQUE NOT NULL REFERENCES resume_projects(id)
- `ats_score` SMALLINT NOT NULL
- `completeness_score` SMALLINT NOT NULL
- `match_score` SMALLINT NOT NULL
- `issues_json` JSONB NOT NULL
- `created_at` TIMESTAMP NOT NULL DEFAULT now()

#### `jd_profiles`
- `id` BIGSERIAL PK
- `project_id` BIGINT NOT NULL REFERENCES resume_projects(id)
- `jd_text` TEXT NOT NULL
- `keywords_json` JSONB NOT NULL
- `missing_keywords_json` JSONB NOT NULL
- `created_at` TIMESTAMP NOT NULL DEFAULT now()

索引：`idx_jd_profiles_project_id(project_id)`

#### `rewrite_tasks`
- `id` BIGSERIAL PK
- `project_id` BIGINT NOT NULL REFERENCES resume_projects(id)
- `mode` SMALLINT NOT NULL -- 1=conservative,2=balanced,3=aggressive
- `status` SMALLINT NOT NULL DEFAULT 0 -- 0=queued,1=running,2=done,3=failed
- `error_message` TEXT
- `created_at` TIMESTAMP NOT NULL DEFAULT now()
- `updated_at` TIMESTAMP NOT NULL DEFAULT now()

索引：`idx_rewrite_tasks_project_id(project_id)`, `idx_rewrite_tasks_status(status)`

### 3.4 订阅与计费

#### `plans`
- `id` BIGSERIAL PK
- `plan_code` VARCHAR(50) UNIQUE NOT NULL -- FREE/PRO_MONTHLY
- `name` VARCHAR(100) NOT NULL
- `price_cents` INT NOT NULL
- `quota_per_month` INT NOT NULL
- `created_at` TIMESTAMP NOT NULL DEFAULT now()

#### `subscriptions`
- `id` BIGSERIAL PK
- `user_id` BIGINT NOT NULL REFERENCES users(id)
- `plan_id` BIGINT NOT NULL REFERENCES plans(id)
- `status` SMALLINT NOT NULL -- 1=active,2=expired,3=canceled
- `start_at` TIMESTAMP NOT NULL
- `end_at` TIMESTAMP NOT NULL
- `created_at` TIMESTAMP NOT NULL DEFAULT now()

索引：`idx_subscriptions_user_id(user_id)`, `idx_subscriptions_status(status)`

#### `usage_ledger`
- `id` BIGSERIAL PK
- `user_id` BIGINT NOT NULL REFERENCES users(id)
- `project_id` BIGINT REFERENCES resume_projects(id)
- `action_type` SMALLINT NOT NULL -- 1=full_optimize
- `used_units` INT NOT NULL DEFAULT 1
- `created_at` TIMESTAMP NOT NULL DEFAULT now()

索引：`idx_usage_ledger_user_id(user_id)`, `idx_usage_ledger_created_at(created_at DESC)`

## 4. 接口清单（REST API, `/api/v1`）

### 4.1 鉴权

1. `POST /auth/send-otp`
- 请求：`{ "email": "user@example.com" }`
- 响应：`{ "code": 0, "message": "ok" }`

2. `POST /auth/login-otp`
- 请求：`{ "email": "user@example.com", "otp": "123456" }`
- 响应：`{ "code": 0, "data": { "access_token": "...", "refresh_token": "..." } }`

3. `POST /auth/refresh`
- 请求：`{ "refresh_token": "..." }`
- 响应：新 token

### 4.2 简历项目

4. `POST /projects`
- `multipart/form-data` 或 `application/json`
- 字段：`title,target_role,target_city,years_experience,file|source_text`
- 响应：`project_id`

5. `GET /projects`
- 分页返回用户项目列表

6. `GET /projects/{project_id}`
- 返回项目详情 + section 列表 + 最新评分

7. `DELETE /projects/{project_id}`
- 软删除项目

### 4.3 解析/评分/JD

8. `POST /projects/{project_id}/parse`
- 触发解析任务
- 响应：`task_id`

9. `GET /tasks/{task_id}`
- 查询异步任务状态（parse/rewrite/export）

10. `POST /projects/{project_id}/score`
- 触发评分，返回三维评分与问题列表

11. `POST /projects/{project_id}/jd/analyze`
- 请求：`{ "jd_text": "..." }`
- 响应：关键词、缺失关键词、匹配建议

### 4.4 改写与编辑

12. `POST /projects/{project_id}/rewrite`
- 请求：`{ "mode": "balanced", "use_jd": true }`
- 响应：`rewrite_task_id`

13. `PUT /sections/{section_id}`
- 请求：`{ "optimized_text": "...", "is_accepted": true }`
- 用于人工编辑与接受改写

14. `POST /projects/{project_id}/rewrite/apply-all`
- 一键接受全部改写

### 4.5 导出

15. `POST /projects/{project_id}/export`
- 请求：`{ "format": "pdf", "template": "ats_default" }`
- 响应：`export_task_id`

16. `GET /exports/{export_id}/download`
- 返回下载链接（预签名 URL）

### 4.6 订阅与额度

17. `GET /billing/plans`
- 返回套餐列表

18. `POST /billing/checkout`
- 请求：`{ "plan_code": "PRO_MONTHLY" }`
- 响应：支付链接或支付参数

19. `POST /billing/webhook`
- 支付回调（服务端验签）

20. `GET /billing/me`
- 返回当前订阅、剩余额度、当月使用量

### 4.7 通用错误码（建议）
- `0` 成功
- `1001` 参数错误
- `1002` 未登录/Token 失效
- `1003` 无权限
- `2001` 解析失败
- `2002` 改写失败
- `2003` 导出失败
- `3001` 配额不足
- `3002` 支付未完成
- `9000` 系统异常

## 5. Python 代码架构设计（实现蓝图）

### 5.1 技术选型
- Web 框架：FastAPI
- 异步任务：Celery + Redis
- 数据库：PostgreSQL + SQLAlchemy 2.x + Alembic
- 文件存储：MinIO/S3
- 鉴权：JWT（access + refresh）
- 文档：OpenAPI（FastAPI 自动）

### 5.2 分层目录（建议）
```txt
rec-scene/
  resume_mvp/
    app/
      api/
        v1/
          auth.py
          projects.py
          rewrite.py
          billing.py
      core/
        config.py
        security.py
        logger.py
      db/
        base.py
        session.py
        models/
      schemas/
      services/
        parser_service.py
        scoring_service.py
        rewrite_service.py
        export_service.py
        billing_service.py
      tasks/
        celery_app.py
        parse_tasks.py
        rewrite_tasks.py
        export_tasks.py
      adapters/
        llm/
          base.py
          openai_adapter.py
          mock_adapter.py
        storage/
          s3_storage.py
      main.py
    alembic/
    tests/
    Dockerfile
```

### 5.3 核心设计点
- `LLM Adapter` 抽象层：上层只依赖接口，便于切换模型供应商。
- `Task-first`：解析/改写/导出走异步任务，前端统一轮询 `/tasks/{id}`。
- `Prompt 模板版本化`：将提示词模板放在 `app/prompts/`，每次改动可追踪。
- `安全合规`：PII 字段最小化存储；日志默认脱敏邮箱/手机号。

### 5.4 里程碑（建议）
1. M1（3 天）：鉴权 + 项目 CRUD + 文件上传 + DB 初始化
2. M2（4 天）：解析 + 评分 + JD 分析
3. M3（4 天）：改写任务 + Diff 编辑 + PDF 导出
4. M4（3 天）：订阅支付 + 配额校验 + 基础埋点

## 6. 下一步
- 你确认本设计后，我将直接在 `rec-scene` 内创建 FastAPI MVP 工程骨架，并优先实现：`登录 -> 项目创建 -> 解析/评分 -> 改写 -> 导出` 主链路。
