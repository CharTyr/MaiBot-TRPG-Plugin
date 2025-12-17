"""Markdown 模组解析器"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

from src.common.logger import get_logger

logger = get_logger("trpg_markdown_parser")


class MarkdownModuleParser:
    """Markdown 模组解析器（零依赖，支持常见 front matter 与章节结构）"""

    FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def parse_markdown(self, md_path: str) -> Optional[Dict[str, Any]]:
        path = Path(md_path)
        if not path.exists():
            return None
        try:
            content = path.read_text(encoding="utf-8")
            return self._parse_content(content, path.stem)
        except Exception as e:
            logger.error(f"解析失败: {e}")
            return None

    def _parse_front_matter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """解析 YAML front matter（仅处理 key: value 与 tags 简单形式）"""
        m = self.FRONT_MATTER_RE.match(content)
        if not m:
            return {}, content

        fm_raw = m.group(1)
        rest = content[m.end():]
        fm: Dict[str, Any] = {}

        for line in fm_raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip("\"'")

            if k == "tags":
                # tags: [a, b] / tags: a,b / tags: a b
                if v.startswith("[") and v.endswith("]"):
                    inner = v[1:-1].strip()
                    tags = [t.strip().strip("\"'") for t in inner.split(",") if t.strip()]
                else:
                    tags = [t.strip().strip("\"'") for t in re.split(r"[,\s]+", v) if t.strip()]
                fm[k] = tags
            else:
                fm[k] = v

        return fm, rest

    def _parse_bullets(self, body: str) -> List[str]:
        """解析简单 bullet 列表（- 开头）"""
        items = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("-"):
                items.append(line.lstrip("-").strip())
        return [i for i in items if i]

    def _parse_content(self, content: str, filename: str) -> Dict[str, Any]:
        module_data: Dict[str, Any] = {
            "info": {
                "id": filename,
                "name": filename,
                "description": "",
                "author": "Anonymous",
                "genre": "fantasy",
                "difficulty": "normal",
                "player_count": "2-5",
                "duration": "未知",
                "tags": [],
            },
            "world_name": filename,
            "world_background": "",
            "lore": [],
            "intro_text": "",
            "starting_location": "起点",
            "starting_time": "day",
            "starting_weather": "sunny",
            "npcs": {},
            "locations": {},
            "events": [],
            "key_items": [],
            "endings": [],
            "dm_notes": "",
            "plot_hooks": [],
        }

        fm, content = self._parse_front_matter(content)
        for k in ("id", "name", "description", "author", "genre", "difficulty", "player_count", "duration", "tags"):
            if k in fm and fm[k] != "":
                module_data["info"][k] = fm[k]
        for k in ("starting_location", "starting_time", "starting_weather", "world_name"):
            if k in fm and fm[k] != "":
                module_data[k] = fm[k]

        # 标题优先覆盖 name/world_name
        h1 = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if h1:
            title = h1.group(1).strip()
            if title:
                module_data["info"]["name"] = title
                module_data["world_name"] = title

        # 章节解析（## / ###）
        for m in re.finditer(r"^##\s+(.+)$\n(.*?)(?=^##\s|\Z)", content, re.MULTILINE | re.DOTALL):
            title = m.group(1).strip().lower()
            body = m.group(2).strip()

            if "背景" in title or "世界" in title:
                module_data["world_background"] = body[:2000]
                continue
            if "开场" in title or "intro" in title:
                module_data["intro_text"] = body[:2000]
                continue
            if "设定" in title or "lore" in title:
                module_data["lore"] = self._parse_bullets(body)[:50]
                continue
            if "物品" in title or "item" in title:
                for item in self._parse_bullets(body):
                    if ":" in item:
                        name, desc = item.split(":", 1)
                        module_data["key_items"].append({"name": name.strip(), "description": desc.strip()[:300]})
                    else:
                        module_data["key_items"].append({"name": item.strip(), "description": ""})
                continue
            if "dm" in title and "提示" in title:
                module_data["dm_notes"] = body[:2000]
                continue

            if "npc" in title or "角色" in title:
                for nm in re.finditer(r"^###\s+(.+)$\n(.*?)(?=^###\s|\Z)", body, re.MULTILINE | re.DOTALL):
                    name = nm.group(1).strip()
                    desc = nm.group(2).strip()
                    module_data["npcs"][name] = {
                        "name": name,
                        "description": desc[:800],
                        "attitude": "neutral",
                        "location": "",
                        "dialogue_style": "",
                    }
                continue

            if "地点" in title or "location" in title:
                for lm in re.finditer(r"^###\s+(.+)$\n(.*?)(?=^###\s|\Z)", body, re.MULTILINE | re.DOTALL):
                    name = lm.group(1).strip()
                    desc = lm.group(2).strip()
                    module_data["locations"][name] = {"name": name, "description": desc[:800], "connections": []}
                continue

            if "结局" in title or "ending" in title:
                for em in re.finditer(r"^###\s+(.+)$\n(.*?)(?=^###\s|\Z)", body, re.MULTILINE | re.DOTALL):
                    module_data["endings"].append(
                        {
                            "name": em.group(1).strip(),
                            "description": em.group(2).strip()[:800],
                            "type": "normal",
                        }
                    )
                continue

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
        module_id = data.get("info", {}).get("id") or Path(md_path).stem
        save_dir.mkdir(parents=True, exist_ok=True)
        with open(save_dir / f"{module_id}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return module_id
    except Exception as e:
        logger.error(f"保存失败: {e}")
        return None
