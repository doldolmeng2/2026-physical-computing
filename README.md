# 2026-physical-computing

2026-2 피지컬컴퓨팅 PiCar 프로젝트 (Adeept PiCar-Pro V2 + Robot HAT V3.3)

미션 흐름: **QR(LEFT/RIGHT) 인식 → 직진 → 모니터 30cm 앞 정지선에서 정지 → 처음 방향 물체를 반대편 빈 칸으로 → 반대편 물체를 처음 방향 빈 칸으로**

---

## 1. 파일 구성

| 파일 | 내용 |
|---|---|
| `hw.py` | 모터·서보·초음파·카메라 설정값과 기본 함수 |
| `qr.py` | 웹캠 QR 인식 |
| `arm.py` | 공통 자세(`drive`, `qr`) 저장/이동, 팔을 천천히 움직이기(`move_to`) |
| `sequence.py` | 물체 옮기기: mode 별 위치 4곳 + lift + 집게 각도 저장, QR 방향에 맞는 순서로 실행 (4절) |
| `drive.py` | 직진하다가 정지선에서 정지 |
| `main.py` | 미션 순서대로 실행. 단계별 함수(`mission_qr`, `mission_drive`, `mission_arm`)로 나뉨 |
| `status.py` | 미션 진행 상태 (모드, QR 결과, 단계, 오류, 기록). OLED·웹이 같이 읽음 |
| `display.py` | OLED 에 배터리 전압 + 미션 상태 표시 |
| `poses.json` | 공통 자세 `drive`, `qr` (웹이나 `tests/test_arm.py` 로 Pi에서 만든다) |
| `modes.json` | mode1/mode2 위치·집게 각도 + 지금 쓰는 mode (웹에서 만든다) |
| `webui/` | 카메라·QR·초음파를 보면서 위치 저장 + 미션 디버깅 실행 웹 페이지 (4절, 5절) |
| `tests/` | 장치를 하나씩 확인하는 테스트 → [tests/README.md](tests/README.md) |

---

## 2. 작업 방법

### 실행 전 (매번)
Adeept 웹 컨트롤러(`Adeept_Robot.service`)가 부팅 때 자동 실행되어 **같은 모터 칩(PCA9685)과 웹캠을 쓰고 있다.** 우리 코드를 돌리기 전에 끈다.
```bash
sudo systemctl stop Adeept_Robot.service
```
웹 컨트롤러를 다시 쓰고 싶으면 `start`, 재부팅하면 다시 켜진다.

### 실행 (Pi)
```bash
cd ~/picar_mission
python3 tests/test_arm.py     # 테스트
python3 main.py               # 전체 미션
```

### 코드 주고받기 (GitHub)
- PC에서 고친 코드 → `git push` → Pi에서 `git pull`
- Pi에서 만든 `poses.json`, `modes.json` → Pi에서 `git add poses.json modes.json && git commit -m "..." && git push` → PC에서 `git pull`
- 한쪽에서 고친 걸 push 하기 전에 다른 쪽에서 같은 파일을 고치면 충돌이 나니, **작업 시작 전에 항상 `git pull`**

---

## 3. 설정값 (값의 의미와 찾는 법)

`None` 인 값은 아직 정하지 않은 값이다. 채우기 전에 그 기능을 실행하면 "TODO 값을 먼저 채우세요" 오류가 난다.

### hw.py
| 값 | 의미 | 현재 | 찾는 법 |
|---|---|---|---|
| `M1_DIR`, `M2_DIR` | 뒷바퀴 왼쪽(M1)/오른쪽(M2) 회전 방향. `1` 또는 `-1` | `1` | `test_motor.py` 에서 `f 30 1` → 뒤로 가는 바퀴는 부호를 바꾼다 |
| `STEER_CENTER` | 앞바퀴가 정면을 볼 때 조향 서보 각도 (0~180) | `90` | `test_motor.py` 에서 `sa 85`, `sa 95` … 로 바꿔가며 `f 30 2` 로 똑바로 가는 값 |
| `SERVO_STEER` ~ `SERVO_GRIP` | PCA9685 채널 번호 (0 조향, 1 팔 좌우, 2 팔 상하, 3 손목, 4 집게) | Adeept 기준 | `test_arm.py` 에서 채널별로 움직여 보고 실제 부위와 다르면 번호를 바꾼다 |
| `ULTRA_TRIG`, `ULTRA_ECHO` | 초음파 Trig/Echo GPIO 번호 (BCM) | `23`, `24` | Adeept 코드 값. 바꿀 일 없음 |
| `CAMERA_INDEX` | 웹캠. `None` 이면 USB 웹캠 자동 찾기 (USB 를 다시 꽂으면 `/dev/video0` → `video1` 처럼 번호가 바뀜) | `None` | 그래도 안 열리면 `ls -l /dev/v4l/by-id` 로 확인 후 번호나 경로(`'/dev/video1'`)를 적는다 |
| `CAMERA_SIZE` | 카메라 해상도 | `(640, 480)` | QR이 잘 안 읽히면 키워 볼 수 있음 (느려짐) |

### arm.py / sequence.py
| 값 | 의미 | 현재 | 찾는 법 |
|---|---|---|---|
| `arm.POSE_NAMES` | mode 와 상관없는 공통 자세 | `drive`, `qr` | 4절 |
| `arm.move_to(step, delay)` | 한 번에 움직이는 각도(°)와 간격(초). 작을수록 부드럽고 느림 | `2`, `0.02` | 팔이 흔들리거나 물체를 넘어뜨리면 줄인다 |
| `sequence.MODES` | 위치 세트 이름 | `mode1`, `mode2` | 세트를 더 만들려면 이름 추가 |
| `sequence.ORDER` | QR 방향별 위치 순서 | LEFT: `left_pick → right_place → right_pick → left_place` / RIGHT: `right_pick → left_place → left_pick → right_place` | |
| 집게 열림/닫힘 | `modes.json` 의 `grip_open`, `grip_close` | 웹에서 저장 | 닫힘은 물체를 **놓치지 않는 가장 약한 값**. 너무 세게 닫으면 서보가 "지잉" 하며 버틴다 (전류 많이 씀) |

### drive.py

초음파 **센서 전면 → 노트북/모니터 전면** 거리가 30cm인 위치에 정지한다.
빨간색을 카메라로 판별하지 않으며, 정지선 중심이
모니터에서 30cm인 경기장 배치를 전제로 한다.

| 값 | 초기값 | 의미 |
|---|---|---|
| `STOP_DISTANCE_CM` | `30.0` | 최종 목표 거리 (차체/집게가 아닌 센서 기준) |
| `DISTANCE_OFFSET_CM` | `0.0` | 자로 잰 실제 거리 - 센서 표시값 |
| `BRAKE_ADVANCE_CM` | `0.0` | 정지 명령 후 밀리는 거리만큼 일찍 제동 |
| `DRIVE_SPEED / SLOW_SPEED / CREEP_SPEED` | `30 / 22 / 18` | 전진 PWM %. 실차 보정 전 초기값 |
| `SLOW_DISTANCE_CM / CREEP_DISTANCE_CM` | `50 / 38` | 감속 시작 거리 (cm) |
| `STOP_TOLERANCE_CM` | `1.0` | 최종 측정값 허용 오차 (폭 2cm 빨간 선 기준) |
| `MAX_DRIVE_SECONDS` | `20.0` | 최대 접근 시간. 초과 시 정지하고 실패 |

`python3 drive.py`로 **주행만** 시험한다. QR을 기다리지 않고 출발하므로,
미션 전체에서는 기존 `python3 main.py`를 사용한다.

```bash
sudo systemctl stop Adeept_Robot.service
python3 tests/test_ultrasonic.py  # Ctrl+C로 종료한 뒤 다음 명령 실행
python3 tests/test_motor.py      # 방향과 조향 확인 후 q로 종료
python3 drive.py
```

1. 센서가 모니터 정면을 향하도록 두고, 센서 전면을 빨간 선 중심(실측 30cm)에 맞춘다.
   센서가 29.2cm를 표시하면 `DISTANCE_OFFSET_CM = 0.8`로 보정한다.
2. 바퀴를 띄워 전진 방향을 확인하고 `hw.py`의 `M1_DIR`, `M2_DIR`를 맞춘다.
   바닥에서 `STEER_CENTER`로 직진을 맞춘다. 초음파 한 개로는 주행 방향을 알 수 없다.
3. 정지선보다 뒤에서 `python3 drive.py`를 실행한다. 50cm, 38cm에서 감속한다.
   근접 속도 18%에서 바퀴가 안 돌면 `CREEP_SPEED`를 올려 실제로 움직이는 최소값을 찾는다.
4. 멈춘 후 **자로 센서 전면 거리**를 재고 출력값과 비교한다.
   예를 들어 29.4cm에서 멈췄다면 `BRAKE_ADVANCE_CM`을 약 0.6cm 늘려 다시 시험한다.
   배터리, 바닥, 팔 자세가 달라지면 반복 보정한다. 정확히 30.0cm 정지는 실차 검증이 필요하다.

주행 중에는 새 에코 하나마다 판단한다. 목표 이하 값이 오면 먼저 정지한 뒤,
0.3초 안정화 후 새 측정 5개의 중앙값으로 최종 위치를 확인한다.
허용 범위를 벗어나거나 에코 미수신/비정상 값/시간 초과가 발생하면 예외를 내어
`main.py`가 팔 미션을 진행하지 않게 한다. 정지 후 자동 재전진/후진은 하지 않는다.
Ctrl+C와 예외에도 모터 정지 명령을 보낸다. 최종 측정 오차 판정만으로 실제 선 위 정지를 보장할 수는 없다.

`hw.py`는 gpiozero 2.x `DistanceSensor._read()`를 확장해 새 측정과 미수신을 구분한다.
기본 이력 필터로 생기는 지연과 에코 미수신 때 과거 값을 재사용하는 문제를 피하기 위한 것이다.
라이브러리 버전 변경 시 `tests/test_ultrasonic.py`로 실제 측정과 미수신 동작을 확인한다.
참고: [gpiozero DistanceSensor 소스](https://github.com/gpiozero/gpiozero/blob/v2.0.1/gpiozero/input_devices.py).

PC에서 하드웨어 없이 주행 로직 검사:
```bash
python3 -m unittest discover -s tests -p '*_logic.py'
```

### qr.py
| 값 | 의미 | 찾는 법 |
|---|---|---|
| `wanted=('LEFT', 'RIGHT')` | 출발 QR로 인정하는 글자 | `test_camera.py` 로 실제 QR을 비춰 터미널에 찍히는 글자 확인 |

---

## 4. 팔 위치 저장하는 법

### 저장할 것
**공통 자세** (`poses.json`, mode 상관없음)
| 이름 | 언제 쓰나 |
|---|---|
| `drive` | 주행할 때 접어 둔 자세 (모니터에 닿지 않게) |
| `qr` | 출발선에서 모니터 QR이 웹캠에 잘 보이는 자세 |

**물체 옮기기 위치** (`modes.json`, mode1 / mode2 각각 한 세트)
| 이름 | 무엇 | 저장되는 값 |
|---|---|---|
| `left_pick` | 왼쪽 상자 물체를 집는 위치 | 팔 좌우·상하·손목 |
| `right_place` | 오른쪽 상자 빈 칸에 놓는 위치 | 〃 |
| `right_pick` | 오른쪽 상자 물체를 집는 위치 | 〃 |
| `left_place` | 왼쪽 상자 빈 칸에 놓는 위치 | 〃 |
| `lift` | 위치 사이를 옮겨 갈 때 거치는 들어 올린 자세 (상자·물체에 걸리지 않게) | 〃 |
| `grip_open` | 집게 열림 | 집게 각도 |
| `grip_close` | 집게 닫힘 (물체를 잡은 상태) | 집게 각도 |

위치는 **로봇을 실제 정지선 위치에 두고** 저장한다 (정지 후에는 바퀴를 못 움직임).
mode2 는 다른 배치·다른 방법을 시험해 볼 두 번째 세트다. 웹에서 고른 mode 가 저장과 실행 모두에 쓰인다.

### 실행 순서 (`sequence.py`)
```
출발 QR LEFT  : left_pick  → right_place → right_pick → left_place
출발 QR RIGHT : right_pick → left_place  → left_pick  → right_place

집기(pick)  : lift → 집게 열기 → 위치 → 집게 닫기 → lift
놓기(place) : lift → 위치 → 집게 열기 → lift
끝나면 drive 자세
```
고른 mode 에 하나라도 저장 안 된 값이 있으면 시작하지 않고 `mode1 에 저장 안 된 위치: ...` 오류를 낸다.

### 방법 A: 웹 페이지 (추천)
1. Pi에서 실행
   ```bash
   sudo systemctl stop Adeept_Robot.service
   cd ~/picar_mission && git pull
   python3 webui/app.py
   ```
2. PC 브라우저에서 **`http://192.168.50.2:5002`** 접속. 시작하면 팔·집게가 90°, 조향이 가운데로 간다.
3. **서보 각도** 카드로 팔을 맞춘다
   - `1° 2° 5° 10°` 로 한 번에 움직일 각도를 고른다
   - `−` / `+` 버튼: 한 번 누르면 한 칸, **누르고 있으면 계속** 움직인다
   - 슬라이더: 끌어서 놓으면 그 각도로 천천히 이동
4. **물체 옮기기 위치** 카드
   - **사용할 mode** 에서 `mode1` / `mode2` 를 고른다 (실행에도 이 mode 가 쓰임)
   - 위치(`left_pick` …, `lift`) 행의 **저장** → 지금 팔 좌우·상하·손목 각도 저장
   - 집게 행(`grip_open`, `grip_close`)의 **집게 각도 저장** → 지금 집게 각도 저장
   - **이동** 으로 다시 불러와 같은 곳으로 오는지 확인. ✓ 저장됨, ○ 아직
   - 위쪽 LEFT/RIGHT 순서 줄에서 초록 = 저장됨, 주황 = 아직
5. **공통 자세** 카드에서 `drive`, `qr` 저장
6. **미션 디버깅** 카드의 **LEFT 강제 → 팔만** / **RIGHT 강제 → 팔만** 으로 순서대로 움직이는지 확인
7. Ctrl+C 로 끄고 `poses.json`, `modes.json` 을 push

이 페이지가 켜져 있는 동안은 카메라·초음파·서보를 쓰는 다른 프로그램(`tests/`, `main.py`)을 같이 실행하지 않는다.

`modes.json` 은 이런 모양이다. 각도를 직접 고쳐도 된다.
```json
{
  "active": "mode1",
  "mode1": {
    "left_pick": {"1": 120, "2": 60, "3": 70},
    "lift": {"1": 90, "2": 120, "3": 100},
    "grip_open": 40,
    "grip_close": 120
  },
  "mode2": {}
}
```

### 방법 B: 터미널 (`tests/test_arm.py`, 공통 자세만)
`test_arm.py` 는 `poses.json`(공통 자세)만 저장한다. mode 위치는 웹에서 저장한다.
1. Pi에서 웹 컨트롤러를 끄고 테스트 실행
   ```bash
   sudo systemctl stop Adeept_Robot.service
   cd ~/picar_mission && git pull
   python3 tests/test_arm.py
   ```
2. 시작하면 팔·집게가 90°로 간다. 채널별로 조금씩 움직인다
   ```
   > 1 +10        # 팔 좌우를 10° 더
   > 2 -5         # 팔 상하를 5° 덜
   > 3 120        # 손목을 120°로
   > show         # 현재 각도 보기
   ```
3. `save drive`, `go drive`, `list`, `q`

---

## 5. 미션 디버깅 (웹 페이지 + OLED)

### 웹 페이지 "미션 디버깅" 카드
`python3 webui/app.py` → `http://192.168.50.2:5002`

| 버튼 | 하는 일 | 로봇 위치 |
|---|---|---|
| **main 처음부터** | `main.py` 와 같은 순서: `qr` 자세 → QR 대기 → `drive` 자세 → 주행·정지 → 물체 2개 옮기기 | 출발선 |
| **LEFT 강제 → 팔만** | QR 을 LEFT 로 정하고 물체 옮기기만 (`left_pick → right_place → right_pick → left_place`) | 정지선 |
| **RIGHT 강제 → 팔만** | QR 을 RIGHT 로 정하고 물체 옮기기만 (`right_pick → left_place → left_pick → right_place`) | 정지선 |
| **정지** | 바퀴 즉시 정지 + 다음 단계로 넘어가지 않음 (지금 움직이는 팔 자세 하나는 끝까지 감) | |

- 위치는 **물체 옮기기 위치** 카드에서 고른 mode 를 쓴다. `python3 main.py` 도 마지막으로 웹에서 고른 mode(`modes.json` 의 `active`)를 쓴다
- 아래에 **모드 / QR / 단계 / 세부** 와 진행 기록이 실시간으로 나온다. 오류가 나면 빨간 글씨로 원인이 나온다 (예: `mode1 에 저장 안 된 위치: lift`)
- 미션이 도는 동안 서보 버튼·위치 저장·mode 바꾸기는 막힌다
- "main 처음부터" 는 **버튼을 누른 뒤에** 새로 인식된 QR 만 받는다 (전에 보던 QR 로 바로 출발하지 않음)
- QR 이 `LEFT*` 처럼 `*` 이 붙으면 강제로 정한 값

### OLED 화면
`main.py` 나 `webui/app.py` 를 실행하면 OLED 에 0.5초마다 표시된다 (영문만 나옴).
```
BAT 7.85V  14:03:21     ← 배터리 전압, 6.3V 미만이면 LOW
MODE FULL m1 RUN        ← IDLE / FULL(main) / ARM(팔만) + 쓰는 mode, RUN = 실행 중
QR   LEFT               ← 인식 결과 (LEFT* = 강제)
STEP 2/3 DRIVE          ← 단계 (1/3 QR, 2/3 DRIVE, 2/3 STOP, ARM 1/4 ~ ARM 4/4, END, DONE / ERROR)
stop 30.2cm             ← 세부 (위치 이름 + open/close/lift, 정지 거리 등)
ERR ...                 ← 오류가 있을 때만
```
단계 이름은 `main.py` 의 `status.step('이름', '세부')` 에서 정한다. 새 단계를 추가하면 여기에도 영문으로 적는다.

### 단계를 따로 실행 (Python)
```python
>>> import main, status
>>> main.run_arm_only('left')            # = 웹의 LEFT 강제 → 팔만 (웹에서 고른 mode)
>>> main.run_arm_only('right', 'mode2')  # mode 를 직접 지정
>>> status.snapshot()                    # 마지막 상태·기록
>>> main.mission_drive()                 # 주행 단계 함수만 (drive 자세 → 정지선까지)
```

---

## 6. 수동 디버깅

### Python에서 하나씩 실행해 보기
테스트 스크립트 없이 함수를 직접 불러 볼 수 있다.
```bash
cd ~/picar_mission
python3
```
```python
>>> import hw, arm, time
>>> hw.steer(0)                                   # 조향 가운데
>>> hw.drive(30); time.sleep(1); hw.stop()        # 1초 앞으로
>>> hw.distance_median()                          # 초음파 (cm)
>>> hw.set_servo(4, 60)                           # 집게 60°
>>> hw.get_servo(4)                               # 마지막으로 보낸 각도
>>> arm.load_poses()                              # 저장된 자세
>>> arm.go_pose('drive')
>>> hw.cleanup(); exit()
```

### 미션을 나눠서 실행
`main.py` 전체 대신 한 부분만:
```python
>>> import hw, qr, drive, sequence
>>> cap = hw.open_camera(); print(qr.wait_for_qr(cap, timeout=10)); cap.release()   # 미션 1
>>> drive.drive_to_stop_line()                    # 미션 2
>>> sequence.missing('mode1')                     # 저장 안 된 위치 확인
>>> sequence.go('mode1', 'left_pick')             # 위치 하나로 이동
>>> sequence.run('left', 'mode1')                 # 물체 옮기기 전체
```

### 바퀴가 안 멈출 때
- 실행 중이면 **Ctrl+C** (`drive_to_stop_line`, `test_motor.py` 는 Ctrl+C 때 모터를 멈춘다)
- 프로그램이 죽었는데 계속 돌면
  ```bash
  python3 -c "import hw; hw.stop()"
  ```
- 그래도 안 되면 배터리 스위치를 끈다

### 자주 나는 문제
| 증상 | 확인할 것 |
|---|---|
| `[경고] Adeept 웹 컨트롤러가 실행 중` | `sudo systemctl stop Adeept_Robot.service` |
| `카메라를 열 수 없습니다` / `USB 웹캠을 찾을 수 없습니다` | 웹 컨트롤러가 웹캠을 쓰는 중인지, `ls -l /dev/v4l/by-id`, USB 연결 |
| `No I2C device at address: 0x5f` | Robot HAT 전원(배터리 스위치), HAT 연결 |
| `GPIO busy` / pin in use | 다른 프로그램이 초음파 핀을 쓰는 중 (웹 컨트롤러, 다른 테스트) |
| 초음파가 계속 200cm | 측정 범위(2m) 밖이거나 앞에 아무것도 없음, 배선 |
| 초음파 값이 튐 | `distance_median(n)` 의 `n` 을 키운다, 센서 앞을 비스듬한 면이 아닌 평평한 면으로 |
| 서보가 "지잉" 소리, 떨림 | 기구 끝에 걸려 버티는 중 → 각도 범위를 줄인다. 배터리 전압도 확인 |
| 모터가 약하거나 멈칫 | 배터리 충전 상태 |
| 팔이 갑자기 튄다 | 프로그램 시작 직후 첫 이동은 현재 각도를 몰라서 한 번에 간다 (정상) |
