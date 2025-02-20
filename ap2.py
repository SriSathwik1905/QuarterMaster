import streamlit as st
import google.generativeai as genai
import subprocess
import re
import os
import logging
from dotenv import load_dotenv

# --- Setup ---

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env (for the API key)
load_dotenv()
logging.info("Loaded environment variables.")

# Configure the Gemini API.  Gets the key from the environment variable.
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')
logging.info("Gemini API configured.")

# --- Helper Functions ---

def run_command(command):
    """
    Runs a shell command and returns its output (stdout) and errors (stderr).
    Uses subprocess.run for safe execution.
    """
    logging.info(f"Executing command: {command}")
    try:
        process = subprocess.run(command, capture_output=True, text=True, shell=True, check=False)
        logging.info(f"Command output: {process.stdout}")
        if process.stderr:
            logging.error(f"Command error: {process.stderr}")
        return process.stdout, process.stderr
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {e}")
        return "", f"Error: {e}"  # Return error message
    except FileNotFoundError:
        logging.error("Command not found. Check if winget is installed.")
        return "", "Command not found error. Check if winget is installed in your system."

def parse_winget_search(output):
    """
    Parses the output of 'winget search' to extract application names and IDs.
    Returns a list of (name, id) tuples.  Handles variations in whitespace.
    """
    logging.info("Parsing winget search output.")
    lines = output.splitlines()
    results = []
    startIndex = 3
    if len(lines) <= startIndex:
        logging.warning("No applications found.")
        st.error("No applications found with the given name")
        return
    for line in lines[startIndex:]:
        match = re.match(r"(.+?)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)", line)
        if match:
            name = match.group(1).strip()  # Extract and clean the name
            id = match.group(2).strip()    # Extract and clean the ID
            results.append((name, id))
    logging.info(f"Parsed results: {results}")
    return results

# --- Streamlit UI Setup ---

st.title("Quartermaster")  # Set the title of the app
logging.info("Streamlit app initialized.")

# Initialize the chat history in Streamlit's session state.
if "messages" not in st.session_state:
    st.session_state.messages = []
    logging.info("Initialized session state for messages.")

# Display existing chat messages from the session state.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get user input using Streamlit's chat input widget.
prompt = st.chat_input("What can I do for you?")

# --- Main Logic (Handles user input and Gemini interaction) ---

if prompt:  # Execute if the user entered something
    logging.info(f"User input received: {prompt}")
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- Construct the prompt for Gemini ---
    system_prompt = """You are Quartermaster, a helpful assistant that manages Windows system settings and software installations.
    You MUST respond in a very specific format:
    - For Winget searches, respond with 'WINGET_SEARCH: <search term>'.
    - For Winget installations, respond with 'WINGET_INSTALL: <package ID>'.
    - To change sleep settings to 'n' minutes respond with 'POWERSHELL_SLEEP: n'.
    - If you don't understand a command, say so.
    """
    full_prompt = f"{system_prompt}\nUser: {prompt}\nQuartermaster:"
    logging.info(f"Sending prompt to Gemini: {full_prompt}")

    response = model.generate_content(full_prompt)
    response_text = response.text
    logging.info(f"Gemini response: {response_text}")

    st.session_state.messages.append({"role": "assistant", "content": response_text})
    with st.chat_message("assistant"):
        st.markdown(response_text)

    # --- Process Gemini's response and execute commands ---
    if "WINGET_SEARCH:" in response_text:
        search_term = response_text.replace("WINGET_SEARCH:", "").strip()
        logging.info(f"Performing winget search for: {search_term}")
        stdout, stderr = run_command(f"winget search \"{search_term}\"")
        if stderr:
            st.error(stderr)
        else:
            results = parse_winget_search(stdout)
            if results:
                with st.chat_message("assistant"):
                    st.write("Here are the search results:")
                    selected_app = st.radio("Select an application to install:", [name for name, _ in results])
                    selected_app_id = [id for name, id in results if name == selected_app][0]
                    if st.button("Install"):
                        logging.info(f"Installing application: {selected_app_id}")
                        install_stdout, install_stderr = run_command(f"winget install --id \"{selected_app_id}\" -e")
                        if install_stderr:
                            st.error(install_stderr)
                        else:
                            st.success(f"Installation output:\n{install_stdout}")
    else:
        with st.chat_message("assistant"):
            if st.button(f"Confirm execution: {response_text}"):
                logging.info(f"Executing command: {response_text}")
                stdout, stderr = run_command(response_text)
                if stderr:
                    logging.error(stderr)
                    st.error(stderr)
                else:
                    logging.info(f"Command executed successfully: {stdout}")
                    st.success(f"Command executed:\n{stdout}")
