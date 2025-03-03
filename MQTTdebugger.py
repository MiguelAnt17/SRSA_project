import paho.mqtt.client as mqtt
import time

GROUP_ID=14
MQTT_BROKER = "10.6.1.9"
MQTT_PORT = 1883
MQTT_TOPIC =f"{GROUP_ID}_ROOM_DATA"  # Adjust this to the topic used by the publisher

client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, message):
    print(f"{time.ctime()} - Topic: {message.topic} - Message: {message.payload.decode()}")

client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT)
client.loop_start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Program terminated")
    client.loop_stop()  # Safely stop the network loop
    client.disconnect()
