"""
模组加载器
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from src.common.logger import get_logger
from .base import ModuleBase, ModuleInfo
from .presets import PRESET_MODULES, get_module_list, create_module as create_preset_module

if TYPE_CHECKING:
    from ..models.session import TRPGSession
    from ..models.storage import StorageManager

logger = get_logger("trpg_module_loader")


class ModuleLoader:
    """模组加载器 - 负责加载和应用模组"""

    def __init__(self, modules_dir: Optional[Path] = None):
        self.modules_dir = modules_dir or Path(__file__).parent / "custom"
        self.modules_dir.mkdir(parents=True, exist_ok=True)
        # Markdown 自定义模组目录
        self.custom_modules_dir = Path(__file__).parent.parent / "custom_modules"
        self.custom_modules_dir.mkdir(parents=True, exist_ok=True)
        # 扫描并导入 Markdown 模组
        self._scan_markdown_modules()

    def _scan_markdown_modules(self):
        """扫描并导入 Markdown 模组"""
        from ..services.markdown_parser import import_markdown_module
        
        for md_file in self.custom_modules_dir.glob("*.md"):
            # 跳过模板和说明文件
            if md_file.name.startswith("_") or md_file.name == "README.md":
                continue
            # 检查是否已导入（对应 JSON 存在）
            json_file = self.modules_dir / f"{md_file.stem}.json"
            if json_file.exists():
                # 检查 Markdown 是否更新
                if md_file.stat().st_mtime <= json_file.stat().st_mtime:
                    continue
            # 导入 Markdown 模组
            try:
                module_id = import_markdown_module(str(md_file), self.modules_dir)
                if module_id:
                    logger.info(f"[ModuleLoader] 已导入 Markdown 模组: {md_file.name} -> {module_id}")
            except Exception as e:
                logger.error(f"[ModuleLoader] 导入 Markdown 模组失败 {md_file.name}: {e}")

    def refresh_modules(self):
        """刷新模组列表，重新扫描 Markdown 模组"""
        self._scan_markdown_modules()

    def list_available_modules(self) -> List[Dict[str, Any]]:
        """列出所有可用的模组"""
        modules = []
        
        # 添加预设模组
        modules.extend(get_module_list())
        
        # 添加自定义模组（JSON）
        for module_file in self.modules_dir.glob("*.json"):
            try:
                with open(module_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    info = data.get("info", {})
                    modules.append({
                        "id": info.get("id", module_file.stem),
                        "name": info.get("name", module_file.stem),
                        "genre": info.get("genre", "unknown"),
                        "difficulty": info.get("difficulty", "normal"),
                        "player_count": info.get("player_count", "?"),
                        "custom": True,
                    })
            except Exception:
                continue
        
        return modules

    def load_module(self, module_id: str) -> Optional[ModuleBase]:
        """加载指定的模组"""
        # 首先尝试加载预设模组
        if module_id in PRESET_MODULES:
            return create_preset_module(module_id)
        
        # 尝试加载自定义模组
        module_file = self.modules_dir / f"{module_id}.json"
        if module_file.exists():
            return self._load_custom_module(module_file)
        
        return None

    def _load_custom_module(self, file_path: Path) -> Optional[ModuleBase]:
        """从JSON文件加载自定义模组"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 解析模组信息
            info_data = data.get("info", {})
            info = ModuleInfo(
                id=info_data.get("id", file_path.stem),
                name=info_data.get("name", "未命名模组"),
                description=info_data.get("description", ""),
                author=info_data.get("author", "Anonymous"),
                version=info_data.get("version", "1.0.0"),
                genre=info_data.get("genre", "fantasy"),
                difficulty=info_data.get("difficulty", "normal"),
                player_count=info_data.get("player_count", "2-5"),
                duration=info_data.get("duration", "未知"),
                tags=info_data.get("tags", []),
            )
            
            # 创建模组实例
            module = ModuleBase(
                info=info,
                world_name=data.get("world_name", info.name),
                world_background=data.get("world_background", ""),
                lore=data.get("lore", []),
                intro_text=data.get("intro_text", ""),
                starting_location=data.get("starting_location", "起点"),
                starting_time=data.get("starting_time", "day"),
                starting_weather=data.get("starting_weather", "sunny"),
                dm_notes=data.get("dm_notes", ""),
                plot_hooks=data.get("plot_hooks", []),
                key_items=data.get("key_items", []),
                endings=data.get("endings", []),
            )
            
            return module
            
        except Exception as e:
            logger.error(f"加载模组失败: {e}")
            return None

    def save_custom_module(self, module: ModuleBase) -> bool:
        """保存自定义模组"""
        try:
            module_file = self.modules_dir / f"{module.info.id}.json"
            with open(module_file, "w", encoding="utf-8") as f:
                json.dump(module.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存模组失败: {e}")
            return False

    async def apply_module_to_session(
        self, 
        module: ModuleBase, 
        session: "TRPGSession",
        storage: "StorageManager"
    ) -> bool:
        """将模组应用到会话"""
        try:
            # 设置世界名称
            session.world_name = module.world_name
            
            # 设置世界状态
            session.world_state.location = module.starting_location
            session.world_state.time_of_day = module.starting_time
            session.world_state.weather = module.starting_weather
            session.world_state.location_description = module.world_background
            
            # 添加世界观设定
            session.lore = module.lore.copy()
            
            # 添加NPC
            from ..models.session import NPCState
            for npc_name, npc_template in module.npcs.items():
                session.npcs[npc_name] = NPCState(
                    name=npc_template.name,
                    description=npc_template.description,
                    location=npc_template.location,
                    attitude=npc_template.attitude,
                )
            
            # 添加开场历史记录
            session.add_history("system", f"模组加载: {module.info.name}")
            session.add_history("dm", module.intro_text)
            
            # 保存会话
            await storage.save_session(session)
            
            return True
            
        except Exception as e:
            logger.error(f"应用模组失败: {e}")
            return False

    def get_module_info(self, module_id: str) -> Optional[Dict[str, Any]]:
        """获取模组详细信息"""
        module = self.load_module(module_id)
        if module:
            return {
                "info": {
                    "id": module.info.id,
                    "name": module.info.name,
                    "description": module.info.description,
                    "author": module.info.author,
                    "genre": module.info.genre,
                    "difficulty": module.info.difficulty,
                    "player_count": module.info.player_count,
                    "duration": module.info.duration,
                    "tags": module.info.tags,
                },
                "world_name": module.world_name,
                "world_background": module.world_background[:500] + "..." if len(module.world_background) > 500 else module.world_background,
                "npc_count": len(module.npcs),
                "location_count": len(module.locations),
                "ending_count": len(module.endings),
            }
        return None
