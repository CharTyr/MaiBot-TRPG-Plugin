"""
PDF 模组解析器
用于从 PDF 文件中提取跑团模组信息
"""

import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.plugin_system.apis import llm_api
from src.common.logger import get_logger

logger = get_logger("trpg_pdf_parser")


class PDFModuleParser:
    """PDF 模组解析器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        module_config = config.get("module", {})
        self.parse_model = module_config.get("pdf_parse_model", "utils")
        self.allow_pdf_import = module_config.get("allow_pdf_import", True)

    async def parse_pdf(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """
        解析 PDF 模组文件
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            解析后的模组数据字典，失败返回 None
        """
        if not self.allow_pdf_import:
            logger.warning("[PDFParser] PDF 导入功能已禁用")
            return None
        
        path = Path(pdf_path)
        if not path.exists():
            logger.error(f"[PDFParser] 文件不存在: {pdf_path}")
            return None
        
        if path.suffix.lower() != ".pdf":
            logger.error(f"[PDFParser] 不是 PDF 文件: {pdf_path}")
            return None
        
        try:
            # 提取 PDF 文本
            text = await self._extract_pdf_text(path)
            if not text:
                logger.error("[PDFParser] 无法提取 PDF 文本")
                return None
            
            # 使用 LLM 解析模组结构
            module_data = await self._parse_module_structure(text, path.stem)
            
            return module_data
            
        except Exception as e:
            logger.error(f"[PDFParser] 解析 PDF 失败: {e}")
            return None

    async def _extract_pdf_text(self, path: Path) -> Optional[str]:
        """提取 PDF 文本内容"""
        try:
            # 尝试使用 PyMuPDF (fitz)
            try:
                import fitz  # PyMuPDF
                
                doc = fitz.open(str(path))
                page_count = len(doc)
                text_parts = []
                
                for page_num, page in enumerate(doc):
                    text = page.get_text()
                    if text.strip():
                        text_parts.append(f"=== 第 {page_num + 1} 页 ===\n{text}")
                
                doc.close()
                
                full_text = "\n\n".join(text_parts)
                logger.info(f"[PDFParser] 成功提取 {page_count} 页，共 {len(full_text)} 字符")
                return full_text
                
            except ImportError:
                logger.warning("[PDFParser] PyMuPDF 未安装，尝试使用 pdfplumber")
            
            # 尝试使用 pdfplumber
            try:
                import pdfplumber
                
                text_parts = []
                with pdfplumber.open(str(path)) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        text = page.extract_text()
                        if text:
                            text_parts.append(f"=== 第 {page_num + 1} 页 ===\n{text}")
                
                full_text = "\n\n".join(text_parts)
                logger.info(f"[PDFParser] 成功提取 {len(pdf.pages)} 页，共 {len(full_text)} 字符")
                return full_text
                
            except ImportError:
                logger.warning("[PDFParser] pdfplumber 未安装，尝试使用 PyPDF2")
            
            # 尝试使用 PyPDF2
            try:
                from PyPDF2 import PdfReader
                
                reader = PdfReader(str(path))
                text_parts = []
                
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"=== 第 {page_num + 1} 页 ===\n{text}")
                
                full_text = "\n\n".join(text_parts)
                logger.info(f"[PDFParser] 成功提取 {len(reader.pages)} 页，共 {len(full_text)} 字符")
                return full_text
                
            except ImportError:
                logger.error("[PDFParser] 没有可用的 PDF 解析库，请安装 PyMuPDF、pdfplumber 或 PyPDF2")
                return None
                
        except Exception as e:
            logger.error(f"[PDFParser] 提取 PDF 文本失败: {e}")
            return None

    async def _parse_module_structure(self, text: str, filename: str) -> Optional[Dict[str, Any]]:
        """使用 LLM 解析模组结构"""
        # 限制文本长度，避免超出上下文
        max_chars = 15000
        if len(text) > max_chars:
            # 取开头和结尾部分
            text = text[:max_chars // 2] + "\n\n...(中间内容省略)...\n\n" + text[-max_chars // 2:]
        
        prompt = f"""你是一个专业的 TRPG 模组分析专家。请分析以下 PDF 文档内容，提取跑团模组的关键信息。

文档内容:
{text}

请以 JSON 格式输出以下信息（如果某项信息无法确定，使用合理的默认值）:

```json
{{
    "info": {{
        "id": "{self._sanitize_id(filename)}",
        "name": "模组名称",
        "description": "模组简介（50-100字）",
        "author": "作者名",
        "genre": "类型（fantasy/horror/scifi/modern）",
        "difficulty": "难度（easy/normal/hard）",
        "player_count": "建议人数（如 2-4）",
        "duration": "预计时长",
        "tags": ["标签1", "标签2"]
    }},
    "world_name": "世界观名称",
    "world_background": "世界背景描述（100-200字）",
    "lore": ["设定1", "设定2", "设定3"],
    "intro_text": "开场白文本（100-150字，用于游戏开始时展示）",
    "starting_location": "起始地点名称",
    "starting_time": "起始时间（day/night/dawn/dusk）",
    "starting_weather": "起始天气（sunny/cloudy/rainy/stormy）",
    "npcs": {{
        "NPC名称": {{
            "name": "NPC名称",
            "description": "NPC描述",
            "location": "所在位置",
            "attitude": "态度（friendly/neutral/hostile）"
        }}
    }},
    "locations": {{
        "地点名称": {{
            "name": "地点名称",
            "description": "地点描述",
            "connections": ["连接的其他地点"]
        }}
    }},
    "key_items": [
        {{"name": "物品名", "description": "物品描述"}}
    ],
    "endings": [
        {{"name": "结局名", "condition": "达成条件", "description": "结局描述"}}
    ],
    "dm_notes": "给 DM 的提示和建议"
}}
```

只输出 JSON，不要其他内容。"""

        try:
            models = llm_api.get_available_models()
            model_config = models.get(self.parse_model) or models.get("utils") or list(models.values())[0]
            
            success, response, _, model_name = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.pdf_parse",
                temperature=0.3,  # 低温度以获得更稳定的输出
                max_tokens=4000,
            )
            
            if success and response:
                # 提取 JSON
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 尝试直接解析
                    json_str = response.strip()
                
                import json
                module_data = json.loads(json_str)
                logger.info(f"[PDFParser] 成功解析模组: {module_data.get('info', {}).get('name', '未知')}")
                return module_data
            else:
                logger.error(f"[PDFParser] LLM 解析失败: {response}")
                return None
                
        except Exception as e:
            logger.error(f"[PDFParser] 解析模组结构失败: {e}")
            return None

    def _sanitize_id(self, name: str) -> str:
        """将名称转换为合法的 ID"""
        # 移除特殊字符，转换为小写
        id_str = re.sub(r'[^\w\u4e00-\u9fff]', '_', name.lower())
        # 移除连续下划线
        id_str = re.sub(r'_+', '_', id_str)
        # 移除首尾下划线
        id_str = id_str.strip('_')
        return id_str or "custom_module"


async def import_pdf_module(
    pdf_path: str,
    config: Dict[str, Any],
    save_dir: Path,
) -> Optional[str]:
    """
    导入 PDF 模组
    
    Args:
        pdf_path: PDF 文件路径
        config: 插件配置
        save_dir: 保存目录
        
    Returns:
        成功返回模组 ID，失败返回 None
    """
    parser = PDFModuleParser(config)
    module_data = await parser.parse_pdf(pdf_path)
    
    if not module_data:
        return None
    
    try:
        import json
        
        module_id = module_data.get("info", {}).get("id", "custom_module")
        save_path = save_dir / f"{module_id}.json"
        
        # 确保目录存在
        save_dir.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(module_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[PDFParser] 模组已保存: {save_path}")
        return module_id
        
    except Exception as e:
        logger.error(f"[PDFParser] 保存模组失败: {e}")
        return None
