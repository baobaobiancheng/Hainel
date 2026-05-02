"""
Qwen模型服务实现
使用LangChain集成Qwen模型
"""
from langchain_community.chat_models import ChatTongyi

from app.ai.llm.base import BaseLLMService, LLMConfig
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QwenLLMService(BaseLLMService):
    """Qwen LLM服务实现"""
    
    def _get_default_config(self) -> LLMConfig:
        """获取默认配置"""
        return LLMConfig(
            model_name=settings.LLM_MODEL_NAME,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.LLM_TIMEOUT,
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_API_BASE,
        )
    
    def _create_llm(self) -> ChatTongyi:
        """创建Qwen LangChain LLM实例"""
        try:
            # 使用通义千问（Tongyi）作为Qwen的API接口
            # 如果使用本地部署的Qwen，可以使用其他方式
            llm = ChatTongyi(
                model_name=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                api_key=self.config.api_key,
                dashscope_api_key=self.config.api_key,  # 通义千问使用dashscope
            )
            
            logger.info(f"Qwen LLM服务创建成功: {self.config.model_name}")
            return llm
        except Exception as e:
            logger.error(f"创建Qwen LLM服务失败: {e}", exc_info=True)
            raise


class QwenLocalLLMService(BaseLLMService):
    """Qwen本地部署LLM服务（使用transformers）"""
    
    def _get_default_config(self) -> LLMConfig:
        """获取默认配置"""
        return LLMConfig(
            model_name=settings.LLM_MODEL_NAME,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.LLM_TIMEOUT,
        )
    
    def _create_llm(self):
        """创建本地Qwen LLM实例"""
        try:
            from langchain_community.llms import HuggingFacePipeline
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            import torch
            
            model_name = self.config.model_name
            
            logger.info(f"正在加载本地Qwen模型: {model_name}")
            
            # 加载tokenizer和model
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
            )
            
            # 创建pipeline
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                return_full_text=False,
            )
            
            # 创建LangChain LLM
            llm = HuggingFacePipeline(pipeline=pipe)
            
            logger.info(f"本地Qwen LLM服务创建成功: {model_name}")
            return llm
        except ImportError:
            logger.error("transformers库未安装，无法使用本地Qwen模型")
            raise
        except Exception as e:
            logger.error(f"创建本地Qwen LLM服务失败: {e}", exc_info=True)
            raise


def get_qwen_service(use_local: bool = False) -> BaseLLMService:
    """
    获取Qwen服务实例
    
    Args:
        use_local: 是否使用本地部署的模型
        
    Returns:
        BaseLLMService: Qwen服务实例
    """
    if use_local:
        return QwenLocalLLMService()
    else:
        return QwenLLMService()

