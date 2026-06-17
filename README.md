# WebSocket Control Testing for SIYI Camera

This document describes the WebSocket payloads and commands supported by `control_websocket.py`.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root or copy `.env.example` and update the values. The script loads `.env` automatically.

```bash
cp .env.example .env
```

3. Run the websocket bridge:

```bash
python control_websocket.py
```

4. If needed, set camera connection variables using environment variables, or override them on the command line:

```bash
export SIYI_IP=192.168.144.25
export SIYI_PORT=37260
export SIYI_WS_URL=ws://localhost:8765
```

## Message Format

Use this envelope for all commands:

```json
{
  "type": "publish",
  "uav_id": 1,
  "kind": "telemetry",
  "metric": "gimbal_control",
  "payload": {
    "command": "<command>",
    ...
  }
}
```

- `type`: always `publish`
- `uav_id`: drone/camera ID, default `1`
- `kind`: must be `telemetry`
- `metric`: must be `gimbal_control`
- `payload.command`: one of the supported commands

## Supported Commands

### set_angle

Set a target gimbal angle.

```json
{
  "type": "publish",
  "uav_id": 1,
  "kind": "telemetry",
  "metric": "gimbal_control",
  "payload": {
    "command": "set_angle",
    "pitch_deg": -30,
    "yaw_deg": 45,
    "speed_percent": 30,
    "mode": "angle",
    "source": "web_gimbal_control",
    "timestamp": "2026-06-15T10:00:00.000Z"
  }
}
```

`speed_percent` controls the gain used by the SDK; valid values are typically 1-100.

### gimbal_speed

Control gimbal motion continuously like a joystick.

```json
{
  "type": "publish",
  "uav_id": 1,
  "kind": "telemetry",
  "metric": "gimbal_control",
  "payload": {
    "command": "gimbal_speed",
    "yaw_speed": 20,
    "pitch_speed": -15,
    "source": "web_gimbal_control",
    "timestamp": "2026-06-17T10:00:00.000Z"
  }
}
```

- `yaw_speed`: -100..100, where negative and positive values set direction and magnitude.
- `pitch_speed`: -100..100, where negative and positive values set direction and magnitude.

Send repeated `gimbal_speed` updates while the joystick is moving, and send `yaw_speed: 0` and `pitch_speed: 0` when the joystick is released.

### zoom_in

```json
{
  "type": "publish",
  "uav_id": 1,
  "kind": "telemetry",
  "metric": "gimbal_control",
  "payload": {
    "command": "zoom_in",
    "source": "web_gimbal_control",
    "timestamp": "2026-06-15T10:00:00.000Z"
  }
}
```

### zoom_out

```json
{
  "type": "publish",
  "uav_id": 1,
  "kind": "telemetry",
  "metric": "gimbal_control",
  "payload": {
    "command": "zoom_out",
    "source": "web_gimbal_control",
    "timestamp": "2026-06-15T10:00:00.000Z"
  }
}
```

### zoom_hold

```json
{
  "type": "publish",
  "uav_id": 1,
  "kind": "telemetry",
  "metric": "gimbal_control",
  "payload": {
    "command": "zoom_hold",
    "source": "web_gimbal_control",
    "timestamp": "2026-06-15T10:00:00.000Z"
  }
}
```

### photo

```json
{
  "type": "publish",
  "uav_id": 1,
  "kind": "telemetry",
  "metric": "gimbal_control",
  "payload": {
    "command": "photo",
    "source": "web_gimbal_control",
    "timestamp": "2026-06-15T10:00:00.000Z"
  }
}
```

### record

```json
{
  "type": "publish",
  "uav_id": 1,
  "kind": "telemetry",
  "metric": "gimbal_control",
  "payload": {
    "command": "record",
    "source": "web_gimbal_control",
    "timestamp": "2026-06-15T10:00:00.000Z"
  }
}
```

### center

```json
{
  "type": "publish",
  "uav_id": 1,
  "kind": "telemetry",
  "metric": "gimbal_control",
  "payload": {
    "command": "center",
    "source": "web_gimbal_control",
    "timestamp": "2026-06-15T10:00:00.000Z"
  }
}
```

### status

Request camera status.

```json
{
  "type": "publish",
  "uav_id": 1,
  "kind": "telemetry",
  "metric": "gimbal_control",
  "payload": {
    "command": "status",
    "source": "web_gimbal_control",
    "timestamp": "2026-06-15T10:00:00.000Z"
  }
}
```

### follow_mode

Request follow mode.

```json
{
  "type": "publish",
  "uav_id": 1,
  "kind": "telemetry",
  "metric": "gimbal_control",
  "payload": {
    "command": "follow_mode",
    "source": "web_gimbal_control",
    "timestamp": "2026-06-15T10:00:00.000Z"
  }
}
```

## Example Testing Using `websocat`

Install `websocat` and use this command:

```bash
websocat ws://localhost:8765
```

Then paste a JSON payload such as `set_angle`.

## Example Python Test Client

```python
import json
import websocket

ws = websocket.create_connection("ws://localhost:8765")
request = {
    "type": "publish",
    "uav_id": 1,
    "kind": "telemetry",
    "metric": "gimbal_control",
    "payload": {
        "command": "set_angle",
        "pitch_deg": -30,
        "yaw_deg": 45,
        "speed_percent": 30,
        "mode": "angle",
        "source": "web_gimbal_control",
        "timestamp": "2026-06-15T10:00:00.000Z"
    }
}
ws.send(json.dumps(request))
print(ws.recv())
ws.close()
```

## Notes

- The script currently expects `metric` = `gimbal_control`.
- Unsupported commands return an error response.
- Responses are published back as `gimbal_control_response` payloads.
