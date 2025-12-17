"""
场景图片生成服务
使用 planner 模型生成提示词，调用生图 API 生成场景图片
支持 OpenAI、SD WebUI API、Gradio、NovelAI 等多种后端
"""

import json
import base64
import os
import urllib.request
import random
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
        # 建议不要把密钥写入仓库：优先读配置，其次读环境变量
        self.api_key = self.image_config.get("api_key", "") or os.getenv("MAIBOT_TRPG_DM_IMAGE_API_KEY", "")
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
        
        # SD API 专用配置
        self.sd_config = self.image_config.get("sd_api", {})
        
        # Gradio 专用配置
        self.gradio_config = self.image_config.get("gradio", {})
        
        # NovelAI 专用配置
        self.novelai_config = self.image_config.get("novelai", {})

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
            if not models:
                return False, "没有可用的 LLM 模型", "landscape"
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
            if not models:
                return False, "没有可用的 LLM 模型"
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
            api_type = self.api_type.lower()
            
            if api_type == "openai":
                return await self._generate_openai(prompt, width, height)
            elif api_type == "sd_api":
                return await self._generate_sd_api(prompt, width, height)
            elif api_type == "gradio":
                return await self._generate_gradio(prompt)
            elif api_type == "novelai":
                return await self._generate_novelai(prompt)
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
        """
        使用 SD API 生成图片
        
        API 参数说明（参考 API 文档）：
        - prompt (string, required): 提示词
        - negative_prompt (string, default ""): 负面提示词
        - width (integer, 64-2048, default 512): 图像宽度
        - height (integer, 64-2048, default 512): 图像高度
        - steps (integer, 1-50, default 20): 生成步数
        - cfg (float, 1-10, default 7.0): CFG 引导强度
        - model_index (integer, default 0): 模型索引
        - seed (integer, default -1): 随机种子，-1为随机
        """
        import asyncio
        
        # API 端点
        url = f"{self.base_url.rstrip('/')}/api/v1/generate_image"
        
        # 从配置获取 SD API 参数（使用简化的参数名）
        sd_width = self.sd_config.get("width", 0)
        sd_height = self.sd_config.get("height", 0)
        negative_prompt = self.sd_config.get("negative_prompt", "")
        steps = self.sd_config.get("steps", 20)
        cfg = self.sd_config.get("cfg", 7.0)
        model_index = self.sd_config.get("model_index", 0)
        seed = self.sd_config.get("seed", -1)
        timeout = self.sd_config.get("timeout", 120)
        
        # 使用配置的尺寸，如果为0则使用传入的尺寸（来自 size_preset）
        final_width = sd_width if sd_width > 0 else width
        final_height = sd_height if sd_height > 0 else height
        
        # 构建请求参数
        data = {
            "prompt": prompt,
        }
        
        # 添加可选参数
        if negative_prompt:
            data["negative_prompt"] = negative_prompt
        data["width"] = final_width
        data["height"] = final_height
        data["steps"] = steps
        data["cfg"] = cfg
        data["model_index"] = model_index
        data["seed"] = seed
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        logger.info(f"[ImageGenerator] SD API 请求: {final_width}x{final_height}, steps={steps}, cfg={cfg}, model_index={model_index}")
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            
            def do_request():
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    response_body = response.read().decode("utf-8")
                    if 200 <= response.status < 300:
                        return json.loads(response_body)
                    else:
                        raise Exception(f"HTTP {response.status}")
            
            result = await asyncio.to_thread(do_request)
            
            # 解析响应，支持多种返回格式
            image_data = None
            
            if "image" in result:
                image_data = result["image"]
            elif "url" in result:
                image_data = result["url"]
            elif "images" in result and result["images"]:
                first_img = result["images"][0]
                if isinstance(first_img, str):
                    image_data = first_img
                elif isinstance(first_img, dict):
                    image_data = first_img.get("url") or first_img.get("image") or first_img.get("base64")
            elif "data" in result:
                data_obj = result["data"]
                if isinstance(data_obj, dict):
                    image_data = data_obj.get("image") or data_obj.get("url") or data_obj.get("image_url")
                elif isinstance(data_obj, str):
                    image_data = data_obj
            
            if image_data:
                logger.info(f"[ImageGenerator] SD API 生成成功")
                return True, image_data
            
            # 如果响应本身是 base64
            if isinstance(result, str) and result.startswith(("iVBORw", "/9j/", "UklGR", "R0lGOD")):
                return True, result
            
            return False, f"API 返回数据格式错误: {str(result)[:200]}"
            
        except urllib.error.URLError as e:
            logger.error(f"[ImageGenerator] SD API 连接失败: {e}")
            return False, f"连接 SD API 失败: {e}"
        except Exception as e:
            logger.error(f"[ImageGenerator] SD API 请求失败: {e}")
            return False, str(e)

    async def _generate_gradio(self, prompt: str) -> Tuple[bool, str]:
        """
        使用 Gradio API 生成图片（如 HuggingFace Space）
        
        Gradio API 使用两步请求：
        1. POST 请求获取 event_id
        2. GET 请求轮询结果
        """
        import asyncio
        import time as time_module
        
        # 从配置获取 Gradio 参数
        resolution = self.gradio_config.get("resolution", "1024x1024 ( 1:1 )")
        steps = self.gradio_config.get("steps", 8)
        shift = self.gradio_config.get("shift", 3)
        timeout = self.gradio_config.get("timeout", 120)
        
        # 第一步：POST 请求获取 event_id
        endpoint = f"{self.base_url.rstrip('/')}/gradio_api/call/generate"
        
        payload = {
            "data": [
                prompt,           # [0] prompt
                resolution,       # [1] resolution
                42,              # [2] seed (固定值，因为会使用random_seed=true)
                steps,           # [3] steps
                shift,           # [4] shift
                True,            # [5] random_seed
                []               # [6] gallery_images
            ]
        }
        
        headers = {"Content-Type": "application/json"}
        
        logger.info(f"[ImageGenerator] Gradio API 请求: resolution={resolution}, steps={steps}")
        
        try:
            def do_post():
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            
            result = await asyncio.to_thread(do_post)
            event_id = result.get("event_id")
            
            if not event_id:
                return False, "未获取到 event_id"
            
            logger.info(f"[ImageGenerator] Gradio 获取到 event_id: {event_id}")
            
            # 第二步：GET 请求轮询结果
            result_endpoint = f"{self.base_url.rstrip('/')}/gradio_api/call/generate/{event_id}"
            start_time = time_module.time()
            
            def do_poll():
                req = urllib.request.Request(result_endpoint, method="GET")
                with urllib.request.urlopen(req, timeout=30) as response:
                    return response.read().decode("utf-8")
            
            while time_module.time() - start_time < timeout:
                try:
                    result_body = await asyncio.to_thread(do_poll)
                    
                    # 解析 SSE 格式的响应
                    for line in result_body.split('\n'):
                        if line.startswith('data: '):
                            data_str = line[6:]
                            try:
                                result_data = json.loads(data_str)
                                
                                # 提取图片URL
                                if isinstance(result_data, list) and len(result_data) > 0:
                                    gallery = result_data[0]
                                    if isinstance(gallery, list) and len(gallery) > 0:
                                        first_image = gallery[0]
                                        if isinstance(first_image, dict):
                                            image_data = first_image.get("image", {})
                                            image_url = image_data.get("url")
                                            
                                            if image_url:
                                                logger.info(f"[ImageGenerator] Gradio 生成成功")
                                                return True, image_url
                            except json.JSONDecodeError:
                                continue
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.debug(f"[ImageGenerator] Gradio 轮询中: {e}")
                    await asyncio.sleep(2)
            
            return False, f"轮询超时（{timeout}秒）"
            
        except Exception as e:
            logger.error(f"[ImageGenerator] Gradio API 请求失败: {e}")
            return False, str(e)

    async def _generate_novelai(self, prompt: str) -> Tuple[bool, str]:
        """
        使用 NovelAI 官方 API 生成图片
        
        NovelAI API 返回 zip 文件，需要解压获取图片
        """
        import asyncio
        import zipfile
        from io import BytesIO
        
        # 从配置获取 NovelAI 参数
        model = self.novelai_config.get("model", "nai-diffusion-4-5-full")
        width = self.novelai_config.get("width", 832)
        height = self.novelai_config.get("height", 1216)
        steps = self.novelai_config.get("steps", 28)
        scale = self.novelai_config.get("scale", 5.0)
        sampler = self.novelai_config.get("sampler", "k_euler")
        negative_prompt = self.novelai_config.get("negative_prompt", "")
        seed = self.novelai_config.get("seed", -1)
        timeout = self.novelai_config.get("timeout", 120)
        
        # 如果 seed 为 -1，生成随机种子
        if seed == -1:
            seed = random.randint(0, 2**32 - 1)
        
        # NovelAI API 端点
        endpoint = "https://image.novelai.net/ai/generate-image"
        
        # 构建请求体
        payload = {
            "input": prompt,
            "model": model,
            "action": "generate",
            "parameters": {
                "width": width,
                "height": height,
                "scale": scale,
                "sampler": sampler,
                "steps": steps,
                "seed": seed,
                "n_samples": 1,
                "negative_prompt": negative_prompt,
                "noise_schedule": "karras",
                "qualityToggle": True,
                "ucPreset": 0,
            }
        }
        
        # 根据模型调整参数
        if "nai-diffusion-4" in model:
            payload["parameters"]["cfg_rescale"] = 0
            payload["parameters"]["noise_schedule"] = "karras"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/zip, image/*",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        logger.info(f"[ImageGenerator] NovelAI 请求: model={model}, {width}x{height}, steps={steps}")
        
        try:
            def do_request():
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read(), response.headers.get("Content-Type", "")
            
            response_data, content_type = await asyncio.to_thread(do_request)
            
            # NovelAI 返回 zip 文件，需要解压
            if "zip" in content_type or response_data[:4] == b'PK\x03\x04':
                try:
                    with zipfile.ZipFile(BytesIO(response_data)) as zf:
                        file_list = zf.namelist()
                        if file_list:
                            image_bytes = zf.read(file_list[0])
                            base64_encoded = base64.b64encode(image_bytes).decode("utf-8")
                            logger.info(f"[ImageGenerator] NovelAI 生成成功，图片大小: {len(image_bytes)} bytes")
                            return True, base64_encoded
                        else:
                            return False, "NovelAI 返回的 zip 文件为空"
                except zipfile.BadZipFile:
                    return False, "NovelAI 返回的不是有效的 zip 文件"
            
            # 如果直接返回图片
            elif content_type.startswith("image/") or response_data[:8].startswith(b'\x89PNG') or response_data[:2] == b'\xff\xd8':
                base64_encoded = base64.b64encode(response_data).decode("utf-8")
                logger.info(f"[ImageGenerator] NovelAI 生成成功，图片大小: {len(response_data)} bytes")
                return True, base64_encoded
            
            else:
                try:
                    error_text = response_data.decode("utf-8")[:500]
                    return False, f"NovelAI 返回未知格式: {error_text}"
                except UnicodeDecodeError:
                    return False, f"NovelAI 返回未知格式 (Content-Type: {content_type})"
                    
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")[:300]
            except Exception:
                pass
            logger.error(f"[ImageGenerator] NovelAI HTTP 错误: {e.code} - {error_body}")
            return False, f"NovelAI 请求失败 (HTTP {e.code}): {error_body}"
        except Exception as e:
            logger.error(f"[ImageGenerator] NovelAI 请求失败: {e}")
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
