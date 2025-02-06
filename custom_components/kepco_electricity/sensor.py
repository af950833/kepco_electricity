import aiohttp
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

def calculate_billing_period(meter_reading_day: int, offset: int):
    """검침일을 기준으로 start_date와 end_date 계산"""

    today = datetime.today()
    
    # 이번 달 첫 날과 마지막 날
    first_day_this_month = today.replace(day=1)
    
    # 이번 달 검침일
    try:
        this_month_meter_date = today.replace(day=meter_reading_day)
    except ValueError:
        # 이번 달에 해당 날짜가 없는 경우 (예: 2월 30일 등)
        last_day_this_month = (first_day_this_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        this_month_meter_date = today.replace(day=min(meter_reading_day, last_day_this_month.day))

    # 검침일이 오늘보다 미래라면 (이번 달 검침일 전이라면)
    if today < this_month_meter_date:
        # 전달 검침일 계산
        last_day_last_month = first_day_this_month - timedelta(days=1)  # 전달 말일
        start_date = last_day_last_month.replace(day=min(meter_reading_day,last_day_last_month.day)) + timedelta(days=offset)
        end_date = this_month_meter_date - timedelta(days=1) + timedelta(days=offset) # 이번 달 검침일 하루 전
    else:
        # 다음 달 검침일 계산
        first_day_next_month = (first_day_this_month + timedelta(days=32)).replace(day=1)
        try:
            next_month_meter_date = first_day_next_month.replace(day=meter_reading_day)
        except ValueError:
            # 다음 달에 해당 날짜가 없을 경우 (예: 2월 30일)
            last_day_next_month = (first_day_next_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            next_month_meter_date = last_day_next_month.replace(day=min(meter_reading_day, last_day_next_month.day))

        start_date = this_month_meter_date + timedelta(days=offset) # 이번 달 검침일 + offset
        end_date = next_month_meter_date - timedelta(days=1) + timedelta(days=offset)  # 다음 달 검침일 하루 전 + offset

    return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")

async def async_setup_entry(hass, config_entry, async_add_entities):
    """센서 엔티티 설정"""
    async_add_entities([KepcoElectricitySensor(config_entry)])

class KepcoElectricitySensor(SensorEntity, RestoreEntity):
    """한국전력 전기요금 계산 센서"""

    _attr_icon = "mdi:flash"
    _attr_native_unit_of_measurement = "원"

    def __init__(self, config_entry):
        self._config_entry = config_entry
        self._attr_name = config_entry.options.get("sensor_name", "Kepco Bill")  # 사용자가 입력한 센서 이름 적용
        self._attr_unique_id = config_entry.entry_id
        self._attributes = {}
        self._last_integer_usage = None  # 마지막 정수 값 저장

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_added_to_hass(self):
        """HA 재시작 시 마지막 상태 복원 및 개별 업데이트 주기 적용"""
        last_state = await self.async_get_last_state()
    
        if last_state:
            # ✅ 이전 상태가 비정상적인 경우, 복원하지 않고 업데이트 트리거
            if last_state.state in [None, "unknown", "unavailable"]:
                _LOGGER.warning("이전 상태가 비정상적임: %s → 상태 및 속성 복원 안함", last_state.state)
                self._attr_native_value = None  # 상태를 직접 설정하지 않음
                self._attributes = {}  # 속성도 초기화 (업데이트를 강제 실행하기 위해)
                self._last_integer_usage = None
                await self.async_update()  # ✅ 강제 업데이트 실행
            else:
                # ✅ 정상적인 경우만 상태 & 속성 복원
                self._attr_native_value = last_state.state
                self._attributes = dict(last_state.attributes)
                self._last_integer_usage = self._attributes.get("월사용량", None)
    
                _LOGGER.debug("정상 상태 복원됨: %s, 월사용량: %s", self._attr_native_value, self._last_integer_usage)
    
                # ✅ 정상 복원된 경우, GUI에 즉시 반영
                self.async_write_ha_state()
            
    async def async_update(self, _=None):
        """API 호출 및 상태 업데이트"""
        try:
            options = self._config_entry.options
            
            reading_day = options.get("meter_reading_day", 25)
            offset = options.get("meter_reading_day_offset", 0)
            usage_entity = options.get("usage_entity")

            # 사용량 조회
            state = self.hass.states.get(usage_entity)
            usage = int(float(state.state)) if state else 0
            
            # 정수 부분이 변경되었는지 확인
            if self._last_integer_usage is not None and self._last_integer_usage == usage:
                _LOGGER.debug("정수 값 변경 없음, 업데이트 건너뜀.")
                return
                
            self._last_integer_usage = usage

            # 날짜 계산
            start_date, end_date = calculate_billing_period(int(reading_day),int(offset))

            # API 요청 데이터
            payload = {
                "dma_reqParam": {
                    "chrgStYmd": start_date,
                    "chrgEndYmd": end_date,
                    "cntrClasCd": "100",
                    "lhvClcd": options.get("lhv_clcd", "1"),
                    "sekchrCd": "0",
                    "chrgAplyPwr": "3",
                    "dwelClcd": options.get("dwel_clcd", "1"),
                    "noho": "1",
                    "tpVarMrYn": "N",
                    "oneaPf": "0",
                    "cdnphPf": "0",
                    "nsla": "0",
                    "stliWattPwr": "0",
                    "whmeLloadUski": "0",
                    "whmeMloadUski": str(usage),
                    "whmeMaxLoadUski": "0",
                    "houseList": [
                        {
                            "housSeqno": "1",
                            "wlfrDcClcd1": options.get("wlfr_dc_clcd1", ""),
                            "wlfrDcClcd2": options.get("wlfr_dc_clcd2", ""),
                            "rowStatus": "R"
                        }
                    ]
                }
            }

            # API 호출
            response = await self._async_fetch_data(payload)
            _LOGGER.debug("API 호출")
            if not response or "dma_resObj" not in response:
                return

            res_obj = response["dma_resObj"]
                
            contract_types = {"1": "주택용(저압)", "2": "주택용(고압)"}
            dwelling_types = {"1": "주거용", "2": "비주거용"}
            welfare_discounts = {
                "01": "장애인",
                "02": "국가유공자",
                "03": "독립유공자",
                "04": "기초생활(생계/의료)",
                "05": "사회복지시설",
                "07": "차상위계층",
                "09": "기초생활(주거/교육)",
                "": "해당 없음"
            }
            family_discounts = {
                "21": "5인 이상 가구",
                "22": "3자녀 이상 가구",
                "23": "생명유지장치 사용자",
                "24": "출산가구",
                "": "해당 없음"
            }
                
            contract_type = contract_types.get(options.get("lhv_clcd", "1"), "주택용(저압)")
            dwelling_type = dwelling_types.get(options.get("dwel_clcd", "1"), "주거용")
            welfare_discount = welfare_discounts.get(options.get("wlfr_dc_clcd1", ""), "해당 없음")
            family_discount = family_discounts.get(options.get("wlfr_dc_clcd2", ""), "해당 없음")
                
            self._attr_native_value = res_obj.get("costTotCharge", 0)
            self._attributes = {
                "계약종별 선택": contract_type,
                "주거구분 선택": dwelling_type,
                "복지할인 선택": welfare_discount,
                "대가족요금/생명유지장치 선택": family_discount,
                "검침 시작일": start_date,
                "검침 종료일": end_date,
                "월사용량": self._last_integer_usage,
                "기본 요금": res_obj.get("costBasic", 0),
                "전력량 요금": res_obj.get("costUse", 0),
                "연료비조정 요금": res_obj.get("costFuel", 0),
                "기후환경 요금": res_obj.get("costClim", 0),
                "전기 요금": res_obj.get("costElecUse", 0),
                "부가가치세": res_obj.get("costAddTax", 0),
                "전력산업기반 기금": res_obj.get("costElecFund", 0),
                "복지 할인": res_obj.get("costDisWelf", 0),
                "다자녀 할인": res_obj.get("costDisMchild", 0),
                "출산가구 할인": res_obj.get("costDisBirth", 0),
                "대가족 할인": res_obj.get("costDisLarge", 0),
                "산업용 할인": res_obj.get("costDisInd", 0),
                "교육용 할인": res_obj.get("costDisIncEdu", 0),
                "저소득층 할인": res_obj.get("costDisIncLiv", 0),
                "주거복지 할인": res_obj.get("costDisLiv", 0),
                "사회적배려계층 할인": res_obj.get("costDisSuplife", 0),
                "장애인 할인": res_obj.get("costDisDef", 0),
                "국가유공자 할인": res_obj.get("costDisNat", 0),
                "요금동결 할인": res_obj.get("calcostList")[0].get("housecalList")[0].get("disVlnCost",0),
                "200kWh 이하 할인": res_obj.get("calcostList")[0].get("costUnder200"),
                "총 청구금액": res_obj.get("costTotCharge", 0)
            }

        except Exception as e:
            _LOGGER.error("요금 계산 오류: %s", e, exc_info=True)

    async def _async_fetch_data(self, payload):
        """API 호출 함수"""
        try:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://online.kepco.co.kr/pr/calcul/calcul",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        return None
                    return await response.json()
        except Exception as e:
            _LOGGER.error("API 호출 실패: %s", e)
            return None
