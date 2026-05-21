import os
from statistics import mode

from flask import Flask, jsonify, request, render_template, send_file
from flask_cors import CORS
import serial
import threading
import time
import json
import csv
from datetime import datetime

# # =============================================================================
# # CONFIG
# # ===========================================================================

API_KEY = "svr123"

PICO_PORT = "COM5"
PICO_BAUD = 115200

LOG_FOLDER = "telemetry_logs"



if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)


def get_log_file():
    return os.path.join(
        LOG_FOLDER,
        f"telemetry_{datetime.now().strftime('%Y%m%d')}.csv"
    )

# # =============================================================================
# # FLASK APP
# # =============================================================================

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

CORS(app)

# # =============================================================================
# # GLOBAL VARIABLES
# # =============================================================================

telemetry = {}
notifications = []
debug_log = []
today_log = []

serial_lock = threading.Lock()
pico_ser = None

_prev_wind_alarm = False

_rtc_last_second = -1
_rtc_stuck_ticks = 0
_RTC_STUCK_LIMIT = 5

# IMPORTANT:
# This tracks what mode WE sent to Pico
_commanded_mode = "auto"

# # =============================================================================
# # NOTIFICATIONS
# # =============================================================================

def _push_notif(msg, level="info"):
    notifications.append({
        "msg": msg,
        "level": level,
        "time": datetime.now().strftime("%H:%M:%S")
    })

    if len(notifications) > 50:
        notifications.pop(0)


def _push_debug(msg):
    debug_log.append({
        "msg": msg,
        "time": datetime.now().strftime("%H:%M:%S")
    })

    if len(debug_log) > 100:
        debug_log.pop(0)

# =============================================================================
# CSV STORAGE FOLDER
#  

LOG_FOLDER = "telemetry_logs"

os.makedirs(LOG_FOLDER, exist_ok=True)

# Create folder automatically


# Daily CSV filename
csv_filename = os.path.join(
    LOG_FOLDER,
    f"telemetry_{datetime.now().strftime('%Y%m%d')}.csv"
)

# =============================================================================
# CREATE CSV HEADER IF FILE DOESN'T EXIST
# =============================================================================

if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            
           
                "mode",
                "ts",
                "az",
                "el",
                "az_actual",
                "el_actual",
                "az_enc",
                "az_tgt",
                "az_err",
                "el_enc",
                "el_tgt",
                "el_err",
                "wind",
                "wind_thr",
                "wind_raw",
                "wind_v",
                "imu_pitch",
                "imu_roll",
                "imu_yaw",
                "imu_ax",
                "imu_ay",
                "imu_az",
                "imu_el_diff",
                "imu_el_alert",
                "imu_enc_az",
                "imu_vs_enc",
                "imu_gx",
                "imu_gy",
                "imu_gz",
                "lat",
                "lon",
                "gps_valid",
                "gps_sats",
                "gps_hdop",
                "gps_age",
                "gps_chars",
                "rtc_h",
                "rtc_m",
                "rtc_s",
                "rtc_d",
                "rtc_mo",
                "rtc_y",
                "day_start",
                "day_end",
                "prox_az",
                "prox_el",
                "el_full",
                "ishome",
                "is_homing",
                "night_park",
                "wind_park_az",
                "wind_park_el",
                "wind_cool",
                "imu_alarm",
                "imu_ok",
                "synced",
                "step_az",
                "step_el",
                "tc_temp",
                "tc_cj",
                "tc_ok",
                "tc_fault",
                "ds_temp",
                "ds_ok",
                "night_done",
                "moving_home",
                "nudge_cnt",
                "az_home_miss",
                "el_home_miss",
                "el_nudge_cnt",
                
                            ])
        
        
        # =============================================================================
# FUNCTION TO SAVE DATA
# =============================================================================

def save_to_csv(mode, ts, az, el, az_actual, el_actual, az_enc, az_tgt, az_err, el_enc, el_tgt, el_err, wind, wind_thr, wind_raw, wind_v, imu_pitch, imu_roll, imu_yaw, imu_ax, imu_ay, imu_az, imu_el_diff, imu_el_alert, imu_enc_az, imu_vs_enc, imu_gx, imu_gy, imu_gz, lat, lon, gps_valid, gps_sats, gps_hdop, gps_age, gps_chars, rtc_h, rtc_m, rtc_s, rtc_d, rtc_mo, rtc_y, day_start, day_end, prox_az, prox_el, el_full, ishome, is_homing, night_park, wind_park_az, wind_park_el, wind_cool, imu_alarm, imu_ok, synced, step_az, step_el, tc_temp, tc_cj, tc_ok, tc_fault, ds_temp, ds_ok, night_done, moving_home, nudge_cnt, az_home_miss, el_home_miss, el_nudge_cnt):
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                mode,
                ts, # type: ignore
                az, # type: ignore
                el, # type: ignore
                az_actual,
                el_actual,
                az_enc, # type: ignore
                az_tgt, # type: ignore
                az_err, # type: ignore
                el_enc, # type: ignore
                el_tgt, # type: ignore
                el_err,# type: ignore
                wind,# type: ignore
                wind_thr,# type: ignore
                wind_raw,# type: ignore
                wind_v,# type: ignore
                imu_pitch,# type: ignore
                imu_roll,# type: ignore
                imu_yaw,# type: ignore
                imu_ax,# type: ignore
                imu_ay,# type: ignore
                imu_az,# type: ignore
                imu_el_diff,# type: ignore
                imu_el_alert,# type: ignore
                imu_enc_az,# type: ignore
                imu_vs_enc,# type: ignore
                imu_gx,# type: ignore
                imu_gy,# type: ignore
                imu_gz,# type: ignore
                lat,# type: ignore
                lon,# type: ignore
                gps_valid,# type: ignore
                gps_sats,# type: ignore
                gps_hdop,# type: ignore
                gps_age,# type: ignore
                gps_chars,# type: ignore
                rtc_h,# type: ignore
                rtc_m,# type: ignore
                rtc_s,# type: ignore
                rtc_d,# type: ignore
                rtc_mo,# type: ignore
                rtc_y,# type: ignore
                day_start,# type: ignore
                day_end,# type: ignore
                prox_az,# type: ignore
                prox_el,# type: ignore
                el_full,# type: ignore
                ishome,# type: ignore
                is_homing,# type: ignore
                night_park,# type: ignore
                wind_park_az,# type: ignore
                wind_park_el,# type: ignore
                wind_cool,# type: ignore
                imu_alarm,# type: ignore
                imu_ok,# type: ignore
                synced,# type: ignore
                step_az,# type: ignore
                step_el,# type: ignore
                tc_temp,# type: ignore
                tc_cj,# type: ignore
                tc_ok,# type: ignore
                tc_fault,# type: ignore
                ds_temp,# type: ignore
                ds_ok,# type: ignore
                night_done,# type: ignore
                moving_home,# type: ignore
                nudge_cnt,# type: ignore
                az_home_miss,# type: ignore
                el_home_miss,# type: ignore
                el_nudge_cnt,# type: ignore
            
        ])
            
# ===============================
# CSV LOGGING
# ===============================


def log_full():

    try:

        if not telemetry:
            return

        log_file = get_log_file()

        file_exists = os.path.exists(log_file)

        fields = ["timestamp"] + list(telemetry.keys())

        with open(log_file, "a", newline="") as f:

            writer = csv.DictWriter(f, fieldnames=fields)

            if not file_exists:
                writer.writeheader()

            row = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            row.update(telemetry)

            writer.writerow(row)

        print("✅ CSV SAVED")

    except Exception as e:

        print("CSV ERROR:", e)
# # =============================================================================
# # SERIAL CONNECTION
# # =============================================================================

def connect_pico():
    global pico_ser

    while True:
        try:
            if pico_ser is None or not pico_ser.is_open:

                pico_ser = serial.Serial(
                    PICO_PORT,
                    PICO_BAUD,
                    timeout=1
                )

                pico_ser.reset_input_buffer()

                print(f"✅ Connected to Pico on {PICO_PORT}")

                _push_notif(
                    f"Pico connected on {PICO_PORT}",
                    "success"
                )

        except Exception as e:

            print(f"⏳ Waiting for Pico... {e}")

            pico_ser = None

        time.sleep(2)

# # =============================================================================
# # SEND DATA TO PICO
# # =============================================================================

def send_to_pico(cmd_dict):

    global pico_ser

    if pico_ser and pico_ser.is_open:

        with serial_lock:

            try:

                json_cmd = json.dumps(cmd_dict) + "\n"

                pico_ser.write(json_cmd.encode())

                pico_ser.flush()

                print(f"📤 Sent: {json_cmd.strip()}")

            except Exception as e:

                print(f"❌ Serial write error: {e}")

                pico_ser.close()

                pico_ser = None

    else:

        print("⚠️ Pico not connected")

# # =============================================================================
# # RTC CHECK
# # =============================================================================

def _check_rtc_ok(d):

    global _rtc_last_second
    global _rtc_stuck_ticks

    year = d.get("rtc_y", 2000)
    sec = d.get("rtc_s", 0)

    if year <= 2000:

        _rtc_last_second = -1
        _rtc_stuck_ticks = 0

        return 0

    if sec == _rtc_last_second:

        _rtc_stuck_ticks += 1

    else:

        _rtc_stuck_ticks = 0

    _rtc_last_second = sec

    if _rtc_stuck_ticks >= _RTC_STUCK_LIMIT:
        return 0

    return 1

# # =============================================================================
# # READ SERIAL DATA
# # =============================================================================
def read_pico_thread():
    
    global pico_ser
    global telemetry
    global _prev_wind_alarm

    while True:

        try:

            if pico_ser and pico_ser.is_open:

                if pico_ser.in_waiting:

                    raw = (
                        pico_ser.readline()
                        .decode("utf-8", errors="ignore")
                        .replace("\x00", "")
                        .strip()
                    )

                    if raw:

                        print("RAW SERIAL:", raw)

                        if "{" in raw and "}" in raw:

                            try:

                                start = raw.find("{")
                                end = raw.rfind("}") + 1

                                raw_json = raw[start:end]

                                d = json.loads(raw_json)

                                print("✅ JSON RECEIVED:", d)

                                if "error" in d and len(d) == 1:

                                    print(f"[PICO ERROR] {d['error']}")

                                    _push_debug(d["error"])

                                    continue

                                telemetry.update ({
                                    
                                    "mode": d.get("mode", ""),
                                    "ts": d.get("ts", 0),
                                    "az": d.get("cur_az", 0),
                                    "el": d.get("cur_el", 0),
                                    "az_actual": d.get("az_actual", 0),
                                    "el_actual": d.get("el_actual", 0),
                                    "az_enc": d.get("az_enc", 0),
                                    "az_tgt": d.get("az_tgt", 0),
                                    "az_err": d.get("az_err", 0),
                                    "el_enc": d.get("el_enc", 0),
                                    "el_tgt": d.get("el_tgt", 0),
                                    "el_err": d.get("el_err", 0),
                                    "wind_speed": d.get("wind", 0),
                                    "wind_limit": d.get("wind_thr", 0),   
                                    "wind_raw": d.get("wind_raw", 0),
                                    "wind_v": d.get("wind_v", 0),  
                                    "imu_pitch": d.get("imu_pitch", 0),
                                    "imu_roll": d.get("imu_roll", 0),
                                    "imu_yaw": d.get("imu_yaw", 0),
                                    "imu_ax": d.get("imu_ax", 0),
                                    "imu_ay": d.get("imu_ay", 0),
                                    "imu_az": d.get("imu_az", 0),
                                    "imu_el_diff": d.get("imu_el_diff", 0),
                                    "imu_el_alert": d.get("imu_el_alert", 0),
                                    "imu_enc_az": d.get("imu_enc_az", 0),
                                    "imu_vs_enc": d.get("imu_vs_enc", 0),
                                    "imu_gx": d.get("imu_gx", 0),
                                    "imu_gy": d.get("imu_gy", 0),
                                    "imu_gz": d.get("imu_gz", 0),
                                    "lat": d.get("lat", 0),
                                    "lon": d.get("lon", 0),
                                    "gps_valid": d.get("gps_valid", 0),
                                    "gps_sats": d.get("gps_sats", 0),
                                    "gps_hdop": d.get("gps_hdop", 0),
                                    "gps_age": d.get("gps_age", 0),
                                    "gps_chars": d.get("gps_chars", 0),
                                    "rtc_h": d.get("rtc_h", 0),
                                        
                                    "rtc_m": d.get("rtc_m", 0),
                                    "rtc_s": d.get("rtc_s", 0),
                                    "rtc_d": d.get("rtc_d", 0),
                                    "rtc_mo": d.get("rtc_mo", 0),
                                    "rtc_y": d.get("rtc_y", 0),
                                    "rtc_ok": _check_rtc_ok(d),
                                    "day_start": d.get("day_start", 0),
                                    "day_end": d.get("day_end", 0),
                                    "prox_az": d.get("prox_az", 0),
                                    "prox_el": d.get("prox_el", 0),
                                    "el_full": d.get("el_full", 0),
                                    "ishome": d.get("ishome", 0),
                                    "is_homing": d.get("is_homing", 0),
                                    "night_park": d.get("night_park", 0),
                                    "wind_park_az": d.get("wind_park_az", 0),
                                    "wind_park_el": d.get("wind_park_el", 0),
                                    "wind_cool": d.get("wind_cool", 0),
                                    "imu_alarm": d.get("imu_alarm", 0),
                                    "imu_ok": d.get("imu_ok", 0),
                                    "synced": d.get("synced", 0),
                                    "step_az": d.get("step_az", 0),
                                    "step_el": d.get("step_el", 0),
                                    "tc_temp": d.get("tc_temp", 0),
                                    "tc_cj": d.get("tc_cj", 0),
                                    "tc_ok": d.get("tc_ok", 0),
                                    "tc_fault": d.get("tc_fault", 0),
                                    "ds_temp": d.get("ds_temp", 0),
                                    "ds_ok": d.get("ds_ok", 0),
                                    "night_done": d.get("night_done", 0),
                                    "moving_home": d.get("moving_home", 0),
                                    "nudge_cnt": d.get("nudge_cnt", 0),
                                    "az_home_miss": d.get("az_home_miss", 0),
                                    "el_home_miss": d.get("el_home_miss", 0),
                                    "el_nudge_cnt": d.get("el_nudge_cnt", 0),
                                })
                                

                                print("📡 TELEMETRY UPDATED")

                                ws = d.get("wind", 0)
                                thr = d.get("wind_thr", 0)

                                wind_alarm_now = (
                                    ws > thr > 0
                                )

                                if wind_alarm_now and not _prev_wind_alarm:

                                    _push_notif(
                                        f"High wind: {ws:.1f} m/s",
                                        "danger"
                                    )

                                elif not wind_alarm_now and _prev_wind_alarm:

                                    _push_notif(
                                        f"Wind safe: {ws:.1f} m/s",
                                        "success"
                                    )

                                _prev_wind_alarm = wind_alarm_now

                            except Exception as e:

                                print("❌ JSON ERROR:", e)

                                _push_debug(str(e))

                else:

                    time.sleep(0.05)

            else:

                time.sleep(1)

        except Exception as e:

            print(f"❌ READ ERROR: {e}")

            time.sleep(1)


# =============================================================================
# SNAPSHOT THREAD
# =============================================================================

def snapshot_thread():

    while True:

        try:

            if telemetry:

                today_log.append({

                    "time": datetime.now().strftime("%H:%M:%S"),

                    "temp": telemetry.get("tc_avg", 0),

                    "wind": telemetry.get("wind_speed", 0),

                    "az": telemetry.get("cur_az", 0),

                    "el": telemetry.get("cur_el", 0)
                })

                if len(today_log) > 86400:
                    today_log.pop(0)

            time.sleep(1)

        except Exception as e:

            print("SNAPSHOT ERROR:", e)
            
# =============================================================================
# CSV LOGGER THREAD
# =============================================================================

def csv_logger_thread():

    while True:

        try:

            log_full()

        except Exception as e:

            print("LOGGER ERROR:", e)

        # Save every 1 minute
        time.sleep(60)     

# =============================================================================
# AUTH
# =============================================================================

@app.before_request
def check_auth():

    # DISABLE AUTH FOR LOCAL TESTING

    return None

    # ENABLE THIS LATER

    # if request.path.startswith("/api"):
    #
    #     if request.headers.get("x-api-key") != API_KEY:
    #
    #         return jsonify({
    #             "error": "Unauthorized"
    #         }), 403

# =============================================================================
# ROUTES
# =============================================================================

@app.route("/")
def index():

    return render_template("dashboard.html")

# =============================================================================

@app.route("/api/data")
def api_data():

    print("📤 API DATA SENT:", telemetry)

    return jsonify(telemetry)

# =============================================================================

@app.route("/api/wind")
def api_wind():

    speed = telemetry.get("wind_speed", 0)
    limit = telemetry.get("wind_limit", 0)

    status = "SAFE"

    if speed > limit:
        status = "HIGH"

    return jsonify({
        "speed": speed,
        "limit": limit,
        "status": status
    })


# =============================================================================
# AUTO DELETE OLD CSV FILES (OLDER THAN 5 YEARS)
# =============================================================================

RETENTION_DAYS = 5 * 365   # 5 years


def cleanup_old_logs():

    try:

        now = time.time()

        for filename in os.listdir(LOG_FOLDER):

            if filename.endswith(".csv"):

                file_path = os.path.join(LOG_FOLDER, filename)

                file_age_days = (
                    now - os.path.getmtime(file_path)
                ) / (60 * 60 * 24)

                if file_age_days > RETENTION_DAYS:

                    os.remove(file_path)

                    print(f"🗑 Deleted old log: {filename}")

    except Exception as e:

        print("CLEANUP ERROR:", e)


# ============================================================================= 

@app.route("/api/debug")
def api_debug():

    return jsonify(debug_log[-50:])

# =============================================================================

@app.route("/api/today")
def api_today():

    return jsonify(today_log[-100:])
@app.route("/api/logs")
def api_logs():
    try:
        with open(LOG_FILE, "r") as f: # pyright: ignore[reportUndefinedVariable]
            return jsonify(list(csv.DictReader(f))[-50:])
    except:
        return jsonify([])


# =============================================================================
# DOWNLOAD CSV
# =============================================================================

@app.route("/download/<filename>")
def download_file(filename):

    file_path = os.path.join(LOG_FOLDER, filename)

    if os.path.exists(file_path):

        return send_file(
            file_path,
            as_attachment=True
        )

    return jsonify({
        "error": "File not found"
    }), 404

# =============================================================================

@app.route("/test")
def test():

    return jsonify({
        "status": "working",
        "telemetry": telemetry,
        "serial_connected": (
            pico_ser.is_open
            if pico_ser else False
        )
    })

# =============================================================================
# CONTROL API
# =============================================================================

@app.route("/api/control", methods=["POST"])
def control_actuator():

    global _commanded_mode

    try:

        data = request.get_json(force=True) or {}

        action = data.get("action")
        cmd = data.get("cmd")

        button_map = {

            "up": {
                "cmd": "el_jog",
                "dir": 1
            },

            "down": {
                "cmd": "el_jog",
                "dir": -1
            },

            "el_stop": {
                "cmd": "el_jog",
                "dir": 0
            },

            "left": {
                "cmd": "az_jog",
                "dir": -1
            },

            "right": {
                "cmd": "az_jog",
                "dir": 1
            },

            "az_stop": {
                "cmd": "az_jog",
                "dir": 0
            },

            "manual_on": {
                "cmd": "set_mode",
                "val": "manual"
            },

            "manual_off": {
                "cmd": "set_mode",
                "val": "auto"
            }
        }

        # ---------------------------------------------------------

        if action in button_map:

            pico_cmd = button_map[action]

            send_to_pico(pico_cmd)

            if pico_cmd.get("cmd") == "set_mode":

                _commanded_mode = pico_cmd.get("val")

            return jsonify({
                "status": "ok",
                "dispatched": pico_cmd
            })

        # ---------------------------------------------------------

        if cmd == "set_mode":

            val = data.get("val")

            send_to_pico({
                "cmd": "set_mode",
                "val": val
            })

            _commanded_mode = val

            return jsonify({
                "status": "ok"
            })

        # ---------------------------------------------------------

        return jsonify({
            "error": "Unknown command"
        }), 400

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 400

# =============================================================================
# UPDATE SETTINGS
# =============================================================================

@app.route("/api/update", methods=["POST"])
def update_settings():

    global _commanded_mode

    try:

        data = request.get_json(force=True) or {}

        if _commanded_mode != "manual":

            return jsonify({
                "error": "Switch to manual mode first"
            }), 409

        # ---------------------------------------------------------

        if "wind_limit" in data:

            send_to_pico({
                "cmd": "set_wind",
                "thr": float(data["wind_limit"])
            })

        # ---------------------------------------------------------

        if "mode" in data:

            send_to_pico({
                "cmd": "set_mode",
                "val": data["mode"]
            })

            _commanded_mode = data["mode"]

        # ---------------------------------------------------------

        return jsonify({
            "status": "ok"
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 400

# =============================================================================
# MAIN
# =============================================================================

# Replace the very end of your app.py with this:
if __name__ == "__main__":
    
        # Delete logs older than 5 years
    cleanup_old_logs()
    # 1. Initialize and start the Pico connection thread
    t1 = threading.Thread(target=connect_pico, daemon=True)
    t1.start()
    
    # 2. Small pause to allow Serial port to initialize
    time.sleep(2)

    # 3. Start the background reading thread
    t2 = threading.Thread(target=read_pico_thread, daemon=True)
    t2.start()

    # 4. Start the snapshot logger
    t3 = threading.Thread(target=snapshot_thread, daemon=True)
    t3.start()

    print("\n" + "="*40)
    print("🚀 SOLAR TRACKER SCADA ONLINE")
    print("📡 Listening on Port: " + PICO_PORT)
    print("🌐 Dashboard URL: http://127.0.0.1:5000")
    print("="*40 + "\n")
    
        # 5. Start CSV logger thread
    t4 = threading.Thread(target=csv_logger_thread, daemon=True)
    t4.start()

    # CRITICAL: debug MUST be False to prevent Serial Port PermissionErrors
    # use_reloader=False is an extra safety measure
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

