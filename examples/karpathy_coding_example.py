"""
Karpathy 风格编码示例

展示如何使用 karpathy-coding skill 进行代码编写和审查
"""

# 示例 1: 过度工程化的代码（需要简化）
def process_user_data_over engineered(user_data):
    """
    过度工程化的用户数据处理
    问题：不必要的抽象和复杂性
    """
    class DataProcessor:
        def __init__(self, config):
            self.config = config
            self.handlers = []
            self.middleware = []
        
        def register_handler(self, handler):
            self.handlers.append(handler)
            return self
        
        def add_middleware(self, middleware):
            self.middleware.append(middleware)
            return self
        
        def process(self, data):
            # 应用中间件
            for mw in self.middleware:
                data = mw(data)
            
            # 应用处理器
            for handler in self.handlers:
                data = handler(data)
            
            return data
    
    # 创建处理器链
    processor = DataProcessor({"validate": True})
    processor.register_handler(lambda x: x.strip())
    processor.register_handler(lambda x: x.lower())
    processor.add_middleware(lambda x: x if x else "")
    
    return processor.process(user_data)


# 示例 2: Karpathy 风格的简化版本
def process_user_data(user_data: str) -> str:
    """
    简化的用户数据处理
    优点：直接、清晰、易于理解
    """
    if not user_data:
        return ""
    return user_data.strip().lower()


# 示例 3: 需要审查的复杂代码
class UserManager:
    """
    用户管理类 - 可能需要简化
    """
    def __init__(self, db_connection, cache_manager, event_bus, logger):
        self.db = db_connection
        self.cache = cache_manager
        self.events = event_bus
        self.logger = logger
        self.users = {}
        self.observers = []
    
    def add_observer(self, observer):
        self.observers.append(observer)
    
    def notify_observers(self, event, data):
        for observer in self.observers:
            observer(event, data)
    
    def get_user(self, user_id):
        # 检查缓存
        if user_id in self.cache:
            return self.cache[user_id]
        
        # 查询数据库
        user = self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        
        if user:
            # 更新缓存
            self.cache[user_id] = user
            # 记录日志
            self.logger.info(f"User {user_id} loaded from database")
            # 发送事件
            self.events.publish("user.loaded", {"user_id": user_id})
            # 通知观察者
            self.notify_observers("user_loaded", user)
        
        return user
    
    def create_user(self, user_data):
        # 验证数据
        if not self._validate_user_data(user_data):
            raise ValueError("Invalid user data")
        
        # 插入数据库
        user_id = self.db.insert("users", user_data)
        
        # 更新缓存
        self.cache[user_id] = user_data
        
        # 记录日志
        self.logger.info(f"User {user_id} created")
        
        # 发送事件
        self.events.publish("user.created", {"user_id": user_id})
        
        # 通知观察者
        self.notify_observers("user_created", user_data)
        
        return user_id
    
    def _validate_user_data(self, data):
        return bool(data.get("name")) and bool(data.get("email"))


# 示例 4: 使用 Karpathy 风格重构后的版本
from typing import Optional, Dict, Any


def get_user(db, user_id: str) -> Optional[Dict[str, Any]]:
    """获取用户信息"""
    return db.query(f"SELECT * FROM users WHERE id = {user_id}")


def create_user(db, user_data: Dict[str, Any]) -> str:
    """创建新用户"""
    if not user_data.get("name") or not user_data.get("email"):
        raise ValueError("Name and email are required")
    
    return db.insert("users", user_data)


# 示例 5: 过度设计的配置系统
class AppConfig:
    """
    过度设计的配置类
    """
    def __init__(self):
        self._config = {}
        self._validators = {}
        self._transformers = {}
        self._listeners = []
    
    def register_validator(self, key, validator):
        self._validators[key] = validator
        return self
    
    def register_transformer(self, key, transformer):
        self._transformers[key] = transformer
        return self
    
    def add_listener(self, listener):
        self._listeners.append(listener)
        return self
    
    def set(self, key, value):
        # 验证
        if key in self._validators:
            if not self._validators[key](value):
                raise ValueError(f"Invalid value for {key}")
        
        # 转换
        if key in self._transformers:
            value = self._transformers[key](value)
        
        old_value = self._config.get(key)
        self._config[key] = value
        
        # 通知监听器
        for listener in self._listeners:
            listener(key, old_value, value)
    
    def get(self, key, default=None):
        return self._config.get(key, default)


# 示例 6: 简化的配置（Karpathy 风格）
from dataclasses import dataclass


@dataclass
class Config:
    """简化的配置类"""
    debug: bool = False
    host: str = "localhost"
    port: int = 8080
    database_url: str = "sqlite:///app.db"


def load_config_from_env() -> Config:
    """从环境变量加载配置"""
    import os
    return Config(
        debug=os.getenv("DEBUG", "false").lower() == "true",
        host=os.getenv("HOST", "localhost"),
        port=int(os.getenv("PORT", "8080")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///app.db")
    )


# 使用示例
if __name__ == "__main__":
    # 过度工程化的用法
    config = AppConfig()
    config.register_validator("port", lambda x: isinstance(x, int) and 0 < x < 65536)
    config.register_transformer("host", lambda x: x.lower().strip())
    config.set("host", "localhost")
    config.set("port", 8080)
    
    # Karpathy 风格的用法
    config = load_config_from_env()
    print(f"Server running on {config.host}:{config.port}")
