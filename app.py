import os
import base64
import json
import ast  # For safely evaluating agent string outputs
from openai import OpenAI
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from PIL import Image
import streamlit as st

# --- 1. API KEY SETUP ---
# Streamlit will get the key from .streamlit/secrets.toml
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
    client = OpenAI(api_key=OPENAI_API_KEY)
except KeyError:
    st.error("OPENAI_API_KEY not found! Please add it to your .streamlit/secrets.toml file.")
    st.stop()


# --- 2. HELPER FUNCTION & ALL TOOL DEFINITIONS ---

# Helper for encoding images
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# --- Module 1 Tools ---
class VisualTools(BaseTool):
    name: str = "Image Description Tool"
    description: str = "Takes the file path of an image and generates brief, standard, and detailed descriptions using GPT-4o vision."

    def _run(self, image_path: str) -> str:
        base64_image = encode_image(image_path)
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": "Describe this image in detail. Follow W3C WAI guidelines. Provide three versions: a 'Brief' description, a 'Standard' description, and a 'Detailed' description."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}
                ], max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error analyzing image: {e}"

class AudioTools(BaseTool):
    name: str = "Text-to-Speech Tool"
    description: str = "Takes text and a save path, converts it to an MP3, and saves it."

    def _run(self, text_to_speak: str, save_path: str = "module_1_output.mp3") -> str:
        try:
            audio_response = client.audio.speech.create(
                model="tts-1", voice="nova", input=text_to_speak
            )
            audio_response.stream_to_file(save_path)
            return f"Audio file saved to {save_path}"
        except Exception as e:
            return f"Error generating audio: {e}"

# --- Module 2 Tool ---
class VisualSimplifierTool(BaseTool):
    name: str = "Complex Text to Visual Tool"
    description: str = "Takes complex text and generates a text-free visual explanation. Returns the URL."

    def _run(self, complex_text: str) -> str:
        try:
            simplification_prompt = f"""
            You are a visual learning designer. Read the following complex text.
            Your goal is to generate a DALL-E 3 prompt to create a simple, clear
            visual diagram or infographic that explains this concept.
            ***IMPORTANT RULE: The visual must contain NO TEXT, NO LABELS, and NO LETTERS.***
            The prompt should describe a visual metaphor or a diagram using only icons and arrows.
            
            Complex Text: "{complex_text}"
            
            Respond with *only* the DALL-E 3 prompt and nothing else.
            """
            
            response = client.chat.completions.create(
                model="gpt-4o", messages=[{"role": "user", "content": simplification_prompt}], max_tokens=300
            )
            dalle_prompt = response.choices[0].message.content

            image_response = client.images.generate(
                model="dall-e-3", prompt=dalle_prompt, size="1024x1024", quality="standard", n=1
            )
            return image_response.data[0].url
        except Exception as e:
            return f"Error in visual generation process: {e}"

# --- Module 4 Tools ---
class ASLGrammarTool(BaseTool):
    name: str = "ASL Grammar Conversion Tool"
    description: str = "Takes an English sentence and converts it into the correct ASL grammatical structure (e.g., Topic-Comment)."

    def _run(self, english_text: str) -> str:
        system_prompt = """
        You are an expert ASL linguist. Your job is to translate English sentences
        into the correct ASL grammatical structure.
        Key rules: Topic-Comment, No Articles, No 'be' verbs, Use Infinitives, Time-first.
        Example:
        - English: "I am going to the store tomorrow."
        - ASL Grammar: "TOMORROW, STORE, I GO-TO."
        Respond with *only* the ASL grammar string and nothing else.
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": english_text}
                ], max_tokens=100
            )
            asl_grammar_string = response.choices[0].message.content
            # Standardize output for the next agent
            signs = [sign.strip().upper() for sign in asl_grammar_string.split(',')]
            return signs
        except Exception as e:
            return f"Error in grammar conversion: {e}"

# Load our new local video map ONCE when the app starts
try:
    with open('sign_video_map.json', 'r') as f:
        SIGN_VIDEO_MAP = json.load(f)
    print("Local sign video map loaded successfully.")
except FileNotFoundError:
    print("ERROR: sign_video_map.json not found. Did you run parse_data.py first?")
    SIGN_VIDEO_MAP = {}

class SignDetailTool(BaseTool):
    name: str = "Sign Detail Lookup Tool"
    description: str = "Takes a Python LIST of ASL sign words and returns a list of dictionaries. Each dictionary contains the sign, its video path, and its text description."

    def _run(self, sign_list: list) -> list:
        print(f"--- Tool: Looking up details (video + text) for {sign_list}... ---")
        
        details_list = []
        for sign_word in sign_list:
            clean_word = sign_word.lower().strip().replace("-", "")
            
            # 1. Get Video Path (from our JSON map)
            video_id = SIGN_VIDEO_MAP.get(clean_word, None)
            video_path = f"videos/{video_id}.mp4" if video_id else f"No video found for sign: {sign_word}"
            
            # 2. Get Text Description (from AI)
            description = "No description found." # Default
            try:
                system_prompt = f"""
                You are a sign language dictionary. Given a single ASL sign word, provide a brief,
                one-sentence description of how to perform the sign.
                Example: - Input: "STORE" - Output: "With both hands in 'S' shape, tap fingertips together twice."
                
                Input: "{sign_word}"
                Output:
                """
                response = client.chat.completions.create(
                    model="gpt-4o", messages=[{"role": "system", "content": system_prompt}], max_tokens=100
                )
                description = response.choices[0].message.content.strip()
            except Exception as e:
                description = f"Error getting description: {e}"

            # 3. Append both to our list
            details_list.append({
                "sign": sign_word,
                "path": video_path,
                "desc": description
            })
        
        return details_list

# --- 3. INSTANTIATE ALL TOOLS ---
visual_tool = VisualTools()
audio_tool = AudioTools()
visual_simplifier_tool = VisualSimplifierTool()
grammar_tool = ASLGrammarTool()
detail_tool = SignDetailTool() # <-- Note: new tool instantiated

# --- 4. DEFINE ALL AGENTS ---

# Module 1 Agents
visual_describer = Agent(
    role='Visual Describer',
    goal='Create brief, standard, and detailed accessibility descriptions for an image.',
    backstory='You are an expert in web accessibility and image analysis.',
    tools=[visual_tool], verbose=False, allow_delegation=False
)
audio_producer = Agent(
    role='Audio Producer',
    goal='Convert text descriptions into natural, high-quality audio files.',
    backstory='You are a professional voice actor with a clear and engaging voice.',
    tools=[audio_tool], verbose=False, allow_delegation=False
)

# Module 2 Agent
visual_simplifier_agent = Agent(
    role='Visual Simplifier',
    goal='Create a clear and simple text-free visual explanation from complex text.',
    backstory='You are an expert in instructional design and cognitive science.',
    tools=[visual_simplifier_tool], verbose=False, allow_delegation=False
)

# Module 3 Agents
asl_grammar_agent = Agent(
    role='ASL Grammar Translator',
    goal='Convert spoken English sentences into the correct ASL grammatical sign order.',
    backstory='You are an expert linguist specializing in English to ASL translation.',
    tools=[grammar_tool], verbose=False, allow_delegation=False
)
sign_sequencer_agent = Agent(
    role='Sign Language Sequencer',
    goal='Take a list of ASL-grammar signs and find the local video file path AND text description for each one.',
    backstory='You are a sign language librarian. You take a list of signs and return a list of objects containing all details for each sign.',
    tools=[detail_tool], # <-- THIS IS THE CHANGE
    verbose=False,
    allow_delegation=False
)

# --- 5. STREAMLIT WEB INTERFACE ---
st.title("Multimodal Accessibility Translator 🤖")
st.markdown("This app uses a CrewAI multi-agent system to make content accessible.")

tab1, tab2, tab3 = st.tabs([
    "👁️ Module 1: Image-to-Audio",
    "🧠 Module 2: Text-to-Visual",
    "✋ Module 3: Text-to-Sign Language"
])

# --- TAB 1: Image-to-Audio ---
with tab1:
    st.header("Generate Audio Descriptions from an Image")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        # Save the uploaded file to a temporary path
        img = Image.open(uploaded_file)
        temp_image_path = "temp_uploaded_image.jpg"
        img.save(temp_image_path)
        
        # --- FIX: Changed 'use_column_width' to 'use_container_width' ---
        st.image(img, caption='Uploaded Image.', use_container_width=True)
        
        if st.button("Generate Accessibility Audio", key="mod1_go"):
            with st.spinner("Agents are working... This may take a moment."):
                
                # Define tasks
                description_task = Task(
                    description=f'Analyze the image at {temp_image_path} and generate descriptions.',
                    expected_output='A single string with brief, standard, and detailed descriptions.',
                    agent=visual_describer
                )
                audio_task = Task(
                    description='Convert the text descriptions into a single audio file named "module_1_output.mp3".',
                    expected_output='A confirmation string that the audio file was saved.',
                    agent=audio_producer,
                    context=[description_task]
                )
                
                # Define crew
                accessibility_crew = Crew(
                    agents=[visual_describer, audio_producer],
                    tasks=[description_task, audio_task],
                    process=Process.sequential,
                    verbose=False
                )
                
                # Run crew
                crew_result = accessibility_crew.kickoff()
                
                # --- FIX: Get the text description from crew_result ---
                text_description = crew_result.tasks_output[0].raw
                
                st.subheader("Generated Descriptions:")
                st.markdown(text_description)
                
                st.subheader("Generated Audio:")
                st.audio("module_1_output.mp3")
                
                # Clean up temp file
                os.remove(temp_image_path)

# --- TAB 2: Text-to-Visual ---
with tab2:
    st.header("Generate a Text-Free Visual from Complex Text")
    complex_text = st.text_area("Paste your complex text here:", height=150, 
                                placeholder="e.g., Photosynthesis is a process used by plants...")
    
    if st.button("Generate Visual Explanation", key="mod3_go"):
        if complex_text:
            with st.spinner("Visual Simplifier Agent is thinking..."):
                
                # Define task
                simplification_task = Task(
                    description=f'Use your tool to convert the following complex text into a single, text-free visual explanation: "{complex_text}"',
                    expected_output='The final URL of the generated visual diagram.',
                    agent=visual_simplifier_agent
                )
                
                # Define crew
                visual_crew = Crew(
                    agents=[visual_simplifier_agent],
                    tasks=[simplification_task],
                    process=Process.sequential,
                    verbose=False
                )
                
                # Run crew
                crew_result = visual_crew.kickoff()
                
                st.subheader("Generated Visual (No Text):")
                if crew_result.raw and crew_result.raw.startswith('http'):
                    st.image(crew_result.raw, caption="AI-generated visual explanation.")
                else:
                    st.error(f"Agent failed to generate image. Log: {crew_result.raw}")
        else:
            st.warning("Please paste some text first.")

# --- TAB 3: Text-to-Sign Language ---
with tab3:
    st.header("Generate Sign Language Video from Text")
    english_text = st.text_input("Enter a simple English sentence:", 
                                 placeholder="e.g., book")
    
    if st.button("Generate Sign Sequence", key="mod2_go"):
        if english_text:
            with st.spinner("Sign Language 'Brain' Crew is working... (This may take a moment)"):
                
                # Define tasks
                grammar_task = Task(
                    description=f"Translate the following English sentence into ASL grammar: '{english_text}'",
                    expected_output="A Python list of ASL sign words in the correct grammatical order.",
                    agent=asl_grammar_agent
                )
                
                sequence_task = Task(
                    description="You have a Python list of ASL signs. Pass this *entire list* to your 'Sign Detail Lookup Tool' to get the final list of details.",
                    expected_output="A final Python list of dictionaries, where each dictionary contains 'sign', 'path', and 'desc'.",
                    agent=sign_sequencer_agent,
                    context=[grammar_task] 
                )
                
                # Define crew
                sign_language_crew = Crew(
                    agents=[asl_grammar_agent, sign_sequencer_agent],
                    tasks=[grammar_task, sequence_task],
                    process=Process.sequential,
                    verbose=False
                )
                
                # Run crew
                crew_result = sign_language_crew.kickoff()
                
                st.subheader("Generated Sign Language Instructions & Videos:")
                
                if crew_result.raw:
                    try:
                        # --- FIX: Convert string-list to real list ---
                        details_list = ast.literal_eval(crew_result.raw)
                        
                        if not isinstance(details_list, list):
                             st.error(f"Agent returned unexpected data: {details_list}")
                             st.stop()
                        
                        # Create columns for a cleaner layout
                        if not details_list:
                             st.warning("No signs were generated. Try a different sentence.")
                             st.stop()
                             
                        cols = st.columns(len(details_list))
                        
                        for i, item in enumerate(details_list):
                            with cols[i]:
                                # 1. Show the Sign
                                st.markdown(f"**{item['sign']}**")
                                # 2. Show the Text Description
                                st.markdown(f"*{item['desc']}*") 
                                
                                video_path = item['path']
                                # 3. Show the Video
                                if video_path.startswith('videos/') and os.path.exists(video_path):
                                    try:
                                        st.video(video_path)
                                    except Exception as e:
                                        st.error(f"Error loading video: {e}")
                                elif video_path.startswith('videos/'):
                                     st.error(f"File not found: {video_path}")
                                else:
                                    st.error(video_path) # Show "No video found..."

                    except Exception as e:
                        st.error(f"Failed to process agent output. Error: {e}")
                        st.text(f"Raw output: {crew_config.raw}")

                else:
                    st.error(f"Agent failed to generate sequence. Log: {crew_result}")
        else:
            st.warning("Please enter a sentence first.")