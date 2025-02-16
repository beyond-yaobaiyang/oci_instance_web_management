import os
import uuid
import logging
from werkzeug.utils import secure_filename

class TenantFileService:
    def __init__(self):
        # 使用项目根目录下的 keys 文件夹
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.upload_folder = os.path.join(self.base_dir, 'keys')
        os.makedirs(self.upload_folder, exist_ok=True)
        logging.info(f"私钥文件存储目录: {self.upload_folder}")

    def save_key_file(self, file):
        """保存私钥文件
        
        Args:
            file: 上传的文件对象
            
        Returns:
            str: 保存后的文件路径（相对路径）
        """
        try:
            if not file:
                logging.error("未提供文件")
                return None

            # 生成文件名
            original_filename = secure_filename(file.filename)
            extension = os.path.splitext(original_filename)[1] or '.pem'
            filename = f"{str(uuid.uuid4())}{extension}"
            
            # 保存文件
            abs_path = os.path.join(self.upload_folder, filename)
            file.save(abs_path)
            logging.info(f"私钥文件保存成功: {abs_path}")
            
            # 返回相对于项目根目录的路径
            rel_path = os.path.relpath(abs_path, self.base_dir)
            logging.info(f"私钥文件相对路径: {rel_path}")
            return rel_path
            
        except Exception as e:
            logging.error(f"保存私钥文件失败: {str(e)}")
            return None

    def delete_key_file(self, file_path):
        """删除私钥文件
        
        Args:
            file_path: 相对文件路径
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 转换为绝对路径
            abs_path = os.path.join(self.base_dir, file_path)
            if os.path.exists(abs_path):
                os.remove(abs_path)
                logging.info(f"私钥文件删除成功: {abs_path}")
                return True
            logging.warning(f"私钥文件不存在: {abs_path}")
            return False
        except Exception as e:
            logging.error(f"删除私钥文件失败: {str(e)}")
            return False
