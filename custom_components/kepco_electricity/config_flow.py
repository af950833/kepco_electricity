import logging
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol
from datetime import datetime, timedelta
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class KepcoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """GUI 설정 화면 처리"""
        errors = {}
        entities = [e.entity_id for e in self.hass.states.async_all() if e.entity_id.startswith("sensor.")]

        if user_input is not None:
            if user_input["usage_entity"] not in entities:
                errors["base"] = "invalid_entity"

            if not errors:
                # 할인 코드 변환
                user_input["wlfr_dc_clcd1"] = "" if user_input["wlfr_dc_clcd1"] == "none" else user_input["wlfr_dc_clcd1"]
                user_input["wlfr_dc_clcd2"] = "" if user_input["wlfr_dc_clcd2"] == "none" else user_input["wlfr_dc_clcd2"]

                user_input["sensor_name"] = user_input.get("sensor_name", "Kepco Bill")  # 센서 이름 저장

                return self.async_create_entry(
                    title=user_input["sensor_name"], 
                    data={}, 
                    options=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("sensor_name", default="Kepco Bill"): str,
                vol.Required("meter_reading_day", default=25): vol.All(vol.Coerce(int),vol.Range(min=1, max=31)
                ),
                vol.Required("usage_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        multiple=False
                    )
                ),
                vol.Required("lhv_clcd", default="1"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "1", "label": "주택용(저압)"},
                            {"value": "2", "label": "주택용(고압)"}
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Required("dwel_clcd", default="1"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "1", "label": "주거용"},
                            {"value": "2", "label": "비주거용"}
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Required("wlfr_dc_clcd1", default="none"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "none", "label": "해당없음"},
                            {"value": "01", "label": "장애인"},
                            {"value": "02", "label": "국가유공자"},
                            {"value": "03", "label": "독립유공자"},
                            {"value": "04", "label": "기초생활(생계/의료)"},
                            {"value": "05", "label": "사회복지시설"},
                            {"value": "07", "label": "차상위계층"},
                            {"value": "09", "label": "기초생활(주거/교육)"}
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Required("wlfr_dc_clcd2", default="none"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "none", "label": "해당없음"},
                            {"value": "21", "label": "5인 이상 가구"},
                            {"value": "22", "label": "3자녀 이상 가구"},
                            {"value": "23", "label": "생명유지장치 사용자"},
                            {"value": "24", "label": "출산가구"}
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                )
            }),
            errors=errors,
            description_placeholders={
                "example_date": self._calculate_dates(25)
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """옵션 플로우 연결"""
        return KepcoOptionsFlow(config_entry)
        
    def _calculate_dates(self, day: int) -> str:
        today = datetime.now()
        try:
            end_date = today.replace(day=day) - timedelta(days=1)
        except ValueError:
            end_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            end_date = end_date.replace(day=min(day, end_date.day))
        start_date = end_date - timedelta(days=30)
        return f"예시: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"



class KepcoOptionsFlow(config_entries.OptionsFlow):
    """설정 옵션 수정 화면"""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            user_input["wlfr_dc_clcd1"] = "" if user_input["wlfr_dc_clcd1"] == "none" else user_input["wlfr_dc_clcd1"]
            user_input["wlfr_dc_clcd2"] = "" if user_input["wlfr_dc_clcd2"] == "none" else user_input["wlfr_dc_clcd2"]
            return self.async_create_entry(
                title=user_input["sensor_name"],
                data=user_input
            )
            
        options = self.config_entry.options
        entities = [e.entity_id for e in self.hass.states.async_all() if e.entity_id.startswith("sensor.")]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("sensor_name", default=options.get("sensor_name", "한국전력 요금")): str,
                vol.Required("meter_reading_day", default=options.get("meter_reading_day", 25)): vol.All(vol.Coerce(int), vol.Range(min=1, max=31)),
                vol.Required("usage_entity", default=options.get("usage_entity")): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required("lhv_clcd", default=options.get("lhv_clcd", "1")): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "1", "label": "주택용(저압)"},
                            {"value": "2", "label": "주택용(고압)"}
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Required("dwel_clcd", default=options.get("dwel_clcd","1")): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "1", "label": "주거용"},
                            {"value": "2", "label": "비주거용"}
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Required("wlfr_dc_clcd1", default="none" if options.get("wlfr_dc_clcd1") == "" else options.get("wlfr_dc_clcd1")): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "none", "label": "해당없음"},
                            {"value": "01", "label": "장애인"},
                            {"value": "02", "label": "국가유공자"},
                            {"value": "03", "label": "독립유공자"},
                            {"value": "04", "label": "기초생활(생계/의료)"},
                            {"value": "05", "label": "사회복지시설"},
                            {"value": "07", "label": "차상위계층"},
                            {"value": "09", "label": "기초생활(주거/교육)"}
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Required("wlfr_dc_clcd2", default="none" if options.get("wlfr_dc_clcd2") == "" else options.get("wlfr_dc_clcd2")): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "none", "label": "해당없음"},
                            {"value": "21", "label": "5인 이상 가구"},
                            {"value": "22", "label": "3자녀 이상 가구"},
                            {"value": "23", "label": "생명유지장치 사용자"},
                            {"value": "24", "label": "출산가구"}
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                )
            })
        )
        
