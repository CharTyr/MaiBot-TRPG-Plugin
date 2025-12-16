"""Markdown 模组解析器"""
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any
from src.common.logger import get_logger

logger = get_logger("trpg_markdown_parser")

class MarkdownModuleParser:
    """Markdown 模组解析器"""
    def parse_markdown(self, md_path: str) -> Optional[Dict[str, Any]]:
        path = Path(md_path)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return self._parse_content(content, path.stem)
        except Exception as e:
            logger.error(f"解析失败: {e}")
            return None

    def _parse_content(self, content: str, filename: str) -> Dict[str, Any]:
        module_data = {
            "info": {"id": filename, "name": filename, "description": "",
                     "author": "Anonymous", "genre": "fantasy", "difficulty": "normal",
                     "player_count": "2-5", "duration": "未知", "tags": []},
            "world_name": filename, "world_background": "", "lore": [],
            "intro_text": "", "starting_location": "起点",
            "npcs": {}, "locations": {}, "events": [], "key_items": [], "endings": [],
        }
        fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if fm:
            for line in fm.group(1).split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip().strip('"\'')
                    if k in ["id", "name", "genre", "difficulty", "author"]:
                        module_data["info"][k] = v
            content = content[fm.end():]
        h1 = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if h1:
            module_data["info"]["name"] = h1.group(1).strip()
            module_data["world_name"] = h1.group(1).strip()
        for m in re.finditer(r"^##\s+(.+)$\n(.*?)(?=^##\s|\Z)", content, re.MULTILINE | re.DOTALL):
            title, body = m.group(1).lower(), m.group(2).strip()
            if "背景" in title or "世界" in title:
                module_data["world_background"] = body[:1000]
            elif "开场" in title or "intro" in title:
                module_data["intro_text"] = body[:1000]
            elif "npc" in title or "角色" in title:
                for nm in re.finditer(r"^###\s+(.+)$\n(.*?)(?=^###\s|\Z)", body, re.MULTILINE | re.DOTALL):
                    module_data["npcs"][nm.group(1).strip()] = {
                        "name": nm.group(1).strip(), "description": nm.group(2).strip()[:500],
                        "attitude": "neutral", "location": "", "dialogue_style": ""
                    }
            elif "地点" in title or "location" in title:
                for lm in re.finditer(r"^###\s+(.+)$\n(.*?)(?=^###\s|\Z)", body, re.MULTILINE | re.DOTALL):
                    module_data["locations"][lm.group(1).strip()] = {
                        "name": lm.group(1).strip(), "description": lm.group(2).strip()[:500]
                    }
            elif "结局" in title or "ending" in title:
                for em in re.finditer(r"^###\s+(.+)$\n(.*?)(?=^###\s|\Z)", body, re.MULTILINE | re.DOTALL):
                    module_data["endings"].append({
                        "name": em.group(1).strip(), "description": em.group(2).strip()[:500], "type": "normal"
                    })
        if not module_data["intro_text"] and module_data["world_background"]:
            module_data["intro_text"] = module_data["world_background"][:500]
        return module_data

def import_markdown_module(md_path: str, save_dir: Path) -> Optional[str]:
    """导入 Markdown 模组"""
    parser = MarkdownModuleParser()
    data = parser.parse_markdown(md_path)
    if not data:
        return None
    try:
        mid = data["info"]["id"]
        save_dir.mkdir(parents=True, exist_ok=True)
        with open(save_dir / f"{mid}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return mid
    except Exception as e:
        logger.error(f"保存失败: {e}")
        return None
