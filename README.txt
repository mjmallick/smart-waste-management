SMART WASTE MANAGEMENT - FRESH GEMINI VERSION
=============================================

This is the clean project folder. The main website is app.py.
The Gemini app does NOT use the old six-class .keras model for image recognition.
It asks Gemini to identify the visible object, likely materials, waste category,
and safe disposal steps.

FIRST-TIME SETUP
----------------
1. Extract the ZIP file.
2. Open the folder named Smart_Waste_Management_Gemini in VS Code:
   File > Open Folder > select this folder.
3. Open .streamlit > secrets.toml.
4. Replace PASTE_YOUR_NEW_GEMINI_API_KEY_HERE with your NEW Gemini API key.
   Keep the double quotes. Do not share the key or upload secrets.toml to GitHub.
5. Save the file (Ctrl + S).
6. In VS Code choose Terminal > New Terminal.
7. Install the packages:

   python -m pip install -r requirements.txt

8. Start the website:

   python -m streamlit run app.py

9. Open the Local URL shown in the terminal. Usually it is:
   http://localhost:8501

EASIER WINDOWS START
--------------------
After adding the API key, you can double-click START_APP.bat. It installs any
missing packages and starts Streamlit. Keep the black terminal window open while
using the website.

USING THE WEBSITE
-----------------
1. Upload one clear JPG, JPEG, PNG or WEBP photo (maximum 8 MB).
2. Click "Identify this object".
3. Read the object name, likely materials, waste category and disposal guidance.

GEMINI MODEL FALLBACK
---------------------
The app first tries Gemini 3.8 Flash. If Google reports temporary capacity or
rate-limit trouble, it automatically tries Gemini 3.5 Flash-Lite. If both are
unavailable or the API quota is exhausted, wait and retry or check your Google
AI Studio project usage.

FILES
-----
app.py                         Main, redesigned Gemini Streamlit website
requirements.txt               Python packages
.streamlit/secrets.toml        Private API key placeholder
START_APP.bat                  Windows setup-and-run helper
legacy/                        Original .keras classifier and previous scripts

SECURITY
--------
The ZIP contains only an empty API-key placeholder. Add your own key locally.
Never paste your real API key into chat, screenshots, source code, or GitHub.
If a key has been exposed, revoke it in Google AI Studio and create a new one.

NOTE
----
AI recognition and disposal suggestions can be mistaken. Check local municipal
rules and use authorised collection services for e-waste, batteries and
hazardous items. The old six-class model is retained only as a backup/reference.
