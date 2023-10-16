from flask import Flask, request,jsonify
import json,os,requests
from app import send_message_to_server,download_pdf_files,get_access_token,clean_local_directory



app = Flask(__name__)




@app.route("/ping", methods=['GET'])
def ping():
    return "Getting response from Entab Webhook server"


@app.route("/webhook", methods=['POST'])
def webhook():
    access_token = get_access_token()

    if not access_token:
        print("Failed to retrieve access token.")
        exit()

    folder_id = "root"
    folder_name = ""

    result, all_files = download_pdf_files(folder_id, folder_name, access_token)
    clean_local_directory(all_files)
    print(result)
    payload = request.form
    data = payload['intent']
    data1 = json.loads(data)
    action = data1['fulfillment']['action']
    parameters = data1['fulfillment']['parameters']

    if action =="action-category-question":
        question = parameters['question']
        print(question)
        x = send_message_to_server(question=question)
        print(x)
        c = {"message": f"{x['content']['message']}", "id": 40, "userInput": True, "trigger": 400}
        c1 = json.dumps(c)
        return c1

    elif action == "action-category-faq-ma":
        # Present the list of filenames
        root_directory_path = r'C:\Users\Gyani\PycharmProjects\pythonProject34\local_directory'
        filenames = [filename for foldername, _, filenames in os.walk(root_directory_path)
                     for filename in filenames if filename.endswith('.pdf')]

        buttons = [{"value": filename, "label": filename, "trigger": 3020} for filename in filenames]

        return jsonify({
            "id": 302,
            "message": "Please select a file to upload:",
            "metadata": {
                "payload": buttons,
                "templateId": 6
            },
            "fulfillment": {
                "action": "action-category-faq-ma",
                "parameters": {},
                "previousIntent": 30
            },
            "userInput": False
        })

    elif action == "action-category-faq-ma-ans":
        selected_filename = parameters['faqans'].replace('{previousValue:', '').replace('}', '')

        # Trigger the upload for the selected file
        response = requests.get(f"http://127.0.0.1:5000/download-and-upload-pdfs?filename={selected_filename}")

        if response.status_code == 200:
            return jsonify({
                "id": 3020,
                "message": f"{selected_filename} uploaded successfully",
                "metadata": {
                    "payload": [{
                        "image": "https://img.icons8.com/flat-round/2x/circled-left.png",
                        "label": "Ask Question",
                        "value": "Ask Question",
                        "trigger": 4
                    }],
                    "templateId": 6
                },
                "fulfillment": {
                    "action": "action-category-faq-ma-ans",
                    "parameters": {},
                    "previousIntent": 302
                },
                "userInput": False
            })
        else:
            return jsonify({
                "error": f"Failed to upload {selected_filename}",
                "response": response.text,
                "id": 304,  # You can set the appropriate ID
                "userInput": True,
                "trigger": 304  # You can set the appropriate trigger
            })

    # ... [Add more conditions for other actions] ...

    return jsonify({"error": "Unknown action"})


if __name__=="__main__":
    app.run(debug=True,port=6000)
