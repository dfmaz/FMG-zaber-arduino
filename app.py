import streamlit as st
import serial
import time
from zaber_motion import Library
from zaber_motion.ascii import Connection
from zaber_motion import Units
from serial.tools import list_ports
import streamlit.components.v1 as components

# Initialize Zaber Motion Library
Library.enable_device_db_store()

# Initialize session state
if 'control_running' not in st.session_state:
    st.session_state.control_running = False
if 'initial_position' not in st.session_state:
    st.session_state.initial_position = None

    ##

def run_zaber_control(arduino_port, zaber_port, move_speed):
    try:
        # Set up serial connection to Arduino
        try:
            arduino = serial.Serial(arduino_port, 9600, timeout=1)
            st.success(f"Connected to Arduino on {arduino_port}")
        except serial.SerialException as e:
            if "PermissionError(13, 'Acceso denegado.', None, 5)" in str(e):
                st.error(f"Error: Could not open port '{arduino_port}'. The port might be in use by another application.")
                return
            else:
                raise  # Re-raise the exception if it's not the specific error we're looking for

        # Set up connection to Zaber device
        with Connection.open_serial_port(zaber_port) as connection:
            device = connection.detect_devices()[0]
            axis = device.get_axis(1)
            st.success(f"Connected to Zaber device on {zaber_port}")

            # Store initial position
            st.session_state.initial_position = axis.get_position()

            voltage_threshold = 4.0  # Threshold in volts
                                
            # Create a placeholder for voltage display
            voltage_placeholder = st.empty()

            while st.session_state.control_running:
                if arduino.in_waiting > 0:
                    data = arduino.readline().decode('utf-8').rstrip()
                
                    voltage = float(data)

                     # Update voltage display
                    voltage_placeholder.metric("Current Voltage", f"{voltage:.2f}V")

                    # Store initial position
                   # initial_position = axis.get_position()

                    if voltage < voltage_threshold:
                        #st.warning(f"Voltage below {voltage_threshold}V. Moving Zaber platform to limit.")
                        
                        # Set the speed
                        axis.settings.set('maxspeed', move_speed, Units.VELOCITY_MILLIMETRES_PER_SECOND)
                        
                        # Move to the positive limit
                        axis.move_min()
                        
                        #st.success("Platform has reached its limit.")
                        
                        # Wait for 5 seconds
                        #st.info("Waiting for 5 seconds before returning...")
                        
                        # Return to initial position
                        #st.info("Returning to initial position...")
                        #axis.move_absolute(initial_position)
                        #st.success("Platform has returned to initial position.")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
    finally:
        if 'arduino' in locals():
            arduino.close()
            st.info("Arduino connection closed")
        st.session_state.control_running = False

def start_control():
    st.session_state.control_running = True

def stop_control():
    st.session_state.control_running = False

def return_home(zaber_port):
    try:
        with Connection.open_serial_port(zaber_port) as connection:
            device = connection.detect_devices()[0]
            axis = device.get_axis(1)
            if st.session_state.initial_position is not None:
                st.info("Returning to home position...")
                axis.move_absolute(st.session_state.initial_position)
                while axis.is_busy():
                        time.sleep(0.1)
                st.success("Platform has returned to home position.")
            else:
                st.warning("Home position not set. Please start control first.")
    except Exception as e:
        st.error(f"An error occurred while returning home: {str(e)}")

def move_to_minimum(zaber_port):
    try:
        with Connection.open_serial_port(zaber_port) as connection:
            device = connection.detect_devices()[0]
            axis = device.get_axis(1)
            st.info("Moving to minimum position...")
            axis.move_max()
            while axis.is_busy():
                time.sleep(0.1)
            st.success("Platform has reached its minimum position.")
    except Exception as e:
        st.error(f"An error occurred while moving to minimum: {str(e)}")

def move_relative(zaber_port, distance):
    try:
        with Connection.open_serial_port(zaber_port) as connection:
            device = connection.detect_devices()[0]
            axis = device.get_axis(1)
            st.info(f"Moving {distance} mm relatively...")
            axis.move_relative(-distance, Units.LENGTH_MILLIMETRES)
            while axis.is_busy():
                time.sleep(0.1)
            st.success(f"Platform has moved {distance} mm.")
    except Exception as e:
        st.error(f"An error occurred during relative movement: {str(e)}")

# App layout
st.set_page_config(layout='wide')
st.title('Zaber Platform Control with Arduino 🤖')

with  st.sidebar:
    st.image('media/logo_about.png')

## Automatic Mode section
st.subheader("Auto Mode")

# Get list of available serial ports
available_ports = [port.device for port in list_ports.comports()]

# Text input for Arduino port
arduino_port = st.text_input("Enter Arduino Port", value="/dev/ttyACM0")

# Text input for Zaber port
zaber_port = st.text_input("Enter Zaber Port", value="/dev/ttyUSB0")

# Set  platform speed
move_speed = st.number_input("Platform Speed (mm/s)", value=10.0, min_value=0.1, max_value=700.0)

# Web Serial API JavaScript code
js_code = """
<script>
let port;
let reader;

async function connectSerial() {
    try {
        port = await navigator.serial.requestPort();
        await port.open({ baudRate: 9600 });
        
        const decoder = new TextDecoderStream();
        port.readable.pipeTo(decoder.writable);
        const inputStream = decoder.readable;
        reader = inputStream.getReader();
        
        document.getElementById('status').textContent = 'Connected';
        document.getElementById('disconnect').disabled = false;
        readSerialData();
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('status').textContent = 'Connection failed';
    }
}

async function disconnectSerial() {
    if (reader) {
        await reader.cancel();
        await port.close();
        document.getElementById('status').textContent = 'Disconnected';
        document.getElementById('disconnect').disabled = true;
    }
}

async function readSerialData() {
    while (true) {
        const { value, done } = await reader.read();
        if (value) {
            document.getElementById('serialData').textContent = value;
            // You can send this value back to Python using Streamlit's 
            // component communication mechanism if needed
        }
        if (done) {
            console.log('Serial port closed');
            reader.releaseLock();
            break;
        }
    }
}

async function writeSerialData(data) {
    const encoder = new TextEncoder();
    const writer = port.writable.getWriter();
    await writer.write(encoder.encode(data));
    writer.releaseLock();
}
</script>

<button onclick="connectSerial()">Connect Serial</button>
<button id="disconnect" onclick="disconnectSerial()" disabled>Disconnect</button>
<p>Status: <span id="status">Not connected</span></p>
<p>Serial Data: <span id="serialData"></span></p>
<input type="text" id="sendData" placeholder="Data to send">
<button onclick="writeSerialData(document.getElementById('sendData').value)">Send</button>
"""

# Embed the JavaScript code
components.html(js_code, height=200)

# Create two columns for auto mode buttons
col1, col2 = st.columns(2)

with col1:
    if st.button("Start Control", on_click=start_control, disabled=st.session_state.control_running):
        st.write("Control started")

with col2:
    if st.button("Stop Control", on_click=stop_control, disabled=not st.session_state.control_running):
        st.write("Control stopped")

## Manual Mode section
st.subheader("Manual Mode")
st.write("Use these controls when the automatic control is stopped.")

# Create three columns for manual mode buttons
col3, col4, col5 = st.columns(3)

with col3:
    if st.button("Return Home", on_click=lambda: return_home(zaber_port), disabled=st.session_state.control_running):
        st.write("Returning to home position")

with col4:
    if st.button("Move to Minimum", on_click=lambda: move_to_minimum(zaber_port), disabled=st.session_state.control_running):
        st.write("Moving to minimum position")

# Relative movement input and button
with col5:
    relative_distance = st.number_input("Relative Move (mm)", value=0.0, step=0.1)
    if st.button("Move Relative", on_click=lambda: move_relative(zaber_port, relative_distance), disabled=st.session_state.control_running):
        st.write(f"Moving {relative_distance} mm relatively")

if st.session_state.control_running:
    run_zaber_control(arduino_port, zaber_port, move_speed)

# Footer section
# Centered footer section
st.markdown("""
---
<div style="text-align: center;">
    <strong>2024 © <a href="https://mfluidosunex.es/" target="_blank">FMG Uex</a> — All rights reserved.</strong><br>
    <a href="https://github.com/dfmaz/FMG-zaber-arduino/tree/main" target="_blank">
        <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="GitHub Logo" style="height: 20px; width: 20px;"/>
    </a>
</div>
""", unsafe_allow_html=True)