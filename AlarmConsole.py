import paho.mqtt.client as mqtt

GROUP_ID = "14"
MQTT_SERVER = "10.6.1.9"
MQTT_PATH = f"{GROUP_ID}_ROOM_DATA"

client = mqtt.Client()
client.connect(MQTT_SERVER, 1883)

while True:
    command = input("Enter a command (on/off): ")
    if command == "on" or command == "off":
        client.publish(MQTT_PATH, command)  
    else:
        print("Invalid Command")
    
