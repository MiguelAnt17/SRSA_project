import configparser
from datetime import datetime
import json
import random
import time
import socket
from influxdb_client_3 import InfluxDBClient3
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import threading

#from influxdb_client import Point, WritePrecision
#from influxdb_client.client.write_api import SYNCHRONOUS



config = configparser.ConfigParser()
config.read('ideal.cfg')

temp_low = config.getfloat('ideal_conditions', 'min_temperature')
temp_hi = config.getfloat('ideal_conditions', 'max_temperature')
temp_ideal = config.getfloat('ideal_conditions', 'ideal_temperature')
hum_low = config.getfloat('ideal_conditions', 'min_humidity')
hum_hi = config.getfloat('ideal_conditions', 'max_humidity')
hum_ideal = config.getfloat('ideal_conditions', 'ideal_humidity')

last_data_received = {}

motion_alarm_enabled = False

device_start_time = {"air_conditioner": None, "humidity_controller": None}

device_total_on_time = 0

device_power_consumption = {"air_conditioner": 3000, "humidity_controller": 1000}

check_data_thread_started = False

energy_cost_per_kWh=0.15


GROUP_ID = "14"
MQTT_BROKER = "10.6.1.9"
MQTT_PORT = 1883
MQTT_PATH = f"{GROUP_ID}_ROOM_DATA"
OTHER_ROOMS = "OTHER_ROOMS"

TCP_ADDRESS = "localhost"  
TCP_PORT = 12345

ClientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    ClientSocket.connect((TCP_ADDRESS, int(TCP_PORT)))
except socket.error as e:
    print(str(e))


host="https://eu-central-1-1.aws.cloud2.influxdata.com"
token="wz0vCkwJOVt0Hi1cf7VdygVXcFV_WZjDQq85WHXy7q8OfFKgkN54KG3TZbe4pzJKdtTX9iHMqIxTixZnYX-MfA=="
org="Example1"
database="SRSA"

clientdb = InfluxDBClient(host=host,token=token,org=org,database=database) 





def check_missing_data():
    while True:
        current_time = time.time()
        for room_number, last_received_time in last_data_received.items():
            if current_time - last_received_time > 15:  
                alarm_message = {"room_number": room_number, "event": "No data received for 15 seconds"}
                send_alarm_to_control_central(alarm_message)
                
                try:
                    #write_in_database_events(alarm_message["event"])
                    print("Event stored in database:", alarm_message)
                except Exception as e:
                    print("An error occurred while writing event to database:", e)
                
                del last_data_received[room_number]
        time.sleep(1) 


def start_background_thread():
    thread = threading.Thread(target=check_missing_data)
    thread.daemon = True  # Configure the thread as a daemon
    thread.start()

def on_connect(client, userdata, flags, rc):
    global check_data_thread_started
    print("Connected to MQTT Broker with result code "+str(rc))
    client.subscribe(MQTT_PATH)
    client.subscribe(OTHER_ROOMS)

def wrtite_in_database(dados):
        p = Point("normal_data").field("temperature", float(dados["temperature"])).field("humidity",float(dados["humidity"])).field("motion",dados["motion"]).field("ac_working",dados["ac_working"]).field("hc_working",dados["hc_working"]).field("sensor_type",dados["sensor_type"]).field("roo_number",dados["room_number"]).time(datetime.datetime.now(datetime.timezone.utc))
        print(f"VALORES INSERIDOS: "," temperature=",dados["temperature"],
            "\nhumidity=",dados["humidity"],
            "\nmotion=",dados["motion"],
            "\nac_working=",dados["ac_working"],
            "\nhc_working=",dados["hc_working"],
            "\nsensor_type=",dados["sensor_type"],
            "\nroom_number=",dados["room_number"])
        
        client.write(p)


def write_in_database_events(descricao):
    p = Point("eventos").field("evento", descricao).time(datetime.datetime.now(datetime.timezone.utc))
    print(f"VALORES INSERIDOS: ", "evento", descricao)
    client.write(p)

def fahrenheit_to_celsius(fahrenheit):
    return (fahrenheit - 32) / 1.8


def on_message(client, userdata, msg):
    global motion_alarm_enabled
    global check_data_thread_started
    payload = msg.payload.decode()
    

    
    room_number = data["room_number"]
    if room_number:
        last_data_received[room_number] = time.time()

    
    if not check_data_thread_started:
        thread = threading.Thread(target=check_missing_data)
        thread.daemon = True
        thread.start()
        check_data_thread_started = True
        print("Background data checking thread started.")
    if msg.topic == MQTT_PATH:
        try:
            data = json.loads(payload)
            room_number = data["room_number"]
            temperature = data["temperature"]
            humidity = data["humidity"]
            ac_working = data["ac_working"]
            hc_working = data["hc_working"]


            sensor_type = data["sensor_type"]
            
            
            if sensor_type == 2:
                conver=fahrenheit_to_celsius(temperature)
                temperature=conver
            if sensor_type not in [1, 2]:
                alarm_message = {"room_number": room_number, 'event': "Bad sensors"}
                send_alarm_to_control_central(alarm_message)
                write_in_database_events(alarm_message["event"])
                return

            if temperature < temp_low or temperature > temp_hi:
                print("Sensor values outside healthy intervals")
                alarm_message = {"message":"Sensor values outside healthy intervals" ,"room_number": room_number, "temperature": temperature, "ideal_temperature": temp_ideal, "ac_working": ac_working, "hc_working": hc_working}
                send_alarm_to_control_central(alarm_message)
                wrtite_in_database(data)
                return

            if humidity < hum_low or humidity > hum_hi:
                alarm_message = {"message":"Sensor values outside healthy intervals","room_number": room_number, "humidity": humidity, "ideal_humidity": hum_ideal,  "ac_working": ac_working, "hc_working": hc_working}
                send_alarm_to_control_central(alarm_message)
                wrtite_in_database(data)
                return
                
            if motion_alarm_enabled == True and data["motion"] == 1:
                alarm_message = {"room_number": room_number, "event": "Motion detected"}
                send_alarm_to_control_central(alarm_message)
                write_in_database_events(alarm_message["event"])
                return
                
            
            if ac_working==1 or hc_working==1:
                process_device_status_change(data)

            wrtite_in_database(data)
                
        except json.JSONDecodeError:
            command = payload.strip()  
            print("Received command from Alarm Console:", command)
        
            if command == "on":
                event = "Motion alarms switched ON"
                motion_alarm_enabled = True
            else:
                event = "Motion alarms switched OFF"
                motion_alarm_enabled= False
                
            alarm_message = {"event": event}
            send_alarm_to_control_central(alarm_message)

            write_in_database_events(alarm_message["event"])
    
    if msg.topic==OTHER_ROOMS:
        data = json.loads(payload)
        room_number = data["room_number"]
        temperature = data["temperature"]
        humidity = data["humidity"]
        ac_working = data["ac_working"]
        hc_working = data["hc_working"]


        sensor_type = data["sensor_type"]
        if sensor_type == 2:
            temperature = (temperature - 32) / 1.8      
                
        if sensor_type not in [1, 2]:
            alarm_message = {"room_number": room_number, "event": "Bad sensors para tópico OTHERS_ACT"}
            send_alarm_to_control_central(alarm_message)
            write_in_database_events(alarm_message["event"])
            return

        if temperature < temp_low or temperature > temp_hi:
            print("Sensor values outside healthy intervals")
            alarm_message = {"message":"ALTERAR TEMP OTHER_ACT" ,"room_number": room_number, "temperature": temperature, "ideal_temperature": temp_ideal, "ac_working": ac_working, "hc_working": hc_working}
            send_alarm_to_control_central(alarm_message)
            wrtite_in_database(data)
            return

        if humidity < hum_low or humidity > hum_hi:
            alarm_message = {"message":"ALTERAR HUM OTHER_ACT","room_number": room_number, "humidity": humidity, "ideal_humidity": hum_ideal,  "ac_working": ac_working, "hc_working": hc_working}
            send_alarm_to_control_central(alarm_message)
            wrtite_in_database(data)
            return
                
        if motion_alarm_enabled == True and data["motion"] == 1:
            alarm_message = {"room_number": room_number, "event": "Motion detected para tópico OTHERS_ACT"}
            send_alarm_to_control_central(alarm_message)
            write_in_database_events(alarm_message["event"])
            return
            
        wrtite_in_database(data)




def process_device_status_change(data):
    global device_start_time, device_total_on_time, device_power_consumption, energy_cost_per_kWh
    if "ac_working" in data:
        ac_status = data["ac_working"]
        device = "air_conditioner"
        handle_device_status_change(device, ac_status)
    
    if "hc_working" in data:
        hc_status = data["hc_working"]
        device = "humidity_controller"
        handle_device_status_change(device, hc_status)

def handle_device_status_change(device, status):
    global device_start_time, device_total_on_time, device_power_consumption, energy_cost_per_kWh
    
    if status == 1:  
        if device_start_time[device] is None:
            device_start_time[device] = time.time() 
    elif status == 0: 
        if device_start_time[device] is not None:
            end_time = time.time()
            duration_seconds = end_time - device_start_time[device]
            device_total_on_time += duration_seconds  
            device_start_time[device] = None  
            
     
            energy_consumption_kWh = (device_power_consumption[device] * duration_seconds) / 3600.0  
            energy_cost = energy_consumption_kWh * energy_cost_per_kWh
            print(f"Energy cost for {device}: ${energy_cost:.2f}")
            
            point = Point("EnergyUsage").field("energy_cost", energy_cost).time(datetime.datetime.now(datetime.timezone.utc))
            try:
                client.write(point)
                print(f"Written to database: {device} used {energy_consumption_kWh:.2f} kWh costing ${energy_cost:.2f}")
            except Exception as e:
                print(f"Failed to write to database: {str(e)}")
            
            
            



def send_alarm_to_control_central(alarm_message):
    global ClientSocket, TCP_ADDRESS, TCP_PORT  
    try:
       
        message_to_send = json.dumps(alarm_message) + '\n'
        ClientSocket.sendall(message_to_send.encode("UTF-8"))
        print("Alarm sent to Control Central:", alarm_message)
    except socket.error as e:
        print(f"Socket error occurred: {e}, attempting to reconnect.")
        try:
            ClientSocket.close()
        except socket.error:
            pass  
        try:
            ClientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ClientSocket.connect((TCP_ADDRESS, TCP_PORT))
            ClientSocket.sendall(message_to_send.encode("UTF-8"))  
        except socket.error as se:
            print("Failed to reconnect:", se)
    except Exception as e:
        print("An error occurred while sending alarm to Control Central:", e)










client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)



client.loop_forever()

