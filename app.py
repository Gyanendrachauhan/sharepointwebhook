import os,json
import requests
from flask import Flask, jsonify,request
from dotenv import load_dotenv


app = Flask(__name__)

load_dotenv()
# Replace these variables with your actual values
client_id = os.getenv('client_id')
client_secret = os.getenv('client_secret')
tenant_id = os.getenv('tenant_id')
resource = os.getenv('resource')
site_id = os.getenv('site_id')

base_url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items'

def get_access_token():
    url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    body = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': resource + '/.default'
    }
    response = requests.post(url, headers=headers, data=body)
    if response.status_code == 200:
        return response.json().get('access_token')

    else:
        return None

def download_pdf_files(folder_id, folder_name, access_token):
    all_files = []  # List to store all files and folders from SharePoint

    url = f'{base_url}/{folder_id}/children'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return f"Failed to list items in folder {folder_name}. Status Code: {response.status_code}", []

    for item in response.json().get('value', []):
        all_files.append(os.path.join(folder_name, item['name']))  # Add item to all_files list

        if 'folder' in item:
            _, child_files = download_pdf_files(item['id'], os.path.join(folder_name, item['name']), access_token)
            all_files.extend(child_files)  # Extend the main list with child files/folders
        elif 'file' in item and item['name'].endswith('.pdf'):
            local_file_path = os.path.join('local_directory', folder_name, item['name'])

            if not os.path.exists(local_file_path):
                file_url = f'{base_url}/{item["id"]}/content'
                file_response = requests.get(file_url, headers=headers, stream=True)

                if file_response.status_code != 200:
                    return f"Failed to download file {item['name']}. Status Code: {file_response.status_code}", all_files
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                with open(local_file_path, 'wb') as local_file:
                    for chunk in file_response.iter_content(chunk_size=1024):
                        if chunk:
                            local_file.write(chunk)

    return "Download successful!", all_files

def clean_local_directory(all_files):
    root_directory_path = r'C:\Users\Gyani\PycharmProjects\pythonProject34\local_directory'
    for foldername, _, filenames in os.walk(root_directory_path):
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(foldername, filename), root_directory_path)
            if rel_path not in all_files:
                os.remove(os.path.join(foldername, filename))


@app.route('/download-and-upload-pdfs', methods=['GET'])
def upload_pdfs_to_server():
    filename_req = request.args.get("filename")
    print((filename_req))
    access_token = get_access_token()
    if not access_token:
        return jsonify({"error": "Failed to retrieve access token"}), 401
    result = download_pdf_files('root', '', access_token)
    root_directory_path = r'C:\Users\Gyani\PycharmProjects\pythonProject34\local_directory'

    # Initialize a list to store file tuples for the POST request
    files_list = []

    # Walk through the directory tree and collect all PDF files
    for foldername, _, filenames in os.walk(root_directory_path):
        for filename in filenames:
            if filename.endswith('.pdf'):
                if filename==filename_req:
                    file_path = os.path.join(foldername, filename)
                    files_list.append(('pdf_docs', (filename, open(file_path, 'rb'), 'application/pdf')))

    url = "http://127.0.0.1:5001/llm-pdf/upload"
    payload = {'email': 'vivek@gmail.com'}

    # Send the POST request with the files
    upload_response = requests.post(url, data=payload, files=files_list)

    # Close the file objects after the request is made
    for _, (_, file, _) in files_list:
        file.close()

    # Ensure the upload was successful before proceeding
    if upload_response.status_code != 200:
        return jsonify(
            {"error": "Failed to upload PDFs", "response": upload_response.text}), upload_response.status_code

    return jsonify({"message": "PDFs uploaded successfully"})

@app.route('/send-message', methods=['GET','POST'])
def send_message_to_server(question='what is STEF agent'):
    url = "http://127.0.0.1:5001/llm-pdf/message"
    payload = {'question': '{"content":{"message": "' +question+ '"}}','email': 'vivek@gmail.com'}
    headers = {}
    response = requests.post(url, headers=headers, data=payload)
    print(response.status_code)  # Check the status code
    print(response.text)
    return response.json()


if __name__ == '__main__':
    app.run(debug=True)
