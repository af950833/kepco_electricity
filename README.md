# Kepco Electricity
Home Assistant - 한전 전기요금계산기

![Kepco Logo](images/logo.png)

Home Assistant에서 한국ON 전기요금계산기의 요금을 센서로 사용하기 위해 만든 Custom Component 입니다.

## 1. 한전 On 계산기 사이트 링크
https://online.kepco.co.kr/PRM033D00

해당 사이트의 모든 종류의 계약을 지원하지는 않으며, 일반적인 주택용 고압/저압만을 지원합니다.


## 2. Home Assistant에 Kepco Electricity 설치

### HACS 또는 Manual 설치

1. HACS를 이용하거나 수동으로 **Kepco Electricity**을 설치합니다.
2. 설치 후 Home Assistant를 재부팅합니다.

![Kepco](images/kepco.png)

### 통합 구성 요소 추가

1. **설정 -> 기기 및 서비스 -> 통합구성요소 추가하기**에서 `KEPCO 전기요금`을 추가합니다.
2. 설정 항목을 입력합니다.
   - **센서 이름**: 원하는 센서 이름을 입력합니다.
   - **월사용 센서**: 월사용량 센서를 추가합니다.(sensor 도메인만 가능하며, 소숫점 자리는 무시하고 정수만 계산됩니다.)
   - **계약 종별**: 주택용 저압 / 주택용 고압
   - **주거 구분**: 주거용 / 비주거용
   - **복지 할인**: 장애인, 국가유공자 등등
   - **대가족/생명유지장치**: 5인 이상, 3자녀 이상 등등


## 3. 센서 업데이트 주기

한전 사이트에 접속해서 전기요금을 계산하고 결과를 받아 오는 방식이라 너무 빈번한 주기의 업데이트는 한전 서버에 무리를 줄 수 있습니다.
HA가 재시작하거나 월사용량의 정수(소숫점 숫자는 무시)가 변경되면 업데이트 되며, 그 외에는 한전 사이트를 호출하지 않습니다.

## Version History
2025/02/04 V1.0.1 초기 배포
2025/02/05 V1.0.5 API 호출 로직 개선, 속성에 월사용량 추가
           V1.0.6 통합구성요소 타이틀을 입력한 센서명으로 나타나게 수정
           
