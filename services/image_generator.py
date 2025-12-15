"""
场景图片生成服务
使用 planner 模型生成提示词，调用生图 API 生成场景图片
"""

import json
import base64
import urllib.request
from typing import Optional, Dict, Any, Tuple, TYPE_CHECKING
from src.plugin_system.apis import llm_api
from src.common.logger import get_logger

if TYPE_CHECKING:
    from ..models.session import TRPGSession
    from ..models.player import Player

logger = get_logger("trpg_image_generator")

# 图片尺寸预设
SIZE_PRESETS = {
    "portrait": (768, 1024),   # 竖版 3:4
    "landscape": (1024, 768),  # 横版 4:3
    "wide": (1024, 512),       # 宽幅 2:1
    "square": (1024, 1024),    # 正方形 1:1
}


class ImageGenerator:
    """场景图片生成器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.image_config = config.get("image", {})
        self.llm_models_config = config.get("llm_models", {})
        
        self.enabled = self.image_config.get("enabled", False)
        self.api_type = self.image_config.get("api_type", "openai")
        self.base_url = self.image_config.get("base_url", "")
        self.api_key = self.image_config.get("api_key", "")
        self.model_name = self.image_config.get("model_name", "")
        
        # 尺寸配置
        self.default_size_preset = self.image_config.get("default_size_preset", "landscape")
        self.custom_width = self.image_config.get("custom_width", 0)
        self.custom_height = self.image_config.get("custom_height", 0)
        
        # 提示词配置
        self.prompt_prefix = self.image_config.get("prompt_prefix", "fantasy illustration, detailed background, ")
        self.character_prompt_prefix = self.image_config.get("character_prompt_prefix", "character portrait, detailed, ")
        
        # 自动生成配置
        self.auto_generate = self.image_config.get("auto_generate", False)
        self.auto_generate_interval = self.image_config.get("auto_generate_interval", 10)

    def is_enabled(self) -> bool:
        """检查是否启用图片生成"""
        return self.enabled and bool(self.base_url or self.api_type == "novelai")

    def get_image_size(self, size_preset: str = None) -> Tuple[int, int]:
        """获取图片尺寸"""
        if self.custom_width > 0 and self.custom_height > 0:
            return (self.custom_width, self.custom_height)
        
        preset = size_preset or self.default_size_preset
        return SIZE_PRESETS.get(preset, SIZE_PRESETS["landscape"])

    async def generate_scene_prompt(
        self,
        session: "TRPGSession",
        context: str = "",
        image_type: str = "scene",  # scene, character, item
    ) -> Tuple[bool, str, str]:
        """
        使用 planner 模型生成场景图片提示词
        
        Returns:
            (成功, 提示词, 推荐尺寸预设)
        """
        # 构建场景描述
        world = session.world_state
        scene_desc = f"""
世界观: {session.world_name}
当前位置: {world.location}
时间: {world.time_of_day}
天气: {world.weather}
场景描述: {world.location_description or "无"}
"""
        
        # 获取最近的历史记录
        recent_history = session.get_recent_history(5)
        history_text = ""
        if recent_history:
            history_lines = []
            for h in recent_history[-3:]:
                if h.entry_type == "dm":
                    history_lines.append(f"[DM]: {h.content[:100]}")
                elif h.entry_type == "player":
                    history_lines.append(f"[玩家]: {h.content[:50]}")
            history_text = "\n".join(history_lines)
        
        # NPC 信息
        npc_info = ""
        if session.npcs:
            npc_list = [f"{name}" for name in list(session.npcs.keys())[:3]]
            npc_info = f"场景中的NPC: {', '.join(npc_list)}"
        
        prompt = f"""你是一个专业的AI绘画提示词生成专家。请根据以下跑团场景信息，生成一段英文图片生成提示词。

{scene_desc}

最近的游戏记录:
{history_text if history_text else "(无)"}

{npc_info}

额外上下文: {context if context else "无"}

请以 JSON 格式输出：
{{
    "prompt": "英文提示词，使用逗号分隔的关键词格式",
    "size_preset": "推荐的尺寸预设: portrait(竖版,适合角色特写), landscape(横版,适合场景), wide(宽幅,适合全景)"
}}

提示词规则：
1. 使用英文关键词，逗号分隔
2. 描述场景氛围、光线、天气
3. 如果有角色，描述其位置和动作
4. 不要添加质量词（系统会自动添加）
5. 不要添加任何NSFW内容

只输出 JSON，不要其他内容。"""

        try:
            # 使用 planner 模型
            models = llm_api.get_available_models()
            model_name = self.llm_models_config.get("image_prompt_model", "planner")
            model_config = models.get(model_name) or models.get("planner") or list(models.values())[0]
            
            success, response, _, used_model = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.image_prompt",
                temperature=0.7,
                max_tokens=300,
            )
            
            if success and response:
                # 解析 JSON
                try:
                    # 尝试提取 JSON
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        prompt_text = data.get("prompt", "")
                        size_preset = data.get("size_preset", "landscape")
                        
                        # 添加前缀
                        if image_type == "character":
                            final_prompt = self.character_prompt_prefix + prompt_text
                        else:
                            final_prompt = self.prompt_prefix + prompt_text
                        
                        logger.info(f"[ImageGenerator] 生成提示词成功: {final_prompt[:100]}...")
                        return True, final_prompt, size_preset
                except json.JSONDecodeError:
                    pass
                
                # 回退：直接使用响应作为提示词
                return True, self.prompt_prefix + response.strip(), "landscape"
            
            return False, "生成提示词失败", "landscape"
            
        except Exception as e:
            logger.error(f"[ImageGenerator] 生成提示词失败: {e}")
            return False, str(e), "landscape"

    async def generate_character_prompt(
        self,
        player: "Player",
        session: "TRPGSession",
    ) -> Tuple[bool, str]:
        """生成角色立绘提示词"""
        prompt = f"""你是一个专业的AI绘画提示词生成专家。请根据以下角色信息，生成一段英文角色立绘提示词。

角色名: {player.character_name}
世界观: {session.world_name}

请生成一段英文提示词，描述这个角色的外貌、服装、姿势。
使用逗号分隔的关键词格式，不要添加质量词。
只输出提示词，不要其他内容。"""

        try:
            models = llm_api.get_available_models()
            model_name = self.llm_models_config.get("image_prompt_model", "planner")
            model_config = models.get(model_name) or models.get("planner") or list(models.values())[0]
            
            success, response, _, _ = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.character_prompt",
                temperature=0.7,
                max_tokens=200,
            )
            
            if success and response:
                final_prompt = self.character_prompt_prefix + response.strip()
                return True, final_prompt
            
            return False, "生成失败"
            
        except Exception as e:
            logger.error(f"[ImageGenerator] 生成角色提示词失败: {e}")
            return False, str(e)

    async def generate_image(
        self,
        prompt: str,
        size_preset: str = None,
    ) -> Tuple[bool, str]:
        """
        调用生图 API 生成图片
        
        Returns:
            (成功, base64图片数据或错误信息)
        """
        if not self.is_enabled():
            return False, "图片生成功能未启用"
        
        width, height = self.get_image_size(size_preset)
        
        try:
            if self.api_type.lower() == "openai":
                return await self._generate_openai(prompt, width, height)
            elif self.api_type.lower() == "sd_api":
                return await self._generate_sd_api(prompt, width, height)
            else:
                return False, f"不支持的 API 类型: {self.api_type}"
                
        except Exception as e:
            logger.error(f"[ImageGenerator] 生成图片失败: {e}")
            return False, str(e)

    async def _generate_openai(self, prompt: str, width: int, height: int) -> Tuple[bool, str]:
        """使用 OpenAI 兼容 API 生成图片"""
        import asyncio
        
        url = f"{self.base_url.rstrip('/')}/images/generations"
        
        # 构建请求
        size_str = f"{width}x{height}"
        data = {
            "model": self.model_name or "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": size_str,
            "response_format": "b64_json",
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            
            def do_request():
                with urllib.request.urlopen(req, timeout=120) as response:
                    return json.loads(response.read().decode("utf-8"))
            
            result = await asyncio.to_thread(do_request)
            
            if "data" in result and len(result["data"]) > 0:
                b64_data = result["data"][0].get("b64_json", "")
                if b64_data:
                    return True, b64_data
            
            return False, "API 返回数据格式错误"
            
        except Exception as e:
            return False, str(e)

    async def _generate_sd_api(self, prompt: str, width: int, height: int) -> Tuple[bool, str]:
        """使用 Stable Diffusion WebUI API 生成图片"""
        import asyncio
        
        url = f"{self.base_url.rstrip('/')}/sdapi/v1/txt2img"
        
        data = {
            "prompt": prompt,
            "negative_prompt": "low quality, blurry, nsfw",
            "width": width,
            "height": height,
            "steps": 20,
            "cfg_scale": 7,
        }
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            
            def do_request():
                with urllib.request.urlopen(req, timeout=120) as response:
                    return json.loads(response.read().decode("utf-8"))
            
            result = await asyncio.to_thread(do_request)
            
            if "images" in result and len(result["images"]) > 0:
                return True, result["images"][0]
            
            return False, "API 返回数据格式错误"
            
        except Exception as e:
            return False, str(e)

    async def generate_scene_image(
        self,
        session: "TRPGSession",
        context: str = "",
    ) -> Tuple[bool, str]:
        """
        生成场景图片的完整流程
        
        Returns:
            (成功, base64图片数据或错误信息)
        """
        if not self.is_enabled():
            return False, "图片生成功能未启用"
        
        # 生成提示词
        success, prompt, size_preset = await self.generate_scene_prompt(session, context)
        if not success:
            return False, f"生成提示词失败: {prompt}"
        
        # 生成图片
        return await self.generate_image(prompt, size_preset)
