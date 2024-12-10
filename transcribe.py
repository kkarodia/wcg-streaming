import argparse
import base64
import configparser
import json
import threading
import time
import os
import sys
import requests

import sounddevice as sd
import numpy as np
import websocket
from websocket._abnf import ABNF
from flask import Flask, render_template, Response, jsonify, send_from_directory
import queue
import ssl

app = Flask(__name__, static_folder='static')

CHUNK = 1024
CHANNELS = 1
RATE = 44100
FINALS = []
LAST = None

# N8N Webhook URL
N8N_WEBHOOK_URL = "https://kkarodia.app.n8n.cloud/webhook-test/eb567b24-6461-4e58-b761-746ccf6b52ea"

REGION_MAP = {
    'us-east': 'us-east.speech-to-text.watson.cloud.ibm.com',
    'us-south': 'us-south.speech-to-text.watson.cloud.ibm.com',
    'eu-gb': 'eu-gb.speech-to-text.watson.cloud.ibm.com',
    'eu-de': 'eu-de.speech-to-text.watson.cloud.ibm.com',
    'au-syd': 'au-syd.speech-to-text.watson.cloud.ibm.com',
    'jp-tok': 'jp-tok.speech-to-text.watson.cloud.ibm.com',
}

transcription_queue = queue.Queue()
final_transcript = []
is_transcribing = False
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

try:
    # Dummy driver for headless environment
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    logging.info("Set SDL_AUDIODRIVER to dummy.")

    # Initialize sounddevice
    logging.info("Querying sound devices...")
    print(sd.query_devices())  # This should show available devices
    logging.info("Sounddevice initialized successfully.")

    # Your main app logic here
    logging.info("Starting main application...")
    # Example: app.run()
except Exception as e:
    logging.error("Application failed to start.", exc_info=True)
    raise e
def send_transcript_to_webhook(transcript):
    """
    Send the transcript to the N8N webhook
    
    :param transcript: The full transcript text
    :return: Response from the webhook
    """
    try:
        # Prepare the payload
        payload = {
            "transcript": transcript,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Send POST request to webhook
        headers = {"Content-Type": "application/json"}
        response = requests.post(N8N_WEBHOOK_URL, 
                                 data=json.dumps(payload), 
                                 headers=headers)
        
        print(f"Webhook response status: {response.status_code}")
        print(f"Webhook response: {response.text}")
        
        return response
    except Exception as e:
        print(f"Error sending transcript to webhook: {e}")
        return None

def read_audio(ws):
    global RATE, is_transcribing
    
    # Detect the default sample rate
    RATE = int(sd.default.samplerate)
    
    def audio_callback(indata, frames, time, status):
        if status:
            print(status)
        
        # Convert numpy array to bytes
        data = indata.tobytes()
        
        try:
            ws.send(data, ABNF.OPCODE_BINARY)
        except websocket.WebSocketConnectionClosedException:
            print("WebSocket connection closed unexpectedly")
        except ssl.SSLError as e:
            print(f"SSL Error occurred: {e}")
        except Exception as e:
            print(f"An error occurred while sending audio data: {e}")

    try:
        with sd.InputStream(callback=audio_callback, 
                            channels=CHANNELS, 
                            samplerate=RATE,
                            dtype='int16'):
            while is_transcribing:
                time.sleep(0.1)
    except Exception as e:
        print(f"Error in audio input stream: {e}")

    try:
        data = {"action": "stop"}
        ws.send(json.dumps(data).encode('utf8'))
    except:
        print("Failed to send stop action")

    time.sleep(1)
    try:
        ws.close()
    except:
        print("Failed to close WebSocket")

def on_message(ws, msg):
    global final_transcript
    data = json.loads(msg)
    if "results" in data:
        transcript = data['results'][0]['alternatives'][0]['transcript']
        print(transcript)
        transcription_queue.put(transcript)
        if data["results"][0]["final"]:
            final_transcript.append(transcript)

def on_error(ws, error):
    print(f"Error occurred: {error}")

def on_close(ws, close_status_code, close_msg):
    global is_transcribing
    is_transcribing = False
    print(f"WebSocket closed. Status code: {close_status_code}. Close message: {close_msg}")

def on_open(ws):
    global is_transcribing
    is_transcribing = True
    print("WebSocket opened")
    data = {
        "action": "start",
        "content-type": f"audio/l16;rate={RATE}",
        "continuous": True,
        "interim_results": True,
        "word_confidence": True,
        "timestamps": True,
        "max_alternatives": 3
    }
    ws.send(json.dumps(data).encode('utf8'))
    threading.Thread(target=read_audio, args=(ws,)).start()

def get_url():
    host = REGION_MAP["us-south"]
    return (f"wss://api.{host}/instances/c68822b4-6c19-4501-8840-c51fd7cbbb36/v1/recognize"
            "?model=en-US_BroadbandModel")

def get_auth():
    apikey = "I9meB5ym-hSrrNCps6CvSyh_aFlDMNfj1k7497B7MeHf"
    return ("apikey", apikey)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/start_transcription')
def start_transcription():
    global is_transcribing, final_transcript
    is_transcribing = True
    final_transcript = []  # Reset final transcript

    def generate():
        headers = {}
        userpass = ":".join(get_auth())
        headers["Authorization"] = "Basic " + base64.b64encode(userpass.encode()).decode()
        url = get_url()

        ws = websocket.WebSocketApp(url,
                                    header=headers,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
        ws.on_open = on_open
        
        wst = threading.Thread(target=ws.run_forever, kwargs={"sslopt": {"cert_reqs": ssl.CERT_NONE}})
        wst.daemon = True
        wst.start()

        while is_transcribing:
            try:
                transcript = transcription_queue.get(timeout=1)
                yield f"data: {transcript}\n\n"
            except queue.Empty:
                pass

    return Response(generate(), mimetype='text/event-stream')

@app.route('/stop_transcription')
def stop_transcription():
    global is_transcribing, final_transcript
    is_transcribing = False
    
    # Send final transcript to webhook when stopping
    if final_transcript:
        full_transcript = " ".join(final_transcript)
        send_transcript_to_webhook(full_transcript)
    
    return jsonify({"status": "Transcription stopped"})

@app.route('/get_final_transcript')
def get_final_transcript():
    global final_transcript
    transcript = " ".join(final_transcript)
    return jsonify({"transcript": transcript})

@app.route('/clear_transcript')
def clear_transcript():
    global final_transcript
    final_transcript = []
    return jsonify({"status": "Transcript cleared"})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
