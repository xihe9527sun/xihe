# ElizaOS · 持久人格AI Agent框架

## 来源
https://docs.elizaos.ai/ · https://github.com/elizaos/eliza · 深度解析: xuqi2024

## 核心价值对曦和

ElizaOS的**个性一致性机制**是曦和最该参考的设计：

### 四层个性保障
1. **系统提示词模板** — 定义Agent的基本行为准则（≈曦和的SOUL.md）
2. **传记/描述(bio)** — 长期背景知识（≈曦和的记忆图谱）
3. **示例对话(messageExamples)** — few-shot规范对话风格
4. **风格指令(style)** — chat/post等场景的风格硬约束

### 分层记忆架构
- DOCUMENT → 完整文档（长期知识库）
- FRAGMENT → 文本片段+向量embedding（RAG检索）
- MESSAGE → 对话历史（短期上下文）
- MEMORY SCOPE → shared/private/room/global记忆隔离
- 对话压缩机制 → 自动摘要替代长历史，节省token

### 插件系统
声明式插件加载，Subaction运行时动态扩展能力

### 对曦和的具体启示
1. "配置即人格"的设计思路 → 曦和应该让暖度/SOUL/身份可配置化
2. 分层记忆(DOCUMENT→FRAGMENT) → 曦和的记忆图谱可以借鉴"文档→片段→向量"的层级
3. 对话压缩 → 赫布事件的自动摘要/折叠机制
4. 风格硬约束 → 曦和的自反层应增加"风格检查"节点
