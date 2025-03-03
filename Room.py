import paho.mqtt.client as mqtt
import json
import random
import sys
import time
import threading

GROUP_ID = sys.argv[1]
TEMP_TIME = int(sys.argv[2])  
MOV_TIME = int(sys.argv[3])   
ROOM_NUMBER = 5

MQTT_BROKER = "10.6.1.9"
MQTT_PORT = 1883
MQTT_PATH = f"{GROUP_ID}_ROOM_DATA"
ACTUATORS = f"{GROUP_ID}_ACT"


running = True



room_data = {
    "temperature": 20.0,
    "humidity": 50,
    "motion": 0,
    "ac_working": 0,
    "hc_working": 0,
    "sensor_type": 1,
    "room_number": ROOM_NUMBER
}

client = mqtt.Client()

client.connect(MQTT_BROKER, MQTT_PORT, 60)

def celsius_to_fahrenheit(celsius):
    return (celsius * 9/5) + 32

def publish_sensor_data():
    global room_data
    while running:
        client.publish(MQTT_PATH, json.dumps(room_data))
        time.sleep(3) 

def update_sensor_data():
    global room_data
    while running:
        if room_data["ac_working"] == 0 and room_data["hc_working"] == 0:
            room_data["temperature"] += random.uniform(-0.75, 0.75)
            room_data["temperature"] = max(0, min(room_data["temperature"], 100))
            room_data["humidity"] += random.randint(-2, 2)
            room_data["humidity"] = max(0, min(room_data["humidity"], 100))
            if room_data["sensor_type"]==2:
                celsius_to_fahrenheit(room_data["temperature"])
        time.sleep(TEMP_TIME)




def simulate_motion():
    global room_data
    last_motion_time = time.time()
    
    while running:
        current_time = time.time()
        if (current_time - last_motion_time) >= MOV_TIME:
            room_data["motion"] = 1
            time.sleep(3)  
            room_data["motion"] = 0  
            last_motion_time = time.time()  
        time.sleep(0.1)  




def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe(ACTUATORS)


def adjust_temperature(ideal_temperature):
    global room_data
    while abs(room_data["temperature"] - ideal_temperature) > 0.5:
        if room_data["temperature"] < ideal_temperature:
            room_data["temperature"] += 0.5
        else:
            room_data["temperature"] -= 0.5
        print(f"Adjusting temperature to: {room_data['temperature']}")
    room_data["ac_working"] = 0

def adjust_humidity(ideal_humidity):
    global room_data
    while abs(room_data["humidity"] - ideal_humidity) > 5:
        if room_data["humidity"] < ideal_humidity:
            room_data["humidity"] += 5
        else:
            room_data["humidity"] -= 5
        print(f"Adjusting humidity to: {room_data['humidity']}")
        time.sleep(1)
    room_data["hc_working"] = 0

def on_message(client, userdata, msg):
    global room_data
    message = json.loads(msg.payload.decode())
    print(message)

    if 'ideal_temperature' in message:
            room_data["ac_working"] = 1
            time.sleep(3)
            print("ac func")
            ideal_temperature = message['ideal_temperature']
            adjust_temperature(ideal_temperature)
            print("ajustou")


    if 'ideal_humidity' in message:
            room_data["hc_working"] = 1
            time.sleep(3)
            print("hc func")
            ideal_humidity = message['ideal_humidity']
            adjust_humidity(ideal_humidity)
            print("ajustou")


client.on_connect = on_connect
client.on_message = on_message




client.loop_start()  

sensor_thread = threading.Thread(target=update_sensor_data)
motion_thread = threading.Thread(target=simulate_motion)
publish_thread = threading.Thread(target=publish_sensor_data)

sensor_thread.start()
motion_thread.start()
publish_thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Program terminated")
    running = False  
    sensor_thread.join()
    motion_thread.join()
    publish_thread.join()
    client.loop_stop()
    client.disconnect()  
