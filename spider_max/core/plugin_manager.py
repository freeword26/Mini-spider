"""Spider Max 核心模块：插件管理器"""
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class PluginStatus(Enum):
    PENDING = "pending"
    INSTALLED = "installed"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str = ""
    author: str = ""
    requires: List[str] = field(default_factory=list)
    entrypoint: str = ""
    enabled: bool = True


class Plugin:
    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest
        self.status = PluginStatus.PENDING
        self._handlers: Dict[str, Callable] = {}

    def on_install(self): self.status = PluginStatus.INSTALLED
    def on_start(self): self.status = PluginStatus.RUNNING
    def on_stop(self): self.status = PluginStatus.STOPPED
    def on_uninstall(self): self.status = PluginStatus.PENDING

    def register_handler(self, event: str, handler: Callable):
        self._handlers[event] = handler

    def handle_event(self, event: str, data: Any = None) -> Any:
        handler = self._handlers.get(event)
        if handler:
            return handler(data)
        return None


class PluginManager:
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    def install(self, manifest: PluginManifest) -> Plugin:
        plugin = Plugin(manifest)
        plugin.on_install()
        self._plugins[manifest.name] = plugin
        return plugin

    def start(self, name: str) -> bool:
        plugin = self._plugins.get(name)
        if plugin and plugin.status in (PluginStatus.INSTALLED, PluginStatus.STOPPED):
            plugin.on_start()
            return True
        return False

    def stop(self, name: str) -> bool:
        plugin = self._plugins.get(name)
        if plugin and plugin.status == PluginStatus.RUNNING:
            plugin.on_stop()
            return True
        return False

    def uninstall(self, name: str) -> bool:
        if name in self._plugins:
            self._plugins[name].on_uninstall()
            del self._plugins[name]
            return True
        return False

    def get(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    def list_installed(self) -> List[Plugin]:
        return list(self._plugins.values())

    def list_running(self) -> List[Plugin]:
        return [p for p in self._plugins.values() if p.status == PluginStatus.RUNNING]

    def register_hook(self, hook_name: str, handler: Callable):
        self._hooks.setdefault(hook_name, []).append(handler)

    def trigger_hook(self, hook_name: str, data: Any = None) -> List[Any]:
        results = []
        for handler in self._hooks.get(hook_name, []):
            try:
                results.append(handler(data))
            except Exception as e:
                results.append(e)
        return results

    def scan_directory(self, path: str):
        import os, json
        if not os.path.isdir(path):
            return
        for entry in os.listdir(path):
            manifest_path = os.path.join(path, entry, "manifest.json")
            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path) as f:
                        data = json.load(f)
                    self.install(PluginManifest(**data))
                except Exception as e:
                    logging.warning(f"Failed to load plugin {entry}: {e}")
