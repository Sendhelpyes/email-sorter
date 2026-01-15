import base64
import time
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from typing import Literal
import create_services

load_dotenv()

class DecideAction(BaseModel):
    response: Literal["A","B","C"]


class auto_sorting_agent:
    def __init__(self):
        self.__service = create_services.create_service("gmail","v1")
        self.__results = []
        self.__message_ids = self.__results.get("messages",[])
        self.__client = OpenAI()

        
    def test(self):
        message_id = self.__message_ids[0]
        message = self.__service.users().messages().get(
            userId="me", 
            id=message_id["id"], 
            format="full"
        ).execute()
        content = self.extract_body_text(message)
        files_for_ai = self.get_files_for_AI(content, message_id["id"])
        self.decide_action(files_for_ai)




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
        if file_type == "text/plain":
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
            messages = [{"role": "system", "content": "Your goal is to identify if LinkedIn sent this email. "
            "Respond with A if it is, "
            "respond with B if it is not, "
            "respond with C if the text clearly makes itself known that it is an unsupported format."},
                        {"role": "user", "content": inputs}],
            response_format = DecideAction,
            temperature=0 #its sorting so 0 makes it more optimised
        )
        decision = completion.choices[0].message.parsed.response
        print(decision)


    def main(self):
        while True:
            self.__results = self.__service.users().messages().list(userId="me",q="is:unread").execute()
            if self.__results:
                message_ids = self.__results.get("messages",[])
                for message_id in message_ids:
                    message = self.__service.users().messages().get(
                        userId="me", 
                        id=message_id["id"], 
                        format="full"
                    ).execute()
                    content = self.extract_body_text(message)
                    files_for_ai = self.get_files_for_AI(content, message_id["id"])
                    self.decide_action(files_for_ai)
                    time.sleep(30)
            time.sleep(10)


agent = auto_sorting_agent()



