import pandas as pd
from docx import Document
from typing import List, Dict, Optional, Union
from pathlib import Path

class ExcelToWordHandler:
    """Excel转Word处理器"""
    
    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self.file_path: Optional[str] = None
    
    def load_excel(self, file_path: str) -> bool:
        """
        加载Excel文件
        
        Args:
            file_path: Excel文件路径
            
        Returns:
            bool: 加载是否成功
        """
        try:
            self.file_path = file_path
            self.data = pd.read_excel(file_path)
            return True
        except Exception as e:
            print(f"加载Excel文件失败: {e}")
            return False
    
    def get_columns(self) -> List[str]:
        """获取列标题列表"""
        if self.data is not None:
            return self.data.columns.tolist()
        return []
    
    def get_rows_count(self) -> int:
        """获取行数"""
        if self.data is not None:
            return len(self.data)
        return 0
    
    def get_column_preview_data(self, column_name: str, row_index: int = 0) -> str:
        """
        获取指定列的预览数据
        
        Args:
            column_name: 列名
            row_index: 行索引，默认为0（第一行数据）
            
        Returns:
            str: 数据值的字符串表示
        """
        if self.data is not None and column_name in self.data.columns:
            try:
                value = self.data.iloc[row_index][column_name]
                return str(value) if pd.notna(value) else ""
            except (IndexError, KeyError):
                return ""
        return ""
    
    def get_row_preview_data(self, row_index: int) -> List[str]:
        """
        获取指定行的所有列数据
        
        Args:
            row_index: 行索引
            
        Returns:
            List[str]: 该行所有列的数据列表
        """
        if self.data is not None and 0 <= row_index < len(self.data):
            try:
                row_data = self.data.iloc[row_index]
                return [str(val) if pd.notna(val) else "" for val in row_data]
            except IndexError:
                return []
        return []
    
    def generate_word_document(self, 
                             primary_title: str = "",
                             preview_items: Optional[List[Dict[str, str]]] = None,
                             footer_content: str = "",
                             output_path: str = "output.docx") -> bool:
        """
        生成Word文档
        
        Args:
            primary_title: 一级标题
            preview_items: 预览项列表 [{title: str, value: str, style: str}]
            footer_content: 末尾内容
            output_path: 输出文件路径
            
        Returns:
            bool: 生成是否成功
        """
        try:
            doc = Document()
            
            # 添加一级标题
            if primary_title.strip():
                doc.add_heading(primary_title.strip(), level=1)
            
            # 添加预览内容（应用样式）
            if preview_items:
                for item in preview_items:
                    title = item.get("title", "")
                    value = item.get("value", "")
                    style = item.get("style", "默认")
                    
                    if not value.strip():
                        continue
                        
                    if style == "二级标题":
                        doc.add_heading(value.strip(), level=2)
                    elif style == "无序列表":
                        p = doc.add_paragraph()
                        p.style = 'List Bullet'
                        p.add_run(value.strip())
                    elif style == "有序列表":
                        p = doc.add_paragraph()
                        p.style = 'List Number'
                        p.add_run(value.strip())
                    else:  # 默认样式
                        # 如果有标题，显示为"标题: 值"格式
                        display_text = f"{title}: {value}" if title else value
                        doc.add_paragraph(display_text.strip())
            
            # 添加末尾内容（用分割线分隔）
            if footer_content.strip():
                doc.add_paragraph("----------", style="Intense Quote")
                doc.add_paragraph(footer_content.strip())
            
            # 保存文档
            doc.save(output_path)
            return True
            
        except Exception as e:
            print(f"生成Word文档失败: {e}")
            return False
    
    def get_file_info(self) -> Dict[str, Union[str, int]]:
        """获取文件基本信息"""
        info = {
            "file_path": self.file_path or "",
            "rows": self.get_rows_count(),
            "columns": len(self.get_columns()),
            "column_names": self.get_columns()
        }
        return info
