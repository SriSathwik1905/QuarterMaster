# app.py
import streamlit as st
import google.generativeai as genai
import subprocess
import re
import os
from dotenv import load_dotenv

# --- Setup ---

# Load environment variables from .env (for the API key)
load_dotenv()

# Configure the Gemini API.  Gets the key from the environment variable.
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

# --- Helper Functions ---

def run_command(command):
    """
    Runs a shell command and returns its output (stdout) and errors (stderr).
    Uses subprocess.run for safe execution.
    """
    try:
        process = subprocess.run(command, capture_output=True, text=True, shell=True, check=False)
        return process.stdout, process.stderr
    except subprocess.CalledProcessError as e:
        return "", f"Error: {e}"  # Return error message
    except FileNotFoundError:
        return "","Command not found error check if winget is installed in your system."

def parse_winget_search(output):
    """
    Parses the output of 'winget search' to extract application names and IDs.
    Returns a list of (name, id) tuples.  Handles variations in whitespace.
    """
    lines = output.splitlines()
    results = []
    startIndex = 3
    if len(lines) <= startIndex:
        st.error("No applications found with the given name")
        return
    for line in lines[startIndex:]:
        match = re.match(r"(.+?)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)", line)
        if match:
            name = match.group(1).strip()  # Extract and clean the name
            id = match.group(2).strip()    # Extract and clean the ID
            results.append((name, id))
    return results

# --- Streamlit UI Setup ---

st.title("Quartermaster")  # Set the title of the app

# Initialize the chat history in Streamlit's session state.
# This persists across interactions within a single session.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display existing chat messages from the session state.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get user input using Streamlit's chat input widget.
prompt = st.chat_input("What can I do for you?")

# --- Main Logic (Handles user input and Gemini interaction) ---

if prompt:  # Execute if the user entered something
    # Add the user's message to the chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)  # Display the user's message

    # --- Construct the prompt for Gemini ---
    system_prompt = """You are Quartermaster, a helpful assistant that manages Windows system settings and software installations.
    You MUST respond in a very specific format:
    - For Winget searches, respond with 'WINGET_SEARCH: <search term>'.
    - For Winget installations, respond with 'WINGET_INSTALL: <package ID>'.
    - To change sleep settings to 'n' minutes respond with 'POWERSHELL_SLEEP: n'.
    - If you don't understand a command, say so.

    Here are some examples:
    User: install vscode
    Quartermaster: WINGET_SEARCH: vscode

    User: Set sleep timer to 30 minutes
    Quartermaster: POWERSHELL_SLEEP: 30

    User: install the visual studio code from the given options.
    Quartermaster: WINGET_INSTALL: Microsoft.VisualStudioCode

    and so on, try to run the commands needed to change settings live even things like brightness darkmode and everything u can do with the command line.
    """
    # Combine the system prompt with the current user prompt.
    full_prompt = f"{system_prompt}\nUser: {prompt}\nQuartermaster:"

    # --- Get response from Gemini ---
    response = model.generate_content(full_prompt)
    response_text = response.text

    # --- Add Gemini's response to chat history ---
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    with st.chat_message("assistant"):
        st.markdown(response_text)  # Display Gemini's response

    # --- Process Gemini's response and execute commands ---

    if "WINGET_SEARCH:" in response_text:
        search_term = response_text.replace("WINGET_SEARCH:", "").strip()
        stdout, stderr = run_command(f"winget search \"{search_term}\"")
        if stderr:
            st.error(stderr)  # Display any errors from the command
        else:
            results = parse_winget_search(stdout)  # Parse the output
            if results:
                with st.chat_message("assistant"):
                    st.write("Here are the search results:")
                    # Display results as radio buttons for selection
                    selected_app = st.radio("Select an application to install:", [name for name, _ in results])
                    selected_app_id = [id for name, id in results if name == selected_app][0]
                    if st.button("Install"):  # Install button
                        install_stdout, install_stderr = run_command(f"winget install --id \"{selected_app_id}\" -e")
                        if install_stderr:
                            st.error(install_stderr)  # Display install errors
                        else:
                             st.success(f"Installation output:\n{install_stdout}")

    elif "WINGET_INSTALL:" in response_text:
        package_id = response_text.replace("WINGET_INSTALL:", "").strip()
        stdout, stderr = run_command(f"winget install --id \"{package_id}\" -e")
        if stderr:
            st.error(stderr)  # Display errors
        else:
            with st.chat_message("assistant"):
                st.success(f"Installation output:\n{stdout}")

    elif "POWERSHELL_SLEEP:" in response_text:
        minutes = response_text.replace("POWERSHELL_SLEEP:", "").strip()
        try:
            minutes_int = int(minutes)  # Convert to integer
            stdout, stderr = run_command(f"powershell -Command \"powercfg /change /standby-timeout-ac {minutes_int}\"")
            if stderr:
                st.error(stderr)  # Display errors
            else:
                with st.chat_message("assistant"):
                    st.success(f"Sleep timeout set to {minutes_int} minutes.")
        except ValueError:
            with st.chat_message("assistant"):
                st.error("Invalid time provided for sleep settings. Please provide a number.")

    else:
        with st.chat_message("assistant"):
            st.write("I couldn't process that request. I can help with Winget installations and setting the sleep timer.")

# --- Neumorphic Styling (Optional) ---
# Add this *before* the main UI code (st.title, etc.) if you want styling.
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f0f0f0; /* Light gray background */
    }
    .stTextInput>div>div>input,
    .stButton>button {
        border-radius: 20px;
        border: none;
        padding: 10px 20px;
        box-shadow:  5px 5px 10px #c8c8c8,  /* Darker shadow */
                    -5px -5px 10px #ffffff;  /* Lighter shadow */
    }
      .stChatFloatingInputContainer{
         border-radius: 20px;
        border: none;
        padding: 10px 20px;
        box-shadow:  5px 5px 10px #c8c8c8,
                    -5px -5px 10px #ffffff;
    }
     .st-b7 {
      border-radius: 20px;
     }
     .st-bf{
      border-radius: 20px;
     }

    .stButton>button:hover {
         box-shadow:  2px 2px 5px #c8c8c8,
                    -2px -2px 5px #ffffff;
    }
    .stChatInputContainer{
    background-color: #f0f0f0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)