# =============================================================
# NEKOVA Standard Library — Voice Module
# =============================================================
# Provides text-to-speech and speech-to-text capabilities.
#
# Usage in NEKOVA:
#   use voice
#   voice_speak("Hello from NEKOVA!")
#   transcript = voice_listen()

import os


def voice_speak(text: str) -> str:
    """
    Convert text to speech and play it aloud.
    Uses edge-tts for natural voice, falls back to pyttsx3.

    Usage in NEKOVA:
        voice_speak("Hello from NEKOVA!")
    """
    text = str(text)

    # Try edge-tts first — Microsoft's natural online voices
    try:
        import edge_tts
        import asyncio
        import tempfile
        import subprocess
        import time

        async def _speak():
            communicate = edge_tts.Communicate(
                text,
                voice="en-US-JennyNeural"  # natural female voice
            )
            with tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            ) as tmp:
                tmp_path = tmp.name

            await communicate.save(tmp_path)
            return tmp_path

        tmp_path = asyncio.run(_speak())

        try:
            # Estimate audio duration: ~150 words/minute, mp3 ~1 sec/word rough
            word_count  = max(1, len(text.split()))
            duration_s  = max(2, int(word_count / 2.5) + 1)

            # Play the mp3 on Windows using a subprocess list (safe, no injection)
            subprocess.run(
                ["powershell", "-c",
                 "Add-Type -AssemblyName presentationCore;"
                 "$p=New-Object system.windows.media.mediaplayer;"
                 f"$p.Open([uri]'{tmp_path}');"
                 "$p.Play();"
                 f"Start-Sleep -s {duration_s}"],
                capture_output=True
            )
        finally:
            # Always clean up the temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        return text

    except ImportError:
        pass
    except Exception:
        pass

    # Fallback — pyttsx3 with Zira
    try:
        import pyttsx3
        engine = pyttsx3.init()
        zira_id = "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_EN-US_ZIRA_11.0"
        engine.setProperty("voice", zira_id)
        engine.setProperty("rate", 145)
        engine.setProperty("volume", 1.0)
        engine.say(text)
        engine.runAndWait()
        return text

    except Exception:
        print(f"🔊 {text}")
        return text


def voice_listen(timeout: int = 5) -> str:
    """
    Record audio from the microphone and transcribe it.
    Falls back to text input if microphone unavailable.

    Usage in NEKOVA:
        transcript = voice_listen()
        show "You said: {transcript}"
    """
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            print("🎤 Listening... (speak now)")
            recognizer.adjust_for_ambient_noise(
                source, duration=0.5
            )
            audio = recognizer.listen(
                source, timeout=timeout
            )

        print("🔄 Transcribing...")

        try:
            text = recognizer.recognize_google(audio)
            print(f"✓ Heard: {text}")
            return text
        except sr.UnknownValueError:
            return "[voice: could not understand audio]"
        except sr.RequestError as e:
            return f"[voice: recognition service error: {e}]"

    except ImportError:
        print("🎤 [Microphone unavailable — type instead]")
        return input("  You: ")
    except Exception as e:
        print(f"🎤 [Microphone error: {e} — type instead]")
        return input("  You: ")


def voice_save(text: str, filepath: str) -> str:
    """
    Save text as an audio file (mp3).

    Usage in NEKOVA:
        voice_save("Hello world", "greeting.mp3")
    """
    try:
        from gtts import gTTS
        tts = gTTS(text=str(text), lang="en", slow=False)
        tts.save(filepath)
        return filepath
    except ImportError:
        return "[voice error: gtts not installed]"
    except Exception as e:
        return f"[voice error: {e}]"


def load() -> dict:
    """Return all voice functions for NEKOVA's use statement."""
    return {
        "voice_speak":  voice_speak,
        "voice_listen": voice_listen,
        "voice_save":   voice_save,
    }