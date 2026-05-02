"""
应用配置文件
管理数据库、AI模型、业务参数等配置
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """应用配置类"""
    
    # ========== 基础配置 ==========
    PROJECT_NAME: str = "医疗健康咨询与辅助诊断系统"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = Field(default=False, description="调试模式")
    
    # ========== 服务器配置 ==========
    HOST: str = Field(default="0.0.0.0", description="服务器主机")
    PORT: int = Field(default=8001, description="服务器端口")
    
    # ========== 数据库配置 ==========
    # MySQL配置
    MYSQL_HOST: str = Field(default="localhost", description="MySQL主机")
    MYSQL_PORT: int = Field(default=3306, description="MySQL端口")
    MYSQL_USER: str = Field(default="root", description="MySQL用户名")
    MYSQL_PASSWORD: str = Field(default="", description="MySQL密码")
    MYSQL_DATABASE: str = Field(default="medical_system", description="MySQL数据库名")
    MYSQL_CHARSET: str = Field(default="utf8mb4", description="MySQL字符集")
    
    @property
    def DATABASE_URL(self) -> str:
        """构建数据库连接URL"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset={self.MYSQL_CHARSET}"
        )
    
    # Redis配置
    REDIS_HOST: str = Field(default="localhost", description="Redis主机")
    REDIS_PORT: int = Field(default=6379, description="Redis端口")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis密码")
    REDIS_DB: int = Field(default=0, description="Redis数据库编号")
    REDIS_DECODE_RESPONSES: bool = Field(default=True, description="Redis响应解码")
    
    @property
    def REDIS_URL(self) -> str:
        """构建Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ========== 安全配置 ==========
    # JWT配置
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT密钥"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT算法")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24, description="访问令牌过期时间（分钟）")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="刷新令牌过期时间（天）")
    
    # 密码加密配置
    PASSWORD_HASH_ALGORITHM: str = Field(default="bcrypt", description="密码哈希算法")
    PASSWORD_ROUNDS: int = Field(default=12, description="密码哈希轮数")
    
    # CORS配置
    CORS_ORIGINS: list[str] = Field(
        default=["*"],
        description="允许的CORS源"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="允许CORS凭证")
    CORS_ALLOW_METHODS: list[str] = Field(
        default=["*"],
        description="允许的HTTP方法"
    )
    CORS_ALLOW_HEADERS: list[str] = Field(
        default=["*"],
        description="允许的HTTP头"
    )
    
    # ========== AI模型配置 ==========
    # 大语言模型配置
    LLM_PROVIDER: str = Field(default="qwen", description="LLM提供商: qwen, chatglm, openai")
    LLM_MODEL_NAME: str = Field(default="Qwen/Qwen2.5-7B-Instruct", description="LLM模型名称")
    LLM_API_BASE: Optional[str] = Field(default=None, description="LLM API基础URL")
    LLM_API_KEY: Optional[str] = Field(default=None, description="LLM API密钥")
    LLM_TEMPERATURE: float = Field(default=0.7, description="LLM温度参数")
    LLM_MAX_TOKENS: int = Field(default=2048, description="LLM最大token数")
    LLM_TIMEOUT: int = Field(default=60, description="LLM请求超时时间（秒）")
    
    # OCR配置（统一使用百炼平台 qwen-vl-ocr，复用 LLM_API_KEY）
    OCR_PROVIDER: str = Field(default="dashscope", description="OCR提供商: dashscope")
    
    # 向量嵌入配置（使用通义千问 text-embedding-v2，维度 1536）
    EMBEDDING_MODEL: str = Field(default="text-embedding-v2", description="嵌入模型名称")
    EMBEDDING_DIMENSION: int = Field(default=1536, description="嵌入向量维度")
    
    # ========== 智能体配置 ==========
    # 复杂度评估配置
    COMPLEXITY_LOW_THRESHOLD: int = Field(default=40, description="低复杂度阈值")
    COMPLEXITY_MEDIUM_THRESHOLD: int = Field(default=70, description="中复杂度阈值")
    
    # PCC模式配置
    PCC_AGENT_COUNT: int = Field(default=1, description="PCC模式智能体数量")
    PCC_MAX_ROUNDS: int = Field(default=5, description="PCC模式最大对话轮数")
    
    # MDT模式配置
    MDT_MIN_AGENTS: int = Field(default=3, description="MDT模式最小智能体数")
    MDT_MAX_AGENTS: int = Field(default=5, description="MDT模式最大智能体数")
    MDT_MAX_DISCUSSION_ROUNDS: int = Field(default=3, description="MDT模式最大讨论轮数")
    MDT_CONSENSUS_THRESHOLD: float = Field(default=0.6, description="MDT模式共识阈值（60%）")
    MDT_MAX_ROUNDS: int = Field(default=10, description="MDT模式最大对话轮数")
    
    # ICT模式配置
    ICT_MIN_AGENTS: int = Field(default=5, description="ICT模式最小智能体数")
    ICT_MAX_AGENTS: int = Field(default=7, description="ICT模式最大智能体数")
    ICT_MAX_ROUNDS: int = Field(default=15, description="ICT模式最大对话轮数")
    
    # ========== 业务参数配置 ==========
    # 会话配置
    CONVERSATION_MAX_MESSAGES: int = Field(default=1000, description="会话最大消息数")
    CONVERSATION_TIMEOUT_MINUTES: int = Field(default=30, description="会话超时时间（分钟）")
    
    # 病历配置
    MEDICAL_RECORD_MAX_SIZE: int = Field(default=10 * 1024 * 1024, description="病历最大大小（字节）")
    MEDICAL_RECORD_AUTO_ARCHIVE_DAYS: int = Field(default=90, description="病历自动归档天数")
    
    # 文件上传配置
    UPLOAD_DIR: str = Field(default="uploads", description="文件上传目录")
    MAX_UPLOAD_SIZE: int = Field(default=10 * 1024 * 1024, description="最大上传文件大小（字节）")
    ALLOWED_EXTENSIONS: list[str] = Field(
        default=["jpg", "jpeg", "png", "webp", "bmp", "pdf", "doc", "docx"],
        description="允许的文件扩展名"
    )
    
    # 缓存配置
    CACHE_DEFAULT_TTL: int = Field(default=3600, description="缓存默认TTL（秒）")
    CACHE_PREFIX: str = Field(default="medical_system:", description="缓存键前缀")
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    LOG_FILE: Optional[str] = Field(default=None, description="日志文件路径")
    LOG_MAX_BYTES: int = Field(default=10 * 1024 * 1024, description="日志文件最大大小（字节）")
    LOG_BACKUP_COUNT: int = Field(default=5, description="日志备份文件数量")
    
    # ========== 知识库配置 ==========
    KNOWLEDGE_BASE_TYPE: str = Field(default="milvus_lite", description="知识库类型")
    KNOWLEDGE_CACHE_TTL: int = Field(default=86400, description="知识库缓存TTL（秒）")

    # Milvus Lite 配置（本地文件，无需独立服务进程）
    MILVUS_URI: str = Field(default="data/milvus.db", description="Milvus Lite 本地数据库文件路径")
    MILVUS_COLLECTION_NAME: str = Field(default="medical_knowledge", description="Milvus 集合名称")

    # Chroma 本地向量知识库配置
    CHROMA_PERSIST_DIR: str = Field(default="data/chroma_db", description="Chroma 持久化目录")
    CHROMA_COLLECTION_NAME: str = Field(default="medical_knowledge", description="Chroma 集合名称")
    CHROMA_EMBEDDING_MODEL: str = Field(
        default="BAAI/bge-small-zh-v1.5",  # 本地中文 embedding 模型，需提前下载
        description="Chroma Embedding 模型路径或名称"
    )
    CHROMA_MODEL_CACHE_DIR: str = Field(
        default="models",
        description="Embedding 模型缓存目录"
    )
    CHROMA_CHUNK_SIZE: int = Field(default=512, description="文档分块大小")
    CHROMA_CHUNK_OVERLAP: int = Field(default=50, description="文档分块重叠")

    # ========== DeepSeek 模型配置 ==========
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, description="DeepSeek API密钥")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com", description="DeepSeek API基础URL")
    DEEPSEEK_MODEL: str = Field(default="deepseek-v4-flash", description="DeepSeek默认模型")

    # ========== Neo4j 知识图谱配置 ==========
    NEO4J_URI:      str = Field(default="bolt://localhost:7687", description="Neo4j 连接地址")
    NEO4J_USER:     str = Field(default="neo4j",                description="Neo4j 用户名")
    NEO4J_PASSWORD: str = Field(default="password",             description="Neo4j 密码")
    NEO4J_DATABASE: str = Field(default="neo4j",                description="Neo4j 数据库名")
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = Field(default=50, description="连接池大小")

    # ========== NLP 模型配置 ==========
    NLP_MODELS_DIR:  str = Field(default="nlp_models",     description="NLP 模型根目录")
    NER_MODEL_PATH:  str = Field(default="nlp_models/ner", description="NER 模型目录")
    RE_MODEL_PATH:   str = Field(default="nlp_models/re",  description="RE 模型目录")
    CWS_MODEL_PATH:  str = Field(default="nlp_models/cws", description="CWS 模型目录")
    NLP_DEVICE:      str = Field(default="cpu",            description="推理设备: cpu / cuda")
    
    # ========== 任务队列配置 ==========
    CELERY_BROKER_URL: Optional[str] = Field(default=None, description="Celery Broker URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(default=None, description="Celery结果后端URL")
    
    @property
    def CELERY_BROKER_URL_AUTO(self) -> str:
        """自动构建Celery Broker URL"""
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        return self.REDIS_URL
    
    @property
    def CELERY_RESULT_BACKEND_AUTO(self) -> str:
        """自动构建Celery结果后端URL"""
        if self.CELERY_RESULT_BACKEND:
            return self.CELERY_RESULT_BACKEND
        return self.REDIS_URL
    
    # ========== 评估与训练配置 ==========
    # 奖励权重配置
    REWARD_ACCURACY_WEIGHT: float = Field(default=5.0, description="诊断准确性奖励权重")
    REWARD_EFFICIENCY_WEIGHT: float = Field(default=1.0, description="信息获取效率奖励权重")
    REWARD_COLLABORATION_WEIGHT: float = Field(default=1.0, description="协作效率奖励权重")
    REWARD_COMPLIANCE_WEIGHT: float = Field(default=1.0, description="遵循规范奖励权重")
    
    # 训练配置
    TRAINING_BATCH_SIZE: int = Field(default=32, description="训练批次大小")
    TRAINING_LEARNING_RATE: float = Field(default=1e-5, description="学习率")
    TRAINING_MAX_EPOCHS: int = Field(default=10, description="最大训练轮数")
    
    # ========== 验证器 ==========
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"日志级别必须是 {valid_levels} 之一")
        return v.upper()
    
    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        valid_providers = ["qwen", "chatglm", "openai"]
        if v.lower() not in valid_providers:
            raise ValueError(f"LLM提供商必须是 {valid_providers} 之一")
        return v.lower()
    
    @field_validator("OCR_PROVIDER")
    @classmethod
    def validate_ocr_provider(cls, v: str) -> str:
        valid_providers = ["dashscope"]
        if v.lower() not in valid_providers:
            raise ValueError(f"OCR提供商必须是 {valid_providers} 之一")
        return v.lower()
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


# 创建全局配置实例
settings = Settings()


# 导出配置
__all__ = ["settings", "Settings"]

