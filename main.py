import tkinter as tk
from tkinter import scrolledtext
import pygame
from newspaper import Article
from pyht import Client
from pyht.client import TTSOptions
import google.generativeai as genai
from pydub import AudioSegment
from dotenv import load_dotenv
import os

load_dotenv()

gemini_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize PlayHT client
client = Client(
    user_id=os.getenv("PLAYHT_USER_ID"),
    api_key=os.getenv("PLAYHT_API_KEY"),
)

# TTS options for male and female voices
male_options = TTSOptions(voice="s3://voice-cloning-zero-shot/d99d35e6-e625-4fa4-925a-d65172d358e1/adriansaad/manifest.json")
female_options = TTSOptions(voice="s3://voice-cloning-zero-shot/e5df2eb3-5153-40fa-9f6e-6e27bbb7a38e/original/manifest.json")

# Function to generate a podcast script
def generate_gemini_script(data):
    print("Generating podcast script...")
    full_prompt = (
        "Generate a podcast script on the given data below where two people are "
        "talking about this content. Give it in this format:\n"
        "[m]: male script goes here\n[f]: female script goes here;\n"
        "Use new lines to differentiate between make and female script as represented and is a must and compulsion!.\n"
        "Keep it short, with 2 speech each. Making a total of 4. the name of m is Mark and f is Sarah so use the name in the script.\n\n" 
        "Make it interactive like male and females asking question like a real podcast and also start with a greetings and mentioning today's topic or something like that" + data
    )
    response = model.generate_content(full_prompt)
    return response.text

# Function to extract text from a given URL
def extract_text_from_url(url):
    print("Fetching text from the url...")
    article = Article(url)
    article.download()
    article.parse()
    return article.text

# Function to synthesize speech using specific voice options and save it to an MP3 file
def synthesize_and_save(text, options, output_file):
    output_file = output_file.replace(".mp3", ".wav")
    with open(output_file, "wb") as audio_file:
        for chunk in client.tts(text, options, voice_engine='PlayDialog-http'):
            if chunk:
                audio_file.write(chunk)

# Function to combine multiple audio files into one
def combine_audio(files, output_file):
    combined = AudioSegment.empty()
    for file in files:
        audio = AudioSegment.from_wav(file) 
        combined += audio
    combined.export(output_file, format="mp3")

# Function to generate audio for each line and combine them into one file
def generate_and_combine_audio(male_script, female_script, text_widget):
    print("Generating audio for the podcast...")
    male_audio_files = []
    female_audio_files = []

    # Generate audio for each line of the male and female scripts
    for i, line in enumerate(male_script):
        if line.strip():
            male_file = f"male_line_{i}.wav"
            synthesize_and_save(line, male_options, male_file)
            male_audio_files.append(male_file)
        text_widget.insert(tk.END, f"Generated male line {i}\n")
        text_widget.yview(tk.END)

    for i, line in enumerate(female_script):
        if line.strip():
            female_file = f"female_line_{i}.wav"
            synthesize_and_save(line, female_options, female_file)
            female_audio_files.append(female_file)
        text_widget.insert(tk.END, f"Generated female line {i}\n")
        text_widget.yview(tk.END)

    # Combine the generated audio files into one
    combined_audio = []
    
    min_len = min(len(male_audio_files), len(female_audio_files))
    
    for i in range(min_len):
        combined_audio.append(male_audio_files[i])
        combined_audio.append(female_audio_files[i])
    
    if len(male_audio_files) > min_len:
        combined_audio.extend(male_audio_files[min_len:])
    elif len(female_audio_files) > min_len:
        combined_audio.extend(female_audio_files[min_len:])

    combine_audio(combined_audio, "final_podcast.mp3")

    for file in male_audio_files + female_audio_files:
        os.remove(file)

    text_widget.insert(tk.END, "Podcast generated and combined successfully!\n")
    text_widget.yview(tk.END)

    # Play the final podcast after it's created
    pygame.mixer.init()  
    pygame.mixer.music.load("final_podcast.mp3")
    pygame.mixer.music.play()  

    # Keep the script running while audio plays
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    text_widget.insert(tk.END, "Podcast finished playing.\n")
    text_widget.yview(tk.END)

# Function to handle the UI button click
def start_process(text_widget, url_entry):
    url = url_entry.get()
    if not url:
        text_widget.insert(tk.END, "Please enter a URL.\n")
        text_widget.yview(tk.END)
        return

    text_widget.insert(tk.END, "Fetching article...\n")
    text_widget.yview(tk.END)

    text = extract_text_from_url(url)

    script = generate_gemini_script(text)

    # Split the script into male and female parts
    print("Refining the script...")
    male_script = []
    female_script = []
    parts = script.split("\n")
    for part in parts:
        if "[m]:" in part:  # Male part
            male_script.append(part.split("[m]:")[1])
        elif "[f]:" in part:  # Female part
            female_script.append(part.split("[f]:")[1])

    # Generate and combine audio for male and female parts
    generate_and_combine_audio(male_script, female_script, text_widget)

# Set up the UI window
root = tk.Tk()
root.title("Podcast Generator")

# UI elements
url_label = tk.Label(root, text="Enter URL:")
url_label.pack(pady=5)

url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)

start_button = tk.Button(root, text="Generate Podcast", command=lambda: start_process(text_widget, url_entry))
start_button.pack(pady=20)

text_widget = scrolledtext.ScrolledText(root, width=60, height=15)
text_widget.pack(pady=5)

# Start the UI loop
root.mainloop()
