"""
数据库初始化脚本
用于创建数据库、初始化基础数据等
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.database.base import init_db, engine
from app.utils.logger import get_logger
from sqlalchemy import text

logger = get_logger(__name__)


def create_database():
    """创建数据库（如果不存在）"""
    # 从 DATABASE_URL 中提取数据库名
    db_name = settings.MYSQL_DATABASE
    
    # 创建不包含数据库名的连接 URL（用于创建数据库）
    base_url = (
        f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
        f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}"
    )
    
    from sqlalchemy import create_engine
    temp_engine = create_engine(base_url)
    
    try:
        with temp_engine.connect() as conn:
            # 检查数据库是否存在
            result = conn.execute(
                text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db_name}'")
            )
            exists = result.fetchone() is not None
            
            if not exists:
                # 创建数据库
                conn.execute(text(f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                conn.commit()
                logger.info(f"数据库 {db_name} 创建成功")
            else:
                logger.info(f"数据库 {db_name} 已存在")
    except Exception as e:
        logger.error(f"创建数据库失败: {e}")
        raise
    finally:
        temp_engine.dispose()


def init_tables():
    """初始化数据库表"""
    logger.info("开始初始化数据库表...")
    
    try:
        init_db()
        logger.info("数据库表初始化成功")
    except Exception as e:
        logger.error(f"数据库表初始化失败: {e}")
        raise


def verify_connection():
    """验证数据库连接"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("数据库连接验证成功")
        return True
    except Exception as e:
        logger.error(f"数据库连接验证失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("数据库初始化脚本")
    logger.info("=" * 60)
    
    # 1. 创建数据库
    logger.info("\n步骤 1: 创建数据库")
    create_database()
    
    # 2. 验证连接
    logger.info("\n步骤 2: 验证数据库连接")
    if not verify_connection():
        logger.error("数据库连接失败，退出")
        sys.exit(1)
    
    # 3. 初始化表结构
    logger.info("\n步骤 3: 初始化数据库表")
    logger.info("提示：也可以直接使用 init_database.sql 文件来初始化数据库")
    response = input("是否继续使用 init_db() 创建表？(y/N): ")
    if response.lower() == 'y':
        init_tables()
    else:
        logger.info("跳过表创建，请使用 init_database.sql 文件来初始化数据库")
    
    logger.info("\n" + "=" * 60)
    logger.info("数据库初始化完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

