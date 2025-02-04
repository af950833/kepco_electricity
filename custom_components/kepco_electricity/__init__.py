"""KEPCO 전기요금 계산 통합구성요소"""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """통합구성요소 초기 설정"""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Config Entry 설정"""
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # 센서 플랫폼 설정
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    
    # 옵션 업데이트 리스너 등록
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Config Entry 언로드"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """옵션 변경 시 업데이트"""
    await hass.config_entries.async_reload(entry.entry_id)
    _LOGGER.debug("설정 변경 감지: %s", entry.options)
