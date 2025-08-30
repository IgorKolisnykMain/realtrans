#!/usr/bin/env python3
"""
TTS Manager for RealTrans
Handles Text-to-Speech conversion using edge-tts
Adapted for integration with RealTrans architecture
"""

import edge_tts
import asyncio
import os
import tempfile
import pygame
import threading
from typing import Optional
import time

class TTSManager:
    def __init__(self, voice: str = "ru-RU-DariyaNeural", enabled: bool = True):
        """
        Initialize TTS Manager
        
        Args:
            voice: Edge-TTS voice for Russian (default: ru-RU-DariyaNeural)
            enabled: Whether TTS is enabled
        """
        self.voice = voice
        self.enabled = enabled
        self.is_playing = False
        self._temp_files = []
        
        # Initialize pygame mixer for audio playback
        if self.enabled:
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                print(f"TTS Manager initialized with voice: {self.voice}")
            except Exception as e:
                print(f"TTS pygame initialization failed: {e}")
                self.enabled = False

    def set_enabled(self, enabled: bool):
        """Enable or disable TTS"""
        self.enabled = enabled
        print(f"TTS {'enabled' if enabled else 'disabled'}")

    def set_voice(self, voice: str):
        """Change TTS voice"""
        self.voice = voice
        print(f"TTS voice changed to: {voice}")

    async def _synthesize_async(self, text: str) -> Optional[str]:
        """
        Synthesize text to speech file asynchronously
        
        Args:
            text: Text to synthesize
            
        Returns:
            Path to temporary audio file or None if failed
        """
        if not text.strip():
            return None
            
        try:
            # Create temporary file with mp3 extension (edge-tts default format)
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Synthesize using edge-tts
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(temp_path)
            
            # Track temp file for cleanup
            self._temp_files.append(temp_path)
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                return temp_path
            else:
                print("TTS: Audio file was not created properly")
                return None
                
        except Exception as e:
            print(f"TTS synthesis error: {e}")
            return None

    def _play_audio_sync(self, file_path: str) -> bool:
        """
        Play audio file synchronously
        
        Args:
            file_path: Path to audio file
            
        Returns:
            True if played successfully
        """
        try:
            if not os.path.exists(file_path):
                return False
                
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            return True
            
        except Exception as e:
            print(f"TTS playback error: {e}")
            return False

    def _play_audio_thread(self, file_path: str):
        """Play audio in separate thread to avoid blocking"""
        self.is_playing = True
        success = self._play_audio_sync(file_path)
        
        # Clean up temp file
        try:
            if file_path in self._temp_files:
                os.unlink(file_path)
                self._temp_files.remove(file_path)
        except:
            pass
            
        self.is_playing = False
        
        if not success:
            print("TTS: Audio playback failed")

    def speak_async(self, text: str):
        """
        Convert text to speech and play asynchronously
        Non-blocking method for integration with RealTrans main loop
        
        Args:
            text: Text to speak
        """
        if not self.enabled or not text.strip():
            return
            
        # Don't start new speech if already playing
        if self.is_playing:
            return
            
        def tts_worker():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Synthesize audio
                audio_file = loop.run_until_complete(self._synthesize_async(text))
                loop.close()
                
                if audio_file:
                    # Play in separate thread to avoid blocking
                    play_thread = threading.Thread(
                        target=self._play_audio_thread, 
                        args=(audio_file,),
                        daemon=True
                    )
                    play_thread.start()
                    
            except Exception as e:
                print(f"TTS worker error: {e}")
        
        # Start TTS in background thread
        tts_thread = threading.Thread(target=tts_worker, daemon=True)
        tts_thread.start()

    def speak_sync(self, text: str) -> bool:
        """
        Convert text to speech and play synchronously
        Blocking method for testing
        
        Args:
            text: Text to speak
            
        Returns:
            True if successful
        """
        if not self.enabled or not text.strip():
            return False
            
        try:
            # Create event loop for synthesis
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            audio_file = loop.run_until_complete(self._synthesize_async(text))
            loop.close()
            
            if audio_file:
                success = self._play_audio_sync(audio_file)
                
                # Clean up
                try:
                    os.unlink(audio_file)
                    if audio_file in self._temp_files:
                        self._temp_files.remove(audio_file)
                except:
                    pass
                    
                return success
                
            return False
            
        except Exception as e:
            print(f"TTS sync error: {e}")
            return False

    def cleanup(self):
        """Clean up temporary files"""
        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        self._temp_files.clear()

    def __del__(self):
        """Destructor - cleanup temp files"""
        self.cleanup()


# Available Russian voices for edge-tts
RUSSIAN_VOICES = {
    "dariya": "ru-RU-DariyaNeural",      # Female, clear
    "svetlana": "ru-RU-SvetlanaNeural",  # Female, warm
    "dmitry": "ru-RU-DmitryNeural",      # Male, confident
    "pavel": "ru-RU-PavelNeural"         # Male, deep
}

def get_available_voices():
    """Get list of available Russian voices"""
    return RUSSIAN_VOICES

# Test function
if __name__ == "__main__":
    print("Testing TTS Manager...")
    
    tts = TTSManager()
    
    test_text = "Привет! Это тест системы синтеза речи для RealTrans."
    print(f"Synthesizing: {test_text}")
    
    success = tts.speak_sync(test_text)
    print(f"TTS test {'successful' if success else 'failed'}")
    
    tts.cleanup()
    print("TTS test completed")