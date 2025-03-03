import socket
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# MQTT setup
MQTT_BROKER = "10.6.1.9"
MQTT_PORT = 1883
GROUP_ID = "14"

mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT Broker with result code "+str(rc))

mqtt_client.on_connect = on_connect

# TCP server setup
TCP_HOST = "localhost"
TCP_PORT = 12345
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((TCP_HOST, TCP_PORT))
server_socket.listen(5)
print("Control Central is listening for alarms...")

def send_control_message(room_number, control_data):
    """Send control message to specific room using MQTT."""
    topic = f"{GROUP_ID}_ACT"
    mqtt_client.publish(topic, json.dumps(control_data))
    print(f"Sent control command to room {room_number}: {control_data}")


def send_control_message_act(room_number, control_data):
    """Send control message to specific room using MQTT."""
    topic = "OTHER_ACT"
    mqtt_client.publish(topic, json.dumps(control_data))
    print(f"Sent control command to room {room_number}: {control_data}")

def handle_events(alarm_data):
    
    message = alarm_data.get('message')
    event = alarm_data.get('event')

    if message == "ALTERAR TEMP OTHER_ACT":
        process_temperature(alarm_data)
        return

    if message == "ALTERAR HUM OTHER_ACT":
        process_humidity(alarm_data)
        return

    if event:
        process_events(alarm_data)
        return

    if 'temperature' in alarm_data:
        process_temperature(alarm_data)
        return

    if 'humidity' in alarm_data:
        process_humidity(alarm_data)
        return


def process_events(alarm_data):
    event_type = alarm_data['event']
    room_number = alarm_data.get('room_number', 'unknown')
    if event_type == "Motion alarms switched OFF":
        print(f"Motion Alarm OFF: Room {room_number}")
        send_control_message(room_number, {'event': 'off'})
    elif event_type == "Motion alarms switched ON":
        print(f"Motion Alarm ON: Room {room_number}")
        send_control_message(room_number, {'event': 'on'})
    elif event_type == "No data received for 15 seconds":
        print(f"Disconnection Alarm: Room {room_number} has not sent data for 15 seconds.")
        send_control_message(room_number, {'event': 'check_connection'})
    elif event_type == "Bad sensors":
        print(f"Bad Sensors: Room {room_number}")
        send_control_message(room_number, {'event': 'bad_sensors'})
    if event_type == "Bad sensors para tópico OTHERS_ACT":
        print(f"Bad Sensors: Room {room_number}")
        send_control_message_act(room_number, {'event': 'bad_sensors'})
    elif event_type == "No data received for 15 seconds para o tópico OTHER_ACT":
        print(f"Disconnection Alarm: Room {room_number} has not sent data for 15 seconds.")
        send_control_message_act(room_number, {'event': 'check_connection'})


def process_temperature(alarm_data):
    room_number = alarm_data['room_number']
    actual_temp = alarm_data['temperature']
    ideal_temp = alarm_data['ideal_temperature']
    if actual_temp > ideal_temp:
        if room_number!=5:
            send_control_message_act(room_number,{"room_number":room_number,"ac_switch_on":1,"hc_switch_on":0,"temperature_ideal":ideal_temp,"ideal_humidity":50})
        else:
            send_control_message(room_number, {'action': 'cool', 'ideal_temperature': ideal_temp})
            print(f"Temperature too high. Cooling down. Room {room_number}")
    elif actual_temp < ideal_temp:
        if room_number!=5:
            send_control_message_act(room_number,{"room_number":room_number,"ac_switch_on":1,"hc_switch_on":0,"temperature_ideal":ideal_temp,"ideal_humidity":50})
        else:
            send_control_message(room_number, {'action': 'heat', 'ideal_temperature': ideal_temp})
            print(f"Temperature too low. Heating up. Room {room_number}")

def process_humidity(alarm_data):
    room_number = alarm_data['room_number']
    actual_humidity = alarm_data['humidity']
    ideal_humidity = alarm_data['ideal_humidity']
    if actual_humidity > ideal_humidity:
        if room_number!=5:
            send_control_message_act(room_number,{"room_number":room_number,"ac_switch_on":0,"hc_switch_on":1,"temperature_ideal":23,"ideal_humidity":ideal_humidity})
        else:
            send_control_message(room_number, {'action': 'dehumidify', 'ideal_humidity': ideal_humidity})
            print(f"Humidity too high. Dehumidifying. Room {room_number}")
    elif actual_humidity < ideal_humidity:
        if room_number!=5:
            send_control_message_act(room_number,{"room_number":room_number,"ac_switch_on":0,"hc_switch_on":1,"temperature_ideal":23,"ideal_humidity":ideal_humidity})
        else:
            send_control_message(room_number, {'action': 'humidify', 'ideal_humidity': ideal_humidity})
            print(f"Humidity too low. Humidifying. Room {room_number}")





def receive_complete_message(client_socket):
    """Receive complete messages split by newline character as delimiter."""
    buffer = ""
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break  
            buffer += data
            while '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                return message.strip()
    except Exception as e:
        print(f"Error receiving data: {e}")
    return buffer.strip() if buffer else None

try:
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Received connection from {addr}")

        while True:
            data = receive_complete_message(client_socket)
            if not data:
                break  

            try:
                alarm_data = json.loads(data)
                print("Alarm Data:", alarm_data)
                
                handle_events(alarm_data)

            except json.JSONDecodeError as e:
                print(f"JSON decoding failed: {e} - Data: {data}")

        client_socket.close()
except KeyboardInterrupt:
    print("Server is shutting down.")
    server_socket.close()
    mqtt_client.loop_stop()

