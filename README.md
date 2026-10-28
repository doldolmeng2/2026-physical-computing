# 2026-physical-computing

2026-2 피지컬컴퓨팅 PiCar 프로젝트 (Adeept PiCar-Pro V2 + Robot HAT V3.3)

미션 흐름: **QR(LEFT/RIGHT) 인식 → 직진 → 모니터 30cm 앞 정지선에서 정지 → 처음 방향 물체를 반대편 빈 칸으로 → 반대편 물체를 처음 방향 빈 칸으로**

---

## 1. 파일 구성

| 파일 | 내용 |
|---|---|
| `hw.py` | 모터·서보·초음파·카메라 설정값과 기본 함수 |
| `qr.py` | 웹캠 QR 인식 |
| `arm.py` | 팔 자세 저장/이동, 집게, 집기(`pick`)/놓기(`place`) |
| `drive.py` | 직진하다가 정지선에서 정지 |
| `main.py` | 미션 1~5 순서대로 실행 |
| `poses.json` | 저장한 팔 자세 (`webui` 나 `tests/test_arm.py` 로 Pi에서 만든다) |
| `webui/` | 카메라·QR·초음파를 보면서 버튼으로 팔을 움직이고 자세를 저장하는 웹 페이지 (4절) |
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
- Pi에서 만든 `poses.json` → Pi에서 `git add poses.json && git commit -m "..." && git push` → PC에서 `git pull`
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
| `CAMERA_INDEX` | 웹캠 번호 (`/dev/video0` → 0) | `0` | 카메라가 안 열리면 `ls /dev/video*` 로 확인 |
| `CAMERA_SIZE` | 카메라 해상도 | `(640, 480)` | QR이 잘 안 읽히면 키워 볼 수 있음 (느려짐) |

### arm.py
| 값 | 의미 | 현재 | 찾는 법 |
|---|---|---|---|
| `GRIP_OPEN` | 집게가 열린 각도 | `None` | `test_arm.py` 에서 `4 <각도>` 로 물체가 충분히 들어갈 만큼 열리는 값 |
| `GRIP_CLOSE` | 물체를 잡은 각도 | `None` | 물체를 넣고 조금씩 닫아서 **놓치지 않는 가장 약한 값**. 너무 세게 닫으면 서보가 "지잉" 소리를 내며 버틴다 (전류 많이 씀) |
| `POSE_NAMES` | 미션에서 쓰는 자세 이름 목록 | 6개 | 아래 4절 참고 |
| `move_to(step, delay)` | 한 번에 움직이는 각도(°)와 간격(초). 작을수록 부드럽고 느림 | `2`, `0.02` | 팔이 흔들리거나 물체를 넘어뜨리면 줄인다 |

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

## 4. 팔 위치(자세) 저장하는 법

자세 = 팔 서보 3개(채널 1 팔 좌우, 2 팔 상하, 3 손목)의 각도 묶음. 집게(채널 4)는 자세에 넣지 않고 `GRIP_OPEN`/`GRIP_CLOSE` 로 따로 쓴다.

### 저장할 자세
| 이름 | 언제 쓰나 |
|---|---|
| `drive` | 주행할 때 접어 둔 자세 (모니터에 닿지 않게) |
| `qr` | 출발선에서 모니터 QR이 웹캠에 잘 보이는 자세 |
| `left_pick` | 왼쪽 상자 물체를 집는 위치 |
| `left_place` | 왼쪽 상자 빈 칸에 놓는 위치 |
| `right_pick` | 오른쪽 상자 물체를 집는 위치 |
| `right_place` | 오른쪽 상자 빈 칸에 놓는 위치 |

pick/place 자세는 **로봇을 실제 정지선 위치에 두고** 저장해야 한다 (정지 후에는 바퀴를 못 움직임).

### 방법 A: 웹 페이지 (추천)
카메라 화면과 인식 중인 QR, 초음파 거리를 보면서 버튼으로 팔을 움직이고 저장한다.
1. Pi에서 실행
   ```bash
   sudo systemctl stop Adeept_Robot.service
   cd ~/picar_mission && git pull
   python3 webui/app.py
   ```
2. PC 브라우저에서 **`http://192.168.50.2:5002`** 접속. 시작하면 팔·집게가 90°, 조향이 가운데로 간다.
3. **서보 각도** 카드
   - `1° 2° 5° 10°` 로 한 번에 움직일 각도를 고른다
   - `−` / `+` 버튼: 한 번 누르면 한 칸, **누르고 있으면 계속** 움직인다
   - 슬라이더: 끌어서 놓으면 그 각도로 천천히 이동
4. **자세 저장** 카드
   - 아래 칩(`○ left_pick` 등)을 누르면 이름 칸에 들어간다. ✓ 는 이미 저장된 자세
   - **현재 자세 저장** → `poses.json` 에 팔 좌우·상하·손목 각도 저장 (같은 이름은 덮어쓰기 확인)
   - 표의 **이동** 으로 다시 불러와 같은 위치로 오는지 확인, **삭제** 로 지우기
5. 집게는 자세에 저장되지 않는다. 집게 행에서 열림/닫힘 각도를 찾아 `arm.py` 의 `GRIP_OPEN`, `GRIP_CLOSE` 에 직접 적는다.
6. Ctrl+C 로 끄고 `poses.json` 을 push (아래 방법 B 의 5번)

이 페이지가 켜져 있는 동안은 카메라·초음파·서보를 쓰는 다른 프로그램(`tests/`, `main.py`)을 같이 실행하지 않는다.

### 방법 B: 터미널 (`tests/test_arm.py`)
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
3. 원하는 위치가 되면 이름을 붙여 저장 (같은 이름으로 다시 저장하면 덮어씀)
   ```
   > save left_pick
   ```
4. 다른 자세로 갔다가 다시 불러와서 같은 위치로 오는지 확인
   ```
   > go drive
   > go left_pick
   > list         # 저장된 자세 전부 보기
   > q
   ```
5. `poses.json` 이 생긴다. GitHub에 올린다
   ```bash
   git add poses.json
   git commit -m "Save arm poses"
   git push
   ```

`poses.json` 은 이런 모양이다. 각도를 직접 고쳐도 된다.
```json
{
  "left_pick": {"1": 150, "2": 60, "3": 110}
}
```

---

## 5. 수동 디버깅

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
>>> import hw, qr, drive, arm
>>> cap = hw.open_camera(); print(qr.wait_for_qr(cap, timeout=10)); cap.release()   # 미션 1
>>> drive.drive_to_stop_line()                    # 미션 2
>>> arm.pick('left'); arm.place('right')          # 미션 3
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
| `카메라를 열 수 없습니다` | 웹 컨트롤러가 웹캠을 쓰는 중인지, `ls /dev/video*`, USB 연결 |
| `No I2C device at address: 0x5f` | Robot HAT 전원(배터리 스위치), HAT 연결 |
| `GPIO busy` / pin in use | 다른 프로그램이 초음파 핀을 쓰는 중 (웹 컨트롤러, 다른 테스트) |
| 초음파가 계속 200cm | 측정 범위(2m) 밖이거나 앞에 아무것도 없음, 배선 |
| 초음파 값이 튐 | `distance_median(n)` 의 `n` 을 키운다, 센서 앞을 비스듬한 면이 아닌 평평한 면으로 |
| 서보가 "지잉" 소리, 떨림 | 기구 끝에 걸려 버티는 중 → 각도 범위를 줄인다. 배터리 전압도 확인 |
| 모터가 약하거나 멈칫 | 배터리 충전 상태 |
| 팔이 갑자기 튄다 | 프로그램 시작 직후 첫 이동은 현재 각도를 몰라서 한 번에 간다 (정상) |
