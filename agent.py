import base64
import time
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from typing import Literal
import create_services

load_dotenv()

class DecideAction(BaseModel):
    response: Literal["important","spam","misc"]


class auto_sorting_agent:
    def __init__(self):
        self.__service = create_services.create_service("gmail","v1")
        self.__results = []
        self.__misc_label_id = ""
        self.__protected_labels = ["SENT", "DRAFTS", "UNREAD", "TRASH","UNREAD"] #These labels can't be removed. (set by google, I added unread on there so it remains unread for the user.
        self.__client = OpenAI()
        self.run_agent()

        
    def extract_body_text(self,message):
        return self.extract_body_logic_recurse({"text":"",
                                                "attachment_ID": []},message["payload"])

    def extract_body_logic_recurse(self,body,mime_message):
        mime_body = mime_message.get("body",{})
        message_type = mime_message.get("mimeType","")
        if "attachmentId" in mime_body: #Check for big attachments sent in a mime message
            body["attachment_ID"].append({
            "id": mime_body["attachmentId"],
            "filename": mime_message.get("filename", ""),
            "file_type": message_type
        }) 

        elif "data" in mime_body: #Not big message nor container
            data = mime_body.get("data")
            if message_type == "text/plain": #Text, just decode
                body["text"] += base64.urlsafe_b64decode(data).decode("utf-8")
            elif message_type.startswith("image/") or message_type != "text/html": #Inline images, store the string
                body["attachmentId"].append({
                "data": data,
                "filename": mime_message.get("filename", ""),
                "fileType": message_type
            })

        if "parts" in mime_message: #recurse through tree
            for part in mime_message["parts"]:
                self.extract_body_logic_recurse(body,part)
        return body

    def get_attachment_from_id(self,attachment_dict,message_ID):
        attachment = self.__service.users().messages().attachments().get(userId="me",messageId=message_ID,id=attachment_dict["id"]).execute()
        data = base64.urlsafe_b64decode(attachment.get("data", ""))
        file_type = attachment_dict["file_type"]
        if file_type == "text/plain": #Figure out what to do with attachment
            return {
                "type": "text",
                "text": data.decode("utf-8", errors="replace")
            }
        elif file_type.startswith("image/"):
            return {
                    "type": "image_url", 
                    "image_url": {
                    "url": f"data:image/png;base64,{base64.b64encode(data).decode("utf-8")}"
            }}
        elif attachment_dict.get("filename", "").endswith(".json"):
            return {
                    "type": "text",
                    "text": f"--- Attached JSON File ({attachment_dict.get("filename", "")}) ---\n{data.decode("utf-8")}"
                }
        else:
            return {
                "type": "text",
                "text": "UNSUPPORTED FORMAT"
            }

    def get_files_for_AI(self,body,message_ID):
        files = []
        if body.get("text",""):
            files.append({"type": "text",
                          "text": body["text"]})
        for attachment_dict in body["attachment_ID"]:
            files.append(self.get_attachment_from_id(attachment_dict, message_ID))
        return files

    def decide_action(self,inputs):
        completion = self.__client.beta.chat.completions.parse(
            model = "gpt-4o-mini",
            messages = [{"role": "system", "content": "Your goal is determine where the email should be moved to. Respond with spam if you believe you got an automated message,"
            " important if the message is important and misc for anything else."},
                        {"role": "user", "content": inputs}],
            response_format = DecideAction, #Restrict its output so it can only respond with important/spam/misc
            temperature=0 #its sorting so 0 makes it more optimised
        )
        decision = completion.choices[0].message.parsed.response
        return decision

    def move_message(self,message_id,decision):
        labels = {
            "important" : "IMPORTANT",
            "spam": "SPAM",
            "misc": self.__misc_label_id
        }   
        new_label = labels[decision]
        message_labels_to_remove = self.__service.users().messages().get(userId="me",id=message_id).execute().get("labelIds",[])
        message_labels_to_remove = [label for label in message_labels_to_remove if label not in self.__protected_labels and label != new_label]
        change_labels = {
            "removeLabelIds": message_labels_to_remove,
            "addLabelIds": [new_label]
        }
        self.__service.users().messages().modify(userId="me",id=message_id,body=change_labels).execute()


    def check_labels(self): #Check if we made a misc label, if not make one.
        labels = self.__service.users().labels().list(userId="me").execute().get("labels",[])
        for label in labels:
            if label["name"] == "misc":
                self.__misc_label_id = label["id"]
                return
        label = {
            "name": "misc",
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        
        misc_label = self.__service.users().labels().create(userId="me",body=label).execute()
        self.__misc_label_id = misc_label["id"]
        return

    def run_agent(self):
        self.check_labels()
        while True:
            try:
                query = "is:inbox newer_than:2m"
                self.__results = self.__service.users().messages().list(userId="me",q=query).execute()
                #self.__results = self.__service.users().messages().list(userId="me",q="is:unread").execute()
                if self.__results:
                    message_dicts = self.__results.get("messages",[])
                    print(len(message_dicts))
                    for message_dict in message_dicts:     
                        message = self.__service.users().messages().get(
                            userId="me", 
                            id=message_dict["id"], 
                            format="full"
                        ).execute()
                        content = self.extract_body_text(message)
                        files_for_ai = self.get_files_for_AI(content, message_dict["id"])
                        decision = self.decide_action(files_for_ai)
                        self.move_message(message_dict["id"],decision)
                        print("Made decision:", decision)
            except Exception as e:
                print(e)
            print("No emails currently")
            time.sleep(100)


agent = auto_sorting_agent()



