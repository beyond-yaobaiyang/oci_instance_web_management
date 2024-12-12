import os
import yaml
import logging
from typing import Dict, Any

class Config:
    _instance = None
    _config = None
    _config_path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件"""
        try:
            logging.debug(f"正在加载配置文件: {self._config_path}")
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logging.debug(f"配置文件加载成功: {self._config}")
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
            self._config = {}

    def reload(self):
        """重新加载配置"""
        self._load_config()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        # 每次获取配置时都重新加载
        self._load_config()
        if isinstance(key, str):
            keys = key.split('.')
            value = self._config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    logging.debug(f"获取配置项 {k}: {value}")
                else:
                    logging.debug(f"配置项 {k} 不存在")
                    return default
            return value if value is not None else default
        return default

    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        try:
            if isinstance(key, str):
                keys = key.split('.')
                config = self._config
                for k in keys[:-1]:
                    if k not in config:
                        config[k] = {}
                    config = config[k]
                config[keys[-1]] = value
                
                # 保存到文件
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(self._config, f, allow_unicode=True)
                return True
        except Exception as e:
            print(f"设置配置失败: {str(e)}")
        return False

# 创建全局配置实例
config = Config()
