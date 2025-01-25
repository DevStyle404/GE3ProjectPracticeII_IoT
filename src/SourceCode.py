# M5Stack関連の基本ライブラリをインポート
from m5stack import *
from m5ui import *
from uiflow import *
import time
import imu
import unit

# HTTPリクエスト用ライブラリ
import urequests
from ujson import dumps as dumps

# Ambient設定用のIDとキー
AMBIENT_CHANNEL_ID = "87640"
AMBIENT_WRITE_KEY = "74c80f5427e584f6"
AMBIENT_READ_KEY = "7e5c78d5dc27e8dd"

# 動作モードの設定（DEMOかPROD）
MODE = 'DEMO'  # 'DEMO' または 'PROD'

# ENV III UnitをポートAへ初期化
env3 = unit.get(unit.ENV3, unit.PORTA)

# 画面の色を設定してクリア
setScreenColor(0x222222)
lcd.clear()

# 在室状況などを表示するラベルを作成
label_presence = M5TextBox(10, 10, "Presence(Toggle): Unknown", lcd.FONT_Default, 0xFFFFFF, rotate=0)
label_presence_auto = M5TextBox(10, 30, "Presence(Auto): Unknown", lcd.FONT_Default, 0xFFFFFF, rotate=0)

label_detection_mode = M5TextBox(10, 50, "Mode: MANUAL", lcd.FONT_Default, 0xFFFFFF, rotate=0)

label_temp = M5TextBox(10, 70, "Temp: 0.0[°C]", lcd.FONT_Default, 0xFFFFFF, rotate=0)
label_ac = M5TextBox(10, 90, "AC: Unknown", lcd.FONT_Default, 0xFFFFFF, rotate=0)
label_led = M5TextBox(10, 110, "LED: Unknown", lcd.FONT_Default, 0xFFFFFF, rotate=0)

# 快適温度かどうかを表示するラベル
label_comfort = M5TextBox(10, 130, "Comfort: Unknown", lcd.FONT_Default, 0xFFFFFF, rotate=0)

# 注意喚起用のプロンプトラベル（赤色）
label_prompt = M5TextBox(10, 150, "", lcd.FONT_Default, 0xFF0000, rotate=0)

# ボタンやLEDに関するフラグ
button_pressed = False
led_button_pressed = False
detection_button_pressed = False
led_state = False

# 在室フラグ（トグルと自動）
presence_manual = False
presence_auto = False

# 検知モード（MANUALまたはAUTO）
detection_mode = 'MANUAL'

# IMUを初期化し、加速度を取得するための準備
imu0 = imu.IMU()

# 加速度データを取得する関数
def get_accel_data():
    acc_x, acc_y, acc_z = imu0.acceleration
    return acc_x, acc_y, acc_z

# 温度センサーのデータを取得する関数
def get_env_data():
    return env3.temperature

# Ambientにデータを送信する関数
def send_to_ambient(acc_x, acc_y, acc_z, temp):
    url = "http://ambidata.io/api/v2/channels/" + AMBIENT_CHANNEL_ID + "/data"
    headers = {"Content-Type": "application/json"}
    payload = {
        "writeKey": AMBIENT_WRITE_KEY,
        "d1": acc_x,
        "d2": acc_y,
        "d3": acc_z,
        "d4": temp
    }
    try:
        res = urequests.post(url, data=dumps(payload), headers=headers)
        res.close()
    except Exception as e:
        print("Error sending data to Ambient: " + str(e))

# 温度の閾値や快適温度範囲を設定
threshold_temp = 25.0
comfort_temp_min = 20.0
comfort_temp_max = 26.0

# モードに応じたチェック間隔などを設定
if MODE == 'DEMO':
    CHECK_INTERVAL = 5  # デモ用は5秒周期
elif MODE == 'PROD':
    CHECK_INTERVAL = 300  # 本番用は300秒周期
    no_change_counter = 0
    previous_diff = None

# 前回のチェック時刻を保持
last_check_time = time.time()

# エアコンの状態を保持する変数
ac_state = False

# メインループ開始
while True:
    # ボタンAを押したら、在室トグルフラグを切り替える
    if btnA.isPressed():
        if not button_pressed:
            presence_manual = not presence_manual
            button_pressed = True
            if detection_mode == 'MANUAL':
                presence_status = "IN" if presence_manual else "OUT"
                label_presence.setText("Presence(Toggle): " + presence_status)
                label_presence_auto.setText("")
                # 在室切り替えをアラート表示（コンソール）
                if presence_manual:
                    print("Alert: Manual presence is ON.")
                else:
                    print("Alert: Manual presence is OFF.")
    else:
        button_pressed = False

    # ボタンBを押したら、LEDのオンオフをトグル
    if btnB.isPressed():
        if not led_button_pressed:
            led_state = not led_state
            led_button_pressed = True
    else:
        led_button_pressed = False

    # ボタンCを押したら、検知モードを切り替える（MANUAL⇔AUTO）
    if btnC.isPressed():
        if not detection_button_pressed:
            if detection_mode == 'MANUAL':
                detection_mode = 'AUTO'
            else:
                detection_mode = 'MANUAL'
            detection_button_pressed = True
            # 表示を更新
            label_detection_mode.setText("Mode: " + detection_mode)
            if detection_mode == 'MANUAL':
                label_presence.setText("Presence(Toggle): " + ("IN" if presence_manual else "OUT"))
                label_presence_auto.setText("")
            else:
                label_presence_auto.setText("Presence(Auto): " + ("IN" if presence_auto else "OUT"))
                label_presence.setText("")
            # モード変更をアラート表示（コンソール）
            print("Alert: Detection mode switched to " + detection_mode + ".")
    else:
        detection_button_pressed = False

    # 各種データを取得
    acc_x, acc_y, acc_z = get_accel_data()
    temp = get_env_data()

    # 検知モードごとに在室ラベルを更新
    if detection_mode == 'MANUAL':
        presence_text = "Presence(Toggle): IN" if presence_manual else "Presence(Toggle): OUT"
        label_presence.setText(presence_text)
        label_presence_auto.setText("")
    elif detection_mode == 'AUTO':
        presence_text = "Presence(Auto): IN" if presence_auto else "Presence(Auto): OUT"
        label_presence_auto.setText(presence_text)
        label_presence.setText("")

    # 取得した温度を表示
    label_temp.setText("Temp: " + str(temp) + "[°C]")

    # エアコンのオンオフを判定して表示
    ac_state = temp > threshold_temp
    if ac_state:
        label_ac.setText("AC: ON")
    else:
        label_ac.setText("AC: OFF")

    # LED状態を表示
    if led_state:
        label_led.setText("LED: ON")
    else:
        label_led.setText("LED: OFF")

    # 快適温度かどうかを判定して表示
    if comfort_temp_min <= temp <= comfort_temp_max:
        label_comfort.setText("Comfort: Yes")
    else:
        label_comfort.setText("Comfort: No")

    # Ambientにデータ送信
    send_to_ambient(acc_x, acc_y, acc_z, temp)

    # 一定時間経過後の処理（DEMO/PRODごとに異なる）
    now = time.time()
    if now - last_check_time >= CHECK_INTERVAL:
        last_check_time = now
        try:
            if MODE == 'DEMO':
                if detection_mode == 'AUTO':
                    # DEMOモードでは最新5秒前の値と比較して在室判定
                    get_url = (
                        "http://ambidata.io/api/v2/channels/"
                        + AMBIENT_CHANNEL_ID
                        + "/data?limit=1&readKey="
                        + AMBIENT_READ_KEY
                    )
                    r = urequests.get(get_url)
                    if r.status_code == 200:
                        recv = r.json()
                        if recv:
                            rec_data = recv[0]
                            remote_x = float(rec_data.get("d1", 0))
                            remote_y = float(rec_data.get("d2", 0))
                            remote_z = float(rec_data.get("d3", 0))
                            diff = abs(remote_x - acc_x) + abs(remote_y - acc_y) + abs(remote_z - acc_z)
                            new_presence = True if diff >= 0.05 else False
                            if presence_auto != new_presence:
                                presence_auto = new_presence
                                if presence_auto:
                                    print("Alert: Auto presence is ON.")
                                else:
                                    print("Alert: Auto presence is OFF.")
                    r.close()
            elif MODE == 'PROD':
                if detection_mode == 'AUTO':
                    # PRODモードでは最新1800秒(30分)のデータを300秒ごとに比較
                    start_time = int(time.time()) - 1800
                    get_url = (
                        "http://ambidata.io/api/v2/channels/"
                        + AMBIENT_CHANNEL_ID
                        + "/data?start="
                        + str(start_time)
                        + "&readKey="
                        + AMBIENT_READ_KEY
                    )
                    r = urequests.get(get_url)
                    if r.status_code == 200:
                        recv = r.json()
                        if recv:
                            recv_sorted = sorted(recv, key=lambda x: x['created_at'])
                            segments = [[] for _ in range(6)]
                            current_time = int(time.time())
                            for data in recv_sorted:
                                timestamp = int(data['created_at'])
                                for i in range(6):
                                    segment_start = current_time - 1800 + (i * 300)
                                    segment_end = segment_start + 300
                                    if segment_start <= timestamp < segment_end:
                                        segments[i].append(data)
                                        break
                            changes_detected = False
                            for segment in segments:
                                if len(segment) == 0:
                                    continue
                                # セグメントごとに最後の値を比較
                                last_data = segment[-1]
                                remote_x = float(last_data.get("d1", 0))
                                remote_y = float(last_data.get("d2", 0))
                                remote_z = float(last_data.get("d3", 0))
                                diff = abs(remote_x - acc_x) + abs(remote_y - acc_y) + abs(remote_z - acc_z)
                                if previous_diff is not None and abs(diff - previous_diff) >= 0.05:
                                    changes_detected = True
                                    break
                                previous_diff = diff
                            if not changes_detected:
                                no_change_counter += 1
                                if no_change_counter >= 6:
                                    if presence_auto != True:
                                        presence_auto = True  # 不在
                                        print("Alert: Auto presence is OFF.")
                            else:
                                no_change_counter = 0
                                if presence_auto != False:
                                    presence_auto = False  # 在室
                                    print("Alert: Auto presence is ON.")
                    r.close()
        except Exception as e:
            print("Error retrieving data from Ambient: " + str(e))

    # プロンプト表示（英語、在室がOUTのときに注意喚起）
    if detection_mode == 'MANUAL' and not presence_manual:
        if ac_state and led_state:
            label_prompt.setText("Turn off Air Conditioner and LEDs!")
        elif ac_state:
            label_prompt.setText("Turn off Air Conditioner!")
        elif led_state:
            label_prompt.setText("Turn off LEDs!")
        else:
            label_prompt.setText("")
    elif detection_mode == 'AUTO' and not presence_auto:
        if ac_state and led_state:
            label_prompt.setText("Turn off Air Conditioner and LEDs!")
        elif ac_state:
            label_prompt.setText("Turn off Air Conditioner!")
        elif led_state:
            label_prompt.setText("Turn off LEDs!")
        else:
            label_prompt.setText("")
    else:
        label_prompt.setText("")

    # 少し待ってから次のループへ
    wait_ms(500)
