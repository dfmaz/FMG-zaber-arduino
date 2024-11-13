import streamlit as st
import serial
import time
from zaber_motion import Library
from zaber_motion.ascii import Connection
from zaber_motion import Units
from serial.tools import list_ports
import streamlit.components.v1 as components
import json

# Initialize session state
if 'control_running' not in st.session_state:
    st.session_state.control_running = False
if 'initial_position' not in st.session_state:
    st.session_state.initial_position = None
if 'current_voltage' not in st.session_state:
    st.session_state.current_voltage = 0

# Update the title with an Arduino emoji
st.title("Zaber Platform Control with Arduino 🤖")

# Web Serial API JavaScript code
js_code = """
<script>
let port;
let reader;
let writer;

async function connectSerial() {
    try {
        port = await navigator.serial.requestPort();
        await port.open({ baudRate: 9600 });
        
        const decoder = new TextDecoderStream();
        port.readable.pipeTo(decoder.writable);
        const inputStream = decoder.readable;
        reader = inputStream.getReader();
        
        const encoder = new TextEncoderStream();
        encoder.readable.pipeTo(port.writable);
        writer = encoder.writable.getWriter();
        
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
            // Send data to Streamlit
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: value
            }, '*');
        }
        if (done) {
            console.log('Serial port closed');
            reader.releaseLock();
            break;
        }
    }
}

async function writeSerialData(data) {
    await writer.write(data);
}

window.writeSerialData = writeSerialData;
</script>

<button onclick="connectSerial()">Connect Serial</button>
<button id="disconnect" onclick="disconnectSerial()" disabled>Disconnect</button>
<p>Status: <span id="status">Not connected</span></p>
<p>Serial Data: <span id="serialData"></span></p>
"""

# Embed the JavaScript code
serial_component = components.html(js_code, height=200)

# Function to send command to Arduino
def send_command(command):
    js_code = f"writeSerialData('{command}');"
    components.html(f"<script>{js_code}</script>", height=0)

# Function to process received data
def process_data(data):
    try:
        voltage = float(data)
        st.session_state.current_voltage = voltage
        return voltage
    except ValueError:
        return None

# Check for new data from serial component
if serial_component:
    voltage = process_data(serial_component)
    if voltage is not None:
        st.write(f"Current Voltage: {voltage:.2f}V")

# Platform control logic
def control_platform():
    voltage_threshold = 4.0
    while st.session_state.control_running:
        if st.session_state.current_voltage < voltage_threshold:
            st.warning(f"Voltage below {voltage_threshold}V. Moving Zaber platform to limit.")
            send_command("MOVE_MAX")
            st.success("Platform has reached its limit.")
            st.info("Waiting for 5 seconds before returning...")
            st.sleep(5)
            st.info("Returning to initial position...")
            send_command("MOVE_HOME")
            st.success("Platform has returned to initial position.")
        st.sleep(0.1)

# Create two columns for Start and Stop buttons
col1, col2 = st.columns(2)

with col1:
    if st.button("Start Control", disabled=st.session_state.control_running):
        st.session_state.control_running = True
        control_platform()

with col2:
    if st.button("Stop Control", disabled=not st.session_state.control_running):
        st.session_state.control_running = False

# Manual Mode section
st.header("Manual Mode")
st.write("Use these controls when the automatic control is stopped.")

# Create three columns for manual mode buttons
col3, col4, col5 = st.columns(3)

with col3:
    if st.button("Return Home", disabled=st.session_state.control_running):
        send_command("MOVE_HOME")

with col4:
    if st.button("Move to Minimum", disabled=st.session_state.control_running):
        send_command("MOVE_MIN")

# Relative movement input and button
with col5:
    relative_distance = st.number_input("Relative Move (mm)", value=0.0, step=0.1)
    if st.button("Move Relative", disabled=st.session_state.control_running):
        send_command(f"MOVE_REL {relative_distance}")

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