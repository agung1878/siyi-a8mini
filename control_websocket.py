#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sys
import time

from dotenv import load_dotenv

try:
    import websocket
except ImportError:
    print("Missing dependency: websocket-client. Install with `pip install websocket-client`.")
    sys.exit(1)

from siyi_sdk import SIYISDK

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def get_default_ws_url():
    return os.getenv("SIYI_WS_URL", "ws://localhost:8765")


def get_default_cam_ip():
    return os.getenv("SIYI_IP", "192.168.144.25")


def get_default_cam_port():
    return int(os.getenv("SIYI_PORT", "37260"))


def send_ws_response(ws, request, status, info=None, data=None):
    if ws is None:
        return
    response = {
        "type": "publish",
        "uav_id": request.get("uav_id", 1),
        "kind": "telemetry",
        "metric": "gimbal_control_response",
        "payload": {
            "command": request.get("payload", {}).get("command"),
            "status": status,
            "info": info,
            "data": data or {},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        },
    }
    try:
        ws.send(json.dumps(response))
    except Exception as exc:
        logger.warning("Unable to send websocket response: %s", exc)


def handle_command(cam, message, ws=None):
    if not isinstance(message, dict):
        raise ValueError("Invalid message format")

    metric = message.get("metric")
    payload = message.get("payload", {})
    command = payload.get("command")

    logger.info("Received websocket command=%s metric=%s payload=%s", command, metric, payload)

    if metric != "gimbal_control":
        raise ValueError("Unsupported metric: %s" % metric)

    if command == "set_angle":
        yaw = float(payload.get("yaw_deg", payload.get("yaw", 0)))
        pitch = float(payload.get("pitch_deg", payload.get("pitch", 0)))
        speed_percent = int(payload.get("speed_percent", 30))
        kp = max(1, min(10, speed_percent // 10))
        cam.setGimbalRotation(yaw, pitch, err_thresh=1.0, kp=kp)
        send_ws_response(ws, message, "ok", info="set_angle applied", data={"yaw": yaw, "pitch": pitch})

    elif command == "gimbal_speed":
        yaw_speed = int(payload.get("yaw_speed", payload.get("yawSpeed", 0)))
        pitch_speed = int(payload.get("pitch_speed", payload.get("pitchSpeed", 0)))
        yaw_speed = max(-100, min(100, yaw_speed))
        pitch_speed = max(-100, min(100, pitch_speed))
        cam.requestGimbalSpeed(yaw_speed, pitch_speed)
        send_ws_response(
            ws,
            message,
            "ok",
            info="gimbal_speed applied",
            data={"yaw_speed": yaw_speed, "pitch_speed": pitch_speed},
        )

    elif command == "zoom_in":
        cam.requestZoomIn()
        time.sleep(0.4)
        cam.requestZoomHold()
        send_ws_response(ws, message, "ok", info="zoom_in applied", data={"zoom": cam.getZoomLevel()})

    elif command == "zoom_out":
        cam.requestZoomOut()
        time.sleep(0.4)
        cam.requestZoomHold()
        send_ws_response(ws, message, "ok", info="zoom_out applied", data={"zoom": cam.getZoomLevel()})

    elif command == "zoom_hold":
        cam.requestZoomHold()
        send_ws_response(ws, message, "ok", info="zoom_hold applied", data={"zoom": cam.getZoomLevel()})

    elif command == "photo":
        cam.requestPhoto()
        send_ws_response(ws, message, "ok", info="photo requested")

    elif command == "record":
        cam.requestRecording()
        send_ws_response(ws, message, "ok", info="recording toggled")

    elif command == "center":
        cam.setGimbalRotation(0, 0)
        send_ws_response(ws, message, "ok", info="center command applied")

    elif command == "status":
        attitude = cam.getAttitude()
        zoom = cam.getZoomLevel()
        send_ws_response(ws, message, "ok", info="status", data={"attitude": attitude, "zoom": zoom})

    elif command == "follow_mode":
        cam.requestFollowMode()
        send_ws_response(ws, message, "ok", info="follow mode requested")

    else:
        raise ValueError("Unsupported command: %s" % command)


def on_message(ws, raw_message):
    try:
        message = json.loads(raw_message)
    except json.JSONDecodeError:
        logger.error("Received invalid JSON: %s", raw_message)
        return

    try:
        handle_command(ws.cam, message, ws)
    except Exception as exc:
        logger.exception("Command handling failed: %s", exc)
        send_ws_response(ws, message, "error", info=str(exc))


def on_open(ws):
    logger.info("WebSocket connection opened to %s", ws.url)
    ws.send(json.dumps({
        "type": "publish",
        "uav_id": 1,
        "kind": "telemetry",
        "metric": "gimbal_control_status",
        "payload": {
            "command": "ready",
            "source": "web_gimbal_control",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        },
    }))


def on_error(ws, error):
    logger.error("WebSocket error: %s", error)


def on_close(ws, close_status_code, close_msg):
    logger.info("WebSocket connection closed: %s %s", close_status_code, close_msg)


def build_parser(default_ws_url, default_ip, default_port):
    parser = argparse.ArgumentParser(description="Control SIYI camera via websocket commands.")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--ws-url", default=default_ws_url, help="WebSocket server URL")
    parser.add_argument("--ip", default=default_ip, help="SIYI camera IP")
    parser.add_argument("--port", default=default_port, type=int, help="SIYI camera port")
    return parser


def main():
    env_parser = argparse.ArgumentParser(add_help=False)
    env_parser.add_argument("--env-file", default=".env", help="Path to .env file")
    env_args, remaining_args = env_parser.parse_known_args()

    if env_args.env_file:
        load_dotenv(dotenv_path=env_args.env_file, override=False)

    parser = build_parser(get_default_ws_url(), get_default_cam_ip(), get_default_cam_port())
    parser.set_defaults(env_file=env_args.env_file)
    args = parser.parse_args(remaining_args)

    cam = SIYISDK(server_ip=args.ip, port=args.port)
    if not cam.connect():
        logger.error("Unable to connect to SIYI camera at %s:%s", args.ip, args.port)
        return 1

    cam.requestFollowMode()

    ws_app = websocket.WebSocketApp(
        args.ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws_app.cam = cam

    while True:
        try:
            logger.info("Connecting to websocket %s", args.ws_url)
            ws_app.run_forever()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as exc:
            logger.exception("WebSocket loop error, reconnecting in 5 seconds: %s", exc)
            time.sleep(5)

    cam.disconnect()
    logger.info("Camera disconnected and exiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
