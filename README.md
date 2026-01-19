# email-sorter
This may fail, I hope it doesn't. Also this requires an API key from OpenAI

To use:
1. Go to google cloud console and create a project.
2. Enable the gmail API in APIs & Services
3. Go to the OAuth consent screen and fill in the app name, user type, and the required emails.
4. Add the email you will be using the sorter on.
5. Go to Credentials and click credentials. Choose OAuth Client ID. Choose Desktop app and create.
6. Click download json and save the file as credentials.json.
7. Create a .env file, and paste an API key.
8. Do pip install -r requirements.txt (you may want do make a venv for this)
9. To run: just run python/python3 agent.py in the command line. You may be asked to login if you are running the program for the first time.

This program will attempt to sort emails into 3 categories: Important, Spam and misc. (It will create a misc label if it doesn't exist). It will move the message from inbox to the appropriate label.
