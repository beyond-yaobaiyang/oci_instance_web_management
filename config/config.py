import os
import yaml
import logging
from typing import Dict, Any

class Config:
    _instance = None
    _config = None
    _tenants = None
    _config_path = None
    _tenants_path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
            cls._tenants_path = os.path.join(os.path.dirname(__file__), 'tenants.yml')
            cls._instance._init_config_files()
            cls._instance._load_config()
        return cls._instance

    def _init_config_files(self):
        """初始化配置文件"""
        # 确保配置文件存在
        if not os.path.exists(self._config_path):
            logging.info(f"创建主配置文件: {self._config_path}")
            with open(self._config_path, 'w', encoding='utf-8') as f:
                yaml.dump({}, f)

        # 确保租户配置文件存在
        if not os.path.exists(self._tenants_path):
            logging.info(f"创建租户配置文件: {self._tenants_path}")
            with open(self._tenants_path, 'w', encoding='utf-8') as f:
                yaml.dump({'tenants': []}, f)

    def _load_config(self):
        """加载配置文件"""
        try:
            logging.debug(f"正在加载配置文件: {self._config_path}")
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            
            logging.debug(f"正在加载租户配置: {self._tenants_path}")
            with open(self._tenants_path, 'r', encoding='utf-8') as f:
                self._tenants = yaml.safe_load(f) or {'tenants': []}
            
            # 将租户配置合并到主配置中
            self._config['tenants'] = self._tenants.get('tenants', [])

        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
            self._config = {'tenants': []}

    def reload(self):
        """重新加载配置"""
        self._load_config()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        try:
            keys = key.split('.')
            value = self._config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        try:
            keys = key.split('.')
            config = self._config
            for k in keys[:-1]:
                config = config.setdefault(k, {})
            config[keys[-1]] = value
            
            # 如果是修改租户配置，则保存到租户配置文件
            if keys[0] == 'tenants':
                logging.info(f"保存租户配置: {value}")
                with open(self._tenants_path, 'w', encoding='utf-8') as f:
                    yaml.dump({'tenants': self._config['tenants']}, f, allow_unicode=True)
            else:
                # 否则保存到主配置文件
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    # 排除租户配置
                    config_without_tenants = {k: v for k, v in self._config.items() if k != 'tenants'}
                    yaml.dump(config_without_tenants, f, allow_unicode=True)
            return True
        except Exception as e:
            logging.error(f"设置配置失败: {str(e)}")
            return False

# 创建全局配置实例
config = Config()
