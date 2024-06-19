
from apscheduler.schedulers.background import BackgroundScheduler
from flask import jsonify
import requests
import time
import os
from dotenv import load_dotenv
from datetime import datetime
from pytz import timezone
from process import sign_s3_url
from eth_account import Account
from eth_account.messages import defunct_hash_message



load_dotenv()




def process_url(task_id):
    user_private_key = os.getenv('USER_PRIVATE_KEY')
    main_server = os.getenv('MAIN_SERVER')
    wallet = os.getenv('WALLET')
    api_url = f"{main_server}/taskInfo/{task_id}"
    headers = {"Content-Type": "application/json"}
    # Call taskInfo_endpoint function with retrieved taskId to get the s3 url
    try:
        print("Getting additional task info")
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            s3_url = data.get('s3_url')
            if not s3_url:
                print("s3_url not found in API response.")
                return {'error':'s3_url not found in API response.'}
        else:
            print(f"Failed to fetch data from API. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Request to API failed: {str(e)}")
    
    #passing the s3 url for signing to sign_s3_url
    is_valid, params = sign_s3_url(task_id,s3_url,user_private_key,wallet)

    # if the process was completed, calling the /confrim endpoint in the main function to confrim the task
    if is_valid:
        print("Sending verified task to backend")
        url = f"{main_server}/confirm"
        headers = {"Content-Type": "application/json"}
        try:
            # Make POST request to /confrim endpoint
            response = requests.post(url, json=params, headers=headers)
            # Check if request was successful (status code 200)
            if response.status_code == 200:
                return response.json()  
            else:
                return {'error': f'Request failed with status code {response.status_code}'}
        except requests.exceptions.RequestException as e:
            return {'error': f'Request failed: {str(e)}'}
    else:
        return jsonify({'error': 'Signature process failed'}), 500





def call_external_api():
    wallet = os.getenv('WALLET')
    main_server = os.getenv('MAIN_SERVER')
    api_url = f"{main_server}/task/{wallet}"
    headers = {"Content-Type": "application/json"}
    #calling the task endpoint and getting taskId 
    try:
        print("Calling the backend for active tasks")
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            task_id = data.get('task_id')
            if not task_id:
                print("No task assigned at the moment")
                return
            # Taskid passed to process_url() fucntion
            result = process_url(task_id)
            print(f"Result of the task: {result}")
        else:
            print(f"Failed to fetch data from API. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Request to API failed: {str(e)}")




def register_node():
    user_private_key = os.getenv('USER_PRIVATE_KEY')
    main_server = os.getenv('MAIN_SERVER')
    api_url = f"{main_server}/register"
    headers = {"Content-Type": "application/json"}
    token_id = os.getenv('NFT_TOKEN_ID')
    ip= os.getenv('IP')
    port = os.getenv('PORT')
    msghash = defunct_hash_message(text="\x19Ethereum Signed Message:\n32" + token_id)
    signedMesaage=Account.signHash(msghash,user_private_key)
    msghash=signedMesaage['messageHash'].hex()
    signature=signedMesaage['signature'].hex()
    v = signedMesaage['v']
    r = signedMesaage['r']
    s = signedMesaage['s']
    params = {
        'keyId':token_id,
        'messageHash':msghash,
        'v':hex(v),
        'r':hex(r),
        's':hex(s),
        'ip':ip,
        'port':port
    }
 
    try:
            # Make POST request to /confrim endpoint
            response = requests.post(api_url, json=params, headers=headers)
            # Check if request was successful (status code 200)
            if response.status_code == 200:
                return True 
            else:
                return False
    except requests.exceptions.RequestException as e:
            return {'error': f'Request failed: {str(e)}'}



if __name__ == '__main__':
    # Configure the scheduler with a timezone
    if register_node():
        print('Node regsitration successful')
    else:
         print('Node regsitration unsuccesful')
         exit()
    scheduler = BackgroundScheduler(timezone='UTC')
    # Add a job that calls the external API every minute to get the task
    scheduler.add_job(call_external_api, 'interval', minutes=0.5)
    print('Scheduler started. Press Ctrl+C to exit.')
    scheduler.start()
    # Keep the script running
    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        print("Exiting...")