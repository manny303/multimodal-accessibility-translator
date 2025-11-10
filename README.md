# Multimodal-Accessibility-Translator

This project is a multi-agent system built with **CrewAI** designed to make digital content accessible across different modalities. It provides solutions for users with visual, hearing, or cognitive disabilities by translating content into their preferred format.

The application is built as a single, interactive web app with three modules:

1.  **Image-to-Audio:** Generates detailed audio descriptions for images.
2.  **Text-to-Visual:** Simplifies complex text into a text-free visual diagram.
3.  **Text-to-Sign Language:** Translates English sentences into a sequence of ASL video demonstrations from the WLASL dataset.

-----

## 🚀 How to Run This Project

This application is built in Python using Streamlit.

1.  **Set up the Environment:**

      * Clone or download the project folder.
      * Open a terminal in the project folder and create a virtual environment:
        ```bash
        python3 -m venv venv
        ```
      * Activate the environment:
        ```bash
        source venv/bin/activate
        ```

2.  **Install Dependencies:**

      * Install all required libraries:
        ```bash
        pip install -r requirements.txt
        ```

3.  **Set API Key:**

      * Create a folder named `.streamlit`.
      * Inside that folder, create a file named `secrets.toml`.
      * Add your OpenAI API key to this file:
        ```toml
        OPENAI_API_KEY = "sk-YourSecretKeyHere"
        ```

4.  **Run the App:**

      * Run the Streamlit application from your terminal:
        ```bash
        streamlit run app.py
        ```
      * Your web browser will automatically open with the running application.

-----

## 🤖 Agentic Architecture

This project is orchestrated by a system of **CrewAI agents**. An agentic framework was chosen because the translation tasks are not simple, one-step processes. They require a "chain of thought," specialization, and the coordination of different tools (AI models, data maps, etc.).

Each module is powered by a dedicated "Crew" of agents:

  * **Module 1 Crew:** A 2-agent team for visual description and audio production.
  * **Module 2 Crew:** A 2-agent "brain" for linguistic translation and video sequencing.
  * **Module 3 Crew:** A 1-agent specialist for visual simplification.

-----

## 👁️ Module 1: Image-to-Audio

This module assists users with visual impairments by converting images into rich, natural-sounding audio descriptions.

  * **Agents:**
    1.  [cite\_start]`Visual_Describer`: Its sole job is to analyze an image with GPT-4V and generate three levels of description (Brief, Standard, Detailed) based on W3C WAI guidelines[cite: 11].
    2.  `Audio_Producer`: It receives the text from the first agent and uses an OpenAI TTS model to generate a high-quality audio file.
  * **Process:** The agents work sequentially. The `Audio_Producer` waits for the `Visual_Describer` to finish, ensuring the audio always matches the final text.
  * **Result:** The user uploads an image and receives both the text descriptions and a playable audio file.

-----

## 🧠 Module 2: Text-to-Visual

This module assists users with cognitive disabilities by converting blocks of complex text into simple, easy-to-understand visual explanations.

  * **Agent:**
    1.  `Visual_Simplifier`: A single-agent specialist that uses GPT-4o to read complex text, extract the core concepts, and then design a new, highly detailed prompt for DALL-E 3.
  * **Key Challenge & Tradeoff:**
    During testing, a key limitation of current generative AI was discovered: **AI is excellent at generating *images* but very poor at generating *text within* those images.** Early prototypes resulted in diagrams with misspelled or nonsensical labels.
  * **Our Solution:** The `Visual_Simplifier` agent is now prompted to create **text-free visual metaphors** that rely only on icons, arrows, and relationships. This results in a cleaner, more accurate, and more useful final product.

-----

## ✋ Module 3: Text-to-Sign Language

This is the most complex module, designed to help users in the Deaf community by translating English text into American Sign Language.

  * **Key Challenge (The "Stretch Goal"):**
    Using "actual animated sign language avatar" as a **Stretch Goal** [cite: 123] [cite\_start]and tools like `JASigning`is a massive, multi-month research problem, as it requires complex linguistic mapping and 3D avatar integration.

  * **Our "Project Leader" Solution (The "Brain"):**
   This project builds the **"brain"** that would be necessary to power *any* sign language system. We solve the true, underlying challenge: **linguistics and data mapping**.

  * **Agents & Process:**

    1.  **`ASL_Grammar_Agent`:** This agent acts as an expert linguist. [cite\_start]It receives an English sentence (e.g., "I am going to the store") and translates it into the correct ASL grammatical structure (`['STORE', 'I', 'GO-TO']`), which is essential for accurate signing[cite: 39].
    2.  **`Sign_Sequencer_Agent`:** This agent takes the grammatical list from the first agent. Its tool, the `SignDetailTool`, then does two things for each sign:
          * **AI Description:** It makes an AI call to get a **textual description** of how to perform the sign.
          * [cite\_start]**Video Lookup:** It performs a high-speed lookup in a local `sign_video_map.json` (created from the **WLASL Dataset** [cite: 30]) to find the matching video file.

  * **Result:** The user gets a side-by-side sequence that is both accessible and educational. For each sign in the translated sentence, they see:

    1.  The sign word
    2.  A text description of how to perform it
    3.  A **real video** of a human signing the word.

  * **Tradeoff:** This high-quality, hybrid approach is the most computationally intensive, as it makes multiple AI calls (1 for grammar + N for descriptions). The result is an incredibly accurate and useful translation, but it takes longer to process than the other modules.